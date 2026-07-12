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

    print("snippets:")
    for snippet in registry.all():
        print(f"{snippet.id}\t{snippet.kind}\t{snippet.name}")
    return 0


def routines() -> int:
    config = load_config()
    registry = load_registry(config)

    print(f"default: {registry.default_routine}")
    for routine in registry.routines():
        cycle = " -> ".join(registry.preview_cycle(routine_id=routine.id))
        print(f"{routine.id}\t{routine.name}\t{cycle}")
    return 0


def build_engine(args: argparse.Namespace, config: dict, registry, routine):
    from .actions import ActionRunner
    from .engine import RoutineEngine
    from .window import find_best_window

    dry_run = config.get("dry_run", True)
    if args.live:
        dry_run = False
    if args.dry_run:
        dry_run = True

    window = None if dry_run else find_best_window(config["window_title_keywords"])
    if not dry_run and window is None:
        print("iPhone Mirroring window was not found. Run `nyanko-auto windows` first.")
        return None

    runner = ActionRunner(
        dry_run=dry_run,
        pause_seconds=float(config.get("action_pause_seconds", 0.15)),
        window=window,
    )
    engine = RoutineEngine(
        registry=registry,
        routine=routine,
        runner=runner,
        root=ROOT,
        screenshot_path=resolve_root_path(config["screenshot_path"]),
        window=window,
    )
    return engine


def run(args: argparse.Namespace) -> int:
    config = load_config()
    registry = load_registry(config)
    routine = registry.get_routine(args.routine_id)

    cycles = None if args.forever else args.cycles
    engine = build_engine(args, config, registry, routine)
    if engine is None:
        return 1

    engine.run(start_id=args.start_id, cycles=cycles)
    return 0


def run_snippet(args: argparse.Namespace) -> int:
    if args.repeat < 1:
        raise ValueError("--repeat must be at least 1")

    config = load_config()
    registry = load_registry(config)
    routine = registry.get_routine(args.routine_id)
    snippet = registry.get(args.snippet_id)

    engine = build_engine(args, config, registry, routine)
    if engine is None:
        return 1

    for index in range(args.repeat):
        print(f"[single {index + 1}/{args.repeat}] {snippet.id}")
        engine.run_snippet(snippet)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="nyanko-auto")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="Print local permission checklist")
    subparsers.add_parser("windows", help="List visible macOS windows")
    subparsers.add_parser("capture", help="Capture iPhone Mirroring window or full screen")
    subparsers.add_parser("snippets", help="List registered snippets")
    subparsers.add_parser("routines", help="List registered routines and transitions")

    run_parser = subparsers.add_parser("run", help="Run the configured snippet loop")
    run_parser.add_argument("--routine", dest="routine_id", help="Routine id to run")
    run_parser.add_argument("--from", dest="start_id", help="Snippet id to start from")
    run_parser.add_argument("--cycles", type=int, default=None, help="Number of full cycles to run")
    run_parser.add_argument("--forever", action="store_true", help="Run until interrupted")
    run_parser.add_argument("--dry-run", action="store_true", help="Print actions without clicking")
    run_parser.add_argument(
        "--live",
        action="store_true",
        help="Execute enabled click/capture steps",
    )

    snippet_parser = subparsers.add_parser(
        "run-snippet",
        help="Run one registered snippet without transitions",
    )
    snippet_parser.add_argument("snippet_id", help="Snippet id to run")
    snippet_parser.add_argument("--routine", dest="routine_id", help="Routine id for context")
    snippet_parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Run the snippet this many times consecutively",
    )
    snippet_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without clicking",
    )
    snippet_parser.add_argument(
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
    if args.command == "routines":
        return routines()
    if args.command == "run":
        if args.forever and args.cycles is not None:
            parser.error("use either --forever or --cycles, not both")
        if args.cycles is None:
            config = load_config()
            args.cycles = int(config.get("default_cycles", 1))
        return run(args)
    if args.command == "run-snippet":
        return run_snippet(args)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
