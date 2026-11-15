"""Run with Python 3 from any directory. Exercises the public JSON and exit-code contract."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts" / "audit.py"


def document(body, head="", lang="zh-CN"):
    language = f' lang="{lang}"' if lang else ""
    return f'<!doctype html><html{language}><head><meta name="viewport" content="width=device-width">{head}</head><body>{body}</body></html>'


class AuditTest(unittest.TestCase):
    def audit(self, sources, expected, *options):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name, source in sources.items():
                filename = Path(directory, name)
                filename.write_text(source, encoding="utf-8")
                paths.append(str(filename))
            result = subprocess.run(
                [sys.executable, "-B", str(AUDIT), "--gate", "--json", *options, *paths],
                capture_output=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            self.assertEqual(result.returncode, expected, result.stderr or result.stdout)
            findings = json.loads(result.stdout)["findings"]
            self.assertEqual(any(item["level"] == "问题" for item in findings), expected == 1)
            return findings

    def test_ordinary_content_and_reused_terms(self):
        self.audit({"index.html": document("<h1>Acme</h1><h2>租赁合同</h2><p>张三</p>"
                   "<label>标题<input></label><label>Description<textarea></textarea></label>")}, 0)

    def test_template_evidence_belongs_to_one_page(self):
        data = {"a.html": document("Meridian · 400 页"), "b.html": document("租赁合同")}
        self.audit(data, 0)
        data["a.html"] = document("Meridian · 400 页 · 租赁合同")
        findings = self.audit(data, 1)
        self.assertTrue(any("a.html" in i["detail"] and "launch.html" in i["detail"] for i in findings))
        self.audit(data, 0, "--allow-sample")

    def test_examples_in_code(self):
        self.audit({"docs.html": document('<pre>Meridian · 400 页 · 租赁合同</pre><p>示例的参数是 maximum-scale=1。</p>'
                   '<code>Lorem ipsum dolor sit amet</code>')}, 0)

    def test_explicit_filler(self):
        self.audit({"test.html": document("Lorem ipsum dolor sit amet")}, 1)
        self.audit({"test.html": document("Lorem ipsum dolor sit amet")}, 0, "--allow-sample")

    def test_zoom_in_real_viewport(self):
        self.audit({"a.html": document("", '<meta CONTENT="maximum-scale=1.5" NAME=viewport>')}, 0)
        for v in ("maximum-scale=1.00", "user-scalable=no"):
            with self.subTest(v=v):
                self.audit({"a.html": document("", f"<meta NAME=viewport CONTENT='{v}'>")}, 1, "--allow-sample")

    def test_labels_are_per_control_and_per_page(self):
        self.audit({"a.html": document('<label for="save">保存</label><input id=save type=checkbox>')}, 0)
        self.audit({"a.html": document('<label><input type=radio name=g>标准模式</label>')}, 0)
        self.audit({"a.html": document('<label for=next>下一项</label>'),
                    "b.html": document('<input id=next type=checkbox>')}, 1)
        self.audit({"a.html": document('<label><input type=checkbox></label>')}, 1)

    def test_document_language_and_images(self):
        self.audit({"a.html": document("甲"), "b.html": document("乙", lang="")}, 1)
        self.audit({"a.html": document('<img src="badge.svg">')}, 1, "--allow-sample")
        self.audit({"a.html": document('<img src="badge.svg" alt="">')}, 0)

    def test_runtime_and_components(self):
        self.audit({"a.html": document("<button></button><script>document.querySelector('button').textContent='确认';</script>")}, 0)
        self.audit({"Card.vue": '<template><button :aria-label="action"></button><input type=checkbox></template>'}, 0)

    def test_focus_is_a_runtime_question(self):
        self.audit({"a.html": document('<div class="divider"></div><button>确认</button>', "<style>.divider{outline:none}</style>")}, 0)
        findings = self.audit({"a.html": document('<button>确认</button>', "<style>button:focus{outline:none}</style>")}, 0)
        self.assertTrue(any(i["level"] == "留意" and "焦点" in i["title"] for i in findings))

    def test_explicit_sample_does_not_hide_missing_name(self):
        body = "<p>青梧图书馆 · 长安的荔枝 · 读者证号</p><button></button>"
        self.audit({"a.html": document(body)}, 1, "--allow-sample")

    def test_inert_html_and_hidden_button_content(self):
        self.audit({"a.html": document('<template><input type=checkbox></template><button>保存</button>')}, 0)
        self.audit({"a.html": document('<button><svg aria-hidden="true"><title>图标</title></svg></button>')}, 1)

    def test_renamed_kit_image_is_matched_by_content(self):
        import base64
        picture = next((ROOT / "assets" / "compare").glob("*.webp"))
        encoded = base64.b64encode(picture.read_bytes()).decode("ascii")
        html = document('<img alt="对照图" src="data:image/webp;base64,' + encoded + '">')
        findings = self.audit({"page.html": html}, 1)
        self.assertTrue(any("套件示例图片" in i["title"] for i in findings))
        self.audit({"page.html": html}, 0, "--allow-sample")

    def test_engine_default_color_is_observational(self):
        result = self.audit({"ui.cpp": "void menu() { ImGui::StyleColorsDark(); ImGui::Button(\"OK\"); }"}, 0)
        self.assertTrue(any(i["level"] == "信息" and "ImGui" in i["title"] for i in result))


if __name__ == "__main__":
    unittest.main()

