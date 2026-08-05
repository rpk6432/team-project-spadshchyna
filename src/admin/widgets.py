from pathlib import Path
from string import Template
from typing import Any

from markupsafe import Markup, escape

_TEMPLATES = Path(__file__).parent / "templates"
_DUAL_LISTBOX = Template((_TEMPLATES / "dual_listbox.html").read_text(encoding="utf-8"))
_IMAGE_UPLOAD = Template((_TEMPLATES / "image_upload.html").read_text(encoding="utf-8"))
_MULTI_IMAGE_UPLOAD = Template(
    (_TEMPLATES / "multi_image_upload.html").read_text(encoding="utf-8")
)


class DualListboxWidget:
    """Widget for selecting multiple items via two-pane picker."""

    def __call__(self, field: Any, **kwargs: Any) -> Markup:
        selected_values = set(field.data or [])
        available = []
        selected = []
        for val, label, *_ in field.iter_choices():
            if val in selected_values:
                selected.append((val, label))
            else:
                available.append((val, label))

        fid = kwargs.get("id", field.id)
        name = field.name
        avail_opts = "".join(
            f'<option value="{escape(v)}">{escape(label)}</option>'
            for v, label in available
        )
        sel_opts = "".join(
            f'<option value="{escape(v)}">{escape(label)}</option>'
            for v, label in selected
        )

        return Markup(
            _DUAL_LISTBOX.substitute(
                fid=fid,
                name=name,
                avail_opts=avail_opts,
                sel_opts=sel_opts,
            )
        )


class ImageUploadWidget:
    """File input with client-side image preview."""

    def __call__(self, field: Any, **kwargs: Any) -> Markup:
        fid = kwargs.get("id", field.id)
        name = field.name
        return Markup(_IMAGE_UPLOAD.substitute(fid=fid, name=name))


class MultiImageUploadWidget:
    """Multi-file input with thumbnails, accumulative add, and remove."""

    def __call__(self, field: Any, **kwargs: Any) -> Markup:
        fid = kwargs.get("id", field.id)
        name = field.name
        return Markup(_MULTI_IMAGE_UPLOAD.substitute(fid=fid, name=name))
