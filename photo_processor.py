"""Image processing core for Photo Border Watermark Studio."""

from __future__ import annotations

import fractions
import glob
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from PIL.ExifTags import GPSTAGS, TAGS


SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png")


@dataclass
class RenderOptions:
    border_style: str = "blur"
    border_ratio: float = 0.10
    corner_radius: int = 34
    shadow_offset: int = 10
    shadow_blur: int = 22
    shadow_opacity: int = 110
    blur_radius: int = 40
    font_scale: float = 0.32
    text_spacing: int = 14
    caption_backdrop_opacity: int = 0
    text_shadow_opacity: int = 150
    jpg_quality: int = 95
    include_brand: bool = True
    include_model: bool = True
    include_params: bool = True
    include_lens: bool = False
    include_datetime: bool = False
    include_custom_title: bool = True
    include_custom_subtitle: bool = True
    custom_title: str = ""
    custom_subtitle: str = ""


@dataclass
class ProcessResult:
    total: int
    success: int
    outputs: List[Path]
    failures: List[str]


def get_exif_data(image_path: os.PathLike[str] | str) -> Optional[dict]:
    """Extract readable EXIF metadata from an image."""
    exif_data = {}
    try:
        with Image.open(image_path) as img:
            raw_exif = None
            if hasattr(img, "_getexif"):
                raw_exif = img._getexif()
            if not raw_exif:
                raw_exif = img.getexif()
            if not raw_exif:
                return None

            for tag_id, value in dict(raw_exif).items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value

            if "GPSInfo" in exif_data:
                gps_info = {}
                for key in exif_data["GPSInfo"]:
                    gps_info[GPSTAGS.get(key, key)] = exif_data["GPSInfo"][key]
                exif_data["GPSInfo"] = gps_info
    except Exception:
        return None
    return exif_data


