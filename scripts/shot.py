#!/usr/bin/env python3
"""渲染检查：用本机的兼容浏览器渲染页面、测量并截图。

用法:
  python shot.py 输出目录/index.html              # 宽屏 1440、手机 375、暗色各一张，并检查横向溢出
  python shot.py index.html --out shots/          # 指定截图目录（默认是页面旁边的 shots/）
  python shot.py index.html --width 1100          # 额外再看一个宽度
  python shot.py index.html --browser 浏览器路径 --scenes  # 实测滚动章节并保存关键帧

它检查的是静态门槛（audit.py --gate）看不到的东西：
  - 手机宽度下有没有横向溢出，是哪个元素撑宽的
  - 样式文件有没有加载上（页面是不是一片浏览器默认样式）
  - 有没有加载失败的图片
截图存成 PNG，能看图的模型应该打开看一眼；不能看图也没关系，溢出与加载问题会直接用文字报出来。

为什么不直接用 --window-size=375：无头浏览器的窗口有最小宽度（约 500px），直接设 375 只会把
500 宽的版面裁掉右边一截，看起来像溢出。这里把页面放进一个 375 宽的 iframe 里渲染，结果才是真的。

找不到浏览器时退出码为 2，不算检查失败——改用别的方式看一眼渲染结果。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "msedge", "chrome"]

MEASURE_DOCUMENT = r"""
function measure(doc) {
  function sel(e) {
    var s = e.tagName.toLowerCase();
    if (e.id) s += '#' + e.id;
    var c = (e.getAttribute('class') || '').trim().split(/\s+/).filter(Boolean).slice(0, 3).join('.');
    return c ? s + '.' + c : s;
  }
  function scrolls(e, doc) {
    for (var p = e.parentElement; p && p !== doc.body; p = p.parentElement) {
      var o = getComputedStyle(p).overflowX;
      if (o === 'auto' || o === 'scroll' || o === 'hidden' || o === 'clip') return true;
    }
    return false;
  }
  var root = doc.documentElement, cw = root.clientWidth;
  var sw = Math.max(root.scrollWidth, doc.body ? doc.body.scrollWidth : 0);
  var off = [];
  if (sw > cw + 1) {
    var all = doc.body.querySelectorAll('*');
    for (var i = 0; i < all.length && off.length < 40; i++) {
      var r = all[i].getBoundingClientRect();
      if (r.width > 0 && r.right > cw + 1 && !scrolls(all[i], doc)) off.push({ el: all[i], right: Math.round(r.right), width: Math.round(r.width) });
    }
    // 只留最里层的：父元素被子元素撑宽时，报子元素
    off = off.filter(function (o) { return !off.some(function (p) { return p !== o && o.el.contains(p.el); }); })
             .slice(0, 6).map(function (o) { return { sel: sel(o.el.parentElement || o.el) + ' > ' + sel(o.el), right: o.right, width: o.width,
               text: (o.el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 24) }; });
  }
  var bs = getComputedStyle(doc.body);
  var imgs = [].filter.call(doc.images, function (im) { return im.complete && im.naturalWidth === 0; }).map(function (im) { return im.getAttribute('src'); });
  var links = [].map.call(doc.querySelectorAll('link[rel~="stylesheet"]'), function (l) {
    var okk = false; try { okk = !!l.sheet && l.sheet.cssRules.length > 0; } catch (e) { okk = !!l.sheet; }
    return { href: l.getAttribute('href'), ok: okk }; }).filter(function (l) { return !/^https?:/.test(l.href || ''); });
  return { ok: true, clientWidth: cw, scrollWidth: sw, height: Math.max(root.scrollHeight, doc.body.scrollHeight), offenders: off,
          unstyled: bs.marginTop !== '0px' && bs.fontFamily.toLowerCase().indexOf('times') >= 0, brokenImages: imgs.slice(0, 8),
          missingCss: links.filter(function (l) { return !l.ok; }).map(function (l) { return l.href; }),
          motion: !!doc.defaultView.Motion, hasMotionAttrs: !!doc.querySelector('[data-reveal],[data-split],[data-count],[data-scroll-scene],[data-compare]') };
}
"""
MEASURE_JS = "(function () {" + MEASURE_DOCUMENT + r"""
  var f = document.getElementById('f'), out = document.getElementById('r');
  function run() {
    var res;
    try { res = measure(f.contentDocument);
    } catch (e) { res = { ok: false, error: String(e) }; }
    out.textContent = JSON.stringify(res);
  }
  if (f.contentDocument && f.contentDocument.readyState === 'complete') setTimeout(run, 1800);
  else f.addEventListener('load', function () { setTimeout(run, 1800); });
})();
"""


def find_browser(requested: str | None = None) -> str | None:
    chosen = requested or os.environ.get("UI_CRAFT_BROWSER")
    if chosen:
        return chosen if os.path.isfile(chosen) else None
    if sys.platform == "win32":
        import winreg
        app_path = r"Software\Microsoft\Windows\CurrentVersion\App Paths\quark.exe"
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, app_path) as key:
                    registered = winreg.QueryValue(key, None).strip('"')
                if os.path.isfile(registered):
                    return registered
            except OSError:
                continue
    for c in CANDIDATES:
        if os.path.isfile(c):
            return c
    for n in NAMES:
        p = shutil.which(n)
        if p:
            return p
    return None


def wrapper(page_name: str, w: int, h: int, dark: bool, measure: bool) -> str:
    scheme = "dark" if dark else "light"
    js = f"<script>{MEASURE_JS}</script>" if measure else ""
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;background:#777;overflow:hidden}}'
            f'iframe{{display:block;border:0;width:{w}px;height:{h}px;color-scheme:{scheme}}}</style></head>'
            f'<body><iframe id="f" src="{page_name}"></iframe><pre id="r" hidden></pre>{js}</body></html>')


def static_copy(html: str) -> str:
    """截图用的副本：关掉入场动画与数字滚动，让画面直接停在最终状态。
    无头浏览器在很高的窗口里计时不稳，等动画放完再截经常截到半途；页面的版面与动画无关，所以直接看终态。"""
    html = html.replace("classList.add('js')", "classList.add('shot')").replace('classList.add("js")', 'classList.add("shot")')
    # The full-page iframe is taller than a real viewport. Keep the static end
    # frame in this copy; measure the live page separately at the requested size.
    html = re.sub(r'\bdata-scroll-scene(?=[\s=>])', 'data-scroll-scene data-scene-still', html, flags=re.I)
    html = re.sub(r'\sdata-(?:count|decimals|delay)="[^"]*"', "", html)
    html = re.sub(r'\sdata-(?:reveal|split|stagger|parallax|tilt)(?:="[^"]*")?', "", html)
    # 无头截图模式下交给显卡的过渡（scale、opacity）不会走完：截图副本里关掉过渡，直接显示终态
    html = html.replace("</head>", "<style>*,*::before,*::after{transition:none!important}.bar>i{scale:1 1!important}</style></head>", 1)   # 截图框和整页一样高，视差会算错位置
    return html


def run_browser(browser: str, profile: str, url: str, w: int, h: int, extra: list[str]) -> str:
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--no-default-browser-check",
           "--allow-file-access-from-files", "--disable-extensions", f"--user-data-dir={profile}",
           f"--window-size={max(w, 500)},{h}", *extra, url]
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=90)
    except subprocess.TimeoutExpired:
        return ""
    return p.stdout.decode("utf-8", errors="replace")


def crop_png(path: Path, w: int) -> None:
    """窗口最小宽度比 375 大时，截图右边会多出灰边：把 PNG 裁到 w 宽。只依赖标准库。"""
    import struct
    import zlib
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        return
    pos, chunks, idat = 8, [], b""
    while pos < len(data):
        n, typ = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        if typ == b"IDAT":
            idat += body
        else:
            chunks.append((typ, body))
        pos += 12 + n
    W, H, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", chunks[0][1])
    if W <= w or depth != 8 or interlace or ctype not in (2, 6):
        return
    bpp = 4 if ctype == 6 else 3
    raw = zlib.decompress(idat)
    stride = W * bpp
    out, prev = bytearray(), bytearray(stride)
    for y in range(H):
        ft = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        if ft == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                line[i] = (line[i] + ((line[i - bpp] if i >= bpp else 0) + prev[i]) // 2) & 255
        elif ft == 4:
            for i in range(stride):
                a = line[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        prev = line
        out += b"\x00" + line[:w * bpp]

    def chunk(typ: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + typ + body + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF)
    ihdr = struct.pack(">IIBBBBB", w, H, 8, ctype, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(out), 6)) + chunk(b"IEND", b""))


def check_scenes(tab, key: str, out: Path | None, issues: list[str]) -> None:
    scenes = tab.locator("[data-scroll-scene]")
    boards = tab.locator("[data-compare]")
    if not scenes.count() and not boards.count():
        issues.append(f"{key} 没有找到待检查的滚动章节或对照控件")
        return
    for i, scene in enumerate(scenes.all(), 1):
        values = []
        if scene.get_attribute("data-scene-active") is not None:
            for label, at in (("start", 0), ("middle", .5), ("end", 1), ("reverse", .5)):
                value = scene.evaluate("""async (s, at) => {
                  const pin=s.querySelector(':scope > [data-scene-pin]');
                  scrollTo({top:scrollY+s.getBoundingClientRect().top+at*(s.offsetHeight-pin.offsetHeight),behavior:'instant'});
                  for (let frame=0; frame<3; frame++) await new Promise(requestAnimationFrame);
                  return Number(getComputedStyle(s).getPropertyValue('--scene-progress'));
                }""", at)
                values.append(round(value, 3))
                if abs(value - at) > .015:
                    issues.append(f"{key} 章节 {i} {label} 的进度为 {value:.3f}，预期 {at}")
                if out:
                    tab.screenshot(path=out / f"{key}-scene-{i}-{label}.png")
            print(f"    章节 {i} 正向与回滚进度 {values}")
        else:
            print(f"    章节 {i} 在这个视口使用静态构图")
    # Exercise the shipping configuration. Adding a flag here would only test a modified page.
    system_mode = tab.locator("html").get_attribute("data-respect-reduced-motion") is not None
    tab.emulate_media(reduced_motion="reduce")
    tab.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
    reduced = tab.evaluate("() => window.Motion?.reduced")
    if reduced != system_mode:
        issues.append(f"{key} 减弱动效的实际状态 {reduced} 与页面配置 {system_mode} 不符")
    if system_mode:
        for i, scene in enumerate(scenes.all(), 1):
            complete = scene.evaluate("""s => {
              const pin=s.querySelector(':scope > [data-scene-pin]');
              return pin && getComputedStyle(pin).position!=='sticky' && !s.hasAttribute('data-scene-active') &&
                Number(getComputedStyle(s).getPropertyValue('--scene-progress'))===1;
            }""")
            if not complete:
                issues.append(f"{key} 章节 {i} 的减少动态效果终帧未就位")
    print("    系统请求减少动态效果：" + ("已启用静态呈现" if system_mode else "按完整动效配置呈现"))
    tab.emulate_media(reduced_motion="no-preference")
    for i, board in enumerate(boards.all(), 1):
        if board.get_attribute("data-compare-ready") is None:
            issues.append(f"{key} 对照 {i} 的滑杆未就绪")
            continue
        slider = board.locator(':scope > input[type="range"]')
        for label, action, endpoint in (("after", "Home", 0), ("before", "End", 100)):
            slider.press(action)
            value = board.evaluate("e => parseFloat(getComputedStyle(e).getPropertyValue('--split'))")
            if value != endpoint:
                issues.append(f"{key} 对照 {i} 的 {action} 到达 {value}%，预期 {endpoint}%")
            if out:
                board.screenshot(path=out / f"{key}-compare-{i}-{label}.png")
        print(f"    对照 {i} 已测试 Home 和 End 两端")


def live_preview(browser: str, page: Path, views: list, out: Path | None, scenes: bool) -> int:
    """Use the selected browser directly when CLI DOM dumps are unavailable or motion is under test."""
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        print("此浏览器的实时测量需要可用的 Playwright。可用允许的内置浏览器按产品展示指南手动检查。")
        return 2

    def ready(tab) -> None:
        tab.evaluate("""async () => {
          document.querySelectorAll('img[loading="lazy"]').forEach(im => im.loading='eager');
          await Promise.race([Promise.all([document.fonts.ready,
            ...Array.from(document.images, im => im.decode().catch(() => {}))]),
            new Promise(resolve => setTimeout(resolve, 8000))]);
        }""")

    issues: list[str] = []
    try:
        with sync_playwright() as pw:
            engine = pw.chromium.launch(executable_path=browser, headless=True,
                                        args=["--no-first-run", "--no-default-browser-check", "--disable-extensions"])
            checks = list(views)
            if out:
                checks.append(("dark", "暗色 1440", 1440, 900, True))
            for key, label, w, h, dark in checks:
                context = engine.new_context(viewport={"width": w, "height": h}, is_mobile=w < 500,
                                             has_touch=w < 500, device_scale_factor=1,
                                             color_scheme="dark" if dark else "light", reduced_motion="no-preference")
                tab = context.new_page()
                tab.on("pageerror", lambda error, label=label: issues.append(f"{label} 脚本错误 {error}"))
                tab.goto(page.as_uri(), wait_until="domcontentloaded")
                ready(tab)
                res = tab.evaluate("() => (" + MEASURE_DOCUMENT + ")(document)")
                print(f"  {label}：可用宽 {res['clientWidth']}px，内容宽 {res['scrollWidth']}px，页面高 {res['height']}px")
                unfinished = tab.locator("img").evaluate_all("imgs=>imgs.filter(i=>!i.complete).length")
                if res["scrollWidth"] > res["clientWidth"] + 1:
                    issues.append(f"{label} 横向溢出 {res['scrollWidth'] - res['clientWidth']}px {res['offenders']}")
                if res["brokenImages"] or unfinished:
                    issues.append(f"{label} 图片未就绪：{len(res['brokenImages'])} 个失败，{unfinished} 个仍在加载")
                if res["missingCss"] or res["unstyled"] or (res["hasMotionAttrs"] and not res["motion"]):
                    issues.append(f"{label} 缺少样式或动效脚本")
                if out:
                    # 数字滚动（data-count）约 1.1 秒放完；不等的话首屏截图里是半途的数字，会被误判成数据错了
                    if tab.evaluate("() => !!document.querySelector('[data-count]')"):
                        tab.wait_for_timeout(1500)
                    tab.screenshot(path=out / f"{key}-viewport.png", animations="disabled")
                    # A tall capture may leave below-fold reveal targets unobserved.
                    # Scroll the real page so its own application logic produces the full-page state.
                    tab.evaluate("""async () => {
                      const frames = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
                      const height = document.documentElement.scrollHeight;
                      for (let top = innerHeight * .8; top < height + innerHeight; top += innerHeight * .8) {
                        scrollTo({top, behavior:'instant'}); await frames();
                      }
                      scrollTo({top:0, behavior:'instant'}); await frames();
                    }""")
                    ready(tab)
                    tab.screenshot(path=out / f"{key}.png", full_page=True, animations="disabled")
                if scenes and not dark:
                    check_scenes(tab, key, out, issues)
                context.close()
            engine.close()
    except (Error, OSError) as error:
        issues.append(str(error))
    if issues:
        print("未通过\n" + "\n".join(issues))
        return 1
    print("通过。布局和资源加载已在浏览器内测量。" + (f" 截图保存在 {out}" if out else ""))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="渲染检查：量横向溢出，截宽屏 / 手机 / 暗色三张图")
    ap.add_argument("page", help="要检查的 HTML 文件")
    ap.add_argument("--out", help="截图目录（默认：页面旁边的 shots/）")
    ap.add_argument("--width", type=int, action="append", default=[], help="额外检查的宽度，可多次给")
    ap.add_argument("--no-shots", action="store_true", help="只量不截图")
    ap.add_argument("--browser", help="使用指定的兼容浏览器可执行文件，也可通过 UI_CRAFT_BROWSER 设置")
    ap.add_argument("--scenes", action="store_true", help="实测滚动、回滚、遵守减少动态效果时的终帧及前后对照控件，使用已有 Playwright")
    a = ap.parse_args()
    if any(w < 1 for w in a.width):
        ap.error("视口宽度须为正整数。")

    page = Path(a.page).resolve()
    if page.is_dir():
        page = page / "index.html"
    if not page.is_file():
        print(f"找不到页面：{page}")
        return 2
    browser = find_browser(a.browser)
    if not browser:
        print("没有找到可执行的兼容浏览器，无法做渲染检查。\n"
              "可以用 --browser 指定允许的浏览器路径，或使用其他预览工具，"
              "在宽屏、375 宽、暗色下各看一眼，确认没有横向滚动条。")
        return 2
    out_dir = Path(a.out).resolve() if a.out else page.parent / "shots"
    if not a.no_shots:
        out_dir.mkdir(parents=True, exist_ok=True)

    views = [("wide", "宽屏 1440", 1440, 900, False), ("narrow", "手机 375", 375, 812, False)]
    views += [(f"w{w}", f"宽度 {w}", w, 900, False) for w in a.width]
    if a.scenes or Path(browser).stem.lower() == "quark":
        return live_preview(browser, page, views, None if a.no_shots else out_dir, a.scenes)
    profile = tempfile.mkdtemp(prefix="ui-craft-shot-")
    problems: list[str] = []
    print(f"渲染检查：{page}\n")
    helpers = []
    try:
        for name in ("wrapper", "still"):
            with tempfile.NamedTemporaryFile(dir=page.parent, prefix=f"__ui_craft_{name}_", suffix=".html", delete=False) as handle:
                helpers.append(Path(handle.name))
        tmp, still = helpers
        heights: dict[str, int] = {}
        for key, label, w, h, dark in views:
            tmp.write_text(wrapper(page.name, w, h, dark, True), encoding="utf-8")
            dom = run_browser(browser, profile, tmp.as_uri(), w, h, ["--dump-dom", "--virtual-time-budget=6000"])
            m = re.search(r'<pre id="r"[^>]*>(.*?)</pre>', dom, re.S)
            res = None
            if m and m.group(1).strip():
                try:
                    res = json.loads(m.group(1).replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&"))
                except ValueError:
                    res = None
            if not res or not res.get("ok"):
                problems.append(f"{label}没有取得布局测量")
                print(f"  {label}：没能量到（{(res or {}).get('error', '浏览器没有返回结果')}）")
                heights[key] = h
                continue
            heights[key] = max(h, min(int(res["height"]), 9000))
            over = res["scrollWidth"] - res["clientWidth"]
            if over > 1:
                problems.append(f"{label}横向溢出")
                print(f"  {label}：横向溢出 {over}px（版面宽 {res['scrollWidth']}，屏幕宽 {res['clientWidth']}）")
                for o in res["offenders"]:
                    print(f"      撑宽的元素：{o['sel']}  右边界 {o['right']}px，宽 {o['width']}px" + (f"  「{o['text']}」" if o["text"] else ""))
                print("      改法：① 这个元素的父级如果是 grid / flex，给子项加 min-width: 0，栅格列写成 minmax(0, 1fr)；"
                      "② 去掉它身上的固定宽度和 white-space: nowrap，或给 flex 容器加 flex-wrap: wrap；"
                      "③ 宽表格、长代码放进 overflow-x: auto 的容器（.table-wrap）。")
            else:
                print(f"  {label}：没有横向溢出，页面高 {res['height']}px")
            if key == "wide":
                if res.get("missingCss"):
                    problems.append("样式文件没加载上")
                    print(f"      样式文件没有加载上：{'、'.join(res['missingCss'])}。确认它和页面在同一个目录，文件名没有改。")
                elif res.get("unstyled"):
                    problems.append("页面没有样式")
                    print("      页面看起来是浏览器默认样式：ui-craft.css 没有生效。确认 <link rel=\"stylesheet\" href=\"ui-craft.css\"> 还在。")
                if res.get("brokenImages"):
                    problems.append("有图片加载失败")
                    print(f"      加载失败的图片：{'、'.join(str(x) for x in res['brokenImages'])}。换成真实存在的文件，或者删掉这张图。")
                if res.get("hasMotionAttrs") and not res.get("motion"):
                    # 无头模式下有时量不到（无限循环动画会拖住虚拟时钟），只提示不判失败
                    print("      提示：没检测到动效脚本。确认 </body> 前的 <script src=\"ui-craft.js\"></script> 还在；在真实浏览器里动效正常就不用管。")
        if not a.no_shots:
            print()
            shots = [(k, lab, w, heights.get(k, h), d) for k, lab, w, h, d in views] + [("dark", "暗色 1440", 1440, heights.get("wide", 900), True)]
            still.write_text(static_copy(page.read_text(encoding="utf-8", errors="replace")), encoding="utf-8")
            for key, label, w, h, dark in shots:
                png = out_dir / f"{key}.png"
                tmp.write_text(wrapper(still.name, w, h, dark, False), encoding="utf-8")
                run_browser(browser, profile, tmp.as_uri(), w, h, [f"--screenshot={png}", "--timeout=3000"])
                if png.is_file():
                    if w < 500:
                        try:
                            crop_png(png, w)
                        except Exception:
                            pass
                    print(f"  截图 {label} → {png}")
                else:
                    problems.append(f"{label}截图没有生成")
                    print(f"  截图 {label}：没有生成")
    finally:
        for f in helpers:
            try:
                f.unlink()
            except OSError:
                pass
        shutil.rmtree(profile, ignore_errors=True)

    print()
    if problems:
        print("未通过：" + "；".join(problems) + "。按上面的改法改完后重新运行。")
        return 1
    print("通过：已测视口未发现横向溢出或本地资源加载错误。CLI 整页截图使用静态校样副本，交互需在原页验证。")
    if not a.no_shots:
        print("能看图的话，打开三张截图各看一眼：有没有哪一块空着、挤着、文字压在一起、对比不够看不清。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
