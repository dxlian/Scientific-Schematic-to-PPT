"""Regression checks for scientific errors that can hide in a visually plausible plot."""
import sys
import json
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import numpy as np
import matplotlib.pyplot as plt
from plot_data import draw_panel, render
from precision_annotations import coordinate_label, numeric_anchor, threshold_crossings


class AnnotationTests(unittest.TestCase):
    def test_coordinate_placeholders_preserve_math_groups(self):
        template = r"峰值 $\frac{x}{y}+\mathrm{Max}_{x}$，{y:.1f}，$t={x:.1f}$"
        expected = r"峰值 $\frac{x}{y}+\mathrm{Max}_{x}$，8.5，$t=2.3$"
        self.assertEqual(coordinate_label(template, 2.3, 8.5), expected)
        self.assertEqual(coordinate_label(r"\$ {x} {{raw}}", 1, 2), r"\$ 1 {raw}")

    def test_mixed_math_chinese_survives_pdf(self):
        try:
            import fitz
            from matplotlib.font_manager import findfont
            for name in ("Times New Roman", "SimSun"):
                findfont(name, fallback_to_default=False)
        except (ImportError, ValueError):
            self.skipTest("PDF/font fixture requires PyMuPDF, Times New Roman and SimSun")
        spec = {"data": "data.csv", "width_mm": 130, "height_mm": 80,
                "panels": [{"xlabel": r"时间 $t$ (s)", "ylabel": r"应力 $\sigma_{\mathrm{eff}}$",
                            "legend": True, "series": [{"id": "s", "x": "x", "y": "y",
                                                         "label": r"载荷 $\frac{x}{y}$"}],
                            "annotations": [{"kind": "peak", "series": "s",
                                             "label": r"峰值 $\frac{x}{y}$ = {y:.1f}"}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.csv").write_text("x,y\n0,1\n1,3\n2,2\n", encoding="utf-8")
            source = root / "spec.json"
            source.write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
            state = render(source, root / "out")
            self.assertEqual(state["panels"][0]["annotations"][0]["text"], r"峰值 $\frac{x}{y}$ = 3.0")
            with fitz.open(root / "out" / "figure.pdf") as pdf:
                page = pdf[0]
                for text in ["时间", "应力", "载荷", "峰值", "σ", "3.0"]:
                    self.assertIn(text, page.get_text())
                cjk_spans = [span for block in page.get_text("dict")["blocks"] if "lines" in block
                             for line in block["lines"] for span in line["spans"]
                             if any(char in span["text"] for char in "时间应力载荷峰值")]
                self.assertTrue(cjk_spans and all("SimSun" in span["font"] for span in cjk_spans))
                embedded = [name for xref, _, _, name, *_ in page.get_fonts(full=True)
                            if pdf.extract_font(xref)[3]]
                for family in ["SimSun", "TimesNewRoman"]:
                    self.assertTrue(any(family in name for name in embedded))

    def test_gaps_and_plateaus(self):
        x = np.arange(7, dtype=float)
        y = np.array([0, np.nan, 2, 1, 1, 0, 2])
        self.assertEqual(threshold_crossings(x, y, 1), [3, 5.5])
        with self.assertRaisesRegex(ValueError, "2 candidates"):
            numeric_anchor(x, y, {"kind":"threshold", "value":1})
        self.assertEqual(numeric_anchor(x, y, {"kind":"threshold", "value":1, "occurrence":2}), (5.5, 1))

    def test_log_display_matches_physical_threshold_and_inset_errors(self):
        fig, ax = plt.subplots()
        self.addCleanup(plt.close, fig)
        rows = [{"x":"1","y":"1","sd":".1"}, {"x":"100","y":"11","sd":".2"}]
        panel = {"xlabel":"x","ylabel":"y","xscale":"log",
                 "series":[{"id":"a","x":"x","y":"y","yerr":"sd","error_definition":"SD","marker":"o"}],
                 "annotations":[{"kind":"threshold","series":"a","value":6},
                     {"kind":"inset","box":[.1,.5,.4,.4],"xlim":[1.5,90],"ylim":[1,12]}]}
        labels, _, _ = draw_panel(ax, panel, rows)
        self.assertEqual(labels[0][0], (50.5, 6))
        fig.canvas.draw()
        line = ax.lines[0]
        pixels = ax.transData.transform(line.get_xydata())
        target_x, target_y = ax.transData.transform(labels[0][0])
        self.assertLess(abs(float(np.interp(target_x, pixels[:,0], pixels[:,1])) - target_y), .1)
        self.assertEqual(len(line.get_markevery()), len(rows))
        inset, = ax.child_axes
        self.assertEqual(inset.get_xscale(), "log")
        self.assertEqual(len(inset.collections), len(ax.collections))
        self.assertTrue(np.array_equal(inset.lines[0].get_xydata(), line.get_xydata()))

    def test_model_and_inflection(self):
        x = np.arange(-3, 4, dtype=float)
        self.assertEqual(numeric_anchor(x, x**3, {"kind":"inflection"}), (0,0))
        with self.assertRaisesRegex(ValueError, "No observed"):
            numeric_anchor(x, x**2, {"kind":"inflection"})
        fig, ax = plt.subplots()
        self.addCleanup(plt.close, fig)
        rows = [{"x":str(v),"y":str(2*v+1)} for v in x]
        panel = {"xlabel":"x","ylabel":"y","series":[{"id":"a","x":"x","y":"y"}],
                 "annotations":[{"kind":"linear_fit","series":"a","bounds":[0,3]}]}
        _, _, features = draw_panel(ax, panel, rows)
        self.assertEqual(features[0]["n"], 4)
        self.assertAlmostEqual(features[0]["slope"], 2)
        self.assertAlmostEqual(features[0]["intercept"], 1)
        self.assertAlmostEqual(features[0]["r2"], 1)


if __name__ == "__main__":
    unittest.main()
