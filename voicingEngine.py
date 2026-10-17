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
    "two-note": Style("two-note", 2, 48, 58, 12, [], False, False),
    "close position": Style("close position", 4, 48, 60, 18, [], False, False),
    "open position": Style("open position", 4, 48, 64, 30, [], False, False),
    "drop-2": Style("drop-2", 4, 48, 60, 30, [], False, False),
    "left/right hand": Style("left/right hand", 4, 40, 60, 36, [], False, False),
}
DEFAULT_STYLE = "rootless"
SHAPE_STYLE_NAMES = (
    "close position",
    "open position",
    "drop-2",
    "left/right hand",
)

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


def twoNoteVoicings(chord, style):
    pairs = []
    seventh = "7" if "7" in chord.degrees else "6"
    if "1" in chord.degrees and seventh in chord.degrees:
        interval_name = "7th" if seventh == "7" else "6th"
        pairs.append((f"root + {interval_name}", ("1", seventh)))
    if "3" in chord.degrees and "5" in chord.degrees:
        pairs.append(("3rd + 5th", ("3", "5")))
    if "1" in chord.degrees and "3" in chord.degrees:
        pairs.append(("root + 3rd", ("1", "3")))
    if "1" in chord.degrees and "5" in chord.degrees:
        pairs.append(("root + 5th", ("1", "5")))

    voicings = []
    for label, degrees in pairs:
        for ordered_degrees in (degrees, degrees[::-1]):
            bottom_degree = ordered_degrees[0]
            bottom_name = {
                "1": "root",
                "3": "3rd",
                "5": "5th",
                "6": "6th",
                "7": "7th",
            }[bottom_degree]
            voicings.append(
                buildVoicing(
                    chord,
                    f"{label} ({bottom_name} on bottom)",
                    ordered_degrees,
                    style,
                )
            )
    return [
        Voicing(
            voicing.label,
            voicing.notes,
            [pitch + octave_shift for pitch in voicing.pitches],
            voicing.style,
        )
        for voicing in voicings
        for octave_shift in (-12, 0, 12)
    ]


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
    if style.name == "two-note":
        return twoNoteVoicings(chord, style)
    if style.name in SHAPE_STYLE_NAMES:
        return shapeVoicings(chord, style)

    candidates = templateVoicings(chord, style)
    if style.allowInversions:
        candidates += inversionVoicings(chord, style)
    elif style.name == "shell" and not candidates:
        degrees = chooseToneDegrees(chord, style)
        if degrees:
            candidates.append(
                buildVoicing(chord, "suspended shell", degrees, style)
            )
    return candidates


def _shape_degrees(chord):
    priority = ["3", "7", "9", "13", "11", "6", "5", "1"]
    present = [degree for degree in priority if degree in chord.degrees]
    return present[:4]


def _ordered_voicing(chord, label, degrees, style, pitches=None):
    voicing = buildVoicing(chord, label, degrees, style)
    if pitches is None:
        return voicing
    voices = sorted(zip(voicing.notes, pitches), key=lambda voice: voice[1])
    return Voicing(
        label,
        [note for note, _ in voices],
        [pitch for _, pitch in voices],
        style,
    )


def _close_position_voicing(chord, degrees, style):
    pitches = []
    for degree in degrees:
        pitch_class = (
            chord.rootPc + semitonesFor(chord, degree)
        ) % 12
        if not pitches:
            pitch = style.bottomFloor + (
                pitch_class - style.bottomFloor
            ) % 12
        else:
            pitch = pitches[-1] + 1
            while pitch % 12 != pitch_class:
                pitch += 1
        pitches.append(pitch)
    return _ordered_voicing(chord, "", degrees, style, pitches)


def _position_candidates(chord, style, shape):
    degrees = _shape_degrees(chord)
    if shape == "drop-2" and len(degrees) < 4:
        return []
    if not degrees:
        return []

    degrees.sort(key=lambda degree: semitonesFor(chord, degree) % 12)
    candidates = []
    for inversion in range(len(degrees)):
        ordered = degrees[inversion:] + degrees[:inversion]
        close = _close_position_voicing(chord, ordered, style)
        voices = list(zip(close.notes, close.pitches))

        if shape == "drop-2":
            voices[-2] = (voices[-2][0], voices[-2][1] - 12)
        elif shape == "open position":
            voices[1] = (voices[1][0], voices[1][1] + 12)

        voices.sort(key=lambda voice: voice[1])
        bottom_degree = voices[0][0][0]
        degree_name = {
            "1": "root",
            "3": "3rd",
            "5": "5th",
            "6": "6th",
            "7": "7th",
            "9": "9th",
            "11": "11th",
            "13": "13th",
        }.get(bottom_degree, bottom_degree)
        if shape == "drop-2":
            label = f"Drop-2 ({degree_name} on bottom)"
        elif shape == "open position":
            label = f"Open position ({degree_name} on bottom)"
        else:
            label = f"Close position ({degree_name} on bottom)"
        candidates.append(
            Voicing(
                label,
                [note for note, _ in voices],
                [pitch for _, pitch in voices],
                style,
            )
        )
    return candidates


def _hand_split_candidates(chord, style):
    degrees = _shape_degrees(chord)
    if not degrees:
        return []

    seventh = "7" if "7" in chord.degrees else "6"
    left_priority = ["1", seventh, "5", "3", "11", "9", "13"]
    left = [degree for degree in left_priority if degree in degrees][:2]
    right_priority = ["3", "9", "13", "5", "11", "7", "6", "1"]
    right = [
        degree for degree in right_priority
        if degree in degrees and degree not in left
    ][:2]
    chosen = left + right
    if len(chosen) < min(3, len(degrees)):
        chosen.extend(degree for degree in degrees if degree not in chosen)

    left_pitches = placePitches(
        [(chord.rootPc + semitonesFor(chord, degree)) % 12 for degree in left],
        style.bottomFloor,
    )
    right_floor = max(60, (max(left_pitches) + 4) if left_pitches else 60)
    right_pitches = placePitches(
        [(chord.rootPc + semitonesFor(chord, degree)) % 12 for degree in right],
        right_floor,
    )
    degree_pitches = dict(zip(left + right, left_pitches + right_pitches))
    ordered = sorted(chosen, key=lambda degree: degree_pitches[degree])
    return [
        _ordered_voicing(
            chord,
            "Left hand / right hand",
            ordered,
            style,
            [degree_pitches[degree] for degree in ordered],
        )
    ]


def shapeVoicings(chord, style):
    if style.name == "left/right hand":
        return _hand_split_candidates(chord, style)
    if style.name == "drop-2" and len(_shape_degrees(chord)) < 4:
        return _position_candidates(chord, style, "close position")
    return _position_candidates(chord, style, style.name)


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

    for candidate_style in STYLES.values():
        matching_voicings = [
            voicing
            for voicing in candidateVoicings(chord, candidate_style)
            if voicing.label == label
        ]
        if matching_voicings:
            return matching_voicings
    return []


def availableLabels(chord):
    labels = []
    for style_name in STYLES:
        labels.extend(
            voicing.label
            for voicing in candidateVoicings(chord, STYLES[style_name])
        )
    if chord.bassLetter is not None:
        labels.append(SLASH_BASS_LABEL)
    return list(dict.fromkeys(labels))


def matchLabel(text, labels=None):
    if labels is None:
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
