#!/usr/bin/env python3
"""一条命令生成一个已经好看的页面，然后只改内容。

用法:
  python scaffold.py --list                                        # 看有哪些模板和风格预设
  python scaffold.py --type landing --style midnight --out site/   # 生成 site/index.html + ui-craft.css + ui-craft.js
  python scaffold.py --type showcase --single --out product.html   # 带原创摄影棚素材和滚动拆解的产品展示页
  python scaffold.py --type dashboard --out admin/
  python scaffold.py --type tool --style graphite --single --out timer.html   # 单个自包含文件
  python scaffold.py --bundle src/styles/ --style sunlit --accent "#E8590C"   # 只要样式和脚本，接进已有项目
  python scaffold.py --pack site/index.html                        # 把已生成的页面打包成单文件 site/index.single.html
  python scaffold.py --type tk --accent "#3358D4" --out mytool/    # tkinter 桌面小工具：ui_craft_ttk.py + app.py

生成的东西：
  index.html      模板的结构与示例内容。你只改这个文件：换文字、换数据、增删区块。
  ui-craft.css    风格预设 + 组件样式 + 动效。不要改它；要换风格或强调色，重新运行本脚本。
  ui-craft.js     动效脚本。不要改它。

--accent 给一个题材里的颜色（十六进制、rgb()、oklch() 都行），脚本用 palette.py 生成
强调、文字和选中态的色值。深色展示区沿用预设，需要它也带上强调色时加 --tint-stage。
"""
from __future__ import annotations

import argparse
import base64
import mimetypes
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import palette  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 每种页面在不指定 --style 时用哪套预设
DEFAULT_STYLE = {"landing": "paper-ink", "launch": "graphite", "showcase": "studio", "compare": "studio",
                 "dashboard": "paper-ink", "tool": "graphite", "mobile": "paper-ink", "form": "studio",
                 "article": "paper-ink", "settings": "graphite", "email": "paper-ink"}
# 不给 --accent 时用的题材色：模板的示例内容自带题材（番茄钟就是番茄红），比预设的通用蓝更有来由
DEFAULT_ACCENT = {"tool": "#D9472B", "launch": "#C8EE4A"}
# 发布页整页深色：不跟随系统，避免一半深一半浅
DEFAULT_THEME = {"launch": "dark", "showcase": "light"}
STYLE_NOTE = {
    "paper-ink": "印刷品、安静、有温度 —— 内容、阅读、人文品牌",
    "graphite": "精密、冷静、高密度 —— 开发者工具、后台、生产力",
    "midnight": "发布会、高级、有光 —— 产品官网、AI/硬件/金融",
    "sunlit": "明亮、友好、圆润 —— 消费 App、教育、生活服务",
    "editorial": "杂志、强对比、大字 —— 媒体、作品集、文化机构",
    "botanical": "自然、柔和、可信 —— 健康、食物、家居",
    "swiss": "理性、锋利、网格 —— 设计机构、活动、数据报告",
    "dusk": "温暖的光、柔焦 —— 品牌页、生活方式、创意工具",
    "studio": "摄影棚、清晰轮廓、材质特写 —— 产品展示与设计作品",
}
# Some Windows MIME registries omit modern media types. Standalone pages should
# have the same decoder hints on every host.
MEDIA_TYPES = {".webp": "image/webp", ".avif": "image/avif", ".svg": "image/svg+xml",
               ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
               ".mp4": "video/mp4", ".webm": "video/webm"}
# 保护计时从页面解析完成（DOMContentLoaded）算起：网络字体慢时不会误把入场动画关掉；6 秒是兜底上限
HEAD_GUARD = ("<script>document.documentElement.classList.add('js');(function(){function f(){if(!window.Motion)document.documentElement.classList.add('no-motion')}document.addEventListener('DOMContentLoaded',function(){setTimeout(f,600)});setTimeout(f,6000)})()</script>")


def async_font(link: str) -> str:
    """字体样式表不挡渲染、不挡脚本：先用回退字体显示，网络字体到了再换上。连不上 Google 字体时页面照常。"""
    if not link:
        return link
    lazy = link.replace('rel="stylesheet"', 'rel="stylesheet" media="print" onload="this.media=\'all\'"')
    return lazy + "<noscript>" + link + "</noscript>"
