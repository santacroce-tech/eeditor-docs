# 5. Notes kept in step

<!-- test: pim -->

So far a task lives in one of two places: a line in a note, or an item in the agenda. This chapter
makes them the same thing. You'll install the PIM — a library of keys and functions that ships
with EEditor — and then a line like

```markdown
- [ ] pay the electricity bill tomorrow !! #money/bills {#14}
```

*is* agenda item 14. Tick it in the note and it's done in the agenda; finish it in the agenda panel
and within a minute the line is ticked, in whichever note it sits. On top of that come capture,
refile, a time clock and a tracker for the things you do every day.

## Install the PIM

The PIM is a keybindings file of its own — [`pim.eelisp`](https://github.com/santacroce-tech/eeditor-next/blob/main/docs/pim/pim.eelisp) — and installing it
means adding it to yours. EEditor does that for you: right-click the workspace (the top row of the
file tree) and choose **Install the PIM keys…**. It

- adds the PIM to the end of `.eeditor/keybindings.eelisp`, between two marker lines — your own
  keys from chapters 2–4 stay exactly as they are
- copies the capture window, [`Capture.eeform`](https://github.com/santacroce-tech/eeditor-next/blob/main/docs/pim/Capture.eeform), to `pim/Capture.eeform`
- reloads, so the keys work at once

Run it again after updating EEditor and it replaces what's between the markers — the PIM's part —
and nothing else. (It's also a command, `install-pim`, so `(ed-cmd "install-pim")` at the REPL
does the same.)

Check it took: press **⌘⌥K** anywhere in a note. A message at the bottom says *No clock running* —
the PIM's keys are live. Its keys are all **⌘⌥** plus a letter (Ctrl+Alt on Windows and Linux), so
they don't collide with EEditor's own or with yours.

Two things change: **⌘D** now creates today's note from a template — an agenda block at the top,
then *Log* and *Notes* — and EEditor opens on today's note when it starts.

## A line that is an item: ⌘⌥T

Type an ordinary line in today's note:

```markdown
pay the electricity bill tomorrow !! #money/bills
```

Press **⌘⌥T** with the caret on it. Three things happen:

- the agenda gets an item — read by `add`, so *tomorrow* and *!!* become its date and priority, and
  each `#tag` becomes a category (here the rules from chapter 4 would have filed it anyway)
- the line becomes `- [ ] pay the electricity bill tomorrow !! #money/bills {#14}` — `{#14}` is the
  item's number, the link between the two
- a message says *Agenda #14 on 2026-10-27*

Press **⌘⌥T** again and the task is done: `- [x] … ✓ 2026-10-26` in the note, gone from the agenda
(and written to a `done` table, so the weekly review can count it). A third press turns it back
into a plain `- …` line. For a repeating item — the rent — done means *next time*: the line stays
open and its `{#id}` moves to the next occurrence.

You can watch it happen at the REPL — each key's work is a function you can call:

```eelisp
(pim-cycle "pay the electricity bill tomorrow !! #money/bills")
; e.g. (("replace-range" 0 0 "- [ ] pay the electricity bill tomorrow !! #money/bills {#14}")
;       ("message" "Agenda #14 on 2026-10-27"))
```

The keys that work on a linked line:

| Key | Does |
|---|---|
| **⌘⌥T** | text → task → done → plain, and the agenda follows |
| **⌘⌥P** | priority `!!!` → `!!` → `!` → none, on the line and the item |
| **⌘⌥A** | you edited the line's words: read them again into the item (or link a hand-typed `- [ ]`) |
| **⌘⌥E** | asks *When?* — `in 3 days`, `2026-12-01`, `none` — and sets the date |
| **⌘⌥G** | asks for a category, from the ones you have, and files the item |
| **⌘⌥S** | bring every note in step with the agenda now (once a minute it happens anyway) |

```eelisp
(pim-priority "- [ ] call the dentist")    ; → (list "replace-range" 0 0 "- [ ] !!! call the dentist")
```

## Hand-typed tasks in the inbox and projects

In chapter 1 the inbox and `projects/website.md` got their tasks typed by hand: `- [ ] pick a
theme`. Tell the PIM which notes hold tasks, and **⌘⌥S** links every hand-typed `- [ ]` in them to a
new agenda item:

```eelisp keys
(on-load
  (set! pim-agenda-files (list "inbox.md" "projects")))
```

Put it *after* the PIM's end marker — your `on-load` runs after the PIM's, so your setting wins,
and installing the PIM again later won't touch it.
`pim-agenda-files` takes notes and folders; a folder means every note in it.

## Capture: ⌘⌥N

Ideas arrive while you're doing something else. **⌘⌥N** opens a small window over whatever you're
in: pick *task*, *inbox* or *log*, type, Enter, and it's gone — filed without leaving where you
were.

- **task** — an agenda item, and its linked line under `## Tasks` in today's note
- **inbox** — an item in the `inbox` category, and its line under `## Inbox` in `inbox.md` — the
  same section chapter 2's **⌘⇧A** writes to
- **log** — a line for the tracker (below), under `## Log` in today's note

```eelisp
(pim-capture "log" "coffee 2")    ; → "Logged coffee 2 un"
```

Sorting the inbox later is **⌘⌥F** — *refile*: the caret's line moves under any heading of any
note, picked from a list you narrow by typing.

## Reminders

An item for today with a time in its text — *call Marta at 15:00* — taps you on the shoulder at
three: a message in EEditor, and a system notification if EEditor isn't in front. Nothing else to
set up: the PIM checks once a minute. (Only while EEditor is open.)

## The clock: ⌘⌥I, ⌘⌥O, ⌘⌥K

Put the caret on a task or a heading and press **⌘⌥I**: the clock starts on it. **⌘⌥I** on another
stops the first and starts the second; **⌘⌥O** stops; **⌘⌥K** says what's running. Every stretch is a
row in the `clock` table, and a linked task's item gets its total.

```eelisp
(pim-clock-in "- [ ] write the budget")    ; → (list "message" "⏱ write the budget")
(pim-clock-out)                            ; → (list "message" "Stopped write the budget — 0 min")
```

## The tracker: ⌘⌥L and ⌘⌥C

For the things you do every day and want to count — coffee, walks, sleep, pages read — write a
line in today's *Log* and press **⌘⌥L**: `coffee 2`, `walk 30` (minutes), `rice 550 kcal | lunch`.
It's stamped with the time and stored in the `log` table. **⌘⌥C** logs one coffee from anywhere.

```eelisp
(pim-parse-log "walk 30")      ; → (list "walk" 30 "" "")
(track "coffee" 1 "" "")       ; → "coffee 1 un"
(pim-streak "drink")           ; → 1
```

`pim-streak` counts the days in a row with something of that kind logged — coffee is a *drink*, a
walk is *exercise* — which is what chapter 6 puts on the dashboard.

## What you have now

- the PIM installed: task lines in notes that *are* agenda items, kept in step both ways
- hand-typed tasks in the inbox and projects linked with **⌘⌥S**
- capture (**⌘⌥N**), refile (**⌘⌥F**), reminders, the clock (**⌘⌥I/O/K**), the tracker (**⌘⌥L**, **⌘⌥C**)
- **⌘D** with a template, and EEditor opening on today's note

The PIM has more than one chapter can hold — archiving (**⌘⌥X**), the weekly review (**⌘⌥V**,
chapter 15), and a list of every function it offers: [the PIM guide](https://github.com/santacroce-tech/eeditor-next/blob/main/docs/PIM.md).

→ [Chapter 6 — A dashboard](06-a-dashboard.md)
