from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class CropBox:
    x: int
    y: int
    width: int
    height: int


def fix_orientation(image: Image.Image) -> Image.Image:
    try:
        exif = image.getexif()
        orientation = exif.get(0x0112)  # EXIF Orientation tag
        rotations = {3: 180, 6: 270, 8: 90}
        if orientation in rotations:
            image = image.rotate(rotations[orientation], expand=True)
    except Exception:
        pass
    return image


def crop_image(source_path: Path, output_dir: Path, job_id: str, crop_box: CropBox | None) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as image:
        image = fix_orientation(image).convert("RGB")

        if crop_box is None:
            output_path = output_dir / f"{job_id}-oriented.png"
            image.save(output_path, format="PNG")
            return output_path

        output_path = output_dir / f"{job_id}-crop.png"
        left = min(max(crop_box.x, 0), image.width - 1)
        top = min(max(crop_box.y, 0), image.height - 1)
        right = min(left + crop_box.width, image.width)
        bottom = min(top + crop_box.height, image.height)

        if right <= left or bottom <= top:
            raise ValueError("Invalid crop area.")

        image.crop((left, top, right, bottom)).save(output_path, format="PNG")

    return output_path