PAGE_JS = """
/* 页面通用小脚本：导航滚动后加底、分段控件切换 */
(function () {
  var nav = document.getElementById('nav');
  // 导航滚过顶部后加底：用一个放在页面顶端的哨兵元素判断，不在每次滚动时跑脚本
  if (nav) { var s = document.createElement('div'); s.setAttribute('aria-hidden', 'true');
    s.style.cssText = 'position:absolute;top:0;left:0;width:1px;height:8px;pointer-events:none';
    document.body.prepend(s);
    new IntersectionObserver(function (e) { nav.classList.toggle('scrolled', !e[0].isIntersecting); }).observe(s); }
  document.querySelectorAll('.seg:not([data-managed])').forEach(function (g) {
    g.addEventListener('click', function (e) { var b = e.target.closest('button'); if (!b) return;
      g.querySelectorAll('button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); }); });
  });
})();
"""


def read(*parts: str) -> str:
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def write(path: str, text: str, force: bool) -> None:
    if os.path.exists(path) and not force:
        sys.exit(f"已存在：{path}\n为了不覆盖你改过的内容，脚本停下了。确认要覆盖就加 --force，或换一个 --out。")
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def bundle_files(directory: str, css: str, js: str) -> dict[Path, bytes]:
    return {Path(directory, "ui-craft.css"): css.encode("utf-8"),
            Path(directory, "ui-craft.js"): js.encode("utf-8")}


def write_assets(files: dict[Path, bytes], force: bool) -> None:
    # Check all conflicts before emitting any assets. Identical shared files can be reused.
    pending = {}
    for target, data in files.items():
        if target.is_file() and target.read_bytes() == data:
            continue
        if target.exists() and (not target.is_file() or not force):
            sys.exit(f"已有不同的素材或套件文件：{target}。可更换输出目录，或用 --force 明确替换文件。")
        pending[target] = data
    for target, data in pending.items():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def presets() -> dict[str, dict]:
    """从 styles.css 里取出每套预设：变量块、字体 <link>、注释。"""
    css = read("assets", "styles.css")
    out = {}
    for m in re.finditer(r"/\* -{10,}\n(.*?)-{10,} \*/\s*\.style-([a-z-]+)\s*\{(.*?)\n\}", css, re.S):
        note, name, body = m.group(1), m.group(2), m.group(3)
        link = re.search(r"<link[^>]+>", note)
        out[name] = {"body": body.rstrip(), "link": link.group(0) if link else "", "note": note}
    return out


def templates() -> dict[str, dict]:
    d = os.path.join(ROOT, "templates")
    out = {}
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".html"):
            continue
        src = read("templates", fn)
        title = re.search(r"<!--@title (.*?)-->", src)
        use = re.search(r"<!--@use (.*?)-->", src, re.S)
        style = re.search(r"<style>(.*?)</style>", src, re.S)
        body = re.sub(r"<!--@(title|use|sample) .*?-->\s*", "", src, flags=re.S)
        body = re.sub(r"<style>.*?</style>\s*", "", body, count=1, flags=re.S)
        kind = re.search(r"<!--@kind (\w+)-->", src)
        out[fn[:-5]] = {"title": title.group(1).strip() if title else fn[:-5],
                        "use": use.group(1).strip() if use else "",
                        "css": style.group(1).strip() if style else "", "body": body.strip(),
                        "kind": kind.group(1) if kind else "page",
                        "raw": re.sub(r"<!--@(title|use|sample|kind) .*?-->\s*", "", src, flags=re.S)}
    return out


