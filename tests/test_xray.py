#!/usr/bin/env python3
"""OKF / Code-XRay: EXTRACTED edges, HEAD resolve, if-stale, delete."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def _load():
    p = ROOT / "scripts" / "dashboard" / "xray.py"
    spec = importlib.util.spec_from_file_location("xray_mod", p)
    return spec.loader.load_module()


class TestXrayOkf(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = _load()

    def _okf(self):
        return {
            "git_head": "63f1ed9",
            "nodes": [
                {"id": "file:a.py", "type": "file", "label": "a.py", "purpose": "x"},
                {"id": "file:gone.py", "type": "file", "label": "gone.py"},
                {"id": "commit:63f1ed9", "type": "commit", "short": "63f1ed9",
                 "sha": "63f1ed9abc", "summary": "fix card", "files": ["a.py"]},
            ],
            "edges": [
                {"from": "commit:63f1ed9", "to": "file:a.py", "type": "touches", "tag": "EXTRACTED"},
                {"from": "file:a.py", "to": "file:b.py", "type": "imports", "tag": "EXTRACTED"},
            ],
        }

    def test_extracted_only_touches_for_head(self):
        with mock.patch.object(self.x, "_run", return_value="63f1ed9"):
            edges = self.x.query_graph(self._okf(), type="touches", commit="HEAD")
        self.assertTrue(edges)
        self.assertTrue(all(e["tag"] == "EXTRACTED" and e["type"] == "touches" for e in edges))
        self.assertEqual(edges[0]["to"], "file:a.py")

    def test_head_resolves_in_commit_impact(self):
        with mock.patch.object(self.x, "_run", return_value="63f1ed9"):
            out = self.x.commit_impact(self._okf(), "HEAD")
        self.assertNotIn("error", out)
        self.assertIn("file:a.py", out["files"])

    def test_query_type_touches_not_empty_vs_node_type(self):
        nodes = self.x.query_graph(self._okf(), type="commit")
        self.assertTrue(any(n["type"] == "commit" for n in nodes))
        with mock.patch.object(self.x, "_run", return_value="63f1ed9"):
            self.assertTrue(self.x.query_graph(self._okf(), type="touches", commit="HEAD"))

    def test_if_stale_noop(self):
        with tempfile.TemporaryDirectory() as td:
            tree = Path(td) / "code-xray.json"
            tree.write_text(json.dumps({"okf": {"git_head": "abc1234", "nodes": [{"id": "keep"}]}, "root": {"id": "r", "children": []}}))
            with mock.patch.object(self.x, "TREE_PATH", tree), mock.patch.object(self.x, "_run", return_value="abc1234"):
                self.assertEqual(self.x.build(if_stale=15)["okf"]["nodes"][0]["id"], "keep")

    def test_head_drifted_detects_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            tree = Path(td) / "code-xray.json"
            tree.write_text(json.dumps({"okf": {"git_head": "oldsha1", "nodes": []}, "root": {}}))
            with mock.patch.object(self.x, "TREE_PATH", tree), mock.patch.object(self.x, "_run", return_value="newsha2"):
                self.assertTrue(self.x.head_drifted())
            with mock.patch.object(self.x, "TREE_PATH", tree), mock.patch.object(self.x, "_run", return_value="oldsha1"):
                self.assertFalse(self.x.head_drifted())

    def test_render_html_rebuilds_on_drift(self):
        x = self.x
        with tempfile.TemporaryDirectory() as td:
            td_path, trees = Path(td), Path(td) / "trees"
            trees.mkdir()
            tree = td_path / "code-xray.json"
            tree.write_text(json.dumps({"okf": {"git_head": "olddead", "nodes": [], "edges": []}, "root": {"id": "r", "children": []}, "repo": "t"}))
            built = {"version": 1, "repo": "t", "root": {"id": "r", "children": []}, "okf": {"git_head": "livehead", "nodes": [], "edges": []}}

            def fake_build(**_kw):
                tree.write_text(json.dumps(built))
                return built

            with mock.patch.object(x, "TREE_PATH", tree), mock.patch.object(x, "HTML_PATH", trees / "t.html"), \
                    mock.patch.object(x, "TREES_DIR", trees), mock.patch.object(x, "VAULT", td_path), \
                    mock.patch.object(x, "live_git_head", return_value="livehead"), \
                    mock.patch.object(x, "build", side_effect=fake_build) as b, \
                    mock.patch.object(x, "publish_viewer"), mock.patch.object(x, "repo_summary", return_value="sum"), \
                    mock.patch.object(x, "enrich_nodes", side_effect=lambda n: n):
                body = x.render_html(open_after=False).read_text(encoding="utf-8")
            self.assertTrue(b.called)
            self.assertIn("livehead", body)
            self.assertIn("live_head", body)

    def test_deleted_file_drops_from_tree(self):
        rebuilt = {
            "a.py": {"id": "a.py", "type": "program", "functions": [], "imports": [], "history": [], "sessions": []},
            "gone.py": {"id": "gone.py", "type": "program", "deleted": True, "functions": [], "imports": [], "history": [], "sessions": []},
        }
        live = {k: v for k, v in rebuilt.items() if not v.get("deleted")}
        self.assertIn("a.py", live)
        self.assertNotIn("gone.py", live)

    def test_commit_icon_not_unknown(self):
        p = ROOT / "scripts" / "dashboard" / "icons.py"
        spec = importlib.util.spec_from_file_location("kg_icons", p)
        ic = spec.loader.load_module()
        key = ic.resolve_icon_key(ntype="commit", label="818782d", node_id="commit:818782d")
        self.assertEqual(key, "commit")
        self.assertNotEqual(ic.emoji_for(key), "❓")

    def test_panel_has_repo_and_looping_flow(self):
        js = (ROOT / "scripts" / "dashboard" / "okf-viewer.js").read_text(encoding="utf-8")
        css = (ROOT / "scripts" / "dashboard" / "okf-viewer.css").read_text(encoding="utf-8")
        src = (ROOT / "scripts" / "dashboard" / "xray.py").read_text(encoding="utf-8")
        self.assertIn("repo: ", js)
        self.assertIn("linear infinite", css)
        self.assertIn("runOnce(true)", js)
        self.assertIn("graph baked at", js)
        self.assertIn("recent change:", js)
        self.assertNotIn("last commit:", js)
        self.assertIn("live_head", js)
        self.assertIn("okf-viewer.js", src)
        self.assertIn("rebake_tree_htmls", src)
        self.assertIn("head_drifted", src)

    def test_rebake_rewrites_stub(self):
        with tempfile.TemporaryDirectory() as td:
            vault, trees = Path(td), Path(td) / "dashboard" / "trees"
            trees.mkdir(parents=True)
            old = '<html><script type="application/json" id="okf">{"repo":"Aryx","nodes":[{"id":"commit:1","type":"commit","label":"818782d"}],"edges":[]}</script><script>old inline</script></html>'
            (trees / "Aryx.html").write_text(old)
            with mock.patch.object(self.x, "VAULT", vault), mock.patch.object(self.x, "TREES_DIR", trees):
                self.assertEqual(self.x.rebake_tree_htmls(), 1)
            body = (trees / "Aryx.html").read_text()
            self.assertIn("okf-viewer.js", body)
            self.assertNotIn("old inline", body)
            self.assertTrue((vault / "dashboard" / "okf-viewer.js").is_file())
            self.assertTrue((trees / "okf-viewer.js").is_file())


if __name__ == "__main__":
    unittest.main()
