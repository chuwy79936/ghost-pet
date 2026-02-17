"""Settings dialog for Ghost Pet."""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QSlider,
    QCheckBox, QPlainTextEdit, QPushButton, QScrollArea, QWidget,
)
from PyQt5.QtCore import Qt


class SettingsDialog(QDialog):
    """Settings dialog for configuring the ghost pet."""

    def __init__(self, ghost, config, parent=None):
        super().__init__(parent)
        self.ghost = ghost
        self.config = config
        self.setWindowTitle("Ghost Pet Settings")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # ── Movement ──
        movement_group = QGroupBox("Movement")
        movement_layout = QVBoxLayout(movement_group)
        self.speed_slider = self._add_slider(
            movement_layout, "Speed", 1, 20, config.speed)
        scroll_layout.addWidget(movement_group)

        # ── Speech ──
        speech_group = QGroupBox("Speech")
        speech_layout = QVBoxLayout(speech_group)
        self.interval_slider = self._add_slider(
            speech_layout, "Speak interval (seconds)", 5, 60,
            config.speak_interval)
        self.chance_slider = self._add_slider(
            speech_layout, "Speak chance (%)", 0, 100,
            int(config.speak_chance * 100))
        speech_layout.addWidget(QLabel("Custom phrases (one per line):"))
        self.phrases_text = QPlainTextEdit()
        self.phrases_text.setMaximumHeight(100)
        self.phrases_text.setPlainText("\n".join(config.custom_phrases))
        speech_layout.addWidget(self.phrases_text)
        scroll_layout.addWidget(speech_group)

        # ── Opacity ──
        opacity_group = QGroupBox("Opacity")
        opacity_layout = QVBoxLayout(opacity_group)
        self.opacity_speed_slider = self._add_float_slider(
            opacity_layout, "Opacity speed", 1, 30, config.opacity_speed, 10)
        self.opacity_min_slider = self._add_slider(
            opacity_layout, "Minimum opacity (%)", 0, 100,
            int(config.opacity_min * 100))
        self.opacity_max_slider = self._add_slider(
            opacity_layout, "Maximum opacity (%)", 0, 100,
            int(config.opacity_max * 100))
        scroll_layout.addWidget(opacity_group)

        # ── Scare ──
        scare_group = QGroupBox("Scare")
        scare_layout = QVBoxLayout(scare_group)
        self.scare_enabled_cb = QCheckBox("Enable scare mode")
        self.scare_enabled_cb.setChecked(config.scare_enabled)
        scare_layout.addWidget(self.scare_enabled_cb)
        self.scare_min_slider = self._add_slider(
            scare_layout, "Minimum minutes between scares", 1, 30,
            config.scare_min_minutes)
        self.scare_max_slider = self._add_slider(
            scare_layout, "Maximum minutes between scares", 1, 30,
            config.scare_max_minutes)
        scare_layout.addWidget(QLabel("Custom scare phrases (one per line):"))
        self.scare_phrases_text = QPlainTextEdit()
        self.scare_phrases_text.setMaximumHeight(100)
        self.scare_phrases_text.setPlainText(
            "\n".join(config.custom_scare_phrases))
        scare_layout.addWidget(self.scare_phrases_text)
        scroll_layout.addWidget(scare_group)

        # ── Appearance ──
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QVBoxLayout(appearance_group)
        self.scale_slider = self._add_float_slider(
            appearance_layout, "Ghost scale", 5, 30, config.ghost_scale, 10)
        scroll_layout.addWidget(appearance_group)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # ── Buttons ──
        button_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(apply_btn)
        layout.addLayout(button_layout)

    # ── helpers ───────────────────────────────────────────────────

    def _add_slider(self, layout, label, min_val, max_val, value):
        lbl = QLabel(f"{label}: {value}")
        layout.addWidget(lbl)
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(value)
        slider.valueChanged.connect(
            lambda v: lbl.setText(f"{label}: {v}"))
        layout.addWidget(slider)
        return slider

    def _add_float_slider(self, layout, label, min_val, max_val, value,
                          divisor):
        lbl = QLabel(f"{label}: {value:.1f}")
        layout.addWidget(lbl)
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(int(value * divisor))
        slider._divisor = divisor
        slider.valueChanged.connect(
            lambda v: lbl.setText(f"{label}: {v / divisor:.1f}"))
        layout.addWidget(slider)
        return slider

    # ── actions ───────────────────────────────────────────────────

    def _parse_lines(self, text_edit):
        text = text_edit.toPlainText().strip()
        if not text:
            return []
        return [line.strip() for line in text.split("\n") if line.strip()]

    def _apply(self):
        self.config.speed = self.speed_slider.value()
        self.config.speak_interval = self.interval_slider.value()
        self.config.speak_chance = self.chance_slider.value() / 100.0
        self.config.opacity_speed = (
            self.opacity_speed_slider.value()
            / self.opacity_speed_slider._divisor)
        self.config.opacity_min = self.opacity_min_slider.value() / 100.0
        self.config.opacity_max = self.opacity_max_slider.value() / 100.0
        self.config.scare_enabled = self.scare_enabled_cb.isChecked()
        self.config.scare_min_minutes = self.scare_min_slider.value()
        self.config.scare_max_minutes = self.scare_max_slider.value()
        self.config.ghost_scale = (
            self.scale_slider.value() / self.scale_slider._divisor)
        self.config.custom_phrases = self._parse_lines(self.phrases_text)
        self.config.custom_scare_phrases = self._parse_lines(
            self.scare_phrases_text)

        self.config.save()
        self.ghost.apply_config()

    def _reset_defaults(self):
        self.config.reset()
        self.speed_slider.setValue(self.config.speed)
        self.interval_slider.setValue(self.config.speak_interval)
        self.chance_slider.setValue(int(self.config.speak_chance * 100))
        self.opacity_speed_slider.setValue(
            int(self.config.opacity_speed
                * self.opacity_speed_slider._divisor))
        self.opacity_min_slider.setValue(
            int(self.config.opacity_min * 100))
        self.opacity_max_slider.setValue(
            int(self.config.opacity_max * 100))
        self.scare_enabled_cb.setChecked(self.config.scare_enabled)
        self.scare_min_slider.setValue(self.config.scare_min_minutes)
        self.scare_max_slider.setValue(self.config.scare_max_minutes)
        self.scale_slider.setValue(
            int(self.config.ghost_scale * self.scale_slider._divisor))
        self.phrases_text.setPlainText("")
        self.scare_phrases_text.setPlainText("")

        self.config.save()
        self.ghost.apply_config()
