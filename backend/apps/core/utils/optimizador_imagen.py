from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile


def optimize_image(image_file, quality=80, max_width=1200):
    img = Image.open(image_file)

    # Convertir a RGB si viene en RGBA o P
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Redimensionar si es muy grande
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    buffer = BytesIO()

    # Guardar como WEBP optimizado
    img.save(buffer, format="WEBP", quality=quality, optimize=True)

    return ContentFile(buffer.getvalue())