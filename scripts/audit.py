#!/usr/bin/env python3
"""界面代码的静态设计体检。

用法:
  python audit.py <文件或目录> [更多路径...] [--json] [--strict]
  python audit.py <页面.html 或目录> --gate      # 门槛模式：检查明确的技术问题和同页模板残留

检查五类问题：
  系统   字号 / 颜色 / 圆角 / 间距是否成体系，还是到处是"差一点"的裸值
  指纹   常见的模板感 / "AI 味"做法
  无障碍 焦点环、alt、label、视口、过小的字
  动效   transition: all、缺少 reduced-motion、过长时长、对布局属性做动画
  中文   含中文内容时的行高、字距、斜体、字体栈

结果分三级：[问题] 基本都该改；[留意] 多半值得改，除非是有意为之；[信息] 供判断。
这是线索而不是判决——是否要改，由设计立场决定。
"""
from __future__ import annotations

import argparse
import colorsys
import json
import mmap
import os
import re
import sys
from collections import Counter
from functools import lru_cache
from html import unescape
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

EXTS_MARKUP = {".html", ".htm", ".vue", ".svelte", ".astro"}
EXTS_STYLE = {".css", ".scss", ".sass", ".less"}
EXTS_SCRIPT = {".jsx", ".tsx", ".js", ".ts", ".mjs"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", ".next", ".nuxt", ".svelte-kit",
             "vendor", "coverage", "__pycache__", ".venv", "venv", "bin", "obj"}
MAX_BYTES = 1_500_000
EMBEDDED_MEDIA = re.compile(rb"data:(?:image|audio|video)/[\w.+-]+;base64,[a-zA-Z0-9+/=\r\n]+", re.I)

ISSUE, WARN, INFO = "问题", "留意", "信息"
ORDER = {ISSUE: 0, WARN: 1, INFO: 2}
CATS = ["门槛", "系统", "指纹", "无障碍", "动效", "性能", "中文"]

GENERIC_FONTS = {
    "inter", "roboto", "arial", "helvetica", "helvetica neue", "open sans", "lato", "poppins",
    "montserrat", "system-ui", "-apple-system", "blinkmacsystemfont", "segoe ui", "sans-serif",
    "serif", "monospace", "ui-sans-serif", "ui-serif", "ui-monospace", "inherit", "segoe ui variable",
    "segoe ui variable text", "noto sans", "apple color emoji", "segoe ui emoji",
}
CJK_FONT_HINTS = ("pingfang", "yahei", "noto sans sc", "noto serif sc", "noto sans cjk", "source han",
                  "hiragino", "simsun", "songti", "stsong", "heiti", "simhei", "harmonyos", "misans",
                  "wenkai", "思源", "苹方", "微软雅黑", "宋体", "黑体", "noto sans tc", "noto sans jp")
PLACEHOLDER_PATTERNS = [
    (r"lorem ipsum", "Lorem ipsum"),
    (r"\bjohn doe\b|\bjane doe\b", "John/Jane Doe"),
    (r"\bacme\b", "Acme"),
    (r"张三|李四|王五", "张三/李四/王五"),
    (r"测试(?:数据|文本|标题|内容|用户)\d*|示例文本|占位(?:文本|内容)", "测试/占位文案"),
    (r"example\.com/(?:image|photo|img)|via\.placeholder\.com|placehold\.co|picsum\.photos", "占位图服务"),
]


# ---------------------------------------------------------------- 读取

def collect(paths: list[str], skipped: list[str] | None = None) -> list[str]:
    files: list[str] = []
    exts = EXTS_MARKUP | EXTS_STYLE | EXTS_SCRIPT
    for p in paths:
        if os.path.isfile(p) and os.path.splitext(p)[1].lower() in exts:
            files.append(p)
        elif os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
                for n in names:
                    if os.path.splitext(n)[1].lower() in exts and not n.endswith(".min.js") \
                            and not n.endswith(".min.css"):
                        files.append(os.path.join(root, n))
        elif skipped is not None:
            skipped.append(p)
    return files


LIB_MARK = "/* ui-craft.css"


def load(files: list[str], skipped: list[str] | None = None,
         pages: dict[str, str] | None = None) -> tuple[str, str, str]:
    """返回 (页面自己的样式, ui-craft 库样式, 标记文本)。
    scaffold.py 生成的 ui-craft.css / ui-craft.js 是校验过的库：不计入"系统""指纹"检查，
    保留在独立的样式上下文中供焦点与减弱动效检查使用。"""
    css_parts: list[str] = []
    lib_parts: list[str] = []
    markup_parts: list[str] = []
    seen_styles: set[str] = set()

    def read(path: str) -> str | None:
        try:
            if os.path.getsize(path) > MAX_BYTES:
                if os.path.splitext(path)[1].lower() in EXTS_MARKUP:
                    # Large single-file showcases usually consist mostly of photography.
                    # Keep the surrounding tags, alt text, CSS and JS available to the audit.
                    with open(path, "rb") as fh, mmap.mmap(fh.fileno(), 0, access=mmap.ACCESS_READ) as data:
                        compact = bytearray()
                        start = 0
                        for match in EMBEDDED_MEDIA.finditer(data):
                            if len(compact) + match.start() - start > MAX_BYTES:
                                break
                            compact.extend(data[start:match.start()])
                            compact.extend(b"embedded-media")
                            start = match.end()
                        if len(compact) + len(data) - start <= MAX_BYTES:
                            compact.extend(data[start:])
                            return compact.decode("utf-8", errors="replace")
                if skipped is not None:
                    skipped.append(path)
                return None
            with open(path, encoding="utf-8", errors="replace") as fh:
                return fh.read()
        except OSError:
            if skipped is not None:
                skipped.append(path)
            return None

    def add_stylesheet(path: str) -> None:
        path = os.path.realpath(path)
        if path in seen_styles:
            return
        seen_styles.add(path)
        content = read(path)
        if content is not None:
            is_kit = os.path.basename(path).lower() == "ui-craft.css" or content.lstrip().startswith(LIB_MARK)
            (lib_parts if is_kit else css_parts).append(content)

    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in EXTS_STYLE:
            add_stylesheet(f)
            continue
        if os.path.basename(f).lower() == "ui-craft.js":
            continue
        text = read(f)
        if text is None:
            continue
        if ext in EXTS_MARKUP:
            for tag in re.findall(r"<link\b[^>]*>", text, re.I):
                attrs = {key.lower(): unescape(value) for key, _, value in
                         re.findall(r"""([\w:-]+)\s*=\s*(["'])(.*?)\2""", tag, re.S)}
                if "stylesheet" not in attrs.get("rel", "").lower().split() or "href" not in attrs or "{" in attrs["href"]:
                    continue
                try:
                    reference = urlsplit(attrs["href"])
                except ValueError:
                    continue
                name = unquote(reference.path)
                if reference.scheme or reference.netloc or name.startswith(("/", "\\")) or not name:
                    continue
                add_stylesheet(os.path.join(os.path.dirname(f), name))
            for block in re.findall(r"<style[^>]*>(.*?)</style>", text, flags=re.S | re.I):
                (lib_parts if block.lstrip().startswith(LIB_MARK) else css_parts).append(block)
            # 内联进来的动效脚本、库样式不算页面内容
            text = re.sub(r"<script>(?:(?!</script>).)*?window\.Motion\s*=.*?</script>", "", text, flags=re.S)
            text = re.sub(r"<style>\s*/\* ui-craft\.css.*?</style>", "", text, flags=re.S)
            if pages is not None:
                pages[f] = re.sub(r"<!--.*?-->", "", text, flags=re.S)
            markup_parts.append(text)
            css_parts += [m + ";" for m in re.findall(r'\sstyle\s*=\s*"([^"]*)"', text)]
        else:
            markup_parts.append(text)
            css_parts.append(text)

    def strip(t: str) -> str:
        return re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    markup = "\n".join(markup_parts)
    markup_nocomment = re.sub(r"<!--.*?-->", "", markup, flags=re.S)
    return strip("\n".join(css_parts)), strip("\n".join(lib_parts)), markup_nocomment


