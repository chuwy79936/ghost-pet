# Ghost Desktop Pet

A cute ghost that floats around the desktop, says random phrases, and occasionally scares you.

## Tech Stack
- Python 3
- PyQt5
- Forced XWayland (`QT_QPA_PLATFORM=xcb`) for proper window positioning on Wayland

## Files
- `ghost_pet.py` - Main application (single-widget design — ghost + speech bubble drawn together), Config class, system tray icon
- `settings_dialog.py` - Settings dialog (QDialog) for configuring ghost behavior live
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
- **System tray icon** with right-click menu: Settings, Scare now!, Quit
- **Settings dialog** — configure speed, speech, opacity, scare, and scale live; persists to `~/.config/ghost-pet/config.json` (XDG-compliant)
- **Ghost scale** — resize the ghost from 0.5x to 3.0x via settings
- **Custom phrases** — override built-in phrases with your own via settings

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

## Settings System
- `Config` class in `ghost_pet.py` handles load/save of `~/.config/ghost-pet/config.json`
- Uses `XDG_CONFIG_HOME` env var (Flatpak-compatible)
- `GhostPet.apply_config()` pushes changes live (timers, scale, phrase queues) without restart
- Settings dialog (`settings_dialog.py`) imported lazily on first open
- Flatpak installs `settings_dialog.py` to `/app/lib/ghost-pet/`; path added via `sys.path`
- `_do_scare()` always executes (for "Scare now!" menu); `_start_scare()` respects `scare_enabled`

## Architecture
- Single widget draws both ghost body and speech bubble in one `paintEvent` — eliminates z-order issues between bubble and ghost
- Opacity controlled via `painter.setOpacity()` per frame
- `painter.scale(s, s)` applies ghost_scale — all drawing uses base coordinates (220x210)
- Phrase queue uses `random.sample()` shuffle to cycle through all phrases without repeats
- System tray icon drawn programmatically via `QPixmap`/`QPainter` (no external icon file needed)

## Known Issues
- Wayland does not support `self.move()`, `setWindowOpacity()`, or `raise_()` — app must run via XWayland (forced with `QT_QPA_PLATFORM=xcb`)
- `WindowStaysOnBottomHint` doesn't work on all compositors (hides behind wallpaper)
- `X11BypassWindowManagerHint` causes invisibility on some setups
