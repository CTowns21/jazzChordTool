#!/usr/bin/env python3
"""
Module Name: voicingEngine.py
Description: Voicing engine for jazzChordTool GUI
Author: Carson Towns
"""

from dataclasses import dataclass, replace
from itertools import combinations

from chordParser import (
    DEGREE_ORDER,
    LETTER_TO_PC,
    VOICING_TEMPLATES,
    bassName,
    effectiveDegree,
    semitonesFor,
    spellDegree,
)

MOVEMENT_WEIGHT = 1.0
LEAP_SIZE = 4
LEAP_PENALTY = 2.0

REGISTER_WEIGHT = 0.25
SPAN_PENALTY = 2.0
INVERSION_PENALTY = 1.5

HALF_STEP_RESOLUTION_BONUS = 4.0
WHOLE_STEP_RESOLUTION_BONUS = 1.5
COMMON_GUIDE_TONE_BONUS = 2.0

SEVENTHS = {"7", "6"}
GUIDE_DEGREES = {"3", "7", "6"}
INVERSION_NAMES = [
    "root position",
    "1st inversion",
    "2nd inversion",
    "3rd inversion",
]
SLASH_BASS_LABEL = "slash bass"


@dataclass
class Style:
    name: str
    voiceCount: int
    bottomFloor: int
    centerPitch: int
    spanLimit: int
    templates: list
    allowInversions: bool
    bassIsRoot: bool


STYLES = {
    "rootless": Style("rootless", 4, 52, 60, 12, ["typeA", "typeB"], True, False),
    "shell": Style("shell", 3, 40, 52, 16, ["shell", "shellB", "triad"], False, True),
}
DEFAULT_STYLE = "rootless"

TEMPLATE_STYLE = {
    label: style.name
    for style in STYLES.values()
    for label in style.templates
}


@dataclass
class Voicing:
    label: str
    notes: list
    pitches: list
    style: Style


def placePitches(pitchClasses, floor):
    current = floor + (pitchClasses[0] - floor) % 12
    pitches = [current]

    for pc in pitchClasses[1:]:
        current += (pc - current) % 12 or 12
        pitches.append(current)

    return pitches


def buildVoicing(chord, label, degrees, style):
    notes = [
        (
            effectiveDegree(chord, d),
            spellDegree(chord, d),
            (chord.rootPc + semitonesFor(chord, d)) % 12,
        )
        for d in degrees
    ]

    return Voicing(
        label,
        notes,
        placePitches([pc for _, _, pc in notes], style.bottomFloor),
        style,
    )


def canSupply(chord, degrees):
    return all(semitonesFor(chord, d) is not None for d in degrees)


def chooseToneDegrees(chord, style):
    present = [d for d in DEGREE_ORDER if d in chord.degrees]
    priority = ["3", "7", "6", "1", "5", "9", "11", "13"]
    kept = sorted(present, key=priority.index)[:style.voiceCount]
    return [d for d in DEGREE_ORDER if d in kept]


def templateVoicings(chord, style):
    labels = [label for label in style.templates if canSupply(chord, VOICING_TEMPLATES[label])]
    if "triad" in labels and len(labels) > 1:
        labels.remove("triad")

    return [buildVoicing(chord, label, VOICING_TEMPLATES[label], style) for label in labels]


def inversionVoicings(chord, style):
    toneDegrees = chooseToneDegrees(chord, style)
    voicings = []

    for i in range(len(toneDegrees)):
        rotated = toneDegrees[i:] + toneDegrees[:i]
        if len(rotated) < style.voiceCount:
            rotated = rotated + [rotated[0]]
        voicings.append(buildVoicing(chord, INVERSION_NAMES[i], rotated, style))

    return voicings


def candidateVoicings(chord, style):
    candidates = templateVoicings(chord, style)
    if style.allowInversions:
        candidates += inversionVoicings(chord, style)
    return candidates


def slashBassVoicings(chord, style):
    if chord.bassLetter is None:
        return []

    bass_pc = (
        LETTER_TO_PC[chord.bassLetter] + chord.bassAccidental
    ) % 12
    bass_pitch = style.bottomFloor - 12 + (bass_pc - style.bottomFloor) % 12
    bass_name = bassName(chord)
    bass_style = replace(style, bassIsRoot=True)
    voicings = []

    for upper in candidateVoicings(chord, style):
        pitch = bass_pitch
        while pitch >= upper.pitches[0]:
            pitch -= 12

        voicings.append(
            Voicing(
                SLASH_BASS_LABEL,
                [("bass", bass_name, bass_pc)] + upper.notes,
                [pitch] + upper.pitches,
                bass_style,
            )
        )

    return voicings


