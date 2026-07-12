from __future__ import annotations

from pathlib import Path

from .window import WindowInfo


def capture_window_or_screen(path: Path, *, window: WindowInfo | None = None) -> Path:
    import pyautogui

    path.parent.mkdir(parents=True, exist_ok=True)

    if window is None:
        image = pyautogui.screenshot()
    else:
        left = int(window.bounds.get("X", 0))
        top = int(window.bounds.get("Y", 0))
        width = int(window.bounds.get("Width", 0))
        height = int(window.bounds.get("Height", 0))
        image = pyautogui.screenshot(region=(left, top, width, height))

    image.save(path)
    return path
