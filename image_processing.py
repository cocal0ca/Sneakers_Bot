import requests
from PIL import Image
from io import BytesIO


def process_image(
    url: str, target_size: tuple = (1080, 1080), image_data: bytes = None
) -> BytesIO:
    """
    Downloads an image (or uses provided bytes), crops it to a square (keeping the bottom part),
    resizes it to target_size (default 1080x1080), and returns bytes.
    """
    try:
        if image_data:
            img = Image.open(BytesIO(image_data))
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Referer": "https://street-beat.ru/",
                "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                "Sec-Ch-Ua-Mobile": "?0",
                "Sec-Ch-Ua-Platform": '"Windows"',
                "Sec-Fetch-Dest": "image",
                "Sec-Fetch-Mode": "no-cors",
                "Sec-Fetch-Site": "same-origin",
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content))

        width, height = img.size
        # min_dim = min(width, height) # Unused

        # Determine crop box for 1:1 aspect ratio
        width, height = img.size

        # Calculate aspect ratio and new size to fit in target_size while maintaining aspect ratio
        target_w, target_h = target_size
        ratio = min(target_w / width, target_h / height)
        new_w = int(width * ratio)
        new_h = int(height * ratio)

        # Resize the image
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Create a new white image of target size
        new_img = Image.new("RGB", target_size, (255, 255, 255))

        # Paste the resized image into the center
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        new_img.paste(img, (paste_x, paste_y))

        img = new_img

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
