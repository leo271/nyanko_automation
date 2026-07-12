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
    detect: dict[str, Any]
    steps: list[Step]
    next_id: str | None

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
            detect=dict(raw.get("detect", {})),
            steps=steps,
            next_id=raw.get("next"),
        )


class SnippetRegistry:
    def __init__(self, *, start: str, snippets: list[Snippet]) -> None:
        self.start = start
        self._snippets = {snippet.id: snippet for snippet in snippets}
        self._order = [snippet.id for snippet in snippets]
        self.validate()

    @classmethod
    def from_path(cls, path: Path) -> SnippetRegistry:
        with path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        start = str(raw.get("start", "")).strip()
        snippets = [Snippet.from_dict(item) for item in raw.get("snippets", [])]
        return cls(start=start, snippets=snippets)

    def all(self) -> list[Snippet]:
        return [self._snippets[snippet_id] for snippet_id in self._order]

    def get(self, snippet_id: str) -> Snippet:
        try:
            return self._snippets[snippet_id]
        except KeyError as exc:
            raise KeyError(f"unknown snippet: {snippet_id}") from exc

    def validate(self) -> None:
        if not self.start:
            raise ValueError("start is required")
        if self.start not in self._snippets:
            raise ValueError(f"start snippet is not defined: {self.start}")

        for snippet in self._snippets.values():
            if snippet.next_id is not None and snippet.next_id not in self._snippets:
                raise ValueError(f"{snippet.id}.next points to unknown snippet: {snippet.next_id}")

    def preview_cycle(self, *, start_id: str | None = None, limit: int = 12) -> list[str]:
        current_id = start_id or self.start
        seen: list[str] = []

        for _ in range(limit):
            seen.append(current_id)
            next_id = self.get(current_id).next_id
            if next_id is None:
                break
            current_id = next_id
            if current_id == (start_id or self.start):
                seen.append(current_id)
                break

        return seen
