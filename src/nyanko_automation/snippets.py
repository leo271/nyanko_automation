from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Step:
    type: str
    label: str
    enabled: bool
    data: dict[str, Any]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Step:
        step_type = str(raw.get("type", "")).strip()
        if not step_type:
            raise ValueError("step.type is required")

        return cls(
            type=step_type,
            label=str(raw.get("label", "")),
            enabled=bool(raw.get("enabled", True)),
            data=dict(raw),
        )


@dataclass(frozen=True)
class Snippet:
    id: str
    name: str
    description: str
    kind: str
    detect: dict[str, Any]
    steps: list[Step]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Snippet:
        snippet_id = str(raw.get("id", "")).strip()
        if not snippet_id:
            raise ValueError("snippet.id is required")

        steps = [Step.from_dict(step) for step in raw.get("steps", [])]
        return cls(
            id=snippet_id,
            name=str(raw.get("name", snippet_id)),
            description=str(raw.get("description", "")),
            kind=str(raw.get("kind", "action")),
            detect=dict(raw.get("detect", {})),
            steps=steps,
        )


@dataclass(frozen=True)
class Transition:
    next_id: str | None
    if_result: bool | None = None
    label: str = ""

    @classmethod
    def from_raw(cls, raw: Any) -> Transition:
        if raw is None or isinstance(raw, str):
            return cls(next_id=raw)

        data = dict(raw)
        next_value = data.get("next")
        return cls(
            next_id=str(next_value) if next_value is not None else None,
            if_result=data.get("if_result"),
            label=str(data.get("label", "")),
        )

    @property
    def is_conditional(self) -> bool:
        return self.if_result is not None


@dataclass(frozen=True)
class RoutineDefinition:
    id: str
    name: str
    description: str
    start_id: str
    transitions: dict[str, list[Transition]]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RoutineDefinition:
        routine_id = str(raw.get("id", "")).strip()
        if not routine_id:
            raise ValueError("routine.id is required")

        start_id = str(raw.get("start", "")).strip()
        if not start_id:
            raise ValueError(f"{routine_id}.start is required")

        transitions = {}
        for source, target in dict(raw.get("transitions", {})).items():
            raw_targets = target if isinstance(target, list) else [target]
            transitions[str(source)] = [Transition.from_raw(item) for item in raw_targets]

        return cls(
            id=routine_id,
            name=str(raw.get("name", routine_id)),
            description=str(raw.get("description", "")),
            start_id=start_id,
            transitions=transitions,
        )

    def transitions_after(self, snippet_id: str) -> list[Transition]:
        return self.transitions.get(snippet_id, [])

    def preview_next_after(self, snippet_id: str) -> str | None:
        transitions = self.transitions_after(snippet_id)
        if not transitions:
            return None

        for transition in transitions:
            if not transition.is_conditional:
                return transition.next_id

        return transitions[0].next_id


class SnippetRegistry:
    def __init__(
        self,
        *,
        default_routine: str,
        routines: list[RoutineDefinition],
        snippets: list[Snippet],
    ) -> None:
        self.default_routine = default_routine
        self._routines = {routine.id: routine for routine in routines}
        self._routine_order = [routine.id for routine in routines]
        self._snippets = {snippet.id: snippet for snippet in snippets}
        self._order = [snippet.id for snippet in snippets]
        self.validate()

    @classmethod
    def from_path(cls, path: Path) -> SnippetRegistry:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        default_routine = str(raw.get("default_routine", "")).strip()
        routines = [RoutineDefinition.from_dict(item) for item in raw.get("routines", [])]
        snippets = [Snippet.from_dict(item) for item in raw.get("snippets", [])]
        return cls(default_routine=default_routine, routines=routines, snippets=snippets)

    def all(self) -> list[Snippet]:
        return [self._snippets[snippet_id] for snippet_id in self._order]

    def routines(self) -> list[RoutineDefinition]:
        return [self._routines[routine_id] for routine_id in self._routine_order]

    def get(self, snippet_id: str) -> Snippet:
        try:
            return self._snippets[snippet_id]
        except KeyError as exc:
            raise KeyError(f"unknown snippet: {snippet_id}") from exc

    def get_routine(self, routine_id: str | None = None) -> RoutineDefinition:
        target_id = routine_id or self.default_routine
        try:
            return self._routines[target_id]
        except KeyError as exc:
            raise KeyError(f"unknown routine: {target_id}") from exc

    def validate(self) -> None:
        if not self.default_routine:
            raise ValueError("default_routine is required")
        if self.default_routine not in self._routines:
            raise ValueError(f"default routine is not defined: {self.default_routine}")

        for routine in self._routines.values():
            if routine.start_id not in self._snippets:
                raise ValueError(
                    f"{routine.id}.start points to unknown snippet: {routine.start_id}"
                )

            for source_id, transitions in routine.transitions.items():
                if source_id not in self._snippets:
                    raise ValueError(
                        f"{routine.id}.transitions has unknown snippet: {source_id}"
                    )
                for transition in transitions:
                    target_id = transition.next_id
                    if target_id is not None and target_id not in self._snippets:
                        raise ValueError(
                            f"{routine.id}.transitions.{source_id} points to unknown snippet: "
                            f"{target_id}"
                        )

    def preview_cycle(
        self,
        *,
        routine_id: str | None = None,
        start_id: str | None = None,
        limit: int = 32,
    ) -> list[str]:
        routine = self.get_routine(routine_id)
        current_id = start_id or routine.start_id
        seen: list[str] = []

        for _ in range(limit):
            seen.append(current_id)
            next_id = routine.preview_next_after(current_id)
            if next_id is None:
                break
            current_id = next_id
            if current_id == (start_id or routine.start_id):
                seen.append(current_id)
                break

        return seen
