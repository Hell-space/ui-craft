#!/usr/bin/env python3
"""游戏、mod 覆盖层与原生应用框架的配色导出。由 exporters.py 注册，经 palette.py --export 调用。

游戏覆盖层（imgui / unity / godot / minecraft / lua / roblox）默认用暗色那一套：
它们浮在游戏画面上，深色半透明面板 + 一个强调色最不抢画面。
应用框架（flutter / compose / swiftui / streamlit / gradio）给浅色与暗色两套。
"""
from __future__ import annotations

import colorkit as ck

PANEL_ALPHA = 0.92


def _rgb(c: str) -> tuple[float, float, float, float]:
    r, g, b, a = ck.to_rgba(c)
    return r, g, b, a


def _f(c: str, a: float | None = None, fmt="{:.3f}") -> list[str]:
    r, g, b, a0 = _rgb(c)
    return [fmt.format(r), fmt.format(g), fmt.format(b), fmt.format(a0 if a is None else a)]


def _i(c: str) -> tuple[int, int, int]:
    r, g, b, _ = _rgb(c)
    return round(r * 255), round(g * 255), round(b * 255)


def _hex(c: str) -> str:
    return ck.hex_of(_rgb(c)[:3])


_mix = ck.theme_mix


# ---------------------------------------------------------------- Dear ImGui

def _imgui_colors(D) -> list[tuple[str, str, float]]:
    acc = D["accent"]
    overlay = ck.layer_color(acc)
    return [
        ("Text", D["text"], 1), ("TextDisabled", D["text-subtle"], 1),
        ("WindowBg", D["bg"], PANEL_ALPHA), ("ChildBg", D["bg"], 0), ("PopupBg", D["surface-raised"], 0.98),
        ("Border", _mix(D["text"], D["bg"], 0.14), 1), ("BorderShadow", D["bg"], 0),
        ("FrameBg", D["surface-sunken"], 1), ("FrameBgHovered", _mix(D["text"], D["surface-sunken"], 0.08), 1),
        ("FrameBgActive", _mix(acc, D["surface-sunken"], 0.25), 1),
        ("TitleBg", D["bg"], 1), ("TitleBgActive", D["surface"], 1), ("TitleBgCollapsed", D["bg"], 0.8),
        ("MenuBarBg", D["surface"], 1), ("ScrollbarBg", D["bg"], 0),
        ("ScrollbarGrab", _mix(D["text"], D["bg"], 0.22), 1), ("ScrollbarGrabHovered", _mix(D["text"], D["bg"], 0.32), 1),
        ("ScrollbarGrabActive", acc, 1), ("CheckMark", acc, 1), ("SliderGrab", acc, 1), ("SliderGrabActive", D["accent-text"], 1),
        ("Button", D["surface-raised"], 1), ("ButtonHovered", _mix(D["text"], D["surface-raised"], 0.1), 1),
        ("ButtonActive", _mix(acc, D["surface-raised"], 0.45), 1),
        ("Header", overlay, 0.20), ("HeaderHovered", overlay, 0.30), ("HeaderActive", overlay, 0.42),
        ("Separator", _mix(D["text"], D["bg"], 0.14), 1), ("SeparatorHovered", overlay, 0.6), ("SeparatorActive", acc, 1),
        ("ResizeGrip", acc, 0), ("ResizeGripHovered", overlay, 0.4), ("ResizeGripActive", overlay, 0.7),
        ("PlotLines", D["text-muted"], 1), ("PlotLinesHovered", acc, 1), ("PlotHistogram", acc, 1), ("PlotHistogramHovered", D["accent-text"], 1),
        ("TableHeaderBg", D["surface"], 1), ("TableBorderStrong", _mix(D["text"], D["bg"], 0.18), 1),
        ("TableBorderLight", _mix(D["text"], D["bg"], 0.10), 1), ("TableRowBg", D["bg"], 0), ("TableRowBgAlt", D["text"], 0.03),
        ("TextSelectedBg", overlay, 0.32), ("DragDropTarget", overlay, 0.9),
        ("ModalWindowDimBg", D["bg"], 0.6),
    ]


