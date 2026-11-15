"""Replay the published rhythm example and compare its visible gate with real inputs."""
import argparse
from datetime import datetime, timedelta, timezone
from io import BytesIO
from itertools import groupby
from pathlib import Path

from PIL import Image
from playwright.sync_api import expect, sync_playwright

GAME = Path(__file__).resolve().parents[1] / "examples" / "festival-beat.html"


def read_edges(page, width, height):
    image = Image.open(BytesIO(page.screenshot())).convert("RGB")
    y = round(height * .75 - min(width / 850, height / 540) * 8)
    bright = []
    for x in range(round(width * .30), round(width * .70)):
        r, g, b = image.getpixel((x, y))
        if r > 205 and g > 195 and b > 135:
            bright.append(x)
    groups = [list(group) for _, group in groupby(enumerate(bright), lambda entry: entry[1] - entry[0])]
    assert len(groups) == 2, groups
    return [(group[0][1] + group[-1][1]) / 2 for group in groups]


def advance(page, elapsed_ms):
    current = page.evaluate("performance.now() - epoch")
    page.clock.run_for(round(elapsed_ms - current))


def run_view(browser, width, height, touch):
    context = browser.new_context(viewport={"width": width, "height": height}, offline=True,
                                  has_touch=touch, is_mobile=touch, reduced_motion="reduce" if touch else "no-preference")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    origin = datetime(2025, 1, 1, tzinfo=timezone.utc)
    page.clock.install(time=origin)
    page.goto(GAME.as_uri())
    page.clock.pause_at(origin + timedelta(seconds=2))
    button = page.get_by_role("button")
    strike = button.tap if touch else lambda: page.keyboard.press("Space")
    strike()
    left, right = read_edges(page, width, height)
    expected = width * .29 * .21
    assert abs(left - (width / 2 - expected)) <= 1.1 and abs(right - (width / 2 + expected)) <= 1.1

    # First beat at 1150 ms, subsequent beats 680 ms apart. Check both sides of the 210 ms limit.
    for at, score in [(939, 0), (941, 1), (2039, 2), (2721, 2)]:
        advance(page, at)
        strike()
        expect(page.locator("#score")).to_have_text(f"{score} / 8")
        assert page.locator("#feedback").text_content() == ("合拍" if at in (941, 2039) else "未合拍")
    advance(page, 6600)
    expect(button).to_have_text("再打一轮")
    strike()
    expect(page.locator("#score")).to_have_text("0 / 8")
    assert not errors, errors
    print(f"{width}×{height}, gate {left:.1f}…{right:.1f}: boundary inputs, finish and restart passed")
    context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser", required=True)
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser)
        run_view(browser, 1120, 680, False)
        run_view(browser, 360, 780, True)
        browser.close()


if __name__ == "__main__":
    main()
