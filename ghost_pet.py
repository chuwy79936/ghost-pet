#!/usr/bin/env python3
"""
Cute Ghost Desktop Pet
A friendly ghost that floats around your desktop and says cute things!
"""

import argparse
import os
os.environ["QT_QPA_PLATFORM"] = "xcb"

import sys
import random
import math
import time
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QPainterPath, QFont, QBrush, QPen


class GhostPet(QWidget):
    """A cute floating ghost desktop pet."""

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

    def __init__(self, monitor_filter=None):
        super().__init__()

        # Base flags (behind other windows)
        self._base_flags = (
            Qt.FramelessWindowHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )
        # Scare flags (on top of everything)
        self._top_flags = (
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowTransparentForInput
        )

        self._scare_active = False

        # Start in background mode
        self.setWindowFlags(self._base_flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Widget large enough for ghost (80x120) + speech bubble above
        self.setFixedSize(220, 210)

        # Where the ghost body is drawn within the widget
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
        self.speak_timer.start(15000)

        # Scare timer — pop up on top every 5-10 minutes
        self._scare_timer = QTimer(self)
        self._scare_timer.setSingleShot(True)
        self._scare_timer.timeout.connect(self._start_scare)
        self._schedule_next_scare()

        # Initial destination
        self._pick_new_destination()

        # Say hello!
        QTimer.singleShot(1000, lambda: self._say_phrase("Boo! I'm your new friend!"))

    # ── positioning ──────────────────────────────────────────────

    def _update_widget_pos(self):
        """Position widget so ghost body center aligns with current_x/y."""
        wx = int(self.current_x - self._ghost_ox - 40)
        wy = int(self.current_y - self._ghost_oy - 50 + self._float_offset)
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
        if not self._phrase_queue:
            self._phrase_queue = random.sample(self.PHRASES, len(self.PHRASES))
        return self._phrase_queue.pop()

    def _say_random_phrase(self):
        if random.random() < 0.7:
            self._say_phrase(self._next_phrase())

    # ── animation ────────────────────────────────────────────────

    def _update_float(self):
        t = time.time()
        self._float_offset = math.sin(t * 2) * 5

        # Ghostly opacity — skip during scare (stay fully visible)
        if not self._scare_active:
            p = self._opacity_phases
            wave = (math.sin(t * 0.3 + p[0]) * 0.35 +
                    math.sin(t * 0.7 + p[1]) * 0.25 +
                    math.sin(t * 1.1 + p[2]) * 0.15)
            self._opacity = max(0.08, min(1.0, 0.55 + wave))
            self.setWindowOpacity(self._opacity)

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

        speed = 2
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

    # ── scare ────────────────────────────────────────────────────

    def _schedule_next_scare(self):
        delay = random.randint(5 * 60 * 1000, 10 * 60 * 1000)  # 5-10 minutes
        self._scare_timer.start(delay)

    def _apply_flags(self, flags):
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.show()

    def _start_scare(self):
        self._scare_active = True
        self._scare_start = time.time()
        self._scare_duration = 5.0  # total seconds

        # Start fully transparent, pop to top
        self.setWindowOpacity(0.0)
        self._apply_flags(self._top_flags)

        # Say a scare phrase
        phrase = random.choice(self.SCARE_PHRASES)
        self._say_phrase(phrase)

        # Tick the scare animation at 30fps
        self._scare_tick_timer = QTimer(self)
        self._scare_tick_timer.timeout.connect(self._scare_tick)
        self._scare_tick_timer.start(33)

    def _scare_tick(self):
        elapsed = time.time() - self._scare_start
        t = elapsed / self._scare_duration  # 0.0 → 1.0

        if t >= 1.0:
            # Done — fade complete, sink back
            self._scare_tick_timer.stop()
            self._scare_tick_timer.deleteLater()
            self.setWindowOpacity(0.0)
            self._apply_flags(self._base_flags)
            self._scare_active = False
            self._dismiss_bubble()
            self._schedule_next_scare()
            return

        # Fade curve: in for first 30%, hold for middle 40%, out for last 30%
        if t < 0.3:
            opacity = t / 0.3                 # 0 → 1
        elif t < 0.7:
            opacity = 1.0                      # hold at full
        else:
            opacity = 1.0 - (t - 0.7) / 0.3   # 1 → 0

        self.setWindowOpacity(opacity)

    # ── drawing ──────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # --- Speech bubble (drawn first, ghost overlaps slightly) ---
        if self._bubble_active:
            bw = min(self._bubble_width, self.width() - 10)
            bh = 60
            bx = (self.width() - bw) // 2
            by = 5

            path = QPainterPath()
            bubble_rect = QRect(bx + 5, by + 5, bw - 10, bh - 10)
            path.addRoundedRect(bubble_rect.x(), bubble_rect.y(),
                                bubble_rect.width(), bubble_rect.height(), 15, 15)

            # Tail pointing down toward ghost
            tail_x = self.width() // 2
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
        path.quadTo(cx + 22, wave_y + 12, cx + 15, wave_y)
        path.quadTo(cx + 7, wave_y - 10, cx, wave_y + 5)
        path.quadTo(cx - 7, wave_y + 15, cx - 15, wave_y)
        path.quadTo(cx - 22, wave_y - 8, cx - 30, wave_y)

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
        painter.drawEllipse(cx - 15, cy - 8, 10, 14)
        painter.drawEllipse(cx + 5, cy - 8, 10, 14)

        # Eye shine
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(cx - 13, cy - 5, 4, 4)
        painter.drawEllipse(cx + 7, cy - 5, 4, 4)

        # Mouth
        painter.setPen(QPen(QColor(80, 80, 80), 2))
        painter.setBrush(Qt.NoBrush)
        mouth = QPainterPath()
        mouth.moveTo(cx - 5, cy + 15)
        mouth.quadTo(cx, cy + 20, cx + 5, cy + 15)
        painter.drawPath(mouth)

        painter.restore()


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

    ghost = GhostPet(monitor_filter=args.monitors)
    ghost.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
