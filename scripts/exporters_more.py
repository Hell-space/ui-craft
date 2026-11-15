#!/usr/bin/env python3
"""更多配色导出：tkinter/ttk、界面里的图表（ECharts、Chart.js、matplotlib、Plotly）、终端界面（Textual、Rich）、微信小程序（WXSS）。
由 exporters.py 注册，经 palette.py --export 调用。
"""
from __future__ import annotations

import json

import colorkit as ck


def _rgba(c):
    return ck.to_rgba(c)


def _hex(c):
    return ck.hex_of(_rgba(c)[:3])


_mix = ck.theme_mix


def solid(T: dict) -> dict:
    """把带透明度的角色色（暗色的线）合成到底色上，得到到处能用的实色 hex。"""
    bg = _rgba(T["bg"])
    out = {}
    for k, v in T.items():
        r, g, b, a = _rgba(v)
        out[k] = ck.theme_hex((r * a + bg[0] * (1 - a), g * a + bg[1] * (1 - a), b * a + bg[2] * (1 - a)))
    return out


def _cat_lc(h: float, dark: bool) -> tuple[float, float]:
    """分类色的明度与彩度随色相走：橙、黄、黄绿在和蓝紫同样的明度下会发棕、发橄榄，要更亮。"""
    if 45 <= h < 75:
        L, C = 0.72, 0.15
    elif 75 <= h < 135:
        L, C = 0.80, 0.15
    elif 135 <= h < 200:
        L, C = 0.66, 0.13
    else:
        L, C = 0.62, 0.14
    return (min(0.86, L + 0.08), C) if dark else (L, C)


def series(T: dict, n: int = 8, dark: bool = False) -> list[str]:
    """图表与分类的颜色：第一个是强调色，其余色相拉开（彼此至少差 28°），并避开危险色的色相，免得被读成“出错”。"""
    r, g, b, _ = _rgba(T["accent"])
    _, _, H0 = ck.srgb_to_oklch(r, g, b)
    dr, dg, db, _ = _rgba(T["danger"])
    _, _, Hd = ck.srgb_to_oklch(dr, dg, db)

    def far(h, others, gap=28):
        return all(min(abs(h - x), 360 - abs(h - x)) >= gap for x in others)
    out, hues = [_hex(T["accent"])], [H0]
    for d in (150, 60, 210, 105, 270, 30, 330, 180, 90, 240, 300, 15, 45, 75, 120, 165, 195, 225, 255, 285, 315, 345):
        if len(out) >= n:
            break
        h = (H0 + d) % 360
        if far(h, hues) and far(h, [Hd]):
            out.append(ck.hex_of(ck.oklch_to_srgb(*_cat_lc(h, dark), h)))
            hues.append(h)
    for d in (150, 60, 210, 105, 270, 30, 330, 180):        # 实在凑不够时放宽间距
        if len(out) >= n:
            break
        h = (H0 + d) % 360
        if far(h, hues, 12):
            out.append(ck.hex_of(ck.oklch_to_srgb(*_cat_lc(h, dark), h)))
            hues.append(h)
    return out[:n]


# ---------------------------------------------------------------- tkinter / ttk

def _lum(h):
    r, g, b = _rgba(h)[:3]

    def f(v):
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def _contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _ok(L, C, H):
    return ck.hex_of(ck.oklch_to_srgb(*ck.theme_tone(L, C, H)))


def _plane(accent, dark):
    """顶栏色块：沿用强调色的色相和彩度，明度压到托得住白字（≥5.6:1）；
    橙、琥珀、黄、黄绿压暗会发棕发脏，改成亮色块配深色字。返回 (色块, 字色, 次要字色)。"""
    r, g, b, _ = _rgba(accent)
    L0, C0, H = ck.srgb_to_oklch(r, g, b)
    C = min(max(C0, 0.10), 0.19)
    if 40 <= H <= 135:
        plane = _ok(max(L0, 0.76) - (0.06 if dark else 0.0), C, H)
        ink = _ok(0.22, 0.04, H)
    else:
        L = min(L0, 0.62)
        while L > 0.3 and _contrast(_ok(L, C, H), "#FFFFFF") < 5.6:
            L -= 0.005
        plane = _ok(L - (0.07 if dark else 0.0), C * (0.9 if dark else 1.0), H)      # 暗色主题里色块再沉一点，免得刺眼
        ink = "#FFFFFF"
    t = 0.70
    while t < 0.98 and _contrast(_mix(ink, plane, t), plane) < 4.5:
        t += 0.01
    return plane, ink, _mix(ink, plane, t)


def ttk(L, D, ramps) -> str:
    l, d = solid(L), solid(D)
    keys = ["bg", "surface", "surface-sunken", "border", "border-strong", "text", "text-muted", "text-subtle",
            "accent", "accent-fg", "accent-text", "accent-subtle", "ok", "warn", "danger", "stage", "stage-ink", "stage-muted"]
    # 暗色主题的强调色：提亮但保留彩度（默认的暗色强调色偏粉，放在桌面窗口里显得发灰）
    r, g, b, _ = _rgba(l["accent"])
    _, Ca, Ha = ck.srgb_to_oklch(r, g, b)
    _, _, dark_hue = ck.srgb_to_oklch(*_rgba(d["accent"])[:3])
    if not 85 <= Ha <= 130 and not ck.green_hue(dark_hue):
        d["accent"] = _ok(0.72, min(max(Ca, 0.10), 0.17), Ha)
        d["accent-fg"] = _ok(0.18, 0.03, Ha)
    for T, dark in ((l, False), (d, True)):
        T["accent-hover"] = _mix(T["accent"], T["text"], 0.88)
        T["accent-press"] = _mix(T["accent"], T["text"], 0.78)
        # 色块（顶栏、舞台）：强调色本身，不是近黑的墨色——一个窗口里唯一的大面积颜色
        T["stage"], T["stage-ink"], T["stage-muted"] = _plane(l["accent"], dark)
        T["stage-raised"] = _mix(T["stage-ink"], T["stage"], 0.14)
        T["stage-track"] = _mix(T["stage-ink"], T["stage"], 0.22)
        T["stage-btn-hover"] = _mix(T["stage-ink"], T["stage"], 0.90)
        T["stage-btn-press"] = _mix(T["stage-ink"], T["stage"], 0.80)
        T["ink-hover"] = _mix(T["text"], T["bg"], 0.86)
        T["ink-press"] = _mix(T["text"], T["bg"], 0.76)
        T["hover"] = _mix(T["text"], T["surface"], 0.07 if dark else 0.045)
        T["series"] = series(T, 6, dark)
        swatches = [T["accent"], T["ok"], T["warn"], T["danger"], *T["series"]]
        T["layers"] = dict(zip(swatches, map(ck.layer_color, swatches)))
    keys += ["accent-hover", "accent-press", "ink-hover", "ink-press", "hover", "stage-raised", "stage-track",
             "stage-btn-hover", "stage-btn-press", "series", "layers"]
    light = json.dumps({k: l[k] for k in keys}, indent=4, ensure_ascii=False)
    dark = json.dumps({k: d[k] for k in keys}, indent=4, ensure_ascii=False)
    return TTK_MODULE.replace("__LIGHT__", light).replace("__DARK__", dark)


