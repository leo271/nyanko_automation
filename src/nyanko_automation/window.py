from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class WindowInfo:
    pid: int
    owner: str
    title: str
    bounds: dict[str, Any]


def list_windows() -> list[WindowInfo]:
    try:
        import Quartz
    except ImportError:
        return []

    options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
    raw_windows = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID) or []

    windows: list[WindowInfo] = []
    for raw in raw_windows:
        owner = raw.get("kCGWindowOwnerName", "")
        title = raw.get("kCGWindowName", "")
        bounds = raw.get("kCGWindowBounds", {})
        pid = int(raw.get("kCGWindowOwnerPID", 0))
        if owner or title:
            windows.append(WindowInfo(pid=pid, owner=owner, title=title, bounds=bounds))

    return windows


def find_best_window(keywords: list[str]) -> WindowInfo | None:
    lowered = [keyword.lower() for keyword in keywords]

    for window in list_windows():
        haystack = f"{window.owner} {window.title}".lower()
        if any(keyword in haystack for keyword in lowered):
            return window

    return None