def imgui(L, D, ramps) -> str:
    rows = "\n".join(f"    c[ImGuiCol_{n}] = ImVec4({', '.join(f + 'f' for f in _f(col, a))});" for n, col, a in _imgui_colors(D))
    tab = D["surface"]
    acc = D["accent"]
    overlay = ck.layer_color(acc)
    return f"""// Dear ImGui 主题 —— 由 ui-craft palette.py 生成。创建上下文后调用一次 UiCraftStyle(缩放);
// 中文：加载带中文字形的字体，例如
//   io.Fonts->AddFontFromFileTTF("C:/Windows/Fonts/msyh.ttc", 18.0f * scale, nullptr, io.Fonts->GetGlyphRangesChineseSimplifiedCommon());
#pragma once
#include "imgui.h"

inline void UiCraftStyle(float scale = 1.0f) {{
    ImGuiStyle& s = ImGui::GetStyle();
    s.WindowPadding = ImVec2(14, 12); s.FramePadding = ImVec2(10, 6); s.CellPadding = ImVec2(8, 5);
    s.ItemSpacing = ImVec2(10, 8); s.ItemInnerSpacing = ImVec2(6, 6); s.IndentSpacing = 18;
    s.ScrollbarSize = 12; s.GrabMinSize = 10;
    s.WindowBorderSize = 1; s.ChildBorderSize = 1; s.PopupBorderSize = 1; s.FrameBorderSize = 0;
    s.WindowRounding = 8; s.ChildRounding = 6; s.FrameRounding = 5; s.PopupRounding = 6;
    s.ScrollbarRounding = 6; s.GrabRounding = 4; s.TabRounding = 5;
    s.WindowTitleAlign = ImVec2(0.0f, 0.5f);
    s.ScaleAllSizes(scale);

    ImVec4* c = s.Colors;
{rows}
#if IMGUI_VERSION_NUM >= 19090
    c[ImGuiCol_Tab] = ImVec4({', '.join(f + 'f' for f in _f(tab, 1))});
    c[ImGuiCol_TabHovered] = ImVec4({', '.join(f + 'f' for f in _f(overlay, 0.30))});
    c[ImGuiCol_TabSelected] = ImVec4({', '.join(f + 'f' for f in _f(_mix(acc, tab, 0.28), 1))});
#else
    c[ImGuiCol_Tab] = ImVec4({', '.join(f + 'f' for f in _f(tab, 1))});
    c[ImGuiCol_TabHovered] = ImVec4({', '.join(f + 'f' for f in _f(overlay, 0.30))});
    c[ImGuiCol_TabActive] = ImVec4({', '.join(f + 'f' for f in _f(_mix(acc, tab, 0.28), 1))});
#endif
}}
"""


def imgui_cs(L, D, ramps) -> str:
    rows = "\n".join(f"        c[(int)ImGuiCol.{n}] = new Vector4({', '.join(f + 'f' for f in _f(col, a))});" for n, col, a in _imgui_colors(D))
    return f"""// ImGui.NET 主题 —— 由 ui-craft palette.py 生成。创建上下文后调用 UiCraftStyle.Apply(缩放);
using System.Numerics;
using ImGuiNET;

public static class UiCraftStyle
{{
    public static void Apply(float scale = 1f)
    {{
        var s = ImGui.GetStyle();
        s.WindowPadding = new Vector2(14, 12); s.FramePadding = new Vector2(10, 6); s.ItemSpacing = new Vector2(10, 8);
        s.ScrollbarSize = 12; s.GrabMinSize = 10; s.WindowBorderSize = 1; s.FrameBorderSize = 0;
        s.WindowRounding = 8; s.ChildRounding = 6; s.FrameRounding = 5; s.PopupRounding = 6; s.GrabRounding = 4; s.TabRounding = 5;
        s.ScaleAllSizes(scale);
        var c = s.Colors;
{rows}
    }}
}}
"""


