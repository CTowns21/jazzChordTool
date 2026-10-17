# Jazz Chord Voicer

Jazz Chord Voicer is a desktop learning tool for exploring chord symbols,
piano voicings, voice leading, and how a voicing looks and sounds. Enter a
progression, compare possible voicings, preview them on the keyboard and
grand staff, and play them with a SoundFont instrument.

## Setup and launch

Install the Python dependencies and start the application:

```cmd
pip install -r requirements.txt
python guiApp.py
```

Sound playback uses FluidSynth and also requires its native library. Install
FluidSynth 2 or newer for your operating system. If the app cannot find the
FluidSynth library on Windows, set `FLUIDSYNTH_DLL_DIR` to the directory
containing `libfluidsynth-3.dll`.

## Build a progression

1. Enter a chord symbol in the **Chord** field and press **Add** or Enter.
2. Repeat for each chord. The chart shows the chord, bass note, selected
   voicing, notes, and whether that voicing is pinned.
3. Select a chart row to see its voicing choices and preview on the keyboard
   and grand staff.
4. Click the **X** at the end of a row to remove that chord.

Chord symbols use a note name from A through G, optionally followed by `#` or
`b`, and a supported chord quality or modifier. Examples include `Cm7`,
`Ebmaj7`, `F7b9`, `Bm7b5`, and `Fadd9/A`. Supported qualities include major,
minor, dominant, diminished, augmented, sixth, and ninth chords, as well as
suspended (`Csus2`, `Csus4`, `C7sus4`, `C9sus4`) and extended 11th and 13th
chords (`Cmaj11`, `Cm11`, `C11`, `Cmaj13`, `Cm13`, `C13`). Modifiers include
`b9`, `#9`, `#11`, `b13`, `b5`, `#5`, `add2`, `add4`, `add9`, `add11`, and
`add13`. Unsupported or malformed symbols are reported when you try to add
them.

## Explore voicings

The **Style** menu controls the automatic voicing approach:

- **rootless**: four-note jazz voicings that omit the root when appropriate.
- **shell**: compact voicings that include the root and core chord tones.
- **two-note**: pairs such as root and seventh or third and fifth, with
  nearby-octave choices.
- **close position** and **open position**: compact and spread chord shapes,
  each with available inversions.
- **drop-2**: four-note voicings with the second-highest voice lowered by an
  octave.
- **left/right hand**: a lower accompaniment shape paired with upper chord
  tones in a separate register.

The chart displays the voicing selected for each chord, taking voice leading
through the progression into account. In **Voicing Controls**, select any
listed option to preview it without changing the progression. Click **Pin**
to keep that choice for the selected chord; **Unpin** returns it to automatic
selection. Two-note labels indicate which note is on the bottom.

For slash chords such as `Fadd9/A`, choose **slash bass** from the voicing
choices and pin it to place the written bass note below the chord voicing.

## Keyboard and staff

The keyboard and grand staff display the selected voicing together. The staff
shows standard noteheads and accidentals, with a text summary identifying each
note's chord role and interval from the root. For example, a minor seventh
chord can show a minor third (`m3`) and minor seventh (`m7`).

The keyboard colors the root, guide tones, and other chord tones differently.
Enable **Show previous chord** to display the preceding voicing as gray notes
on the keyboard; the staff shows only the current voicing. The keyboard adjusts
its visible range to include the notes being shown.

## Listen

- **Play Preview** auditions the selected voicing without pinning it.
- **Play Progression** plays the current progression in order and follows the
  active chord in the chart and visualizations.
- Set the playback tempo in **BPM**, or click **Stop** to end playback early.

Progression playback currently gives each chord two beats.

### SoundFonts and instrument settings

Place `.sf2` or `.sf3` files in the `SoundFonts` folder beside the app.
Subfolders are scanned too. Choose a SoundFont from the list and select one of
its available bank 0 instruments. Use **Refresh** after adding or removing
SoundFonts; **Browse...** can load a SoundFont from elsewhere.

The **Volume** and **Reverb** sliders adjust playback. SoundFont, instrument,
volume, and reverb settings are remembered on this computer. SoundFonts are
not included with the app: use files whose licenses permit your intended use.
The [Upright Piano KW SoundFont](https://github.com/AppCenterCDN-App/modubible-soundfonts/releases/download/v1/piano-upright-kw.sf3)
is one tested option and is released under CC0 1.0.

## Save and load progressions

Click **Save...** to save the current chord symbols, voicing style, and pinned
choices as a JSON progression file. The default location is the
Git-ignored `ExportedProgressions` folder beside the app. Use **Choose music
folder...** to set a different default folder; that preference is remembered
on this computer.

The **Load** dropdown lists JSON progression files in the configured folder,
including its subfolders. Select a file to load it, or use **Refresh** after
adding files outside the app. Loading validates the file and asks before
replacing a nonempty progression.

The `SoundFonts` and `ExportedProgressions` folders are included in the
repository only as empty placeholders. Their contents are Git-ignored, so
personal SoundFonts and exported progression files are not added to the repo.
