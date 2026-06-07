# claude-code-break

> Tiny movement + hydration nudges during the windows when Claude Code is working or waiting on you.

Claude Code's long-running tasks create dead time. Most of us fill it by scrolling. `claude-code-break` hooks into Claude Code's lifecycle and pushes a short suggestion to your screen instead — "roll your neck," "5 pushups," "drink a glass of water" — exactly when you're tempted to grab your phone.

## Install

Requires Python 3.8+. macOS and Linux.

```bash
git clone https://github.com/himanshusaleria/claude-code-break.git ~/claude-code-break
chmod +x ~/claude-code-break/mover.py
```

Add the hooks to `~/.claude/settings.json` (a copy is in `settings.example.json`):

```json
{
  "hooks": {
    "Notification": [
      { "hooks": [{ "type": "command", "command": "~/claude-code-break/mover.py prompt" }] }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": "~/claude-code-break/mover.py prompt" }] }
    ]
  }
}
```

Restart Claude Code. Verify with `echo '{}' | ~/claude-code-break/mover.py prompt`.

### Install via a Claude Code prompt

Paste this into any Claude Code session and it'll set the hooks up globally for every future session:

> Install claude-code-break for all my Claude Code sessions. If `~/claude-code-break` doesn't exist, clone `https://github.com/himanshusaleria/claude-code-break` into it and `chmod +x mover.py`. Then merge — don't overwrite — `Notification` and `Stop` hooks into `~/.claude/settings.json` that each run `~/claude-code-break/mover.py prompt`. Verify by running `echo '{}' | ~/claude-code-break/mover.py prompt` and confirm a notification fires.

## How it works

Two hooks fire the script:

- **`Notification`** — Claude Code is idle or waiting on you (permission/idle prompt).
- **`Stop`** — Claude Code finished a turn.

The script picks a movement or hydration prompt, respects a cooldown so you aren't spammed, and emits the suggestion via native notification (with sound) + terminal. State and history live in `~/.movement-break/`.

## Configure

Edit `config.json`:

| Key | Meaning |
|-----|---------|
| `intensity_weights` | Probability of each movement tier. Default: 60% micro, 30% light, 10% active. |
| `cooldown_seconds` | Min gap between any prompts. Default 90s. |
| `daily_cap_active` | Max active exercises per day. Default 40. |
| `hydration_interval_seconds` | Min gap between hydration prompts. Default 7200 (2h). Hydration overrides the random pick when due. |
| `notification_sound` | macOS: name from `/System/Library/Sounds` (Glass, Ping, Hero…). Linux: absolute path to a sound file. Empty string disables. Default `Glass`. |
| `channels.notification` | OS notification. Default on. |
| `channels.terminal` | Print to stdout. Default on. |
| `channels.tts` | Speak the suggestion aloud (`say` on Mac, `espeak`/`spd-say` on Linux). Default off. |
| `trigger_events` | Which Claude Code events fire a prompt. Default `["Notification", "Stop"]`. Add `"PreToolUse"` for nudges on every tool call (cooldown still applies). |

## Exercise pool

`exercises.json` ships with four tiers — edit the JSON to add your own:

- **micro** (~10s, always safe): breathing, neck rolls, jaw, eye rest, posture
- **light** (~20–30s): shoulder rolls, calf raises, short walks, stretches
- **active** (~30–60s): pushups, squats, plank, brisk walks, stairs
- **hydration** (every ~2h): drink water, refill bottle

## Stats

Every prompt is logged to `~/.movement-break/log.jsonl` (one JSON per line). Run `mover.py stats` for today's tally. Pipe through `jq` for weekly breakdowns.

## Troubleshooting

- **No notification on macOS?** First run prompts for notification permission for `osascript`/Terminal. Allow it.
- **Too frequent?** Bump `cooldown_seconds` to 180–300, or set `trigger_events` to `["Stop"]` only.
- **No terminal print inside Claude Code's UI?** Expected — the hook's stdout doesn't always surface. The notification is the primary channel.

## License

MIT.
