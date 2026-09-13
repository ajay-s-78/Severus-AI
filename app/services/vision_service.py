import base64
import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger("severus.vision_service")


class VisionService:
    """
    Validation and processing service for image files and vision inputs.
    Supports PNG, JPG/JPEG, and WEBP formats up to 10 MB.
    """

    ALLOWED_MIME_TYPES = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/webp": ".webp",
    }

    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
    MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

    def validate_image_bytes(self, image_bytes: bytes, filename: str = "") -> Optional[str]:
        """
        Validates raw image bytes and optional filename.
        Returns error message string if invalid, or None if valid.
        """
        if not image_bytes or len(image_bytes) == 0:
            return "Uploaded image file is empty."

        if len(image_bytes) > self.MAX_FILE_SIZE_BYTES:
            size_mb = len(image_bytes) / (1024 * 1024)
            return f"Image size ({size_mb:.2f} MB) exceeds maximum allowed limit of 10 MB."

        if filename:
            ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
            if ext not in self.ALLOWED_EXTENSIONS:
                return f"Unsupported image file extension '{ext}'. Allowed formats: PNG, JPG, JPEG, WEBP."

        return None

    def parse_data_uri(self, data_uri: str) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        """
        Parses a base64 data URI string (e.g. 'data:image/png;base64,...').
        Returns (image_bytes, mime_type, error_message).
        """
        if not data_uri or not isinstance(data_uri, str):
            return None, None, "Invalid image data format."

        data_uri = data_uri.strip()

        if data_uri.startswith("data:"):
            try:
                header, encoded = data_uri.split(",", 1)
                mime_part = header.split(";")[0].replace("data:", "").strip().lower()

                if mime_part not in self.ALLOWED_MIME_TYPES:
                    return None, None, f"Unsupported MIME type '{mime_part}'. Allowed formats: PNG, JPG, JPEG, WEBP."

                image_bytes = base64.b64decode(encoded)
                err = self.validate_image_bytes(image_bytes)
                if err:
                    return None, None, err

                return image_bytes, mime_part, None
            except Exception as e:
                return None, None, f"Failed to parse base64 image data URI: {str(e)}"
        else:
            # Assume raw base64 string
            try:
                image_bytes = base64.b64decode(data_uri)
                err = self.validate_image_bytes(image_bytes)
                if err:
                    return None, None, err
                return image_bytes, "image/jpeg", None
            except Exception as e:
                return None, None, f"Invalid base64 image encoding: {str(e)}"


vision_service = VisionService()