TTK_MODULE = r'''"""tkinter / ttk 主题 —— 由 ui-craft palette.py 生成。存成 ui_craft_ttk.py 放在项目里。

用法：
    import tkinter as tk
    from tkinter import ttk
    import ui_craft_ttk as ui

    ui.enable_dpi_awareness()        # 必须在创建 Tk() 之前：否则 Windows 高分屏上文字是糊的
    root = tk.Tk()
    ui.apply(root)                   # 暗色：ui.apply(root, dark=True)

控件都是圆角、抗锯齿的（用程序生成的可拉伸图片画），只用 ttk 控件即可。照 templates/tkinter/app.py 的结构写最省事。

  表面   ui.band(root)              整幅强调色顶栏：一个窗口一条，放标题和全窗口最重要的数字；里面的文字用 Stage. 前缀
         ui.card(父容器)            圆角卡片（浅色主题带一层很淡的投影）；里面的文字用 Card. 前缀
         ui.stage(父容器)           圆角的强调色块（不用整幅顶栏时用）
         ui.group(父容器, on=…)     卡片、色块里的分组容器，on = "card" / "stage" / "page"
         这几个函数会把内边距交给控件——ttk 的框架不认样式里的内边距，直接写 ttk.Frame(style=…) 内容会贴边
  列表   ui.scroll_area(卡片)       返回 (外框, 内容框)：滚轮可滚，内容放不下时才出现细滚动条
         ui.row(内容框)             一行可悬停的列表项（圆角浅底高亮），行里用 Card. 样式，悬停时自动切换
         ui.avatar(行, "餐", 颜色)  圆形分类头像；ui.dot(root, 颜色, gap=…) 小圆点图片（gap 是圆点右边留的空）
  按钮   Accent.TButton（主操作，一屏一个）、Ink.TButton（深色主按钮）、TButton（普通）、Ghost.TButton（次要）、
         Stage.TButton / StageGhost.TButton（色块上的按钮）；在卡片里加 Card. 前缀
  选择   Card.Chip.TRadiobutton（胶囊选项，可配 image=ui.dot(...)、compound="left"）、Card.TCheckbutton、Card.TCombobox
  文字   Title / Heading / Muted / Small / Eyebrow / Display（大数字）/ Unit / Num（金额）/ NumOk / NumDanger / Danger / Ok
         加前缀 Card. / Stage.，例如 Card.Heading.TLabel、Stage.Display.TLabel
  进度   ui.progress(父容器, 值, 颜色, on="card")；Stage.Horizontal.TProgressbar
  颜色   ui.COLORS 是当前主题的颜色表（c["series"] 是 6 个分类色）；ui.mix(a, b, t) 混色，给 Canvas 模拟半透明
  动效   ui.tween(控件, 毫秒, 每帧函数)：每帧函数收到 0–1 的缓出进度，用于数字滚动、进度条和图表生长
  窗口   ui.titlebar(root, 颜色, 文字色)：Windows 11 上把标题栏染成顶栏的颜色，标题栏和顶栏连成一片

tk.Text、tk.Listbox、tk.Canvas 这些经典控件也会自动套上颜色。
"""
import base64
import math
import struct
import sys
import time
import tkinter as tk
import zlib
from tkinter import ttk
from tkinter import font as tkfont

LIGHT = __LIGHT__

DARK = __DARK__

COLORS = LIGHT          # apply() 之后是当前主题的颜色表
DARK_MODE = False
FAMILY = NUM_FAMILY = None
BASE = 10
K = 1.0                 # 高分屏倍数：150% 缩放时是 1.5


def enable_dpi_awareness():
    """Windows 上让程序按真实分辨率绘制。不调用的话系统会把整个窗口放大，文字发虚。"""
    if sys.platform.startswith("win"):
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass


def P(n):
    """按高分屏倍数换算像素。"""
    return max(1, int(round(n * K)))


# ---------------------------------------------------------------- 字体

def _pick(root, names):
    have = set(tkfont.families(root))
    for f in names:
        if f in have:
            return f
    return tkfont.nametofont("TkDefaultFont", root).actual("family")


def _family(root):
    return _pick(root, ("Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "Noto Sans SC",
                        "Segoe UI", "SF Pro Text", "Helvetica Neue", "DejaVu Sans"))


def _num_family(root):
    # 数字用一款数字好看的无衬线；Windows 11 上是 Segoe UI Variable 的半粗体
    return _pick(root, ("Segoe UI Variable Display Semib", "Segoe UI Semibold", "SF Pro Display", "Helvetica Neue",
                        "Segoe UI", "DejaVu Sans"))


# ---------------------------------------------------------------- 颜色与抗锯齿图片（纯 Python 生成 PNG，不依赖 Pillow）

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    """a 占 t、b 占 1−t 的混色。Canvas 没有透明度，用它模拟“白色 40% 叠在色块上”。"""
    ra, rb = _rgb(a), _rgb(b)
    return "#%02X%02X%02X" % tuple(int(round(x * t + y * (1 - t))) for x, y in zip(ra, rb))


def _png(w, h, pixel, gx=0, gy=0):
    """pixel(x, y) -> (r, g, b, a)，a 为 0–1。返回 base64 PNG。
    gx / gy：把正中那一列 / 一行再复制这么多份。ttk 拉伸图片元素时是平铺中间那块，中间只有两三个像素的话，
    一张卡片要画几万次半透明小块，窗口打开要好几秒；中间加宽到近百像素就只要画几十次。"""
    rows = []
    for y in range(h):
        row = bytearray()
        for x in range(w):
            r, g, b, a = pixel(x + 0.5, y + 0.5)
            row += bytes((int(r), int(g), int(b), max(0, min(255, int(round(a * 255))))))
        if gx:
            m = (w // 2) * 4
            row = row[:m] + row[m:m + 4] * gx + row[m:]
        rows.append(bytes(row))
    if gy:
        mid = h // 2
        rows = rows[:mid] + [rows[mid]] * gy + rows[mid:]
    w, h = w + gx, h + gy

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + r for r in rows)
    data = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    return base64.b64encode(data).decode("ascii")


GROW = 96   # 可拉伸图片中间那块的宽度（见 _png 的说明）


def _clamp(v):
    return 0.0 if v < 0 else (1.0 if v > 1 else v)


def _rrect_sd(x, y, w, h, r):
    """点到圆角矩形边界的有向距离（里面为负）。"""
    qx = abs(x - w / 2) - (w / 2 - r)
    qy = abs(y - h / 2) - (h / 2 - r)
    ox, oy = max(qx, 0.0), max(qy, 0.0)
    return (ox * ox + oy * oy) ** 0.5 + min(max(qx, qy), 0.0) - r


def _shape(w, h, r, fill, border=None, bw=1.0, inset=0.0):
    """圆角矩形：fill 填充色（None 为空心）、border 描边色（None 为无描边）。两者都是 None 时是全透明。"""
    f = _rgb(fill) if fill else None
    b = _rgb(border) if border else None

    def px(x, y):
        if f is None and b is None:
            return (0, 0, 0, 0)
        sd = _rrect_sd(x - inset, y - inset, w - 2 * inset, h - 2 * inset, max(0.5, r))
        a_out = _clamp(0.5 - sd)
        if a_out <= 0:
            return (0, 0, 0, 0)
        if b is None:
            return (*f, a_out)
        a_in = _clamp(0.5 - (sd + bw))
        a_b = a_out - a_in
        if f is None:
            return (*b, a_b)
        col = tuple((f[i] * a_in + b[i] * a_b) / a_out for i in range(3))
        return (*col, a_out)
    return px


def _lifted(w, h, r, fill, border, m, alpha):
    """带一层柔和投影的圆角矩形：四周留 m 像素给投影，卡片本体略微上移，投影多露在下边。"""
    f, b = _rgb(fill), (_rgb(border) if border else None)
    soft = max(1.0, m * 0.55)

    def px(x, y):
        sd = _rrect_sd(x - m, y - m + 1, w - 2 * m, h - 2 * m, r)
        a_out = _clamp(0.5 - sd)
        if b is not None and a_out > 0:
            a_in = _clamp(0.5 - (sd + 1.0))
            col = [(f[i] * a_in + b[i] * (a_out - a_in)) / a_out for i in range(3)]
        else:
            col = list(f)
        sd2 = _rrect_sd(x - m, y - m - 0.5, w - 2 * m, h - 2 * m, r)
        a_sh = alpha * math.exp(-max(sd2, 0.0) / soft)
        A = a_out + a_sh * (1 - a_out)
        if A <= 0.002:
            return (0, 0, 0, 0)
        return (col[0] * a_out / A, col[1] * a_out / A, col[2] * a_out / A, A)
    return px


class _Kit:
    def __init__(self, root):
        self.root, self.keep = root, []

    def img(self, w, h, pixel, gx=0, gy=0):
        im = tk.PhotoImage(master=self.root, data=_png(int(w), int(h), pixel, gx, gy))
        im.small = (int(w), int(h))           # 加宽前的尺寸：当作控件的最小尺寸，不然控件会被撑大
        self.keep.append(im)
        return im

    def box(self, r, fill, border=None, bw=1.0):
        """可九宫格拉伸的圆角框图片（中间加宽过，拉伸时画得快）。"""
        size = int(2 * r + 6)
        return self.img(size, size, _shape(size, size, r, fill, border, bw), GROW, GROW)

    def lifted(self, r, fill, border, m, alpha):
        size = int(2 * (r + m) + 6)
        return self.img(size, size, _lifted(size, size, r, fill, border, m, alpha), GROW, GROW)


def _seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ((px - ax - u * dx) ** 2 + (py - ay - u * dy) ** 2) ** 0.5


def _store(root, key):
    return root.__dict__.setdefault(f"_ui_craft_{key}", {})


def dot(root, color, size=None, gap=0):
    """分类圆点图片。gap 是圆点右边留的空白，配 compound="left" 时让圆点和文字隔开。"""
    s = size or max(8, P(10))
    key = (color, s, gap)
    store = _store(root, "dots")
    if key not in store:
        c = _rgb(color)
        store[key] = tk.PhotoImage(master=root, data=_png(s + gap, s, lambda x, y: (
            *c, _clamp(0.5 - (((x - s / 2) ** 2 + (y - s / 2) ** 2) ** 0.5 - s * 0.36)))))
    return store[key]


def _prefix(on):
    return {"card": "Card.", "stage": "Stage.", "page": "", "hover": "Hover."}[on]


# ---------------------------------------------------------------- 表面

def card(parent, padding=None, **kw):
    """圆角卡片。用它创建，内边距才会生效（ttk 的框架不认样式里的内边距）。卡片里的文字用 Card. 前缀的样式。"""
    return ttk.Frame(parent, style="Card.TFrame", padding=P(20) if padding is None else padding, **kw)


def stage(parent, padding=None, **kw):
    """圆角的强调色块：一屏一块，放全窗口最重要的那个数字。里面的文字用 Stage. 前缀的样式。"""
    return ttk.Frame(parent, style="Stage.TFrame", padding=(P(26), P(22)) if padding is None else padding, **kw)


def band(parent, padding=None, **kw):
    """整幅的强调色顶栏（不带圆角，贴满窗口宽度）。配 titlebar(root, COLORS["stage"], COLORS["stage-ink"]) 和标题栏连成一片。"""
    return ttk.Frame(parent, style="Stage.Plain.TFrame", padding=(P(28), P(16), P(28), P(22)) if padding is None else padding, **kw)


def group(parent, on="card", **kw):
    """卡片或色块里的分组容器（背景跟随所在的表面）。on = "card" / "stage" / "page"。"""
    return ttk.Frame(parent, style={"card": "Card.Plain.TFrame", "stage": "Stage.Plain.TFrame", "page": "TFrame",
                                    "hover": "Hover.Plain.TFrame"}[on], **kw)


def _swap(w, a, b):
    try:
        s = str(w.cget("style"))
    except tk.TclError:
        s = ""
    if s.startswith(a):
        w.configure(style=b + s[len(a):])
    for ch in w.winfo_children():
        _swap(ch, a, b)


def row(parent, padding=None, **kw):
    """可悬停的列表行：鼠标移上去整行出现圆角浅底。行里的控件用 Card. 前缀的样式（悬停时自动换成 Hover. 前缀）。
    要响应点击：创建完行里的控件后调用 ui.on_click(行, 函数)。"""
    r = ttk.Frame(parent, style="Row.TFrame", padding=(P(10), P(8)) if padding is None else padding, **kw)

    def inside(e):
        try:
            w = r.winfo_containing(e.x_root, e.y_root)
        except (KeyError, tk.TclError):
            return False
        while w is not None:
            if w is r:
                return True
            w = w.master
        return False

    def enter(_e):
        if "active" not in r.state():
            r.state(["active"])
            for ch in r.winfo_children():
                _swap(ch, "Card.", "Hover.")

    def leave(e):
        if inside(e):
            return
        r.state(["!active"])
        for ch in r.winfo_children():
            _swap(ch, "Hover.", "Card.")
    r.bind("<Enter>", enter, add="+")
    r.bind("<Leave>", leave, add="+")
    return r


def on_click(widget, fn):
    """给一个容器和它里面所有控件绑定单击。"""
    widget.bind("<Button-1>", lambda e: fn(), add="+")
    widget.configure(cursor="hand2")
    for ch in widget.winfo_children():
        on_click(ch, fn)


def avatar(parent, text, color, on="card", size=34):
    """圆形分类头像：浅色圆底 + 一个字。颜色用 COLORS["series"] 里的分类色。"""
    c = COLORS
    s = P(size)
    root = parent.winfo_toplevel()
    key = color.lstrip("#").upper()
    store = _store(root, "avatars")
    if (key, s) not in store:
        layer = c["layers"].get(color.upper(), color)
        tint = _rgb(mix(layer, c["surface"], 0.26 if DARK_MODE else 0.15))
        store[(key, s)] = tk.PhotoImage(master=root, data=_png(s, s, lambda x, y: (
            *tint, _clamp(0.5 - (((x - s / 2) ** 2 + (y - s / 2) ** 2) ** 0.5 - s / 2 + 0.5)))))
        fg = color if DARK_MODE else mix(color, c["text"], 0.8)
        st = ttk.Style(root)
        for prefix, bg in (("Card.", c["surface"]), ("Hover.", c["hover"]), ("", c["bg"]), ("Stage.", c["stage"])):
            st.configure(f"{prefix}Av{key}.TLabel", background=bg, foreground=fg, font=(FAMILY, BASE, "bold"),
                         anchor="center", padding=0)
    return ttk.Label(parent, image=store[(key, s)], text=text, compound="center", style=f"{_prefix(on)}Av{key}.TLabel")


def progress(parent, value=0, color=None, on="card", **kw):
    """圆头进度条，可指定颜色（分类色、危险色）。"""
    c = COLORS
    color = color or c["accent"]
    root = parent.winfo_toplevel()
    st = ttk.Style(root)
    prefix = _prefix(on)
    tag = "UcDark" if DARK_MODE else "UcLight"
    key = color.lstrip("#").upper()
    el = f"{tag}.Bar{key}.pbar"
    if el not in st.element_names():
        h = P(6)
        w = h * 2 + 4
        im = tk.PhotoImage(master=root, data=_png(w, h, _shape(w, h, h / 2, color), GROW, 0))
        _store(root, "bars")[el] = im
        st.element_create(el, "image", im, border=(h // 2 + 1, 0), sticky="nswe", padding=0, width=w, height=h)
    name = f"{prefix}B{key}.Horizontal.TProgressbar"
    st.layout(name, [(f"{tag}.{prefix}Bar.trough", {"sticky": "nswe", "children": [(el, {"side": "left", "sticky": "ns"})]})])
    st.configure(name, thickness=P(6), background={"Card.": c["surface"], "Stage.": c["stage"]}.get(prefix, c["bg"]))
    return ttk.Progressbar(parent, style=name, value=value, **kw)


def scroll_area(parent, on="card", height=120):
    """可滚动的区域：返回 (外框, 内容框)。把外框 pack/grid 好，内容放进内容框。滚轮可滚；内容放得下时不显示滚动条。"""
    c = COLORS
    bg = {"card": c["surface"], "page": c["bg"], "stage": c["stage"]}[on]
    outer = group(parent, on=on)
    cv = tk.Canvas(outer, bg=bg, highlightthickness=0, bd=0, height=P(height), width=P(200), yscrollincrement=P(8))
    inner = group(cv, on=on)
    win = cv.create_window(0, 0, window=inner, anchor="nw")
    sb = ttk.Scrollbar(outer, orient="vertical", command=cv.yview)

    def place(a, b):
        sb.set(a, b)
        if float(a) <= 0.0 and float(b) >= 1.0:
            sb.grid_remove()
        else:
            sb.grid()
    cv.configure(yscrollcommand=place)
    cv.grid(row=0, column=0, sticky="nswe")
    sb.grid(row=0, column=1, sticky="ns", padx=(P(4), 0))
    outer.rowconfigure(0, weight=1)
    outer.columnconfigure(0, weight=1)
    inner.bind("<Configure>", lambda e: cv.configure(scrollregion=(0, 0, e.width, e.height)), add="+")
    cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width), add="+")

    def wheel(e):
        try:
            w = cv.winfo_containing(e.x_root, e.y_root)
        except (KeyError, tk.TclError):
            return
        if w is not None and str(w).startswith(str(cv)):
            cv.yview_scroll(int(-e.delta / 120 * 6) if abs(e.delta) >= 120 else (-1 if e.delta > 0 else 1), "units")
    cv.bind_all("<MouseWheel>", wheel, add="+")
    cv.bind_all("<Button-4>", lambda e: cv.yview_scroll(-6, "units") if str(e.widget).startswith(str(cv)) else None, add="+")
    cv.bind_all("<Button-5>", lambda e: cv.yview_scroll(6, "units") if str(e.widget).startswith(str(cv)) else None, add="+")
    return outer, inner


def tween(widget, ms, step, done=None, delay=0):
    """在 ms 毫秒内反复调用 step(进度)，进度按缓出曲线从 0 走到 1。用于数字滚动、进度条和图表生长。
    控件被销毁（比如动画没放完就关了窗口）时自动停下。"""
    pending = {"id": None}

    def cancel(_e=None):
        if pending["id"]:
            try:
                widget.after_cancel(pending["id"])
            except tk.TclError:
                pass
            pending["id"] = None
    widget.bind("<Destroy>", cancel, add="+")

    def start():
        t0 = time.perf_counter()

        def tick():
            pending["id"] = None
            try:
                t = min(1.0, (time.perf_counter() - t0) * 1000 / ms)
                step(1 - (1 - t) ** 3)
            except tk.TclError:
                return
            if t < 1:
                pending["id"] = widget.after(15, tick)
            elif done:
                done()
        tick()
    if delay:
        pending["id"] = widget.after(delay, start)
    else:
        start()


def titlebar(root, color=None, text=None, dark=None):
    """Windows 11：把标题栏染成 color、标题文字用 text；dark 让旧版 Windows 10 也用深色标题栏。其他系统上什么都不做。"""
    if not sys.platform.startswith("win"):
        return

    def go():
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(root.winfo_id()) or root.winfo_id()

            def put(attr, val):
                v = ctypes.c_int(val)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(v), ctypes.sizeof(v))

            def ref(h):
                r, g, b = _rgb(h)
                return r | (g << 8) | (b << 16)
            if dark is not None:
                put(20, 1 if dark else 0)
            if color:
                put(35, ref(color))
            if text:
                put(36, ref(text))
        except Exception:
            pass
    try:
        root.update_idletasks()
    except tk.TclError:
        return
    go()
    root.after(30, go)


# ---------------------------------------------------------------- 主题

def apply(root, dark=False, base_size=10, icon=True):
    global COLORS, DARK_MODE, FAMILY, NUM_FAMILY, BASE, K
    c = COLORS = DARK if dark else LIGHT
    DARK_MODE, BASE = dark, base_size
    family = FAMILY = _family(root)
    numfam = NUM_FAMILY = _num_family(root)
    numw = "normal" if "Semib" in numfam else "bold"
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
        try:
            tkfont.nametofont(name, root).configure(family=family, size=base_size)
        except tk.TclError:
            pass
    K = max(1.0, root.winfo_fpixels("1i") / 96)              # 高分屏倍数，保留小数（150% 缩放就是 1.5）

    kit = _Kit(root)
    root._ui_craft_kit = kit                                  # 保持图片引用，避免被回收
    style = ttk.Style(root)
    style.theme_use("clam")                                   # clam 允许改所有颜色；默认的 vista / aqua 主题改不了
    root.configure(bg=c["bg"])
    tag = "UcDark" if dark else "UcLight"
    made = f"{tag}.Field" in style.element_names()

    def element(name, imgs, border, sticky="nswe", **kw):
        if made:
            return
        default, *states = imgs
        sw, sh = getattr(default, "small", (None, None))
        if sw:
            kw.setdefault("width", sw)
            kw.setdefault("height", sh)
        kw.setdefault("padding", 0)                           # 不然 ttk 会把 border 也当成内边距，控件会被撑得很高
        style.element_create(name, "image", default, *states, border=border, sticky=sticky, **kw)

    style.configure(".", background=c["bg"], foreground=c["text"], fieldbackground=c["surface"],
                    bordercolor=c["border"], lightcolor=c["bg"], darkcolor=c["bg"], troughcolor=c["surface-sunken"],
                    focuscolor=c["accent"], selectbackground=c["accent-subtle"], selectforeground=c["text"],
                    insertcolor=c["text"], arrowcolor=c["text-subtle"], font=(family, base_size))
    style.configure("TFrame", background=c["bg"])

    # ---- 文字（四种底：页面、卡片、悬停的列表行、强调色块）
    for prefix, bg, fg, muted, okc, bad in (
            ("", c["bg"], c["text"], c["text-subtle"], c["ok"], c["danger"]),
            ("Card.", c["surface"], c["text"], c["text-subtle"], c["ok"], c["danger"]),
            ("Hover.", c["hover"], c["text"], c["text-subtle"], c["ok"], c["danger"]),
            ("Stage.", c["stage"], c["stage-ink"], c["stage-muted"], c["stage-ink"], c["stage-ink"])):
        style.configure(f"{prefix}TLabel", background=bg, foreground=fg)
        style.configure(f"{prefix}Title.TLabel", background=bg, foreground=fg, font=(family, base_size + 9, "bold"))
        style.configure(f"{prefix}Heading.TLabel", background=bg, foreground=fg, font=(family, base_size + 2, "bold"))
        style.configure(f"{prefix}Muted.TLabel", background=bg, foreground=muted)
        style.configure(f"{prefix}Small.TLabel", background=bg, foreground=muted, font=(family, base_size - 1))
        style.configure(f"{prefix}Eyebrow.TLabel", background=bg, foreground=muted, font=(family, base_size - 1, "bold"))
        style.configure(f"{prefix}Display.TLabel", background=bg, foreground=fg, font=(numfam, base_size + 26, numw))
        style.configure(f"{prefix}Unit.TLabel", background=bg, foreground=muted, font=(numfam, base_size + 8, numw))
        style.configure(f"{prefix}Num.TLabel", background=bg, foreground=fg, font=(numfam, base_size + 2, numw))
        style.configure(f"{prefix}NumOk.TLabel", background=bg, foreground=okc, font=(numfam, base_size + 2, numw))
        style.configure(f"{prefix}NumDanger.TLabel", background=bg, foreground=bad, font=(numfam, base_size + 2, numw))
        style.configure(f"{prefix}Danger.TLabel", background=bg, foreground=bad)
        style.configure(f"{prefix}Ok.TLabel", background=bg, foreground=okc)
        if prefix:
            style.configure(f"{prefix}Plain.TFrame", background=bg)

    # ---- 卡片与色块（圆角表面）、可悬停的列表行
    r_card, m = P(12), P(3)
    element(f"{tag}.Card.border", [kit.lifted(r_card, c["surface"], c["border"], m, 0.0 if dark else 0.07)], r_card + m + 2)
    element(f"{tag}.Stage.border", [kit.box(r_card, c["stage"])], r_card + 2)
    style.layout("Card.TFrame", [(f"{tag}.Card.border", {"sticky": "nswe"})])
    style.configure("Card.TFrame", background=c["bg"])
    style.layout("Stage.TFrame", [(f"{tag}.Stage.border", {"sticky": "nswe"})])
    style.configure("Stage.TFrame", background=c["bg"])
    r_row = P(8)
    element(f"{tag}.Row.bg", [kit.box(r_row, None), ("active", kit.box(r_row, c["hover"]))], r_row + 2)
    style.layout("Row.TFrame", [(f"{tag}.Row.bg", {"sticky": "nswe"})])
    style.configure("Row.TFrame", background=c["surface"])

    # ---- 按钮
    r_btn = P(8)

    def button(name, on, normal, hover, press, dis, fg, fg_dis, border=None, font=None, ring=None):
        imgs = [kit.box(r_btn, normal, border), ("disabled", kit.box(r_btn, dis)),
                ("pressed", kit.box(r_btn, press, border)), ("active", kit.box(r_btn, hover, border)),
                ("focus", kit.box(r_btn, normal, ring or c["accent"], 1.8))]
        element(f"{tag}.Btn{name}.border", imgs, r_btn + 2)
        sname = "TButton" if name == "Button" else f"{name}.TButton"
        style.layout(sname, [(f"{tag}.Btn{name}.border", {"sticky": "nswe", "children": [
            ("Button.padding", {"sticky": "nswe", "children": [("Button.label", {"sticky": "nswe"})]})]})])
        style.configure(sname, background=on, foreground=fg, padding=(P(16), P(7)), anchor="center",
                        font=font or (family, base_size))
        style.map(sname, foreground=[("disabled", fg_dis)], background=[("active", on)])

    bold = (family, base_size, "bold")
    button("Button", c["bg"], c["surface"], c["hover"], c["border"], c["surface-sunken"], c["text"], c["text-subtle"],
           border=c["border-strong"])
    button("Accent", c["bg"], c["accent"], c["accent-hover"], c["accent-press"], c["surface-sunken"], c["accent-fg"], c["text-subtle"],
           font=bold, ring=c["text"])
    button("Ink", c["bg"], c["text"], c["ink-hover"], c["ink-press"], c["surface-sunken"], c["bg"], c["text-subtle"],
           font=bold, ring=c["accent"])
    # 次要按钮：浅色主题里是浅灰底；暗色主题里要比卡片亮一点（比卡片暗会像个洞）
    ghost, ghost_hover = (c["hover"], mix(c["text"], c["surface"], 0.13)) if dark else (c["surface-sunken"], c["border"])
    button("Ghost", c["bg"], ghost, ghost_hover, c["border-strong"], c["surface-sunken"], c["text"], c["text-subtle"])
    button("Stage", c["stage"], c["stage-ink"], c["stage-btn-hover"], c["stage-btn-press"], c["stage-raised"], c["stage"],
           c["stage-muted"], font=bold, ring=c["stage-muted"])
    button("StageGhost", c["stage"], c["stage-raised"], c["stage-track"], c["stage-track"], c["stage-raised"], c["stage-ink"],
           c["stage-muted"], ring=c["stage-muted"])
    # 卡片里的按钮：外圈透明处要露出卡片色
    for nm in ("TButton", "Accent.TButton", "Ink.TButton", "Ghost.TButton"):
        style.configure(f"Card.{nm}", background=c["surface"])
        style.layout(f"Card.{nm}", style.layout(nm))

    # ---- 输入框、下拉框、数字框
    r_in = P(8)
    fld = [kit.box(r_in, c["surface"], c["border-strong"]), ("disabled", kit.box(r_in, c["surface-sunken"], c["border"])),
           ("focus", kit.box(r_in, c["surface"], c["accent"], 1.8)), ("hover", kit.box(r_in, c["surface"], c["text-subtle"]))]
    element(f"{tag}.Field", fld, r_in + 2)
    style.layout("TEntry", [(f"{tag}.Field", {"sticky": "nswe", "children": [
        ("Entry.padding", {"sticky": "nswe", "children": [("Entry.textarea", {"sticky": "nswe"})]})]})])
    style.configure("TEntry", padding=(P(12), P(7)), foreground=c["text"], insertcolor=c["text"], background=c["bg"])
    style.map("TEntry", foreground=[("disabled", c["text-subtle"])])
    aw, ah = P(24), P(14)

    def chevron(col):
        rgb = _rgb(col)
        x0, x1, x2, y0, y1 = aw * 0.30, aw * 0.47, aw * 0.64, ah * 0.36, ah * 0.66
        t = max(1.1, K * 1.5)
        return lambda x, y: (*rgb, _clamp(0.5 - (min(_seg(x, y, x0, y0, x1, y1), _seg(x, y, x1, y1, x2, y0)) - t / 2)))
    element(f"{tag}.Combobox.arrow", [kit.img(aw, ah, chevron(c["text-subtle"])), ("active", kit.img(aw, ah, chevron(c["text"])))], 0, sticky="")
    style.layout("TCombobox", [(f"{tag}.Field", {"sticky": "nswe", "children": [
        (f"{tag}.Combobox.arrow", {"side": "right", "sticky": ""}),
        ("Combobox.padding", {"expand": "1", "sticky": "nswe", "children": [("Combobox.textarea", {"sticky": "nswe"})]})]})])
    style.configure("TCombobox", padding=(P(12), P(7), P(4), P(7)), foreground=c["text"], background=c["bg"])
    style.map("TCombobox", foreground=[("disabled", c["text-subtle"])], fieldbackground=[("readonly", c["surface"])],
              selectbackground=[("readonly", c["surface"])], selectforeground=[("readonly", c["text"])])
    for nm in ("TEntry", "TCombobox"):
        style.configure(f"Card.{nm}", background=c["surface"])
        style.layout(f"Card.{nm}", style.layout(nm))
    style.map("Card.TCombobox", fieldbackground=[("readonly", c["surface"])], selectbackground=[("readonly", c["surface"])],
              selectforeground=[("readonly", c["text"])])
    style.layout("TSpinbox", [(f"{tag}.Field", {"sticky": "nswe", "children": [
        ("null", {"side": "right", "sticky": "", "children": [("Spinbox.uparrow", {"side": "top", "sticky": "e"}),
                                                                ("Spinbox.downarrow", {"side": "bottom", "sticky": "e"})]}),
        ("Spinbox.padding", {"sticky": "nswe", "children": [("Spinbox.textarea", {"sticky": "nswe"})]})]})])
    style.configure("TSpinbox", padding=(P(12), P(5)), arrowcolor=c["text-subtle"], background=c["surface"],
                    bordercolor=c["surface"], lightcolor=c["surface"], darkcolor=c["surface"], arrowsize=P(9))
    for key, val in {"*TCombobox*Listbox.background": c["surface"], "*TCombobox*Listbox.foreground": c["text"],
                     "*TCombobox*Listbox.selectBackground": c["accent-subtle"], "*TCombobox*Listbox.selectForeground": c["text"],
                     "*TCombobox*Listbox.font": (family, base_size), "*TCombobox*Listbox.relief": "flat",
                     "*TCombobox*Listbox.borderWidth": 0, "*TCombobox*Listbox.highlightThickness": 0}.items():
        root.option_add(key, val)

    # ---- 复选框与单选框（抗锯齿的圆角方框 + 对勾、圆点）
    s = P(18)
    r_cb = max(2.0, s * 0.26)
    pts = [(0.27 * s, 0.53 * s), (0.44 * s, 0.69 * s), (0.74 * s, 0.34 * s)]
    tw = max(1.5, s / 8)

    def check_box(fill, border, mark=None):
        base = _shape(s, s, r_cb, fill, border, 1.3)
        if not mark:
            return base
        mk = _rgb(mark)

        def px(x, y):
            r0, g0, b0, a0 = base(x, y)
            if a0 <= 0:
                return (0, 0, 0, 0)
            a = _clamp(0.5 - (min(_seg(x, y, *pts[0], *pts[1]), _seg(x, y, *pts[1], *pts[2])) - tw / 2))
            return (r0 * (1 - a) + mk[0] * a, g0 * (1 - a) + mk[1] * a, b0 * (1 - a) + mk[2] * a, a0)
        return px

    def radio(fill, border, inner=None):
        f, b = _rgb(fill), _rgb(border)
        i = _rgb(inner) if inner else None

        def px(x, y):
            d = ((x - s / 2) ** 2 + (y - s / 2) ** 2) ** 0.5
            a_out = _clamp(0.5 - (d - s / 2 + 0.5))
            if a_out <= 0:
                return (0, 0, 0, 0)
            a_in = _clamp(0.5 - (d - s / 2 + 1.8))
            col = [(f[j] * a_in + b[j] * (a_out - a_in)) / a_out for j in range(3)]
            if i:
                a_dot = _clamp(0.5 - (d - s * 0.19))
                col = [col[j] * (1 - a_dot) + i[j] * a_dot for j in range(3)]
            return (*col, a_out)
        return px

    wide = s + P(8)                                            # 元素比图片宽、图片靠左：指示器和文字之间留出距离
    cbs = [kit.img(s, s, check_box(c["surface"], c["border-strong"])), ("disabled", kit.img(s, s, check_box(c["surface-sunken"], c["border"]))),
           ("selected", kit.img(s, s, check_box(c["accent"], c["accent"], c["accent-fg"]))),
           ("active", kit.img(s, s, check_box(c["surface"], c["accent"])))]
    rbs = [kit.img(s, s, radio(c["surface"], c["border-strong"])), ("disabled", kit.img(s, s, radio(c["surface-sunken"], c["border"]))),
           ("selected", kit.img(s, s, radio(c["accent"], c["accent"], c["accent-fg"]))),
           ("active", kit.img(s, s, radio(c["surface"], c["accent"])))]
    element(f"{tag}.Check.indicator", cbs, 0, sticky="w", width=wide)
    element(f"{tag}.Radio.indicator", rbs, 0, sticky="w", width=wide)
    for prefix, bg in (("", c["bg"]), ("Card.", c["surface"]), ("Stage.", c["stage"])):
        fg = c["stage-ink"] if prefix == "Stage." else c["text"]
        for w, el in (("TCheckbutton", f"{tag}.Check.indicator"), ("TRadiobutton", f"{tag}.Radio.indicator")):
            base_name = w[1:]
            style.layout(f"{prefix}{w}", [(f"{base_name}.padding", {"sticky": "nswe", "children": [
                (el, {"side": "left", "sticky": ""}),
                (f"{base_name}.focus", {"side": "left", "sticky": "w", "children": [(f"{base_name}.label", {"sticky": "nswe"})]})]})])
            style.configure(f"{prefix}{w}", padding=(0, P(3)), focusthickness=0, background=bg, foreground=fg)
            style.map(f"{prefix}{w}", foreground=[("disabled", c["text-subtle"])], background=[("active", bg)])

    # ---- 胶囊选项（单选的一组标签）：未选是灰色描边，选中是强调色描边加浅底
    r_chip = P(12)
    element(f"{tag}.Chip.bg", [kit.box(r_chip, c["surface"], c["border-strong"]),
                                ("selected", kit.box(r_chip, c["accent-subtle"], c["accent"], 1.5)),
                                ("active", kit.box(r_chip, c["hover"], c["text-subtle"]))], r_chip + 2)
    for prefix, bg in (("", c["bg"]), ("Card.", c["surface"])):
        nm = f"{prefix}Chip.TRadiobutton"
        style.layout(nm, [(f"{tag}.Chip.bg", {"sticky": "nswe", "children": [("Radiobutton.padding", {"sticky": "nswe", "children": [
            ("Radiobutton.label", {"sticky": "nswe"})]})]})])
        style.configure(nm, background=bg, foreground=c["text"], padding=(P(12), P(5)), focusthickness=0, anchor="center")
        style.map(nm, foreground=[("selected", c["accent-text"]), ("disabled", c["text-subtle"])], background=[("active", bg)],
                  font=[("selected", bold)])

    # ---- 标签页：胶囊式，选中的那一格是一块白色圆角
    r_tab = P(8)
    seg_bg = kit.box(r_tab + P(3), c["surface-sunken"])
    tab_imgs = [kit.box(r_tab, None), ("selected", kit.box(r_tab, c["surface"], c["border"])),
                ("active", kit.box(r_tab, c["border"]))]
    element(f"{tag}.Tab", tab_imgs, r_tab + 2)
    element(f"{tag}.Tabs.bg", [seg_bg], r_tab + P(3) + 2)
    for nb in ("TNotebook", "Pill.TNotebook"):
        style.layout(f"{nb}.Tab", [(f"{tag}.Tab", {"sticky": "nswe", "children": [
            ("Notebook.padding", {"sticky": "nswe", "children": [("Notebook.label", {"sticky": ""})]})]})])
        style.configure(f"{nb}.Tab", padding=(P(16), P(7)), foreground=c["text-subtle"], background=c["surface-sunken"],
                        font=(family, base_size))
        style.map(f"{nb}.Tab", foreground=[("selected", c["text"]), ("active", c["text"])],
                  background=[("selected", c["surface-sunken"])], font=[("selected", bold)])
        style.layout(nb, [("Notebook.client", {"sticky": "nswe"})])
        style.configure(nb, background=c["bg"], tabmargins=(0, 0, 0, P(12)), borderwidth=0, bordercolor=c["bg"],
                        lightcolor=c["bg"], darkcolor=c["bg"], tabposition="nw")

    # ---- 表格（Treeview）：放在卡片里；行少、要好看时改用 scroll_area + row
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Treeview", background=c["surface"], fieldbackground=c["surface"], foreground=c["text"],
                    rowheight=P(base_size * 3.3), borderwidth=0, font=(family, base_size))
    style.map("Treeview", background=[("selected", c["accent-subtle"])], foreground=[("selected", c["text"])])
    style.configure("Treeview.Heading", background=c["surface"], foreground=c["text-subtle"], bordercolor=c["surface"],
                    lightcolor=c["surface"], darkcolor=c["surface"], relief="flat", padding=(P(4), P(4), P(4), P(8)),
                    font=(family, base_size - 1, "bold"))
    style.map("Treeview.Heading", background=[("active", c["surface"])], foreground=[("active", c["text"])])

    # ---- 进度条：细、圆头；色块上有一版白色的
    h_bar = P(6)

    def pill(col):
        w = h_bar * 2 + 4
        return kit.img(w, h_bar, _shape(w, h_bar, h_bar / 2, col), GROW, 0)
    for prefix, trough, fill, on in (("", c["surface-sunken"], c["accent"], c["bg"]),
                                     ("Card.", c["surface-sunken"], c["accent"], c["surface"]),
                                     ("Stage.", c["stage-track"], c["stage-ink"], c["stage"])):
        element(f"{tag}.{prefix}Bar.trough", [pill(trough)], (h_bar // 2 + 1, 0))
        element(f"{tag}.{prefix}Bar.pbar", [pill(fill)], (h_bar // 2 + 1, 0))
        style.layout(f"{prefix}Horizontal.TProgressbar", [(f"{tag}.{prefix}Bar.trough", {"sticky": "nswe", "children": [
            (f"{tag}.{prefix}Bar.pbar", {"side": "left", "sticky": "ns"})]})])
        style.configure(f"{prefix}Horizontal.TProgressbar", thickness=h_bar, background=on)

    # ---- 滚动条：一根细圆头滑块，没有箭头
    t = P(6)
    vt = [kit.img(t, t * 2 + 4, _shape(t, t * 2 + 4, t / 2, c["border-strong"]), 0, GROW),
          ("active", kit.img(t, t * 2 + 4, _shape(t, t * 2 + 4, t / 2, c["text-subtle"]), 0, GROW))]
    ht = [kit.img(t * 2 + 4, t, _shape(t * 2 + 4, t, t / 2, c["border-strong"]), GROW, 0),
          ("active", kit.img(t * 2 + 4, t, _shape(t * 2 + 4, t, t / 2, c["text-subtle"]), GROW, 0))]
    element(f"{tag}.VThumb", vt, (0, t // 2 + 1))
    element(f"{tag}.HThumb", ht, (t // 2 + 1, 0))
    style.layout("Vertical.TScrollbar", [("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
        (f"{tag}.VThumb", {"expand": "1", "sticky": "nswe"})]})])
    style.layout("Horizontal.TScrollbar", [("Horizontal.Scrollbar.trough", {"sticky": "we", "children": [
        (f"{tag}.HThumb", {"expand": "1", "sticky": "nswe"})]})])
    for o in ("Vertical", "Horizontal"):
        style.configure(f"{o}.TScrollbar", troughcolor=c["surface"], bordercolor=c["surface"], lightcolor=c["surface"],
                        darkcolor=c["surface"], arrowsize=t, gripcount=0)

    # ---- 滑块、分隔线、分组框
    style.configure("Horizontal.TScale", troughcolor=c["surface-sunken"], background=c["accent"], bordercolor=c["surface-sunken"],
                    lightcolor=c["accent"], darkcolor=c["accent"])
    style.configure("TSeparator", background=c["border"])
    style.configure("Card.TSeparator", background=c["border"])
    style.configure("TLabelframe", background=c["bg"], bordercolor=c["border"], lightcolor=c["bg"], darkcolor=c["bg"])
    style.configure("TLabelframe.Label", background=c["bg"], foreground=c["text-muted"])

    # 经典 tk 控件（Text、Listbox、Canvas、Menu）没有 ttk 样式，用选项数据库上色
    for key, val in {"*Text.background": c["surface"], "*Text.foreground": c["text"], "*Text.insertBackground": c["text"],
                     "*Text.selectBackground": c["accent-subtle"], "*Text.selectForeground": c["text"], "*Text.relief": "flat",
                     "*Text.highlightThickness": 1, "*Text.highlightColor": c["accent"], "*Text.highlightBackground": c["border-strong"],
                     "*Listbox.background": c["surface"], "*Listbox.foreground": c["text"], "*Listbox.selectBackground": c["accent-subtle"],
                     "*Listbox.selectForeground": c["text"], "*Listbox.relief": "flat", "*Listbox.highlightThickness": 0,
                     "*Canvas.background": c["bg"], "*Canvas.highlightThickness": 0,
                     "*Menu.background": c["surface"], "*Menu.foreground": c["text"], "*Menu.activeBackground": c["accent-subtle"],
                     "*Menu.activeForeground": c["text"], "*Menu.relief": "flat"}.items():
        root.option_add(key, val)
    root.option_add("*Text.font", (family, base_size + 1))

    # 窗口图标（换掉 Tk 默认的羽毛）和标题栏颜色
    if icon:
        n = 64
        fill, ring = _rgb(c["stage"]), _rgb(c["stage-ink"])
        body = _shape(n, n, 15, c["stage"])

        def ico(x, y):
            a = body(x, y)[3]
            d = ((x - n / 2) ** 2 + (y - n / 2) ** 2) ** 0.5
            a_r = _clamp(0.5 - (abs(d - 13) - 3.2))
            return (*(fill[i] * (1 - a_r) + ring[i] * a_r for i in range(3)), a)
        root.iconphoto(True, kit.img(n, n, ico))
    titlebar(root, c["bg"], c["text"], dark)
    return style
'''


