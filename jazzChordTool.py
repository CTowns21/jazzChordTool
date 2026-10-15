#!/usr/bin/env python3
"""
Module Name: jazzChordTool.py
Description: A CLI tool that voices a jazz chord progression. Voicings come from
             a selectable style (rootless Bill Evans A/B, or left-hand shells).
             By default the tool picks the smoothest voicing path automatically.
             You can also pin a specific voicing on any chord, and every other
             chord re-optimizes around it.
Author: Carson Towns

Requires chordParser.py in the same folder.
"""

import os
from dataclasses import dataclass, field
from itertools import combinations

from chordParser import (
    ACC_TEXT, DEGREE_ORDER, VOICING_TEMPLATES, bassName, effectiveDegree,
    parseChordSymbol, semitonesFor, spellDegree,
)

# ---------------------------------------------------------------------------
# Settings you can tune by ear
# MIDI reference: https://computermusicresource.com/midikeys.html
# Octave labels: middle C = MIDI 60 = C4
# ---------------------------------------------------------------------------

# Transition scoring parameters
MOVEMENT_WEIGHT = 1.0       # cost per semitone any voice moves
LEAP_SIZE       = 4         # a voice moving more than this many semitones...
LEAP_PENALTY    = 2.0       # ...costs this much extra

# Static voicing-shape scoring parameters
REGISTER_WEIGHT   = 0.25    # cost per semitone the voicing's average is off center
SPAN_PENALTY      = 2.0     # cost per semitone beyond a style's span limit
INVERSION_PENALTY = 1.5     # plain inversions cost extra so that named jazz voicings win close calls

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
# Styles
# ---------------------------------------------------------------------------

@dataclass
class Style:
    name: str
    voiceCount: int         # notes per voicing (used when building plain inversions)
    bottomFloor: int        # MIDI: a voicing's lowest note lands in the octave starting here
    centerPitch: int        # MIDI: voicings are gently pulled toward this pitch
    spanLimit: int          # widest comfortable voicing, in semitones
    templates: list         # named voicings this style draws from
    allowInversions: bool   # also consider plain inversions of the chord tones
    bassIsRoot: bool        # lowest note is the chord root, which moves freely with the harmony


STYLES = {
    "rootless": Style("rootless", 4, 52, 60, 12, ["typeA", "typeB"], True, False),
    "shell":    Style("shell",    3, 40, 52, 16, ["shell", "shellB", "triad"], False, True),
}
DEFAULT_STYLE = "rootless"

# Which style owns each named template, so a pin can pull a voicing from either style
TEMPLATE_STYLE = {label: style.name for style in STYLES.values() for label in style.templates}


# ---------------------------------------------------------------------------
# Voicings
# ---------------------------------------------------------------------------

@dataclass
class Voicing:
    label: str      # human-readable label: shell, typeA, 1st inversion, etc.
    notes: list     # (degree, noteName, pitchClass), bottom to top
    pitches: list   # absolute pitch numbers (60 = middle C), bottom to top
    style: Style    # style whose register and rules this voicing was built under


def placePitches(pitchClasses, floor):
    """ Convert an ordered list of pitch classes into ascending absolute pitches

        Important behavior:
        - Start the bottom note in the first matching octave above floor
        - Each subsequent note is stacked upward to the next occurrence of its pitch class
        - This guarantees strictly ascending pitches

        Example: If pitch classes are [11, 2, 5]   (B, D, F) and floor is 52
                     this produces   [59, 62, 65]  (B3, D4, F4)
    """

    current = floor + (pitchClasses[0] - floor) % 12
    pitches = [current]

    for pc in pitchClasses[1:]:
        current += (pc - current) % 12 or 12
        pitches.append(current)

    return pitches


