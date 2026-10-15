# Jazz Chord Voicer Roadmap

This roadmap is intentionally conservative.

The goal is not to turn this project into a huge AI-generated codebase all at once. The goal is to grow it in a way that keeps the design understandable, the code explainable, and the musical ideas intentional. I want to be able to answer **“How does it work?”** in detail at every stage.

## Project philosophy

This tool should grow slowly enough that each new feature is something I understand well.

Before adding a feature, I want to be able to answer:

1. **What problem does this solve?**
2. **Where does that logic belong in the code?**
3. **Why am I implementing it this way instead of another way?**

If I cannot answer those clearly, the project is growing faster than my understanding.

A useful rule for this project:

> one musical idea, one code change, one explanation

That means:
- add one concept at a time
- keep the implementation small
- make sure I can explain the result afterward

---

## What the program currently does

At a high level, the current tool works like this:

1. The user types chord symbols or commands into the CLI.
2. A chord symbol is parsed into a structured `Chord` object.
3. Candidate voicings are generated for each chord based on the selected style.
4. If a chord is pinned to a specific voicing, that constraint is enforced.
5. A dynamic programming pass chooses the lowest-cost path through the full progression.
6. The chosen voicings are displayed in a table.

That pipeline is the core of the project. Future work should build on it without making it opaque.

---

## Development priorities

The next stages should emphasize understanding before expansion.

Priority order:

1. Understand the current system more deeply
2. Make the optimizer easier to inspect
3. Add one small musical improvement
4. Add one small parser or voicing feature
5. Add small usability improvements
6. Refactor only when the code creates real friction

---

## Phase 1: Understand the current engine better

### Goal
Strengthen understanding of the existing code before adding much new functionality.

### Planned work

#### 1. Write down the pipeline clearly
Document, in plain language, how the program moves from:
- user input
- to parsed chord objects
- to candidate voicings
- to optimization
- to display output

This helps turn “I think I get it” into “I can explain it.”

#### 2. Add a few small tests
Not a large test suite at first. Just enough to verify and understand core behavior.

Good starting targets:
- `parseChordSymbol("Dm7")`
- `parseChordSymbol("E♭m7")`
- `splitSlash("Fadd9/A")`
- `matchLabel("typeb")`
- one short progression through `chooseVoicings()`

The purpose of these tests is not just correctness. It is also to force close reading of the code.

#### 3. Add an explain/debug mode
This is the most valuable near-term improvement.

The tool should be able to show, for each chord:
- what candidate voicings were available
- which voicing was chosen
- the static cost of that voicing
- the transition cost from the previous voicing
- any guide-tone bonus that affected the result

This will make the optimizer easier to understand and easier to tune.

### Why this phase comes first
Before adding many new features, I want the current logic to feel visible rather than mysterious.

---

## Phase 2: Make one small musical improvement

### Goal
Change one part of the musical behavior in a way that is easy to hear and easy to explain.

### Planned work
Add **one** new scoring rule only.

Possible candidates:
- reward common tones more strongly
- penalize large top-voice leaps
- penalize muddy low-register voicings
- reward smoother overall motion

### Recommended first choice
**Top-voice leap penalty**

Why this is a good next step:
- it is musically noticeable
- it is relatively localized in the code
- it teaches how the cost function shapes the chosen voicings

### Guardrail
Do not add several scoring heuristics at once. Add one, test it, listen to it, and understand its effect.

---

## Phase 3: Add one small musical feature

### Goal
Expand the tool a little without changing its character or making the code too complex too quickly.

### Planned work
Add **either**:
- one new chord feature
- or one new voicing style

Not both at once.

### Recommended first direction
Add one new chord feature.

Good candidates:
- `sus4`
- `add11`
- `7b9`

Why this is a good step:
- it builds directly on the current parser design
- it improves real-world usefulness
- it deepens understanding of the chord representation

### Alternative
If I want to focus on voicing generation instead, add one new style such as:
- quartal voicings
- drop-2 voicings

But only after I feel confident explaining how styles and templates work now.

---

## Phase 4: Add a practical usability feature

### Goal
Make the tool more useful outside the terminal while keeping implementation manageable.

### Planned work
Add **JSON export**.

Useful exported fields:
- chord symbol
- chosen voicing label
- note names
- MIDI pitches
- selected style
- whether the voicing was pinned

### Why JSON first
JSON export is simpler than MIDI or MusicXML and helps clarify the internal data model.

---

## Phase 5: Refactor only when needed

### Goal
Improve structure only when there is a specific reason, not just because a refactor sounds nice.

### Rule
Refactor in response to concrete friction, such as:
- parser additions becoming hard to manage
- optimization logic becoming hard to inspect
- CLI code and musical logic becoming too entangled
- tests being difficult to write because responsibilities are mixed

### Examples of useful small refactors
- extract explanation/debug helpers
- move formatting logic into its own module
- isolate optimization code further
- clarify parser tables and parsing helpers

### Guardrail
Do not do a large architecture rewrite without a specific pain point.

---

## Things to avoid for now

These ideas are interesting, but they should wait until the current system is very comfortable to explain and maintain:

- full harmonic function analysis
- reharmonization tools
- MIDI playback
- multiple new voicing systems at once
- several scoring changes in the same pass
- a GUI or web app
- melody-aware harmonization
- a major multi-file rewrite done preemptively

The reason is not that these are bad ideas. The reason is that they could outpace understanding.

---

## How to judge whether I am ready for the next step

Before moving to the next phase, I should be able to answer:

- Can I explain this feature without reading the code?
- Can I point to the exact functions involved?
- Can I describe why I used this design?
- If this feature broke, would I know where to start debugging?

If not, I should pause and consolidate before adding more.

---

## Current roadmap summary

### Milestone 1: Understand the current engine
- document the pipeline
- add a few focused tests
- add explain/debug output

### Milestone 2: Make one optimizer improvement
- add one scoring rule
- preferably top-voice leap penalty

### Milestone 3: Add one small musical feature
- add one chord feature such as `sus4` or `7b9`
- or add one new voicing family, but not both

### Milestone 4: Add one output feature
- add JSON export

### Milestone 5: Refactor only when earned
- refactor in response to concrete friction

---

## Long-term direction

Longer-term ideas may include:
- richer chord vocabulary
- more voicing styles
- smarter quality-aware voicing choices
- playback or MIDI export
- melody-aware voicing
- progression-aware harmonic analysis

But those should come later, after the current system remains easy to explain in detail.

---

## Guiding principle

This project should stay understandable.

The goal is not to add features as fast as possible. The goal is to build a tool whose behavior, musical logic, and code structure I can explain with confidence.
