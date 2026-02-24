#!/usr/bin/env python3
"""Local MedGemma Inference Module"""

import os

import torch
from PIL import Image
from transformers import AutoModelForCausalLM
from transformers.models.gemma3.processing_gemma3 import Gemma3Processor


class LocalMedGemma:
    """Local MedGemma model runner."""

    def __init__(self, model_id="google/medgemma-1.5-4b-it"):
        print("\n" + "=" * 60)
        print("Loading MedGemma Model Locally")
        print("=" * 60)
        print(f"Model: {model_id}")
        print("Device: MPS (Apple Silicon)")
        print("\nThis will download ~8GB on first run...")
        print("=" * 60 + "\n")

        print("Loading processor...")
        self.processor = Gemma3Processor.from_pretrained(model_id)

        print("Loading model to MPS...")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16,
            device_map="mps",
            low_cpu_mem_usage=True,
        )

        print("✓ MedGemma loaded successfully!\n")

    def generate(self, image_path, prompt, max_tokens=500, temperature=0.0):
        """Generate response from MedGemma."""
        image = Image.open(image_path).convert("RGB")

        messages = [
            {
                "role": "user",
                "content": [{"type": "image"}, {"type": "text", "text": prompt}],
            }
        ]

        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = self.processor(text=text, images=image, return_tensors="pt").to("mps")

        print("Generating response...")
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=1000,
                min_new_tokens=100,
                do_sample=False,
                num_beams=1,
                pad_token_id=self.processor.tokenizer.eos_token_id,
                eos_token_id=self.processor.tokenizer.eos_token_id,
                early_stopping=False,
            )

        response = self.processor.batch_decode(outputs, skip_special_tokens=True)[0]

        # Remove the prompt echo
        if text in response:
            response = response.replace(text, "").strip()

        # Remove conversation markers
        if "model\n" in response:
            response = response.split("model\n")[-1].strip()

        response = response.replace("user\n", "").strip()

        return response


_model_instance = None


def get_medgemma():
    global _model_instance
    if _model_instance is None:
        _model_instance = LocalMedGemma()
    return _model_instance


def ask_medgemma(image_path, prompt, max_tokens=500, temperature=0.0):
    model = get_medgemma()
    return model.generate(image_path, prompt, max_tokens, temperature)
