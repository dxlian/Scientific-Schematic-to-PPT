"""Tests for two failure modes reproduced by the paper-figure trials."""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_pptx import audit
from build_pptx import build
import matplotlib.pyplot as plt
import numpy as np
from plot_data import draw_panel


class RealFigureTests(unittest.TestCase):
    def test_log_axis_requires_positive_drawn_lower_error_endpoint(self):
        rows = [{"x": "1", "y": "5", "lower": "1", "upper": "2"},
                {"x": "2", "y": "3", "lower": "3", "upper": "1"}]
        for error in ("lower", {"lower": "lower", "upper": "upper"}):
            for magnitude in ("3", "4"):
                with self.subTest(error=error, magnitude=magnitude):
                    rows[1]["lower"] = magnitude
                    series = {"id": "trial", "x": "x", "y": "y", "yerr": error,
                              "error_definition": "Supplied uncertainty"}
                    panel = {"xlabel": "X", "ylabel": "Y", "yscale": "log", "series": [series]}
                    fig, ax = plt.subplots()
                    self.addCleanup(plt.close, fig)
                    with self.assertRaisesRegex(ValueError, "Series 'trial', CSV row 3: lower error endpoint"):
                        draw_panel(ax, panel, rows)

    def test_log_error_domain_ignores_missing_centres_and_incomplete_bars(self):
        rows = [{"x": "1", "y": "5", "lower": "1", "upper": "2"},
                {"x": "", "y": "3", "lower": "4", "upper": "1"},
                {"x": "2", "y": "", "lower": "7", "upper": "1"},
                {"x": "3", "y": "2", "lower": "4", "upper": ""}]
        series = {"id": "trial", "x": "x", "y": "y", "yerr": {"lower": "lower", "upper": "upper"},
                  "error_definition": "Supplied uncertainty"}
        panel = {"xlabel": "X", "ylabel": "Y", "yscale": "log", "series": [series]}
        fig, ax = plt.subplots()
        self.addCleanup(plt.close, fig)
        _, report, _ = draw_panel(ax, panel, rows)
        self.assertEqual(report["trial"]["missing_xy"], 2)
        self.assertEqual(report["trial"]["missing_error_at_valid_xy"], 1)

    def test_asymmetric_errors_keep_bounds_and_inset(self):
        rows = [{"x":"1","y":"3","dn":"0.2","up":"0.6"},
                {"x":"2","y":"5","dn":"","up":"0.3"},
                {"x":"3","y":"4","dn":"0.8","up":"0.1"}]
        series = {"id":"observed","kind":"scatter","x":"x","y":"y","yerr":{"lower":"dn","upper":"up"},
                  "error_definition":"Reported lower and upper parameter uncertainty"}
        panel = {"xlabel":"Period","ylabel":"Radius","series":[series],"annotations":[
                 {"kind":"inset","box":[.15,.5,.3,.25],"xlim":[.5,3.5],"ylim":[1,6]}]}
        fig, ax = plt.subplots()
        self.addCleanup(plt.close,fig)
        _, report, _ = draw_panel(ax,panel,rows)
        self.assertEqual(report["observed"]["missing_error_at_valid_xy"],1)
        self.assertEqual(len(ax.lines[0].get_xdata()),3)
        for layer in (ax,ax.child_axes[0]):
            bars=layer.collections[0].get_segments()
            np.testing.assert_allclose(bars[0], [[1,2.8],[1,3.6]])
            self.assertEqual(len(bars[1]),0)
            np.testing.assert_allclose(bars[2], [[3,3.2],[3,4.1]])

    def test_line_width_warning_from_saved_file(self):
        try:
            from matplotlib.font_manager import findfont
            import PIL
            findfont("Times New Roman",fallback_to_default=False)
        except (ImportError,ValueError):self.skipTest("Requires local Times New Roman and Pillow")
        scene={"version":1,"width_mm":80,"height_mm":50,"elements":[
                {"id":"narrow","type":"text","x":1,"y":2,"w":10,"h":8,"text":"Resonator interface","font_pt":12},
                {"id":"wide","type":"text","x":1,"y":14,"w":72,"h":18,"text":"Resonator\ninterface","font_pt":12}]}
        with TemporaryDirectory() as tmp:
            target=Path(tmp)/"case.pptx";build(scene,target)
            result=audit(target,native_only=True,check_text_width=True)
        checks={r["shape"]:r["status"] for r in result["text_width_checks"]}
        self.assertEqual(checks["SCHEM_narrow"],"review_wrap")
        self.assertEqual(checks["SCHEM_wide"],"fits_width")
        self.assertTrue(result["passed"])


if __name__=="__main__":unittest.main()