def pinnedVoicings(chord, label, style=None):
    if label == SLASH_BASS_LABEL:
        return slashBassVoicings(chord, style or STYLES[DEFAULT_STYLE])

    if label in VOICING_TEMPLATES:
        degrees = VOICING_TEMPLATES[label]
        if not canSupply(chord, degrees):
            return []
        return [buildVoicing(chord, label, degrees, STYLES[TEMPLATE_STYLE[label]])]

    return [v for v in inversionVoicings(chord, STYLES["rootless"]) if v.label == label]


def availableLabels(chord):
    labels = [
        label for label in list(VOICING_TEMPLATES) + INVERSION_NAMES
        if pinnedVoicings(chord, label)
    ]
    if chord.bassLetter is not None:
        labels.append(SLASH_BASS_LABEL)
    return labels


def matchLabel(text):
    labels = list(VOICING_TEMPLATES) + INVERSION_NAMES + [SLASH_BASS_LABEL]
    text = text.strip().lower()

    exact = [label for label in labels if label.lower() == text]
    if exact:
        return exact[0]

    prefixed = [label for label in labels if label.lower().startswith(text)]
    return prefixed[0] if len(prefixed) == 1 else None


def guideToneBonus(previous, new):
    bonus = 0.0

    for (prevDegree, _, _), prevPitch in zip(previous.notes, previous.pitches):
        for (newDegree, _, _), newPitch in zip(new.notes, new.pitches):
            step = newPitch - prevPitch
            if prevDegree in SEVENTHS and newDegree == "3":
                if step == -1:
                    bonus += HALF_STEP_RESOLUTION_BONUS
                elif step == -2:
                    bonus += WHOLE_STEP_RESOLUTION_BONUS
            elif prevDegree == "3" and newDegree in SEVENTHS and step == 0:
                bonus += COMMON_GUIDE_TONE_BONUS

    return bonus


def voiceMovements(previous, new):
    a = previous.pitches[1:] if previous.style.bassIsRoot else previous.pitches
    b = new.pitches[1:] if new.style.bassIsRoot else new.pitches
    if len(a) > len(b):
        a, b = b, a

    options = ([abs(x - y) for x, y in zip(a, chosen)] for chosen in combinations(b, len(a)))
    return min(options, key=sum)


def transitionCost(previous, new):
    movements = voiceMovements(previous, new)
    cost = MOVEMENT_WEIGHT * sum(movements)
    cost += LEAP_PENALTY * sum(1 for m in movements if m > LEAP_SIZE)
    return cost - guideToneBonus(previous, new)


def voicingCost(voicing):
    average = sum(voicing.pitches) / len(voicing.pitches)
    span = voicing.pitches[-1] - voicing.pitches[0]

    cost = REGISTER_WEIGHT * abs(average - voicing.style.centerPitch)
    cost += SPAN_PENALTY * max(0, span - voicing.style.spanLimit)
    if voicing.label not in VOICING_TEMPLATES:
        cost += INVERSION_PENALTY

    return cost


def chooseVoicings(chords, pins, style):
    if not chords:
        return []

    candidateLists = [
        (
            pinnedVoicings(chord, pin, style)
            if pin else []
        ) or candidateVoicings(chord, style)
        for chord, pin in zip(chords, pins)
    ]

    best = [[(voicingCost(v), None) for v in candidateLists[0]]]

    for i in range(1, len(candidateLists)):
        row = []
        for voicing in candidateLists[i]:
            cost, back = min(
                (best[i - 1][k][0] + transitionCost(prev, voicing), k)
                for k, prev in enumerate(candidateLists[i - 1])
            )
            row.append((cost + voicingCost(voicing), back))
        best.append(row)

    j = min(range(len(best[-1])), key=lambda idx: best[-1][idx][0])
    path = []
    for i in range(len(best) - 1, -1, -1):
        path.append(candidateLists[i][j])
        j = best[i][j][1]

    return path[::-1]
