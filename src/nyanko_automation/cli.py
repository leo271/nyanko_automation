from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "default.json"


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolve_root_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def load_registry(config: dict):
    from .snippets import SnippetRegistry

    return SnippetRegistry.from_path(resolve_root_path(config["snippets_path"]))


def doctor() -> int:
    print("Check macOS permissions before running automation:")
    print("- System Settings > Privacy & Security > Accessibility")
    print("- System Settings > Privacy & Security > Screen Recording")
    print("Grant both to Terminal, iTerm, or the app that runs Python.")
    return 0


def windows() -> int:
    from .window import list_windows

    items = list_windows()
    if not items:
        print("No windows found. On macOS, install dependencies and grant permissions first.")
        return 1

    for item in items:
        title = item.title or "(no title)"
        print(f"{item.pid}\t{item.owner}\t{title}\t{item.bounds}")
    return 0


def capture() -> int:
    from .screenshot import capture_window_or_screen
    from .window import find_best_window

    config = load_config()
    keywords = config["window_title_keywords"]
    screenshot_path = ROOT / config["screenshot_path"]
    window = find_best_window(keywords)

    saved = capture_window_or_screen(screenshot_path, window=window)
    target = f"{window.owner}: {window.title}" if window else "full screen"
    print(f"Captured {target} -> {saved}")
    return 0


def snippets() -> int:
    config = load_config()
    registry = load_registry(config)

    print(f"start: {registry.start}")
    print("cycle: " + " -> ".join(registry.preview_cycle()))
    for snippet in registry.all():
        next_id = snippet.next_id or "(stop)"
        print(f"{snippet.id}\t{snippet.name}\t-> {next_id}")
    return 0


def run(args: argparse.Namespace) -> int:
    from .actions import ActionRunner
    from .engine import RoutineEngine
    from .window import find_best_window

    config = load_config()
    registry = load_registry(config)

    dry_run = config.get("dry_run", True)
    if args.live:
        dry_run = False
    if args.dry_run:
        dry_run = True

    cycles = None if args.forever else args.cycles
    window = None if dry_run else find_best_window(config["window_title_keywords"])
    if not dry_run and window is None:
        print("iPhone Mirroring window was not found. Run `nyanko-auto windows` first.")
        return 1

    runner = ActionRunner(
        dry_run=dry_run,
        pause_seconds=float(config.get("action_pause_seconds", 0.15)),
        window=window,
    )
    engine = RoutineEngine(
        registry=registry,
        runner=runner,
        root=ROOT,
        screenshot_path=resolve_root_path(config["screenshot_path"]),
        window=window,
    )
    engine.run(start_id=args.start_id, cycles=cycles)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="nyanko-auto")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="Print local permission checklist")
    subparsers.add_parser("windows", help="List visible macOS windows")
    subparsers.add_parser("capture", help="Capture iPhone Mirroring window or full screen")
    subparsers.add_parser("snippets", help="List registered snippets and transitions")

    run_parser = subparsers.add_parser("run", help="Run the configured snippet loop")
    run_parser.add_argument("--from", dest="start_id", help="Snippet id to start from")
    run_parser.add_argument("--cycles", type=int, default=None, help="Number of full cycles to run")
    run_parser.add_argument("--forever", action="store_true", help="Run until interrupted")
    run_parser.add_argument("--dry-run", action="store_true", help="Print actions without clicking")
    run_parser.add_argument(
        "--live",
        action="store_true",
        help="Execute enabled click/capture steps",
    )

    args = parser.parse_args()

    if args.command == "doctor":
        return doctor()
    if args.command == "windows":
        return windows()
    if args.command == "capture":
        return capture()
    if args.command == "snippets":
        return snippets()
    if args.command == "run":
        if args.forever and args.cycles is not None:
            parser.error("use either --forever or --cycles, not both")
        if args.cycles is None:
            config = load_config()
            args.cycles = int(config.get("default_cycles", 1))
        return run(args)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
