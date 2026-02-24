#!/usr/bin/env python3
"""
Flask API for Medical-Clarity
Connects Next.js UI to MedSAM2 + MedGemma pipeline
"""

import os
import json
import tempfile
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import subprocess
import sys

app = Flask(__name__)
CORS(app)  # Allow requests from Next.js (localhost:3000)

# Paths
PIPELINE_SCRIPT = os.path.join(os.path.dirname(__file__), "complete_pipeline.py")
DEMO_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "web-app", "public", "demo", "ankle")
UPLOAD_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "userOutput")


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "Medical-Clarity API is running"})


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Analyze uploaded MRI image
    
    Expects: multipart/form-data with 'image' file
    Returns: JSON with regions, diagnosis, visualization
    """
    
    # Validate request
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files["image"]
    
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    
    # Save uploaded file temporarily
    try:
        # Create temp file with proper extension
        suffix = Path(file.filename).suffix or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            file.save(tmp_path)
        
        print(f"Saved uploaded file to: {tmp_path}")
        
        # Run the pipeline
        print("Running MedSAM2 + MedGemma pipeline...")
        result = run_pipeline(tmp_path)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Clean up on error
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        
        return jsonify({"error": str(e)}), 500


def run_pipeline(image_path):
    """
    Run complete_pipeline.py on the uploaded image
    
    Returns: Dictionary with analysis results
    """
    
    pipeline_dir = os.path.dirname(PIPELINE_SCRIPT)
    
    # Create userOutput folder
    os.makedirs(UPLOAD_OUTPUT_DIR, exist_ok=True)
    
    # Copy uploaded image to pipeline folder as upload.png
    import shutil
    upload_input_path = os.path.join(pipeline_dir, "upload.png")
    shutil.copy(image_path, upload_input_path)
    
    # Modify pipeline script to use upload.png and output to userOutput
    # We'll do this by temporarily modifying the INPUT and OUTPUT variables
    pipeline_backup = PIPELINE_SCRIPT + ".backup"
    shutil.copy(PIPELINE_SCRIPT, pipeline_backup)
    
    try:
        # Read pipeline script
        with open(PIPELINE_SCRIPT, 'r') as f:
            pipeline_code = f.read()
        
        # Replace paths
        modified_code = pipeline_code.replace(
            'DEMO_INPUT_IMAGE = os.path.join(BASE_DIR, "ankle.png")',
            'DEMO_INPUT_IMAGE = os.path.join(BASE_DIR, "upload.png")'
        )
        modified_code = modified_code.replace(
            'DEMO_OUTPUT_DIR = os.path.join(BASE_DIR, "..", "web-app", "public", "demo", "ankle")',
            f'DEMO_OUTPUT_DIR = "{UPLOAD_OUTPUT_DIR}"'
        )
        
        # Write modified pipeline
        with open(PIPELINE_SCRIPT, 'w') as f:
            f.write(modified_code)
        
        # Run pipeline
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        process = subprocess.Popen(
            [sys.executable, PIPELINE_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=pipeline_dir
        )
        
        # Stream output
        for line in process.stdout:
            print(line, end="")
        
        process.wait()
        
        if process.returncode != 0:
            raise Exception(f"Pipeline failed with code {process.returncode}")
        
        # Read output files from userOutput
        output_json_path = os.path.join(UPLOAD_OUTPUT_DIR, "data.json")
        output_viz_path = os.path.join(UPLOAD_OUTPUT_DIR, "annotated_visualization.png")
        output_original_path = os.path.join(UPLOAD_OUTPUT_DIR, "upload.png")
        
        if not os.path.exists(output_json_path):
            raise Exception(f"Pipeline did not generate output JSON at {output_json_path}")
        
        # Load results
        with open(output_json_path, "r") as f:
            data = json.load(f)
        
        # Convert to frontend format
        regions = []
        for region in data.get("regions", []):
            regions.append({
                "id": region.get("id", ""),
                "number": region.get("number", 0),
                "label": region.get("label", ""),
                "mentioned": region.get("mentioned_in_diagnosis", False),
                "color": region.get("color", [128, 128, 128]),
                "bbox": region.get("bbox", [0, 0, 0, 0]),
                "center": region.get("center", [0, 0])
            })
        
        # Get diagnosis text
        diagnosis_text = data.get("diagnosis", {}).get("full_report", "")
        
        # Read original uploaded image as base64
        import base64
        with open(output_original_path, "rb") as f:
            original_base64 = base64.b64encode(f.read()).decode("utf-8")
        
        response = {
            "visualization": f"data:image/png;base64,{original_base64}",
            "regions": regions,
            "diagnosis": diagnosis_text,
            "metadata": data.get("image_info", {})
        }
        
        return response
        
    finally:
        # Restore original pipeline script
        shutil.move(pipeline_backup, PIPELINE_SCRIPT)
        
        # Clean up upload input
        if os.path.exists(upload_input_path):
            os.unlink(upload_input_path)


if __name__ == "__main__":
    print("=" * 60)
    print("Medical-Clarity API Server")
    print("=" * 60)
    print(f"Pipeline: {PIPELINE_SCRIPT}")
    print(f"Demo output: {DEMO_OUTPUT_DIR}")
    print(f"Upload output: {UPLOAD_OUTPUT_DIR}")
    print("\nStarting server on http://localhost:8000")
    print("Ready to accept MRI uploads from Next.js UI")
    print("=" * 60)
    
    app.run(host="0.0.0.0", port=8000, debug=True)