# ---------------------------------------------------------------- 工具

def decl_values(css: str, prop: str) -> list[str]:
    """取某个属性的所有声明值（kebab-case 与 camelCase 都认）。"""
    camel = re.sub(r"-(\w)", lambda m: m.group(1).upper(), prop)
    names = {prop, camel}
    out: list[str] = []
    for name in names:
        pat = r"(?<![\w-])" + re.escape(name) + r"\s*:\s*([^;{}\n]+)"
        for m in re.finditer(pat, css):
            v = m.group(1).strip().strip("'\",").strip()
            if v:
                out.append(v)
    return out


def px_of(value: str) -> float | None:
    m = re.fullmatch(r"(-?\d*\.?\d+)(px|rem|em)?", value.strip())
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2)
    if unit == "em":
        return None                  # 相对于父级字号，无法换算成绝对值
    if unit == "rem":
        return n * 16
    if unit == "px":
        return n
    return n if n > 4 else None      # 无单位的小数字多半是别的含义（JS 数值字号除外）


def hex_hue_sat(hexstr: str) -> tuple[float, float, float] | None:
    h = hexstr.lstrip("#")
    if len(h) in (3, 4):
        h = "".join(c * 2 for c in h[:3])
    if len(h) < 6:
        return None
    try:
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return None
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    return hue * 360, sat, light


def is_purple(color: str) -> bool:
    color = color.strip().lower()
    if color.startswith("#"):
        hs = hex_hue_sat(color)
        return bool(hs and 225 <= hs[0] <= 310 and hs[1] > 0.3 and 0.25 < hs[2] < 0.85)
    m = re.match(r"oklch\(\s*([\d.]+%?)\s+([\d.]+)\s+([\d.]+)", color)
    if m:
        return float(m.group(2)) > 0.1 and 265 <= float(m.group(3)) <= 320
    m = re.match(r"hsla?\(\s*([\d.]+)(?:deg)?[\s,]+([\d.]+)%", color)
    if m:
        return 225 <= float(m.group(1)) <= 310 and float(m.group(2)) > 30
    return color in ("purple", "indigo", "violet", "blueviolet", "rebeccapurple", "mediumpurple")


COLOR_RE = re.compile(
    r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z_-])"
    r"|(?:rgba?|hsla?|oklch|oklab|lch|lab)\([^()]*\)", re.I)


class Report:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, cat: str, level: str, title: str, detail: str = "", fix: str = "") -> None:
        self.items.append({"category": cat, "level": level, "title": title, "detail": detail, "fix": fix})


def sample(values, n: int = 10) -> str:
    vals = list(values)
    shown = "、".join(str(v) for v in vals[:n])
    return shown + (f" …等 {len(vals)} 个" if len(vals) > n else "")


# ---------------------------------------------------------------- 检查：系统

def check_system(css: str, markup: str, rep: Report) -> None:
    # 字号
    sizes = decl_values(css, "font-size")
    sizes += [f"{v}" for v in re.findall(r"\btext-\[(\d+(?:\.\d+)?(?:px|rem|em))\]", markup)]
    literal = Counter()
    for v in sizes:
        v = v.replace("!important", "").strip()
        if v.startswith("var(") or v in ("inherit", "initial", "unset", "100%", "1em", "revert"):
            continue
        literal[v] += 1
    px_sizes = sorted({round(p, 2) for p in (px_of(v) for v in literal) if p})
    if len(literal) > 9:
        rep.add("系统", WARN, f"字号种类偏多：{len(literal)} 种裸值",
                sample(sorted(literal, key=lambda s: px_of(s) or 0)),
                "收敛到 6–7 级的字号阶梯，并通过变量引用。")
    near = [(a, b) for a, b in zip(px_sizes, px_sizes[1:]) if 0 < b - a <= 1 and a >= 11]
    if near:
        rep.add("系统", INFO, "存在相差不到 1px 的字号",
                "；".join(f"{a:g}px 与 {b:g}px" for a, b in near[:6]),
                "同一语义的字号可复用；光学校正与宿主控件可有小差异。")
    tiny = [p for p in px_sizes if p < 12]
    if tiny:
        rep.add("无障碍", WARN, "存在小于 12px 的字号", sample(f"{p:g}px" for p in tiny),
                "正文与标签不小于 12px（中文建议 13px 起）。")

    # 颜色：定义在自定义属性里的不算裸值
    non_token = re.sub(r"--[\w-]+\s*:[^;{}]+[;}]", "", css)
    # 内联 SVG（物件插画、渐变色标）的颜色属于物件材质，不计入调色板
    non_token = re.sub(r"<svg\b.*?</svg>", "", non_token, flags=re.S | re.I)
    raw = Counter(c.lower().replace(" ", "") for c in COLOR_RE.findall(non_token))
    # 半透明的纯黑、纯白是光影材质（高光、投影、颗粒），不算调色板里的颜色
    raw = Counter({c: n for c, n in raw.items() if not re.fullmatch(
        r"rgba?\((?:0,?0,?0|255,?255,?255)(?:[,/][\d.]+%?)?\)|#(?:000|fff)(?:[0-9a-f]{1,2})?|#(?:000000|ffffff)[0-9a-f]{2}|oklch\((?:0|1|100%)0+(?:/[0-9.]+%?)?\)", c)})
    token_defs = len(re.findall(r"--[\w-]+\s*:", css))
    if len(raw) > 14:
        rep.add("系统", WARN, f"裸色值偏多：{len(raw)} 种（未计入变量定义）",
                sample([c for c, _ in raw.most_common()], 12),
                "把颜色收进角色变量（--text、--surface、--accent…），组件只引用变量。")
    elif len(raw) > 6 and token_defs == 0:
        rep.add("系统", INFO, f"没有使用 CSS 变量，却有 {len(raw)} 种裸色值", "",
                "建立 tokens 后再写组件，改色和做暗色都会容易得多。")

    # 圆角
    radii = Counter(v.replace("!important", "").strip() for v in decl_values(css, "border-radius"))
    radii = Counter({k: v for k, v in radii.items() if not k.startswith("var(") and k not in ("0", "inherit")})
    if len(radii) > 5:
        rep.add("系统", INFO, f"圆角值种类偏多：{len(radii)} 种", sample(radii),
                "定一套圆角阶梯（如 4 / 8 / 12 / 全圆），嵌套时内 = 外 − 间距。")

    # 间距：不在 4px 网格上的 px 值
    odd = Counter()
    for prop in ("margin", "margin-top", "margin-bottom", "margin-left", "margin-right",
                 "padding", "padding-top", "padding-bottom", "padding-left", "padding-right",
                 "padding-inline", "padding-block", "margin-inline", "margin-block",
                 "gap", "row-gap", "column-gap"):
        for v in decl_values(css, prop):
            for n in re.findall(r"(?<![\w.-])(\d+(?:\.\d+)?)px", v):
                f = float(n)
                if f > 2 and f % 4 != 0 and f not in (6, 10, 14):
                    odd[f"{f:g}px"] += 1
    if sum(odd.values()) >= 4:
        rep.add("系统", INFO, f"有 {sum(odd.values())} 处间距不在 4px 阶梯上",
                sample([k for k, _ in odd.most_common()]),
                "检查相近间距是否表达同一分组。必要时沿用项目阶梯或光学对齐。")

    # 字重
    weights = {v.replace("!important", "").strip() for v in decl_values(css, "font-weight")}
    weights = {w for w in weights if re.fullmatch(r"\d{3}|bold|normal", w)}
    if len(weights) > 4:
        rep.add("系统", INFO, f"字重种类偏多：{len(weights)} 种", sample(sorted(weights)),
                "两到三个字重足以建立层级。")

    # z-index
    big = sorted({int(v) for v in re.findall(r"z-?[iI]ndex\s*:\s*['\"]?(\d{4,})", css)})
    if big:
        rep.add("系统", INFO, "出现很大的 z-index", sample(big),
                "给层叠顺序一个阶梯（吸附 100、下拉 200、弹窗 400…），避免军备竞赛。")


