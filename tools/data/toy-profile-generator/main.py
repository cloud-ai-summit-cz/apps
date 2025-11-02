"""
Toy Profile Generator with AI-generated avatars.

Generates toy profiles (name, description) and matching avatar images using
Azure OpenAI GPT and image generation models with DefaultAzureCredential authentication.
"""

import base64
import json
import os
import random
import uuid
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AzureOpenAI
from PIL import Image
from io import BytesIO
from pydantic import BaseModel


class ToyProfile(BaseModel):
    """Structured output for toy profile generation."""

    name: str
    description: str
    image_prompt: str


def load_config() -> dict[str, Any]:
    """
    Load configuration from .env file.

    Returns:
        Dictionary with configuration values.

    Raises:
        ValueError: If required environment variables are missing.
    """
    load_dotenv()

    config = {
        "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
        "gpt_model": os.getenv("GPT_DEPLOYMENT_NAME"),
        "image_model": os.getenv("IMAGE_DEPLOYMENT_NAME"),
        "num_toys": int(os.getenv("NUM_TOYS", "10")),
        "owner_oids": [
            oid.strip()
            for oid in os.getenv("OWNER_OIDS", "").split(",")
            if oid.strip()
        ],
    }

    missing = [k for k, v in config.items() if not v and k != "owner_oids"]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")

    if not config["owner_oids"]:
        raise ValueError("OWNER_OIDS must contain at least one owner ID")

    return config


def create_openai_client(endpoint: str) -> AzureOpenAI:
    """
    Create authenticated AzureOpenAI client using DefaultAzureCredential.

    Args:
        endpoint: Azure OpenAI endpoint URL.

    Returns:
        Configured AzureOpenAI client instance.
    """
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )

    return AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2025-01-01-preview",
    )


def generate_toy_profile(
    client: AzureOpenAI, model: str, previous_toys: list[dict[str, str]]
) -> ToyProfile:
    """
    Generate toy profile using structured outputs.

    Args:
        client: OpenAI client instance.
        model: GPT model deployment name.
        previous_toys: List of previously generated toys to avoid duplicates.

    Returns:
        ToyProfile with name, description, and image generation prompt.
    """
    previous_context = ""
    if previous_toys:
        previous_context = "\n\nPreviously generated toys (create something different):\n"
        previous_context += "\n".join(
            f"- {toy['name']}: {toy['description']}" for toy in previous_toys[-5:]
        )

    prompt = f"""Generate a funny and cute toy profile for our toy travel service.

The toy should have:
- A SHORT name (1-3 words max, catchy and memorable)
- A cute/funny description (2-3 sentences, max 100 words, playful tone)
- A detailed image generation prompt that describes a dramatic, interesting photo of this toy

Make the toy unique, adorable, and full of personality. Think stuffed animals, action figures, 
quirky characters - anything that would make people smile!{previous_context}"""

    completion = client.beta.chat.completions.parse(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a creative toy designer creating whimsical, cute, and funny toy characters.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format=ToyProfile,
    )

    return completion.choices[0].message.parsed


def generate_and_process_image(
    client: AzureOpenAI, model: str, prompt: str, output_path: Path
) -> None:
    """
    Generate image using gpt-image-1, resize to 256x256, and save.
    
    Note: gpt-image-1 always returns base64-encoded images (no URL option).

    Args:
        client: AzureOpenAI client instance.
        model: Image generation model deployment name.
        prompt: Image generation prompt.
        output_path: Path to save the processed image.
    """
    response = client.images.generate(
        model=model,
        prompt=prompt,
        n=1,
        size="1024x1024",
    )

    # gpt-image-1 returns base64-encoded images
    image_base64 = response.data[0].b64_json
    image_data = base64.b64decode(image_base64)
    image = Image.open(BytesIO(image_data))

    resized = image.resize((256, 256), Image.Resampling.LANCZOS)
    resized.save(output_path, "JPEG", quality=85, optimize=True)


def main():
    """Generate toy profiles with AI-generated avatars."""
    print("🎲 Toy Profile Generator")
    print("=" * 50)

    try:
        config = load_config()
        print(f"\n✅ Configuration loaded:")
        print(f"   - Endpoint: {config['endpoint']}")
        print(f"   - GPT Model: {config['gpt_model']}")
        print(f"   - Image Model: {config['image_model']}")
        print(f"   - Toys to generate: {config['num_toys']}")
        print(f"   - Owner IDs: {len(config['owner_oids'])} available")

        client = create_openai_client(config["endpoint"])
        print("\n✅ OpenAI client authenticated")

        images_dir = Path(__file__).parent.parent / "toy-images"
        images_dir.mkdir(parents=True, exist_ok=True)

        output_file = Path(__file__).parent.parent / "toy_profiles.json"
        toy_profiles = []
        previous_toys = []

        print(f"\n🎨 Generating {config['num_toys']} toy profiles...")
        print("-" * 50)

        for i in range(config["num_toys"]):
            print(f"\n[{i+1}/{config['num_toys']}] Generating toy profile...")

            profile = generate_toy_profile(
                client, config["gpt_model"], previous_toys
            )
            print(f"   ✨ Name: {profile.name}")
            print(f"   📝 Description: {profile.description[:60]}...")

            image_id = str(uuid.uuid4())
            image_filename = f"{image_id}.jpg"
            image_path = images_dir / image_filename

            print(f"   🖼️  Generating image...")
            generate_and_process_image(
                client, config["image_model"], profile.image_prompt, image_path
            )
            print(f"   💾 Saved: {image_filename}")

            owner_oid = random.choice(config["owner_oids"])
            toy_data = {
                "owner_oid": owner_oid,
                "name": profile.name,
                "description": profile.description,
                "avatar_blob_name": image_filename,
            }
            toy_profiles.append(toy_data)
            previous_toys.append(
                {"name": profile.name, "description": profile.description}
            )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(toy_profiles, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 50)
        print(f"✅ Successfully generated {len(toy_profiles)} toy profiles!")
        print(f"📄 Data saved to: {output_file}")
        print(f"🖼️  Images saved to: {images_dir}")
        print("\nReady to import into your toy service!")

    except ValueError as e:
        print(f"\n❌ Configuration error: {e}")
        print("\nPlease check your .env file and ensure all required values are set.")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
