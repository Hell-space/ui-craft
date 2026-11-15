#!/usr/bin/env python3
"""把一套配色导出成各框架的主题。由 palette.py --export 调用。

思路：不去改模型写的每一个类名，而是在主题层面把框架的默认色族整体换掉。
Tailwind 的 blue / indigo / violet / purple…… 全部指向同一个强调色色阶，slate / gray / zinc…… 指向调过色温的中性色，
于是代码里已有的 bg-indigo-600、text-slate-500 原样生效，颜色却变成了这一套。
"""
from __future__ import annotations

import json

import colorkit as ck

ACCENT_FAMILIES = ("blue", "indigo", "violet", "purple", "sky", "cyan", "fuchsia", "pink", "teal")
NEUTRAL_FAMILIES = ("slate", "gray", "zinc", "neutral", "stone")
SEMANTIC = {"red": "danger", "rose": "danger", "green": "ok", "emerald": "ok", "lime": "ok",
            "amber": "warn", "yellow": "warn", "orange": "warn"}


def _palette(accent: str, neutral: str | None, style: str):
    light, dark = ck.preset_roles(style, accent, neutral or "warm")
    L = {k: ck.concrete(v) for k, v in light.items()}
    D = {k: ck.concrete(v) for k, v in dark.items()}
    # Keep the light end of a mint ramp even when its dark button tone was replaced.
    _, _, hue = ck.srgb_to_oklch(*ck.to_rgba(accent)[:3])
    ramp_seed = accent if ck.green_hue(hue) else L["accent"]
    ramps = {"accent": ck.ramp(ramp_seed), "neutral": ck.ramp(L["text"], neutral=True),
             "ok": ck.ramp(L["ok"]), "warn": ck.ramp(L["warn"]), "danger": ck.ramp(L["danger"])}
    # Bright yellow buttons use dark labels. Keep their numbered shades in order.
    if not 85 <= hue <= 130:
        ramps["accent"][600] = L["accent"]
    return L, D, ramps


def _families(ramps) -> dict[str, dict[int, str]]:
    fam = {f: ramps["accent"] for f in ACCENT_FAMILIES}
    fam.update({f: ramps["neutral"] for f in NEUTRAL_FAMILIES})
    fam.update({f: ramps[r] for f, r in SEMANTIC.items()})
    return fam


_mix = ck.theme_mix


def _argb(c: str) -> str:
    r, g, b, a = ck.to_rgba(c)
    return "#" + f"{round(a * 255):02X}" + ck.hex_of((r, g, b))[1:]


def tailwind(L, D, ramps) -> str:
    fam = _families(ramps)
    body = ",\n".join(f"        {name}: {json.dumps({str(k): v for k, v in r.items()})}" for name, r in
                      [("accent", ramps["accent"])] + list(fam.items()))
    button_roles = {"accent-button": L["accent"], "accent-label": L["accent-fg"]}
    body += ",\n" + ",\n".join(f'        "{name}": "{color}"' for name, color in button_roles.items())
    return f"""// tailwind.config.js（Tailwind v3）—— 由 ui-craft palette.py 生成
// 把 colors 合进你的 theme.extend。模型常用的 blue/indigo/violet/purple/sky/cyan/pink 色族全部指向同一个强调色色阶，
// slate/gray/zinc/neutral/stone 指向调过色温的中性色，red/green/amber 指向校验过的语义色。
// 保留 bg-indigo-600、text-slate-500 等类名。主按钮与字色可使用配对的 accent-button / accent-label。
module.exports = {{
  theme: {{
    extend: {{
      colors: {{
{body}
      }},
      borderRadius: {{ DEFAULT: "8px", lg: "10px", xl: "14px" }},
    }},
  }},
}};
"""