# ---------------------------------------------------------------- Unity

def unity(L, D, ramps) -> str:
    keys = ["bg", "surface", "surface-raised", "surface-sunken", "border", "border-strong", "text", "text-muted", "text-subtle",
            "accent", "accent-fg", "accent-text", "accent-subtle", "ok", "warn", "danger"]
    def name(k):
        return "".join(p.capitalize() for p in k.split("-"))
    consts = "\n".join(f"    public static readonly Color {name(k)} = new Color({', '.join(f + 'f' for f in _f(D[k] if not k.startswith('border') else _mix(D['text'], D['bg'], 0.14 if k == 'border' else 0.22), PANEL_ALPHA if k == 'bg' else None))});" for k in keys)
    return f"""// Unity 配色与 IMGUI 皮肤 —— 由 ui-craft palette.py 生成（暗色面板，适合 BepInEx / MelonLoader 的游戏内菜单）
// 用法：void OnGUI() {{ GUI.skin = UiCraftPalette.Skin; GUILayout.Window(…); }}
// uGUI / TextMeshPro 直接用下面的静态颜色；UI Toolkit 用 --export uss。
using UnityEngine;

public static class UiCraftPalette
{{
{consts}

    static GUISkin _skin;
    // 只能在 OnGUI 里第一次取用（需要 GUI.skin 作为底）
    public static GUISkin Skin => _skin != null ? _skin : (_skin = Build());

    static Texture2D Tex(Color c)
    {{
        var t = new Texture2D(1, 1) {{ hideFlags = HideFlags.HideAndDontSave }};
        t.SetPixel(0, 0, c); t.Apply(); return t;
    }}

    static void Flat(GUIStyle s, Color normal, Color hover, Color active, Color text, Color activeText)
    {{
        s.normal.background = Tex(normal); s.hover.background = Tex(hover); s.active.background = Tex(active);
        s.focused.background = Tex(hover); s.onNormal.background = Tex(active); s.onHover.background = Tex(active);
        s.normal.textColor = text; s.hover.textColor = text; s.focused.textColor = text;
        s.active.textColor = activeText; s.onNormal.textColor = activeText; s.onHover.textColor = activeText;
        s.border = new RectOffset(0, 0, 0, 0);
    }}

    static GUISkin Build()
    {{
        var s = Object.Instantiate(GUI.skin);
        Flat(s.window, Bg, Bg, Bg, Text, Text);
        s.window.padding = new RectOffset(14, 14, 30, 14); s.window.fontStyle = FontStyle.Bold; s.window.alignment = TextAnchor.UpperLeft;
        s.window.contentOffset = new Vector2(14, 0);
        Flat(s.box, SurfaceSunken, SurfaceSunken, SurfaceSunken, TextMuted, TextMuted);
        Flat(s.button, SurfaceRaised, Border, Accent, Text, AccentFg);
        s.button.padding = new RectOffset(12, 12, 6, 6);
        Flat(s.textField, SurfaceSunken, SurfaceSunken, SurfaceSunken, Text, Text);
        Flat(s.textArea, SurfaceSunken, SurfaceSunken, SurfaceSunken, Text, Text);
        s.label.normal.textColor = Text; s.label.wordWrap = true;
        s.toggle.normal.textColor = Text; s.toggle.onNormal.textColor = AccentText; s.toggle.hover.textColor = Text;
        Flat(s.horizontalSlider, SurfaceSunken, SurfaceSunken, SurfaceSunken, Text, Text);
        Flat(s.horizontalSliderThumb, Accent, AccentText, AccentText, Text, Text);
        Flat(s.verticalScrollbar, Bg, Bg, Bg, Text, Text);
        Flat(s.verticalScrollbarThumb, BorderStrong, TextSubtle, Accent, Text, Text);
        return s;
    }}
}}
"""


