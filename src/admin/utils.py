import io
import mimetypes

from markupsafe import Markup
from PIL import Image

from s3.client import get_public_url

HOST_AVATAR_SIZE = (200, 200)


def resize_image(data: bytes, width: int, height: int) -> bytes:
    """Resize image to fit within width x height, keeping aspect ratio."""
    img = Image.open(io.BytesIO(data))
    img.thumbnail((width, height))
    buf = io.BytesIO()
    fmt = img.format or "PNG"
    img.save(buf, format=fmt)
    return buf.getvalue()


def guess_content_type(filename: str | None) -> str:
    """Guess MIME type from filename, defaulting to image/jpeg."""
    if filename:
        mime, _ = mimetypes.guess_type(filename)
        if mime:
            return mime
    return "image/jpeg"


def format_s3_thumbnail(key: str | None, link_url: str | None = None) -> str | Markup:
    """Render an S3 key as a clickable thumbnail image."""
    if not key:
        return ""
    src = get_public_url(key)
    href = link_url or src
    target = "" if link_url else ' target="_blank"'
    return Markup(
        f'<a href="{href}"{target}>'
        f'<img src="{src}" style="max-width:100px;max-height:100px;'
        f'border-radius:4px;object-fit:cover">'
        f"</a>"
    )
