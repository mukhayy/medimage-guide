#!/usr/bin/env python3
"""
Complete MRI Analysis Pipeline for Interactive Diagnosis
==========================================================

Flow:
1. MedSAM2 segments anatomical regions
2. MedGemma labels each region with medical terminology
3. MedGemma generates diagnostic report
4. Match diagnosis mentions to labeled regions
5. Output structured data for UI highlighting

This enables real-time highlighting of regions as diagnosis is read.
"""

import json
import os
import re
from pathlib import Path

import cv2
import numpy as np
import torch
from hydra import initialize_config_dir
from hydra.core.global_hydra import GlobalHydra

# Import local MedGemma
from medgemma_local import ask_medgemma
from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
from sam2.build_sam import build_sam2

# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "sam2", "configs")
MODEL_CFG = "sam2.1_hiera_t512.yaml"
CHECKPOINT = os.path.join(BASE_DIR, "checkpoints", "MedSAM2_latest.pt")

# Input/Output paths - DEMO ONLY (hardcoded for demo generation)
DEMO_INPUT_IMAGE = os.path.join(BASE_DIR, "ankle.png")

# Save directly to web-app demo folder
DEMO_OUTPUT_DIR = os.path.join(BASE_DIR, "..", "web-app", "public", "demo", "ankle")
os.makedirs(DEMO_OUTPUT_DIR, exist_ok=True)

DEMO_OUTPUT_VISUALIZATION = os.path.join(DEMO_OUTPUT_DIR, "annotated_visualization.png")
DEMO_OUTPUT_JSON = os.path.join(DEMO_OUTPUT_DIR, "data.json")
DEMO_OUTPUT_DIAGNOSIS = os.path.join(DEMO_OUTPUT_DIR, "diagnosis_report.txt")
DEMO_OUTPUT_ORIGINAL = os.path.join(DEMO_OUTPUT_DIR, "ankle.png")  # Copy of original

DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"

# =============================================================================
# STEP 1: SEGMENT WITH MedSAM2
# =============================================================================


def segment_image(image_path):
    """Segment MRI image using MedSAM2."""
    print("\n" + "=" * 60)
    print("STEP 1: Segmenting with MedSAM2")
    print("=" * 60)

    if GlobalHydra.instance().is_initialized():
        GlobalHydra.instance().clear()
    initialize_config_dir(config_dir=CONFIG_DIR, version_base="1.2")

    print("Loading MedSAM2...")
    sam2_model = build_sam2(
        MODEL_CFG, CHECKPOINT, device=DEVICE, apply_postprocessing=False
    )

    mask_generator = SAM2AutomaticMaskGenerator(
        model=sam2_model,
        points_per_side=36,          # Increased from 28 for finer detection
        points_per_batch=64,
        pred_iou_thresh=0.45,         # Lowered from 0.5 to accept more regions
        stability_score_thresh=0.75,  # Lowered from 0.8 for more permissive detection
        crop_n_layers=1,
        crop_n_points_downscale_factor=2,
        min_mask_region_area=200,    # Lowered from 150 to catch smaller structures
    )

    print(f"Loading image: {image_path}")
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    image = cv2.normalize(image, None, 0, 255, cv2.NORM_MINMAX)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

    print("Running segmentation...")
    masks = mask_generator.generate(image_rgb)

    print(f"✓ Found {len(masks)} regions")
    return masks, image_rgb


def remove_overlapping_regions(masks, iou_threshold=0.3):
    """Remove overlapping masks."""
    print("\nRemoving overlapping regions...")

    def compute_iou(box1, box2):
        x1, y1, w1, h1 = box1
        x2, y2, w2, h2 = box2

        box1_coords = [x1, y1, x1 + w1, y1 + h1]
        box2_coords = [x2, y2, x2 + w2, y2 + h2]

        xi1 = max(box1_coords[0], box2_coords[0])
        yi1 = max(box1_coords[1], box2_coords[1])
        xi2 = min(box1_coords[2], box2_coords[2])
        yi2 = min(box1_coords[3], box2_coords[3])

        inter_area = max(0, xi2 - xi1) * max(0, yi2 - yi1)

        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - inter_area

        return inter_area / union_area if union_area > 0 else 0

    sorted_masks = sorted(masks, key=lambda x: x["area"], reverse=True)

    keep_masks = []
    for mask in sorted_masks:
        overlaps = False
        for kept_mask in keep_masks:
            iou = compute_iou(mask["bbox"], kept_mask["bbox"])
            if iou > iou_threshold:
                overlaps = True
                break

        if not overlaps:
            keep_masks.append(mask)

    print(f"Filtered {len(masks)} → {len(keep_masks)} regions")
    return keep_masks