def uss(L, D, ramps) -> str:
    lines = ["/* Unity UI Toolkit（USS）—— 由 ui-craft palette.py 生成。在根样式表里引入，元素上用 var(--uc-accent)。 */", ":root {"]
    for k in ck.ROLES:
        if k in D:
            lines.append(f"    --uc-{k}: {ck.concrete(D[k])};")
    lines += ["}", ".uc-panel { background-color: var(--uc-surface); border-color: var(--uc-border); border-width: 1px; border-radius: 8px; padding: 12px; }",
              ".uc-button { background-color: var(--uc-surface-raised); color: var(--uc-text); border-radius: 6px; border-width: 0; padding: 6px 12px; }",
              ".uc-button:hover { background-color: var(--uc-border-strong); }",
              ".uc-button--primary { background-color: var(--uc-accent); color: var(--uc-accent-fg); }"]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- Godot

def godot(L, D, ramps) -> str:
    keys = {"BG": D["bg"], "SURFACE": D["surface"], "SURFACE_RAISED": D["surface-raised"], "SURFACE_SUNKEN": D["surface-sunken"],
            "BORDER": _mix(D["text"], D["bg"], 0.14), "BORDER_STRONG": _mix(D["text"], D["bg"], 0.24), "TEXT": D["text"],
            "TEXT_MUTED": D["text-muted"], "TEXT_SUBTLE": D["text-subtle"], "ACCENT": D["accent"], "ACCENT_FG": D["accent-fg"],
            "ACCENT_TEXT": D["accent-text"], "OK": D["ok"], "WARN": D["warn"], "DANGER": D["danger"]}
    consts = "\n".join(f'const {k} := Color("{_hex(v)}")' for k, v in keys.items())
    return f"""# Godot 4 主题 —— 由 ui-craft palette.py 生成（暗色面板）
# 用法：在根 Control 上 theme = UiCraftTheme.build()，子节点自动继承。
class_name UiCraftTheme

{consts}

static func _box(c: Color, radius: int = 6, border: Color = Color(0, 0, 0, 0), pad: int = 10) -> StyleBoxFlat:
	var s := StyleBoxFlat.new()
	s.bg_color = c
	s.set_corner_radius_all(radius)
	s.content_margin_left = pad
	s.content_margin_right = pad
	s.content_margin_top = pad * 0.6
	s.content_margin_bottom = pad * 0.6
	if border.a > 0.0:
		s.set_border_width_all(1)
		s.border_color = border
	return s

static func build() -> Theme:
	var t := Theme.new()
	var panel := _box(Color(BG, {PANEL_ALPHA}), 8, BORDER, 14)
	t.set_stylebox("panel", "PanelContainer", panel)
	t.set_stylebox("panel", "Panel", panel)
	t.set_stylebox("normal", "Button", _box(SURFACE_RAISED, 6, BORDER))
	t.set_stylebox("hover", "Button", _box(BORDER_STRONG, 6, BORDER_STRONG))
	t.set_stylebox("pressed", "Button", _box(ACCENT, 6))
	t.set_stylebox("disabled", "Button", _box(SURFACE, 6))
	var focus := _box(Color(0, 0, 0, 0), 6, ACCENT)
	focus.set_border_width_all(2)
	t.set_stylebox("focus", "Button", focus)
	t.set_color("font_color", "Button", TEXT)
	t.set_color("font_hover_color", "Button", TEXT)
	t.set_color("font_pressed_color", "Button", ACCENT_FG)
	t.set_color("font_disabled_color", "Button", TEXT_SUBTLE)
	t.set_color("font_color", "Label", TEXT)
	t.set_stylebox("normal", "LineEdit", _box(SURFACE_SUNKEN, 6, BORDER))
	t.set_stylebox("focus", "LineEdit", focus)
	t.set_color("font_color", "LineEdit", TEXT)
	t.set_color("font_placeholder_color", "LineEdit", TEXT_SUBTLE)
	t.set_stylebox("panel", "PopupMenu", _box(SURFACE_RAISED, 6, BORDER))
	t.set_stylebox("tab_selected", "TabContainer", _box(SURFACE, 6))
	t.set_stylebox("tab_unselected", "TabContainer", _box(BG, 6))
	t.set_stylebox("fill", "ProgressBar", _box(ACCENT, 4, Color(0, 0, 0, 0), 0))
	t.set_stylebox("background", "ProgressBar", _box(SURFACE_SUNKEN, 4, Color(0, 0, 0, 0), 0))
	return t
"""


