import os

import google.generativeai as genai
import requests
from PIL import Image
from django.conf import settings


GEMINI_API_KEY = getattr(settings, 'GEMINI_API_KEY', os.getenv("GEMINI_API_KEY"))
HF_API_KEY = getattr(settings, 'HUGGING_FACE_API_KEY', os.getenv("HUGGING_FACE_API_KEY"))

HF_INFERENCE_API_URL = "https://api-inference.huggingface.co/models/google/vit-base-patch16-224"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}


try:
    genai.configure(api_key=GEMINI_API_KEY)
    print("Gemini API configured successfully")
except Exception as e:
    print(f"Gemini API configuration failed: {e}")


def classify_image_category(image_path):
    try:
        with open(image_path, "rb") as f:
            img_bytes = f.read()

        response = requests.post(
            HF_INFERENCE_API_URL,
            headers=HF_HEADERS,
            data=img_bytes
        )
        response.raise_for_status()
        predictions = response.json()

        print("HF Predictions:", predictions)

        if isinstance(predictions, list) and len(predictions) > 0:
            label = predictions[0].get("label", "").lower()

            if "road" in label or "pothole" in label:
                return "RO"
            if "garbage" in label or "trash" in label:
                return "GA"
            if "water" in label or "pipe" in label or "electric" in label:
                return "UT"
            return "OT"

        return "OT"

    except Exception as e:
        print("HuggingFace API ERROR:", e)
        return "OT"


def generate_description(image_path, category_code):
    """Generate title and description using Gemini Vision API."""
    try:
        print(f"Starting description generation for category: {category_code}")

        if not os.path.exists(image_path):
            print(f"Image file not found: {image_path}")
            return "Civic Issue Complaint", "Issue reported by citizen"

        try:
            image = Image.open(image_path)
            print(f"Image loaded: {image.format} {image.size}")
        except Exception as img_err:
            print(f"Failed to open image: {img_err}")
            return "Civic Issue Complaint", "Issue reported by citizen"

        prompt = f"""You are a civic issue analyzer. Analyze this image of a civic complaint.

Category Type: {category_code}

Provide EXACTLY in this format:
Title: [8 words or less - clear, concise title]
Description: [40 words or less - what's the issue and where]"""

        try:
            model = genai.GenerativeModel("gemini-2.0-flash-exp")
            response = model.generate_content([
                Image.open(image_path),
                prompt
            ])

            text = response.text.strip()
            print(f"Gemini response received: {len(text)} chars")
            print(f"Raw output: {text[:200]}...")

            title = "Civic Issue Complaint"
            description = "Issue reported by citizen"

            for line in text.split('\n'):
                if 'Title:' in line:
                    title = line.split('Title:')[1].strip()[:100].strip('[]"\'')
                if 'Description:' in line:
                    description = line.split('Description:')[1].strip()[:200].strip('[]"\'')

            print(f"Title: {title}")
            print(f"Description: {description}")
            return title, description

        except Exception as gemini_err:
            print(f"Gemini generation failed: {gemini_err}")
            print(f"Error type: {type(gemini_err).__name__}")
            return "Civic Issue Complaint", "Issue reported by citizen"

    except Exception as e:
        print(f"Unexpected error in generate_description: {e}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return "Civic Issue Complaint", "Issue reported by citizen"


def calculate_severity_score(category_code):
    if category_code == "RO":
        return 75
    if category_code == "GA":
        return 60
    if category_code == "UT":
        return 90
    if category_code == "PB":
        return 40
    return 10