# =============================================================================
# STEP 2: CREATE VISUALIZATION
# =============================================================================


def create_colored_visualization(image, masks, output_path):
    """Create colored mask visualization with numbers."""
    print("\n" + "=" * 60)
    print("STEP 2: Creating Colored Visualization")
    print("=" * 60)

    h, w = image.shape[:2]
    colored_mask = np.zeros((h, w, 3), dtype=np.uint8)

    sorted_masks = sorted(masks, key=lambda x: x["area"], reverse=True)

    # Generate distinct colors
    np.random.seed(42)
    colors = []
    for i in range(len(sorted_masks)):
        color = [
            np.random.randint(50, 255),
            np.random.randint(50, 255),
            np.random.randint(50, 255),
        ]
        colors.append(color)

    # Apply masks
    for mask_dict, color in zip(sorted_masks, colors):
        mask = mask_dict["segmentation"]
        colored_mask[mask] = color

    # Blend
    alpha = 0.5
    blended = cv2.addWeighted(image, 1 - alpha, colored_mask, alpha, 0)

    # Add numbers
    for idx, mask_dict in enumerate(sorted_masks, start=1):
        mask = mask_dict["segmentation"]

        y_indices, x_indices = np.where(mask)
        if len(x_indices) > 0:
            centroid_x = int(np.mean(x_indices))
            centroid_y = int(np.mean(y_indices))
        else:
            bbox = mask_dict["bbox"]
            centroid_x = int(bbox[0] + bbox[2] / 2)
            centroid_y = int(bbox[1] + bbox[3] / 2)

        label = str(idx)
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        thickness = 3

        (text_width, text_height), _ = cv2.getTextSize(
            label, font, font_scale, thickness
        )

        circle_radius = max(text_width, text_height) // 2 + 10
        cv2.circle(
            blended, (centroid_x, centroid_y), circle_radius, (255, 255, 255), -1
        )
        cv2.circle(blended, (centroid_x, centroid_y), circle_radius, (0, 0, 0), 2)

        text_x = centroid_x - text_width // 2
        text_y = centroid_y + text_height // 2
        cv2.putText(
            blended, label, (text_x, text_y), font, font_scale, (0, 0, 0), thickness
        )

    cv2.imwrite(output_path, blended)
    print(f"✓ Created visualization with {len(sorted_masks)} regions")
    print(f"✓ Saved to: {output_path}")

    return sorted_masks, colors


# =============================================================================
# STEP 3: LABEL REGIONS
# =============================================================================


def label_regions_with_medgemma(image_path, num_regions):
    """Get anatomical labels for each region."""
    print("\n" + "=" * 60)
    print("STEP 3: Labeling Regions with MedGemma")
    print("=" * 60)

    prompt = f"""This is a medical MRI scan with {num_regions} numbered anatomical regions shown as colored masks.

Carefully identify each numbered region using precise medical terminology.

Respond ONLY in this format (one per line):
1: [specific anatomical structure]
2: [specific anatomical structure]
3: [specific anatomical structure]
...continue for all {num_regions} regions

Be specific - each number marks a different structure (bones, tendons, ligaments, soft tissues, organs, etc.)."""

    print(f"Calling MedGemma for region labeling...")
    response = ask_medgemma(
        image_path=image_path, prompt=prompt, max_tokens=800, temperature=0.0
    )

    print(f"✓ Received labels from MedGemma")

    # Parse labels
    labels = {}
    for line in response.strip().split("\n"):
        line = line.strip()
        if not line:
            continue

        if ":" in line:
            parts = line.split(":", 1)
        elif "." in line and line[0].isdigit():
            parts = line.split(".", 1)
        else:
            continue

        try:
            region_num = int(parts[0].strip())
            label = parts[1].strip()

            if label and label not in [
                "[specific anatomical structure]",
                "[anatomical structure name]",
            ]:
                labels[region_num] = label.lower()  # Lowercase for matching
        except (ValueError, IndexError):
            continue

    print(f"✓ Parsed {len(labels)} region labels")
    return labels


# =============================================================================
# STEP 4: GENERATE DIAGNOSTIC REPORT
# =============================================================================