# ---------------------------------------------------------------- 图表

def echarts(L, D, ramps) -> str:
    def theme(T, dark):
        s = solid(T)
        axis = {"axisLine": {"lineStyle": {"color": s["border-strong"]}}, "axisTick": {"show": False},
                "axisLabel": {"color": s["text-subtle"]}, "splitLine": {"lineStyle": {"color": s["border"], "type": "dashed"}}}
        return {"color": series(T, 8, dark), "backgroundColor": "transparent",
                "textStyle": {"color": s["text-muted"], "fontFamily": "-apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"},
                "title": {"textStyle": {"color": s["text"], "fontWeight": 600}, "subtextStyle": {"color": s["text-subtle"]}},
                "legend": {"textStyle": {"color": s["text-muted"]}, "icon": "roundRect", "itemWidth": 12, "itemHeight": 8},
                "tooltip": {"backgroundColor": s["surface"], "borderColor": s["border"], "textStyle": {"color": s["text"]}},
                "categoryAxis": axis, "valueAxis": dict(axis, axisLine={"show": False}), "timeAxis": axis,
                "line": {"symbol": "none", "smooth": False, "lineStyle": {"width": 2}},
                "bar": {"itemStyle": {"borderRadius": [3, 3, 0, 0]}, "barMaxWidth": 28}}
    return ("// ECharts 主题 —— 由 ui-craft palette.py 生成\n"
            "// 用法：echarts.registerTheme('ui-craft', uiCraftLight); echarts.init(el, 'ui-craft')；暗色注册 uiCraftDark\n"
            f"export const uiCraftLight = {json.dumps(theme(L, False), ensure_ascii=False, indent=2)};\n"
            f"export const uiCraftDark = {json.dumps(theme(D, True), ensure_ascii=False, indent=2)};\n")


