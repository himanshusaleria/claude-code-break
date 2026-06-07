#!/usr/bin/env python3
"""Movement Break — fire a short movement suggestion when Claude Code goes idle or finishes a turn.

Usage (from Claude Code hooks):
    mover.py prompt    # pick + emit a suggestion (reads hook JSON from stdin)
    mover.py clear     # clear any pending notification + log completion
    mover.py stats     # print today's tally

Hook payload is read from stdin as JSON; we use hook_event_name to gate behavior.
"""

from __future__ import annotations

import json
import os
import platform
import random
import subprocess
import sys
import time
from datetime import date, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
STATE_DIR = Path(os.environ.get("MOVEMENT_BREAK_HOME", Path.home() / ".movement-break"))
STATE_FILE = STATE_DIR / "state.json"
LOG_FILE = STATE_DIR / "log.jsonl"


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def load_config() -> dict:
    return load_json(SCRIPT_DIR / "config.json", {})


def load_exercises() -> dict:
    return load_json(SCRIPT_DIR / "exercises.json", {})


def load_state() -> dict:
    return load_json(STATE_FILE, {})


def save_state(state: dict) -> None:
    save_json(STATE_FILE, state)


def append_log(entry: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


def read_hook_payload() -> dict:
    if sys.stdin.isatty():
        return {}
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return {}


def pick_intensity(weights: dict) -> str:
    items = list(weights.items())
    population = [k for k, _ in items]
    probs = [w for _, w in items]
    return random.choices(population, weights=probs, k=1)[0]


def pick_exercise(config: dict, state: dict, exercises: dict) -> tuple[str, str]:
    """Returns (intensity, exercise_text). Avoids repeating the last exercise.

    Hydration fires on its own slow cadence and overrides the random pick when due.
    """
    hydration_pool = list(exercises.get("hydration", []))
    if hydration_pool:
        interval = int(config.get("hydration_interval_seconds", 7200))
        last_at = float(state.get("last_hydration_at", 0))
        if (time.time() - last_at) >= interval:
            last = state.get("last_exercise")
            if last in hydration_pool and len(hydration_pool) > 1:
                hydration_pool.remove(last)
            return "hydration", random.choice(hydration_pool)

    weights = dict(config.get("intensity_weights", {"micro": 0.6, "light": 0.3, "active": 0.1}))

    today = date.today().isoformat()
    daily = state.get("daily", {})
    if daily.get("date") != today:
        daily = {"date": today, "active_count": 0, "total_count": 0}

    if daily["active_count"] >= int(config.get("daily_cap_active", 40)):
        weights.pop("active", None)
        if not weights:
            weights = {"micro": 1.0}

    last = state.get("last_exercise")
    for _ in range(8):
        intensity = pick_intensity(weights)
        pool = list(exercises.get(intensity, []))
        if last in pool and len(pool) > 1:
            pool.remove(last)
        if not pool:
            continue
        choice = random.choice(pool)
        return intensity, choice
    return "micro", "Take three slow deep breaths"


def _applescript_quote(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def notify_macos(title: str, message: str, sound: str | None = None) -> None:
    script = (
        f'display notification {_applescript_quote(message)} '
        f'with title {_applescript_quote(title)}'
    )
    if sound:
        script += f' sound name {_applescript_quote(sound)}'
    subprocess.run(["osascript", "-e", script], check=False)


def notify_linux(title: str, message: str, sound: str | None = None) -> None:
    subprocess.run(["notify-send", title, message], check=False)
    if sound:
        for cmd in (["paplay", sound], ["aplay", sound], ["play", sound]):
            try:
                subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except FileNotFoundError:
                continue


def emit_notification(title: str, message: str, sound: str | None = None) -> None:
    system = platform.system()
    try:
        if system == "Darwin":
            notify_macos(title, message, sound)
        elif system == "Linux":
            notify_linux(title, message, sound)
    except FileNotFoundError:
        pass


def emit_tts(message: str) -> None:
    system = platform.system()
    try:
        if system == "Darwin":
            subprocess.Popen(["say", message])
        elif system == "Linux":
            for cmd in (["espeak", message], ["spd-say", message]):
                try:
                    subprocess.Popen(cmd)
                    return
                except FileNotFoundError:
                    continue
    except FileNotFoundError:
        pass


def cmd_prompt(payload: dict) -> int:
    config = load_config()
    exercises = load_exercises()
    state = load_state()

    hook_event = payload.get("hook_event_name", "manual")
    triggers = set(config.get("trigger_events", ["Notification", "Stop"]))
    if hook_event != "manual" and hook_event not in triggers:
        return 0

    now = time.time()
    cooldown = int(config.get("cooldown_seconds", 90))
    last_at = float(state.get("last_prompt_at", 0))
    if hook_event != "manual" and (now - last_at) < cooldown:
        return 0

    intensity, exercise = pick_exercise(config, state, exercises)

    if intensity == "hydration":
        title = config.get("hydration_title", "Hydration Break")
    else:
        title = config.get("notification_title", "Movement Break")
    channels = config.get("channels", {})
    if channels.get("notification", True):
        sound = config.get("notification_sound") or None
        emit_notification(title, exercise, sound)
    if channels.get("terminal", True):
        sys.stdout.write(f"\n[movement-break] {intensity}: {exercise}\n")
        sys.stdout.flush()
    if channels.get("tts", False):
        emit_tts(exercise)

    today = date.today().isoformat()
    daily = state.get("daily", {})
    if daily.get("date") != today:
        daily = {"date": today, "active_count": 0, "total_count": 0}
    daily["total_count"] = int(daily.get("total_count", 0)) + 1
    if intensity == "active":
        daily["active_count"] = int(daily.get("active_count", 0)) + 1

    state["last_exercise"] = exercise
    state["last_intensity"] = intensity
    state["last_prompt_at"] = now
    if intensity == "hydration":
        state["last_hydration_at"] = now
    state["daily"] = daily
    save_state(state)

    append_log({
        "ts": datetime.now().isoformat(),
        "event": "prompt",
        "hook": hook_event,
        "intensity": intensity,
        "exercise": exercise,
    })
    return 0


def cmd_clear(payload: dict) -> int:
    state = load_state()
    state["last_cleared_at"] = time.time()
    save_state(state)
    append_log({
        "ts": datetime.now().isoformat(),
        "event": "clear",
        "hook": payload.get("hook_event_name", "manual"),
    })
    return 0


def cmd_stats(_payload: dict) -> int:
    state = load_state()
    daily = state.get("daily", {})
    today = date.today().isoformat()
    if daily.get("date") != today:
        print("No prompts today yet.")
        return 0
    print(f"Today ({today}): {daily.get('total_count', 0)} prompts, "
          f"{daily.get('active_count', 0)} active.")
    if state.get("last_exercise"):
        print(f"Last: [{state.get('last_intensity', '?')}] {state['last_exercise']}")
    return 0


COMMANDS = {
    "prompt": cmd_prompt,
    "clear": cmd_clear,
    "stats": cmd_stats,
}


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"usage: mover.py {{{'|'.join(COMMANDS)}}}", file=sys.stderr)
        return 2
    payload = read_hook_payload()
    return COMMANDS[sys.argv[1]](payload)


if __name__ == "__main__":
    raise SystemExit(main())