def generate_diagnosis_report(original_image_path):
    """Generate diagnostic report from MedGemma."""
    print("\n" + "=" * 60)
    print("STEP 4: Generating Diagnostic Report")
    print("=" * 60)

    prompt = """You are an experienced radiologist analyzing this MRI scan.

Provide a detailed radiology report with specific observations about each visible structure.

FINDINGS:
Systematically describe all visible anatomical structures:
- Identify the body region and imaging plane shown
- Bone structures: assess for edema, fractures, degenerative changes, alignment, lesions
- Joint spaces: assess for effusion, narrowing, erosions
- Soft tissues: muscles, tendons, ligaments (thickness, signal, tears, sprains)
- Organs (if visible): assess morphology and signal characteristics
- Vessels and nerves (if visible)
- Any edema, masses, fluid collections, or abnormal signals

IMPRESSION:
1. Identify the anatomical region being imaged
2. Prioritize key findings
3. Grade severity (mild/moderate/severe) if abnormalities present
4. Note any incidental findings

RECOMMENDATIONS:
Suggest further imaging or clinical correlation if warranted.

Be specific and detailed. If you see normal structures, explicitly state they are normal."""

    print("Calling MedGemma for diagnostic analysis...")
    diagnosis = ask_medgemma(
        image_path=original_image_path, prompt=prompt, max_tokens=1000, temperature=0.3
    )

    print(f"✓ Generated diagnostic report ({len(diagnosis)} chars)")
    return diagnosis


# =============================================================================
# STEP 5: MATCH DIAGNOSIS TO REGIONS
# =============================================================================


def match_diagnosis_to_regions(diagnosis_text, region_labels):
    """Find which regions are mentioned in the diagnosis."""
    print("\n" + "=" * 60)
    print("STEP 5: Matching Diagnosis to Regions")
    print("=" * 60)

    diagnosis_lower = diagnosis_text.lower()

    matches = {}
    mentioned_terms = []

    for region_id, label in region_labels.items():
        mentioned = False
        
        # Direct match - exact label
        pattern = r"\b" + re.escape(label) + r"\b"
        if re.search(pattern, diagnosis_lower):
            mentioned = True
        else:
            # Category matching for plurals
            # Check if diagnosis mentions the category that this region belongs to
            
            # Extract base term (remove modifiers like "first", "medial", etc.)
            label_words = label.split()
            
            # Common anatomical categories with their plural forms
            category_patterns = {
                'cuneiform': r'\bcuneiforms\b',
                'metatarsal': r'\bmetatarsals\b',
                'phalanx': r'\bphalanges\b',
                'tarsal': r'\btarsal bones\b',
                'tendon': r'\btendons\b',
                'ligament': r'\bligaments\b',
                'joint': r'\bjoints\b',
            }
            
            # Check if any word in the label matches a category
            for word in label_words:
                if word in category_patterns:
                    plural_pattern = category_patterns[word]
                    if re.search(plural_pattern, diagnosis_lower):
                        mentioned = True
                        break
        
        if mentioned:
            matches[region_id] = {"label": label, "mentioned": True}
            mentioned_terms.append(label)
            print(f"  ✓ Region {region_id} ({label}) mentioned in diagnosis")
        else:
            matches[region_id] = {"label": label, "mentioned": False}

    print(f"\n✓ Found {len(mentioned_terms)} regions mentioned in diagnosis")
    return matches, mentioned_terms


# =============================================================================
# STEP 6: CREATE OUTPUT FILES
# =============================================================================


