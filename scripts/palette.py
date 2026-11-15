#!/usr/bin/env python3
"""从一个"题材色"生成一整套协调的配色，并校验对比度。

用法:
  python palette.py "#9E4A2F"                 # 从丹霞岩壁的锈红出发
  python palette.py "oklch(0.55 0.15 262)"    # 也接受 oklch / rgb / hsl
  python palette.py "#9E4A2F" --neutral warm   # 中性色：warm（默认，暖纸）/ cool / tinted（跟随强调色色相）
  python palette.py "#9E4A2F" --css            # 直接输出可粘贴的 :root { … } 片段
  python palette.py "#9E4A2F" --hex            # 十六进制色值，给 Qt / WPF / tkinter / 游戏引擎
  python palette.py "#9E4A2F" --export tailwind  # 导出成框架主题，替换掉框架和模型的默认色：
                                                 #   tailwind / tailwind4 / antd / element / mui / qss / wpf / tk / json
  python palette.py "#8a8a8a" "#3fae5a" "#3d7fe0" "#a352e0" "#f08a24" --align   # 稀有度 / 阵营 / 分类色：对齐明度

它做的事：
  1. 把输入色转到 OKLCH，取它的色相 H 与彩度 C。
  2. 强调色：浅色主题落到 L 0.50（能托住白字），暗色主题提亮到 L 0.74、彩度 ×0.8。
     黄、黄绿（H 85–130）撑不起白字，自动改成"亮底深字"。
  3. 生成 hover / 浅底 / 文字用强调色 / 深色舞台色（L 0.24 的同色相深色面）。
  4. 中性色按选定色温生成三档表面、两档线、四档文字，彩度按明度分段（浅端低、深端略高）。
  5. 逐对检查 WCAG 对比度；不达标的自动微调明度直到达标。
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contrast import parse_color, contrast  # noqa: E402
from colorkit import layer_color, srgb_to_oklch, theme_tone  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def ok(L, C, H, a=None):
    L, C, H = theme_tone(L, C, H)
    s = f"oklch({L:.3f} {C:.3f} {H:.0f}"
    return s + (f" / {a})" if a is not None else ")")


def fit(fg_fn, bg, target, lo, hi, step):
    """沿明度方向微调前景，直到对比度达标。fg_fn(L) -> 颜色串。"""
    L = lo
    for _ in range(80):
        c, _ = contrast(fg_fn(L), bg)
        if c >= target:
            return L
        L += step
        if (step > 0 and L > hi) or (step < 0 and L < hi):
            break
    return L


STAGE_CHROMA = None


def build(src: str, neutral: str):
    r, g, b, _, _ = parse_color(src)
    _, C0, H = srgb_to_oklch(r, g, b)
    C = max(0.06, min(C0, 0.19))
    yellow = 85 <= H <= 130

    if neutral == "cool":
        NH, nc = 255, 0.006
    elif neutral == "tinted":
        NH, nc = H, 0.008
    else:
        NH, nc = 80, 0.007

    light, dark = {}, {}
    light["bg"] = ok(0.972, nc, NH);            dark["bg"] = ok(0.170, nc * 1.4, NH)
    light["surface"] = ok(0.993, nc * 0.4, NH); dark["surface"] = ok(0.205, nc * 1.6, NH)
    light["surface-sunken"] = ok(0.948, nc * 1.5, NH); dark["surface-sunken"] = ok(0.150, nc * 1.4, NH)
    light["border"] = ok(0.902, nc * 1.6, NH);  dark["border"] = "oklch(1 0 0 / 0.08)"
    light["border-strong"] = ok(0.830, nc * 2, NH); dark["border-strong"] = "oklch(1 0 0 / 0.14)"
    light["text"] = ok(0.230, nc * 2.2, NH);    dark["text"] = ok(0.935, nc * 1.4, NH)
    light["text-muted"] = ok(0.430, nc * 2.4, NH); dark["text-muted"] = ok(0.750, nc * 2, NH)
    Ls = fit(lambda L: ok(L, nc * 2.2, NH), light["surface-sunken"], 4.5, 0.56, 0.30, -0.005)
    light["text-subtle"] = ok(Ls, nc * 2.2, NH)
    Ld = fit(lambda L: ok(L, nc * 2, NH), dark["surface"], 4.5, 0.60, 0.85, 0.005)
    dark["text-subtle"] = ok(Ld, nc * 2, NH)
    light["text-faint"] = ok(0.70, nc * 2.2, NH); dark["text-faint"] = ok(0.48, nc * 2, NH)

    light["accent-subtle"] = ok(0.945, C * 0.18, H); dark["accent-subtle"] = ok(0.27, C * 0.35, H)
    if yellow:
        light["accent"] = ok(0.84, C, H);      light["accent-fg"] = ok(0.22, 0.04, H)
        dark["accent"] = ok(0.84, C * 0.9, H); dark["accent-fg"] = ok(0.20, 0.04, H)
        La = fit(lambda L: ok(L, C, H), light["accent-subtle"], 4.6, 0.55, 0.30, -0.01)
        light["accent-text"] = ok(La, C, H)
    else:
        La = fit(lambda L: ok(L, C, H), "#ffffff", 4.6, 0.56, 0.30, -0.01)   # 托住白字
        light["accent"] = ok(La, C, H);        light["accent-fg"] = ok(0.99, 0.005, H)
        dark["accent"] = ok(0.74, C * 0.8, H); dark["accent-fg"] = ok(0.18, 0.03, H)
        Lt = fit(lambda L: ok(L, C, H), light["accent-subtle"], 4.6, La, 0.30, -0.01)
        light["accent-text"] = ok(Lt, C, H)
    Lad = fit(lambda L: ok(L, C * 0.75, H), dark["bg"], 4.5, 0.76, 0.92, 0.01)
    dark["accent-text"] = ok(Lad, C * 0.75, H)
    sc = STAGE_CHROMA if STAGE_CHROMA is not None else min(C * 0.25, 0.03)   # 深色面彩度高了会显得像巧克力或墨水，默认压到 ≤0.03
    stage = {"stage": ok(0.225, sc, H), "stage-glow": ok(0.42, min(C * 0.8, 0.14), H),
             "stage-ink": ok(0.965, 0.012, NH), "stage-muted": ok(0.78, 0.03, H)}
    return H, C, light, dark, stage


def align(colors, bg):
    """把多个颜色调到同一明度与相近彩度：返回 (名字, 填充色, 文字色) 列表。
    填充色的 L 固定为 0.72；单独为指定背景选择可读的前景色。"""
    out = []
    # At least one neutral endpoint meets 4.5:1 on any opaque sRGB background.
    # Use the same compositing assumption as the reported ratio for translucent backgrounds.
    lighter = contrast("#fff", bg)[0] >= contrast("#000", bg)[0]
    lightness = range(62, 101) if lighter else range(62, -1, -1)
    fallback = "#fff" if lighter else "#000"
    for c in colors:
        r, g, b, _, _ = parse_color(c)
        _, C0, H = srgb_to_oklch(r, g, b)
        C = min(max(C0, 0.04), 0.14) if C0 > 0.02 else 0.0
        fill = ok(0.72, C, H)
        text = fallback
        for level in lightness:
            candidate = ok(level / 100, C, H)
            if contrast(candidate, bg)[0] >= 4.5:
                text = candidate
                break
        out.append((c, fill, text))
    return out


def main():
    ap = argparse.ArgumentParser(description="从题材色生成协调的配色")
    ap.add_argument("color", nargs="+", help="一个题材色；配合 --align 时可给多个")
    ap.add_argument("--align", action="store_true", help="把多个颜色对齐到同一明度（稀有度、阵营、分类色），输出填充色与文字色")
    ap.add_argument("--on", default="#1A1712", help="--align 时文字色要压在哪个底色上（默认深底；网页浅底用 #FFFFFF）")
    ap.add_argument("--stage-chroma", type=float, help="深色舞台的彩度（默认自动，≤0.03）")
    ap.add_argument("--neutral", choices=["warm", "cool", "tinted"],
                    help="中性色：warm 暖纸（网页默认）/ cool 冷灰（桌面导出 ttk tk qss wpf 默认）/ tinted 跟随强调色")
    ap.add_argument("--css", action="store_true")
    ap.add_argument("--hex", action="store_true", help="输出十六进制色值（给 Qt / WPF / tkinter / 游戏引擎等不能用 oklch 的环境）")
    ap.add_argument("--export", help="导出成框架主题。网页：tailwind tailwind4 antd element mui；桌面：qss qss-dark wpf wpf-dark ttk tk；图表：echarts chartjs mpl plotly；终端：textual rich；小程序：wxss；应用：flutter compose swiftui streamlit gradio；游戏与 mod：imgui imgui-cs unity uss godot minecraft lua roblox；通用：json。--export list 列出全部")
    ap.add_argument("--style", default="graphite", help="配合 --export：取哪套预设的圆角与阴影色（颜色本身都来自题材色）")
    ap.add_argument("--out", help="配合 --export：写到文件，不写就打印出来")
    a = ap.parse_args()
    if a.export == "list":
        import exporters
        for k, (_, zh) in exporters.FORMATS.items():
            print(f"  {k:<11}{zh}")
        return
    if a.export:
        import exporters
        text = exporters.export(a.export, a.color[0], a.neutral, a.style)
        if a.out:
            with open(a.out, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            print(f"已写入 {a.out}")
        else:
            print(text)
        return
    global STAGE_CHROMA
    STAGE_CHROMA = a.stage_chroma
    if a.align:
        print(f"明度对齐（文字色压在 {a.on} 上 ≥ 4.5:1；填充色明度统一 0.72）\n")
        print(f"{'输入':<14}{'填充色':<28}{'文字色':<28}对比度")
        for src, fill, text in align(a.color, a.on):
            c, _ = contrast(text, a.on)
            print(f"{src:<14}{fill:<28}{text:<28}{c:.2f}:1")
        print("\n提示：只靠颜色区分不够，稀有度、阵营还要配形状或边框样式（见 references/game-ui.md 第 8 节）。")
        return
    a.color = a.color[0]
    a.neutral = a.neutral or "warm"
    H, C, light, dark, stage = build(a.color, a.neutral)

    if a.hex:
        def hx(c):
            r, g, b, al, _ = parse_color(c)
            base = "#" + "".join(f"{max(0, min(255, round(v * 255))):02X}" for v in (r, g, b))
            return base if al is None or al >= 0.999 else f"{base} 透明度 {al:.0%}"
        print(f"题材色 {a.color}（中性色：{a.neutral}）—— 十六进制，对比度已校验\n")
        print(f"{'角色':<16}{'浅色主题':<22}{'暗色主题'}")
        for k in light:
            print(f"{k:<16}{hx(light[k]):<22}{hx(dark[k])}")
        print("\n深色舞台（两个主题共用）")
        for k, v in stage.items():
            print(f"  {k:<14}{hx(v)}")
        print("\n用法：bg 窗口底色 · surface 面板与卡片 · surface-sunken 输入槽与侧栏 · border 分隔线 · text 正文 · text-muted 次要文字 ·")
        print("      text-subtle 说明文字 · accent 主按钮与选中 · accent-fg 压在 accent 上的字 · accent-subtle 选中行的浅底")
        return

    if a.css:
        print(f"/* 由 palette.py 从 {a.color} 生成：H {H:.0f}，C {C:.3f}，中性色 {a.neutral} */")
        print(":root {")
        for k in light:
            print(f"  --{k}: light-dark({light[k]}, {dark[k]});")
        print(f"  --accent-layer: light-dark({layer_color(light['accent'])}, {layer_color(dark['accent'])});")
        for k, v in stage.items():
            print(f"  --{k}: {v};")
        print("}")
        return

    print(f"题材色 {a.color} → H {H:.0f}°，C {C:.3f}（中性色：{a.neutral}）\n")
    print(f"{'角色':<16}{'浅色':<30}{'暗色'}")
    for k in light:
        print(f"{k:<16}{light[k]:<30}{dark[k]}")
    print("\n深色舞台（两个主题共用）")
    for k, v in stage.items():
        print(f"  {k:<14}{v}")
    print("\n对比度")
    checks = [("text", "bg"), ("text-muted", "bg"), ("text-subtle", "surface-sunken"),
              ("accent-fg", "accent"), ("accent-text", "bg"), ("accent-text", "accent-subtle")]
    for theme, pal in (("浅", light), ("暗", dark)):
        for f, b in checks:
            c, _ = contrast(pal[f], pal[b])
            print(f"  [{theme}] {f:<12} 在 {b:<15} {c:5.2f}:1  {'通过' if c >= 4.5 else '不达标'}")
    c, _ = contrast(stage["stage-ink"], stage["stage"])
    print(f"  [舞台] stage-ink 在 stage    {c:5.2f}:1  {'通过' if c >= 4.5 else '不达标'}")
    print("\n加 --css 输出可直接粘贴的 :root 片段。")


if __name__ == "__main__":
    main()
