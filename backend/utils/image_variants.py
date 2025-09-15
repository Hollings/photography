import tempfile
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps


class VariantBuilder:
    TMP_ROOT       = Path(tempfile.gettempdir()) / "photo_variants"
    VARIANT_SPECS  = {"thumbnail": 400, "small": 1600}

    def ensure_variant(self, base: Path, variant: str) -> Path:
        target_px = self.VARIANT_SPECS[variant]
        out_path  = (self.TMP_ROOT / variant) / base.name
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists() and out_path.stat().st_mtime >= base.stat().st_mtime:
            return out_path

        with Image.open(base) as img:
            img = ImageOps.exif_transpose(img)
            img.thumbnail((target_px, target_px), resample=Image.LANCZOS)
            save_kwargs: dict[str, Any] = {}
            if img.format == "JPEG":
                save_kwargs.update({"quality": 85, "optimize": True})
            exif_bytes = img.info.get("exif")
            if exif_bytes:
                img.save(out_path, exif=exif_bytes, **save_kwargs)
            else:
                img.save(out_path, **save_kwargs)
        return out_path