def create_output_files(masks, labels, matches, diagnosis, colors, image_name, image):
    """Create all output files."""
    print("\n" + "=" * 60)
    print("STEP 6: Creating Output Files")
    print("=" * 60)

    sorted_masks = sorted(masks, key=lambda x: x["area"], reverse=True)

    # Build regions data
    regions = []
    for idx, mask_dict in enumerate(sorted_masks, start=1):
        bbox = mask_dict["bbox"]
        x, y, w, h = bbox

        label = labels.get(idx, f"unlabeled_region_{idx}")
        match_info = matches.get(idx, {"mentioned": False})

        # Get RGB color for this region
        color_rgb = colors[idx - 1] if idx <= len(colors) else [128, 128, 128]

        region_data = {
            "id": f"region_{idx}",
            "number": idx,
            "label": label,
            "mentioned_in_diagnosis": match_info["mentioned"],
            "bbox": [int(x), int(y), int(x + w), int(y + h)],
            "center": [int(x + w // 2), int(y + h // 2)],
            "area": int(mask_dict["area"]),
            "color": color_rgb,  # For UI to highlight exact region
            "confidence": float(mask_dict.get("predicted_iou", 0.0)),
            "stability": float(mask_dict.get("stability_score", 0.0)),
        }

        regions.append(region_data)

    image_height, image_width = image.shape[:2]
    # Create JSON output
    output_data = {
        "image_info": {
            "filename": f"{image_name}.png",
            "num_regions": len(regions),
            "width": int(image_width),
            "height": int(image_height),
        },
        "regions": regions,
        "diagnosis": {
            "full_report": diagnosis,
            "mentioned_regions": [
                r["label"] for r in regions if r["mentioned_in_diagnosis"]
            ],
            "num_mentioned": sum(1 for r in regions if r["mentioned_in_diagnosis"]),
        },
    }

    # Save JSON
    with open(DEMO_OUTPUT_JSON, "w") as f:
        json.dump(output_data, f, indent=2)
    print(f"✓ Saved JSON to: {DEMO_OUTPUT_JSON}")

    # Save diagnosis report
    report_header = f"""MRI ANALYSIS REPORT
Generated: {image_name}
Regions Identified: {len(regions)}
Regions Mentioned in Diagnosis: {output_data["diagnosis"]["num_mentioned"]}

{"=" * 60}

"""

    with open(DEMO_OUTPUT_DIAGNOSIS, "w") as f:
        f.write(report_header)
        f.write(diagnosis)
    print(f"✓ Saved diagnosis to: {DEMO_OUTPUT_DIAGNOSIS}")

    return output_data


# =============================================================================
# MAIN PIPELINE
# =============================================================================


def main():
    """Run the complete pipeline."""
    print("\n" + "=" * 60)
    print("DEMO GENERATION PIPELINE")
    print("Segmentation → Labeling → Diagnosis → Region Matching")
    print("=" * 60)
    print(f"Demo Input: {DEMO_INPUT_IMAGE}")
    print(f"Demo Output: {DEMO_OUTPUT_DIR}")
    print(f"Device: {DEVICE}")

    if not os.path.exists(DEMO_INPUT_IMAGE):
        print(f"\n❌ Error: Demo input image not found: {DEMO_INPUT_IMAGE}")
        return

    try:
        # Step 1: Segment with MedSAM2
        masks, image = segment_image(DEMO_INPUT_IMAGE)
        masks = remove_overlapping_regions(masks, iou_threshold=0.3)

        # Step 2: Visualize
        sorted_masks, colors = create_colored_visualization(
            image, masks, DEMO_OUTPUT_VISUALIZATION
        )

        # Step 3: Label regions
        region_labels = label_regions_with_medgemma(
            DEMO_OUTPUT_VISUALIZATION, len(sorted_masks)
        )

        # Step 4: Generate diagnosis
        diagnosis = generate_diagnosis_report(DEMO_INPUT_IMAGE)

        # Step 5: Match diagnosis to regions
        matches, mentioned_terms = match_diagnosis_to_regions(diagnosis, region_labels)

        # Step 6: Create outputs
        image_name = Path(DEMO_INPUT_IMAGE).stem
        output_data = create_output_files(
            sorted_masks, region_labels, matches, diagnosis, colors, image_name, image
        )
        
        # Copy original image to demo folder
        import shutil
        shutil.copy(DEMO_INPUT_IMAGE, DEMO_OUTPUT_ORIGINAL)

        print("\n" + "=" * 60)
        print("DEMO GENERATION COMPLETE!")
        print("=" * 60)
        print(f"✓ Segmented regions: {len(sorted_masks)}")
        print(f"✓ Labeled regions: {len(region_labels)}")
        print(
            f"✓ Regions mentioned in diagnosis: {output_data['diagnosis']['num_mentioned']}"
        )
        print(f"\nMentioned regions: {', '.join(mentioned_terms)}")
        print(f"\nDemo files saved to:")
        print(f"  1. {DEMO_OUTPUT_VISUALIZATION}")
        print(f"  2. {DEMO_OUTPUT_JSON}")
        print(f"  3. {DEMO_OUTPUT_DIAGNOSIS}")

        print("\n" + "=" * 60)
        print("Ready for interactive UI!")
        print("UI can now highlight regions as diagnosis is read aloud.")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