def tailwind4(L, D, ramps) -> str:
    lines = ["/* Tailwind v4 —— 由 ui-craft palette.py 生成。放在 @import \"tailwindcss\"; 之后。",
             "   模型常用的蓝紫色族指向强调色，灰色族指向调过色温的中性色，类名不用改。 */", "@theme {"]
    for name, r in [("accent", ramps["accent"])] + list(_families(ramps).items()):
        lines += [f"  --color-{name}-{k}: {v};" for k, v in r.items()]
    button, label = L["accent"], L["accent-fg"]
    lines += [f"  --color-accent-button: {button};", f"  --color-accent-label: {label};"]
    lines.append("}")
    return "\n".join(lines) + "\n"


def antd(L, D, ramps) -> str:
    tok = {"colorPrimary": L["accent"], "colorInfo": L["accent"], "colorLink": L["accent-text"],
           "colorSuccess": L["ok"], "colorWarning": L["warn"], "colorError": L["danger"],
           "colorTextBase": L["text"], "colorBgBase": L["surface"], "colorBgLayout": L["bg"],
           "colorBorder": L["border-strong"], "colorBorderSecondary": L["border"], "borderRadius": 8,
           "fontFamily": '-apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei UI", sans-serif'}
    dtok = dict(tok, colorPrimary=D["accent"], colorInfo=D["accent"], colorLink=D["accent-text"], colorTextBase=D["text"],
                colorBgBase=D["surface"], colorBgLayout=D["bg"], colorBorder=D["border-strong"], colorBorderSecondary=D["border"])
    return f"""// Ant Design 5 主题 —— 由 ui-craft palette.py 生成
// 用法：<ConfigProvider theme={{lightTheme}}>…</ConfigProvider>；暗色用 darkTheme。替换掉默认的 #1677FF。
import {{ theme }} from "antd";
export const lightTheme = {{ token: {json.dumps(tok, ensure_ascii=False, indent=2)} }};
export const darkTheme = {{ algorithm: theme.darkAlgorithm, token: {json.dumps(dtok, ensure_ascii=False, indent=2)} }};
"""


def element(L, D, ramps) -> str:
    def group(name, c, base_white="#FFFFFF", base_black="#000000"):
        out = [f"  --el-color-{name}: {c};"]
        out += [f"  --el-color-{name}-light-{i}: {_mix(c, base_white, 1 - i / 10)};" for i in (3, 5, 7, 8, 9)]
        out.append(f"  --el-color-{name}-dark-2: {_mix(c, base_black, 0.8)};")
        return out
    lines = ["/* Element Plus 主题 —— 由 ui-craft palette.py 生成。在全局样式里引入，覆盖默认的 #409EFF。 */", ":root {"]
    for name, c in (("primary", L["accent"]), ("success", L["ok"]), ("warning", L["warn"]), ("danger", L["danger"]),
                    ("error", L["danger"]), ("info", ramps["neutral"][500])):
        lines += group(name, c)
    lines += [f"  --el-text-color-primary: {L['text']};", f"  --el-text-color-regular: {L['text-muted']};",
              f"  --el-text-color-secondary: {L['text-subtle']};", f"  --el-text-color-placeholder: {L['text-faint']};",
              f"  --el-border-color: {L['border-strong']};", f"  --el-border-color-light: {L['border']};",
              f"  --el-border-color-lighter: {L['border']};", f"  --el-bg-color: {L['surface']};",
              f"  --el-bg-color-page: {L['bg']};", f"  --el-fill-color-light: {L['surface-sunken']};",
              "  --el-border-radius-base: 6px;", "}"]
    dl = ["html.dark {"]
    for name, c in (("primary", D["accent"]), ("success", D["ok"]), ("warning", D["warn"]), ("danger", D["danger"]), ("error", D["danger"])):
        dl += group(name, c, base_white=D["bg"], base_black="#FFFFFF")
    dl += [f"  --el-text-color-primary: {D['text']};", f"  --el-text-color-regular: {D['text-muted']};",
           f"  --el-bg-color: {D['surface']};", f"  --el-bg-color-page: {D['bg']};", f"  --el-border-color: {D['border-strong']};", "}"]
    return "\n".join(lines + dl) + "\n"


