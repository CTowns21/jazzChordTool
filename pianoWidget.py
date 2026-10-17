#!/usr/bin/env python3
"""
Module Name: pianoWidget.py
Description: Widget for piano visualization in GUI
Author: Carson Towns
"""

import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

WHITE_PCS = {0, 2, 4, 5, 7, 9, 11}
BLACK_PCS = {1, 3, 6, 8, 10}


class PianoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_low_midi = 48   # C3
        self.default_high_midi = 84  # C6
        self.low_midi = self.default_low_midi
        self.high_midi = self.default_high_midi
        self.notes = []      # [{"midi": 60, "name": "C", "degree": "1"}]
        self.previous_notes = []
        self.setMinimumSize(0, 210)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_notes(self, notes, previous_notes=None):
        self.notes = notes or []
        self.previous_notes = previous_notes or []
        visible_notes = self.notes + self.previous_notes
        if visible_notes:
            self._center_range_on_notes(visible_notes)
        else:
            self.low_midi = self.default_low_midi
            self.high_midi = self.default_high_midi
        self.update()

    def _center_range_on_notes(self, notes):
        pitches = [note["midi"] for note in notes]
        lowest = min(pitches)
        highest = max(pitches)
        octaves = max(1, math.ceil((highest - lowest + 12) / 12))
        range_size = octaves * 12

        desired_low = (lowest + highest - range_size) / 2
        low_midi = round(desired_low / 12) * 12
        while lowest < low_midi:
            low_midi -= 12
        while highest > low_midi + range_size:
            low_midi += 12

        self.low_midi = low_midi
        self.high_midi = low_midi + range_size

    def set_voicing(self, voicing, previous_voicing=None):
        notes = []
        for (degree, name, _), midi in zip(voicing.notes, voicing.pitches):
            notes.append({
                "midi": midi,
                "name": name,
                "degree": degree,
            })
        previous_notes = []
        if previous_voicing is not None:
            for (degree, name, _), midi in zip(
                previous_voicing.notes,
                previous_voicing.pitches,
            ):
                previous_notes.append({
                    "midi": midi,
                    "name": name,
                    "degree": degree,
                })
        self.set_notes(notes, previous_notes)

    def clear(self):
        self.set_notes([])

    def color_for_previous_note(self, midi):
        return QColor("#B8B8B8") if self.is_white(midi) else QColor("#666666")

    def label_color_for_previous_note(self, midi):
        return Qt.black if self.is_white(midi) else QColor("#F2F2F2")

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

        white_keys = [
            midi for midi in range(self.low_midi, self.high_midi + 1)
            if self.is_white(midi)
        ]
        if not white_keys:
            painter.end()
            return

        white_w = rect.width() / len(white_keys)
        white_h = rect.height()
        black_w = white_w * 0.65
        black_h = white_h * 0.62

        # Scale labels with key dimensions; clamp sizes to keep them legible.
        scale = min(white_w / 25, white_h / 150)
        white_name_px = max(12, min(26, round(15 * scale)))
        white_degree_px = max(10, min(22, round(13 * scale)))
        black_name_px = max(10, min(17, round(12 * scale)))
        black_degree_px = max(9, min(15, round(11 * scale)))

        white_name_h = white_name_px + 5
        white_degree_h = white_degree_px + 5
        black_name_h = black_name_px + 4
        black_degree_h = black_degree_px + 4

        white_positions = {}
        active_by_midi = {note["midi"]: note for note in self.notes}
        previous_by_midi = {
            note["midi"]: note for note in self.previous_notes
            if note["midi"] not in active_by_midi
        }

        # Draw white keys and their labels first.
        x = rect.left()
        for midi in white_keys:
            key_rect = QRectF(x, rect.top(), white_w, white_h)
            white_positions[midi] = key_rect

            active = active_by_midi.get(midi)
            previous = previous_by_midi.get(midi)
            if active:
                fill = self.color_for_degree(active["degree"])
            elif previous:
                fill = self.color_for_previous_note(midi)
            else:
                fill = Qt.white

            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(fill)
            painter.drawRect(key_rect)

            # For white keys, draw the name and degree labels below the key
            if active or previous:
                note = active or previous
                label_top = rect.top() + black_h + 8

                name_font = QFont("Arial")
                name_font.setPixelSize(white_name_px)
                name_font.setBold(True)
                painter.setFont(name_font)
                label_color = (
                    Qt.black
                    if active
                    else self.label_color_for_previous_note(midi)
                )
                painter.setPen(label_color)
                painter.drawText(
                    QRectF(
                        key_rect.left() + 1, label_top,
                        key_rect.width() - 2, white_name_h,
                    ),
                    Qt.AlignCenter,
                    note["name"],
                )

                degree_font = QFont("Arial")
                degree_font.setPixelSize(white_degree_px)
                degree_font.setBold(True)
                painter.setFont(degree_font)
                painter.drawText(
                    QRectF(
                        key_rect.left() + 1, label_top + white_name_h,
                        key_rect.width() - 2, white_degree_h,
                    ),
                    Qt.AlignCenter,
                    note["degree"],
                )

            x += white_w

        # Draw black keys on top of the white keys.
        for midi in range(self.low_midi, self.high_midi + 1):
            if midi % 12 not in BLACK_PCS:
                continue

            prev_white = midi - 1
            if prev_white not in white_positions or midi + 1 not in white_positions:
                continue

            left_rect = white_positions[prev_white]
            key_x = left_rect.right() - black_w / 2
            key_rect = QRectF(key_x, rect.top(), black_w, black_h)

            active = active_by_midi.get(midi)
            previous = previous_by_midi.get(midi)
            if active:
                fill = self.color_for_degree(active["degree"])
            elif previous:
                fill = self.color_for_previous_note(midi)
            else:
                fill = QColor("#111111")

            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(fill)
            painter.drawRect(key_rect)

            # For black keys, draw the name and degree labels inside the key
            if active or previous:
                note = active or previous
                label_top = key_rect.top() + black_h/2

                name_font = QFont("Arial")
                name_font.setPixelSize(black_name_px)
                name_font.setBold(True)
                painter.setFont(name_font)
                label_color = (
                    Qt.black
                    if active
                    else self.label_color_for_previous_note(midi)
                )
                painter.setPen(label_color)
                painter.drawText(
                    QRectF(
                        key_rect.left() + 1,
                        label_top,
                        key_rect.width() - 2,
                        black_name_h,
                    ),
                    Qt.AlignCenter,
                    note["name"],
                )

                degree_font = QFont("Arial")
                degree_font.setPixelSize(black_degree_px)
                degree_font.setBold(True)
                painter.setFont(degree_font)
                painter.drawText(
                    QRectF(
                        key_rect.left() + 1,
                        label_top + black_name_h,
                        key_rect.width() - 2,
                        black_degree_h,
                    ),
                    Qt.AlignCenter,
                    note["degree"],
                )

        # Draw the piano's outer border.
        painter.setPen(QPen(QColor("#888888"), 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(rect)