def chartjs(L, D, ramps) -> str:
    s = solid(L)
    return f"""// Chart.js 默认样式 —— 由 ui-craft palette.py 生成。在创建任何图表之前执行一次
import {{ Chart }} from "chart.js";

export const SERIES = {json.dumps(series(L, 8))};

Chart.defaults.color = "{s['text-muted']}";
Chart.defaults.borderColor = "{s['border']}";
Chart.defaults.font.family = "-apple-system, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.plugins.legend.labels.boxWidth = 12;
Chart.defaults.plugins.legend.labels.boxHeight = 8;
Chart.defaults.plugins.tooltip.backgroundColor = "{s['text']}";
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.elements.line.borderWidth = 2;
Chart.defaults.elements.point.radius = 0;
Chart.defaults.elements.bar.borderRadius = 3;
// 数据集颜色：datasets.map((d, i) => ({{ ...d, borderColor: SERIES[i], backgroundColor: SERIES[i] }}))
"""


def mpl(L, D, ramps) -> str:
    s = solid(L)
    cyc = ", ".join(f"'{c[1:]}'" for c in series(L, 8))
    h = lambda k: s[k][1:]
    return f"""# matplotlib 样式 —— 由 ui-craft palette.py 生成。存成 ui-craft.mplstyle，用 plt.style.use("ui-craft.mplstyle")
# 颜色在样式文件里不带 #（# 在这里是注释）
axes.prop_cycle: cycler('color', [{cyc}])
figure.facecolor: {h('surface')}
axes.facecolor: {h('surface')}
savefig.facecolor: {h('surface')}
axes.edgecolor: {h('border-strong')}
axes.labelcolor: {h('text-muted')}
axes.titlecolor: {h('text')}
axes.titleweight: bold
axes.titlelocation: left
axes.titlesize: 13
axes.labelsize: 10
axes.spines.top: False
axes.spines.right: False
axes.grid: True
axes.grid.axis: y
axes.axisbelow: True
grid.color: {h('border')}
grid.linewidth: 0.8
xtick.color: {h('text-subtle')}
ytick.color: {h('text-subtle')}
xtick.major.size: 0
ytick.major.size: 0
text.color: {h('text')}
legend.frameon: False
lines.linewidth: 2
font.family: sans-serif
font.sans-serif: Microsoft YaHei, PingFang SC, Noto Sans CJK SC, Source Han Sans SC, Segoe UI, DejaVu Sans
axes.unicode_minus: False
figure.dpi: 120
"""