# ---------------------------------------------------------------- 检查：指纹

def check_ink_green(css: str, markup: str, rep: Report) -> None:
    import colorkit as ck

    # Inspect paint declarations. IDs, URL references and visible text can look like hex colours.
    inline = re.findall(r"""\sstyle\s*=\s*(["'])(.*?)\1""", markup, re.S | re.I)
    styles = css + "\n" + "\n".join(value for _, value in inline)
    props = r"--[\w-]+|(?:background|color|border|outline|box-shadow|text-shadow|fill|stroke|stop-color|accent-color)(?:-[\w-]+)?"
    paints = re.findall(r"(?:^|[;{])\s*(?:" + props + r")\s*:\s*([^;{}]+)", styles, re.M | re.I)
    paints.extend(value for _, value in re.findall(
        r"""\s(?:fill|stroke|stop-color|flood-color|lighting-color)\s*=\s*(["'])(.*?)\1""", markup, re.I))
    values = re.sub(r"url\([^)]*\)|var\(\s*--[\w-]+", "", " ".join(paints), flags=re.I)
    colors = set(COLOR_RE.findall(values))
    colors.update(re.findall(r"(?<![\w-])(?:darkgreen|forestgreen|seagreen|green|teal)(?![\w-])", values, re.I))
    hits = [color for color in sorted(colors) if ck.visible_ink_green(ck.to_rgba(color))]
    if hits:
        rep.add(GATE, ISSUE, "着色声明中存在禁用的墨绿色", sample(hits, 5),
                "核对实际着色的对象，替换该色，并检查投影、渐变和暗色状态的合成结果。")


def check_fingerprints(css: str, markup: str, rep: Report, has_lib: bool = False) -> None:
    both = css + "\n" + markup

    # 紫/靛渐变
    hits = []
    for m in re.finditer(r"(?:linear|radial|conic)-gradient\(", css):
        depth, i = 1, m.end()
        while i < len(css) and depth:
            depth += css[i] == "("
            depth -= css[i] == ")"
            i += 1
        body = css[m.end():i - 1]
        colors = COLOR_RE.findall(body) + re.findall(r"\b(?:purple|indigo|violet|blueviolet|rebeccapurple)\b", body)
        if len(colors) >= 2 and any(is_purple(c) for c in colors):
            hits.append(" ".join(body.split())[:70])
    tw = re.findall(r"\bfrom-(?:indigo|purple|violet|fuchsia)-\d{2,3}\b[^\"'`]*?\b(?:via|to)-(?:blue|purple|pink|indigo|violet|fuchsia|cyan)-\d{2,3}\b"
                    r"|\bfrom-(?:blue|cyan|pink)-\d{2,3}\b[^\"'`]*?\b(?:via|to)-(?:purple|indigo|violet|fuchsia)-\d{2,3}\b", markup)
    if hits or tw:
        rep.add("指纹", INFO, f"紫/靛色渐变 {len(hits) + len(tw)} 处", sample(hits + tw, 3),
                "检查渐变是否遮挡文字、夺走主体焦点，或确有品牌与材料依据。")

    # 在极坐标色彩空间里与 transparent 混色：低彩度颜色会丢色相，暖色泛粉
    n = len(re.findall(r"color-mix\(\s*in\s+(?:oklch|lch|hsl|hwb)\b[^;{}]*\btransparent\b", css))
    if n:
        rep.add("系统", WARN, f"用 oklch/lch/hsl 与 transparent 混色 {n} 处", "",
                "低彩度颜色（纸色、墨色）在这种混色里会丢失色相，渲染时偏粉偏红。改成 color-mix(in srgb, …, transparent)。")

    # 模型惯用色：框架默认蓝、Tailwind 的靛蓝紫与 slate 灰、教程渐变、纯原色
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import colorkit as ck
    except Exception:
        ck = None
    if ck:
        hits = Counter()
        no_svg = re.sub(r"<svg\b.*?</svg>", "", css + "\n" + markup, flags=re.S | re.I)
        for c in COLOR_RE.findall(no_svg):
            rgba = ck.to_rgba(c)
            name = rgba and rgba[3] > 0.2 and ck.model_default_name(rgba)
            if name:
                hits[f"{c.strip()}（{name}）"] += 1
        remapped = "由 ui-craft palette.py 生成" in markup
        tw = Counter() if remapped else Counter(m.group(1) for m in ck.TAILWIND_CLASS.finditer(markup))
        tw_hot = {k: v for k, v in tw.items() if k in ("blue", "indigo", "violet", "purple", "slate", "gray", "zinc", "sky", "cyan", "fuchsia", "pink")}
        if hits or tw_hot:
            detail = sample([k for k, _ in hits.most_common()], 6)
            if tw_hot:
                detail += ("；" if detail else "") + "Tailwind 默认色族 " + "、".join(f"{k}×{v}" for k, v in sorted(tw_hot.items(), key=lambda kv: -kv[1]))
            n = len(hits) + len(tw_hot)
            rep.add("指纹", INFO, f"命中常见预设色 {n} 种", detail,
                    "在渲染图上确认品牌、信息编码和对比。需要统一主题时可先预览 recolor.py 的映射。")

    # 渐变文字
    n = len(re.findall(r"background-clip\s*:\s*text|backgroundClip\s*:\s*['\"]text", css)) \
        + len(re.findall(r"\bbg-clip-text\b", markup))
    if n:
        rep.add("指纹", INFO, f"渐变文字 {n} 处", "", "用字号、字重和字体本身制造力量，可读性也更好。")

    # 字体
    families = decl_values(css, "font-family")
    firsts = []
    for fam in families:
        if fam.startswith("var(") or fam == "inherit":
            continue
        first = fam.split(",")[0].strip().strip("'\"").lower()
        if first:
            firsts.append(first)
    has_style = bool(css.strip())
    token_fonts = re.findall(r"--font[\w-]*\s*:\s*([^;{}]+)", css)
    for tf in token_fonts:
        first = tf.split(",")[0].strip().strip("'\"").lower()
        if first and not first.startswith("var("):
            firsts.append(first)
    if firsts and all(f in GENERIC_FONTS for f in firsts):
        rep.add("指纹", INFO, "字体以常见系统字体为主",
                sample(sorted(set(firsts))),
                "后台、工具、设置页这样做没问题（标题靠 600 字重与按字号收紧的字距立起来）；"
                "品牌或阅读页可试着改变字面、留白或编排，系统字体也可以承担展示。")
    elif has_style and not families and not firsts and not has_lib and not decl_values(css, "font") and re.search(r"<body|<html", markup, re.I):
        rep.add("指纹", WARN, "没有设置任何 font-family", "", "浏览器默认字体（通常是 Times/宋体）会直接上场。")

    # emoji 当图标
    emoji = re.findall(r"[\U0001F300-\U0001FAFF☀-⛿✨⭐✅❌]", markup)
    if len(emoji) >= 3:
        rep.add("指纹", INFO, f"界面里有 {len(emoji)} 个 emoji", sample(list(dict.fromkeys(emoji)), 12),
                "若是充当图标，换成一套线宽一致的 SVG 图标。")

    # 纯黑纯白
    pure_black_text = len(re.findall(r"(?<![\w-])color\s*:\s*(?:#000(?:000)?\b|black\b|rgb\(\s*0\s*,?\s*0\s*,?\s*0\s*\))", css, re.I))
    pure_white_bg = len(re.findall(r"background(?:-color)?\s*:\s*(?:#fff(?:fff)?\b|white\b|rgb\(\s*255\s*,?\s*255\s*,?\s*255\s*\))", css, re.I))
    if pure_black_text and pure_white_bg:
        rep.add("指纹", INFO, "纯黑文字与纯白背景均出现在源文件中", "",
                "在实际组合中检查辨读和舒适度。单色及高对比任务可保留原色。")

    # 毛玻璃
    n = len(re.findall(r"backdrop-filter\s*:|backdropFilter\s*:", css)) + len(re.findall(r"\bbackdrop-blur", markup))
    if n > 3:
        rep.add("指纹", INFO, f"backdrop-filter 用了 {n} 处", "", "只在确有内容从下方滚过时使用（如吸顶导航）。")

    # 重阴影
    heavy = 0
    for v in decl_values(css, "box-shadow"):
        for a in re.findall(r"rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*(0?\.\d+|1)\s*\)", v):
            if float(a) >= 0.25:
                heavy += 1
    if heavy >= 2:
        rep.add("指纹", INFO, f"又黑又重的阴影 {heavy} 处（黑色，不透明度 ≥ 0.25）", "",
                "阴影分两层、降低不透明度、颜色取背景的深色调；或直接换成 1px 边框。")

    # 彩色左边框
    n = len(re.findall(r"border-left\s*:\s*[3-9]px\s+solid", css)) + len(re.findall(r"\bborder-l-(?:4|8)\b", markup))
    if n >= 2:
        rep.add("指纹", INFO, f"粗的彩色左边框 {n} 处", "", "核对线条是否在表示状态、系列或选中项，并观察相邻内容的注意力。")

    # 占位内容
    found = [label for pat, label in PLACEHOLDER_PATTERNS if re.search(pat, markup, re.I)]
    if found:
        rep.add("指纹", INFO, "出现常见示例词或地址", sample(found), "结合实际文案判断这些词是否符合本项目。")

    # 均匀的大圆角 + 阴影卡片
    cards = len(re.findall(r"\brounded-(?:2xl|3xl)\b[^\"'`]*\bshadow-(?:lg|xl|2xl)\b|\bshadow-(?:lg|xl|2xl)\b[^\"'`]*\brounded-(?:2xl|3xl)\b", markup))
    if cards >= 4:
        rep.add("指纹", INFO, f"大圆角加大阴影的组合出现 {cards} 次", "",
                "所有东西一样软、一样浮就没有主次。按元素角色使用圆角与阴影阶梯。")


