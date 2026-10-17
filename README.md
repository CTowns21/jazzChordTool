# Jazz Chord Tool

## How to run

* Place all files in same directory
* Run the following:

```cmd
pip install -r requirements.txt
python guiApp.py
```

SoundFont playback also requires the native FluidSynth library. On Windows,
install FluidSynth 2 or newer and set `FLUIDSYNTH_DLL_DIR` to the directory
containing `libfluidsynth-3.dll` if FluidSynth is not found automatically.

## Save and load chord progressions

Use **Save...** to export the current progression as a JSON file, including
its voicing style and any pinned voicings. The **Load** dropdown lists saved
progressions in the current export folder; use **Refresh** after adding files
outside the app, or **Browse...** to load a file from another location.
Loading validates the whole file before replacing the current progression and
asks for confirmation when chords are already in the session.

Progressions save by default to the Git-ignored `ExportedProgressions` folder
beside the application. Use **Export folder...** to choose a different default
folder. The selected folder is remembered on this computer; Save dialogs can
still navigate to other locations.

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
change the progression; click **Pin** to keep that choice.
The labels indicate which note is on the bottom.

## Audio playback

Use **Play Preview** to hear the voicing shown for the selected chord without
pinning it. **Play Progression** plays the selected voicings in sequence, with
two beats per chord at the chosen tempo. As each chord plays, its row is
selected and its notes are shown on the keyboard. Use **Stop** to end playback
early.

Place `.sf2` or `.sf3` SoundFont files in the `SoundFonts` folder beside the
application, then choose one from the SoundFont list. **Refresh** rescans that
folder, including subfolders; **Browse...** can load a SoundFont from elsewhere.
Choose one of the loaded file's bank 0 presets. Volume and reverb can be
adjusted beside the instrument selector. The selected SoundFont, preset,
volume, and reverb are remembered on this computer. SoundFont files are not
bundled; use files whose licenses permit your intended use. A tested option is
the [Upright Piano KW SoundFont](https://github.com/AppCenterCDN-App/modubible-soundfonts/releases/download/v1/piano-upright-kw.sf3),
which is CC0 1.0.