def plotly(L, D, ramps) -> str:
    def tpl(T):
        s = solid(T)
        axis = {"gridcolor": s["border"], "linecolor": s["border-strong"], "zerolinecolor": s["border-strong"], "tickcolor": s["border"],
                "tickfont": {"color": s["text-subtle"]}, "title": {"font": {"color": s["text-muted"]}}}
        return {"colorway": series(T, 8), "paper_bgcolor": s["surface"], "plot_bgcolor": s["surface"],
                "font": {"family": "-apple-system, Segoe UI, PingFang SC, Microsoft YaHei, sans-serif", "color": s["text-muted"]},
                "title": {"font": {"color": s["text"]}, "x": 0}, "xaxis": axis, "yaxis": axis,
                "hoverlabel": {"bgcolor": s["text"], "font": {"color": s["surface"]}}, "legend": {"font": {"color": s["text-muted"]}}}
    return f"""# Plotly 模板 —— 由 ui-craft palette.py 生成
import plotly.graph_objects as go
import plotly.io as pio

pio.templates["ui_craft"] = go.layout.Template(layout={json.dumps(tpl(L), ensure_ascii=False)})
pio.templates["ui_craft_dark"] = go.layout.Template(layout={json.dumps(tpl(D), ensure_ascii=False)})
pio.templates.default = "ui_craft"
"""


