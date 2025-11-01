import os
import json
from PIL import Image
import torch
from huggingface_hub import login
from transformers import AutoProcessor, AutoModelForVision2Seq
import google.generativeai as genai

# -----------------------------
# 0️⃣ Setup
# -----------------------------
hf_token = os.getenv("HUGGINGFACE_TOKEN")
if hf_token:
    login(token=hf_token)
else:
    raise ValueError("❌ Hugging Face token not found. Set HUGGINGFACE_TOKEN as environment variable.")

genai_key = os.getenv("GENIE_API_KEY")
if genai_key:
    genai.configure(api_key=genai_key)
else:
    raise ValueError("❌ Gemini API key not found. Set GENIE_API_KEY as environment variable.")

# Device setup
if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
elif torch.cuda.is_available():
    DEVICE = torch.device("cuda")
else:
    DEVICE = torch.device("cpu")
print(f"✅ Using device: {DEVICE}")

# -----------------------------
# 1️⃣ Load BLIP-2
# -----------------------------
MODEL_NAME = "Salesforce/blip2-opt-2.7b"
print("⏳ Loading BLIP-2 model for captions...")
processor = AutoProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForVision2Seq.from_pretrained(MODEL_NAME)
model.to(DEVICE)
model.eval()
print(f"✅ BLIP-2 model loaded on {DEVICE}")

# -----------------------------
# 2️⃣ Caption generation
# -----------------------------
@torch.no_grad()
def generate_caption(img: Image.Image, num_beams: int = 8, max_length: int = 128) -> str:
    inputs = processor(images=img, return_tensors="pt").to(DEVICE, dtype=torch.float32)
    outputs = model.generate(**inputs, num_beams=num_beams, max_length=max_length)
    caption = processor.decode(outputs[0], skip_special_tokens=True)
    return caption

# -----------------------------
# 3️⃣ Expand caption with Gemini
# -----------------------------
def expand_caption_to_story(caption: str, min_sentences: int = 3) -> str:
    prompt = (
        f"Take the following image caption and expand it into a vivid, artisan-style description. "
        f"Include colors, textures, materials, patterns, environment, lighting, and emotions. "
        f"Make it at least {min_sentences} sentences.\n\nCaption: {caption}"
    )
    try:
        model_gemini = genai.GenerativeModel("gemini-flash-latest")
        response = model_gemini.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"❌ Gemini expansion failed: {e}"


CAPTIONS_FILE = "./artisan_images/captions.json"

def save_to_json(image_name, caption, description, file_path=CAPTIONS_FILE):
    # Load existing data if the file exists
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    # Update with new entry
    data[image_name] = {
        "caption": caption,
        "description": description
    }

    # Save back to file
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# -----------------------------
# Update your process_single_image
# -----------------------------
def process_single_image(image_path: str, thumb_size=(400, 400)):
    if not os.path.exists(image_path):
        print(f"⚠️ File not found: {image_path}")
        return

    try:
        img = Image.open(image_path).convert("RGB")
        img.thumbnail(thumb_size)

        caption = generate_caption(img)
        description = expand_caption_to_story(caption)

        img.show(title=os.path.basename(image_path))

        print(f"\n🖼️ Image: {os.path.basename(image_path)}")
        print(f"📝 Caption: {caption}")
        print("-" * 60)
        print(f"📝 Rich description:\n{description}")
        print("-" * 60)

        # Save the results
        save_to_json(os.path.basename(image_path), caption, description)

        return {
            "image": img,
            "caption": caption,
            "description": description
        }

    except Exception as e:
        print(f"❌ Error processing {image_path}: {e}")

# -----------------------------
# 5️⃣ Optional: Process batch of images
# -----------------------------
def process_batch_images(folder: str = "./artisan_images", thumb_size=(400, 400)):
    files = sorted([f for f in os.listdir(folder) if f.lower().endswith(('.jpg','.jpeg','.png','.webp','.avif'))])
    if not files:
        print(f"⚠️ No images found in {folder}")
        return

    print(f"📂 Found {len(files)} images in {folder}")
    for idx, fname in enumerate(files, start=1):
        print(f"\n--- [{idx}/{len(files)}] {fname} ---")
        path = os.path.join(folder, fname)
        process_single_image(path, thumb_size=thumb_size)

# -----------------------------
# 🔥 Standalone run example
# -----------------------------
if __name__ == "__main__":
    process_single_image("./artisan_images/img11.webp")