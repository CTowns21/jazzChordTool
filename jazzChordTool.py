#!/usr/bin/env python3
"""
Module Name: jazzChordTool.py
Description: A CLI tool to determine the least-distance-inversion for a chord progression
Author: Carson Towns
"""

import os
import sys
from chordParser import parseChordSymbol, availableVoicings, bassName

chordFormulas = {
    "major":      [0, 4, 7],
    "minor":      [0, 3, 7],
    "diminished": [0, 3, 6],
    "augmented":  [0, 4, 8],
    "dominant7":  [0, 4, 7, 10],
    "major7":     [0, 4, 7, 11],
    "minor7":     [0, 3, 7, 10],
}

# Many-to-One input mapping
notes = {
    "C" : 0,
    "B#": 0,
    "C#": 1,
    "Db": 1,
    "D" : 2,
    "Eb": 3,
    "D#": 3,
    "E" : 4,
    "Fb": 4,
    "F" : 5,
    "E#": 5,
    "F#": 6,
    "Gb": 6,
    "G" : 7,
    "Ab": 8,
    "G#": 8,
    "A" : 9,
    "Bb": 10,
    "A#": 10,
    "B" : 11,
    "Cb": 11
}

# One-to-One output mapping
pitchToName = {
    0:  "C" ,
    1:  "Db",
    2:  "D" ,
    3:  "Eb",
    4:  "E" ,
    5:  "F" ,
    6:  "Gb",
    7:  "G" ,
    8:  "Ab",
    9:  "A" ,
    10: "Bb",
    11: "B"
}

qualityAliases = {
    "augmented": ["aug", "+"],
    "diminished": ["dim", "o"],
    "dominant7": ["7"],
    "major": ["", "maj", "major"],
    "major7": ["M7", "maj7", "major7"],
    "minor": ["m", "min", "minor", "-"],
    "minor7": ["m7", "min7", "minor7", "-7"]
}

qualityMap = {
    alias: chordType
    for chordType, aliases in qualityAliases.items()
    for alias in aliases
}

def clearScreen():
    os.system('cls' if os.name == 'nt' else 'clear')

def displayState(chordNames, chosenInversions):
    clearScreen()

    if chordNames:
        print("Chosen Inversions:")
        for name, inversion in zip(chordNames, chosenInversions):
            print(f"{name}: {inversion}")

def getChordSymbol():

    while True:
        symbol = input(
            "Enter chord symbol (or type 'done'): "
        ).strip()

        if symbol.lower() == "done":
            return None

        try:
            chord = parseChordSymbol(symbol)
        except ValueError as e:
            print(e)
            continue

        if chord.bassLetter:
            print(f"  Bass: {bassName(chord)}")
        for name, notes in availableVoicings(chord).items():
            print(f"  {name:6} {' '.join(n for n, _ in notes)}")

def buildChordFromSymbol(symbol):
    rootNote, chordType = parseChordSymbol(symbol)
    rootValue = notes[rootNote]
    intervals = chordFormulas[chordType]

    return [pitchToName[(rootValue + interval) % 12] for interval in intervals]

def createChordInversions(chordNotes):
    inversions = []
    n = len(chordNotes)

    for i in range(n):
        inversions.append(chordNotes[i:] + chordNotes[:i])
    return inversions

def calculateDistanceScore(chordA, chordB):

    distanceScore = 0

    for i in range(len(chordA)):
        firstValue = abs(notes[chordA[i]] - notes[chordB[i]])
        secondValue = abs(notes[chordA[i]] - (notes[chordB[i]] + 12))
        distanceScore += min(firstValue, secondValue)

    return distanceScore

def chooseBestInversion(previousChord, newChord):
    bestInversion = None
    bestDistanceScore = sys.maxsize

    inversions = createChordInversions(newChord)

    for inversion in inversions:
        distanceScore = calculateDistanceScore(previousChord, inversion)

        if distanceScore < bestDistanceScore:
            bestDistanceScore = distanceScore
            bestInversion = inversion

    return bestInversion

def main():

    chordNames = []
    chosenInversions = []
    displayState(chordNames, chosenInversions)

    while True:

        chordSymbol = getChordSymbol()
        if chordSymbol is None:
            break

        chordNotes = buildChordFromSymbol(chordSymbol)

        # Validating that chords have same amount of notes for now
        if chosenInversions and len(chordNotes) != len(chosenInversions[0]):
            print("Please enter a chord with the same number of notes as the previous chords. Stupid idiot chop hoe!")
            input("Press Enter to continue...")
            continue

        chordNames.append(chordSymbol)

        if not chosenInversions:
            # First chord stays as written
            chosenInversions.append(chordNotes)
        else:
            chosenInversions.append(
                chooseBestInversion(chosenInversions[-1], chordNotes)
            )
        displayState(chordNames, chosenInversions)

if __name__ == "__main__":
    main()
