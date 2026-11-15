"""Verify the authored palette at its public command-line entry points."""
import ast
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from colorkit import srgb_to_oklch, to_rgba, visible_ink_green
from contrast import contrast

MINT = "#36C9AC"


def run(script, *args, check=True):
    return subprocess.run(
        [sys.executable, "-B", "-X", "utf8", str(SCRIPTS / script), *map(str, args)],
        capture_output=True, encoding="utf-8", check=check,
    )


def export(kind, seed=MINT):
    return run("palette.py", seed, "--neutral", "tinted", "--export", kind).stdout


def lightness(color):
    return srgb_to_oklch(*to_rgba(color)[:3])[0]


class PaletteRegression(unittest.TestCase):
    def test_deep_seed_and_readable_roles(self):
        for seed in ("#253A32", "#164D35", MINT, "#A6CA53", "#345899"):
            with self.subTest(seed=seed):
                data = json.loads(export("json", seed))
                for theme in ("light", "dark"):
                    roles = data[theme]
                    for name, color in roles.items():
                        self.assertFalse(visible_ink_green(to_rgba(color)), (theme, name, color))
                    for fg, bg in (("text", "bg"), ("accent-fg", "accent"), ("ok", "ok-soft"), ("stage-ink", "stage")):
                        self.assertGreaterEqual(contrast(roles[fg], roles[bg])[0], 4.5, (theme, fg, bg))
                if seed == MINT:
                    for step in ("400", "500"):
                        level, chroma, hue = srgb_to_oklch(*to_rgba(data["ramps"]["accent"][step])[:3])
                        self.assertTrue(level > 0.60 and chroma > 0.05 and 145 < hue < 190)
                if seed == "#345899":
                    self.assertLess(to_rgba(data["dark"]["accent"])[0], to_rgba(data["dark"]["accent"])[2])

    def test_tailwind_yellowgreen_order_and_button_pair(self):
        css = export("tailwind4", "oklch(.75 .15 125)")
        shades = re.findall(r"--color-accent-(\d+): (#[A-F\d]+);", css)
        levels = [lightness(color) for _, color in shades]
        self.assertEqual(len(levels), 11)
        self.assertTrue(all(a > b for a, b in zip(levels, levels[1:])), levels)
        button, label = re.findall(r"--color-accent-(?:button|label): (#[A-F\d]+);", css)
        self.assertGreaterEqual(contrast(label, button)[0], 4.5)
        tailwind3 = export("tailwind", "oklch(.75 .15 125)")
        self.assertIn('"accent-button": "' + button + '"', tailwind3)
        self.assertIn('"accent-label": "' + label + '"', tailwind3)

    def test_element_and_game_composites(self):
        dark = export("element").split("html.dark {", 1)[1]
        shades = re.findall(r"--el-color-primary-light-\d+: (#[A-F\d]+);", dark)
        self.assertEqual(len(shades), 5)
        self.assertTrue(all(not visible_ink_green(to_rgba(s)) for s in shades))
        cpp = export("imgui")
        slots = {}
        for name, value in re.findall(r"c\[ImGuiCol_(\w+)\] = ImVec4\(([^)]+)\)", cpp):
            slots[name] = [float(v.strip().rstrip("f")) for v in value.split(",")]
        bg = slots["WindowBg"][:3]
        for name in ("FrameBgActive", "ButtonActive", "HeaderHovered", "TabHovered", "TabSelected"):
            red, green, blue, alpha = slots[name]
            displayed = [v * alpha + b * (1 - alpha) for v, b in zip((red, green, blue), bg)]
            self.assertFalse(visible_ink_green((*displayed, 1)), name)
        self.assertTrue(srgb_to_oklch(*slots["CheckMark"][:3])[0] > .67)

    def test_raw_measurement_and_svg_strokes(self):
        answer = run("contrast.py", "#104E33", "#FFFFFF").stdout
        self.assertIn("9.72", answer)
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "check.svg"
            for color in ("#164D35", "#164D357F", MINT, "currentColor"):
                run("icons.py", "check", "--svg-dir", folder, "--color", color)
                stroke = re.search(r'\bstroke="([^"]+)"', target.read_text(encoding="utf-8"))[1]
                if color in (MINT, "currentColor"):
                    self.assertEqual(stroke, color)
                else:
                    rgba = to_rgba(stroke)
                    self.assertFalse(visible_ink_green((*rgba[:3], 1)))
                    self.assertEqual(rgba[3], to_rgba(color)[3])

    def test_runtime_layer_tokens_and_desktop_swatches(self):
        with tempfile.TemporaryDirectory() as folder:
            page = Path(folder) / "app.html"
            run("scaffold.py", "--type", "tool", "--style", "graphite", "--accent", MINT,
                "--single", "--system-fonts", "--out", page)
            css = page.read_text(encoding="utf-8")
            self.assertIn("--accent-layer: light-dark(", css)
            for selector in (r"\.axis2 \.blk", r"\.axis2 \.blk\.now"):
                decl = re.search(selector + r"\s*\{([^{}]+)\}", css)[1]
                self.assertIn("var(--accent-layer", decl)
        tree = ast.parse(export("ttk"))
        dark = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                    and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "DARK")
        roles = json.loads(export("json"))["dark"]
        self.assertEqual(dark["accent"], roles["accent"])
        overlay = to_rgba(dark["layers"][dark["accent"]])[:3]
        surface = to_rgba(dark["surface"])[:3]
        self.assertFalse(visible_ink_green((*[a * .26 + b * .74 for a, b in zip(overlay, surface)], 1)))

    def test_recolor_gradient_and_static_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for mode in ("hex", "vars"):
                path = root / (mode + ".html")
                path.write_text('<style>.bar{background:linear-gradient(90deg,#bc391e,#d54e29,#e55c32,#fa6a37)}</style>', encoding="utf-8")
                run("recolor.py", path, "--style", "graphite", "--accent", MINT,
                    "--theme", "dark", "--to", mode, "--write")
                result = path.read_text(encoding="utf-8")
                bar = re.search(r"\.bar\{([^}]+)\}", result)[1]
                if mode == "vars":
                    self.assertIn("var(--accent-layer)", bar)
                else:
                    stops = re.findall(r"#[a-f\d]{6}", bar, re.I)
                    self.assertEqual(len(stops), 4)
                    self.assertTrue(all(not visible_ink_green(to_rgba(x)) for x in stops))
            artifact = root / "paint.html"
            blocks = (
                ('<style>.tile{background:#164D35}</style>', True),
                ('<svg><path stroke="#203930"/></svg>', True),
                ('<style>#164d35{color:#345899;background:url(#164d35)}</style><p>#164D35</p>', False),
                ('<p style="color:#36C9AC">薄荷</p>', False),
            )
            for content, flagged in blocks:
                artifact.write_text('<!doctype html><html lang="zh"><title>颜色</title>' + content + '</html>', encoding="utf-8")
                report = run("audit.py", artifact, "--gate", "--json", "--allow-sample", check=False)
                findings = json.loads(report.stdout)["findings"]
                self.assertEqual(any("禁用的墨绿" in x["title"] for x in findings), flagged, content)


if __name__ == "__main__":
    unittest.main()