def buildVoicing(chord, label, degrees, style):
    """ Build one Voicing object from a chord and an ordered degree list

        For each degree:
        - Resolve special cases like 6 standing in for 7
        - Spell the note name correctly
        - Compute pitch class
        - Finally place all notes into ascending absolute pitches for the style
    """

    notes = [
        (effectiveDegree(chord, d),
         spellDegree(chord, d),
         (chord.rootPc + semitonesFor(chord, d)) % 12)
        for d in degrees
    ]

    return Voicing(label, notes, placePitches([pc for _, _, pc in notes], style.bottomFloor), style)


def canSupply(chord, degrees):
    """ True if the chord can provide every degree in the list """

    return all(semitonesFor(chord, d) is not None for d in degrees)


def chooseToneDegrees(chord, style):
    """ Pick which chord tones should be used for plain inversion candidates

        If the chord has more tones than the style's voiceCount allows, keep the most important ones:
            3rd, 7th, 6th, root, 5th, then extensions

        Returns chosen degrees in canonical DEGREE_ORDER, not priority order
    """

    present = [d for d in DEGREE_ORDER if d in chord.degrees]
    priority = ["3", "7", "6", "1", "5", "9", "11", "13"]
    kept = sorted(present, key=priority.index)[:style.voiceCount]

    return [d for d in DEGREE_ORDER if d in kept]


def templateVoicings(chord, style):
    """ Named templates (shell, typeA, typeB, etc.) the chord can support in this style

        The plain triad is only a fallback, so it's dropped when anything richer fits
    """

    labels = [label for label in style.templates if canSupply(chord, VOICING_TEMPLATES[label])]
    if "triad" in labels and len(labels) > 1:
        labels.remove("triad")

    return [buildVoicing(chord, label, VOICING_TEMPLATES[label], style) for label in labels]


def inversionVoicings(chord, style):
    """ Rotated inversions of the selected chord tones """

    toneDegrees = chooseToneDegrees(chord, style)
    voicings = []

    for i in range(len(toneDegrees)):
        rotated = toneDegrees[i:] + toneDegrees[:i]
        if len(rotated) < style.voiceCount:
            rotated = rotated + [rotated[0]]    # triads: double the bottom note on top
        voicings.append(buildVoicing(chord, INVERSION_NAMES[i], rotated, style))

    return voicings


def candidateVoicings(chord, style):
    """ Every voicing the automatic mode considers for one chord in the given style """

    candidates = templateVoicings(chord, style)
    if style.allowInversions:
        candidates += inversionVoicings(chord, style)

    return candidates


def pinnedVoicings(chord, label):
    """ Voicings matching a label the user pinned, or [] if the chord can't do it

        Named templates are built in the style that owns them, so you can pin a shell
        in the middle of a rootless progression (or the reverse). Inversions are
        built in the rootless style.
    """

    if label in VOICING_TEMPLATES:
        degrees = VOICING_TEMPLATES[label]
        if not canSupply(chord, degrees):
            return []
        return [buildVoicing(chord, label, degrees, STYLES[TEMPLATE_STYLE[label]])]

    return [v for v in inversionVoicings(chord, STYLES["rootless"]) if v.label == label]


def availableLabels(chord):
    """ Every label that can be pinned on this chord """

    return [label for label in list(VOICING_TEMPLATES) + INVERSION_NAMES
            if pinnedVoicings(chord, label)]


def matchLabel(text):
    """ Turn what the user typed into a known voicing label, or None

        Accepts an exact name in any case, or a unique prefix
        ('typeb', 'root', '1st')
    """

    labels = list(VOICING_TEMPLATES) + INVERSION_NAMES
    text = text.strip().lower()

    exact = [label for label in labels if label.lower() == text]
    if exact:
        return exact[0]

    prefixed = [label for label in labels if label.lower().startswith(text)]
    return prefixed[0] if len(prefixed) == 1 else None


# ---------------------------------------------------------------------------
# Voice-leading cost (lower is better)
# ---------------------------------------------------------------------------

