# claude-code-break

> Tiny movement nudges during the windows when Claude Code is working or waiting on you.

Claude Code's long-running tasks create dead time. Most of us fill it by scrolling. `claude-code-break` hooks into Claude Code's lifecycle and pushes a short suggestion to your screen instead — "roll your neck," "5 pushups," "look 20 feet away" — exactly when you're tempted to grab your phone.

When Claude Code finishes, the prompt is done. No timers. No app to open. No habit to maintain.

## How it works

`claude-code-break` is a single Python script wired to two Claude Code hooks:

- **`Notification`** — fires when Claude Code is idle or waiting on you (permission prompt, idle prompt). The classic "don't reach for your phone" moment.
- **`Stop`** — fires when Claude Code finishes a turn. Catches the end-of-task pause.

On each event the script picks an exercise, respects a cooldown so you aren't spammed, and emits the suggestion via native notification + terminal print. State and history live in `~/.movement-break/`.

## Install

Requires Python 3.8+. macOS and Linux supported.

```bash
git clone https://github.com/himanshusaleria/claude-code-break.git ~/claude-code-break
chmod +x ~/claude-code-break/mover.py
```

Then add the hooks to `~/.claude/settings.json` (create the file if it doesn't exist):

```json
{
  "hooks": {
    "Notification": [
      {
        "hooks": [
          { "type": "command", "command": "/Users/YOU/claude-code-break/mover.py prompt" }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "/Users/YOU/claude-code-break/mover.py prompt" }
        ]
      }
    ]
  }
}
```

Replace the path with the absolute path to your `mover.py`. Restart Claude Code. Next time it goes idle, you'll get a nudge.

A copy of this snippet is in `settings.example.json`.

## Test it before wiring

```bash
echo '{}' | ./mover.py prompt
./mover.py stats
```

You should see a notification appear and a line in the terminal.

## Configure

Edit `config.json`:

| Key | Meaning |
|-----|---------|
| `intensity_weights` | Probability of each tier. Default: 60% micro, 30% light, 10% active. Adjust to taste. |
| `cooldown_seconds` | Minimum gap between prompts. Default 90s — prevents spam during rapid tool calls. |
| `daily_cap_active` | Max active exercises per day (e.g. pushups). After the cap, active tier is skipped. Default 40. |
| `channels.notification` | OS notification (osascript on Mac, notify-send on Linux). Default on. |
| `channels.terminal` | Print the suggestion to stdout. Default on. |
| `channels.tts` | Speak the suggestion aloud (`say` on Mac, `espeak`/`spd-say` on Linux). Default off. |
| `trigger_events` | Which Claude Code hook events fire a prompt. Default `["Notification", "Stop"]`. Add `"PreToolUse"` if you want a nudge on every tool call (cooldown still applies). |

## The exercise pool

`exercises.json` ships with 24 exercises in three tiers:

- **micro** (~10s, always safe): breathing, neck rolls, jaw unclench, eye rest, posture resets
- **light** (~20–30s): shoulder rolls, wrist stretches, calf raises, spinal twists, forward folds
- **active** (~30–60s): 1 pushup, 5 pushups, 10 squats, 30s wall sit, plank

Add your own — just edit the JSON. Pick whatever tier fits the intensity.

## Stats and history

Every prompt is logged to `~/.movement-break/log.jsonl` (one JSON object per line). Run `mover.py stats` to see today's tally:

```text
Today (2026-06-07): 12 prompts, 2 active.
Last: [micro] Drop your shoulders away from your ears
```

Pipe the log through `jq` if you want a weekly breakdown.

## Troubleshooting

- **No notification on macOS?** First run will prompt for notification permission for `osascript` or your Terminal app. Allow it.
- **Notification but no terminal print?** The hook's stdout doesn't always surface inside Claude Code's UI. That's fine — the notification is the primary channel.
- **Getting nudged too often?** Bump `cooldown_seconds` to 180 or 300. Or set `trigger_events` to `["Stop"]` only.
- **Want the prompt spoken aloud?** Set `channels.tts` to `true` in `config.json`. Mac uses the system `say` command; Linux needs `espeak` or `spd-say` installed.

## License

MIT.