# ---------------------------------------------------------------- Minecraft / Lua / Roblox

def minecraft(L, D, ramps) -> str:
    keys = ["bg", "surface", "surface-raised", "border", "border-strong", "text", "text-muted", "text-subtle", "accent", "accent-text", "ok", "warn", "danger"]
    def argb(c, a=1.0):
        r, g, b = _i(c)
        return f"0x{round(a * 255):02X}{r:02X}{g:02X}{b:02X}"
    rows = []
    for k in keys:
        v = D[k] if not k.startswith("border") else _mix(D["text"], D["bg"], 0.14 if k == "border" else 0.24)
        alpha = 0.86 if k == "bg" else (0.94 if k.startswith("surface") else 1.0)
        rows.append(f"    public static final int {k.upper().replace('-', '_')} = {argb(v, alpha)};")
    return ("// Minecraft Java 配色（ARGB int）—— 由 ui-craft palette.py 生成。适合 mod 自己的工具类界面与 HUD 叠加层；\n"
            "// 原版风格的界面优先用原版控件与 GUI 贴图。用法：context.fill(x1, y1, x2, y2, UiCraftColors.SURFACE)；\n"
            "// context.drawTextWithShadow(textRenderer, text, x, y, UiCraftColors.TEXT)。新版本的文字颜色必须带不透明的 alpha（0xFF…），否则不显示。\n"
            "public final class UiCraftColors {\n    private UiCraftColors() {}\n" + "\n".join(rows) + "\n}\n")


def lua(L, D, ramps) -> str:
    keys = ["bg", "surface", "surface-raised", "surface-sunken", "border", "text", "text-muted", "text-subtle", "accent", "accent-fg", "accent-text", "ok", "warn", "danger"]
    rows = []
    for k in keys:
        v = D[k] if k != "border" else _mix(D["text"], D["bg"], 0.16)
        a = PANEL_ALPHA if k == "bg" else 1.0
        rows.append(f"    [\"{k}\"] = {{ {', '.join(_f(v, a))} }},")
    return ("-- Lua 配色（0–1 的 r, g, b, a）—— 由 ui-craft palette.py 生成\n"
            "-- WoW：frame:SetBackdropColor(unpack(UiCraft[\"bg\"]))；fs:SetTextColor(unpack(UiCraft[\"text\"]))\n"
            "-- Factorio：style.font_color = UiCraft[\"text\"]（Factorio 也接受 0–1 的颜色表）\n"
            "-- LÖVE：love.graphics.setColor(UiCraft[\"accent\"])\n"
            "UiCraft = {\n" + "\n".join(rows) + "\n}\n")


def roblox(L, D, ramps) -> str:
    keys = ["bg", "surface", "surface-raised", "surface-sunken", "text", "text-muted", "text-subtle", "accent", "accent-fg", "accent-text", "ok", "warn", "danger"]
    rows = [f"    {''.join(p.capitalize() for p in k.split('-'))} = Color3.fromRGB({', '.join(str(x) for x in _i(D[k]))})," for k in keys]
    rows.append(f"    Border = Color3.fromRGB({', '.join(str(x) for x in _i(_mix(D['text'], D['bg'], 0.16)))}),")
    return ("-- Roblox 配色 —— 由 ui-craft palette.py 生成。放进 ReplicatedStorage 的 ModuleScript。\n"
            "-- 面板：BackgroundColor3 = Palette.Bg, BackgroundTransparency = 0.08；加 UICorner(8)、UIStroke(Palette.Border, 1)、UIPadding。\n"
            "local Palette = {\n" + "\n".join(rows) + "\n}\nreturn Palette\n")


