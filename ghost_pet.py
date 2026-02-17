#!/usr/bin/env python3
"""
Cute Ghost Desktop Pet
A friendly ghost that floats around your desktop and says cute things!
"""

import argparse
import json
import os
os.environ["QT_QPA_PLATFORM"] = "xcb"

import sys
import random
import math
import time

# Path setup for settings_dialog import (local dev + Flatpak)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_flatpak_lib = os.path.join(sys.prefix, "lib", "ghost-pet")
if os.path.isdir(_flatpak_lib):
    sys.path.insert(0, _flatpak_lib)

from PyQt5.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QFont, QBrush, QPen, QIcon, QPixmap


class Config:
    """Loads/saves ghost settings to XDG config directory."""

    DEFAULTS = {
        "speed": 2,
        "speak_interval": 15,
        "speak_chance": 0.7,
        "opacity_speed": 1.0,
        "opacity_min": 0.08,
        "opacity_max": 1.0,
        "scare_enabled": True,
        "scare_min_minutes": 5,
        "scare_max_minutes": 10,
        "ghost_scale": 1.0,
        "custom_phrases": [],
        "custom_scare_phrases": [],
    }

    def __init__(self):
        config_home = os.environ.get(
            "XDG_CONFIG_HOME",
            os.path.join(os.path.expanduser("~"), ".config"),
        )
        self._config_dir = os.path.join(config_home, "ghost-pet")
        self._config_file = os.path.join(self._config_dir, "config.json")
        for k, v in self.DEFAULTS.items():
            setattr(self, k, list(v) if isinstance(v, list) else v)
        self.load()

    def load(self):
        if os.path.isfile(self._config_file):
            try:
                with open(self._config_file) as f:
                    saved = json.load(f)
                for k, v in saved.items():
                    if k in self.DEFAULTS:
                        setattr(self, k, v)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        os.makedirs(self._config_dir, exist_ok=True)
        with open(self._config_file, "w") as f:
            json.dump(self.as_dict(), f, indent=2)

    def reset(self):
        for k, v in self.DEFAULTS.items():
            setattr(self, k, list(v) if isinstance(v, list) else v)

    def as_dict(self):
        return {k: getattr(self, k) for k in self.DEFAULTS}


