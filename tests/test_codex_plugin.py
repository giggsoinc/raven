"""Codex plugin packaging and host-install regressions."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_codex_manifest_declares_skills_and_valid_interface():
    manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    assert manifest["name"] == "raven"
    assert manifest["skills"] == "./skills/"
    assert manifest["interface"]["displayName"] == "Raven"
    assert manifest["interface"]["shortDescription"]
    assert manifest["interface"]["longDescription"]
    assert manifest["interface"]["developerName"]
    assert manifest["interface"]["category"]


def test_direct_plugin_source_has_codex_manifest():
    root_manifest = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
    plugin_manifest = json.loads((ROOT / "plugin/.codex-plugin/plugin.json").read_text())
    assert plugin_manifest == root_manifest


def test_package_includes_codex_manifest():
    script = (ROOT / "plugin/make-plugin.sh").read_text()
    assert 'mkdir -p "$TMP_DIR/.claude-plugin" "$TMP_DIR/.codex-plugin"' in script
    assert 'cp "$REPO_DIR/.codex-plugin/plugin.json" "$TMP_DIR/.codex-plugin/plugin.json"' in script


def test_host_installer_provisions_codex_skills():
    script = (ROOT / "plugin/install-host.sh").read_text()
    assert 'mkdir -p "$TARGET/.codex/skills"' in script
    assert 'cp -R "$ROOT/skills/." "$TARGET/.codex/skills/"' in script
