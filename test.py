#!/usr/bin/env python3
"""
Module Name: test.py
Description: A proof of concept to show that I can output the notes of a triad from user input
Author: Carson Towns
"""

import os, sys

chordChoices = {
    "1": "Major",
    "2": "Minor"
}

noteChoices = {
        "1": "A",
        "2": "B",
        "3": "C",
        "4": "D",
        "5": "E",
        "6": "F",
        "7": "G"
}

def getRootNote():

    # Print choices
    for number, type in noteChoices.items():
        print(f"{number} - {type}")

    # Get input
    while True:
        userInput = input("Choose a root note by number: ")
        if userInput in noteChoices.keys():
            result = userInput
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        else:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid root note:")
            for number, type in noteChoices.items():
                    print(f"{number} - {type}")

    return result

def getChordType():

    # Print choices
    for number, type in chordChoices.items():
        print(f"{number} - {type}")

    # Get input
    while True:
        userInput = input("Choose a chord type by number: ")
        if userInput in chordChoices.keys():
            result = userInput
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            break
        else:
            # Clear the terminal screen
            os.system('cls' if os.name == 'nt' else 'clear')
            print("Please enter a valid chord type:")
            for number, type in chordChoices.items():
                    print(f"{number} - {type}")

    return result

def main():

    # Collecting input
    rootNote = getRootNote()
    chordType = getChordType()

    if noteChoices[rootNote] in ['A', 'E']:
         article = "an"
    else:
         article = "a"
    print(f"The following is {article} {noteChoices[rootNote]} {chordChoices[chordType]} triad:")
    

if __name__ == "__main__":
    # Clear the terminal screen
    os.system('cls' if os.name == 'nt' else 'clear')
    main()