# ---------------------------------------------------------------- 检查：无障碍

class PageMarkup(HTMLParser):
    """Collect page-local HTML evidence; the browser remains authoritative for computed names."""
    VOID_TAGS = frozenset("area base br col embed hr img input link meta param source track wbr".split())

    def __init__(self, markup: str, *, component=False):
        self.component = component
        super().__init__(convert_charrefs=True)
        self.html: list[dict[str, str]] = []
        self.viewports: list[str] = []
        self.images: list[dict[str, str]] = []
        self.buttons: list[dict[str, str]] = []
        self.controls: list[tuple[dict[str, str], int | None]] = []
        self.labels: list[dict[str, str]] = []
        self.has_runtime = False
        self._label: int | None = None
        self._button: dict[str, str] | None = None
        self._hidden: list[str] = []
        self.feed(markup)
        self.close()

    def handle_starttag(self, tag, attrs):
        values = {key: (value or "").strip() for key, value in attrs}
        if self._hidden:
            if tag == self._hidden[-1]:
                self._hidden.append(tag)
            return
        if tag == "script" and values.get("type", "").lower() in ("", "module", "text/javascript", "application/javascript"):
            self.has_runtime = True
        ignored = (tag in ("script", "style") or (tag == "template" and not self.component) or
                   "hidden" in values or values.get("aria-hidden", "").lower() == "true")
        if ignored:
            if tag not in self.VOID_TAGS:
                self._hidden.append(tag)
            return
        if tag == "html":
            self.html.append(values)
        elif tag == "meta" and values.get("name", "").lower() == "viewport":
            self.viewports.append(values.get("content", ""))
        elif tag == "label":
            self._label = len(self.labels)
            self.labels.append({"for": values.get("for", ""), "name": values.get("aria-label") or values.get("aria-labelledby") or values.get("title", "")})
        elif tag == "button":
            self._button = values.copy()
            self._button["_content"] = ""
            self.buttons.append(self._button)
        elif tag == "img":
            self.images.append(values)
        elif tag in ("input", "select", "textarea"):
            self.controls.append((values, self._label))
        if tag != "button" and self._button is not None:
            self._button["_content"] += values.get("alt") or values.get("aria-label", "")
        if self._label is not None and tag == "img":
            self.labels[self._label]["name"] += values.get("alt", "")

    def handle_endtag(self, tag):
        if self._hidden:
            if tag == self._hidden[-1]:
                self._hidden.pop()
            return
        if tag == "label":
            self._label = None
        if tag == "button":
            self._button = None

    def handle_data(self, data):
        if self._hidden:
            return
        if self._button is not None:
            self._button["_content"] += data
        if self._label is not None:
            self.labels[self._label]["name"] += data


def has_bound_name(attrs: dict[str, str]) -> bool:
    named = ("aria-label", "aria-labelledby", "title")
    if any(attrs.get(key) for key in named):
        return True
    # Component shorthand and bound/spread directives are resolved by the renderer.
    if any(key in attrs for key in ("v-bind", "v-text", "v-html")):
        return True
    for key in attrs:
        if key.startswith("{"):
            return True
        if key.startswith((":", "[", "v-bind:", "x-bind:")):
            target = key.split(":")[-1].strip("[]")
            if target in (*named, "alt"):
                return True
    return False


def limits_zoom(content: str) -> bool:
    for name, value in re.findall(r"(?:^|[,;\s])([\w-]+)\s*=\s*([^,;\s]+)", content.lower()):
        if name == "user-scalable" and value in ("no", "0"):
            return True
        if name == "maximum-scale":
            try:
                if 0 < float(value) <= 1:
                    return True
            except ValueError:
                pass
    return False


