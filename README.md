# Jazz Chord Tool

## How to run

* Place all files in same directory
* Run the following:

```cmd
pip install PySide6
python guiApp.py
```

## Save and load chord progressions

Use **Save...** to export the current progression as a JSON file, including
its voicing style and any pinned voicings. Use **Load...** to restore it later.
Loading validates the whole file before replacing the current progression and
asks for confirmation when chords are already in the session.

The keyboard view automatically adjusts to center the selected voicing and
includes every note, even when the voicing falls below the default range.
Use **Show previous chord** to toggle the preceding chord's gray notes on the
keyboard when comparing voicings.

For slash chords such as `Fadd9/A`, choose **slash bass** in the selected
chord's voicing list and pin it to put the written bass note below the chord
tones.

The **two-note** style uses voice-leading between two-note chord voicings. It
considers root-and-seventh, third-and-fifth, root-and-third, and root-and-fifth
pairs in nearby octaves, choosing the combination that best connects the
progression.
To override the automatic choice for one chord, select a specific pair in the
voicing controls to preview its notes on the keyboard. Previewing does not
change the progression; click **Pin Previewed Voicing** to keep that choice.
The labels indicate which note is on the bottom.

## Audio playback

Use **Play Preview** to hear the voicing shown for the selected chord without
pinning it. **Play Progression** plays the selected voicings in sequence, with
two beats per chord at the chosen tempo. Use **Stop** to end playback early.
Playback uses a simple synthesized tone rather than piano samples.
