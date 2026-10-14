#!/usr/bin/env python3
"""
Module Name: jazzChordTool.py
Description: A CLI tool that voices a jazz chord progression. For each chord it
             considers shell, rootless (Bill Evans A/B), and inversion voicings,
             then picks the combination with the smoothest voice leading,
             rewarding guide-tone resolution (7th -> 3rd).
Author: Carson Towns

Requires chordParser.py in the same folder.
"""

import os
from dataclasses import dataclass

from chordParser import (
    ACC_TEXT, DEGREE_ORDER, VOICING_TEMPLATES, bassName, effectiveDegree,
    parseChordSymbol, semitonesFor, spellDegree,
)

# ---------------------------------------------------------------------------
# Settings you can tune by ear
# For reference, MIDI values can be found here: https://computermusicresource.com/midikeys.html
# ---------------------------------------------------------------------------

VOICE_COUNT  = 4            # notes per voicing (3 or 4)
BOTTOM_FLOOR = 52           # E2 in MIDI numbering. The first note of a built voicing is placed in the first matching octave
CENTER_PITCH = 60           # voicings are gently pulled toward middle C

# Transition scoring parameters
MOVEMENT_WEIGHT = 1.0       # cost per semitone any voice moves
LEAP_SIZE       = 4         # a voice moving more than this many semitones...
LEAP_PENALTY    = 2.0       # ...costs this much extra

# Static voicing-shape scoring parameters
REGISTER_WEIGHT   = 0.25    # cost per semitone the voicing's average is off center
SPAN_LIMIT        = 12      # a voicing wider than this many semitones...
SPAN_PENALTY      = 2.0     # ...costs this much per extra semitone
INVERSION_PENALTY = 1.5     # plain inversions cost extra so named jazz voicings win close calls

# Bonus for classic guide-tone behavior across chord changes
HALF_STEP_RESOLUTION_BONUS  = 4.0   # 7th falls a half step onto the next chord's 3rd
WHOLE_STEP_RESOLUTION_BONUS = 1.5   # 7th falls a whole step onto the next chord's 3rd
COMMON_GUIDE_TONE_BONUS     = 2.0   # 3rd stays put and becomes the next chord's 7th

SEVENTHS        = {"7", "6"}        # a 6 chord's 6th plays the role of the 7th
GUIDE_DEGREES   = {"3", "7", "6"}   # degrees visually highlighted in output
INVERSION_NAMES = ["root position", # labels for rotated inversions
                   "1st inversion",
                   "2nd inversion",
                   "3rd inversion"]


# ---------------------------------------------------------------------------
# Voicings
# ---------------------------------------------------------------------------

@dataclass
class Voicing:
    label: str      # human-readable label: shell, typeA, triad, etc.
    notes: list     # (degree, noteName, pitchClass), bottom to top
    pitches: list   # absolute pitch numbers (60 = middle C), bottom to top


def placePitches(pitchClasses):
    """ Stack pitch classes upward, starting in the octave above BOTTOM_FLOOR
    """

    current = BOTTOM_FLOOR + (pitchClasses[0] - BOTTOM_FLOOR) % 12
    pitches = [current]
    for pc in pitchClasses[1:]:
        current += (pc - current) % 12 or 12
        pitches.append(current)
    return pitches


def buildVoicing(chord, label, degrees):
    notes = [
        (effectiveDegree(chord, d),
         spellDegree(chord, d),
         (chord.rootPc + semitonesFor(chord, d)) % 12)
        for d in degrees
    ]
    return Voicing(label, notes, placePitches([pc for _, _, pc in notes]))


def chooseToneDegrees(chord):
    """ Pick up to VOICE_COUNT degrees to rotate through for the inversion voicings.
        Chords with extra tones drop the least essential ones first
    """

    present = [d for d in DEGREE_ORDER if d in chord.degrees]

    priority = ["3", "7", "6", "1", "5", "9", "11", "13"]
    kept = sorted(present, key=priority.index)[:VOICE_COUNT]
    return [d for d in DEGREE_ORDER if d in kept]


