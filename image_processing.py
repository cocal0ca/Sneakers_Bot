import requests
from PIL import Image
from io import BytesIO


def process_image(url: str, target_size: tuple = None) -> BytesIO:
    """
    Downloads an image, crops it to a square (keeping the bottom part),
    and returns bytes.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        img = Image.open(BytesIO(response.content))

        width, height = img.size
        min_dim = min(width, height)

        # Determine crop box for 1:1 aspect ratio
        if width > height:
            # Wide image: crop center horizontally
            left = (width - height) // 2
            upper = 0
            right = left + height
            lower = height
        else:
            # Tall image: crop top, keep bottom
            # User reported "too much whitespace at top", so we align to bottom.
            # Crop box: (left, upper, right, lower)
            left = 0
            # To keep bottom: start 'upper' at (height - width)
            # However, sometimes bottom has logos or is too close.
            # Let's align mostly to bottom but leave a tiny margin if possible?
            # Or just strict bottom. STRICT BOTTOM seems safest based on user feedback.
            upper = height - width
            right = width
            lower = height

        crop_box = (left, upper, right, lower)
        img = img.crop(crop_box)

        # Optional: Resize to standard size (e.g. 1080x1080) for consistency
        # if target_size:
        #     img = img.resize(target_size, Image.Resampling.LANCZOS)

        # Convert to RGB to handle PNG/RGBA correctly if needed (though usually JPG)
        if img.mode != "RGB":
            img = img.convert("RGB")

        bio = BytesIO()
        img.save(bio, format="JPEG", quality=95)
        bio.seek(0)

        return bio

    except Exception as e:
        print(f"[ImageProc] Error processing {url}: {e}")
        return None
