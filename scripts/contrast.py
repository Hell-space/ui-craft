#!/usr/bin/env python3
"""WCAG 对比度检查。

用法:
  python contrast.py <前景色> <背景色>
  python contrast.py --tokens tokens.css [--pair text:bg ...] [--strict]

支持的颜色写法: #rgb / #rrggbb / #rrggbbaa / rgb() / rgba() / hsl() / oklch() / black / white。
前景带透明度时会先叠到背景上再计算。

--tokens 模式: 解析 CSS 自定义属性（支持 var()、light-dark()、纯数字 calc()、
[data-theme="dark"] 与 prefers-color-scheme: dark 覆盖），按约定的角色变量名
（--text / --bg / --surface / --accent ...，见 assets/tokens.css）在明暗两套主题下
检查常见的 前景/背景 配对。变量名不同的项目用 --pair 前景变量:背景变量[:阈值] 指定。
"""
from __future__ import annotations

import argparse
import math
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# ---------------------------------------------------------------- 颜色解析

def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _num(tok: str, scale: float = 1.0) -> float:
    """解析数字或百分比。scale 为百分比 100% 对应的数值。"""
    tok = tok.strip()
    if tok == "none":
        return 0.0
    if tok.endswith("%"):
        return float(tok[:-1]) / 100.0 * scale
    return float(re.sub(r"(deg|turn|rad)$", "", tok))


def _split_args(body: str) -> tuple[list[str], str | None]:
    """把 'L C H / A' 或 'r, g, b, a' 拆成分量与 alpha。"""
    alpha = None
    if "/" in body:
        body, alpha = body.rsplit("/", 1)
        alpha = alpha.strip()
    parts = [p for p in re.split(r"[,\s]+", body.strip()) if p]
    if alpha is None and len(parts) == 4:
        alpha = parts.pop()
    return parts, alpha


def _oklch_to_srgb(L: float, C: float, H: float) -> tuple[float, float, float, bool]:
    a = C * math.cos(math.radians(H))
    b = C * math.sin(math.radians(H))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    lin = (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )
    out_of_gamut = any(v < -0.002 or v > 1.002 for v in lin)

    def gamma(v: float) -> float:
        v = _clamp01(v)
        return 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055

    return gamma(lin[0]), gamma(lin[1]), gamma(lin[2]), out_of_gamut


def _hsl_to_srgb(h: float, s: float, l: float) -> tuple[float, float, float]:
    h = (h % 360) / 360.0

    def hue(p: float, q: float, t: float) -> float:
        t %= 1.0
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    if s == 0:
        return l, l, l
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    return hue(p, q, h + 1 / 3), hue(p, q, h), hue(p, q, h - 1 / 3)


class ColorError(ValueError):
    pass


def parse_color(text: str) -> tuple[float, float, float, float, bool]:
    """返回 (r, g, b, a, out_of_gamut)，分量为 0–1 的 sRGB。"""
    s = text.strip().lower().rstrip(";")
    if s in ("black",):
        return 0.0, 0.0, 0.0, 1.0, False
    if s in ("white",):
        return 1.0, 1.0, 1.0, 1.0, False
    if s == "transparent":
        return 0.0, 0.0, 0.0, 0.0, False

    m = re.fullmatch(r"#([0-9a-f]{3,8})", s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8):
            raise ColorError(f"无法解析的十六进制颜色: {text}")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1.0
        return r, g, b, a, False

    m = re.fullmatch(r"(rgba?|hsla?|oklch)\((.*)\)", s)
    if not m:
        raise ColorError(f"不支持的颜色写法: {text}")
    fn, body = m.group(1), m.group(2)
    parts, alpha = _split_args(body)
    if len(parts) != 3:
        raise ColorError(f"颜色分量数量不对: {text}")
    try:
        a = _clamp01(_num(alpha, 1.0)) if alpha is not None else 1.0
        if fn.startswith("rgb"):
            r, g, b = (_clamp01(_num(p, 255.0) / 255.0) for p in parts)
            return r, g, b, a, False
        if fn.startswith("hsl"):
            r, g, b = _hsl_to_srgb(_num(parts[0]), _clamp01(_num(parts[1], 1.0)), _clamp01(_num(parts[2], 1.0)))
            return r, g, b, a, False
        L = _num(parts[0], 1.0)
        C = _num(parts[1], 0.4)
        H = _num(parts[2])
        r, g, b, oog = _oklch_to_srgb(L, C, H)
        return r, g, b, a, oog
    except ValueError as exc:
        raise ColorError(f"无法解析: {text} ({exc})") from exc


