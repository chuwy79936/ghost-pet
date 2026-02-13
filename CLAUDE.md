# Ghost Desktop Pet

A cute ghost that floats around the desktop, says random phrases, and occasionally scares you.

## Tech Stack
- Python 3
- PyQt5
- Forced XWayland (`QT_QPA_PLATFORM=xcb`) for proper window positioning on Wayland

## Files
- `ghost_pet.py` - Main application (single-widget design — ghost + speech bubble drawn together)
- `ghost-pet.desktop` - Desktop entry for app menu and autostart

## Running
```bash
python3 ghost_pet.py &
```

## Installation Locations
- App menu: `~/.local/share/applications/ghost-pet.desktop`
- Autostart: `~/.config/autostart/ghost-pet.desktop`

## Features
- Transparent floating ghost with cute design (blush, shiny eyes, drop shadow)
- Continuously drifts across all monitors (optionally filtered with `--monitors MANUFACTURER`)
- Gentle bobbing float animation
- Organic opacity phasing — layered sine waves fade the ghost in and out like a real ghost
- Speech bubbles with 47 shuffled phrases (ghost puns, encouragement) every ~15 seconds
- **Scare mode**: Every 5-10 minutes, ghost fades in on top of all windows, says a scare phrase (30 total), then fades back out (5-second animation)
- Click-through at all times (mouse events pass to windows underneath)
- Never steals focus or appears in taskbar

## Monitor Filter
Uses all monitors by default. Pass `--monitors Samsung` (or any manufacturer substring) to restrict. Falls back to the primary screen if no monitors match.

## Window Flags
- `Qt.FramelessWindowHint` - No window decorations
- `Qt.WindowStaysOnTopHint` - Always on top (scare effect uses opacity only)
- `Qt.Tool` - Doesn't appear in taskbar
- `Qt.WindowTransparentForInput` - Click-through
- `Qt.WA_TranslucentBackground` - Transparent background
- `Qt.WA_ShowWithoutActivating` - Doesn't steal focus

**Important**: Flags are set once at startup and never swapped. Calling `setWindowFlags()` at runtime on XWayland leaks native X11 windows (creates duplicates).

## Architecture
- Single widget draws both ghost body and speech bubble in one `paintEvent` — eliminates z-order issues between bubble and ghost
- Opacity controlled via `setWindowOpacity()` — requires XWayland on Wayland compositors
- Phrase queue uses `random.sample()` shuffle to cycle through all phrases without repeats

## Known Issues
- Wayland does not support `self.move()`, `setWindowOpacity()`, or `raise_()` — app must run via XWayland (forced with `QT_QPA_PLATFORM=xcb`)
- `WindowStaysOnBottomHint` doesn't work on all compositors (hides behind wallpaper)
- `X11BypassWindowManagerHint` causes invisibility on some setups
