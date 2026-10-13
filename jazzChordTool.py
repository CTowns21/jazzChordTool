#!/usr/bin/env python3
"""
Module Name: jazzChordTool.py
Description: A CLI tool to determine the least-distance-inversion for a chord progression
Author: Carson Towns
"""

import os
import sys
import json

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

def getScaleType(chordType, rootNote, num):

    while True:
        userInput = input(f"Chord Type: {chordType}\nRoot Note: {rootNote}\nChoose a scale type: ")
        if userInput in scales.keys():
            result = userInput
            break
        else:
            print("Please enter a valid scale type you stupid idiot chop hoe!")

    return result

def getChordType():

    # Print choices
    for type, recipe in chords.items():
        print(f"{type}")

    while True:
        userInput = input("\n\nChoose a chord type: ")
        if userInput in chords.keys():
            result = userInput
            break
        else:
            print("Please enter a valid chord type you stupid idiot chop hoe!")

    return result

def assembleChordFromInputs(rootNote, scaleType, chordType):

    # Create initial mapping and get needed adjustment
    baseRecipe = scales[f"{scaleType}"]
    adjustmentValue = notes[rootNote]
    
    # Adjust based off values greater than 7 and loop around
    realRecipe = [(x + adjustmentValue) % 12 for x in baseRecipe]

    # Swap note values with keys to retrieve easier
    val_to_key = {v: k for k, v in notes.items()}
    swappedScale = [val_to_key[val] for val in realRecipe]

    # Take just desired chord notes
    return [swappedScale[int(x-1)] for x in chords[f"{chordType}"]]

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
        num = len(chordNames)

        displayState(chordNames, chosenInversions, chordType)
        rootNote  = getRootNote(chordType, num)
        if not rootNote:
            break

        displayState(chordNames, chosenInversions, chordType)
        scaleType = getScaleType(chordType, rootNote, num)

        chordName = f"{rootNote} {scaleType} {chordType}"
        chordNames.append(chordName)

        chordNotes = assembleChordFromInputs(rootNote, scaleType, chordType)

        if not chosenInversions:
            # First chord stays as written
            chosenInversions.append(chordNotes)
        else:
            previousChord = chosenInversions[-1]
            bestInversion = chooseBestInversion(previousChord, chordNotes)
            chosenInversions.append(bestInversion)

        displayState(chordNames, chosenInversions, chordType)
    
        if not shouldContinue():
            break

if __name__ == "__main__":

    # File loading
    with open('musicalBuildingBlocks/notes.json', 'r') as file:
        notes = json.load(file)
    with open('musicalBuildingBlocks/scales.json', 'r') as file:
        scales = json.load(file)
    with open('musicalBuildingBlocks/chords.json', 'r') as file:
        chords = json.load(file)

    clearScreen()
    main()
