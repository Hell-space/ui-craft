#!/usr/bin/env python3
"""Make comparable PNG proofs from screenshots, preserving scale and geometry."""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit('需要已有 Pillow 的 Python 环境；也可在图像查看器中按同等比例比较。')


def open_image(path: Path) -> Image.Image:
    with Image.open(path) as source:
        rgba = ImageOps.exif_transpose(source).convert("RGBA")
    paper = Image.new("RGB", rgba.size, "white")
    paper.paste(rgba, mask=rgba.getchannel("A"))
    return paper


def fit_width(image: Image.Image, scale: float) -> Image.Image:
    if scale == 1:
        return image
    size = tuple(max(1, round(value * scale)) for value in image.size)
    return image.resize(size, Image.Resampling.LANCZOS)


def main() -> int:
    parser = argparse.ArgumentParser(description="按原比例比较截图，或按输入顺序排列同机位的动作帧。需要 Pillow。")
    parser.add_argument("images", type=Path, nargs="+")
    parser.add_argument("--mode", choices=("side", "overlay", "gray", "strip"), default="side")
    parser.add_argument("--crop", type=int, nargs=4, metavar=("X", "Y", "W", "H"),
                        help="以原图像素为单位，先在每张图的同一位置裁取一个矩形。")
    parser.add_argument("--width", type=int, help="每幅图的最大宽度，不放大原图。")
    parser.add_argument("--out", type=Path, required=True, help="输出 PNG 校样。")
    args = parser.parse_intermixed_args()

    if args.width is not None and args.width <= 0:
        parser.error("--width 应为正整数。")
    paths = args.images
    required = {"gray": 1, "side": 2, "overlay": 2}
    if args.mode in required and len(paths) != required[args.mode]:
        parser.error(f"{args.mode} 需要 {required[args.mode]} 张图。")
    if args.mode == "strip" and len(paths) < 2:
        parser.error("strip 至少需要两张按时间排列的图。")
    if args.out.suffix.lower() != ".png":
        parser.error("--out 请使用 .png 扩展名。")
    if any(args.out.resolve() == path.resolve() or
           (args.out.exists() and path.exists() and args.out.samefile(path)) for path in paths):
        parser.error("请将校样写到原图以外的路径。")
    try:
        originals = [open_image(path) for path in paths]
        if args.mode in ("overlay", "strip") and any(im.size != originals[0].size for im in originals):
            parser.error("叠加与动作序列需要相同的原图尺寸。确认机位和裁切，或使用 side。")
        if args.crop:
            x, y, w, h = args.crop
            if x < 0 or y < 0 or w <= 0 or h <= 0 or any(x + w > im.width or y + h > im.height for im in originals):
                parser.error("--crop 需要在每张原图内指定正面积的矩形。")
            originals = [im.crop((x, y, x + w, y + h)) for im in originals]
        largest_width = max(image.width for image in originals)
        scale = min(1, (args.width or largest_width) / largest_width)
        frames = [fit_width(image, scale) for image in originals]
        if args.mode == "gray":
            result = ImageOps.grayscale(frames[0])
        elif args.mode == "overlay":
            result = Image.blend(frames[0], frames[1], 0.5)
        else:
            gutter = 8
            width = sum(frame.width for frame in frames) + gutter * (len(frames) - 1)
            result = Image.new("RGB", (width, max(frame.height for frame in frames)), "#dcdcdc")
            x = 0
            for frame in frames:
                result.paste(frame, (x, 0))
                x += frame.width + gutter
        args.out.parent.mkdir(parents=True, exist_ok=True)
        result.save(args.out, "PNG")
    except (OSError, Image.DecompressionBombError) as error:
        print(f"校样生成失败：{error}", file=sys.stderr)
        return 1
    print(f"{args.out} ({result.width} × {result.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
