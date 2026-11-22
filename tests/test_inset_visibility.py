"""Inset coverage must reflect observed scatter points and physically drawn line segments."""
import sys
import unittest
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from plot_data import draw_panel


class InsetVisibility(unittest.TestCase):
    def exercise(self, x, y, kind="line", placement="fixed"):
        fig, ax = plt.subplots()
        self.addCleanup(plt.close, fig)
        rows = [{"x": str(a), "y": str(b)} for a,b in zip(x,y)]
        spec = {"xlabel":"x", "ylabel":"y", "xlim":[0,1], "ylim":[0,1],
                "series":[{"id":"s","x":"x","y":"y","kind":kind}],
                "annotations":[{"kind":"inset","box":[.4,.4,.2,.2], "xlim":[0,.4],
                                "ylim":[0,.4],"placement":placement}]}
        if placement == "auto":
            spec["annotations"][0]["candidates"] = [[.05,.75,.2,.2]]
        _, _, features = draw_panel(ax, spec, rows)
        fig.canvas.draw()
        result = features[0]["placement_audit"]
        shown = (ax.figure.transFigure - ax.transAxes).transform_bbox(ax.child_axes[0].get_position())
        np.testing.assert_allclose(shown.bounds, result["actual_box"], atol=1e-8)
        return result

    def test_fixed_crossing_has_no_vertex_inside(self):
        f = self.exercise([0,1],[0,1])
        self.assertTrue(f["review_occlusion"])
        self.assertEqual((f["covered_points"], f["intersecting_segments"]), (0,1))
        np.testing.assert_allclose(f["actual_box"], [.4,.4,.2,.2])

    def test_auto_relocates_and_keeps_preferred_box_evidence(self):
        f = self.exercise([0,.5,1],[0,.5,1],placement="auto")
        self.assertEqual(f["initial_covered_points"],1)
        self.assertEqual(f["initial_intersecting_segments"],2)
        self.assertFalse(f["review_occlusion"])
        np.testing.assert_allclose(f["actual_box"], [.05,.75,.2,.2])

    def test_missing_points_and_scatter_are_not_connected(self):
        for kind,x,y in [("line",[0,.5,1],[0,float("nan"),1]),("scatter",[0,1],[0,1])]:
            with self.subTest(kind=kind):
                self.assertFalse(self.exercise(x,y,kind)["review_occlusion"])
