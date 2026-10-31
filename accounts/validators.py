from pathlib import Path

from django.core.exceptions import ValidationError

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_image(file):
    """Check the extension and size of an uploaded image.

    Pillow verifies that the content is a real image (Django's ImageField does this
    when the form is cleaned); this adds the format whitelist and the size cap.
    """
    extension = Path(file.name).suffix.lower().lstrip('.')
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError('Unsupported image type. Please upload a JPG, PNG, GIF or WebP file.')
    if file.size > MAX_IMAGE_BYTES:
        raise ValidationError('That image is too large. The maximum size is 5 MB.')
