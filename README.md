## Proof of Concept -- Flow of Events

```mermaid
graph TD
A(["Ask for Chords (Accept 4)"]) --> B([Retrieve Inversions for the 1st and 2nd Chords])
B --> C([Starting with 1st Inversion of 1st Chord, compare/calculate against each inversion of 2nd chord])
C --> D([Store distance scores])
D --> C
D --> E([At end, display possible other branches those whose score was very similar give choice to re-calculate with new inversion choices])