# ---------------------------------------------------------------- 终端界面

def textual(L, D, ramps) -> str:
    def theme(name, T, dark):
        s = solid(T)
        return (f'{name} = Theme(\n    name="{name.lower().replace("_", "-")}",\n    primary="{s["accent"]}",\n    secondary="{s["accent-text"]}",\n'
                f'    accent="{s["accent"]}",\n    foreground="{s["text"]}",\n    background="{s["bg"]}",\n    surface="{s["surface"]}",\n'
                f'    panel="{s["surface-sunken"]}",\n    success="{s["ok"]}",\n    warning="{s["warn"]}",\n    error="{s["danger"]}",\n    dark={dark},\n)')
    return ("# Textual 主题 —— 由 ui-craft palette.py 生成\n# 用法：在 App.on_mount 里 self.register_theme(UI_CRAFT_DARK); self.theme = \"ui-craft-dark\"\n"
            "from textual.theme import Theme\n\n" + theme("UI_CRAFT_DARK", D, True) + "\n\n" + theme("UI_CRAFT_LIGHT", L, False) + "\n")


def rich(L, D, ramps) -> str:
    s = solid(D)
    return f"""# Rich 主题 —— 由 ui-craft palette.py 生成（深色终端）
# 用法：console = Console(theme=UI_CRAFT)；console.print("[title]同步完成[/] [muted]用时 3.2 秒[/]")
from rich.theme import Theme

UI_CRAFT = Theme({{
    "title": "bold {s['text']}",
    "muted": "{s['text-subtle']}",
    "accent": "bold {s['accent']}",
    "ok": "{s['ok']}",
    "warn": "{s['warn']}",
    "danger": "bold {s['danger']}",
    "number": "{s['accent-text']}",
    "rule.line": "{s['border-strong']}",
    "table.header": "bold {s['text-muted']}",
    "progress.bar.complete": "{s['accent']}",
    "progress.bar.finished": "{s['ok']}",
}})
"""


