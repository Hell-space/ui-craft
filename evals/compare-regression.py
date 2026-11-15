"""Exercise the generated scan comparison with real ink at the image edges."""
import argparse
import io
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAPER = (247, 239, 227)
INK = {"reference": (35, 98, 152), "before": (154, 46, 62), "after": (72, 54, 133)}
# Four corners, both sides at the old handle height, and the two contours around the notch.
MARKS = ((.025, .03), (.975, .03), (.025, .97), (.975, .97), (.025, .5), (.975, .5), (.63, .30), (.69, .32))


def make_plates(directory, size):
    for state, ink in INK.items():
        image = Image.new("RGB", size, PAPER)
        draw = ImageDraw.Draw(image)
        for u, v in MARKS:
            x, y = round(u * size[0]), round(v * size[1])
            draw.rectangle((x - 12, y - 12, x + 12, y + 12), fill=ink)
        image.save(directory / "media" / f"registration-{state}.webp", lossless=True)


def check_ink(screenshot, state, points):
    image = Image.open(io.BytesIO(screenshot)).convert("RGB")
    for u, v in points:
        xy = (round(u * (image.width - 1)), round(v * (image.height - 1)))
        actual = image.getpixel(xy)
        assert max(abs(a - b) for a, b in zip(actual, INK[state])) <= 8, (state, xy, actual)


def check_view(page, directory, size):
    page.goto((directory / "index.html").as_uri())
    page.get_by_role("link", name="比较两次扫描").click()
    board = page.locator("#board")
    slider = page.get_by_role("slider")
    layer = page.get_by_role("checkbox", name="叠加朱红稿")
    board.locator("img").evaluate_all("imgs => Promise.all(imgs.map(i => i.decode()))")
    box = board.bounding_box()
    assert abs(box["height"] - box["width"] * size[1] / size[0]) <= 1
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    check_ink(board.screenshot(), "before", MARKS[-2:])
    for key, state in (("Home", "after"), ("End", "before")):
        slider.press(key)
        check_ink(board.screenshot(), state, MARKS)
        layer.uncheck()
        expect(slider).to_be_hidden()
        check_ink(board.screenshot(), "reference", MARKS)
        layer.check()
        check_ink(board.screenshot(), state, MARKS)

    slider.press("ArrowLeft")
    expect(slider).to_have_value("99")
    page.locator('label[for="view-detail"]').click()
    check_ink(board.screenshot(), "before", [(.5, .5)])
    slider.press("Home")
    check_ink(board.screenshot(), "after", [(.5, .5)])
    layer.uncheck()
    check_ink(board.screenshot(), "reference", [(.5, .5)])
    layer.check()
    page.locator('label[for="view-whole"]').click()
    expect(slider).to_have_value("0")
    check_ink(board.screenshot(), "after", MARKS)


def swipe(cdp, start_x, start_y, dx, dy):
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": start_x, "y": start_y}]})
    for step in range(1, 11):
        point = {"x": start_x + dx * step / 10, "y": start_y + dy * step / 10}
        cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [point]})
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


def check_touch(page):
    board = page.locator("#board")
    slider = page.get_by_role("slider")
    board.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'instant'})")
    box = board.bounding_box()
    x, y, width = box["x"], box["y"] + box["height"] / 2, box["width"]
    scroll_before = page.evaluate("scrollY")
    assert scroll_before > 50
    cdp = page.context.new_cdp_session(page)
    swipe(cdp, x + width * .22, y, width * .56, 0)
    horizontal = slider.input_value()
    assert 75 <= int(horizontal) <= 81 and abs(page.evaluate("scrollY") - scroll_before) <= 1
    swipe(cdp, x + width * .64, y, 0, 100)
    page.wait_for_function("y => scrollY < y - 30", arg=scroll_before)
    expect(slider).to_have_value(horizontal)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
        directory = Path(tmp)
        subprocess.run([sys.executable, "-B", str(ROOT / "scripts/scaffold.py"), "--type", "compare",
                        "--system-fonts", "--motion", "system", "--out", tmp], check=True, stdout=subprocess.DEVNULL)
        browser = playwright.chromium.launch(executable_path=args.browser)
        for size in ((1200, 780), (780, 1200)):
            make_plates(directory, size)
            for w, h in ((1366, 864), (768, 900), (360, 780)):
                page = browser.new_page(viewport={"width": w, "height": h}, has_touch=w < 500,
                                        is_mobile=w < 500, reduced_motion="reduce")
                check_view(page, directory, size)
                if w == 360 and size[0] > size[1]:
                    check_touch(page)
                    print("Touch: horizontal seek and vertical scroll passed")
                page.close()
                print(f"{size[0]}×{size[1]} at {w}×{h}: edges, layer and zoom passed")
        browser.close()


if __name__ == "__main__":
    main()
