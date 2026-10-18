#!/usr/bin/env python3
"""
Module Name: sessionModel.py
Description: Handles session info for jazzChordTool
Author: Carson Towns
"""

from dataclasses import dataclass, field

from chordParser import ACC_TEXT, bassName, parseChordSymbol
from voicingEngine import (
    GUIDE_DEGREES,
    STYLES,
    availableVoicings,
    chooseVoicings,
    matchLabel,
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

    def addChord(self, symbol_text, pin_text=None, pin_style=None):
        chord = parseChordSymbol(symbol_text.strip())
        self.chords.append(chord)
        self.pins.append(None)
        if pin_text:
            try:
                self.pinChord(len(self.chords) - 1, pin_text, pin_style)
            except ValueError:
                self.chords.pop()
                self.pins.pop()
                raise

    def removeLast(self):
        if self.chords:
            self.chords.pop()
            self.pins.pop()

    def deleteAt(self, index):
        if not (0 <= index < len(self.chords)):
            raise IndexError("Chord index out of range")
        del self.chords[index]
        del self.pins[index]

    def pinChord(self, index, label_text, style_name=None):
        if not (0 <= index < len(self.chords)):
            raise IndexError("Chord index out of range")
        if style_name is not None and style_name not in STYLES:
            raise ValueError(f"Unknown style: {style_name}")

        chord = self.chords[index]
        options = [
            (candidate_style, voicing.label)
            for candidate_style, voicing in availableVoicings(chord)
            if style_name is None or candidate_style == style_name
        ]
        labels = list(dict.fromkeys(label for _, label in options))
        label = matchLabel(label_text, labels)
        matching_styles = [
            candidate_style
            for candidate_style, candidate_label in options
            if candidate_label == label
        ]
        if label is None or not matching_styles:
            option_text = ", ".join(labels)
            raise ValueError(
                f"Can't pin '{label_text}' on {chord.symbol}. "
                f"Options: {option_text}"
            )

        self.pins[index] = (style_name or matching_styles[0], label)

    def unpinChord(self, index):
        if not (0 <= index < len(self.chords)):
            raise IndexError("Chord index out of range")
        self.pins[index] = None

    def voicings(self):
        return chooseVoicings(self.chords, self.pins)

    def availableVoicingsFor(self, index):
        if not (0 <= index < len(self.chords)):
            raise IndexError("Chord index out of range")
        return availableVoicings(self.chords[index])

    def renderRows(self, voicings=None):
        if voicings == None:
            voicings = self.voicings()
        rows = []

        for i, (chord, pin, voicing) in enumerate(zip(self.chords, self.pins, voicings), start=1):
            rows.append({
                "index": i,
                "symbol": chord.symbol,
                "bass": bassOf(chord),
                "voicing": f"{voicing.style.name} - {voicing.label}",
                "notes": formatVoicing(voicing),
                "pinned": bool(pin),
            })

        return rows