def check_a11y(css: str, markup: str, rep: Report, *, fragment=False) -> None:
    page = PageMarkup(markup, component=fragment)
    dynamic = fragment or page.has_runtime
    if page.html and not page.viewports:
        rep.add("无障碍", WARN, "完整 HTML 未声明移动视口", "", "需要响应窄屏时补上 viewport 并在目标视口核对。")
    if any(not (attrs.get("lang") or attrs.get(":lang") or attrs.get("v-bind:lang") or attrs.get("xml:lang")) for attrs in page.html):
        rep.add("无障碍", WARN if dynamic else ISSUE, "<html> 在源标记中缺少 lang 属性", "", "按页面实际语言声明根元素的 lang。")
    if any(limits_zoom(v) for v in page.viewports):
        rep.add("无障碍", ISSUE, "viewport 限制了页面缩放", "", "移除禁用缩放的指令并在浏览器验证。")

    images = [img for img in page.images if "alt" not in img and not has_bound_name(img)
              and img.get("role", "").lower() not in ("presentation", "none") and img.get("aria-hidden", "").lower() != "true"]
    if images:
        rep.add("无障碍", WARN if dynamic else ISSUE, f"{len(images)} 个图片在源标记中缺少 alt", "",
                  '表意图提供等价说明，装饰图使用 alt=""。运行时绑定请在可访问树确认。')

    named_for = {label["for"] for label in page.labels if label["for"] and label["name"].strip()}
    unnamed = []
    for control, label_index in page.controls:
        kind = control.get("type", "text").lower()
        if kind in ("hidden", "submit", "reset") or "hidden" in control or has_bound_name(control):
            continue
        if control.get("id") and control["id"] in named_for:
            continue
        if label_index is not None:
            label = page.labels[label_index]
            if label["name"].strip() and (not label["for"] or label["for"] == control.get("id")):
                continue
        if (kind == "button" and control.get("value")) or (kind == "image" and control.get("alt")):
            continue
        if control.get("placeholder") and kind not in ("checkbox", "radio", "button", "image"):
            rep.add("无障碍", WARN, "输入框只有占位提示", control.get("id", ""), "填写后核对字段名称是否仍可读。")
            continue
        unnamed.append(control.get("id") or control.get("name") or kind)
    if unnamed:
        rep.add("无障碍", WARN if dynamic else ISSUE, f"{len(unnamed)} 个输入控件在源标记中没有关联名称",
                  sample(unnamed, 4), "关联 label 或提供可访问名称。运行时设置的名称要在实际界面核对。")
    buttons = [button for button in page.buttons if "hidden" not in button and
               not button["_content"].strip() and not has_bound_name(button)]
    if buttons:
        rep.add("无障碍", WARN if dynamic else ISSUE, f"{len(buttons)} 个按钮在源标记中没有可访问名称", "",
                  "给出动作文字或可访问名称。运行时生成名称时在可访问树确认。")

    # Outline removal alone cannot establish whether a host, a parent or another sheet supplies focus.
    focus_reset = re.search(r"outline(?:-width|-style)?\s*:\s*(?:none|0)\b|\boutline-none\b", css + "\n" + markup, re.I)
    if focus_reset:
        focus_selectors = [selector.strip() for selector, block in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
                           if ":focus" in selector and re.search(r"outline(?:-width|-style)?\s*:\s*(?:none|0)\b", block, re.I)]
        if focus_selectors:
            rep.add("无障碍", WARN, "焦点选择器显式移除了轮廓", sample(focus_selectors, 3),
                    "用键盘聚焦该对象，检查替代的底色、边框或轮廓在当前主题中是否可辨。")
        elif page.buttons or page.controls or re.search(r"<a\b[^>]*\bhref\s*=|\btabindex\s*=", markup, re.I):
            rep.add("无障碍", INFO, "源样式含轮廓重置", "", "在目标控件实看原生或自定义键盘焦点。")
    elif (page.buttons or page.controls) and ":focus" not in css and 'content="ui-craft email"' not in markup:
        rep.add("无障碍", INFO, "使用原生或外部焦点样式", "", "用键盘核对实际焦点。")
    n = len(re.findall(r"<(?:div|span)\b[^>]*\bon[Cc]lick\s*=", markup))
    if n:
        rep.add("无障碍", WARN, f"{n} 个 div/span 绑定了点击事件", "", "检查角色、键盘激活与焦点。")


# ---------------------------------------------------------------- 检查：动效

def check_motion(css: str, markup: str, rep: Report, ctx: str = "") -> None:
    """css 是页面自己的样式；ctx 是已校验的库样式，只用来判断是否处理了 reduced-motion。"""
    both = css + "\n" + ctx + "\n" + markup
    has_motion = bool(re.search(r"(?<![\w-])(?:transition|animation)(?:-[\w]+)?\s*:|@keyframes|\btransition-|\banimate-", both))
    if not has_motion:
        return

    if not re.search(r"prefers-reduced-motion|motion-reduce:|motion-safe:|useReducedMotion", both):
        rep.add("动效", INFO, "没有为 prefers-reduced-motion 准备退化方案", "",
                "按页面的动效策略验证减少动态效果时的内容、操作与结果。")

    n = len(re.findall(r"transition(?:-property)?\s*:\s*all\b", css)) + len(re.findall(r"\btransition-all\b", markup))
    if n:
        rep.add("动效", WARN, f"transition: all 出现 {n} 次", "",
                "明确列出要过渡的属性（多为 background-color、border-color、opacity、transform）。")

    long_durs = []
    for v in decl_values(css, "transition") + decl_values(css, "transition-duration"):
        for num, unit in re.findall(r"(?<![\w.-])(\d*\.?\d+)(ms|s)\b", v):
            ms = float(num) * (1000 if unit == "s" else 1)
            if ms > 1000 and not re.search(r"stroke-dashoffset|clip-path|background-position", v):
                long_durs.append(f"{ms:g}ms")
    if long_durs:
        rep.add("动效", INFO, f"界面过渡超过 1000ms 的有 {len(long_durs)} 处", sample(sorted(set(long_durs))),
                "界面过渡多在 120–300ms，弹簧 450–700ms；更长的只给首屏编排、描线、结算揭晓。")

    layout = 0
    for v in decl_values(css, "transition") + decl_values(css, "transition-property"):
        if re.search(r"(?<![\w-])(?:width|height|top|left|right|bottom|margin|padding)(?![\w-])", v):
            layout += 1
    if layout:
        rep.add("动效", INFO, f"对布局属性做过渡 {layout} 处（width/height/top/left/margin…）", "",
                "改用 transform 与 opacity；高度展开可用 grid-template-rows 0fr → 1fr。")

    infinite = len(re.findall(r"animation[^;{}]*\binfinite\b", css)) + len(re.findall(r"\banimate-(?:bounce|pulse|ping)\b", markup))
    if infinite > 2:
        rep.add("动效", INFO, f"无限循环的动画 {infinite} 处", "",
                "网页里除了加载与\"正在发生\"的状态，持续运动会一直争夺注意力；游戏里慢速的环境层（齿轮、蒸汽、水面）可以有，界面层只给\"现在该按这个\"。")


# ---------------------------------------------------------------- 检查：中文

