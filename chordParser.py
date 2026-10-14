#!/usr/bin/env python3
"""
Module Name: chordParser.py
Description: Chord symbol parser, letter-correct spelling, and voicing
             templates for jazzChordTool.
Author: Carson Towns
"""

import re
from dataclasses import dataclass

LETTERS = "CDEFGAB"
LETTER_TO_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11} # Pitch-class mapping
ACC_TO_INT = {"": 0, "#": 1, "b": -1} # Accidental text -> offset
ACC_TEXT = {-2: "bb", -1: "b", 0: "", 1: "#", 2: "##"} # Reverse mapping for display/spelling

# Letters above the root for each degree
# Example:
#   root C + 3rd -> E (2 letter steps up: C -> D -> E)
DEGREE_LETTER_STEPS = {"1": 0, "3": 2, "5": 4, "6": 5, "7": 6,
                       "9": 1, "11": 3, "13": 5}
DEGREE_ORDER = ["1", "3", "5", "6", "7", "9", "11", "13"]
DEFAULT_9TH = 2

# Quality -> {degree: semitones above root}
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
}

# Handles multiple spellings of the same chord quality
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
}

# Alterations/additions: token -> (degree, semitones)
MODIFIERS = {
    "b9": ("9", 1), "#9": ("9", 3), "#11": ("11", 6), "b13": ("13", 8),
    "b5": ("5", 6), "#5": ("5", 8),
    "add9": ("9", 2), "add2": ("9", 2), "add11": ("11", 5),
}

# Voicing templates: degrees ordered bottom to top
VOICING_TEMPLATES = {
    "triad": ["1", "3", "5"],
    "shell": ["1", "3", "7"],
    "typeA": ["3", "5", "7", "9"],
    "typeB": ["7", "9", "3", "5"],
}

# Dict comprehension for aliases
# Longest-first so "o7" beats "o" and "+7" beats "+"
ALIAS_LIST = sorted(
    ((alias, name) for name, aliases in QUALITY_ALIASES.items() for alias in aliases),
    key=lambda pair: -len(pair[0]),
)
MODIFIER_LIST = sorted(MODIFIERS.items(), key=lambda item: -len(item[0])) # Dict comprehension for modifiers

NOTE_RE = re.compile(r"^([A-G])([#b]?)$")       # Parses standalone note names like B#
ROOT_RE = re.compile(r"^([A-G])([#b]?)(.*)$")   # Splits chord symbol into note letter,
                                                #   accidental, remaining quality/modifier text


@dataclass
class Chord:
    symbol: str             # Ebmaj7/Gb
    rootLetter: str         # E
    rootAccidental: int     # b
    quality: str            # maj7
    degrees: dict           # {"1": 0, "3": 4, "5": 7, "7": 11}
    bassLetter: str = None  # G
    bassAccidental: int = 0 # b

    @property
    def rootPc(self):       # 3 (Eb)
        return (LETTER_TO_PC[self.rootLetter] + self.rootAccidental) % 12

def normalizeSymbol(symbol):
    """ Normalizes a given symbol to handle non-ASCII chars like ♭ 

        Args: chord symbol ('E♭m7')
        Returns: normalized chord symbol ('Ebm7')
    """

    for old, new in [("♭", "b"), ("♯", "#"), ("°", "o"), ("Δ", "maj"),
                     ("(", ""), (")", ""), (" ", "")]:
        symbol = symbol.replace(old, new)
    return symbol

def splitSlash(symbol):
    """ Handles slashes for bass notes if applicable

        Args: chord symbol ('Fadd9/A')
        Returns:
            head = 'Fadd9'
            tail = 'A'
                OR
            symbol remains unchanged if 

    """

    head, sep, tail = symbol.rpartition("/")
    if sep and NOTE_RE.match(tail):
        return head, tail
    return symbol, None