# ---------------------------------------------------------------- 微信小程序

def wxss(L, D, ramps) -> str:
    keys = ["bg", "surface", "surface-sunken", "border", "border-strong", "text", "text-muted", "text-subtle",
            "accent", "accent-fg", "accent-text", "accent-subtle", "ok", "warn", "danger"]
    l, d = solid(L), solid(D)
    body = "\n".join(f"  --{k}: {l[k]};" for k in keys)
    dark = "\n".join(f"    --{k}: {d[k]};" for k in keys)
    return f"""/* 微信小程序配色 —— 由 ui-craft palette.py 生成。放进 app.wxss；组件里用 var(--accent)。
   暗色需要在 app.json 里设 "darkmode": true。 */
page {{
{body}
  background: var(--bg);
  color: var(--text);
}}
@media (prefers-color-scheme: dark) {{
  page {{
{dark}
  }}
}}
"""


FORMATS = {
    "ttk": (ttk, "tkinter / ttk：完整主题模块（含高分屏适配、经典控件上色）"),
    "echarts": (echarts, "ECharts 主题（浅色与暗色）"),
    "chartjs": (chartjs, "Chart.js 默认样式 + 分类色"),
    "mpl": (mpl, "matplotlib 样式文件（含中文字体与负号设置）"),
    "plotly": (plotly, "Plotly 模板"),
    "textual": (textual, "Textual 终端界面主题"),
    "rich": (rich, "Rich 终端输出主题"),
    "wxss": (wxss, "微信小程序 app.wxss 配色变量（含暗色）"),
}