# ---------------------------------------------------------------- 原生应用框架

def _argb_dart(c: str) -> str:
    r, g, b = _i(c)
    return f"Color(0xFF{r:02X}{g:02X}{b:02X})"


def flutter(L, D, ramps) -> str:
    def scheme(T, bright):
        return (f"ColorScheme(\n    brightness: Brightness.{bright},\n    primary: {_argb_dart(T['accent'])}, onPrimary: {_argb_dart(T['accent-fg'])},\n"
                f"    secondary: {_argb_dart(T['accent-text'])}, onSecondary: {_argb_dart(T['surface'])},\n"
                f"    error: {_argb_dart(T['danger'])}, onError: {_argb_dart(T['surface'])},\n"
                f"    surface: {_argb_dart(T['surface'])}, onSurface: {_argb_dart(T['text'])},\n"
                f"    onSurfaceVariant: {_argb_dart(T['text-muted'])}, outline: {_argb_dart(T['border-strong'] if not T['border-strong'].startswith('oklch(1') else _mix(T['text'], T['bg'], .24))},\n"
                f"    outlineVariant: {_argb_dart(T['border'] if not T['border'].startswith('oklch(1') else _mix(T['text'], T['bg'], .14))},\n"
                f"    surfaceContainerHighest: {_argb_dart(T['surface-sunken'])}, primaryContainer: {_argb_dart(T['accent-subtle'])},\n"
                f"    onPrimaryContainer: {_argb_dart(T['text'])},\n  )")
    return f"""// Flutter 主题 —— 由 ui-craft palette.py 生成。MaterialApp(theme: uiCraftLight, darkTheme: uiCraftDark)
import 'package:flutter/material.dart';

final uiCraftLight = ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: {_argb_dart(L['bg'])},
  colorScheme: const {scheme(L, 'light')},
);

final uiCraftDark = ThemeData(
  useMaterial3: true,
  scaffoldBackgroundColor: {_argb_dart(D['bg'])},
  colorScheme: const {scheme(D, 'dark')},
);
"""


def compose(L, D, ramps) -> str:
    def c(x):
        r, g, b = _i(x)
        return f"Color(0xFF{r:02X}{g:02X}{b:02X})"
    def scheme(fn, T):
        return (f"val UiCraft{fn.capitalize()} = {fn}ColorScheme(\n    primary = {c(T['accent'])}, onPrimary = {c(T['accent-fg'])},\n"
                f"    primaryContainer = {c(T['accent-subtle'])}, onPrimaryContainer = {c(T['text'])},\n"
                f"    background = {c(T['bg'])}, onBackground = {c(T['text'])},\n    surface = {c(T['surface'])}, onSurface = {c(T['text'])},\n"
                f"    surfaceVariant = {c(T['surface-sunken'])}, onSurfaceVariant = {c(T['text-muted'])},\n"
                f"    outline = {c(_mix(T['text'], T['bg'], .24))}, error = {c(T['danger'])},\n)")
    return f"""// Jetpack Compose 配色 —— 由 ui-craft palette.py 生成。MaterialTheme(colorScheme = if (isSystemInDarkTheme()) UiCraftDark else UiCraftLight)
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

{scheme('light', L)}

{scheme('dark', D)}
"""


