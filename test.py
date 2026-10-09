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

print(notes["1"])

def getRootNote():

    # Print choices
    for number, note in notes.items():
        print(f"{note}")

    # Get input
    while True:
        userInput = input("Choose a root note: ")
        if userInput in notes.values():
            result = userInput
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        else:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid root note:")
            for number, note in notes.items():
                    print(f"{note}")

    return result

def getScaleType():

    # Print choices
    for number, type in scales.items():
        print(f"{number} - {type}")

    # Get input
    while True:
        userInput = input("Choose a scale type by number: ")
        if userInput in scales.keys():
            result = userInput
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        else:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid scale type:")
            for number, type in scales.items():
                    print(f"{number} - {type}")

    return result

def getChordType():

    # Print choices
    for type, recipe in chords.items():
        print(f"{type} - {recipe}")

    # Get input
    while True:
        userInput = input("Choose a chord type: ")
        if userInput in chords.keys():
            result = userInput
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        else:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid chord type:")
            for type, recipe in chords.items():
                    print(f"{type} - {recipe}")

    return result

def main():

    # Collecting input
    rootNote  = getRootNote()
    scaleType = getScaleType()
    chordType = getChordType()

    if rootNote in ['A', 'E']:
         article = "an"
    else:
         article = "a"
    print(f"The following is {article} {rootNote} {scales[scaleType]} {chordType}:")
    

if __name__ == "__main__":
    # Clear the terminal screen
    os.system('cls' if os.name == 'nt' else 'clear')
    main()