def check_scroll_perf(css: str, markup: str, rep: Report) -> None:
    """滚动时会掉帧的写法。css 只含页面自己的样式（已校验的 ui-craft 库不算）。"""
    scripts = " ".join(re.findall(r"<script\b[^>]*>(.*?)</script>", markup, flags=re.S | re.I))
    scripts = re.sub(r"window\.Motion\s*=.*", "", scripts, flags=re.S)       # 内联进来的动效库不算
    n = len(re.findall(r"backdrop-filter\s*:\s*(?!none)", css)) + len(re.findall(r"\bbackdrop-blur", markup))
    if n:
        rep.add("性能", WARN, f"毛玻璃（backdrop-filter）{n} 处", "",
                "滚动时它要把背后的内容每一帧重新模糊一遍，吸顶导航上最费。改成接近不透明的底色："
                "background: color-mix(in srgb, var(--bg) 94%, transparent)；确实要毛玻璃时只留一处，模糊半径 ≤ 12px。")
    big = [int(float(x)) for x in re.findall(r"(?<![\w-])filter\s*:[^;{}]*blur\(\s*(\d+(?:\.\d+)?)px", css) if float(x) >= 16]
    if big:
        rep.add("性能", WARN, f"大半径 filter: blur() {len(big)} 处", "、".join(f"{b}px" for b in big[:6]),
                "做光晕时不需要模糊：radial-gradient(closest-side, color-mix(in srgb, var(--accent) 30%, transparent), transparent) 本身就是柔边。"
                "模糊滤镜的开销随半径和面积增长，和视差、浮动叠在一起时每帧都要重算。")
    blend = [m for m in re.findall(r"mix-blend-mode\s*:\s*([\w-]+)", css) if m not in ("normal", "lighten")]
    if blend:
        rep.add("性能", WARN, f"mix-blend-mode {len(blend)} 处", "、".join(sorted(set(blend))),
                "混合模式让整块区域无法单独交给显卡合成，里面有任何动画都要重绘。颗粒、光感改用带透明度的图层叠放。")
    if re.search(r"background-attachment\s*:\s*fixed", css):
        rep.add("性能", WARN, "background-attachment: fixed", "", "滚动时整块背景每帧重绘。改成 position: fixed 的独立图层，或直接去掉。")
    heavy_kf = []
    for name, body in re.findall(r"@keyframes\s+([\w-]+)\s*\{((?:[^{}]*\{[^{}]*\})*[^{}]*)\}", css):
        props = set(re.findall(r"([a-z-]+)\s*:", body))
        bad = props & {"width", "height", "top", "left", "right", "bottom", "margin", "padding", "box-shadow", "filter",
                       "clip-path", "background-position", "border-width", "font-size", "letter-spacing"}
        if bad:
            heavy_kf.append(f"{name}（{'、'.join(sorted(bad))}）")
    if heavy_kf:
        rep.add("性能", WARN, f"动画用了不能交给显卡的属性 {len(heavy_kf)} 处", "；".join(heavy_kf[:5]),
                "只动画 transform（translate / scale / rotate）和 opacity。尺寸变化用 scale，阴影变化用叠一层阴影再改它的 opacity。")
    svg_anim = re.findall(r"<(?:g|path|circle|ellipse|rect|line|polyline|polygon)\b[^>]*class=\"[^\"]*\b(spin-slow|float|spin)\b", markup)
    if svg_anim:
        rep.add("性能", WARN, f"<svg> 内部的元素在做持续动画 {len(svg_anim)} 处", "",
                "SVG 里的 <g>、<path> 做动画时，浏览器每帧都要重绘整张图。把动画放到外层的 <svg> 或包着它的 <div> 上（transform 动画），效果一样，交给显卡合成。")
    for m in re.finditer(r"addEventListener\(\s*['\"]scroll['\"]\s*,(.{0,40})", scripts, re.S):
        if "passive" not in scripts[m.start():m.start() + 600]:
            rep.add("性能", WARN, "滚动监听没有标 passive", "", "addEventListener('scroll', fn, { passive: true })。")
            break
    if re.search(r"addEventListener\(\s*['\"]scroll['\"]", scripts) and re.search(r"getBoundingClientRect|offsetTop|offsetHeight|scrollHeight", scripts) \
            and not re.search(r"requestAnimationFrame", scripts):
        rep.add("性能", WARN, "滚动回调里直接读布局", "",
                "每次滚动事件都读位置、改样式，会让浏览器反复重新布局。用 requestAnimationFrame 合并到每帧一次，先读完所有位置再统一写；"
                "进度条用 CSS 的 animation-timeline: scroll()，目录高亮用 IntersectionObserver。")


# ---------------------------------------------------------------- 检查：游戏 mod 与引擎代码里的界面

EXTS_ENGINE = {".cpp", ".cc", ".cxx", ".h", ".hpp", ".cs", ".java", ".kt", ".lua", ".luau", ".gd", ".py", ".dart", ".swift"}


def collect_engine(paths: list[str]) -> list[str]:
    out = []
    for p in paths:
        if os.path.isfile(p) and os.path.splitext(p)[1].lower() in EXTS_ENGINE:
            out.append(p)
        elif os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".") and d not in ("imgui", "third_party", "external", "lib", "libs")]
                out += [os.path.join(root, n) for n in names if os.path.splitext(n)[1].lower() in EXTS_ENGINE]
    return out[:4000]


def check_engine_code(files: list[str], rep: Report) -> None:
    """mod 菜单、游戏内覆盖层、原生界面里最常见的"默认皮肤"和模型惯用色。"""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import colorkit as ck
    except Exception:
        ck = None
    imgui_default = imgui_custom = False
    imgui_blue = []
    unity_gui = unity_skin = False
    hits = Counter()
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                t = fh.read(800_000)
        except OSError:
            continue
        if re.search(r"StyleColors(?:Dark|Classic|Light)\s*\(", t):
            imgui_default = True
        if re.search(r"ImGuiCol[_.]\w+\s*\]\s*=|PushStyleColor\s*\(", t):
            imgui_custom = True
        if re.search(r"0\.26f?\s*,\s*0\.59f?\s*,\s*0\.98f?", t):
            imgui_blue.append(os.path.basename(f))
        if re.search(r"\bvoid\s+OnGUI\s*\(", t) and re.search(r"\bGUI(?:Layout)?\.(?:Window|Box|Button|Label)\b", t):
            unity_gui = True
        if re.search(r"\bGUISkin\b|\bGUI\.skin\s*=|new\s+GUIStyle\b", t):
            unity_skin = True
        if re.search(r"seedColor\s*:\s*Colors\.(?:deepPurple|purple|indigo|blue)\b", t):
            hits["Flutter 模板默认 seedColor（Colors.deepPurple 一族）"] += 1
        if ck:
            cands = re.findall(r"['\"]#[0-9A-Fa-f]{6}['\"]", t)
            cands += [f"#{m}" for m in re.findall(r"\b0x(?:FF)?([0-9A-Fa-f]{6})\b", t) if re.search(r"(?i)colou?r|fill|text|bg|draw", t)]
            cands += ["#%02X%02X%02X" % tuple(int(x) for x in m) for m in
                      re.findall(r"(?:Color3\.fromRGB|new\s+Color(?:32)?|Color\.FromArgb|rgb)\s*\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*[,)]", t)
                      if all(int(x) <= 255 for x in m)]
            for c in cands:
                c = c.strip("'\"")
                rgba = ck.to_rgba(c)
                name = rgba and ck.model_default_name(rgba)
                if name and not name.startswith("Tailwind slate") and not name.startswith("Tailwind gray"):
                    hits[f"{c.upper()}（{name}）"] += 1
    if imgui_default and not imgui_custom:
        rep.add("指纹", INFO, "发现 Dear ImGui 内置主题", "StyleColorsDark/Classic/Light",
                "核对宿主约定、选区和键盘焦点。自定义主题时可复用现有令牌。")
    elif imgui_blue:
        rep.add("指纹", INFO, "发现 ImGui 预设蓝色值", sample(sorted(set(imgui_blue)), 4),
                "若为宿主选择或品牌色，沿用它。用实际状态判断是否需调整。")
    if unity_gui and not unity_skin:
        rep.add("指纹", INFO, "发现 Unity IMGUI 原生控件", "OnGUI / GUI / GUILayout",
                "在当前宿主检查字体、缩放与可读性。需要自定皮肤时再选择 GUISkin 或其他适合的主题。")
    if hits:
        rep.add("指纹", INFO, f"代码含常见预设色 {len(hits)} 种", sample([k for k, _ in hits.most_common()], 6),
                "在实际背景核对颜色的用途。局部修改保持宿主约定。")


