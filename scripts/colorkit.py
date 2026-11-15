#!/usr/bin/env python3
"""颜色工具的公共部分：OKLCH 换算、取预设配色、色阶、模型惯用色清单、按用途归类。

被 recolor.py、palette.py、audit.py 共用。单独运行没有作用。
"""
from __future__ import annotations

import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from contrast import parse_color  # noqa: E402

# ---------------------------------------------------------------- 换算

def srgb_to_oklch(r: float, g: float, b: float) -> tuple[float, float, float]:
    def lin(v):
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = lin(r), lin(g), lin(b)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(x) ** (1 / 3), x) for x in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def _oklch_to_linear(L, C, H):
    h = math.radians(H)
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def oklch_to_srgb(L: float, C: float, H: float) -> tuple[float, float, float]:
    """超出 sRGB 时降彩度，保住明度与色相。"""
    def ok(c):
        return all(-1e-4 <= v <= 1 + 1e-4 for v in _oklch_to_linear(L, c, H))
    if not ok(C):
        lo, hi = 0.0, C
        for _ in range(24):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if ok(mid) else (lo, mid)
        C = lo
    def gam(v):
        v = min(1.0, max(0.0, v))
        return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055
    return tuple(gam(v) for v in _oklch_to_linear(L, C, H))


def hex_of(rgb: tuple[float, float, float]) -> str:
    return "#" + "".join(f"{round(min(1, max(0, v)) * 255):02X}" for v in rgb)


NAMED = {
    "black": "#000000", "white": "#FFFFFF", "red": "#FF0000", "green": "#008000", "blue": "#0000FF",
    "yellow": "#FFFF00", "orange": "#FFA500", "purple": "#800080", "pink": "#FFC0CB", "gray": "#808080",
    "grey": "#808080", "silver": "#C0C0C0", "navy": "#000080", "teal": "#008080", "aqua": "#00FFFF",
    "cyan": "#00FFFF", "magenta": "#FF00FF", "fuchsia": "#FF00FF", "lime": "#00FF00", "maroon": "#800000",
    "olive": "#808000", "violet": "#EE82EE", "indigo": "#4B0082", "gold": "#FFD700", "crimson": "#DC143C",
    "tomato": "#FF6347", "coral": "#FF7F50", "royalblue": "#4169E1", "dodgerblue": "#1E90FF",
    "deepskyblue": "#00BFFF", "skyblue": "#87CEEB", "lightgray": "#D3D3D3", "lightgrey": "#D3D3D3",
    "darkgray": "#A9A9A9", "darkgrey": "#A9A9A9", "dimgray": "#696969", "whitesmoke": "#F5F5F5",
    "gainsboro": "#DCDCDC", "slategray": "#708090", "steelblue": "#4682B4", "blueviolet": "#8A2BE2",
    "mediumpurple": "#9370DB", "rebeccapurple": "#663399", "hotpink": "#FF69B4", "deeppink": "#FF1493",
    "limegreen": "#32CD32", "forestgreen": "#228B22", "seagreen": "#2E8B57", "darkblue": "#00008B",
    "darkred": "#8B0000", "darkgreen": "#006400", "lightblue": "#ADD8E6", "beige": "#F5F5DC",
}


def to_rgba(text: str) -> tuple[float, float, float, float] | None:
    t = text.strip().lower()
    if t in NAMED:
        t = NAMED[t]
    try:
        r, g, b, a, _ = parse_color(t)
    except Exception:
        return None
    return r, g, b, (1.0 if a is None else a)


# ---------------------------------------------------------------- 模型惯用色

