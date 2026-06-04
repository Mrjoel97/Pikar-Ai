from __future__ import annotations

import app.agent as executive_module


def test_manifest_mode_keeps_manifest_sub_agent_graph(monkeypatch) -> None:
    monkeypatch.setattr(executive_module, "_USE_MANIFESTS", True)

    assert executive_module._default_sub_agents_for_mode() is None