def _clean_text(value: object, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback


def _rational_to_float(value: object) -> Optional[float]:
    try:
        if isinstance(value, tuple) and len(value) == 2 and value[1]:
            return float(value[0]) / float(value[1])
        return float(value)
    except Exception:
        return None


def _format_focal_length(value: object) -> str:
    number = _rational_to_float(value)
    if number is None:
        return "未知焦距"
    if abs(number - round(number)) < 0.05:
        return f"{int(round(number))}mm"
    return f"{number:.1f}mm"


def _format_f_number(value: object) -> str:
    number = _rational_to_float(value)
    if number is None:
        return "未知光圈"
    return f"F{number:.1f}"


def _format_exposure_time(value: object) -> str:
    if not value:
        return "未知快门"
    try:
        if isinstance(value, tuple) and len(value) == 2:
            frac = fractions.Fraction(value[0], value[1])
        else:
            frac = fractions.Fraction(value).limit_denominator(10000)
    except Exception:
        number = _rational_to_float(value)
        if number is None:
            return "未知快门"
        frac = fractions.Fraction(number).limit_denominator(10000)

    if frac.denominator == 1:
        return str(frac.numerator)
    return f"{frac.numerator}/{frac.denominator}"


def format_exif_params(exif_data: Optional[dict]) -> dict:
    """Format EXIF metadata into the text fields shown on the image."""
    if not exif_data:
        return {
            "brand": "未知品牌",
            "model": "未知型号",
            "lens": "未知镜头",
            "params": "参数未知",
            "datetime": "拍摄时间未知",
        }

    brand = _clean_text(exif_data.get("Make"), "未知品牌")
    model = _clean_text(exif_data.get("Model"), "未知型号")
    lens = _clean_text(
        exif_data.get("LensModel", exif_data.get("Lens")),
        "未知镜头",
    )
    focal_length = _format_focal_length(exif_data.get("FocalLength"))
    f_number = _format_f_number(exif_data.get("FNumber"))
    exposure_time = _format_exposure_time(exif_data.get("ExposureTime"))
    iso = _clean_text(exif_data.get("ISOSpeedRatings"), "未知ISO")
    if not iso.upper().startswith("ISO"):
        iso = f"ISO{iso}"

    shoot_time = _clean_text(
        exif_data.get("DateTimeOriginal") or exif_data.get("DateTimeDigitized"),
        "拍摄时间未知",
    )
    if shoot_time != "拍摄时间未知":
        shoot_time = shoot_time.replace(":", ".", 2)

    return {
        "brand": brand,
        "model": model,
        "lens": lens,
        "params": f"{focal_length}  {f_number}  {exposure_time}  {iso}",
        "datetime": shoot_time,
    }


def find_font_path() -> Optional[Path]:
    windows_dir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    candidates = [
        windows_dir / "Fonts" / "msyh.ttc",
        windows_dir / "Fonts" / "msyhbd.ttc",
        windows_dir / "Fonts" / "simhei.ttf",
        windows_dir / "Fonts" / "arial.ttf",
        Path("/System/Library/Fonts/PingFang.ttc"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_font(size: int) -> ImageFont.ImageFont:
    font_path = find_font_path()
    if font_path:
        return ImageFont.truetype(str(font_path), size)
    return ImageFont.load_default()


def _rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def _text_lines(params: dict, options: RenderOptions) -> str:
    first_line_parts = []
    if options.include_custom_title and options.custom_title.strip():
        first_line_parts.append(options.custom_title.strip())
    if options.include_custom_subtitle and options.custom_subtitle.strip():
        first_line_parts.append(options.custom_subtitle.strip())

    identity_parts = []
    if options.include_brand and params["brand"] != "未知品牌":
        identity_parts.append(params["brand"])
    if options.include_model and params["model"] != "未知型号":
        identity_parts.append(params["model"])
    if identity_parts:
        first_line_parts.append(" ".join(identity_parts))

    second_line_parts = []
    if options.include_params and params["params"] != "参数未知":
        second_line_parts.append(params["params"])
    if options.include_lens and params["lens"] != "未知镜头":
        second_line_parts.append(params["lens"])
    if options.include_datetime and params["datetime"] != "拍摄时间未知":
        second_line_parts.append(params["datetime"])

    lines = []
    first_line = "  |  ".join(first_line_parts).strip()
    second_line = "  |  ".join(second_line_parts).strip()
    if first_line:
        lines.append(first_line)
    if second_line:
        lines.append(second_line)
    if not lines:
        lines.append(" ")
    return "\n".join(lines[:2])


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    start_size: int,
    max_width: int,
    max_height: int,
    spacing: int,
) -> ImageFont.ImageFont:
    for size in range(max(10, start_size), 9, -1):
        font = _load_font(size)
        bbox = draw.multiline_textbbox((0, 0), text, font=font, spacing=spacing, align="center")
        if bbox[2] - bbox[0] <= max_width and bbox[3] - bbox[1] <= max_height:
            return font
    return _load_font(10)


def _draw_centered_text(
    image: Image.Image,
    text: str,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int],
    start_size: int,
    spacing: int,
    shadow_opacity: int,
) -> None:
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = box
    max_width = max(1, right - left - 32)
    max_height = max(1, bottom - top - 18)
    font = _fit_font(draw, text, start_size, max_width, max_height, spacing)
    center = ((left + right) // 2, (top + bottom) // 2)

    base = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    if shadow_opacity > 0:
        overlay_draw.multiline_text(
            (center[0] + 2, center[1] + 2),
            text,
            font=font,
            fill=(0, 0, 0, shadow_opacity),
            anchor="mm",
            align="center",
            spacing=spacing,
        )
    overlay_draw.multiline_text(
        center,
        text,
        font=font,
        fill=(*fill, 255),
        anchor="mm",
        align="center",
        spacing=spacing,
    )
    composed = Image.alpha_composite(base, overlay)
    if image.mode == "RGBA":
        image.paste(composed)
    else:
        image.paste(composed.convert(image.mode))


def _normalized_options(options: RenderOptions) -> RenderOptions:
    options.border_style = "white" if options.border_style == "white" else "blur"
    options.border_ratio = min(0.30, max(0.03, options.border_ratio))
    options.corner_radius = max(0, options.corner_radius)
    options.shadow_offset = max(0, options.shadow_offset)
    options.shadow_blur = max(0, options.shadow_blur)
    options.shadow_opacity = min(255, max(0, options.shadow_opacity))
    options.blur_radius = max(0, options.blur_radius)
    options.font_scale = min(0.80, max(0.12, options.font_scale))
    options.text_spacing = max(0, options.text_spacing)
    options.caption_backdrop_opacity = min(180, max(0, options.caption_backdrop_opacity))
    options.text_shadow_opacity = min(255, max(0, options.text_shadow_opacity))
    options.jpg_quality = min(100, max(1, options.jpg_quality))
    return options


def build_framed_image(
    source_image: Image.Image,
    params: dict,
    options: RenderOptions,
) -> Image.Image:
    """Create the framed/watermarked image without saving it."""
    options = _normalized_options(options)
    img = source_image.convert("RGB")
    width, height = img.size
    border_width = max(28, int(min(width, height) * options.border_ratio))
    font_size = max(18, int(border_width * options.font_scale))
    bottom_text = _text_lines(params, options)

    if options.border_style == "white":
        new_width = width
        new_height = height + border_width
        new_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))
        new_img.paste(img, (0, 0))
        _draw_centered_text(
            new_img,
            bottom_text,
            (0, height, new_width, new_height),
            fill=(28, 28, 28),
            start_size=font_size,
            spacing=options.text_spacing,
            shadow_opacity=0,
        )
        return new_img

    new_width = width + border_width * 2
    new_height = height + border_width * 2
    blur_radius = options.blur_radius or max(20, border_width // 3)
    background = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    background = background.filter(ImageFilter.GaussianBlur(radius=blur_radius)).convert("RGBA")

    if options.caption_backdrop_opacity:
        shade = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
        shade_draw = ImageDraw.Draw(shade)
        shade_draw.rectangle(
            (0, new_height - border_width - 8, new_width, new_height),
            fill=(0, 0, 0, options.caption_backdrop_opacity),
        )
        background = Image.alpha_composite(background, shade)

    radius = min(options.corner_radius, min(width, height) // 2)
    image_pos = (border_width, border_width)
    if options.shadow_offset or options.shadow_blur:
        shadow = Image.new("RGBA", background.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_box = (
            image_pos[0] + options.shadow_offset,
            image_pos[1] + options.shadow_offset,
            image_pos[0] + options.shadow_offset + width,
            image_pos[1] + options.shadow_offset + height,
        )
        shadow_draw.rounded_rectangle(
            shadow_box,
            radius=radius,
            fill=(0, 0, 0, options.shadow_opacity),
        )
        if options.shadow_blur:
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=options.shadow_blur))
        background = Image.alpha_composite(background, shadow)

    if radius:
        mask = _rounded_mask((width, height), radius)
        foreground = img.convert("RGBA")
        foreground.putalpha(mask)
        background.paste(foreground, image_pos, foreground)
        outline = ImageDraw.Draw(background)
        outline.rounded_rectangle(
            (
                image_pos[0],
                image_pos[1],
                image_pos[0] + width,
                image_pos[1] + height,
            ),
            radius=radius,
            outline=(255, 255, 255, 72),
            width=max(1, border_width // 90),
        )
    else:
        background.paste(img, image_pos)

    new_img = background.convert("RGB")
    _draw_centered_text(
        new_img,
        bottom_text,
        (0, border_width + height, new_width, new_height),
        fill=(255, 255, 255),
        start_size=font_size,
        spacing=options.text_spacing,
        shadow_opacity=options.text_shadow_opacity,
    )
    return new_img


def render_image(
    image_path: os.PathLike[str] | str,
    output_path: os.PathLike[str] | str,
    options: RenderOptions,
) -> Path:
    """Render one image and save it to output_path."""
    image_path = Path(image_path)
    output_path = Path(output_path)
    params = format_exif_params(get_exif_data(image_path))
    with Image.open(image_path) as img:
        img = ImageOps.exif_transpose(img)
        framed = build_framed_image(img, params, options)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    extension = output_path.suffix.lower()
    if extension in (".jpg", ".jpeg"):
        framed.save(output_path, quality=options.jpg_quality, subsampling=0)
    elif extension == ".png":
        framed.save(output_path, compress_level=1)
    else:
        framed.save(output_path)
    return output_path


def render_preview(
    image_path: os.PathLike[str] | str,
    options: RenderOptions,
    max_source_side: int = 1280,
) -> Image.Image:
    """Render a smaller preview image for the desktop studio."""
    image_path = Path(image_path)
    params = format_exif_params(get_exif_data(image_path))
    with Image.open(image_path) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((max_source_side, max_source_side), Image.Resampling.LANCZOS)
        return build_framed_image(img.copy(), params, options)


def collect_images(patterns: Iterable[str]) -> List[Path]:
    images: List[Path] = []
    seen = set()
    for pattern in patterns:
        matches = glob.glob(pattern)
        candidates = matches if matches else [pattern]
        for candidate in candidates:
            path = Path(candidate)
            if path.is_dir():
                child_paths = sorted(path.iterdir())
            else:
                child_paths = [path]
            for child in child_paths:
                if child.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    continue
                try:
                    key = child.resolve()
                except OSError:
                    key = child
                if key in seen:
                    continue
                seen.add(key)
                images.append(child)
    return images


def output_path_for(input_path: os.PathLike[str] | str, output_dir: os.PathLike[str] | str, style: str) -> Path:
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    return output_dir / f"{input_path.stem}_{style}{input_path.suffix}"


def process_images(
    input_patterns: Iterable[str],
    output_dir: os.PathLike[str] | str,
    options: RenderOptions,
    logger: Optional[Callable[[str], None]] = None,
    progress: Optional[Callable[[int, int, Path], None]] = None,
) -> ProcessResult:
    log = logger or (lambda message: None)
    image_files = collect_images(input_patterns)
    if not image_files:
        log("错误: 没有找到要处理的图片文件")
        return ProcessResult(total=0, success=0, outputs=[], failures=[])

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    log(f"找到 {len(image_files)} 个图片文件，输出目录: {output_dir}")

    outputs: List[Path] = []
    failures: List[str] = []
    for index, image_path in enumerate(image_files, 1):
        try:
            if progress:
                progress(index, len(image_files), image_path)
            log(f"[{index}/{len(image_files)}] 处理中: {image_path.name}")
            output_path = output_path_for(image_path, output_dir, options.border_style)
            render_image(image_path, output_path, options)
            outputs.append(output_path)
            log(f"    已保存: {output_path}")
        except Exception as exc:
            message = f"{image_path}: {exc}"
            failures.append(message)
            log(f"    处理失败: {message}")

    log(f"处理完成: 成功 {len(outputs)}/{len(image_files)}")
    return ProcessResult(
        total=len(image_files),
        success=len(outputs),
        outputs=outputs,
        failures=failures,
    )