# 模型不假思索时最常写出的颜色：框架默认蓝、Tailwind 的靛蓝紫、教程里的紫色渐变、纯原色。
# 它们本身不一定难看，难看在于与题材无关、千篇一律、饱和度过高或冷暖打架。
MODEL_DEFAULTS = {
    "#007BFF": "Bootstrap 4 主色", "#0D6EFD": "Bootstrap 5 主色", "#1890FF": "Ant Design 4 主色",
    "#1677FF": "Ant Design 5 主色", "#409EFF": "Element 主色", "#2196F3": "Material 蓝",
    "#3F51B5": "Material 靛蓝", "#673AB7": "Material 深紫", "#9C27B0": "Material 紫", "#E91E63": "Material 粉",
    "#3B82F6": "Tailwind blue-500", "#2563EB": "Tailwind blue-600", "#1D4ED8": "Tailwind blue-700",
    "#60A5FA": "Tailwind blue-400", "#6366F1": "Tailwind indigo-500", "#4F46E5": "Tailwind indigo-600",
    "#4338CA": "Tailwind indigo-700", "#818CF8": "Tailwind indigo-400", "#8B5CF6": "Tailwind violet-500",
    "#7C3AED": "Tailwind violet-600", "#A855F7": "Tailwind purple-500", "#9333EA": "Tailwind purple-600",
    "#C084FC": "Tailwind purple-400", "#EC4899": "Tailwind pink-500", "#DB2777": "Tailwind pink-600",
    "#06B6D4": "Tailwind cyan-500", "#0EA5E9": "Tailwind sky-500", "#14B8A6": "Tailwind teal-500",
    "#10B981": "Tailwind emerald-500", "#22C55E": "Tailwind green-500", "#EF4444": "Tailwind red-500",
    "#F59E0B": "Tailwind amber-500", "#F97316": "Tailwind orange-500", "#EAB308": "Tailwind yellow-500",
    "#667EEA": "教程紫色渐变起点", "#764BA2": "教程紫色渐变终点", "#6A11CB": "教程紫色渐变",
    "#2575FC": "教程蓝紫渐变", "#FF6B6B": "教程珊瑚红", "#4ECDC4": "教程青绿", "#45B7D1": "教程天蓝",
    "#F093FB": "教程粉紫渐变", "#F5576C": "教程粉红渐变", "#4FACFE": "教程蓝色渐变", "#00F2FE": "教程青色渐变",
    "#FF0000": "纯红", "#00FF00": "纯绿", "#0000FF": "纯蓝", "#FFFF00": "纯黄", "#FF00FF": "纯品红",
    "#00FFFF": "纯青", "#008000": "CSS green", "#800080": "CSS purple", "#FFA500": "CSS orange",
    "#1E293B": "Tailwind slate-800", "#0F172A": "Tailwind slate-900", "#334155": "Tailwind slate-700",
    "#64748B": "Tailwind slate-500", "#94A3B8": "Tailwind slate-400", "#E2E8F0": "Tailwind slate-200",
    "#F1F5F9": "Tailwind slate-100", "#F8FAFC": "Tailwind slate-50", "#111827": "Tailwind gray-900",
    "#1F2937": "Tailwind gray-800", "#374151": "Tailwind gray-700", "#6B7280": "Tailwind gray-500",
    "#9CA3AF": "Tailwind gray-400", "#E5E7EB": "Tailwind gray-200", "#F3F4F6": "Tailwind gray-100",
    "#F9FAFB": "Tailwind gray-50", "#18181B": "Tailwind zinc-900", "#27272A": "Tailwind zinc-800",
}
TAILWIND_FAMILIES = ("slate", "gray", "zinc", "neutral", "stone", "red", "orange", "amber", "yellow", "lime", "green",
                     "emerald", "teal", "cyan", "sky", "blue", "indigo", "violet", "purple", "fuchsia", "pink", "rose")
TAILWIND_CLASS = re.compile(
    r"(?<![\w-])(?:[a-z0-9-]+:)*(?:bg|text|border|from|via|to|ring|outline|fill|stroke|divide|decoration|shadow|accent|caret|placeholder)"
    r"-(" + "|".join(TAILWIND_FAMILIES) + r")-(50|[1-9]00|950)(?:/\d+)?(?![\w-])")


def model_default_name(rgba) -> str | None:
    """完全命中清单，或是高饱和的靛蓝紫（模型最爱、与题材最无关的一族）。"""
    r, g, b, a = rgba
    h = hex_of((r, g, b))
    if h in MODEL_DEFAULTS:
        return MODEL_DEFAULTS[h]
    L, C, H = srgb_to_oklch(r, g, b)
    if C > 0.15 and 265 <= H <= 310 and 0.4 < L < 0.75:
        return "高饱和靛蓝紫"
    if C > 0.24:
        return "接近纯色的高饱和色"
    return None


# ---------------------------------------------------------------- 预设配色

def _split_top(s: str) -> list[str]:
    out, depth, cur = [], 0, ""
    for ch in s:
        depth += ch == "("
        depth -= ch == ")"
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return out


def _vars(block: str) -> tuple[dict, dict]:
    light, dark = {}, {}
    for name, val in re.findall(r"--([\w-]+)\s*:\s*([^;]+);", block):
        val = val.strip()
        m = re.match(r"light-dark\((.*)\)$", val)
        if m:
            parts = _split_top(m.group(1))
            if len(parts) == 2:
                light[name], dark[name] = parts
        elif re.match(r"(#|oklch\(|rgb|hsl)", val):
            light[name] = dark[name] = val
    return light, dark


