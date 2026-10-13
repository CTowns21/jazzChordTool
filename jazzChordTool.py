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

def displayState(chordNames, chosenInversions, chordType=None):
    clearScreen()

    if chordNames:
        print("Chosen Inversions:")
        for name, inversion in zip(chordNames, chosenInversions):
            print(f"{name}: {inversion}")
    print()

def shouldContinue():

    while True:
        userInput = input("Add another chord? Type [Enter] or no: ").strip().lower()

        if userInput in ['y', 'yes', '']:
            return True
        elif userInput in ['n', 'no']:
            return False
        else:
            print("Please enter a valid answer you stupid idiot chop hoe! (y/n)")

def getRootNote(chordType, num):

    while True:
        userInput = input(
            f"Chord Type: {chordType}\nChoose a root note (or type 'done'): "
        ).strip()

        if userInput.lower() == "done":
            return None

        if userInput in notes.keys():
            result = userInput
            break
        else:
            print("Please enter a valid root note you stupid idiot chop hoe!")

    return result

def getChordType():

    for chordType in chordFormulas.keys():
        print(chordType)
    
    while True:
        userInput = input("\n\nChoose a chord type: ").strip()
        if userInput in chordFormulas.keys():
            return userInput
        else:
            print("Please enter a valid chord type you stupid idiot chop hoe!")

def assembleChordFromInputs(rootNote, chordType):

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

    chordType = getChordType()

    chordNames = []
    chosenInversions = []

    while True:

        displayState(chordNames, chosenInversions, chordType)
        rootNote  = getRootNote(chordType, len(chordNames))
        if rootNote is None:
            break

        chordName = f"{rootNote} {chordType}"
        chordNames.append(chordName)

        chordNotes = assembleChordFromInputs(rootNote, chordType)

        if not chosenInversions:
            # First chord stays as written
            chosenInversions.append(chordNotes)
        else:
            chosenInversions.append(
                chooseBestInversion(chosenInversions[-1], chordNotes)
            )

        displayState(chordNames, chosenInversions, chordType)
    
        if not shouldContinue():
            break

if __name__ == "__main__":
    main()
