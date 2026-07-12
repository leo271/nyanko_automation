from __future__ import annotations

from datetime import datetime
from pathlib import Path
from shutil import copy2
from typing import Any

from .actions import ActionRunner, Tap
from .screenshot import capture_window_or_screen
from .snippets import RoutineDefinition, Snippet, SnippetRegistry, Step, Transition
from .window import WindowInfo


class RoutineEngine:
    def __init__(
        self,
        *,
        registry: SnippetRegistry,
        routine: RoutineDefinition,
        runner: ActionRunner,
        root: Path,
        screenshot_path: Path,
        window: WindowInfo | None = None,
        debug_screenshots: bool = False,
    ) -> None:
        self.registry = registry
        self.routine = routine
        self.runner = runner
        self.root = root
        self.screenshot_path = screenshot_path
        self.window = window
        self.debug_screenshots = debug_screenshots
        self.snippet_results: dict[str, bool | None] = {}

    def run(self, *, start_id: str | None = None, cycles: int | None = 1) -> None:
        current_id = start_id or self.routine.start_id
        completed_cycles = 0

        print(f"[routine] {self.routine.id}: {self.routine.name}")
        if self.routine.description:
            print(self.routine.description)

        while cycles is None or completed_cycles < cycles:
            snippet = self.registry.get(current_id)
            self.run_snippet(snippet)

            next_id = self.next_after(snippet.id)
            if next_id is None:
                print(f"[stop] {self.routine.id}.{snippet.id} has no next snippet")
                return

            if next_id == (start_id or self.routine.start_id):
                completed_cycles += 1
                print(f"[cycle] completed {completed_cycles}")

            current_id = next_id

    def save_debug_snapshot(self, label: str) -> None:
        if not self.debug_screenshots:
            return

        screenshot_path = self.root / "assets" / "screenshots" / "_runtime_interrupt.png"
        capture_window_or_screen(screenshot_path, window=self.window)
        self._save_debug_capture(label, screenshot_path)

    def next_after(self, snippet_id: str) -> str | None:
        transitions = self.routine.transitions_after(snippet_id)
        if not transitions:
            return None

        fallback: Transition | None = None
        for transition in transitions:
            if not transition.is_conditional:
                fallback = transition
                continue

            if self._transition_matches(snippet_id, transition):
                return transition.next_id

        if fallback is not None:
            return fallback.next_id

        return None

    def run_snippet(self, snippet: Snippet) -> bool | None:
        print(f"\n== {snippet.id}: {snippet.name} ==")
        if snippet.description:
            print(snippet.description)

        detect = snippet.detect
        if detect:
            template = detect.get("template")
            color_probe = detect.get("color_probe")
            threshold = detect.get("threshold")
            required = detect.get("required", False)
            if color_probe:
                print(f"[detect] color_probe={color_probe} required={required}")
            elif template:
                print(f"[detect] template={template} threshold={threshold} required={required}")

        if snippet.kind == "condition":
            result = self._evaluate_condition_snippet(snippet)
            self.snippet_results[snippet.id] = result
            print(f"[condition] {snippet.id} -> {result}")
            return result

        for step in snippet.steps:
            self.run_step(step)
        self.snippet_results[snippet.id] = None
        return None

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
            duration_seconds=float(step.data.get("duration_seconds", 0.0)),
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

    def _transition_matches(self, snippet_id: str, transition: Transition) -> bool:
        if transition.if_result is None:
            return False

        result = self.snippet_results.get(snippet_id)
        matched = result is transition.if_result
        label = f" ({transition.label})" if transition.label else ""
        print(
            f"[transition] result={result} expected={transition.if_result} "
            f"matched={matched}{label}"
        )
        return matched

    def _evaluate_condition_snippet(self, snippet: Snippet) -> bool:
        color_probe = snippet.detect.get("color_probe")
        if self.runner.dry_run:
            target = (
                color_probe
                or snippet.detect.get("templates")
                or snippet.detect.get("template")
            )
            print(f"[dry-run] condition check {target} -> false")
            return False

        if color_probe:
            return self._evaluate_color_probe(color_probe, snippet.id)

        templates = snippet.detect.get("templates")
        threshold = float(snippet.detect.get("threshold", 0.88))
        if templates:
            results = []
            for template_value in templates:
                result = self._match_template(self._resolve_path(str(template_value)))
                results.append(result)
                score, scale, location, size = result
                print(
                    f"[condition] template={template_value} score={score:.3f} "
                    f"threshold={threshold:.3f} scale={scale:.2f} "
                    f"location={location[0]},{location[1]} size={size[0]}x{size[1]}"
                )
            matched = all(result[0] >= threshold for result in results)
            print(f"[condition] templates matched={matched}")
            if not matched:
                self._save_debug_capture(
                    snippet.id, self.root / "assets/screenshots/_runtime_match.png"
                )
            return matched

        template = snippet.detect.get("template")
        if not template:
            raise ValueError(
                f"condition snippet requires detect.template, detect.templates, "
                f"or detect.color_probe: {snippet.id}"
            )

        score, scale, location, size = self._match_template(self._resolve_path(template))
        matched = score >= threshold
        print(
            f"[condition] template={template} score={score:.3f} "
            f"threshold={threshold:.3f} matched={matched} "
            f"scale={scale:.2f} location={location[0]},{location[1]} "
            f"size={size[0]}x{size[1]}"
        )
        if not matched:
            self._save_debug_capture(
                snippet.id, self.root / "assets/screenshots/_runtime_match.png"
            )
        return matched

    def _save_debug_capture(self, snippet_id: str, source: Path) -> None:
        if not self.debug_screenshots:
            return

        if not source.exists():
            return

        debug_dir = self.root / "assets" / "screenshots" / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        target = debug_dir / f"{timestamp}_{snippet_id}_false.png"
        copy2(source, target)
        print(f"[debug] saved {target}")

    def _match_template(
        self, template_path: Path
    ) -> tuple[float, float, tuple[int, int], tuple[int, int]]:
        import cv2

        screenshot_path = self.root / "assets" / "screenshots" / "_runtime_match.png"
        capture_window_or_screen(screenshot_path, window=self.window)

        image = cv2.imread(str(screenshot_path), cv2.IMREAD_GRAYSCALE)
        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise RuntimeError(f"failed to read screenshot: {screenshot_path}")
        if template is None:
            raise RuntimeError(f"failed to read template: {template_path}")

        image_height, image_width = image.shape[:2]
        template_height, template_width = template.shape[:2]
        best_value = 0.0
        best_scale = 1.0
        best_location = (0, 0)
        best_size = (template_width, template_height)
        scales = (0.45, 0.48, 0.49, 0.50, 0.51, 0.52, 0.53, 0.54, 0.55, 0.60, 0.65, 0.70, 0.80, 1.0)
        for scale in scales:
            width = int(template_width * scale)
            height = int(template_height * scale)
            if width < 1 or height < 1 or width > image_width or height > image_height:
                continue

            resized = cv2.resize(template, (width, height), interpolation=cv2.INTER_AREA)
            result = cv2.matchTemplate(image, resized, cv2.TM_CCOEFF_NORMED)
            _, max_value, _, max_location = cv2.minMaxLoc(result)
            if float(max_value) > best_value:
                best_value = float(max_value)
                best_scale = scale
                best_location = (int(max_location[0]), int(max_location[1]))
                best_size = (width, height)

        return best_value, best_scale, best_location, best_size

    def _evaluate_color_probe(self, probe: dict[str, Any], snippet_id: str) -> bool:
        from PIL import Image

        screenshot_path = self.root / "assets" / "screenshots" / "_runtime_condition.png"
        capture_window_or_screen(screenshot_path, window=self.window)

        region = dict(probe["region"])
        left = int(region["x"])
        top = int(region["y"])
        right = left + int(region["width"])
        bottom = top + int(region["height"])

        image = Image.open(screenshot_path).convert("RGB").crop((left, top, right, bottom))
        pixels = list(image.getdata())
        if not pixels:
            return False

        mode = str(probe.get("mode", "white_ratio"))
        if mode == "white_ratio":
            min_rgb = int(probe.get("min_rgb", 170))
            max_delta = int(probe.get("max_delta", 80))
            count = sum(
                1
                for red, green, blue in pixels
                if red > min_rgb
                and green > min_rgb
                and blue > min_rgb
                and max(red, green, blue) - min(red, green, blue) < max_delta
            )
        elif mode == "green_ratio":
            count = sum(
                1 for red, green, blue in pixels if green > 140 and red < 120 and blue < 120
            )
        else:
            raise ValueError(f"unsupported color probe mode: {mode}")

        ratio = count / len(pixels)
        min_ratio = float(probe.get("min_ratio", 0.05))
        matched = ratio >= min_ratio
        print(
            f"[condition] color_probe mode={mode} ratio={ratio:.4f} "
            f"threshold={min_ratio:.4f} matched={matched}"
        )
        if not matched:
            self._save_debug_capture(snippet_id, screenshot_path)
        return matched
