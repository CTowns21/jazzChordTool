#!/usr/bin/env python3
"""
Module Name: chordParser.py
Description: Chord symbol parser, letter-correct spelling, and voicing
             templates for jazzChordTool
Author: Carson Towns
"""

import re
from dataclasses import dataclass, replace

LETTERS = "CDEFGAB"
LETTER_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
ACC_TO_INT = {"": 0, "#": 1, "b": -1}
ACC_TEXT = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "##"}

DEGREE_LETTER_STEPS = {
    "1": 0, "3": 2, "5": 4, "6": 5, "7": 6,
    "9": 1, "11": 3, "13": 5
}
DEGREE_ORDER = ["1", "3", "5", "6", "7", "9", "11", "13"]
DEFAULT_9TH = 2

QUALITIES = {
    "major":   {"1": 0, "3": 4, "5": 7},
    "minor":   {"1": 0, "3": 3, "5": 7},
    "dim":     {"1": 0, "3": 3, "5": 6},
    "aug":     {"1": 0, "3": 4, "5": 8},
    "dom7":    {"1": 0, "3": 4, "5": 7, "7": 10},
    "maj7":    {"1": 0, "3": 4, "5": 7, "7": 11},
    "min7":    {"1": 0, "3": 3, "5": 7, "7": 10},
    "m7b5":    {"1": 0, "3": 3, "5": 6, "7": 10},
    "dim7":    {"1": 0, "3": 3, "5": 6, "7": 9},
    "aug7":    {"1": 0, "3": 4, "5": 8, "7": 10},
    "minMaj7": {"1": 0, "3": 3, "5": 7, "7": 11},
    "major6":  {"1": 0, "3": 4, "5": 7, "6": 9},
    "minor6":  {"1": 0, "3": 3, "5": 7, "6": 9},
    "sixNine": {"1": 0, "3": 4, "5": 7, "6": 9, "9": 2},
    "maj9":    {"1": 0, "3": 4, "5": 7, "7": 11, "9": 2},
    "dom9":    {"1": 0, "3": 4, "5": 7, "7": 10, "9": 2},
    "min9":    {"1": 0, "3": 3, "5": 7, "7": 10, "9": 2},
    "sus2":    {"1": 0, "5": 7, "9": 2},
    "sus4":    {"1": 0, "5": 7, "11": 5},
    "dom7sus4": {"1": 0, "5": 7, "7": 10, "11": 5},
    "dom9sus4": {"1": 0, "5": 7, "7": 10, "9": 2, "11": 5},
    "maj11":   {"1": 0, "3": 4, "5": 7, "7": 11, "9": 2, "11": 17},
    "dom11":   {"1": 0, "3": 4, "5": 7, "7": 10, "9": 2, "11": 17},
    "min11":   {"1": 0, "3": 3, "5": 7, "7": 10, "9": 2, "11": 17},
    "maj13":   {"1": 0, "3": 4, "5": 7, "7": 11, "9": 2, "11": 5, "13": 9},
    "dom13":   {"1": 0, "3": 4, "5": 7, "7": 10, "9": 2, "11": 5, "13": 9},
    "min13":   {"1": 0, "3": 3, "5": 7, "7": 10, "9": 2, "11": 5, "13": 9},
}

QUALITY_ALIASES = {
    "major":   ["", "maj", "major"],
    "minor":   ["m", "min", "minor", "-"],
    "dim":     ["o", "dim"],
    "aug":     ["+", "aug"],
    "dom7":    ["7"],
    "maj7":    ["maj7", "M7", "Maj7", "major7"],
    "min7":    ["m7", "min7", "minor7", "-7"],
    "m7b5":    ["m7b5", "min7b5", "-7b5", "ø", "ø7"],
    "dim7":    ["o7", "dim7"],
    "aug7":    ["+7", "aug7"],
    "minMaj7": ["mmaj7", "mM7", "minmaj7", "-maj7", "-M7"],
    "major6":  ["6", "maj6"],
    "minor6":  ["m6", "min6", "-6"],
    "sixNine": ["6/9", "69"],
    "maj9":    ["maj9", "M9"],
    "dom9":    ["9"],
    "min9":    ["m9", "min9", "-9"],
    "sus2":    ["sus2"],
    "sus4":    ["sus4", "sus"],
    "dom7sus4": ["7sus4", "7sus"],
    "dom9sus4": ["9sus4", "9sus"],
    "maj11":   ["maj11", "M11"],
    "dom11":   ["11"],
    "min11":   ["m11", "min11", "-11"],
    "maj13":   ["maj13", "M13"],
    "dom13":   ["13"],
    "min13":   ["m13", "min13", "-13"],
}

MODIFIERS = {
    "b9": ("9", 1), "#9": ("9", 3), "#11": ("11", 6), "b13": ("13", 8),
    "b5": ("5", 6), "#5": ("5", 8),
    "add9": ("9", 2), "add2": ("9", 2), "add11": ("11", 5),
    "add4": ("11", 5),
    "add13": ("13", 21),
}

VOICING_TEMPLATES = {
    "triad": ["1", "3", "5"],
    "shell": ["1", "3", "7"],
    "shellB": ["1", "7", "3"],
    "typeA": ["3", "5", "7", "9"],
    "typeB": ["7", "9", "3", "5"],
}

ALIAS_LIST = sorted(
    ((alias, name) for name, aliases in QUALITY_ALIASES.items() for alias in aliases),
    key=lambda pair: -len(pair[0]),
)
MODIFIER_LIST = sorted(MODIFIERS.items(), key=lambda item: -len(item[0]))

NOTE_RE = re.compile(r"^([A-G])([#b]?)$")
ROOT_RE = re.compile(r"^([A-G])([#b]?)(.*)$")


