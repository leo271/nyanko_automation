from __future__ import annotations

from dataclasses import dataclass
from time import sleep

from .window import WindowInfo


@dataclass(frozen=True)
class Tap:
    x: int
    y: int
    label: str = ""
    coordinate_space: str = "window"
    duration_seconds: float = 0.0


class ActionRunner:
    def __init__(
        self,
        *,
        dry_run: bool = True,
        pause_seconds: float = 0.15,
        window: WindowInfo | None = None,
    ) -> None:
        self.dry_run = dry_run
        self.pause_seconds = pause_seconds
        self.window = window

    def tap(self, tap: Tap) -> None:
        x, y = self._resolve_coordinates(tap)
        if self.dry_run:
            name = f" ({tap.label})" if tap.label else ""
            print(f"[dry-run] tap {x},{y}{name}")
            return

        import pyautogui

        name = f" ({tap.label})" if tap.label else ""
        print(f"[live] tap {x},{y}{name}")
        pyautogui.click(x, y, duration=max(0.0, self._duration(tap)))
        sleep(self.pause_seconds)

    def move(self, tap: Tap) -> None:
        x, y = self._resolve_coordinates(tap)
        if self.dry_run:
            name = f" ({tap.label})" if tap.label else ""
            print(f"[dry-run] move {x},{y}{name}")
            return

        import pyautogui

        name = f" ({tap.label})" if tap.label else ""
        print(f"[live] move {x},{y}{name}")
        pyautogui.moveTo(x, y, duration=0.1)

    @staticmethod
    def _duration(tap: Tap) -> float:
        return tap.duration_seconds

    def wait(self, seconds: float, *, label: str = "") -> None:
        name = f" ({label})" if label else ""
        if self.dry_run:
            print(f"[dry-run] wait {seconds:.2f}s{name}")
            return

        print(f"[live] wait {seconds:.2f}s{name}")
        sleep(seconds)

    def _resolve_coordinates(self, tap: Tap) -> tuple[int, int]:
        if tap.coordinate_space == "screen":
            return tap.x, tap.y

        if tap.coordinate_space != "window":
            raise ValueError(f"unsupported coordinate_space: {tap.coordinate_space}")

        if self.window is None:
            if self.dry_run:
                return tap.x, tap.y
            raise RuntimeError("window-relative tap requires a detected iPhone Mirroring window")

        left = int(self.window.bounds.get("X", 0))
        top = int(self.window.bounds.get("Y", 0))
        return left + tap.x, top + tap.y

    def pause_after_step(self) -> None:
        if self.dry_run:
            return
        sleep(self.pause_seconds)
