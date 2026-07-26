import mimetypes
import os
import secrets
from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename
from PIL import Image

# Max image size limit for decompression-bomb protection (10 MP max)
Image.MAX_IMAGE_PIXELS = 10_000_000

ALLOWED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".webm",
    ".wav",
    ".mp3",
    ".png",
    ".jpg",
    ".jpeg",
}

ALLOWED_MIME_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
    "audio/wav",
    "audio/x-wav",
    "audio/mpeg",
    "audio/mp3",
    "image/png",
    "image/jpeg",
    "image/pjpeg",
}

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB limit


def generate_collision_safe_filename(file_obj) -> str:
    """Sanitizes raw filename and prepends a cryptographically secure random prefix to prevent collisions and path traversal."""
    if not file_obj or not hasattr(file_obj, "name"):
        return f"upload_{secrets.token_hex(16)}"

    raw_name = os.path.basename(file_obj.name)
    sanitized = get_valid_filename(raw_name)
    prefix = secrets.token_hex(12)
    return f"{prefix}_{sanitized}"


def validate_uploaded_file(file_obj, max_size_bytes=MAX_FILE_SIZE_BYTES, allowed_exts=ALLOWED_EXTENSIONS):
    if not file_obj:
        return

    # 1. Size Validation
    if file_obj.size > max_size_bytes:
        raise ValidationError(
            f"File size ({file_obj.size / (1024 * 1024):.1f} MB) exceeds maximum allowed size of {max_size_bytes / (1024 * 1024):.0f} MB."
        )

    # 2. Extension Validation
    raw_name = getattr(file_obj, "name", "")
    _, ext = os.path.splitext(raw_name)
    ext_lower = ext.lower()
    if ext_lower not in allowed_exts:
        raise ValidationError(
            f"File extension '{ext}' is not permitted. Allowed extensions: {', '.join(sorted(allowed_exts))}"
        )

    # 3. MIME Type & Header Inspection
    content_type = getattr(file_obj, "content_type", None)
    if content_type and content_type.lower() not in ALLOWED_MIME_TYPES:
        guessed_type, _ = mimetypes.guess_type(raw_name)
        if not guessed_type or guessed_type.lower() not in ALLOWED_MIME_TYPES:
            raise ValidationError(
                f"File MIME type '{content_type}' is not permitted for upload."
            )

    # 4. Image Validation & Decompression Bomb Protection
    if ext_lower in {".png", ".jpg", ".jpeg"}:
        try:
            # Read header to verify valid image format without loading entire payload
            image = Image.open(file_obj)
            image.verify()
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
        except Exception as e:
            raise ValidationError(f"Invalid or corrupted image file: {str(e)}")
