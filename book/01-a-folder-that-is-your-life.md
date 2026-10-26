# 1. A folder that is your life

Everything in this book lives in one folder. Notes are plain Markdown files in it, the agenda and
your tables are a database inside it (`.eeditor/eeditor.db`), sheets are files next to your notes.
Copy the folder and you have copied your whole system; open it in ten years with any text editor
and the notes still read.

By the end of this chapter you'll have that folder, a shape for it that scales, and the habit that
keeps it from turning into a pile: everything new goes to one place, and gets sorted later.

## Pick the folder

Make an empty folder — `~/Life`, say — then in EEditor press **folder…** above the file tree and
choose it. An empty folder is offered the sample notes: say **no** this time. The samples are
worth reading (the welcome note, *TRY ME*), but this book builds its own system from nothing, so
you can see where every piece comes from.

## A shape that scales

Five places are enough for years:

| Where | What goes there | Ends? |
|---|---|---|
| `inbox.md` | anything new, the moment it arrives | emptied daily |
| `2026-10-26.md` | today: the plan and a log | one per day |
| `projects/` | things with a finish line: *launch the website* | yes — then to `archive/` |
| `areas/` | things you keep up with no end: *money*, *health* | no |
| `reference/` | things you look up: how-tos, lists, decisions | no |

Make them now. **＋** in the file tree makes a note, **＋ dir** a folder. Start `inbox.md` with:

```markdown
# Inbox

Everything lands here first. Empty it once a day: do it, file it, or delete it.

## Inbox

- [ ] book the car service
- [ ] read the article Ana sent about index funds
```

The `## Inbox` heading matters later: chapter 2 sends things *under* it.

## Today's note

Press **⌘D**. EEditor opens today's note — `2026-10-26.md` — creating it if it isn't there. Give it
two sections and use them all day:

```markdown
# 2026-10-26 · Monday

## Plan

- [ ] finish the budget sheet

## Log

- 09:30  started the PIM book
```

**⌘⇧I** puts a `## HH:MM` heading at the caret when you'd rather log under the time.

## Links and tags

Write `[[how-i-work]]` in any note and it becomes a link: **⌘-click** it to follow, and typing
`[[` suggests note names as you go. The note you land on shows a **backlinks** bar — every note
that links to it — so a page about a project quietly collects everything that mentions it.

`#website`, `#money`, `#project` are tags. The **Tags** panel lists them all with how many notes
use each; click one to see those notes. Use tags for what cuts across folders, folders for where
a thing lives.

Two keys find anything: **⌘P** opens a note by a few letters of its name, **⌘⇧F** searches the
text of every note.

## Your notes, from the language

Everything you just did by hand, EELisp can see. Open the REPL with **⌘J** and try:

```eelisp
(notes)                               ; every note in the folder, as paths
(length (notes "projects"))           ; → 1
(str-starts-with (read-note "inbox.md") "# Inbox")   ; → true
```

`(notes)` lists every note, `(notes "projects")` the ones in a folder, and `(read-note path)` gives
a note's text as saved. That is all chapter 2 needs to start building on it — counting what's
open, for instance:

```eelisp
(defn open-tasks (path)
  (length (filter (fn (line) (str-starts-with line "- [ ]"))
                  (str-split (read-note path) "\n"))))

(open-tasks "inbox.md")               ; → 3
(open-tasks "projects/website.md")    ; → 2
```

## What you have now

- one folder, with `inbox.md`, today's note, `projects/`, `areas/`, `reference/`, `archive/`
- links and tags between notes, and two keys to find anything
- a first function of your own, `open-tasks`, written at the REPL

A function typed at the REPL is gone when EEditor quits. Chapter 2 gives your functions a home
that lasts, and puts them on keys.

→ [Chapter 2 — Your first shortcut](02-your-first-shortcut.md)
