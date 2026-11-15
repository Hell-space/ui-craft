"""在允许的 Chromium 系浏览器中实际操作生成页。通过 --browser 指定可执行文件。"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def position(element):
    return element.evaluate("""el => {
        const r = el.getBoundingClientRect();
        return [r.left, r.top, r.width, window.scrollX, window.scrollY];
    }""")


def check_position(element, before, step):
    after = position(element)
    assert all(abs(a - b) <= 1 for a, b in zip(after, before)), f"{step}: {before} -> {after}"


def start_at(element):
    element.evaluate("el => el.scrollIntoView({block: 'center', behavior: 'instant'})")
    before = position(element)
    assert before[-1] > 0, f"测试需要从已滚动的位置开始，实际为 {before}"
    return before


def activate(element, touch):
    if touch:
        element.tap()
    else:
        element.click()


def check_article(page, directory, touch):
    page.goto((directory / "article.html").as_uri())
    follow = page.get_by_role("button", name="关注陈默")
    before = start_at(follow)
    url = page.url
    for state in ("true", "false"):
        activate(follow, touch)
        expect(follow).to_have_attribute("aria-pressed", state)
        check_position(follow, before, "切换关注")
        assert page.url == url

    if not touch:
        page.locator('.toc a[href="#water"]').click()
        expect(page.locator("#water")).to_be_in_viewport()
        assert page.url.endswith("#water")


def check_timer(page, directory, touch):
    page.goto((directory / "tool.html").as_uri())
    trigger = page.locator("#custom-time")
    dialog = page.locator("#duration")
    for action in ("取消", "应用时长", "Escape"):
        before = start_at(trigger)
        activate(trigger, touch)
        expect(page.locator("#minutes")).to_be_focused()
        check_position(trigger, before, "打开时长弹窗")
        dialog.evaluate("el => Promise.all(el.getAnimations().map(a => a.finished))")
        page.mouse.move(8, 80)
        page.mouse.wheel(0, -180)
        page.wait_for_timeout(250)  # 浏览器异步派发滚轮并绘制下一帧
        check_position(trigger, before, "模态背景收到滚轮")
        if action == "Escape":
            page.keyboard.press("Escape")
        else:
            if action == "应用时长":
                page.locator("#minutes").fill("137")
            activate(dialog.get_by_role("button", name=action), touch)
        expect(dialog).to_be_hidden()
        expect(trigger).to_be_focused()
        check_position(trigger, before, action)
    expect(trigger).to_have_text("137 分")
    page.keyboard.press("Tab")
    expect(page.locator("#skip")).to_be_focused()
    page.mouse.move(8, 80)
    page.mouse.wheel(0, -180)
    page.wait_for_function("y => scrollY < y - 1", arg=before[-1])


def check_nested(page):
    page.goto((ROOT / "evals/evidence/prism-nights.html").as_uri())
    page.locator('#lineup [data-toggle="tide"]').tap()
    trigger = page.locator('#lineup [data-open="mirror"]')
    home = start_at(trigger)
    trigger.tap()
    sheet = page.locator("#sheet")
    join = sheet.locator('[data-focus="toggle"]')
    check_position(trigger, home, "打开作品详情")
    sheet.hover()
    page.mouse.wheel(0, 700)
    page.wait_for_function("""() => {
        const el = document.getElementById('sheet');
        return el.scrollTop > 0 && el.scrollTop >= el.scrollHeight - el.clientHeight - 1;
    }""")
    parent_scroll = sheet.evaluate("el => el.scrollTop")
    parent = position(join)
    page.mouse.wheel(0, 400)
    page.wait_for_timeout(250)
    check_position(trigger, home, "详情滚到底后继续滚动")
    join.tap()
    expect(sheet.locator("#sheet-title")).to_have_text("场次撞时")
    check_position(trigger, home, "打开第二层")
    page.keyboard.press("Escape")
    expect(join).to_be_focused()
    assert abs(sheet.evaluate("el => el.scrollTop") - parent_scroll) <= 1
    check_position(join, parent, "返回上一层详情")
    sheet.get_by_role("button", name="关闭", exact=True).tap()
    expect(trigger).to_be_focused()
    check_position(trigger, home, "返回节目单")


def check_disclosure(page, directory):
    page.goto((directory / "form.html").as_uri())
    trigger = page.get_by_role("button", name="忘了密码")
    before = position(trigger)
    submit = page.locator("#submit")
    submit_top = position(submit)[1]
    trigger.click()
    expect(page.locator("#pw-help")).to_be_visible()
    check_position(trigger, before, "展开密码提示")
    assert position(submit)[1] > submit_top
    trigger.click()
    expect(page.locator("#pw-help")).to_be_hidden()
    check_position(trigger, before, "收起密码提示")
    assert abs(position(submit)[1] - submit_top) <= 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
        directory = Path(tmp)
        for kind in ("article", "tool", "form"):
            subprocess.run([sys.executable, "-B", str(ROOT / "scripts/scaffold.py"),
                            "--type", kind, "--single", "--system-fonts", "--out", str(directory / f"{kind}.html")],
                           check=True, stdout=subprocess.DEVNULL)
        browser = playwright.chromium.launch(executable_path=args.browser, ignore_default_args=["--hide-scrollbars"])
        for width, height, touch in ((1280, 640, False), (390, 515, True)):
            page = browser.new_page(viewport={"width": width, "height": height}, has_touch=touch, is_mobile=touch)
            check_article(page, directory, touch)
            check_timer(page, directory, touch)
            if touch:
                check_nested(page)
            page.close()
            print(f"{width} × {height} 位置与焦点检查通过")
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        check_disclosure(page, directory)
        page.close()
        print("1440 × 900 行内展开检查通过")
        browser.close()


if __name__ == "__main__":
    main()
