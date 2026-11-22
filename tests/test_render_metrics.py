"""Compare registered full-view and region metrics on synthetic images with known differences."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_render import compare


class RenderMetrics(unittest.TestCase):
    def setUp(self):
        try:
            import cv2
            import numpy
            from PIL import Image
        except ImportError:
            self.skipTest("Optional metrics need Pillow, NumPy and OpenCV")
        self.Image = Image
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def test_mae_foreground_and_half_open_local_crop(self):
        src = self.Image.new("RGBA", (20, 10), (0, 12, 70, 0))
        src.paste((242, 255, 255, 255), (0, 0, 10, 10))
        out = self.Image.new("RGB", src.size, "white")
        out.paste((239, 252, 252), (0, 0, 10, 10))
        src.save(self.root / "src.png")
        out.save(self.root / "out.png")
        regions = {"regions": [{"name": "器件边界", "box": [0, 0, 0.5, 1]},
                               {"name": "paper", "box": [0.5, 0, 1, 1]}]}
        files = compare(self.root / "src.png", self.root / "out.png", regions, self.root / "proof", metrics=True)
        data = json.loads(Path(files[-1]).read_text(encoding="utf-8"))
        self.assertEqual(data["canvas_px"], [20, 10])
        full, ink, paper = data["regions"]
        self.assertEqual(ink["name"], "器件边界")
        self.assertEqual(full["rgb_mae_0_255"], 1.5)
        self.assertEqual(full["nonwhite_mae_0_255"], 3)
        self.assertEqual(full["nonwhite_pixels"], 100)
        self.assertEqual(ink["box_px"], [0, 0, 10, 10])
        self.assertEqual(ink["rgb_mae_0_255"], 3)
        self.assertEqual(paper["rgb_mae_0_255"], 0)
        self.assertIsNone(paper["nonwhite_mae_0_255"])
        self.assertEqual(paper["reference_edges"], 0)
        self.assertEqual(paper["edge_recall_1px"], 0)

    def test_edge_recall_uses_one_native_pixel_and_preserves_geometry(self):
        for offset in (0, 1, 3):
            img = self.Image.new("RGB", (24, 18), "white")
            img.paste("black", (0, 0, 10 + offset, 18))
            img.save(self.root / f"step-{offset}.png")
        for offset, recall in ((0, 1), (1, 1), (3, 0)):
            with self.subTest(offset=offset):
                files = compare(self.root / "step-0.png", self.root / f"step-{offset}.png", {},
                                self.root / f"proof-{offset}", metrics=True)
                region = json.loads(Path(files[-1]).read_text(encoding="utf-8"))["regions"][0]
                self.assertEqual(region["reference_edges"], 18)
                self.assertEqual(region["edge_recall_1px"], recall)
                self.assertEqual(region["rgb_mae_0_255"], offset * 255 / 24)

    def test_equal_aspect_ratio_with_distinct_pixel_grids_is_rejected(self):
        src, out = self.root / "a.png", self.root / "b.png"
        self.Image.new("RGB", (20, 10), "white").save(src)
        self.Image.new("RGB", (40, 20), "white").save(out)
        with self.assertRaisesRegex(ValueError, "pixel dimensions"):
            compare(src, out, {}, self.root / "proof", overlay=True, metrics=True)
        self.assertFalse((self.root / "proof").exists())


if __name__ == "__main__":
    unittest.main()
