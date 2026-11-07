"""Regression: both gen_extras charts must paint an opaque backdrop rect.

GitHub renders these SVGs inside <img>; an SVG without a painted background
inherits the README surface, so the pale #c0caf5 labels vanish on a white page.
"""
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gen_extras  # noqa: E402

NS = "{http://www.w3.org/2000/svg}"


def langs_fixture():
    return {
        "repositories": {
            "nodes": [
                {
                    "languages": {
                        "edges": [
                            {"size": 600, "node": {"name": "Python", "color": "#3572A5"}},
                            {"size": 400, "node": {"name": "TypeScript", "color": "#3178c6"}},
                        ]
                    }
                },
                {"languages": {"edges": [{"size": 200, "node": {"name": "Python", "color": "#3572A5"}}]}},
            ]
        }
    }


def activity_fixture():
    weeks = []
    for w, count in enumerate((4, 9, 2)):
        days = [{"date": f"2026-01-{w * 7 + d + 1:02d}", "contributionCount": count} for d in range(7)]
        weeks.append({"contributionDays": days})
    return {
        "contributionsCollection": {
            "contributionCalendar": {"totalContributions": 105, "weeks": weeks}
        }
    }


class OpaqueBackdropTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR") or None)
        self._saved_assets = gen_extras.ASSETS
        gen_extras.ASSETS = self.tmp.name

    def tearDown(self):
        gen_extras.ASSETS = self._saved_assets
        self.tmp.cleanup()

    def assert_opaque_backdrop(self, name, width, height):
        path = os.path.join(self.tmp.name, name)
        # stdlib parser is fine here: input is our own writer's output, never external XML.
        root = ET.parse(path).getroot()  # raises on invalid XML
        self.assertEqual(root.tag, NS + "svg")

        gradients = {g.get("id"): g for g in root.iter(NS + "linearGradient")}
        frames = [
            r
            for r in root.findall(NS + "rect")
            if r.get("width") == str(width - 2) and r.get("height") == str(height - 2)
        ]
        self.assertTrue(frames, f"{name}: no full-size backdrop rect")

        fill = frames[0].get("fill")
        self.assertNotIn(fill, (None, "none", "transparent"), f"{name}: backdrop is not painted")
        if fill == "url(#bg)":
            self.assertIn("bg", gradients, f"{name}: url(#bg) has no gradient def")
            for stop in gradients["bg"].findall(NS + "stop"):
                self.assertTrue(stop.get("stop-color"), f"{name}: gradient stop without colour")
                self.assertIn(stop.get("stop-opacity", "1"), ("1", "1.0"),
                              f"{name}: gradient stop is translucent")

    def test_langs_has_opaque_backdrop(self):
        gen_extras.langs_svg(langs_fixture())
        self.assert_opaque_backdrop("langs.svg", 860, 190)

    def test_activity_has_opaque_backdrop(self):
        gen_extras.activity_svg(activity_fixture())
        self.assert_opaque_backdrop("activity.svg", 860, 270)


if __name__ == "__main__":
    unittest.main(verbosity=2)
