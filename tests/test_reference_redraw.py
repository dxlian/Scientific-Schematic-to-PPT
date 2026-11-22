"""Bilingual DrawingML and registered source/render proof checks."""
import sys
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_pptx import audit
from build_pptx import NS, build
from compare_render import compare


def bilingual_scene():
    return {"version": 1, "width_mm": 100, "height_mm": 50,
            "elements": [{"type": "text", "id": "label", "x": 5, "y": 8, "w": 70, "h": 12,
                          "runs": [{"text": "载荷 "}, {"text": "F", "italic": True}, {"text": " (N)"}]}]}


class TextFonts(unittest.TestCase):
    def test_defaults_on_every_run_and_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            pptx = build(bilingual_scene(), Path(tmp) / "test.pptx")
            result = audit(pptx, True, font_latin="Times New Roman", font_ea="SimSun")
            self.assertTrue(result["passed"], result["errors"])
            self.assertEqual(result["fonts_by_script"], {"latin": ["Times New Roman"], "ea": ["SimSun"]})
            with ZipFile(pptx) as archive:
                theme = ET.fromstring(archive.read("ppt/theme/theme1.xml"))
                for slot in ("majorFont", "minorFont"):
                    self.assertEqual(theme.find(f".//a:{slot}/a:ea", NS).get("typeface"), "SimSun")
                slide = ET.fromstring(archive.read("ppt/slides/slide1.xml"))
                self.assertEqual([run.text for run in slide.findall(".//a:r/a:t", NS)], ["载荷 ", "F", " (N)"])
                self.assertEqual(slide.findall(".//a:r/a:rPr", NS)[1].get("i"), "1")
            self.assertFalse(audit(pptx, True, font_ea="Times New Roman")["passed"])

    def test_existing_uniform_overrides_and_specific_inheritance(self):
        with tempfile.TemporaryDirectory() as tmp:
            scene = bilingual_scene()
            scene["font"] = "Arial"
            legacy = build(scene, Path(tmp) / "legacy.pptx")
            self.assertTrue(audit(legacy, True, font="Arial")["passed"])
            scene["font_ea"] = "SimSun"
            scene["elements"][0]["font_latin"] = "Georgia"
            scene["elements"][0]["runs"][0]["font_ea"] = "SimHei"
            revised = build(scene, Path(tmp) / "custom.pptx")
            result = audit(revised)
            self.assertEqual(result["fonts_by_script"], {"latin": ["Georgia"], "ea": ["SimHei", "SimSun"]})


class ReferenceProof(unittest.TestCase):
    def test_overlay_and_crop_registration(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow needed for visual proof")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = {"regions": [{"name": "inset", "box": [0, 0, 0.5, 0.5]}]}
            source, same, mismatch = (root / name for name in ["a.png", "b.png", "c.png"])
            Image.new("RGBA", (200, 100), (0, 0, 0, 0)).save(source)
            Image.new("RGB", (400, 200), "white").save(same)
            Image.new("RGB", (400, 280), "white").save(mismatch)
            files = compare(source, same, data, root / "good", "Original", overlay=True)
            self.assertEqual(len(files), 4)
            with Image.open(files[1]) as proof:
                self.assertEqual(proof.getpixel((5, 5)), (255, 255, 255))
            with self.assertRaisesRegex(ValueError, "aspect ratios"):
                compare(source, mismatch, data, root / "bad", overlay=True)
            self.assertFalse((root / "bad").exists())


if __name__ == "__main__":
    unittest.main()
