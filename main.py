"""Launcher for Photo Border Watermark Studio."""

from __future__ import annotations

import argparse
import sys

from photo_processor import RenderOptions, process_images


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="给照片添加边框并写入 EXIF 参数水印。无图片参数时打开桌面控制台。"
    )
    parser.add_argument("inputs", nargs="*", help="图片路径、文件夹或通配符，例如 *.jpg")
    parser.add_argument("--studio", action="store_true", help="强制打开桌面控制台")
    parser.add_argument(
        "--style",
        choices=["blur", "white"],
        default="blur",
        help="边框样式：blur 虚化边框，white 白色底框",
    )
    parser.add_argument("--output", default="output", help="输出目录")
    parser.add_argument("--border", type=float, default=10.0, help="边框比例，单位百分比")
    parser.add_argument("--corner", type=int, default=34, help="圆角大小，仅 blur 模式有效")
    parser.add_argument("--shadow", type=int, default=10, help="阴影偏移，仅 blur 模式有效")
    parser.add_argument("--shadow-blur", type=int, default=22, help="阴影模糊半径")
    parser.add_argument("--shadow-opacity", type=int, default=110, help="阴影不透明度 0-255")
    parser.add_argument("--blur-radius", type=int, default=40, help="背景虚化强度")
    parser.add_argument("--font-scale", type=float, default=32.0, help="文字大小比例，单位百分比")
    parser.add_argument("--text-spacing", type=int, default=14, help="水印文字行距")
    parser.add_argument(
        "--caption-backdrop",
        type=int,
        default=0,
        help="水印底部底纹透明度 0-160，默认 0 表示关闭",
    )
    parser.add_argument("--text-shadow", type=int, default=150, help="文字阴影透明度 0-240")
    parser.add_argument("--quality", type=int, default=95, help="JPG 输出质量 1-100")
    parser.add_argument("--hide-brand", action="store_true", help="不显示相机品牌")
    parser.add_argument("--hide-model", action="store_true", help="不显示相机型号")
    parser.add_argument("--hide-params", action="store_true", help="不显示拍摄参数")
    parser.add_argument("--include-lens", action="store_true", help="在水印中显示镜头")
    parser.add_argument("--include-datetime", action="store_true", help="在水印中显示拍摄时间")
    parser.add_argument("--hide-title", action="store_true", help="不显示自定义标题")
    parser.add_argument("--hide-subtitle", action="store_true", help="不显示自定义副标题")
    parser.add_argument("--title", default="", help="自定义第一行文字")
    parser.add_argument("--subtitle", default="", help="自定义第二行文字")
    return parser


def options_from_args(args: argparse.Namespace) -> RenderOptions:
    return RenderOptions(
        border_style=args.style,
        border_ratio=max(1.0, args.border) / 100.0,
        corner_radius=args.corner,
        shadow_offset=args.shadow,
        shadow_blur=args.shadow_blur,
        shadow_opacity=args.shadow_opacity,
        blur_radius=args.blur_radius,
        font_scale=max(1.0, args.font_scale) / 100.0,
        text_spacing=args.text_spacing,
        caption_backdrop_opacity=args.caption_backdrop,
        text_shadow_opacity=args.text_shadow,
        jpg_quality=args.quality,
        include_brand=not args.hide_brand,
        include_model=not args.hide_model,
        include_params=not args.hide_params,
        include_lens=args.include_lens,
        include_datetime=args.include_datetime,
        include_custom_title=not args.hide_title,
        include_custom_subtitle=not args.hide_subtitle,
        custom_title=args.title,
        custom_subtitle=args.subtitle,
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.studio or not args.inputs:
        from studio_app import run_studio

        run_studio()
        return 0

    options = options_from_args(args)
    result = process_images(args.inputs, args.output, options, logger=print)
    if result.total == 0:
        return 2
    return 0 if result.success == result.total else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