@dataclass
class Chord:
    symbol: str
    rootLetter: str
    rootAccidental: int
    quality: str
    degrees: dict
    bassLetter: str = None
    bassAccidental: int = 0

    @property
    def rootPc(self):
        return (LETTER_TO_PC[self.rootLetter] + self.rootAccidental) % 12


def normalizeSymbol(symbol):
    for old, new in [("♭", "b"), ("♯", "#"), ("°", "o"), ("Δ", "maj"),
                     ("(", ""), (")", ""), (" ", "")]:
        symbol = symbol.replace(old, new)
    return symbol


def splitSlash(symbol):
    head, sep, tail = symbol.rpartition("/")
    if sep and NOTE_RE.match(tail):
        return head, tail
    return symbol, None


def parseModifiers(text):
    found = []
    while text:
        for token, alteration in MODIFIER_LIST:
            if text.startswith(token):
                found.append(alteration)
                text = text[len(token):]
                break
        else:
            return None
    return found


def parseQuality(text):
    for alias, name in ALIAS_LIST:
        if text.startswith(alias):
            modifiers = parseModifiers(text[len(alias):])
            if modifiers is not None:
                degrees = dict(QUALITIES[name])
                degrees.update(modifiers)
                return name, degrees
    raise ValueError(f"Unsupported chord quality: '{text}'")


def parseChordSymbol(symbol):
    cleaned = normalizeSymbol(symbol.strip())
    if not cleaned:
        raise ValueError("Chord symbol cannot be empty")

    head, bassText = splitSlash(cleaned)

    match = ROOT_RE.match(head)
    if not match:
        raise ValueError(f"Invalid root note in '{symbol}'")
    letter, accidental, qualityText = match.groups()

    quality, degrees = parseQuality(qualityText)
    chord = Chord(symbol, letter, ACC_TO_INT[accidental], quality, degrees)

    if bassText:
        bassLetter, bassAccidental = NOTE_RE.match(bassText).groups()
        chord.bassLetter = bassLetter
        chord.bassAccidental = ACC_TO_INT[bassAccidental]

    return simplifyRoot(chord)


def parseNoteName(text):
    note_text = text.strip()
    if note_text:
        note_text = note_text[0].upper() + note_text[1:]
    match = NOTE_RE.fullmatch(note_text)
    if not match:
        raise ValueError(f"Invalid note name: '{text}'")
    letter, accidental = match.groups()
    pitch_class = (LETTER_TO_PC[letter] + ACC_TO_INT[accidental]) % 12
    return f"{letter}{accidental}", pitch_class


def effectiveDegree(chord, degree):
    if degree == "7" and "7" not in chord.degrees and "6" in chord.degrees:
        return "6"
    return degree


def semitonesFor(chord, degree):
    degree = effectiveDegree(chord, degree)
    if degree in chord.degrees:
        return chord.degrees[degree]
    return DEFAULT_9TH if degree == "9" else None


def simplestSpelling(pc, nominalLetter):
    nominal = LETTERS.index(nominalLetter)
    candidates = []
    for letter in LETTERS:
        offset = (pc - LETTER_TO_PC[letter] + 6) % 12 - 6
        if abs(offset) <= 1:
            gap = (LETTERS.index(letter) - nominal) % 7
            candidates.append((abs(offset), min(gap, 7 - gap), letter, offset))

    _, _, letter, offset = min(candidates)
    return letter, offset


def spellPitch(pc, letter, allowDouble=False):
    offset = (pc - LETTER_TO_PC[letter] + 6) % 12 - 6
    if abs(offset) > 1 and not allowDouble:
        letter, offset = simplestSpelling(pc, letter)
    return letter + ("#" * offset if offset > 0 else "b" * -offset)


def spellDegree(chord, degree, allowDouble=False):
    degree = effectiveDegree(chord, degree)
    letter = LETTERS[(LETTERS.index(chord.rootLetter) + DEGREE_LETTER_STEPS[degree]) % 7]
    return spellPitch((chord.rootPc + semitonesFor(chord, degree)) % 12, letter, allowDouble)


def accidentalLoad(chord):
    degrees = [d for d in DEGREE_ORDER if d in chord.degrees or d == "9"]
    accidentals = [spellDegree(chord, d, allowDouble=True)[1:] for d in degrees]
    return (
        sum(1 for a in accidentals if len(a) >= 2),
        sum(len(a) for a in accidentals),
    )


def simplifyRoot(chord):
    if accidentalLoad(chord)[0] == 0:
        return chord

    typed = (chord.rootLetter, chord.rootAccidental)
    options = []
    for letter in LETTERS:
        offset = (chord.rootPc - LETTER_TO_PC[letter] + 6) % 12 - 6
        if abs(offset) <= 1:
            options.append(replace(chord, rootLetter=letter, rootAccidental=offset))

    return min(
        options,
        key=lambda c: accidentalLoad(c) + ((c.rootLetter, c.rootAccidental) != typed,),
    )


def chordToneNames(chord):
    return [spellDegree(chord, d) for d in DEGREE_ORDER if d in chord.degrees]


def bassName(chord):
    if chord.bassLetter is None:
        return None
    pc = (LETTER_TO_PC[chord.bassLetter] + chord.bassAccidental) % 12
    return spellPitch(pc, chord.bassLetter)


def availableVoicings(chord):
    return {
        name: [
            (spellDegree(chord, d), (chord.rootPc + semitonesFor(chord, d)) % 12)
            for d in degrees
        ]
        for name, degrees in VOICING_TEMPLATES.items()
        if all(semitonesFor(chord, d) is not None for d in degrees)
    }