def mui(L, D, ramps) -> str:
    def pal(T):
        return {"primary": {"main": T["accent"], "contrastText": T["accent-fg"]}, "success": {"main": T["ok"]},
                "warning": {"main": T["warn"]}, "error": {"main": T["danger"]}, "info": {"main": T["accent"]},
                "text": {"primary": T["text"], "secondary": T["text-muted"]}, "divider": T["border"],
                "background": {"default": T["bg"], "paper": T["surface"]}}
    return f"""// MUI 主题 —— 由 ui-craft palette.py 生成。用法：<ThemeProvider theme={{lightTheme}}>
import {{ createTheme }} from "@mui/material/styles";
export const lightTheme = createTheme({{ palette: {{ mode: "light", ...{json.dumps(pal(L), indent=2)} }}, shape: {{ borderRadius: 8 }} }});
export const darkTheme = createTheme({{ palette: {{ mode: "dark", ...{json.dumps(pal(D), indent=2)} }}, shape: {{ borderRadius: 8 }} }});
"""


def qss(L, D, ramps, T=None) -> str:
    T = T or L
    return f"""/* Qt 样式表（PySide / PyQt）—— 由 ui-craft palette.py 生成。app.setStyleSheet(open("theme.qss", encoding="utf-8").read())
   主按钮：btn.setProperty("primary", True)；危险按钮：btn.setProperty("danger", True)。 */
QWidget {{ background: {T['bg']}; color: {T['text']}; font-family: "Segoe UI", "Microsoft YaHei UI"; font-size: 10pt; }}
QFrame#card, QGroupBox {{ background: {T['surface']}; border: 1px solid {T['border']}; border-radius: 8px; }}
QGroupBox {{ margin-top: 14px; padding: 12px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; color: {T['text-muted']}; }}
QLabel[muted="true"] {{ color: {T['text-subtle']}; }}
QPushButton {{ background: {T['surface']}; color: {T['text']}; border: 1px solid {T['border-strong']}; border-radius: 6px; padding: 6px 14px; min-height: 22px; }}
QPushButton:hover {{ background: {T['surface-sunken']}; }}
QPushButton:pressed {{ background: {T['border']}; }}
QPushButton:disabled {{ color: {T['text-faint']}; border-color: {T['border']}; }}
QPushButton[primary="true"] {{ background: {T['accent']}; color: {T['accent-fg']}; border: 1px solid {T['accent']}; font-weight: 600; }}
QPushButton[primary="true"]:hover {{ background: {_mix(T['accent'], T['text'], 0.88)}; }}
QPushButton[danger="true"] {{ background: {T['danger']}; color: #FFFFFF; border: 1px solid {T['danger']}; }}
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{ background: {T['surface']}; border: 1px solid {T['border-strong']}; border-radius: 6px; padding: 5px 8px; selection-background-color: {T['accent-subtle']}; selection-color: {T['text']}; }}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {{ border: 1px solid {T['accent']}; }}
QComboBox QAbstractItemView {{ background: {T['surface']}; border: 1px solid {T['border-strong']}; selection-background-color: {T['accent-subtle']}; selection-color: {T['text']}; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{ background: {T['accent']}; border: 1px solid {T['accent']}; }}
QTabBar::tab {{ background: transparent; color: {T['text-muted']}; padding: 8px 14px; border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {T['text']}; border-bottom: 2px solid {T['accent']}; }}
QHeaderView::section {{ background: {T['surface-sunken']}; color: {T['text-subtle']}; border: 0; border-bottom: 1px solid {T['border-strong']}; padding: 6px 8px; }}
QTableView, QListView, QTreeView {{ background: {T['surface']}; border: 1px solid {T['border']}; gridline-color: {T['border']}; selection-background-color: {T['accent-subtle']}; selection-color: {T['text']}; alternate-background-color: {T['bg']}; }}
QProgressBar {{ background: {T['surface-sunken']}; border: 0; border-radius: 4px; height: 8px; text-align: center; }}
QProgressBar::chunk {{ background: {T['accent']}; border-radius: 4px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; }} QScrollBar::handle:vertical {{ background: {T['border-strong']}; border-radius: 5px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QToolTip {{ background: {T['text']}; color: {T['bg']}; border: 0; padding: 4px 8px; }}
"""