def guideToneBonus(previous, new):
    """ Reward musically desirable guide-tone motion between two voicings

        Looks at every note pair across previous and new voicings and awards bonuses when:
        - Previous 7th (or 6 in a 6 chord role) resolves down to a new 3rd
        - Previous 3rd stays put and becomes new 7th/6th

        This is a "bonus", so caller subtracts it from cost later
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


def voiceMovements(previous, new):
    """ Semitone movement of each voice between two voicings

        - A root bass (shell style) is left out, since roots follow the harmony freely
        - Same number of voices: compared low-to-high by index
        - Different numbers of voices (e.g. a pinned shell next to a rootless voicing):
          each voice of the smaller voicing is matched to the nearest voices of the
          larger one, keeping their order
    """

    a = previous.pitches[1:] if previous.style.bassIsRoot else previous.pitches
    b = new.pitches[1:] if new.style.bassIsRoot else new.pitches
    if len(a) > len(b):
        a, b = b, a

    options = ([abs(x - y) for x, y in zip(a, chosen)] for chosen in combinations(b, len(a)))
    return min(options, key=sum)


def transitionCost(previous, new):
    """ Cost of moving from one voicing to the next

        Cost components:
        - Sum of absolute semitone movement (see voiceMovements)
        - Extra penalty for large leaps
        - Subtract guide-tone bonuses
    """

    movements = voiceMovements(previous, new)
    cost = MOVEMENT_WEIGHT * sum(movements)
    cost += LEAP_PENALTY * sum(1 for m in movements if m > LEAP_SIZE)

    return cost - guideToneBonus(previous, new)


def voicingCost(voicing):
    """ Static cost of one voicing by itself

        Penalizes:
        - Voicings whose average register is far from the style's center
        - Voicings wider than the style's span limit
        - Plain inversions, so named jazz voicings win close comparisons
    """

    average = sum(voicing.pitches) / len(voicing.pitches)
    span = voicing.pitches[-1] - voicing.pitches[0]

    cost = REGISTER_WEIGHT * abs(average - voicing.style.centerPitch)
    cost += SPAN_PENALTY * max(0, span - voicing.style.spanLimit)
    if voicing.label not in VOICING_TEMPLATES:
        cost += INVERSION_PENALTY

    return cost


def chooseVoicings(chords, pins, style):
    """ Choose the best full-sequence voicing path for the given chord progression

        This is dynamic programming over a layered graph:
        - Each chord has several candidate voicings
        - Each candidate can transition to each candidate of the next chord
        - Total cost = sum of per-voicing costs + transition costs

        A pinned chord has exactly one candidate, so the path is forced through it
        and the unpinned chords around it adapt. Unpinned chords use the style's
        automatic candidates.

        The algorithm only keeps the cheapest path to each candidate state
    """

    if not chords:
        return []

    candidateLists = [
        (pinnedVoicings(chord, pin) if pin else []) or candidateVoicings(chord, style)
        for chord, pin in zip(chords, pins)
    ]

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
# Session state
# ---------------------------------------------------------------------------

@dataclass
class Session:
    chords: list = field(default_factory=list)
    pins: list = field(default_factory=list)    # parallel to chords: a voicing label, or None
    styleName: str = DEFAULT_STYLE

    def voicings(self):
        return chooseVoicings(self.chords, self.pins, STYLES[self.styleName])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

HELP_LINES = [
    "Chords:    Dm7        (or  Dm7 @typeB  to pin a voicing as you add it)",
    "Pinning:   pin 2 shell | unpin 2 | options 2",
    "Other:     style shell | style rootless | undo | done",
]


def clearScreen():
    """ Clear terminal screen """

    os.system('cls' if os.name == 'nt' else 'clear')


def bassOf(chord):
    """ Display slash bass if present; otherwise display root """

    return bassName(chord) or chord.rootLetter + ACC_TEXT[chord.rootAccidental]


def formatVoicing(voicing):
    """ Format note names for terminal output; guide tones shown in brackets """

    return " ".join(
        f"[{name}]" if degree in GUIDE_DEGREES else name
        for degree, name, _ in voicing.notes
    )


def displayState(session, message=""):
    """ Redraw the current progression and chosen voicings
        Each change can cause unpinned voicings to change after re-optimization
    """

    clearScreen()
    print(f"Style: {session.styleName}\n")

    if session.chords:
        print(f"{'#':<4}{'Chord':<12}{'Bass':<6}{'Voicing':<16}Notes (low to high)")
        print("-----------------------------------------------------------")
        for i, (chord, pin, voicing) in enumerate(zip(session.chords, session.pins, session.voicings()), 1):
            label = voicing.label + ("*" if pin else "")
            print(f"{i:<4}{chord.symbol:<12}{bassOf(chord):<6}{label:<16}{formatVoicing(voicing)}")
        print("\n[ ] = guide tone (3rd / 7th)     * = pinned by you")

    print()
    print("\n".join(HELP_LINES))
    if message:
        print(f"\n{message}")
    print()


def parseChordNumber(text, session):
    """ Turn '2' into index 1, or return None if it isn't a valid chord number """

    if text.isdigit() and 1 <= int(text) <= len(session.chords):
        return int(text) - 1
    return None


