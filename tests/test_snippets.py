from __future__ import annotations

from pathlib import Path

from nyanko_automation.snippets import SnippetRegistry

ROOT = Path(__file__).resolve().parents[1]


def test_default_snippet_cycle() -> None:
    registry = SnippetRegistry.from_path(ROOT / "config" / "snippets.json")

    assert registry.preview_cycle() == [
        "check_energy",
        "start_battle",
        "deploy_units",
        "finish_battle",
        "check_energy",
    ]


def test_all_snippets_have_next_transitions() -> None:
    registry = SnippetRegistry.from_path(ROOT / "config" / "snippets.json")

    assert all(snippet.next_id for snippet in registry.all())