def wpf(L, D, ramps) -> str:
    rows = []
    for k in ck.ROLES:
        if k in L and k in D:
            name = "".join(p.capitalize() for p in k.split("-"))
            rows.append(f'  <Color x:Key="{name}Color">{_argb(L[k])}</Color>')
            rows.append(f'  <SolidColorBrush x:Key="{name}Brush" Color="{{StaticResource {name}Color}}"/>')
    return ("<!-- WPF / WinUI / Avalonia 资源字典 —— 由 ui-craft palette.py 生成（浅色）。暗色把 --export wpf-dark 的结果另存一份。\n"
            "     在 App.xaml 的 MergedDictionaries 里引入；控件里用 {StaticResource AccentBrush}。 -->\n"
            '<ResourceDictionary xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"\n'
            '                    xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">\n' + "\n".join(rows) + "\n</ResourceDictionary>\n")


def tk(L, D, ramps) -> str:
    keys = [k for k in ck.ROLES if k in L]
    return ("# tkinter / pygame / matplotlib 等 Python 界面用的配色 —— 由 ui-craft palette.py 生成\n"
            "# 用法：from theme import LIGHT as C；root.configure(bg=C['bg'])；Button(…, bg=C['accent'], fg=C['accent-fg'])\n"
            f"LIGHT = {json.dumps({k: L[k] for k in keys}, indent=4)}\n"
            f"DARK = {json.dumps({k: D[k] for k in keys}, indent=4)}\n")


def generic_json(L, D, ramps) -> str:
    return json.dumps({"light": L, "dark": D, "ramps": {k: {str(s): v for s, v in r.items()} for k, r in ramps.items()}},
                      ensure_ascii=False, indent=2) + "\n"


FORMATS = {
    "tailwind": (tailwind, "Tailwind v3：tailwind.config.js 的 colors"),
    "tailwind4": (tailwind4, "Tailwind v4：@theme 变量"),
    "antd": (antd, "Ant Design 5：ConfigProvider token"),
    "element": (element, "Element Plus：CSS 变量"),
    "mui": (mui, "MUI：createTheme"),
    "qss": (qss, "Qt 样式表（PySide / PyQt）"),
    "qss-dark": (lambda L, D, r: qss(L, D, r, D), "Qt 样式表，暗色"),
    "wpf": (wpf, "WPF / WinUI / Avalonia 资源字典"),
    "wpf-dark": (lambda L, D, r: wpf(D, L, r), "资源字典，暗色"),
    "tk": (tk, "Python 字典：tkinter、pygame、matplotlib"),
    "json": (generic_json, "通用 JSON：Flutter、Compose、Unity、Godot 等自行读取"),
}


try:                                   # 游戏、mod 覆盖层与原生应用框架
    import exporters_game
    FORMATS.update(exporters_game.FORMATS)
except ImportError:
    pass
try:                                   # tkinter、图表、终端界面、小程序
    import exporters_more
    FORMATS.update(exporters_more.FORMATS)
except ImportError:
    pass


def export(fmt: str, accent: str, neutral: str | None, style: str = "graphite") -> str:
    if fmt not in FORMATS:
        raise SystemExit(f"不支持 {fmt}。可用：{', '.join(FORMATS)}")
    if neutral is None:
        # 桌面窗口挨着系统的冷灰窗框，暖纸色放在里面显得发黄发旧；网页和其他格式仍默认暖纸
        neutral = "cool" if fmt in ("ttk", "tk", "qss", "qss-dark", "wpf", "wpf-dark") else "warm"
    L, D, ramps = _palette(accent, neutral, style)
    return FORMATS[fmt][0](L, D, ramps)