def parseModifiers(text):
    """ Parses modifiers from modification text

        Args: modifier text ('b9#11' (from 'Emb9#11/D'))
        Returns:
            found = [('9', 1), ('11', 6)]
                OR
            None (if any leftover text is unsupported)
    """

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
    """ Parses specific quality name and degrees from quality text

        Args: quality text ('m7add9' (if chord were 'Ebm7add9/A#'))
        Returns:
            name = 'min'
            degrees = {'1': 0, '3': 3, '5': 7, '7': 10, '9': 2}
        Strategy:
            1. Try each known quality alias, longest-first
            2. If alias matches the prefix, parse the remainder as modifiers
            3. If modifiers parse cleanly, clone base quality degrees and apply them
    """

    for alias, name in ALIAS_LIST:
        if text.startswith(alias):
            modifiers = parseModifiers(text[len(alias):])
            if modifiers is not None:
                degrees = dict(QUALITIES[name])
                degrees.update(modifiers)
                return name, degrees
    raise ValueError(f"Unsupported chord quality: '{text}'")

def parseChordSymbol(symbol):
    """ Primary chord parser, makes use of all other parsers up to this point
    
        Args: chord symbol ('Emb9#11/D')
        Returns: structured 'chord' object with attributes populated
    """

    # Normalize symbol ('E♭m7' -> 'Ebm7')
    cleaned = normalizeSymbol(symbol.strip())
    if not cleaned:
        raise ValueError("Chord symbol cannot be empty")

    # Pull off slash bass note if applicable
    head, bassText = splitSlash(cleaned)

    # Parse root note and remaining quality text
    match = ROOT_RE.match(head)
    if not match:
        raise ValueError(f"Invalid root note in '{symbol}'")
    letter, accidental, qualityText = match.groups()

    # Parse quality/modifier part into normalized quality + degrees dict
    quality, degrees = parseQuality(qualityText)

    # Assemble initial chord obj
    chord = Chord(symbol, letter, ACC_TO_INT[accidental], quality, degrees)

    # Assign bass note as chord obj property if applicable
    if bassText:
        bassLetter, bassAccidental = NOTE_RE.match(bassText).groups()
        chord.bassLetter = bassLetter
        chord.bassAccidental = ACC_TO_INT[bassAccidental]
    return chord

def effectiveDegree(chord, degree):
    """ For 6 chords, treat the 6th like the "seventh-ish" guide tone if no 7 is present
    
        Args:
            chord = chord obj
            degree = degree value ('7')
        Returns: degree = "6" if applicable
        
    """

    if degree == "7" and "7" not in chord.degrees and "6" in chord.degrees:
        return "6"
    return degree

def semitonesFor(chord, degree):
    """ Semitones above root, or None if the chord can't supply it.
        The 9th defaults to natural unless the symbol altered it """

    degree = effectiveDegree(chord, degree)
    if degree in chord.degrees:
        return chord.degrees[degree]
    return DEFAULT_9TH if degree == "9" else None

def spellPitch(pc, letter):
    """ Compute appropriate accidental
        Example: pc = 3, letter = E -> Eb
        Example: pc = 3, letter = D -> D# """

    offset = (pc - LETTER_TO_PC[letter] + 6) % 12 - 6
    return letter + ACC_TEXT[offset]


def spellDegree(chord, degree):
    """"""

    degree = effectiveDegree(chord, degree)
    letter = LETTERS[(LETTERS.index(chord.rootLetter) + DEGREE_LETTER_STEPS[degree]) % 7]
    return spellPitch((chord.rootPc + semitonesFor(chord, degree)) % 12, letter)


def chordToneNames(chord):
    """"""

    return [spellDegree(chord, d) for d in DEGREE_ORDER if d in chord.degrees]


def bassName(chord):
    """"""

    if chord.bassLetter is None:
        return None
    pc = (LETTER_TO_PC[chord.bassLetter] + chord.bassAccidental) % 12
    return spellPitch(pc, chord.bassLetter)


def availableVoicings(chord):
    """ {templateName: [(noteName, pitchClass), ...]} ordered bottom to top """
    return {
        name: [(spellDegree(chord, d), (chord.rootPc + semitonesFor(chord, d)) % 12)
               for d in degrees]
        for name, degrees in VOICING_TEMPLATES.items()
        if all(semitonesFor(chord, d) is not None for d in degrees)
    }
