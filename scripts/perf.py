#!/usr/bin/env python3
"""滚动流畅度实测：用本机浏览器像真人一样滚完整页，量每一帧的耗时，找出拖慢滚动的写法。

用法:
  python perf.py 页面.html                    # 宽屏与手机各滚一遍，CPU 降速 4 倍（模拟普通笔记本）
  python perf.py 页面.html --cpu 1            # 不降速
  python perf.py 页面.html --cpu 6 --mobile-only
  python perf.py 页面.html --browser "允许的兼容浏览器可执行文件"

需要已安装 Playwright（pip install playwright；用本机 Chrome / Edge，不用另外下载浏览器）。

判定（CPU 降速后）：
  慢帧（超过 20 毫秒，60Hz 屏幕上会被看出卡顿）不超过 2%、最长一帧不超过 50 毫秒为"流畅"；
  最长一帧在 100 毫秒以内为"基本流畅"（多是区块第一次出现时的绘制），也算通过。
  无头浏览器没有显卡加速，数字比真机悲观；它的用处是比较：改之前和改之后、这一页和另一页。

同时列出代码里会拖慢滚动的写法（与 audit.py 的"滚动性能"检查相同），每条附改法。
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RECORDER = r"""() => {
  window.__frames = []; window.__loaf = []; window.__maxY = 0;
  addEventListener('scroll', () => { if (scrollY > window.__maxY) window.__maxY = scrollY; }, { passive: true });
  let last = performance.now(), on = true;
  window.__where = [];
  const near = () => { const e = document.elementFromPoint(innerWidth / 2, innerHeight / 2); const sec = e && e.closest('section, header, footer, main > *, article');
    return sec ? (sec.tagName.toLowerCase() + (sec.id ? '#' + sec.id : '') + (sec.className && typeof sec.className === 'string' ? '.' + sec.className.trim().split(/\s+/).slice(0, 2).join('.') : '')) : '?'; };
  const tick = (t) => { if (!on) return; const d = t - last; window.__frames.push(d); if (d > 34) window.__where.push([Math.round(d), Math.round(scrollY), near()]); last = t; requestAnimationFrame(tick); };
  requestAnimationFrame((t) => { last = t; requestAnimationFrame(tick); });
  window.__stop = () => { on = false; };
  try {
    new PerformanceObserver((list) => {
      for (const e of list.getEntries()) {
        const s = (e.scripts || []).map(x => (x.sourceFunctionName || x.invoker || '') + ' @ ' + (x.sourceURL || '').split('/').pop() + ' ' + Math.round(x.duration) + 'ms');
        window.__loaf.push({ d: Math.round(e.duration), style: Math.round(e.styleAndLayoutStart ? e.startTime + e.duration - e.styleAndLayoutStart : 0), s });
      }
    }).observe({ type: 'long-animation-frame', buffered: false });
  } catch (err) {}
}"""


def metrics(cdp) -> dict:
    return {m["name"]: m["value"] for m in cdp.send("Performance.getMetrics")["metrics"]}


def run_view(pw, browser_path: str, page: Path, w: int, h: int, cpu: float, mobile: bool) -> dict:
    b = pw.chromium.launch(executable_path=browser_path, args=["--enable-gpu-rasterization"])
    ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if mobile else 1,
                        is_mobile=mobile, has_touch=mobile, reduced_motion="no-preference")
    tab = ctx.new_page()
    cdp = ctx.new_cdp_session(tab)
    cdp.send("Performance.enable")
    tab.goto(page.as_uri())
    tab.wait_for_timeout(1800)                        # 等首屏编排放完
    if cpu > 1:
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": cpu})
    total = tab.evaluate("() => Math.max(document.documentElement.scrollHeight, document.body.scrollHeight) - innerHeight")
    tab.evaluate(RECORDER)
    m0 = metrics(cdp)
    dist = max(0, int(total))
    # 像滚轮一样滚：先往下滚到底，再滚回顶部
    for direction in (1, -1):
        left = dist
        while left > 0:
            step = min(left, 1600)
            cdp.send("Input.synthesizeScrollGesture", {"x": w // 2, "y": h // 2, "yDistance": -step * direction,
                                                       "speed": 1800, "gestureSourceType": "mouse",
                                                       "preventFling": True})
            left -= step
    tab.wait_for_timeout(300)
    m1 = metrics(cdp)
    frames = tab.evaluate("() => { window.__stop(); return window.__frames; }")
    loaf = tab.evaluate("() => window.__loaf")
    reached = tab.evaluate("() => window.__maxY")
    where = tab.evaluate("() => window.__where")
    b.close()
    frames = [f for f in frames[2:] if f < 1000]
    secs = max(0.001, sum(frames) / 1000)
    return {
        "frames": frames, "loaf": loaf, "secs": secs, "scroll": dist, "reached": reached, "where": where,
        "style_per_s": (m1.get("RecalcStyleCount", 0) - m0.get("RecalcStyleCount", 0)) / secs,
        "layout_per_s": (m1.get("LayoutCount", 0) - m0.get("LayoutCount", 0)) / secs,
        "script_ms": (m1.get("ScriptDuration", 0) - m0.get("ScriptDuration", 0)) * 1000,
        "style_ms": (m1.get("RecalcStyleDuration", 0) - m0.get("RecalcStyleDuration", 0)) * 1000,
        "layout_ms": (m1.get("LayoutDuration", 0) - m0.get("LayoutDuration", 0)) * 1000,
    }


def report(label: str, r: dict) -> bool:
    f = r["frames"]
    if r["scroll"] > 50 and r.get("reached", 0) < r["scroll"] * 0.5:
        print(f"  {label}：没能滚动起来（可滚 {r['scroll']}px，实际只到 {r.get('reached', 0):.0f}px），这一项的数字不可信")
        return True
    if len(f) < 10:
        print(f"  {label}：页面太短或没有滚动（可滚 {r['scroll']}px），跳过")
        return True
    slow = sum(1 for x in f if x > 20) / len(f)
    p95 = sorted(f)[int(len(f) * 0.95) - 1]
    worst = max(f)
    fps = 1000 / statistics.mean(f)
    smooth = slow <= 0.02 and worst <= 50
    ok = slow <= 0.02 and worst <= 100
    verdict = "流畅" if smooth else ("基本流畅：偶有一帧较长，多是某个区块第一次出现时的绘制" if ok else "会卡")
    print(f"  {label}：平均 {fps:.0f} 帧/秒，慢帧 {slow:.1%}，95% 的帧在 {p95:.1f}ms 内，最长一帧 {worst:.0f}ms"
          f"  —— {verdict}")
    print(f"      滚动期间每秒：样式重算 {r['style_per_s']:.0f} 次、布局 {r['layout_per_s']:.0f} 次；"
          f"脚本 {r['script_ms']:.0f}ms、样式 {r['style_ms']:.0f}ms、布局 {r['layout_ms']:.0f}ms（共 {r['secs']:.1f} 秒）")
    if r["layout_per_s"] > 25:
        print("      滚动时在反复布局：多半是滚动回调里先改样式再读位置（getBoundingClientRect / offsetTop），"
              "或者动画了 width / height / top / left。读写分开，并改用 transform / opacity。")
    if r["style_per_s"] > 120:
        print("      滚动时每帧都在重算样式：多半是滚动回调里改了会被继承的 CSS 变量，或每帧切换类名。"
              "用 @property 把变量设成不继承，只在值变化时才写。")
    if r.get("where"):
        spots = "；".join(f"{d}ms 在 {y}px 处（{sec}）" for d, y, sec in sorted(r["where"], key=lambda x: -x[0])[:4])
        print(f"      慢帧出现的位置：{spots}")
    long = sorted(r["loaf"], key=lambda e: -e["d"])[:3]
    for e in long:
        if e["d"] >= 50:
            src = "；".join(e["s"][:2]) or "（不是脚本：多半是绘制或合成——大面积模糊、混合模式、毛玻璃）"
            print(f"      长帧 {e['d']}ms：{src}")
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="滚动流畅度实测", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("page")
    ap.add_argument("--cpu", type=float, default=4, help="CPU 降速倍数（默认 4，模拟普通笔记本；1 表示不降速）")
    ap.add_argument("--browser", help="允许的 Chromium 兼容浏览器可执行文件")
    scope = ap.add_mutually_exclusive_group()
    scope.add_argument("--mobile-only", action="store_true")
    scope.add_argument("--desktop-only", action="store_true")
    a = ap.parse_args()
    if not 1 <= a.cpu < float("inf"):
        ap.error("--cpu 须为不小于 1 的有限数值。")

    page = Path(a.page).resolve()
    if page.is_dir():
        page = page / "index.html"
    if not page.is_file():
        print(f"找不到页面：{page}")
        return 2
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("当前 Python 环境缺少 Playwright，可使用已有该依赖的环境，或在允许的浏览器中记录一次滚动。")
        return 2
    import shot
    browser = shot.find_browser(a.browser)
    if not browser:
        print("未找到可用浏览器。用 --browser 指定允许的浏览器路径。")
        return 2

    print(f"滚动实测：{page.name}（CPU 降速 {a.cpu:g} 倍）\n")
    views = []
    if not a.mobile_only:
        views.append(("宽屏 1440", 1440, 900, False))
    if not a.desktop_only:
        views.append(("手机 390", 390, 844, True))
    ok = True
    with sync_playwright() as pw:
        for label, w, h, mobile in views:
            ok &= report(label, run_view(pw, browser, page, w, h, a.cpu, mobile))

    try:
        import audit
        files = audit.collect([str(page)] + ([str(page.parent / "ui-craft.css")] if (page.parent / "ui-craft.css").exists() else []))
        css, lib, markup = audit.load(files)
        rep = audit.Report()
        audit.check_scroll_perf(css, markup, rep)
        if rep.items:
            print("\n代码里会拖慢滚动的写法：")
            for it in rep.items:
                print(f"  · {it['title']}" + (f"（{it['detail']}）" if it["detail"] else ""))
                print(f"    改法：{it['fix']}")
    except Exception:
        pass

    print("\n" + ("通过：滚动流畅。" if ok else "未通过：滚动会卡。按上面的提示改，改完再跑一次对比。"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
