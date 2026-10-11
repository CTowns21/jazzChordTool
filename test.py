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

def getRootNote():

    # Print choices
    for note, number in notes.items():
        print(f"{note}", end=" ")

    # Get input
    while True:
        userInput = input("\n\nChoose a root note: ")
        if userInput in notes.keys():
            result = userInput
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        else:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid root note!\n")
            for note, number in notes.items():
                    print(f"{note}", end=" ")

    return result

def getScaleType():

    # Print choices
    for scale, recipe in scales.items():
        print(f"{scale}")

    # Get input
    while True:
        userInput = input("\n\nChoose a scale type: ")
        if userInput in scales.keys():
            result = userInput
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        else:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid scale type:\n")
            for scale, recipe in scales.items():
                    print(f"{scale}")

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
            print("Please enter a valid chord type:\n")
            for type, recipe in chords.items():
                    print(f"{type}")

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

def main():

    # Collecting input
    rootNote  = getRootNote()
    scaleType = getScaleType()
    chordType = getChordType()
    finalChord = calculateChord(rootNote, scaleType, chordType)

    if rootNote in ['A', 'E']:
         article = "an"
    else:
         article = "a"
    print(f"The following is {article} {rootNote} {scaleType} {chordType}:\n{finalChord}")

if __name__ == "__main__":
    # Clear the terminal screen
    os.system('cls' if os.name == 'nt' else 'clear')
    main()
