from __future__ import annotations

from pathlib import Path
from typing import Any

from .actions import ActionRunner, Tap
from .screenshot import capture_window_or_screen
from .snippets import Snippet, SnippetRegistry, Step
from .window import WindowInfo


class RoutineEngine:
    def __init__(
        self,
        *,
        registry: SnippetRegistry,
        runner: ActionRunner,
        root: Path,
        screenshot_path: Path,
        window: WindowInfo | None = None,
    ) -> None:
        self.registry = registry
        self.runner = runner
        self.root = root
        self.screenshot_path = screenshot_path
        self.window = window

    def run(self, *, start_id: str | None = None, cycles: int | None = 1) -> None:
        current_id = start_id or self.registry.start
        completed_cycles = 0

        while cycles is None or completed_cycles < cycles:
            snippet = self.registry.get(current_id)
            self.run_snippet(snippet)

            next_id = snippet.next_id
            if next_id is None:
                print(f"[stop] {snippet.id} has no next snippet")
                return

            if next_id == (start_id or self.registry.start):
                completed_cycles += 1
                print(f"[cycle] completed {completed_cycles}")

            current_id = next_id

    def run_snippet(self, snippet: Snippet) -> None:
        print(f"\n== {snippet.id}: {snippet.name} ==")
        if snippet.description:
            print(snippet.description)

        detect = snippet.detect
        if detect:
            template = detect.get("template")
            threshold = detect.get("threshold")
            required = detect.get("required", False)
            print(f"[detect] template={template} threshold={threshold} required={required}")

        for step in snippet.steps:
            self.run_step(step)

    def run_step(self, step: Step) -> None:
        label = step.label or step.type
        if not step.enabled:
            print(f"[skip] {label}")
            return

        match step.type:
            case "note":
                print(f"[note] {label}")
            case "tap":
                self._tap(step)
            case "wait":
                seconds = float(step.data.get("seconds", 0))
                self.runner.wait(seconds, label=label)
            case "capture":
                self._capture(step)
            case "wait_for_template":
                self._wait_for_template(step)
            case _:
                raise ValueError(f"unsupported step type: {step.type}")

    def _tap(self, step: Step) -> None:
        x = step.data.get("x")
        y = step.data.get("y")
        if x is None or y is None:
            print(f"[skip] {step.label}: x/y is not configured")
            return

        tap = Tap(
            x=int(x),
            y=int(y),
            label=step.label,
            coordinate_space=str(step.data.get("coordinate_space", "window")),
        )
        self.runner.tap(tap)

    def _capture(self, step: Step) -> None:
        path_value = step.data.get("path")
        path = self._resolve_path(path_value) if path_value else self.screenshot_path
        if self.runner.dry_run:
            print(f"[dry-run] capture {path}")
            return

        saved = capture_window_or_screen(path, window=self.window)
        print(f"[capture] {saved}")

    def _wait_for_template(self, step: Step) -> None:
        template = step.data.get("template")
        threshold = step.data.get("threshold")
        timeout = step.data.get("timeout_seconds")
        print(
            "[todo] wait_for_template "
            f"label={step.label} template={template} threshold={threshold} timeout={timeout}"
        )

    def _resolve_path(self, value: Any) -> Path:
        path = Path(str(value))
        if path.is_absolute():
            return path
        return self.root / path
