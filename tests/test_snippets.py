from __future__ import annotations

from pathlib import Path

from nyanko_automation.snippets import SnippetRegistry

ROOT = Path(__file__).resolve().parents[1]


def test_default_snippet_cycle() -> None:
    registry = SnippetRegistry.from_path(ROOT / "config" / "snippets.json")

    assert registry.default_routine == "packman"
    assert registry.preview_cycle(routine_id="packman") == [
        "detect_stamina_recover_available",
        "tap_battle_start",
        "wait_battle_start",
        "wait_initial_money",
        "deploy_unit_slot_4",
        "wait_battle_progress",
        "detect_drop_reward",
        "detect_extra_stage",
        "return_to_map",
        "wait_after_map_return",
        "detect_stamina_recover_available",
    ]


def test_packman_routine_is_registered() -> None:
    registry = SnippetRegistry.from_path(ROOT / "config" / "snippets.json")
    routine = registry.get_routine("packman")

    assert routine.name == "パックマン周回"
    assert routine.start_id == "detect_stamina_recover_available"


def test_drop_reward_detection_loops_before_result() -> None:
    registry = SnippetRegistry.from_path(ROOT / "config" / "snippets.json")
    routine = registry.get_routine("packman")

    transitions = routine.transitions["detect_drop_reward"]
    assert transitions[0].if_result is True
    assert transitions[0].next_id == "dismiss_drop_reward"
    assert transitions[1].next_id == "detect_extra_stage"
    assert routine.transitions["wait_after_drop_reward"][0].next_id == "detect_drop_reward"


def test_stamina_recovery_transition() -> None:
    registry = SnippetRegistry.from_path(ROOT / "config" / "snippets.json")
    routine = registry.get_routine("packman")
    transitions = routine.transitions["detect_stamina_recover_available"]

    assert transitions[0].if_result is True
    assert transitions[0].next_id == "tap_stamina_recover_button"
    assert transitions[1].next_id == "tap_battle_start"


def test_extra_stage_detection_transition() -> None:
    registry = SnippetRegistry.from_path(ROOT / "config" / "snippets.json")
    routine = registry.get_routine("packman")
    transitions = routine.transitions["detect_extra_stage"]

    assert transitions[0].if_result is True
    assert transitions[0].next_id == "accept_extra_stage"
    assert transitions[1].next_id == "return_to_map"