ROLES = ["bg", "surface", "surface-raised", "surface-sunken", "border", "border-strong", "text", "text-muted",
         "text-subtle", "text-faint", "accent", "accent-fg", "accent-text", "accent-subtle", "stage", "stage-ink",
         "stage-muted", "ok", "ok-soft", "warn", "warn-soft", "danger", "danger-soft"]


def preset_roles(style: str, accent: str | None = None, neutral: str | None = None) -> tuple[dict, dict]:
    """返回 (浅色, 暗色) 两套角色色值（原始写法，可能是 oklch / hex / 带透明度）。"""
    css = open(os.path.join(ROOT, "assets", "styles.css"), encoding="utf-8").read()
    m = re.search(r"\.style-" + re.escape(style) + r"\s*\{(.*?)\n\}", css, re.S)
    if not m:
        names = re.findall(r"\.style-([a-z-]+)\s*\{", css)
        raise SystemExit(f"没有叫 {style} 的预设。可用的：{', '.join(names)}")
    light, dark = _vars(m.group(1))
    ui = open(os.path.join(ROOT, "assets", "ui.css"), encoding="utf-8").read()
    root = re.search(r":root\s*\{(.*?)\n\}", ui, re.S)
    if root:
        l2, d2 = _vars(root.group(1))
        for k in ("ok", "ok-soft", "warn", "warn-soft", "danger", "danger-soft"):
            if k in l2:
                light[k], dark[k] = l2[k], d2[k]
    if accent:
        import palette
        H, C, pl, pd, stage = palette.build(accent, neutral or "warm")
        keys = ["accent", "accent-fg", "accent-text", "accent-subtle"]
        if neutral:
            keys += ["bg", "surface", "surface-sunken", "border", "border-strong", "text", "text-muted", "text-subtle", "text-faint"]
        for k in keys:
            light[k], dark[k] = pl[k], pd[k]
        if neutral:
            # 浮起表面跟着新的中性色走：浅色同表面，暗色比表面亮一点
            light["surface-raised"] = pl["surface"]
            r1, g1, b1, _ = to_rgba(pd["surface"]); r2, g2, b2, _ = to_rgba(pd["text"])
            dark["surface-raised"] = hex_of((r1 * .94 + r2 * .06, g1 * .94 + g2 * .06, b1 * .94 + b2 * .06))
        for k in ("stage", "stage-ink", "stage-muted"):
            light[k] = dark[k] = stage[k]
    for d in (light, dark):
        d.setdefault("surface-raised", d.get("surface", "#FFFFFF"))
    return light, dark


def concrete(value: str) -> str:
    """把 oklch / 带透明度的写法换成到处能用的 hex 或 rgba()。"""
    rgba = to_rgba(value)
    if not rgba:
        return value
    r, g, b, a = rgba
    if a >= 0.999:
        return hex_of((r, g, b))
    return f"rgba({round(r * 255)}, {round(g * 255)}, {round(b * 255)}, {a:.2f})"


# ---------------------------------------------------------------- 色阶

STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
_L = [0.975, 0.945, 0.89, 0.82, 0.73, 0.645, 0.56, 0.48, 0.405, 0.335, 0.265]
_CK = [0.10, 0.20, 0.40, 0.65, 0.88, 1.0, 1.0, 0.92, 0.80, 0.66, 0.52]


def green_hue(hue: float) -> bool:
    return 118 <= round(hue) % 360 <= 193


def visible_ink_green(rgba) -> bool:
    if not rgba or rgba[3] < 0.999:
        return False
    lightness, chroma, hue = srgb_to_oklch(*rgba[:3])
    return round(lightness, 3) <= 0.56 and chroma >= 0.016 and green_hue(hue)


def theme_tone(lightness: float, chroma: float, hue: float) -> tuple[float, float, float]:
    """Map deep green in authored colours to a slate of the same lightness."""
    if round(lightness, 3) <= 0.56 and green_hue(hue):
        return lightness, min(chroma, 0.020), 260
    return lightness, chroma, hue


def theme_hex(rgb: tuple[float, float, float]) -> str:
    original = srgb_to_oklch(*rgb)
    authored = theme_tone(*original)
    return hex_of(rgb if authored == original else oklch_to_srgb(*authored))