def candidateVoicings(chord):
    """
    """

    candidates = []

    # Named templates (shell, Type A, Type B...) with the right number of notes
    for label, degrees in VOICING_TEMPLATES.items():
        if len(degrees) == VOICE_COUNT and all(semitonesFor(chord, d) is not None for d in degrees):
            candidates.append(buildVoicing(chord, label, degrees))

    # Plain inversions of the chord tones (your original idea)
    toneDegrees = chooseToneDegrees(chord)
    for i in range(len(toneDegrees)):
        rotated = toneDegrees[i:] + toneDegrees[:i]
        if len(rotated) < VOICE_COUNT:
            rotated = rotated + [rotated[0]]    # triads: double the bottom note on top
        candidates.append(buildVoicing(chord, INVERSION_NAMES[i], rotated))
    return candidates


# ---------------------------------------------------------------------------
# Voice-leading cost (lower is better)
# ---------------------------------------------------------------------------

def guideToneBonus(previous, new):
    """
    """

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


def transitionCost(previous, new):
    """
    """

    movements = [abs(a - b) for a, b in zip(previous.pitches, new.pitches)]
    cost = MOVEMENT_WEIGHT * sum(movements)
    cost += LEAP_PENALTY * sum(1 for m in movements if m > LEAP_SIZE)
    return cost - guideToneBonus(previous, new)


def voicingCost(voicing):
    """ Cost of a voicing on its own: register, width, and whether it's a named voicing
    """

    average = sum(voicing.pitches) / len(voicing.pitches)
    span = voicing.pitches[-1] - voicing.pitches[0]

    cost = REGISTER_WEIGHT * abs(average - CENTER_PITCH)
    cost += SPAN_PENALTY * max(0, span - SPAN_LIMIT)
    if voicing.label not in VOICING_TEMPLATES:
        cost += INVERSION_PENALTY
    return cost


def chooseVoicings(chords):
    """ Find the cheapest path through every chord's candidate voicings.
        Because it optimizes the whole progression, earlier chords can change
        as you add later ones
    """

    if not chords:
        return []

    candidateLists = [candidateVoicings(chord) for chord in chords]

    # best[i][j] = (lowest total cost ending in voicing j of chord i, index of previous voicing)
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


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def clearScreen():
    """
    """

    os.system('cls' if os.name == 'nt' else 'clear')


def bassOf(chord):
    """
    """

    return bassName(chord) or chord.rootLetter + ACC_TEXT[chord.rootAccidental]


def formatVoicing(voicing):
    """
    """

    return " ".join(
        f"[{name}]" if degree in GUIDE_DEGREES else name
        for degree, name, _ in voicing.notes
    )


def displayState(chords, voicings):
    """
    """

    clearScreen()

    if chords:
        print(f"{'Chord':<12}{'Bass':<6}{'Voicing':<16}Notes (low to high)")
        print("-----------------------------------------------------")
        for chord, voicing in zip(chords, voicings):
            print(f"{chord.symbol:<12}{bassOf(chord):<6}{voicing.label:<16}{formatVoicing(voicing)}")
        print("\n[ ] = guide tone (3rd / 7th)")
    print()


def getUserInput():
    """ Returns ('done', None), ('undo', None), or ('chord', Chord)
    """

    while True:
        userInput = input(
            "Enter chord symbol ('undo' to remove the last one, 'done' to finish): "
        ).strip()

        if userInput.lower() == "done":
            return "done", None
        if userInput.lower() == "undo":
            return "undo", None

        try:
            return "chord", parseChordSymbol(userInput)
        except ValueError as e:
            print(e)


def main():
    chords = []
    voicings = []
    displayState(chords, voicings)

    while True:
        command, chord = getUserInput()

        if command == "done":
            break
        if command == "undo":
            if chords:
                chords.pop()
        else:
            chords.append(chord)

        voicings = chooseVoicings(chords)
        displayState(chords, voicings)


if __name__ == "__main__":
    main()
