# Ghost Desktop Pet

A cute ghost that floats around the desktop and says random phrases.

## Tech Stack
- Python 3
- PyQt5

## Files
- `ghost_pet.py` - Main application
- `ghost-pet.desktop` - Desktop entry for app menu and autostart

## Running
```bash
python3 ghost_pet.py &
```

## Installation Locations
- App menu: `~/.local/share/applications/ghost-pet.desktop`
- Autostart: `~/.config/autostart/ghost-pet.desktop`

## Features
- Transparent floating ghost with cute design (blush, shiny eyes)
- Wanders randomly around the screen
- Gentle floating animation
- Speech bubbles with random phrases every ~15 seconds
- Click-through (doesn't block mouse input)
- Stays on top of desktop but doesn't steal focus

## Window Flags Used
- `Qt.FramelessWindowHint` - No window decorations
- `Qt.WindowStaysOnTopHint` - Always visible
- `Qt.Tool` - Doesn't appear in taskbar
- `Qt.WindowTransparentForInput` - Click-through
- `Qt.WA_TranslucentBackground` - Transparent background
- `Qt.WA_ShowWithoutActivating` - Doesn't steal focus

## Known Issues
- `WindowStaysOnBottomHint` doesn't work on all compositors (hides behind wallpaper)
- `X11BypassWindowManagerHint` causes invisibility on some setups
- Speech bubbles may briefly steal focus on some window managers