def theme_mix(foreground: str, background: str, amount: float) -> str:
    """Check the displayed sRGB mixture as well as its endpoints."""
    fg, bg = to_rgba(foreground), to_rgba(background)
    return theme_hex(tuple(f * amount + b * (1 - amount) for f, b in zip(fg[:3], bg[:3])))


def layer_color(color: str) -> str:
    """A source for deep gradients and translucent overlays on varied backdrops."""
    lightness, chroma, hue = srgb_to_oklch(*to_rgba(color)[:3])
    if chroma > 0.004 and green_hue(hue):
        return hex_of(oklch_to_srgb(lightness, min(chroma, 0.065), 260))
    return color


def ramp(color: str, neutral: bool = False) -> dict[int, str]:
    """从一个颜色生成 50–950 的 11 级色阶（hex）。neutral=True 时只保留一点色温。"""
    r, g, b, _ = to_rgba(color)
    _, C, H = srgb_to_oklch(r, g, b)
    if neutral:
        C = min(C, 0.012)
    else:
        C = max(0.05, min(C, 0.2))
    return {step: hex_of(oklch_to_srgb(*theme_tone(level, C * weight, H)))
            for step, level, weight in zip(STEPS, _L, _CK)}


# ---------------------------------------------------------------- 按用途归类

def is_neutral(L: float, C: float) -> bool:
    """带一点色温的灰（Tailwind slate、zinc）也算中性；极浅极深时彩度门槛更低，淡蓝浅底仍算强调色一族。"""
    return C < (0.02 if (L > 0.88 or L < 0.2) else 0.06)


def family(rgba) -> str:
    """neutral / red / green / yellow / blue（其余色相都归 blue，当作强调色一族）。"""
    r, g, b, a = rgba
    L, C, H = srgb_to_oklch(r, g, b)
    if is_neutral(L, C):
        return "neutral"
    if H < 40 or H >= 345:
        return "red"
    if 55 <= H < 110:
        return "yellow"
    if 125 <= H < 175:
        return "green"
    return "blue"


def role_for(rgba, prop: str, dark_page: bool, accent_family: str) -> str | None:
    """按颜色本身的明度彩度 + 它用在什么属性上，决定换成哪个角色。返回 None 表示保留原样。"""
    r, g, b, a = rgba
    L, C, H = srgb_to_oklch(r, g, b)
    fam = family(rgba)
    if a < 0.999 and fam == "neutral":
        return None                                   # 半透明黑白：投影、遮罩、高光，保留
    if prop == "shadow":
        return None if fam == "neutral" else "shadow"
    if fam == "neutral":
        if prop == "border":
            if dark_page:
                return "border" if L < 0.35 else "border-strong"
            return "border" if L > 0.86 else "border-strong"
        if prop == "bg":
            if dark_page:
                if L < 0.2:
                    return "bg"
                if L < 0.27:
                    return "surface"
                if L < 0.4:
                    return "surface-raised"
                return "text" if L > 0.85 else "border-strong"
            if L >= 0.985:
                return "surface"
            if L >= 0.94:
                return "bg"
            if L >= 0.8:
                return "surface-sunken"
            if L < 0.32:
                return "stage"
            return "border-strong"
        # 文字与其他
        if dark_page:
            if L > 0.85:
                return "text"
            if L > 0.7:
                return "text-muted"
            if L > 0.55:
                return "text-subtle"
            return "bg" if L < 0.22 else "text-faint"
        if L > 0.95:
            return "accent-fg"                        # 浅底页面上的白字，多半压在彩色按钮上
        if L < 0.36:
            return "text"
        if L < 0.55:
            return "text-muted"
        if L < 0.8:
            return "text-subtle"                      # 说明文字要达标；--text-faint 只给装饰性的线和刻度
        return "text-faint"
    # 有彩色：页面里最多的那一族当作品牌强调色，其余按语义
    group = "accent" if fam == accent_family or fam == "blue" else {"red": "danger", "green": "ok", "yellow": "warn"}[fam]
    light_tone = L > (0.3 if dark_page else 0.86)
    if group == "accent":
        if prop == "text":
            return "accent-text"
        if prop == "bg" and ((L > 0.86 and not dark_page) or (dark_page and L < 0.32)):
            return "accent-subtle"
        return "accent"
    if prop == "bg" and ((light_tone and not dark_page) or (dark_page and L < 0.32)):
        return group + "-soft"
    return group
