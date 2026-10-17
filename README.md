# Jazz Chord Tool

## How to run

* Place all files in same directory
* Run the following:
```
pip install PySide6
python guiApp.py
```

## Save and load chord progressions

Use **Save...** to export the current progression as a JSON file, including
its voicing style and any pinned voicings. Use **Load...** to restore it later.
Loading validates the whole file before replacing the current progression and
asks for confirmation when chords are already in the session.
