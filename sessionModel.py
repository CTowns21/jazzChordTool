#!/usr/bin/env python3
"""
Module Name: sessionModel.py
Description: Handles session info for jazzChordTool
Author: Carson Towns
"""

from dataclasses import dataclass, field

from chordParser import ACC_TEXT, bassName, parseChordSymbol
from voicingEngine import (
    DEFAULT_STYLE,
    GUIDE_DEGREES,
    STYLES,
    availableLabels,
    chooseVoicings,
    matchLabel,
    pinnedVoicings,
)


def formatVoicing(voicing):
    return " ".join(
        f"[{name}]" if degree in GUIDE_DEGREES else name
        for degree, name, _ in voicing.notes
    )


def bassOf(chord):
    return bassName(chord) or chord.rootLetter + ACC_TEXT[chord.rootAccidental]


@dataclass
class Session:
    chords: list = field(default_factory=list)
    pins: list = field(default_factory=list)
    styleName: str = DEFAULT_STYLE

    def addChord(self, symbol_text, pin_text=None):
        chord = parseChordSymbol(symbol_text.strip())

        pin = None
        if pin_text:
            pin = matchLabel(pin_text)
            if pin is None or not pinnedVoicings(chord, pin):
                options = ", ".join(availableLabels(chord))
                raise ValueError(f"Can't pin '{pin_text}' on {chord.symbol}. Options: {options}")

        self.chords.append(chord)
        self.pins.append(pin)

    def removeLast(self):
        if self.chords:
            self.chords.pop()
            self.pins.pop()

    def deleteAt(self, index):
        if not (0 <= index < len(self.chords)):
            raise IndexError("Chord index out of range")
        del self.chords[index]
        del self.pins[index]

    def pinChord(self, index, label_text):
        if not (0 <= index < len(self.chords)):
            raise IndexError("Chord index out of range")

        chord = self.chords[index]
        label = matchLabel(label_text)
        if label is None or not pinnedVoicings(chord, label):
            options = ", ".join(availableLabels(chord))
            raise ValueError(f"Can't pin that on {chord.symbol}. Options: {options}")

        self.pins[index] = label

    def unpinChord(self, index):
        if not (0 <= index < len(self.chords)):
            raise IndexError("Chord index out of range")
        self.pins[index] = None

    def setStyle(self, style_name):
        if style_name not in STYLES:
            raise ValueError(f"Unknown style: {style_name}")
        self.styleName = style_name

    def voicings(self):
        return chooseVoicings(self.chords, self.pins, STYLES[self.styleName])

    def availableLabelsFor(self, index):
        if not (0 <= index < len(self.chords)):
            raise IndexError("Chord index out of range")
        return availableLabels(self.chords[index])

    def renderRows(self):
        voicings = self.voicings()
        rows = []

        for i, (chord, pin, voicing) in enumerate(zip(self.chords, self.pins, voicings), start=1):
            rows.append({
                "index": i,
                "symbol": chord.symbol,
                "bass": bassOf(chord),
                "voicing": voicing.label,
                "notes": formatVoicing(voicing),
                "pinned": bool(pin),
            })

        return rows