def accent_css(color: str, neutral: str, keep_stage: bool, retint: bool = False) -> str:
    H, C, light, dark, stage = palette.build(color, neutral)
    keys = ["accent", "accent-fg", "accent-text", "accent-subtle"]
    if retint:
        # 明确给了 --neutral：底色、表面、线、文字一起换成这个色温，和强调色不打架
        keys = ["bg", "surface", "surface-sunken", "border", "border-strong", "text", "text-muted", "text-subtle", "text-faint"] + keys
    lines = [f"/* 强调色：由 palette.py 从 {color} 生成（H {H:.0f}，C {C:.3f}" + (f"，中性色 {neutral}" if retint else "") + "），对比度已校验 */", ":root {"]
    lines += [f"  --{k}: light-dark({light[k]}, {dark[k]});" for k in keys]
    lines.append(f"  --accent-layer: light-dark({palette.layer_color(light['accent'])}, {palette.layer_color(dark['accent'])});")
    if retint:
        nh = {"cool": 255, "tinted": H}.get(neutral, 80)
        lines.append(f"  --surface-raised: light-dark({light['surface']}, {palette.ok(0.24, 0.012, nh)});")
    if not keep_stage:
        # 舞台的光跟着强调色走；舞台上的主按钮反白，避免和同色相的背景融在一起
        glow = palette.ok(0.42, min(C * 0.8, 0.14), H, 0.6)
        top, bottom = palette.ok(0.235, min(C * 0.25, 0.03), H), palette.ok(0.165, min(C * 0.2, 0.025), H)
        lines += [f"  --stage: {stage['stage']}; --stage-ink: {stage['stage-ink']}; --stage-muted: {stage['stage-muted']};",
                  "  --stage-btn: var(--stage-ink); --stage-btn-fg: var(--stage);",
                  f"  --stage-bg: radial-gradient(60% 85% at 78% 8%, {glow}, transparent 68%), linear-gradient({top}, {bottom});"]
    lines.append("}")
    return "\n".join(lines)


def build_css(style: str, accent: str | None, neutral: str | None, keep_stage: bool) -> tuple[str, str]:
    ps = presets()
    if style not in ps:
        sys.exit(f"没有叫 {style} 的预设。可用的：{', '.join(ps)}")
    p = ps[style]
    parts = [f"/* ui-craft.css —— 由 scaffold.py 生成（预设 {style}" + (f"，强调色 {accent}" if accent else "") + "）。\n"
             "   不要手改这个文件：要换风格或强调色，重新运行 scaffold.py。页面自己的布局写在 index.html 的 <style> 里。 */",
             f"/* ===== 1 · 风格预设：{style} ===== */\n:root {{{p['body']}\n}}"]
    if accent:
        parts.append(accent_css(accent, neutral or "warm", keep_stage, retint=neutral is not None))
    parts.append("/* ===== 2 · 动效 ===== */\n" + read("assets", "motion.css"))
    parts.append("/* ===== 3 · 组件 ===== */\n" + read("assets", "ui.css"))
    return "\n\n".join(parts) + "\n", p["link"]


def page(t: dict, title: str, lang: str, theme: str, font_link: str, css: str | None, js: str | None, motion: str = "full") -> str:
    motion_attr = " data-respect-reduced-motion" if motion == "system" else ""
    theme_attr = "" if theme == "auto" else f' data-theme="{theme}"'
    fonts = ""
    if font_link:
        fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
                 '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n' + async_font(font_link) + "\n")
    lib_css = f"<style>\n{css}</style>" if css is not None else '<link rel="stylesheet" href="ui-craft.css">'
    lib_js = f"<script>\n{js}\n</script>" if js is not None else '<script src="ui-craft.js"></script>'
    return f"""<!doctype html>
<html lang="{lang}"{theme_attr}{motion_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
{HEAD_GUARD}
{fonts}{lib_css}
<!-- 页面样式：按项目的排版、取景与交互调整 -->
<style>
{t['css']}
</style>
</head>
<body>
<!-- 页面内容 -->
{t['body']}
<!-- ↑ 内容到此为止 -->
{lib_js}
</body>
</html>
"""


