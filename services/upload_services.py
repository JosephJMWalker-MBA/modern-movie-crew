import os
from django.core.exceptions import ValidationError

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

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB limit for dev slice


def validate_uploaded_file(file_obj, max_size_bytes=MAX_FILE_SIZE_BYTES, allowed_exts=ALLOWED_EXTENSIONS):
    if not file_obj:
        return

    if file_obj.size > max_size_bytes:
        raise ValidationError(
            f"File size ({file_obj.size / (1024 * 1024):.1f} MB) exceeds maximum allowed size of {max_size_bytes / (1024 * 1024):.0f} MB."
        )

    _, ext = os.path.splitext(file_obj.name)
    if ext.lower() not in allowed_exts:
        raise ValidationError(
            f"File extension '{ext}' is not permitted. Allowed extensions: {', '.join(sorted(allowed_exts))}"
        )