def swiftui(L, D, ramps) -> str:
    keys = ["bg", "surface", "surface-sunken", "text", "text-muted", "text-subtle", "accent", "accent-fg", "accent-text", "accent-subtle", "ok", "warn", "danger"]
    def comp(x):
        r, g, b, _ = _rgb(x)
        return f"{r:.3f}, {g:.3f}, {b:.3f}"
    rows = []
    for k in keys:
        name = "uc" + "".join(p.capitalize() for p in k.split("-"))
        rows.append(f"    static let {name} = Color.adaptive(light: ({comp(L[k])}), dark: ({comp(D[k])}))")
    return ("// SwiftUI 配色 —— 由 ui-craft palette.py 生成。用法：.foregroundStyle(Color.ucText)、.tint(.ucAccent)\n"
            "import SwiftUI\n#if canImport(UIKit)\nimport UIKit\n#endif\n\nextension Color {\n"
            "    static func adaptive(light: (Double, Double, Double), dark: (Double, Double, Double)) -> Color {\n"
            "        #if canImport(UIKit)\n"
            "        return Color(UIColor { $0.userInterfaceStyle == .dark\n"
            "            ? UIColor(red: dark.0, green: dark.1, blue: dark.2, alpha: 1)\n"
            "            : UIColor(red: light.0, green: light.1, blue: light.2, alpha: 1) })\n"
            "        #else\n"
            "        return Color(red: light.0, green: light.1, blue: light.2)\n"
            "        #endif\n    }\n\n" + "\n".join(rows) + "\n}\n")


def streamlit(L, D, ramps) -> str:
    return f"""# Streamlit 主题 —— 由 ui-craft palette.py 生成。存成 .streamlit/config.toml
[theme]
base = "light"
primaryColor = "{_hex(L['accent'])}"
backgroundColor = "{_hex(L['bg'])}"
secondaryBackgroundColor = "{_hex(L['surface-sunken'])}"
textColor = "{_hex(L['text'])}"
font = "sans serif"
"""


def gradio(L, D, ramps) -> str:
    def color(name, r):
        args = ", ".join(f"c{s}=\"{v}\"" for s, v in r.items())
        return f"gr.themes.Color(name=\"{name}\", {args})"
    return f"""# Gradio 主题 —— 由 ui-craft palette.py 生成。用法：gr.Blocks(theme=ui_craft_theme)
import gradio as gr

ui_craft_theme = gr.themes.Base(
    primary_hue={color('uc_accent', ramps['accent'])},
    neutral_hue={color('uc_neutral', ramps['neutral'])},
    radius_size=gr.themes.sizes.radius_md,
).set(
    body_background_fill="{_hex(L['bg'])}",
    block_background_fill="{_hex(L['surface'])}",
    button_primary_background_fill="{_hex(L['accent'])}",
    button_primary_text_color="{_hex(L['accent-fg'])}",
)
"""


FORMATS = {
    "imgui": (imgui, "Dear ImGui（C++）：mod 菜单、游戏内工具、模拟器与 ReShade 覆盖层"),
    "imgui-cs": (imgui_cs, "ImGui.NET（C#）"),
    "unity": (unity, "Unity：C# 静态颜色 + IMGUI 皮肤（BepInEx / MelonLoader 菜单）"),
    "uss": (uss, "Unity UI Toolkit 样式表"),
    "godot": (godot, "Godot 4 Theme（GDScript）"),
    "minecraft": (minecraft, "Minecraft Java：ARGB int 常量"),
    "lua": (lua, "Lua 颜色表：WoW 插件、Factorio、LÖVE"),
    "roblox": (roblox, "Roblox：Color3 调色板模块"),
    "flutter": (flutter, "Flutter：ThemeData 浅色与暗色"),
    "compose": (compose, "Jetpack Compose：ColorScheme"),
    "swiftui": (swiftui, "SwiftUI：自适应明暗的 Color 扩展"),
    "streamlit": (streamlit, "Streamlit：.streamlit/config.toml"),
    "gradio": (gradio, "Gradio：gr.themes.Base"),
}