def page_media(html: str, source_dir: Path, *, copy_to: Path | None = None) -> tuple[str, dict[Path, bytes]]:
    """Resolve media/ URLs; return external assets for preflight with the rest of the kit."""
    if "media/" not in html:
        return html, {}
    source_dir = source_dir.resolve()
    urls: dict[str, str] = {}
    copies: dict[Path, bytes] = {}

    def resolve(url: str) -> str:
        if url in urls:
            return urls[url]
        if not url.startswith(("media/", "./media/")):
            return url
        relative = unquote(urlsplit(url).path).removeprefix("./").removeprefix("media/")
        source = (source_dir / relative).resolve()
        if not source.is_relative_to(source_dir) or not source.is_file():
            sys.exit(f"找不到可打包的本地素材：{url}")
        data = source.read_bytes()
        if copy_to is None:
            mime = MEDIA_TYPES.get(source.suffix.lower()) or mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            urls[url] = f"data:{mime};base64," + base64.b64encode(data).decode("ascii")
        else:
            target = (copy_to / relative).resolve()
            if not target.is_relative_to(copy_to.resolve()):
                sys.exit(f"素材输出路径越界：{url}")
            copies[target] = data
            urls[url] = url
        return urls[url]

    def attribute(match: re.Match) -> str:
        lead, name, quote, value = match.groups()
        if name.lower() == "srcset":
            value = re.sub(r"(?:^|(?<=[\s,]))(?:\./)?media/[^\s,]+", lambda m: resolve(m.group()), value)
        else:
            value = resolve(value)
        return lead + quote + value + quote

    def tag(match: re.Match) -> str:
        return re.sub(r"""(\s(srcset|src|poster)\s*=\s*)(["'])(.*?)\3""", attribute, match.group(), flags=re.I | re.S)

    html = re.sub(r"<(?:img|source|video)\b[^>]*>", tag, html, flags=re.I)
    return html, copies


def pack(path: str, force: bool) -> None:
    """Embed the kit and local media into a standalone HTML file."""
    with open(path, encoding="utf-8") as f:
        html = f.read()
    d = os.path.dirname(os.path.abspath(path))

    def inline(name: str) -> str:
        with open(os.path.join(d, name), encoding="utf-8") as f:
            return f.read()
    if 'href="ui-craft.css"' in html:
        html = html.replace('<link rel="stylesheet" href="ui-craft.css">', "<style>\n" + inline("ui-craft.css") + "</style>")
    if 'src="ui-craft.js"' in html:
        html = html.replace('<script src="ui-craft.js"></script>', "<script>\n" + inline("ui-craft.js") + "\n</script>")
    html, _ = page_media(html, Path(d) / "media")
    out = re.sub(r"\.html?$", "", path) + ".single.html"
    write(out, html, True)   # 打包结果是派生文件，每次直接覆盖
    print(f"已打包：{out}（{len(html.encode('utf-8')) // 1024} KB，可以单独发给别人）")