def check_cjk(css: str, markup: str, rep: Report, ctx: str = "") -> None:
    visible = re.sub(r"<(script|style)\b.*?</\1>", "", markup, flags=re.S | re.I)
    cjk = re.findall(r"[一-鿿]", visible)
    if len(cjk) < 20:
        return

    neg = [v for v in decl_values(css, "letter-spacing") if v.strip().startswith("-")]
    if neg:
        rep.add("中文", INFO, f"页面含中文，且有 {len(neg)} 处负字距", sample(sorted(set(neg))),
                "确认负字距只作用于纯西文标题；汉字收紧字距会相互挤压。")

    lhs = []
    for v in decl_values(css + "\n" + ctx, "line-height"):
        m = re.fullmatch(r"(\d*\.?\d+)", v.replace("!important", "").strip())
        if m:
            lhs.append(float(m.group(1)))
    lh_vars = [float(x) for x in re.findall(r"--(?:leading|line-height)[\w-]*\s*:\s*(\d*\.?\d+)\s*[;}]", css)]
    if (lhs or lh_vars) and max(lhs + lh_vars) < 1.6:
        rep.add("中文", WARN, f"页面含中文，但最大的行高只有 {max(lhs + lh_vars):g}", "",
                "中文正文行高建议 1.7–1.85，标题 1.3–1.45。")

    if re.search(r"font-style\s*:\s*italic|<em\b|<i>(?!\s*</i>)", css + markup, re.I):
        rep.add("中文", INFO, "页面含中文，且使用了斜体", "",
                "中文没有真斜体。确认斜体只落在西文上；中文强调用字重、颜色或着重号。")

    fam_text = " ".join(decl_values(css, "font-family") + re.findall(r"--font[\w-]*\s*:\s*([^;{}]+)", css)).lower()
    if fam_text and not any(h in fam_text for h in CJK_FONT_HINTS):
        rep.add("中文", INFO, "字体栈里没有指定任何中文字体", "",
                "在西文字体之后加上 \"PingFang SC\", \"Noto Sans SC\", \"Microsoft YaHei\" 等，避免回退到不可控的默认字体。")

    if re.search(r"font-?[wW]eight\s*:\s*['\"]?500\b|\bfont-medium\b", css + markup) and \
            not re.search(r"noto sans sc|source han|harmonyos|misans|思源", fam_text):
        rep.add("中文", INFO, "页面含中文，并使用了 500 字重", "",
                "微软雅黑没有 Medium，Windows 上中文的 500 与 400 完全相同。靠 500 区分的层级改用 600/700 或配合字号与颜色。")


# ---------------------------------------------------------------- 门槛（--gate）