class GhostPet(QWidget):
    """A cute floating ghost desktop pet."""

    # Base widget dimensions (before scaling)
    _BASE_W = 220
    _BASE_H = 210

    SCARE_PHRASES = [
        "BOO!!",
        "Did I scare you?",
        "Behind you!!",
        "I see you~",
        "*jumps out*",
        "Peek-a-boo!",
        "Miss me?",
        "Surprise!!",
        "Gotcha!",
        "Still here~",
        "You can't escape me!",
        "I never left...",
        "*appears menacingly*",
        "Thought you lost me?",
        "Guess who!",
        "You looked away...",
        "I was here the whole time",
        "*materializes*",
        "Boo from the beyond!",
        "Can't get rid of me~",
        "The walls have eyes!",
        "*emerges from screen*",
        "Right behind you!",
        "I haunt this desktop now",
        "Feeling a chill?",
        "*phases into reality*",
        "You forgot about me!",
        "Knock knock... BOO!",
        "The ghost is back!",
        "I'm always watching~",
    ]

    PHRASES = [
        "Boo! ~",
        "I'm friendly!",
        "*floats happily*",
        "Spooky vibes~",
        "Want a hug?",
        "I like you!",
        "*wiggles*",
        "So cozy here~",
        "Hewwo!",
        "*happy ghost noises*",
        "You're doing great!",
        "Take a break?",
        "Stay hydrated!",
        "*peeks at you*",
        "Boop!",
        "I believe in you!",
        "*sparkles*",
        "Keep going!",
        "You got this!",
        "*floats around*",
        "I'm here for the boos!",
        "You're my ghoul friend~",
        "I'm dead tired...",
        "Just passing through!",
        "Life is un-boo-lievable!",
        "I've got spirit!",
        "Don't ghost me!",
        "Creeping it real~",
        "Haunt you later!",
        "If you got it, haunt it!",
        "I'm having a fang-tastic day!",
        "Ghosting is my thing~",
        "You look boo-tiful!",
        "I'm a little ghoul-ish~",
        "Spook-tacular vibes!",
        "The ghoul next door~",
        "I ain't afraid of no work!",
        "Fangs for being here!",
        "Having a wail of a time!",
        "*phases through wall*",
        "Boo-lieve in yourself!",
        "I'm just a lost soul~",
        "Eek-xcuse me!",
        "*rattles chains cutely*",
        "I'm dead serious rn",
        "That was eerie-sistible!",
        "Ghouls just wanna have fun!",
    ]

    def __init__(self, config, monitor_filter=None):
        super().__init__()

        self.config = config
        self._scare_active = False

        # Single set of flags — never swap at runtime (XWayland leaks
        # native windows when setWindowFlags() recreates them).
        # No WindowStaysOnTopHint — ghost stays behind other windows.
        # Scares use raise_()/lower() to temporarily pop on top.
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Widget size scales with ghost_scale
        s = self.config.ghost_scale
        self.setFixedSize(int(self._BASE_W * s), int(self._BASE_H * s))

        # Where the ghost body is drawn within the widget (base coordinates)
        self._ghost_ox = 70   # (220 - 80) / 2
        self._ghost_oy = 90   # leave room for bubble + tail above

        # Speech bubble state (drawn in same widget — no z-order issues)
        self._bubble_msg = ""
        self._bubble_active = False
        self._bubble_width = 150

        self._phrase_queue = []

        self._bubble_timer = QTimer(self)
        self._bubble_timer.timeout.connect(self._dismiss_bubble)

        # Animation state
        self._float_offset = 0
        self._opacity = 1.0
        # Random phase offsets for organic-feeling opacity waves
        self._opacity_phases = [random.uniform(0, math.tau) for _ in range(3)]
        self.direction = 1  # 1 = right, -1 = left
        self.target_x = 0
        self.target_y = 0
        self.moving = False

        # Eye animation state
        self._blinking = False
        self._blink_style = "closed"  # "closed" or "squint" (><)
        self._sparkle_active = False
        self._sparkle_start = 0

        # Mouth animation state: "normal", "O", "happy"
        self._mouth = "normal"
        self._mouth_start = 0

        # Get bounding box of screens (optionally filtered by manufacturer)
        rects = []
        for screen in QApplication.screens():
            if monitor_filter and monitor_filter.lower() not in screen.manufacturer().lower():
                continue
            rects.append(screen.geometry())

        if not rects:
            # Fallback to primary screen
            screen = QApplication.primaryScreen().geometry()
            rects.append(screen)

        self.bounds_x = min(r.x() for r in rects)
        self.bounds_y = min(r.y() for r in rects)
        self.bounds_right = max(r.x() + r.width() for r in rects)
        self.bounds_bottom = max(r.y() + r.height() for r in rects)

        # current_x/y = ghost body center on screen
        self.current_x = (self.bounds_x + self.bounds_right) // 2
        self.current_y = (self.bounds_y + self.bounds_bottom) // 2
        self._update_widget_pos()

        # Timers
        self.float_timer = QTimer(self)
        self.float_timer.timeout.connect(self._update_float)
        self.float_timer.start(50)

        self.move_timer = QTimer(self)
        self.move_timer.timeout.connect(self._update_position)
        self.move_timer.start(30)

        self.wander_timer = QTimer(self)
        self.wander_timer.timeout.connect(self._pick_new_destination)
        self.wander_timer.start(5000)

        self.speak_timer = QTimer(self)
        self.speak_timer.timeout.connect(self._say_random_phrase)
        self.speak_timer.start(self.config.speak_interval * 1000)

        # Scare timer — pop up on top periodically
        self._scare_timer = QTimer(self)
        self._scare_timer.setSingleShot(True)
        self._scare_timer.timeout.connect(self._start_scare)
        if self.config.scare_enabled:
            self._schedule_next_scare()

        # Blink timer — random blinks every 3-7 seconds
        self._blink_timer = QTimer(self)
        self._blink_timer.setSingleShot(True)
        self._blink_timer.timeout.connect(self._start_blink)
        self._schedule_next_blink()

        # Sparkle timer — sparkly eyes every 20-40 seconds
        self._sparkle_timer = QTimer(self)
        self._sparkle_timer.setSingleShot(True)
        self._sparkle_timer.timeout.connect(self._start_sparkle)
        self._schedule_next_sparkle()

        # Mouth animation timer — random expressions every 10-25 seconds
        self._mouth_timer = QTimer(self)
        self._mouth_timer.setSingleShot(True)
        self._mouth_timer.timeout.connect(self._start_mouth)
        self._schedule_next_mouth()

        # Arms animation — little nubs poke out every 15-35 seconds
        self._arms_active = False
        self._arms_start = 0
        self._arms_timer = QTimer(self)
        self._arms_timer.setSingleShot(True)
        self._arms_timer.timeout.connect(self._start_arms)
        self._schedule_next_arms()

        # Initial destination
        self._pick_new_destination()

        # Say hello!
        QTimer.singleShot(1000, lambda: self._say_phrase("Boo! I'm your new friend!"))

    # ── config ────────────────────────────────────────────────────

    def apply_config(self):
        """Apply config changes live without restart."""
        self.speak_timer.start(self.config.speak_interval * 1000)
        self._phrase_queue = []

        if not self.config.scare_enabled:
            self._scare_timer.stop()
        elif not self._scare_timer.isActive() and not self._scare_active:
            self._schedule_next_scare()

        s = self.config.ghost_scale
        self.setFixedSize(int(self._BASE_W * s), int(self._BASE_H * s))
        self._update_widget_pos()
        self.update()

    # ── positioning ──────────────────────────────────────────────

    def _update_widget_pos(self):
        """Position widget so ghost body center aligns with current_x/y."""
        s = self.config.ghost_scale
        wx = int(self.current_x - (self._ghost_ox + 40) * s)
        wy = int(self.current_y - (self._ghost_oy + 50) * s + self._float_offset)
        self.move(wx, wy)

    # ── speech bubble ────────────────────────────────────────────

    def _dismiss_bubble(self):
        self._bubble_active = False
        self._bubble_timer.stop()
        self.update()

    def _say_phrase(self, phrase):
        self._bubble_msg = phrase
        self._bubble_width = max(150, len(phrase) * 10 + 40)
        self._bubble_active = True
        self._bubble_timer.start(3000)
        self.update()

    def _next_phrase(self):
        phrases = self.config.custom_phrases or self.PHRASES
        if not self._phrase_queue:
            self._phrase_queue = random.sample(phrases, len(phrases))
        return self._phrase_queue.pop()

    def _say_random_phrase(self):
        if random.random() < self.config.speak_chance:
            self._say_phrase(self._next_phrase())

    # ── animation ────────────────────────────────────────────────

    def _update_float(self):
        t = time.time()
        self._float_offset = math.sin(t * 2) * 5

        # Ghostly opacity — skip during scare (stay fully visible)
        if not self._scare_active:
            p = self._opacity_phases
            sp = self.config.opacity_speed
            wave = (math.sin(t * 0.3 * sp + p[0]) * 0.35 +
                    math.sin(t * 0.7 * sp + p[1]) * 0.25 +
                    math.sin(t * 1.1 * sp + p[2]) * 0.15)
            self._opacity = max(self.config.opacity_min,
                                min(self.config.opacity_max, 0.55 + wave))

        self._update_widget_pos()
        self.update()

    def _pick_new_destination(self):
        margin = 100
        self.target_x = random.randint(self.bounds_x + margin,
                                       self.bounds_right - margin)
        self.target_y = random.randint(self.bounds_y + margin,
                                       self.bounds_bottom - margin)
        self.moving = True

        if self.target_x > self.current_x:
            self.direction = 1
        else:
            self.direction = -1

    def _update_position(self):
        if not self.moving:
            return

        speed = self.config.speed
        dx = self.target_x - self.current_x
        dy = self.target_y - self.current_y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < speed:
            self.current_x = self.target_x
            self.current_y = self.target_y
            self.moving = False
            # Immediately pick a new destination — keeps the ghost always drifting
            self._pick_new_destination()
        else:
            self.current_x += (dx / distance) * speed
            self.current_y += (dy / distance) * speed

        self._update_widget_pos()

    # ── eye animations ───────────────────────────────────────────

    def _schedule_next_blink(self):
        self._blink_timer.start(random.randint(3000, 7000))

    def _start_blink(self):
        self._blink_style = random.choice(["closed", "closed", "squint"])
        self._blinking = True
        self.update()
        duration = 150 if self._blink_style == "closed" else 300
        QTimer.singleShot(duration, self._end_blink)

    def _end_blink(self):
        self._blinking = False
        self.update()
        self._schedule_next_blink()

    def _schedule_next_sparkle(self):
        self._sparkle_timer.start(random.randint(20000, 40000))

    def _start_sparkle(self):
        self._sparkle_active = True
        self._sparkle_start = time.time()
        QTimer.singleShot(2000, self._end_sparkle)

    def _end_sparkle(self):
        self._sparkle_active = False
        self.update()
        self._schedule_next_sparkle()

    def _schedule_next_mouth(self):
        self._mouth_timer.start(random.randint(10000, 25000))

    def _start_mouth(self):
        self._mouth = random.choice(["O", "happy"])
        self._mouth_start = time.time()
        self.update()
        duration = 1500 if self._mouth == "O" else 2000
        QTimer.singleShot(duration, self._end_mouth)

    def _end_mouth(self):
        self._mouth = "normal"
        self.update()
        self._schedule_next_mouth()

    # ── arms ─────────────────────────────────────────────────────

    def _schedule_next_arms(self):
        self._arms_timer.start(random.randint(15000, 35000))

    def _start_arms(self):
        self._arms_active = True
        self._arms_start = time.time()
        QTimer.singleShot(3000, self._end_arms)

    def _end_arms(self):
        self._arms_active = False
        self.update()
        self._schedule_next_arms()

    # ── scare ────────────────────────────────────────────────────

    def _schedule_next_scare(self):
        lo = self.config.scare_min_minutes * 60 * 1000
        hi = self.config.scare_max_minutes * 60 * 1000
        if lo > hi:
            lo, hi = hi, lo
        delay = random.randint(lo, hi)
        self._scare_timer.start(delay)

    def _start_scare(self):
        """Called by scare timer — respects scare_enabled setting."""
        if not self.config.scare_enabled:
            self._schedule_next_scare()
            return
        self._do_scare()

    def _do_scare(self):
        """Execute a scare animation (always runs, even if scare is disabled)."""
        self._scare_active = True
        self._scare_start = time.time()
        self._scare_duration = 5.0  # total seconds

        # Pop to front of all windows
        self.raise_()

        # Start fully transparent then fade in
        self._opacity = 0.0

        # Say a scare phrase
        scare_phrases = self.config.custom_scare_phrases or self.SCARE_PHRASES
        phrase = random.choice(scare_phrases)
        self._say_phrase(phrase)

        # Tick the scare animation at 30fps
        self._scare_tick_timer = QTimer(self)
        self._scare_tick_timer.timeout.connect(self._scare_tick)
        self._scare_tick_timer.start(33)

    def _scare_tick(self):
        elapsed = time.time() - self._scare_start
        t = elapsed / self._scare_duration  # 0.0 → 1.0

        if t >= 1.0:
            # Done — fade complete, sink back behind windows
            self._scare_tick_timer.stop()
            self._scare_tick_timer.deleteLater()
            self._scare_active = False
            self._dismiss_bubble()
            self.lower()
            if self.config.scare_enabled:
                self._schedule_next_scare()
            return

        # Fade curve: in for first 30%, hold for middle 40%, out for last 30%
        if t < 0.3:
            opacity = t / 0.3                 # 0 → 1
        elif t < 0.7:
            opacity = 1.0                      # hold at full
        else:
            opacity = 1.0 - (t - 0.7) / 0.3   # 1 → 0

        self._opacity = opacity

    # ── drawing ──────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setOpacity(self._opacity)

        s = self.config.ghost_scale
        painter.scale(s, s)

        # --- Speech bubble (drawn first, ghost overlaps slightly) ---
        if self._bubble_active:
            # Keep bubble readable even when ghost is faded
            painter.setOpacity(max(self._opacity, 0.6))

            bw = min(self._bubble_width, self._BASE_W - 10)
            bh = 60
            bx = (self._BASE_W - bw) // 2
            by = 5

            path = QPainterPath()
            bubble_rect = QRect(bx + 5, by + 5, bw - 10, bh - 10)
            path.addRoundedRect(bubble_rect.x(), bubble_rect.y(),
                                bubble_rect.width(), bubble_rect.height(), 15, 15)

            # Tail pointing down toward ghost
            tail_x = self._BASE_W // 2
            tail_top = by + bh
            path.moveTo(tail_x - 10, tail_top - 5)
            path.lineTo(tail_x, tail_top + 10)
            path.lineTo(tail_x + 10, tail_top - 5)

            painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
            painter.setPen(QPen(QColor(200, 200, 200), 2))
            painter.drawPath(path)

            painter.setPen(QColor(60, 60, 60))
            painter.setFont(QFont("Sans", 10))
            painter.drawText(bubble_rect, Qt.AlignCenter | Qt.TextWordWrap,
                             self._bubble_msg)

            # Restore ghost opacity for body
            painter.setOpacity(self._opacity)

        # --- Ghost body ---
        painter.save()
        painter.translate(self._ghost_ox, self._ghost_oy)

        cx = 40   # center within 80-wide ghost area
        cy = 50

        if self.direction == -1:
            painter.translate(80, 0)
            painter.scale(-1, 1)

        # Ghost body path
        path = QPainterPath()
        path.moveTo(cx - 30, cy + 45)

        path.quadTo(cx - 35, cy, cx - 30, cy - 25)
        path.quadTo(cx - 25, cy - 40, cx, cy - 42)
        path.quadTo(cx + 25, cy - 40, cx + 30, cy - 25)
        path.quadTo(cx + 35, cy, cx + 30, cy + 45)

        wave_y = cy + 45
        wt = time.time() * 3  # wave animation speed
        w0 = math.sin(wt) * 4
        w1 = math.sin(wt + 1.5) * 4
        w2 = math.sin(wt + 3.0) * 4
        w3 = math.sin(wt + 4.5) * 4
        path.quadTo(cx + 22, wave_y + 12 + w0, cx + 15, wave_y + w0)
        path.quadTo(cx + 7, wave_y - 10 + w1, cx, wave_y + 5 + w1)
        path.quadTo(cx - 7, wave_y + 15 + w2, cx - 15, wave_y + w2)
        path.quadTo(cx - 22, wave_y - 8 + w3, cx - 30, wave_y + w3)

        # Arms (little rounded nubs that poke out from the sides)
        if self._arms_active:
            at = time.time() - self._arms_start
            # Ease in 0.4s, hold 2.2s, ease out 0.4s
            if at < 0.4:
                t = at / 0.4
            elif at < 2.6:
                t = 1.0
            else:
                t = max(0.0, 1.0 - (at - 2.6) / 0.4)
            extend = (1 - math.cos(t * math.pi)) / 2

            arm_reach = 14 * extend
            wiggle = math.sin(at * 4) * 2.5 * extend
            arm_y = cy + 10

            painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
            painter.setPen(QPen(QColor(180, 180, 200), 2))

            # Left arm
            lx = cx - 28 - arm_reach
            ly = arm_y + wiggle
            painter.drawEllipse(int(lx - 7), int(ly - 5), 14, 10)

            # Right arm
            rx = cx + 28 + arm_reach
            ry = arm_y - wiggle
            painter.drawEllipse(int(rx - 7), int(ry - 5), 14, 10)

        # Shadow
        painter.save()
        painter.translate(2, 3)
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
        painter.restore()

        # Body
        painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
        painter.setPen(QPen(QColor(180, 180, 200), 2))
        painter.drawPath(path)

        # Blush
        painter.setBrush(QBrush(QColor(255, 180, 180, 100)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - 28, cy + 5, 12, 8)
        painter.drawEllipse(cx + 16, cy + 5, 12, 8)

        # Eyes
        painter.setBrush(QBrush(QColor(40, 40, 40)))
        if self._blinking and self._blink_style == "squint":
            # (><) squint eyes
            painter.setPen(QPen(QColor(40, 40, 40), 2.5))
            painter.setBrush(Qt.NoBrush)
            # Left eye: >
            painter.drawLine(cx - 15, cy - 5, cx - 8, cy)
            painter.drawLine(cx - 15, cy + 5, cx - 8, cy)
            # Right eye: <
            painter.drawLine(cx + 15, cy - 5, cx + 8, cy)
            painter.drawLine(cx + 15, cy + 5, cx + 8, cy)
            painter.setPen(Qt.NoPen)
        elif self._blinking:
            # Closed eyes — horizontal lines
            painter.setPen(QPen(QColor(40, 40, 40), 2))
            painter.drawLine(cx - 15, cy, cx - 5, cy)
            painter.drawLine(cx + 5, cy, cx + 15, cy)
            painter.setPen(Qt.NoPen)
        else:
            painter.drawEllipse(cx - 15, cy - 8, 10, 14)
            painter.drawEllipse(cx + 5, cy - 8, 10, 14)

            # Eye shine
            painter.setBrush(QBrush(QColor(255, 255, 255)))
            painter.drawEllipse(cx - 13, cy - 5, 4, 4)
            painter.drawEllipse(cx + 7, cy - 5, 4, 4)

            # Sparkle effect
            if self._sparkle_active:
                st = (time.time() - self._sparkle_start) * 4
                painter.setPen(QPen(QColor(255, 255, 100), 1.5))
                painter.setBrush(Qt.NoBrush)
                for ex in (cx - 10, cx + 10):
                    ey = cy - 1
                    sz = 6 + math.sin(st) * 2
                    # Four-point star
                    star = QPainterPath()
                    star.moveTo(ex, ey - sz)
                    star.lineTo(ex + sz * 0.3, ey - sz * 0.3)
                    star.lineTo(ex + sz, ey)
                    star.lineTo(ex + sz * 0.3, ey + sz * 0.3)
                    star.lineTo(ex, ey + sz)
                    star.lineTo(ex - sz * 0.3, ey + sz * 0.3)
                    star.lineTo(ex - sz, ey)
                    star.lineTo(ex - sz * 0.3, ey - sz * 0.3)
                    star.closeSubpath()
                    painter.drawPath(star)
                # Extra tiny sparkle dots
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(255, 255, 200)))
                for i, (dx, dy) in enumerate([(-18, -10), (18, -12), (-14, 8), (16, 6)]):
                    a = math.sin(st * 1.5 + i * 1.7)
                    if a > 0:
                        r = 1 + a * 1.5
                        painter.drawEllipse(
                            int(cx + dx - r), int(cy + dy - r),
                            int(r * 2), int(r * 2))

        # Mouth
        if self._mouth == "O":
            # Surprised "O" mouth with shake
            mt = time.time() - self._mouth_start
            shake_x = math.sin(mt * 25) * 1.5
            shake_y = math.cos(mt * 30) * 1.0
            painter.setPen(QPen(QColor(80, 80, 80), 2))
            painter.setBrush(QBrush(QColor(220, 100, 100, 140)))
            painter.drawEllipse(
                int(cx - 4 + shake_x), int(cy + 13 + shake_y), 8, 10)
        elif self._mouth == "happy":
            # Big happy grin — D rotated 90° clockwise (flat top, round bottom)
            painter.setPen(QPen(QColor(80, 80, 80), 2))
            painter.setBrush(QBrush(QColor(220, 100, 100, 140)))
            grin = QPainterPath()
            grin.moveTo(cx - 6, cy + 15)
            grin.lineTo(cx + 6, cy + 15)
            grin.quadTo(cx + 8, cy + 22, cx, cy + 24)
            grin.quadTo(cx - 8, cy + 22, cx - 6, cy + 15)
            painter.drawPath(grin)
        else:
            # Normal small smile
            painter.setPen(QPen(QColor(80, 80, 80), 2))
            painter.setBrush(Qt.NoBrush)
            mouth = QPainterPath()
            mouth.moveTo(cx - 5, cy + 15)
            mouth.quadTo(cx, cy + 20, cx + 5, cy + 15)
            painter.drawPath(mouth)

        painter.restore()