def main() -> None:
    ap = argparse.ArgumentParser(description="生成一个已经好看的页面骨架", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--list", action="store_true", help="列出模板与风格预设")
    ap.add_argument("--type", help="见 --list；showcase 用于产品摄影与滚动叙事，compare 用于效果前后对照")
    ap.add_argument("--style", help="风格预设；不给就按模板类型选默认的")
    ap.add_argument("--accent", help="取自项目品牌或物件的强调色，用于操作、文字和选中态")
    ap.add_argument("--neutral", choices=["warm", "cool", "tinted"],
                    help="配合 --accent：把底色、表面、文字的色温一起换掉（暖色强调配 warm，冷色强调配 cool）。不写就保留预设的中性色")
    stage_options = ap.add_mutually_exclusive_group()
    stage_options.add_argument("--keep-stage", dest="keep_stage", action="store_true",
                               help="保留预设的深色展示区（默认）")
    stage_options.add_argument("--tint-stage", dest="keep_stage", action="store_false",
                               help="让深色展示区的底色与光晕跟随强调色")
    ap.set_defaults(keep_stage=True)
    ap.add_argument("--theme", choices=["auto", "light", "dark"], help="auto 跟随系统；默认 launch 深色、showcase 浅色，其余跟随系统")
    ap.add_argument("--motion", choices=["full", "system"], default="full",
                    help="full 沿用套件完整动效；system 响应系统的减少动态效果设置。")
    ap.add_argument("--system-fonts", action="store_true", help="省略预设的在线字体链接，使用现有字体栈回退。")
    ap.add_argument("--title", help="页面标题")
    ap.add_argument("--lang", default="zh-CN")
    ap.add_argument("--out", help="输出目录，或以 .html 结尾的文件路径")
    ap.add_argument("--single", action="store_true", help="输出单个自包含 HTML（样式和脚本内联）")
    ap.add_argument("--bundle", metavar="目录", help="只输出 ui-craft.css 和 ui-craft.js，用于接进已有项目")
    ap.add_argument("--pack", metavar="HTML", help="把已生成的页面打包成单文件")
    ap.add_argument("--force", action="store_true", help="允许覆盖已存在的文件")
    a = ap.parse_args()

    ts = templates()
    if a.list:
        print("模板（--type）")
        for k, t in ts.items():
            print(f"  {k:<10} 默认预设 {DEFAULT_STYLE.get(k, 'graphite'):<10} {t['use']}")
        print("\n风格预设（--style）")
        for k in presets():
            print(f"  {k:<10} {STYLE_NOTE.get(k, '')}")
        print(f"  {'tk':<10} {'（桌面）':<15} tkinter 小工具：强调色顶栏 + 大数字 + 柱状图、卡片、可悬停列表、表单（写出 ui_craft_ttk.py 和 app.py）")
        print("\n--accent 控制局部强调色。需要大面积同色布光时再加 --tint-stage。")
        return
    if a.pack:
        pack(a.pack, a.force)
        return

    js = read("assets", "motion.js") + "\n" + PAGE_JS
    if a.bundle:
        style = a.style or DEFAULT_STYLE.get(a.type or "", "graphite")
        css, link = build_css(style, a.accent, a.neutral, a.keep_stage)
        write_assets(bundle_files(a.bundle, css, js), a.force)
        print(f"已输出：{os.path.join(a.bundle, 'ui-craft.css')}、ui-craft.js（预设 {style}）")
        print("接入：1) <head> 最前面加一行  " + HEAD_GUARD)
        if a.motion == "system":
            print("      在 <html> 上加 data-respect-reduced-motion，让套件响应系统动效偏好。")
        if link and not a.system_fonts:
            print("      2) 字体  " + link)
        print('      3) 引入 ui-craft.css；<body> 末尾引入 ui-craft.js（React/Vue 里在根组件挂载后调用 Motion.auto()）')
        print("      4) 组件直接写 ui-craft.css 里的类名（.btn .card .field .table …），清单见 assets/ui.css 开头的目录")
        return

    if not a.type:
        ap.error("要给 --type（先用 --list 看有哪些），或用 --bundle / --pack")
    if a.type == "tk":
        # tkinter 桌面小工具：配好色的主题模块 + 模板程序。桌面窗口默认冷灰中性色，和系统窗口框更协调
        import exporters
        accent = a.accent or "#3358D4"
        d = a.out or "ui-craft-tk"
        files = {os.path.join(d, "ui_craft_ttk.py"): exporters.export("ttk", accent, a.neutral or "cool"),
                 os.path.join(d, "app.py"): read("templates", "tkinter", "app.py")}
        for path in files:
            if os.path.exists(path) and not a.force:
                sys.exit(f"已存在：{path}\n为了不覆盖你改过的内容，脚本停下了。确认要覆盖就加 --force，或换一个 --out。")
        for path, text in files.items():
            write(path, text, a.force)
        print(f"已生成：{os.path.join(d, 'ui_craft_ttk.py')} + app.py（强调色 {accent}，中性色 {a.neutral or 'cool'}）")
        print("接下来：")
        print(f"  1. python {os.path.join(d, 'app.py')} 先看一眼（加 --dark 看暗色）；再换成你的文字、数据和操作，用不上的卡片整块删掉。")
        print("  2. 颜色、字体、圆角都从 ui_craft_ttk 取（ui.COLORS、ui.mix、样式名见它开头的说明），不要另写颜色。")
        print("     要换强调色：重新运行本脚本并加 --force 只会覆盖这两个文件，改过的 app.py 先备份。")
        print("  3. 截图检查：窗口按常用尺寸打开，浅色和暗色各看一次，文字不被裁掉、主按钮一眼能找到。")
        return
    if a.type not in ts:
        sys.exit(f"没有叫 {a.type} 的模板。可用的：{', '.join(ts)}, tk")
    t = ts[a.type]
    style = a.style or DEFAULT_STYLE.get(a.type, "graphite")
    if not a.accent and not a.style:
        a.accent = DEFAULT_ACCENT.get(a.type)
    a.theme = a.theme or DEFAULT_THEME.get(a.type, "auto")
    css, link = build_css(style, a.accent, a.neutral, a.keep_stage)
    out = a.out or f"ui-craft-{a.type}"
    html_path = out if out.lower().endswith((".html", ".htm")) else os.path.join(out, "index.html")
    d = os.path.dirname(os.path.abspath(html_path))
    title = a.title or t["title"]
    if os.path.exists(html_path) and not a.force:
        sys.exit(f"已存在：{html_path}。要保留请换输出路径，要覆盖请加 --force。")
    if t.get("kind") == "email":
        # 邮件客户端不认外部样式、CSS 变量和脚本：颜色按预设（与 --accent）直接写进每个标签
        import colorkit
        light, _ = colorkit.preset_roles(style, a.accent, a.neutral)
        roles = {k: colorkit.concrete(v) for k, v in light.items()}
        html = re.sub(r"\{\{([\w-]+)\}\}", lambda m: roles.get(m.group(1), title if m.group(1) == "title" else m.group(0)), t["raw"])
        write(html_path, html, a.force)
        print(f"已生成：{html_path}（HTML 邮件，颜色已写死，预设 {style}" + (f"，强调色 {a.accent}" if a.accent else "") + "）")
        print("接下来：只改文字和链接；不要加 <style> 里的新规则、外部字体、脚本或背景图——多数邮件客户端会删掉它们。")
        print("        发送前用 Outlook、Gmail 网页版、手机邮件 App 各收一封看。")
        return
    t["body"], assets = page_media(t["body"], Path(ROOT, "assets", a.type),
                                   copy_to=None if a.single else Path(d, "media"))

    if a.single:
        write(html_path, page(t, title, a.lang, a.theme, "" if a.system_fonts else link, css, js, a.motion), a.force)
        print(f"已生成：{html_path}（单文件，预设 {style}）")
    else:
        assets.update(bundle_files(d, css, js))
        write_assets(assets, a.force)
        write(html_path, page(t, title, a.lang, a.theme, "" if a.system_fonts else link, None, None, a.motion), a.force)
        print(f"已生成：{html_path} + ui-craft.css + ui-craft.js（预设 {style}" + (f"，强调色 {a.accent}" if a.accent else "") + "）")
    print("接下来：")
    if a.type == "compare":
        print("  1. 替换固定底稿与配准前后两张叠印，核对图例、图像宽高和要放大的笔迹。")
        print("  2. 拨到两端看原稿四边，再让分界扫过同一笔迹。切换叠层、键盘微调，最后关脚本检查静态对照。")
    elif a.type == "showcase":
        print("  1. 按 references/product-showcase.md 选择镜头。换成项目自己的产品、素材和说明。")
        print("  2. 在浏览器中向前和向后滚动同一章节，切换细节，切换系统减少动态效果，检查实际配置下的结果与静态读法。")
    else:
        print(f"  1. 用实际内容编辑 {os.path.basename(html_path)}，按任务取舍区块，补齐主要操作。")
        print("  2. 套件控件可复用 ui-craft.css 的变量与类；项目已有的视觉语言优先。")
    print(f"  3. 改完运行  python {os.path.join(HERE, 'audit.py')} {html_path} --gate  ，修正阻断项并在截图上判断视觉提示。")
    extra = " --scenes" if a.type in ("showcase", "compare") else ""
    print(f"  4. 用允许的浏览器验证：python {os.path.join(HERE, 'shot.py')} {html_path}{extra}（可用 --browser 指定路径）。")


if __name__ == "__main__":
    main()
