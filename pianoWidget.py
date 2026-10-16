#!/usr/bin/env python3
"""
Module Name: pianoWidget.py
Description: Widget for piano visualization in GUI
Author: Carson Towns
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

WHITE_PCS = {0, 2, 4, 5, 7, 9, 11}
BLACK_PCS = {1, 3, 6, 8, 10}


class PianoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.low_midi = 48   # C3
        self.high_midi = 84  # C6
        self.notes = []      # [{"midi": 60, "name": "C", "degree": "1"}]
        self.setMinimumHeight(170)

    def set_notes(self, notes):
        self.notes = notes or []
        self.update()

    def set_voicing(self, voicing):
        notes = []
        for (degree, name, _pc), midi in zip(voicing.notes, voicing.pitches):
            notes.append({
                "midi": midi,
                "name": name,
                "degree": degree,
            })
        self.set_notes(notes)

    def clear(self):
        self.set_notes([])

    def color_for_degree(self, degree):
        if degree == "1":
            return QColor("#4A90E2")   # root
        if degree in {"3", "7", "6"}:
            return QColor("#E6A23C")   # guide tones
        return QColor("#67C23A")       # other tones/extensions

    def is_white(self, midi):
        return midi % 12 in WHITE_PCS

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(8, 8, -8, -8)
        painter.fillRect(rect, QColor("#F5F5F5"))

        white_keys = [m for m in range(self.low_midi, self.high_midi + 1) if self.is_white(m)]
        if not white_keys:
            return

        white_w = rect.width() / len(white_keys)
        white_h = rect.height()

        white_positions = {}
        active_by_midi = {note["midi"]: note for note in self.notes}

        x = rect.left()

        # Draw white keys first
        for midi in white_keys:
            key_rect = QRectF(x, rect.top(), white_w, white_h)
            white_positions[midi] = key_rect

            active = active_by_midi.get(midi)
            fill = self.color_for_degree(active["degree"]) if active else Qt.white

            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(fill)
            painter.drawRect(key_rect)

            if active:
                painter.setPen(Qt.black)
                painter.setFont(QFont("Arial", 8))
                painter.drawText(
                    key_rect.adjusted(2, 2, -2, -22),
                    Qt.AlignTop | Qt.AlignHCenter,
                    active["name"],
                )
                painter.drawText(
                    key_rect.adjusted(2, 20, -2, -2),
                    Qt.AlignBottom | Qt.AlignHCenter,
                    active["degree"],
                )

            x += white_w

        # Draw black keys on top
        black_w = white_w * 0.65
        black_h = white_h * 0.62

        for midi in range(self.low_midi, self.high_midi + 1):
            if midi % 12 not in BLACK_PCS:
                continue

            prev_white = midi - 1
            next_white = midi + 1
            if prev_white not in white_positions or next_white not in white_positions:
                continue

            left_rect = white_positions[prev_white]
            key_x = left_rect.right() - black_w / 2
            key_rect = QRectF(key_x, rect.top(), black_w, black_h)

            active = active_by_midi.get(midi)
            fill = self.color_for_degree(active["degree"]) if active else QColor("#111111")

            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(fill)
            painter.drawRect(key_rect)

            if active:
                painter.setPen(Qt.white)
                painter.setFont(QFont("Arial", 7))
                painter.drawText(
                    key_rect.adjusted(1, 1, -1, -12),
                    Qt.AlignTop | Qt.AlignHCenter,
                    active["name"],
                )
                painter.drawText(
                    key_rect.adjusted(1, 10, -1, -1),
                    Qt.AlignBottom | Qt.AlignHCenter,
                    active["degree"],
                )

        # Border
        painter.setPen(QPen(QColor("#888888"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect)