GATE = "门槛"
@lru_cache(maxsize=1)
def template_samples() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Preserve template identity when matching several phrases on one page."""
    from pathlib import Path
    groups = []
    for path in sorted((Path(__file__).resolve().parents[1] / "templates").glob("*.html")):
        try:
            template = path.read_text(encoding="utf-8")
        except OSError:
            continue
        markers = re.findall(r"<!--@sample (.*?)-->", template)
        words = tuple(dict.fromkeys(s.strip() for marker in markers for s in marker.split("|") if s.strip()))
        if words:
            groups.append((path.name, words))
    return tuple(groups)


def check_sample_media(files: list[str], rep: Report) -> None:
    """模板自带的示例图片（唱机、银杏叶……）还留在页面里：按文件内容比对，改名也认得出。"""
    import base64
    import hashlib
    root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
    samples: dict[str, str] = {}
    for sub in ("showcase", "compare"):
        d = os.path.join(root, sub)
        if os.path.isdir(d):
            for n in os.listdir(d):
                if not os.path.isfile(os.path.join(d, n)):
                    continue
                with open(os.path.join(d, n), "rb") as fh:
                    samples[hashlib.sha1(fh.read()).hexdigest()] = f"{sub}/{n}"
    if not samples:
        return
    found: list[str] = []
    for f in files:
        if os.path.splitext(f)[1].lower() not in EXTS_MARKUP:
            continue
        try:
            with open(f, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        base = os.path.dirname(os.path.abspath(f))
        # Match every local candidate in srcset as well as src, poster and image links.
        attrs = re.findall(rb"""(?<![\w-])(?:src|srcset|href|poster)\s*=\s*(["'])(.*?)\1""", data, re.I | re.S)
        references = set()
        for _, raw_attr in attrs:
            value = unescape(raw_attr.decode("utf-8", "replace")).strip()
            if not value or value.startswith("data:"):
                continue
            for candidate in re.split(r",\s*(?=[^\s])", value):
                # A responsive image candidate may end with a 2x or 600w descriptor.
                ref = re.sub(r"\s+[\d.]+[wx]\s*$", "", candidate.strip(), flags=re.I)
                try:
                    parsed = urlsplit(ref)
                except ValueError:
                    continue
                path = unquote(parsed.path)
                if parsed.scheme or parsed.netloc or path.startswith(("/", "\\")):
                    continue
                if path.lower().endswith((".webp", ".png", ".jpg", ".jpeg", ".avif")):
                    references.add(os.path.join(base, path))
        for path in references:
            if os.path.isfile(path):
                with open(path, "rb") as fh:
                    h = hashlib.sha1(fh.read()).hexdigest()
                if h in samples:
                    found.append(samples[h])
        for b64 in EMBEDDED_MEDIA.findall(data):
            try:
                raw = base64.b64decode(b64.split(b",", 1)[1])
            except Exception:
                continue
            h = hashlib.sha1(raw).hexdigest()
            if h in samples:
                found.append(samples[h])
    if found:
        rep.add(GATE, ISSUE, f"页面引用了套件示例图片（{len(set(found))} 张）", sample(sorted(set(found)), 6),
                "核对来源。意外带入时换成项目素材；简报明确指定同一素材时保留原图，用 --allow-sample 并核对其余演示内容。")


def check_gate(css_lib: str, markup: str, rep: Report, allow_sample: bool) -> None:
    visible = re.sub(r"<(script|style)\b[^>]*>.*?</\1\s*>", "", markup, flags=re.S | re.I)
    # Examples quoted in documentation do not constitute residual product copy.
    content = re.sub(r"<(pre|code)\b[^>]*>.*?</\1\s*>", "", visible, flags=re.S | re.I)
    if not allow_sample:
        text_only = unescape(re.sub(r"<[^>]+>", " ", content))
        attrs = re.findall(r"""\s(?:value|alt|placeholder|aria-label|title)\s*=\s*(["'])(.*?)\1""",
                           content, flags=re.S | re.I)
        words = "\n".join([text_only, *(unescape(value) for _, value in attrs)])
        for example, tokens in template_samples():
            hits = [token for token in tokens if token in words]
            if len(hits) >= 3:
                rep.add(GATE, ISSUE, "同页命中同一模板的多处示例文案", example + " · " + sample(hits, 5),
                        "核对项目要展示的内容。有意保留套件样例时使用 --allow-sample。")
        if re.search(r"\blorem\s+ipsum\s+dolor\s+sit\s+amet\b", words, re.I):
            rep.add(GATE, ISSUE, "包含完整的排版占位短语", "Lorem ipsum dolor sit amet",
                    "替换为实际文案。有意保留的演示内容可用 --allow-sample。")
    h1 = len(re.findall(r"<h1\b", visible, re.I))
    if h1 > 1:
        rep.add(GATE, INFO, f"源页面含 {h1} 个 h1", "", "结合当前可见状态、标题层级与阅读顺序核对。")
    if css_lib and re.search(r"<html\b", markup, re.I) and not re.search(r"classList\.add\(['\"]js['\"]\)", markup):
        rep.add(GATE, INFO, "套件页面未发现动效初始化", "",
                "页面确实依赖套件动效时，核对关闭脚本与开启脚本两种状态的内容是否可见。")


def render_gate(rep: Report, n_files: int) -> tuple[str, bool]:
    blockers = [item for item in rep.items if item["level"] == ISSUE]
    observations = [item for item in rep.items if item["level"] != ISSUE]
    if blockers:
        lines = [f"未通过：发现 {len(blockers)} 项需要修正（扫描了 {n_files} 个文件）。"]
    else:
        lines = [f"通过：已检查的源文件未发现阻断项（{n_files} 个文件）。"]
    for n, item in enumerate(blockers, 1):
        lines.append(f"{n}. {item['title']}")
        if item["detail"]:
            lines.append(f"   线索：{item['detail']}")
        if item["fix"]:
            lines.append(f"   改法：{item['fix']}")
    if observations:
        lines.append(f"另有 {len(observations)} 条观察提示，需在实际使用场景判断。")
        for item in observations:
            suffix = f" · {item['detail']}" if item["detail"] else ""
            lines.append(f"  [{item['category']}] {item['title']}{suffix}")
    lines.append("请在目标尺寸查看实际画面，并操作本次改动的流程。")
    return "\n".join(lines), not blockers


# ---------------------------------------------------------------- 输出

def render(rep: Report, n_files: int) -> str:
    lines = [f"设计体检：扫描了 {n_files} 个文件", ""]
    counts = Counter(i["level"] for i in rep.items)
    if not rep.items:
        lines.append("没有发现需要留意的地方。静态检查看不到画面——仍然要渲染出来看。")
        return "\n".join(lines)
    for cat in CATS:
        items = sorted((i for i in rep.items if i["category"] == cat), key=lambda i: ORDER[i["level"]])
        if not items:
            continue
        lines.append(f"── {cat} " + "─" * (40 - len(cat) * 2))
        for it in items:
            lines.append(f"  [{it['level']}] {it['title']}")
            if it["detail"]:
                lines.append(f"         {it['detail']}")
            if it["fix"]:
                lines.append(f"       → {it['fix']}")
        lines.append("")
    lines.append(f"合计：问题 {counts[ISSUE]} · 留意 {counts[WARN]} · 信息 {counts[INFO]}")
    fp = sum(1 for i in rep.items if i["category"] == "指纹")
    if fp >= 4:
        lines.append(f"模板指纹命中 {fp} 条——回到设计立场，确认每一条都是有意的选择。")
    lines.append("提示：这些是线索不是判决；静态检查看不到画面，渲染出来看才算数。")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="界面代码的静态设计体检")
    ap.add_argument("paths", nargs="+", help="文件或目录")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    ap.add_argument("--strict", action="store_true", help="存在 [问题] 级条目时以退出码 1 结束")
    ap.add_argument("--gate", action="store_true",
                    help="加查模板残留；仅 [问题] 导致退出码 1。审美和实现线索在渲染后判断。")
    ap.add_argument("--allow-sample", action="store_true", help="允许套件示例文本与图片，适用于验证模板或明确复用素材。")
    args = ap.parse_args()

    skipped: list[str] = []
    files = collect(args.paths, skipped)
    engine_files = collect_engine(args.paths)
    skipped = [x for x in skipped if os.path.splitext(x)[1].lower() not in EXTS_ENGINE]
    if not files and engine_files:
        # 只有 mod / 引擎 / 原生应用代码：只做这一类检查
        rep = Report()
        check_engine_code(engine_files, rep)
        if args.json:
            print(json.dumps({"files": len(engine_files), "findings": rep.items}, ensure_ascii=False, indent=2))
        else:
            print(render(rep, len(engine_files)))
            print("这是 mod、引擎或桌面程序的代码：静态检查只能找出默认皮肤和惯用色，界面本身要运行起来截图看"
                  "（游戏 mod 见 references/game-mods.md 第 8 节；tkinter 按常用窗口尺寸开，浅色、暗色各截一次）。")
        return 1 if (args.strict and any(i["level"] == ISSUE for i in rep.items)) else 0
    if not files:
        message = "没有找到可检查的文件（支持 HTML、样式表、前端源文件，以及 C++ / C# / Java / Kotlin / Lua / GDScript / Python 的界面代码）。"
        print(json.dumps({"files": 0, "findings": [], "error": message}, ensure_ascii=False) if args.json else message)
        return 2
    pages: dict[str, str] = {}
    css, css_lib, markup = load(files, skipped, pages)
    has_lib = bool(css_lib.strip())
    css_all = css + "\n" + css_lib
    rep = Report()
    if skipped:
        rep.add("系统", ISSUE, "部分源文件未能检查", sample(skipped, 3),
                "检查文件是否可读，并将超过体积限制的源代码分开检查。内嵌图片不计入网页的代码体积。")
    check_system(css, markup, rep)
    check_ink_green(css_all, markup, rep)
    check_fingerprints(css, markup, rep, has_lib)
    # A second page cannot supply this page's language, label or template copy.
    for path, source in pages.items():
        page_report = Report()
        is_component = os.path.splitext(path)[1].lower() not in (".html", ".htm")
        check_a11y(css_all, source, page_report, fragment=is_component)
        if args.gate:
            check_gate(css_lib, source, page_report, args.allow_sample)
        for finding in page_report.items:
            finding["detail"] = path + (" · " + finding["detail"] if finding["detail"] else "")
        rep.items.extend(page_report.items)
    if not pages and markup.strip() and re.search(r"<(?:button|input|img|select|textarea)\b", markup, re.I):
        rep.add("无障碍", INFO, "前端脚本含运行时标记", "", "在渲染的组件中检查名称、焦点和输入。")
    check_motion(css, markup, rep, css_lib)
    check_cjk(css, markup, rep, css_lib)
    check_scroll_perf(css, markup, rep)
    if engine_files:
        check_engine_code(engine_files, rep)
    if args.gate and not args.allow_sample:
        check_sample_media(files, rep)

    failed = any(i["level"] == ISSUE for i in rep.items)
    if args.json:
        print(json.dumps({"files": len(files), "findings": rep.items}, ensure_ascii=False, indent=2))
        return int(failed and (args.gate or args.strict))
    if args.gate:
        text, ok = render_gate(rep, len(files))
        print(text)
        return 0 if ok else 1
    print(render(rep, len(files)))
    return 1 if (args.strict and any(i["level"] == ISSUE for i in rep.items)) else 0


if __name__ == "__main__":
    sys.exit(main())
