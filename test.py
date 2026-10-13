#!/usr/bin/env python3
"""
Module Name: test.py
Description: A proof of concept to show that I can output the notes of a triad from user input
Author: Carson Towns
"""

import os
import sys
import json

with open('musicalBuildingBlocks/notes.json', 'r') as file:
    notes = json.load(file)
with open('musicalBuildingBlocks/scales.json', 'r') as file:
    scales = json.load(file)
with open('musicalBuildingBlocks/chords.json', 'r') as file:
    chords = json.load(file)

def getNumberOfChords():

    # Get input
    while True:
        userInput = input("How many chords will you need: ")
        try:
            result = int(userInput)
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        except ValueError:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid number you stupid idiot chop hoe!")

    return result

def getRootNote(chordType, num):

    # Get input
    while True:
        userInput = input(f"Chord #{num+1}\nChord Type: {chordType}\nChoose a root note: ")
        if userInput in notes.keys():
            result = userInput
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        else:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid root note you stupid idiot chop hoe!")

    return result

def getScaleType(chordType, rootNote, num):

    # Get input
    while True:
        userInput = input(f"Chord #{num+1}\nChord Type: {chordType}\nRoot Note: {rootNote}\nChoose a scale type: ")
        if userInput in scales.keys():
            result = userInput
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        else:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid scale type you stupid idiot chop hoe!")

    return result

def getChordType():

    # Print choices
    for type, recipe in chords.items():
        print(f"{type}")

    # Get input
    while True:
        userInput = input("\n\nChoose a chord type: ")
        if userInput in chords.keys():
            result = userInput
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        else:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid chord type you stupid idiot chop hoe!")

    return result

def calculateChord(rootNote, scaleType, chordType):

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

def getChordInversions(chordNotes):
    inversions = []
    n = len(chordNotes)

    for i in range(n):
        inversions.append(chordNotes[i:] + chordNotes[:i])
    return inversions

def getDistanceScores(chordA, chordB):

    distanceScore = 0

    for i in range(len(chordA)):
        firstValue = abs(notes[chordA[i]] - notes[chordB[i]])
        secondValue = abs(notes[chordA[i]] - (notes[chordB[i]] + 12))
        distanceScore += min(firstValue, secondValue)

    return distanceScore

def runCalculations(inputChords):

    chordList = list(inputChords.values())
    chosenInversions = [chordList[0]]
    previousChord = chordList[0]

    for nextChord in chordList[1:]:
        bestInversion = None
        bestDistanceScore = sys.maxsize

        # Calculate distances and add best inversion to chosenInversion list
        inversions = getChordInversions(nextChord)
        for currentChord in inversions: # Ex: ['G', 'Bb', 'D']
            distanceScore = getDistanceScores(previousChord, currentChord)

            if distanceScore < bestDistanceScore:
                bestDistanceScore = distanceScore
                bestInversion = currentChord

        chosenInversions.append(bestInversion)
        previousChord = bestInversion

    return chosenInversions

def main():

    # Collecting input
    chordType = getChordType() # Gathering only once so we don't have mismatching amounts of notes; TODO: solve later
    numberOfChords = getNumberOfChords()
    inputChords = {}
    for num in range(numberOfChords):
        rootNote  = getRootNote(chordType, num)
        scaleType = getScaleType(chordType, rootNote, num)
        chordName = f"{rootNote} {scaleType} {chordType}"
        inputChords[chordName] = calculateChord(rootNote, scaleType, chordType)

    finalInversions = runCalculations(inputChords)

    # Printing results
    os.system('cls' if os.name == 'nt' else 'clear')
    for name, inversion in zip(inputChords.keys(), finalInversions):
        print(f"{name}: {inversion}")

if __name__ == "__main__":
    # Clear the terminal screen
    os.system('cls' if os.name == 'nt' else 'clear')
    main()