def luminance(rgb: tuple[float, float, float]) -> float:
    def lin(v: float) -> float:
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg_text: str, bg_text: str) -> tuple[float, list[str]]:
    notes: list[str] = []
    fr, fg, fb, fa, foog = parse_color(fg_text)
    br, bg, bb, ba, boog = parse_color(bg_text)
    if ba < 1:
        # 背景半透明时假设其下是白色，并提醒
        br, bg, bb = (c * ba + (1 - ba) for c in (br, bg, bb))
        notes.append("背景带透明度，已按叠在白色上估算")
    if fa < 1:
        fr, fg, fb = (f * fa + b * (1 - fa) for f, b in ((fr, br), (fg, bg), (fb, bb)))
        notes.append("前景带透明度，已叠到背景上计算")
    if foog or boog:
        notes.append("颜色超出 sRGB 色域，已截断，结果为近似值")
    l1, l2 = luminance((fr, fg, fb)), luminance((br, bg, bb))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05), notes


def grade(ratio: float) -> str:
    if ratio >= 7:
        return "AAA 正文"
    if ratio >= 4.5:
        return "AA 正文"
    if ratio >= 3:
        return "仅大字/控件 (3:1)"
    return "不达标"


# ---------------------------------------------------------------- tokens 解析

def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def parse_custom_props(css: str) -> tuple[dict[str, str], dict[str, str]]:
    """返回 (基础/浅色声明, 暗色覆盖声明)。"""
    css = _strip_comments(css)
    base: dict[str, str] = {}
    dark: dict[str, str] = {}
    stack: list[str] = []
    buf = ""
    depth_paren = 0
    for ch in css:
        if ch == "(":
            depth_paren += 1
        elif ch == ")":
            depth_paren = max(0, depth_paren - 1)
        if ch == "{" and depth_paren == 0:
            stack.append(buf.strip().lower())
            buf = ""
        elif ch in ";}" and depth_paren == 0:
            decl = buf.strip()
            buf = ""
            m = re.match(r"(--[\w-]+)\s*:\s*(.+)$", decl, flags=re.S)
            if m:
                name, value = m.group(1), " ".join(m.group(2).split())
                is_dark = any("dark" in p for p in stack)
                target = dark if is_dark else base
                target.setdefault(name, value)
            if ch == "}" and stack:
                stack.pop()
        else:
            buf += ch
    return base, dark