def _create_tray_icon():
    """Create a simple ghost icon for the system tray."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.Antialiasing)

    # Ghost shape
    path = QPainterPath()
    path.moveTo(6, 28)
    path.quadTo(4, 16, 6, 8)
    path.quadTo(8, 2, 16, 2)
    path.quadTo(24, 2, 26, 8)
    path.quadTo(28, 16, 26, 28)
    path.quadTo(23, 24, 20, 28)
    path.quadTo(17, 24, 16, 28)
    path.quadTo(13, 24, 12, 28)
    path.quadTo(9, 24, 6, 28)

    p.setBrush(QBrush(QColor(255, 255, 255)))
    p.setPen(QPen(QColor(180, 180, 200), 1.5))
    p.drawPath(path)

    # Eyes
    p.setBrush(QBrush(QColor(40, 40, 40)))
    p.setPen(Qt.NoPen)
    p.drawEllipse(10, 11, 4, 6)
    p.drawEllipse(18, 11, 4, 6)

    # Eye shine
    p.setBrush(QBrush(QColor(255, 255, 255)))
    p.drawEllipse(11, 12, 2, 2)
    p.drawEllipse(19, 12, 2, 2)

    p.end()
    return QIcon(pixmap)


def main():
    parser = argparse.ArgumentParser(description="Cute Ghost Desktop Pet")
    parser.add_argument(
        "--monitors", metavar="MANUFACTURER",
        help="only use monitors matching this manufacturer substring "
             "(e.g. --monitors Samsung). Default: all monitors.",
    )
    args, remaining = parser.parse_known_args()

    app = QApplication(remaining)
    app.setQuitOnLastWindowClosed(False)

    config = Config()
    ghost = GhostPet(config=config, monitor_filter=args.monitors)
    ghost.show()

    # System tray icon
    tray = QSystemTrayIcon(_create_tray_icon(), app)
    tray.setToolTip("Ghost Pet")

    menu = QMenu()
    settings_action = menu.addAction("Settings")
    scare_action = menu.addAction("Scare now!")
    menu.addSeparator()
    quit_action = menu.addAction("Quit")

    _settings_dialog = None

    def open_settings():
        nonlocal _settings_dialog
        from settings_dialog import SettingsDialog
        if _settings_dialog is not None and _settings_dialog.isVisible():
            _settings_dialog.raise_()
            _settings_dialog.activateWindow()
            return
        _settings_dialog = SettingsDialog(ghost, config)
        _settings_dialog.show()

    settings_action.triggered.connect(open_settings)
    scare_action.triggered.connect(ghost._do_scare)
    quit_action.triggered.connect(app.quit)

    tray.setContextMenu(menu)
    tray.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
