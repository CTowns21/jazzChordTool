#!/usr/bin/env python3
"""
Module Name: jazzChordTool.py
Description: A CLI tool to determine the least-distance-inversion for a chord progression
Author: Carson Towns
"""

import os
import sys

chordFormulas = {
    "major":     [0, 4, 7],
    "minor":     [0, 3, 7],
    "dominant7": [0, 4, 7, 10],
    "major7":    [0, 4, 7, 11],
    "minor7":    [0, 3, 7, 10],
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

def clearScreen():
    os.system('cls' if os.name == 'nt' else 'clear')

def displayState(chordNames, chosenInversions):
    clearScreen()

    if chordNames:
        print("Chosen Inversions:")
        for name, inversion in zip(chordNames, chosenInversions):
            print(f"{name}: {inversion}")
    print()

def getChordSymbol():

    while True:
        userInput = input(
            "Enter chord symbol (or type 'done'): "
        ).strip()

        if userInput.lower() == "done":
            return None
        
        try:
            parseChordSymbol(userInput)
            return userInput
        except ValueError as e:
            print(e)

def buildChordFromInputs(symbol):
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

def parseChordSymbol(symbol):

    symbol = symbol.strip()

    if not symbol:
        raise ValueError("Chord symbol cannot be empty, stupid idiot chop hoe!")

    if len(symbol) >= 2 and symbol[1] in ['#', 'b']:
        rootNote    = symbol[:2]
        qualityText = symbol[2:]
    else:
        rootNote    = symbol[:1]
        qualityText = symbol[1:]

    if rootNote not in notes:
        raise ValueError(f"Invalid root note: {rootNote}, stupid idiot chop hoe!")
    
    if qualityText in ["", "maj", "major"]:
        chordType = "major"
    elif qualityText in ["m", "min", "minor", "-"]:
        chordType = "minor"
    elif qualityText == "7":
        chordType = "dominant7"
    elif qualityText in ["M7", "maj7", "major7"]:
        chordType = "major7"
    elif qualityText in ["m7", "min7", "minor7", "-7"]:
        chordType = "minor7"
    else:
        raise ValueError(f"Unsupported chord quality: {qualityText}, stupid idiot chop hoe!")
    
    return rootNote, chordType

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

    while True:

        displayState(chordNames, chosenInversions)

        chordSymbol = getChordSymbol()
        if chordSymbol is None:
            break
        
        chordNotes = buildChordFromInputs(chordSymbol)

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
    
if __name__ == "__main__":
    main()