def _find_call(text: str, fn: str) -> tuple[int, int, str] | None:
    """找到第一个 fn(...) 调用，返回 (起点, 终点, 括号内文本)。"""
    for m in re.finditer(r"(?<![\w-])" + re.escape(fn) + r"\(", text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += text[i] == "("
            depth -= text[i] == ")"
            i += 1
        if depth == 0:
            return m.start(), i, text[m.end():i - 1]
    return None


def _split_top(body: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    return parts


def resolve(name: str, theme: str, base: dict[str, str], dark: dict[str, str], _seen: tuple[str, ...] = ()) -> str:
    if name in _seen:
        raise ColorError(f"变量循环引用: {name}")
    value = dark.get(name) if theme == "dark" else None
    if value is None:
        value = base.get(name)
    if value is None:
        raise KeyError(name)
    return _expand(value, theme, base, dark, _seen + (name,))


def _expand(value: str, theme: str, base: dict[str, str], dark: dict[str, str], seen: tuple[str, ...]) -> str:
    # var()
    while True:
        call = _find_call(value, "var")
        if not call:
            break
        start, end, body = call
        args = _split_top(body)
        try:
            rep = resolve(args[0], theme, base, dark, seen)
        except KeyError:
            if len(args) > 1:
                rep = _expand(",".join(args[1:]), theme, base, dark, seen)
            else:
                raise ColorError(f"未定义的变量: {args[0]}")
        value = value[:start] + rep + value[end:]
    # light-dark()
    while True:
        call = _find_call(value, "light-dark")
        if not call:
            break
        start, end, body = call
        args = _split_top(body)
        if len(args) != 2:
            raise ColorError(f"light-dark() 需要两个参数: {body}")
        value = value[:start] + (args[1] if theme == "dark" else args[0]) + value[end:]
    # calc()：只处理纯数字表达式
    while True:
        call = _find_call(value, "calc")
        if not call:
            break
        start, end, body = call
        if not re.fullmatch(r"[\d\s.+\-*/()]+", body):
            raise ColorError(f"无法求值的 calc(): {body}")
        result = eval(body, {"__builtins__": {}}, {})  # noqa: S307  已限制为纯算术字符
        value = value[:start] + f"{result:.6g}" + value[end:]
    return value.strip()


TEXT_VARS = ["--text", "--text-muted", "--text-subtle"]
SURFACE_VARS = ["--bg", "--surface", "--surface-raised", "--surface-sunken"]
SEMANTIC = ["success", "warning", "danger", "info"]


def default_pairs(names: set[str]) -> list[tuple[str, str, float]]:
    pairs: list[tuple[str, str, float]] = []
    for t in TEXT_VARS:
        for s in SURFACE_VARS:
            pairs.append((t, s, 4.5))
    pairs += [
        ("--accent-fg", "--accent", 4.5),
        ("--accent-text", "--bg", 4.5),
        ("--accent-text", "--surface", 4.5),
        ("--accent-text", "--accent-subtle", 4.5),
        ("--accent", "--bg", 3.0),
        ("--focus-ring", "--bg", 3.0),
        ("--focus-ring", "--surface", 3.0),
        ("--border-control", "--bg", 3.0),
        ("--border-control", "--surface", 3.0),
    ]
    for k in SEMANTIC:
        pairs.append((f"--{k}-text", f"--{k}-subtle", 4.5))
        pairs.append((f"--{k}-text", "--surface", 4.5))
    return [(f, b, th) for f, b, th in pairs if f in names and b in names]


def check_tokens(path: str, extra_pairs: list[str], strict: bool) -> int:
    with open(path, encoding="utf-8") as fh:
        base, dark = parse_custom_props(fh.read())
    names = set(base) | set(dark)
    pairs = default_pairs(names)
    for spec in extra_pairs:
        bits = spec.split(":")
        if len(bits) < 2:
            print(f"忽略无法识别的 --pair: {spec}")
            continue
        fg, bg = ("--" + b.lstrip("-") for b in bits[:2])
        th = float(bits[2]) if len(bits) > 2 else 4.5
        pairs.append((fg, bg, th))
    if not pairs:
        print("没有找到可检查的配对。变量名与约定不同的话，用 --pair 前景:背景[:阈值] 指定。")
        return 0

    has_dark = bool(dark) or any("light-dark(" in v for v in base.values())
    themes = ["light", "dark"] if has_dark else ["light"]
    failures = 0
    for theme in themes:
        label = "浅色主题" if theme == "light" else "暗色主题"
        print(f"\n== {label} ==")
        print(f"{'前景':<20}{'背景':<20}{'比值':>7}  {'要求':>5}  结果")
        for fg, bg, th in pairs:
            try:
                fv = resolve(fg, theme, base, dark)
                bv = resolve(bg, theme, base, dark)
                ratio, notes = contrast(fv, bv)
            except (ColorError, KeyError) as exc:
                print(f"{fg:<20}{bg:<20}{'—':>7}  {th:>5}  跳过（{exc}）")
                continue
            ok = ratio >= th
            failures += not ok
            mark = "通过" if ok else "不达标 ←"
            tail = f"  （{'；'.join(notes)}）" if notes else ""
            print(f"{fg:<20}{bg:<20}{ratio:>6.2f}:1  {th:>5}  {mark}{tail}")
    print(f"\n共 {len(pairs) * len(themes)} 项，{failures} 项不达标。")
    return 1 if (failures and strict) else 0


# ---------------------------------------------------------------- CLI

def main() -> int:
    ap = argparse.ArgumentParser(description="WCAG 对比度检查")
    ap.add_argument("colors", nargs="*", help="前景色 背景色")
    ap.add_argument("--tokens", help="检查一个 CSS 文件里的角色变量配对")
    ap.add_argument("--pair", action="append", default=[], help="额外配对: 前景变量:背景变量[:阈值]")
    ap.add_argument("--strict", action="store_true", help="有不达标项时以退出码 1 结束")
    args = ap.parse_args()

    if args.tokens:
        return check_tokens(args.tokens, args.pair, args.strict)

    if len(args.colors) != 2:
        ap.print_help()
        return 2
    try:
        ratio, notes = contrast(args.colors[0], args.colors[1])
    except ColorError as exc:
        print(f"错误: {exc}")
        return 2
    print(f"对比度 {ratio:.2f}:1  →  {grade(ratio)}")
    print(f"  正文 AA (4.5:1): {'通过' if ratio >= 4.5 else '不通过'}")
    print(f"  大字/控件 (3:1): {'通过' if ratio >= 3 else '不通过'}")
    print(f"  正文 AAA (7:1):  {'通过' if ratio >= 7 else '不通过'}")
    for n in notes:
        print(f"  注: {n}")
    return 1 if (args.strict and ratio < 4.5) else 0


if __name__ == "__main__":
    sys.exit(main())
