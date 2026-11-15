#!/usr/bin/env python3
"""把代码里模型自己挑的颜色，按用途换成调好的配色。

用法:
  python recolor.py 页面.html                          # 只预览：列出每个颜色会换成什么，不改文件
  python recolor.py src/ --accent "#365899" --write    # 整个目录换色（先备份到 .ui-craft-backup/）
  python recolor.py app/ --style midnight --write      # 换成某套预设的配色
  python recolor.py ui/ --to hex --write               # 写死成十六进制（Qt / WPF / tkinter / SCSS / 邮件）
  python recolor.py src/ --only-defaults --write       # 只换"模型惯用色"，其他颜色不动
  python recolor.py src/ --keep "#C8102E" --write      # 保护品牌色不被换掉

它做的事：
  1. 找出每一处颜色：#hex、rgb()/hsl()/oklch()、CSS 颜色名，以及 Tailwind 的 bg-[#…] 写法。
  2. 看这个颜色用在哪：背景、文字、边框、渐变、投影，以及它自己的明暗与彩度。
  3. 换成对应的角色：近白的背景 → 表面色，深灰文字 → 主文字色，灰边 → 线色，
     页面里最多的那一族彩色 → 强调色，红/绿/黄 → 危险/成功/警告，渐变 → 同一色相的深浅变化。
  4. 网页默认写成 var(--…)，并在 HTML 里注入一段配色变量（项目已经引入 ui-craft.css 时不注入）；
     SCSS/LESS、桌面与引擎文件自动写成十六进制。

不会动的：半透明的黑白（投影、遮罩、高光）、<svg> 里的插画颜色（加 --include-svg 才换）、
ui-craft.css / ui-craft.js、node_modules 等目录。
Tailwind 的 bg-indigo-600 这类类名不在这里改：用 palette.py --export tailwind 覆盖调色板，类名原样生效。
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import colorkit as ck  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WEB = {".html", ".htm", ".css", ".vue", ".svelte", ".astro", ".jsx", ".tsx", ".js", ".ts", ".mjs"}
HEX_ONLY = {".scss", ".sass", ".less", ".qss", ".xaml", ".axaml", ".ui", ".py", ".gd", ".tscn", ".tres", ".cs", ".kt", ".swift", ".dart"}
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", ".next", ".nuxt", "vendor", "__pycache__", ".venv", "venv",
             ".ui-craft-backup", "bin", "obj", ".godot", ".import"}
SKIP_FILES = {"ui-craft.css", "ui-craft.js", "ui-craft-colors.css"}

COLOR = re.compile(
    r"(?<![\w&#-])#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9a-zA-Z_-])"
    r"|(?<![\w-])(?:rgba?|hsla?|oklch)\([^()]*\)", re.I)
NAMED_RE = re.compile(r"(?<=[:=\s'\"(,])(" + "|".join(sorted(ck.NAMED, key=len, reverse=True)) + r")(?=\s*[;'\"),}\n!]|\s+!)", re.I)
GRADIENT = re.compile(r"(?:repeating-)?(?:linear|radial|conic)-gradient\(", re.I)

PROP = re.compile(r"([A-Za-z-]+|--[\w-]+)\s*[:=]\s*['\"]?[^;:{}=\n]*$")
TW_ARB = re.compile(r"(?<![\w-])(bg|text|border|from|via|to|ring|outline|fill|stroke|divide|decoration|shadow|accent|caret)-\[$")


def kind_of(prop: str) -> str:
    p = re.sub(r"([a-z])([A-Z])", r"\1-\2", prop).lower()
    if "shadow" in p or p in ("filter",):
        return "shadow"
    if p.startswith("--"):
        if re.search(r"bg|background|surface|canvas|panel|card|fill", p):
            return "bg"
        if re.search(r"border|line|divider|stroke|outline|ring", p):
            return "border"
        if re.search(r"text|fg|foreground|ink|font|heading|muted|label", p):
            return "text"
        return "other"
    if re.match(r"(background|bg|bgcolor|fill|stop-color|from|via|to|accent)", p):
        return "bg"
    if re.match(r"(border|outline|stroke|divide|ring|column-rule|text-decoration|decoration)", p):
        return "border"
    if re.match(r"(color|text|caret|-webkit-text-fill|placeholder|foreground)", p):
        return "text"
    return "other"


def spans(pattern: re.Pattern, text: str) -> list[tuple[int, int]]:
    out = []
    for m in pattern.finditer(text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += text[i] == "("
            depth -= text[i] == ")"
            i += 1
        out.append((m.start(), i))
    return out


def svg_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r"<svg\b.*?</svg>", text, re.S | re.I)]


def inside(pos: int, ranges) -> tuple[int, int] | None:
    for a, b in ranges:
        if a <= pos < b:
            return a, b
    return None


def find_colors(text: str, ext: str, include_svg: bool):
    """返回 [(start, end, 原文, rgba, 用途, 渐变区间)]。"""
    grads = spans(GRADIENT, text)
    svgs = [] if include_svg or ext not in (".html", ".htm", ".vue", ".svelte", ".astro", ".jsx", ".tsx") else svg_spans(text)
    code = ext in (".js", ".ts", ".mjs", ".jsx", ".tsx", ".py", ".cs", ".kt", ".swift", ".dart", ".gd")
    found = []
    seen = set()
    for m in list(COLOR.finditer(text)) + list(NAMED_RE.finditer(text)):
        s, e, raw = m.start(), m.end(), m.group(0)
        if s in seen or inside(s, svgs):
            continue
        before = text[max(0, s - 100):s]
        line = before.split("\n")[-1]
        if re.search(r"(href|src|url|xlink:href|querySelector(All)?|getElementById)\s*[=(]\s*['\"]?$", line):
            continue
        is_named = not raw.startswith("#") and "(" not in raw
        rgba = ck.to_rgba(raw)
        if not rgba:
            continue
        g = inside(s, grads)
        tw = TW_ARB.search(line)
        pm = PROP.search(line)
        if g:
            prop = "bg"
        elif tw:
            prop = kind_of(tw.group(1))
        elif pm:
            prop = kind_of(pm.group(1))
        else:
            prop = None
        if prop is None:
            # 代码文件里只认带引号的完整色值，避免把 '#face' 这类 id 当成颜色
            quoted = re.search(r"['\"`]$", line) and text[e:e + 1] in "'\"`"
            if is_named or not (quoted and (raw.startswith("#") and len(raw) in (7, 9) or "(" in raw)):
                if code or is_named or ext in (".html", ".htm"):
                    continue
            prop = "other"
        if is_named and not pm:
            continue
        seen.add(s)
        found.append((s, e, raw, rgba, prop, g))
    found.sort()
    return found


def page_tone(items, forced: str) -> bool:
    if forced in ("light", "dark"):
        return forced == "dark"
    dark = light = 0
    for _, _, _, (r, g, b, a), prop, _ in items:
        if prop != "bg" or a < 0.999:
            continue
        L, C, _ = ck.srgb_to_oklch(r, g, b)
        if C < 0.035:
            dark += L < 0.3
            light += L > 0.85
    return dark > light


def accent_family(items) -> str:
    c = Counter(ck.family(it[3]) for it in items)
    c.pop("neutral", None)
    return c.most_common(1)[0][0] if c else "blue"


def replacement(role: str, rgba, mode: str, roles: dict, grad_index: int, shade: str) -> str:
    alpha = rgba[3]
    if role == "shadow":
        return f"rgb(var(--shade, {shade}) / .18)" if mode == "vars" else f"rgba({', '.join(str(int(x)) for x in shade.split())}, 0.18)"
    if grad_index >= 0 and role.startswith("accent"):
        # 彩色渐变（多是首屏大背景）→ 深色舞台，越往后越带一点强调色；按钮、链接仍用强调色，不会融进背景
        pct = min(40, 14 * grad_index)
        if mode == "vars":
            return "var(--stage)" if pct == 0 else f"color-mix(in srgb, var(--accent-layer) {pct}%, var(--stage))"
        return ck.theme_mix(ck.layer_color(roles["accent"]), roles["stage"], pct / 100)
    if mode == "vars":
        if alpha < 0.999:
            token = "accent-layer" if role == "accent" else role
            return f"color-mix(in srgb, var(--{token}) {round(alpha * 100)}%, transparent)"
        return f"var(--{role})"
    value = ck.concrete(roles[role])
    if alpha < 0.999:
        if role == "accent":
            value = ck.layer_color(value)
        r, g, b, _ = ck.to_rgba(value)
        return f"rgba({round(r * 255)}, {round(g * 255)}, {round(b * 255)}, {alpha:.2f})"
    return value


def tokens_css(light: dict, dark: dict, dark_page: bool, shade: str, style: str, accent: str | None) -> str:
    lines = [f"/* ui-craft 配色（recolor.py 生成，预设 {style}" + (f"，强调色 {accent}" if accent else "") + "）。不要手改，要换配色重新运行 recolor.py。 */",
             ":root {", f"  color-scheme: {'dark' if dark_page else 'light'};", f"  --shade: {shade};"]
    for k in ck.ROLES:
        if k in light:
            lines.append(f"  --{k}: light-dark({light[k]}, {dark[k]});" if light[k] != dark[k] else f"  --{k}: {light[k]};")
    lines.append(f"  --accent-layer: light-dark({ck.layer_color(light['accent'])}, {ck.layer_color(dark['accent'])});")
    lines.append("}")
    return "\n".join(lines) + "\n"


def collect(paths):
    out = []
    for p in paths:
        if os.path.isfile(p):
            out.append(p)
            continue
        for root, dirs, names in os.walk(p):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for n in names:
                ext = os.path.splitext(n)[1].lower()
                if n in SKIP_FILES or ".min." in n or (ext not in WEB and ext not in HEX_ONLY):
                    continue
                out.append(os.path.join(root, n))
    return out


ROLE_ZH = {"bg": "页面底色", "surface": "表面", "surface-raised": "浮起表面", "surface-sunken": "凹槽", "border": "线",
           "border-strong": "深线", "text": "主文字", "text-muted": "次要文字", "text-subtle": "说明文字", "text-faint": "装饰灰",
           "accent": "强调色", "accent-fg": "强调色上的字", "accent-text": "强调色文字", "accent-subtle": "强调浅底",
           "stage": "深色舞台", "ok": "成功", "ok-soft": "成功浅底", "warn": "警告", "warn-soft": "警告浅底",
           "danger": "危险", "danger-soft": "危险浅底", "shadow": "彩色投影→中性投影"}
PROP_ZH = {"bg": "背景", "text": "文字", "border": "边框", "shadow": "投影", "other": "其他"}


def main() -> int:
    ap = argparse.ArgumentParser(description="把模型自己挑的颜色按用途换成调好的配色", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--style", help="换成哪套预设（默认：浅色页面 graphite，深色页面 midnight）")
    ap.add_argument("--accent", help='题材里的一个颜色，如 "#365899"；不给就用预设的强调色')
    ap.add_argument("--neutral", choices=["warm", "cool", "tinted"], help="配合 --accent：中性色一起换成这个色温")
    ap.add_argument("--to", choices=["auto", "vars", "hex"], default="auto", help="auto：网页写 var(--…)，SCSS/桌面/引擎写十六进制")
    ap.add_argument("--theme", choices=["auto", "light", "dark"], default="auto", help="页面基调；auto 按现有背景判断")
    ap.add_argument("--only-defaults", action="store_true", help="只换模型惯用色（框架默认蓝、靛蓝紫、教程渐变、纯原色……）")
    ap.add_argument("--keep", default="", help="逗号分隔的品牌色，原样保留")
    ap.add_argument("--include-svg", action="store_true", help="连 <svg> 里的颜色一起换（默认不动插画）")
    ap.add_argument("--write", action="store_true", help="真的改文件（先备份）。不加只预览")
    a = ap.parse_args()

    files = collect(a.paths)
    if not files:
        print("没有找到可处理的文件。")
        return 2
    keep = {ck.hex_of(ck.to_rgba(k)[:3]) for k in a.keep.split(",") if k.strip() and ck.to_rgba(k)}

    texts, per_file = {}, {}
    allitems = []
    for f in files:
        try:
            t = open(f, encoding="utf-8").read()
        except (OSError, UnicodeDecodeError):
            continue
        ext = os.path.splitext(f)[1].lower()
        items = find_colors(t, ext, a.include_svg)
        texts[f], per_file[f] = t, items
        allitems += items
    if not allitems:
        print(f"扫描了 {len(texts)} 个文件，没有找到颜色。")
        return 0

    dark_page = page_tone(allitems, a.theme)
    fam = accent_family(allitems)
    style = a.style or ("midnight" if dark_page else "graphite")
    light, dark = ck.preset_roles(style, a.accent, a.neutral)
    roles = dark if dark_page else light
    styles_css = open(os.path.join(ck.ROOT, "assets", "styles.css"), encoding="utf-8").read()
    sm = re.search(r"\.style-" + style + r"\s*\{.*?--shade:\s*([\d\s]+);", styles_css, re.S)
    shade = sm.group(1).strip() if sm else "0 0 0"

    report = defaultdict(lambda: [0, "", "", set()])
    edits = {}
    n_default = 0
    for f, items in per_file.items():
        ext = os.path.splitext(f)[1].lower()
        mode = a.to if a.to != "auto" else ("hex" if ext in HEX_ONLY else "vars")
        grad_count = Counter()
        out, last = [], 0
        text = texts[f]
        for s, e, raw, rgba, prop, g in items:
            hx = ck.hex_of(rgba[:3])
            is_default = ck.model_default_name(rgba)
            if hx in keep or (a.only_defaults and not is_default):
                continue
            role = ck.role_for(rgba, prop, dark_page, fam)
            if role is None:
                continue
            gi = -1
            if g and role.startswith("accent"):
                gi = grad_count[g]
                grad_count[g] += 1
            new = replacement(role, rgba, mode, roles, gi, shade)
            if new == raw:
                continue
            n_default += bool(is_default)
            key = (raw.lower(), new)
            rec = report[key]
            rec[0] += 1
            rec[1] = f"{PROP_ZH.get(prop, prop)} → {ROLE_ZH.get(role, role)}"
            rec[2] = is_default or ""
            rec[3].add(os.path.basename(f))
            out.append(text[last:s] + new)
            last = e
        if out:
            edits[f] = ("".join(out) + text[last:], mode)

    total = sum(r[0] for r in report.values())
    print(f"扫描了 {len(texts)} 个文件，找到 {len(allitems)} 处颜色，{total} 处会被替换（其中模型惯用色 {n_default} 处）。")
    print(f"页面基调：{'深色' if dark_page else '浅色'}；当作强调色的一族：{ {'blue': '蓝紫青', 'red': '红', 'green': '绿', 'yellow': '黄橙'}[fam] }；"
          f"换成预设 {style}" + (f"，强调色 {a.accent}" if a.accent else "") + "\n")
    for (raw, new), (cnt, what, dflt, fs) in sorted(report.items(), key=lambda kv: -kv[1][0])[:60]:
        tag = f"  ← {dflt}" if dflt else ""
        print(f"  {raw:<24} ×{cnt:<3} {what:<18} {new}{tag}")
    if len(report) > 60:
        print(f"  …另有 {len(report) - 60} 种")
    if not a.accent:
        print("\n提示：没给 --accent，用的是预设自带的强调色。给一个题材里实物的颜色效果更好，例如 --accent \"#365899\"。")

    if not a.write:
        print("\n这是预览，没有改任何文件。确认后加 --write。")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    base = os.path.commonpath([os.path.abspath(p) for p in a.paths])
    base = base if os.path.isdir(base) else os.path.dirname(base)
    bdir = os.path.join(base, ".ui-craft-backup", stamp)
    token_block = tokens_css(light, dark, dark_page, shade, style, a.accent)
    need_tokens_file = False
    for f, (new_text, mode) in edits.items():
        dst = os.path.join(bdir, os.path.relpath(os.path.abspath(f), base))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(f, dst)
        ext = os.path.splitext(f)[1].lower()
        if mode == "vars":
            has_lib = re.search(r"ui-craft(-colors)?\.css|/\* ui-craft\.css|id=\"ui-craft-colors\"", new_text)
            if ext in (".html", ".htm") and not has_lib:
                tag = '<style id="ui-craft-colors">\n' + token_block + "</style>\n"
                new_text = re.sub(r"(<head[^>]*>\s*)", lambda m: m.group(1) + tag, new_text, count=1) if "<head" in new_text else tag + new_text
            elif ext not in (".html", ".htm"):
                need_tokens_file = True
        with open(f, "w", encoding="utf-8", newline="") as fh:
            fh.write(new_text)
    print(f"\n已改 {len(edits)} 个文件，原文件备份在 {bdir}")
    if need_tokens_file:
        tf = os.path.join(base, "ui-craft-colors.css")
        with open(tf, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(token_block)
        print(f"配色变量写在 {tf}：在应用入口（main.js / App.vue / layout）里引入一次，或把它的内容并进全局样式。")
    print("接着运行 audit.py 看还剩什么，再用 shot.py 渲染看一眼。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