def handleChordCommand(command, args, session):
    """ pin N voicing | unpin N | options N  ->  message to show the user """

    index = parseChordNumber(args[0], session) if args else None
    if index is None:
        return f"Usage: {command} <chord number>" + (" <voicing>" if command == "pin" else "")
    chord = session.chords[index]

    if command == "options":
        return f"Chord {index + 1} ({chord.symbol}) can be pinned to: {', '.join(availableLabels(chord))}"

    if command == "unpin":
        session.pins[index] = None
        return f"Chord {index + 1} is back to automatic."

    label = matchLabel(" ".join(args[1:]))
    if label is None or not pinnedVoicings(chord, label):
        return f"Can't pin that on {chord.symbol}. Options: {', '.join(availableLabels(chord))}"
    session.pins[index] = label
    return f"Pinned chord {index + 1} ({chord.symbol}) to {label}."


def addChord(line, session):
    """ Parse 'Dm7' or 'Dm7 @typeB', add it to the session, and return a message """

    symbolText, _, pinText = line.partition("@")

    try:
        chord = parseChordSymbol(symbolText.strip())
    except ValueError as e:
        return str(e)

    pin = None
    if pinText.strip():
        pin = matchLabel(pinText)
        if pin is None or not pinnedVoicings(chord, pin):
            return (f"Not added: can't pin '{pinText.strip()}' on {chord.symbol}. "
                    f"Options: {', '.join(availableLabels(chord))}")

    session.chords.append(chord)
    session.pins.append(pin)
    return ""


def handleCommand(line, session):
    """ Interpret one line of user input

        Returns (done, message): done is True when the user is finished, and
        message is shown under the table on the next redraw
    """

    words = line.split()
    if not words:
        return False, ""

    command = words[0].lower()

    if command == "done":
        return True, ""

    if command == "undo":
        if session.chords:
            session.chords.pop()
            session.pins.pop()
        return False, ""

    if command == "style":
        name = words[1].lower() if len(words) > 1 else ""
        if name not in STYLES:
            return False, f"Styles: {', '.join(STYLES)}"
        session.styleName = name
        return False, f"Style set to {name}."

    if command in ("pin", "unpin", "options"):
        return False, handleChordCommand(command, words[1:], session)

    return False, addChord(line, session)


def main():
    """ Main interactive program loop

        Workflow:
            1. Redraw the progression with the current voicings
            2. Read one line (a chord or a command)
            3. Update the session, then repeat

        Voicings are optimized for the full progression so far, not chosen
        greedily one chord at a time. Pinned chords stay fixed; everything
        else adapts around them.
    """

    session = Session()
    message = ""

    while True:
        displayState(session, message)
        done, message = handleCommand(input("> "), session)
        if done:
            break


if __name__ == "__main__":
    main()