#!/usr/bin/env python3
"""Grand-staff view and note-role labels for a chord voicing."""

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from chordParser import LETTERS

NOTE_PATTERN = re.compile(r"^([A-G])([#b]*)$")
DEGREE_NAMES = {
    "1": "Root",
    "3": "3rd",
    "5": "5th",
    "6": "6th",
    "7": "7th",
    "9": "9th",
    "11": "11th",
    "13": "13th",
    "bass": "Bass",
}
INTERVAL_BASES = {
    "1": (1, 0, "perfect"),
    "3": (3, 4, "major"),
    "5": (5, 7, "perfect"),
    "6": (6, 9, "major"),
    "7": (7, 11, "major"),
    "9": (9, 14, "major"),
    "11": (11, 17, "perfect"),
    "13": (13, 21, "major"),
}
INTERVAL_QUALITIES = {
    "perfect": {0: "P", -1: "d", 1: "A"},
    "major": {0: "M", -1: "m", -2: "d", 1: "A"},
}
DEGREE_COLORS = {
    "1": QColor("#4A90E2"),
    "3": QColor("#E6A23C"),
    "7": QColor("#E6A23C"),
    "6": QColor("#E6A23C"),
}
def interval_name(degree, pitch_class, root_pitch_class):
    if degree not in INTERVAL_BASES:
        return f"{(pitch_class - root_pitch_class) % 12} semitones"

    number, base_semitones, interval_type = INTERVAL_BASES[degree]
    actual_semitones = (pitch_class - root_pitch_class) % 12
    actual_semitones += 12 * round(
        (base_semitones - actual_semitones) / 12
    )
    alteration = actual_semitones - base_semitones
    quality = INTERVAL_QUALITIES[interval_type].get(alteration)
    return f"{quality}{number}" if quality else f"{actual_semitones} semitones"


class StaffWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.notes = []
        self.note_summary = "Select a chord to see its notes and intervals."
        self.setMinimumSize(300, 205)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_voicing(self, voicing, chord):
        self.notes = self._notes_for_voicing(voicing, chord)
        self._update_summary()
        self.update()

    def clear(self):
        self.notes = []
        self.note_summary = "Select a chord to see its notes and intervals."
        self.update()

    @staticmethod
    def _notes_for_voicing(voicing, chord):
        notes = []
        for (degree, name, pitch_class), midi in zip(
            voicing.notes,
            voicing.pitches,
        ):
            notes.append({
                "degree": degree,
                "name": name,
                "midi": midi,
                "pitch_class": pitch_class,
                "role": DEGREE_NAMES.get(degree, degree),
                "interval": interval_name(
                    degree,
                    pitch_class,
                    chord.rootPc,
                ),
            })
        return notes

    def _update_summary(self):
        self.note_summary = "   ".join(
            f"{note['name']}{note['midi'] // 12 - 1}: "
            f"{note['role']} ({note['interval']})"
            for note in self.notes
        )

    @staticmethod
    def _diatonic_index(note_name, midi):
        match = NOTE_PATTERN.match(note_name)
        if not match:
            return None
        letter, _ = match.groups()
        octave = midi // 12 - 1
        return octave * 7 + LETTERS.index(letter)

    @staticmethod
    def _color_for_degree(degree):
        return DEGREE_COLORS.get(degree, QColor("#67C23A"))

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#F5F5F5"))

        left = 54
        right = self.width() - 10
        if right <= left:
            painter.end()
            return

        treble_top = 24
        line_spacing = 8
        bass_top = 87
        staff_color = QColor("#333333")
        painter.setPen(QPen(staff_color, 1))

        for top in (treble_top, bass_top):
            for line in range(5):
                y = top + line * line_spacing
                painter.drawLine(left, y, right, y)

        clef_font = QFont("Segoe UI Symbol")
        clef_font.setPixelSize(29)
        painter.setFont(clef_font)
        painter.drawText(8, treble_top + 35, "𝄞")
        painter.drawText(8, bass_top + 31, "𝄢")

        self._draw_notes(
            painter,
            left,
            right,
            treble_top,
            bass_top,
            line_spacing,
        )

        summary_top = bass_top + 4 * line_spacing + 18
        summary_rect = self.rect().adjusted(
            8,
            summary_top,
            -8,
            -4,
        )
        summary_font = QFont("Arial")
        summary_font.setPixelSize(11)
        painter.setFont(summary_font)
        painter.setPen(QColor("#222222"))
        painter.drawText(
            summary_rect,
            Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
            self.note_summary,
        )
        painter.end()

    def _draw_notes(
        self,
        painter,
        left,
        right,
        treble_top,
        bass_top,
        line_spacing,
    ):
        if not self.notes:
            return

        step_size = line_spacing / 2
        treble_bottom = treble_top + 4 * line_spacing
        bass_bottom = bass_top + 4 * line_spacing
        treble_reference = 4 * 7 + LETTERS.index("E")
        bass_reference = 2 * 7 + LETTERS.index("G")

        for index, note in enumerate(self.notes):
            diatonic_index = self._diatonic_index(
                note["name"],
                note["midi"],
            )
            if diatonic_index is None:
                continue

            is_treble = note["midi"] >= 60
            staff_top = treble_top if is_treble else bass_top
            staff_bottom = treble_bottom if is_treble else bass_bottom
            reference = treble_reference if is_treble else bass_reference
            staff_steps = diatonic_index - reference
            y = staff_bottom - staff_steps * step_size
            x = left + (right - left) * (index + 0.5) / len(self.notes)
            color = self._color_for_degree(note["degree"])

            self._draw_ledger_lines(
                painter,
                x,
                staff_top,
                staff_bottom,
                staff_steps,
                step_size,
            )

            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(color)
            painter.drawEllipse(int(x - 7), int(y - 4.5), 14, 9)

            stem_x = x + 6 if staff_steps < 4 else x - 6
            stem_end = y - 25 if staff_steps < 4 else y + 25
            painter.drawLine(int(stem_x), int(y), int(stem_x), int(stem_end))

            match = NOTE_PATTERN.match(note["name"])
            if match and match.group(2):
                accidental = match.group(2).replace("#", "♯").replace("b", "♭")
                accidental_font = QFont("Segoe UI Symbol")
                accidental_font.setPixelSize(17)
                painter.setFont(accidental_font)
                painter.drawText(int(x - 23), int(y + 6), accidental)

    @staticmethod
    def _draw_ledger_lines(
        painter,
        x,
        staff_top,
        staff_bottom,
        staff_steps,
        step_size,
    ):
        if staff_steps > 8:
            steps = range(10, staff_steps + 1, 2)
        elif staff_steps < 0:
            steps = range(-2, staff_steps - 1, -2)
        else:
            return

        for step in steps:
            ledger_y = staff_bottom - step * step_size
            if ledger_y < staff_top or ledger_y > staff_bottom:
                painter.drawLine(
                    int(x - 11),
                    int(ledger_y),
                    int(x + 11),
                    int(ledger_y),
                )
