# 2. Your first shortcut

EEditor's keyboard shortcuts aren't settings: they are a program. **⌘⇧K** opens
`.eeditor/keybindings.eelisp` in your folder — the file *is* the shortcut table — and anything you
add there runs the moment you save it. This chapter adds two keys you will use every day, and a
place for your own functions that survives a restart.

## How a binding reads

Scroll past the comments and you'll find lines like this one:

```eelisp keys
(bind "Mod-Shift-i"
  (ed-insert (str (cond (= *col* 1) "" true "\n") "## " *time* "\n\n")))
```

- `"Mod-Shift-i"` is the key: **Mod** is ⌘ on a Mac and Ctrl elsewhere.
- The rest is EELisp. It runs on the engine when you press the key, and returns *editor commands*
  — `ed-insert` here — which EEditor then carries out.
- Before every run EEditor defines the context: `*date*` and `*time*`, `*file*` (the note in front),
  `*line-text*` (the caret's line), `*selection*`, `*buffer*` and a few more.

The commands you'll use most: `ed-insert`, `ed-new` (create a note and open it), `ed-append` (add
to a note, open or not), `ed-message` (a short message at the bottom of the window), and
`ed-prompt` (ask a question, then call one of your functions with the answer).

## A home for your functions: `on-load`

`(on-load …)` is for definitions. It runs when EEditor starts and again every time you save the
file, so a function written there is always there — unlike one typed at the REPL. Move chapter 1's
`open-tasks` into it, along with what this chapter needs:

```eelisp keys
(on-load
  (defn open-tasks (path)
    (length (filter (fn (line) (str-starts-with line "- [ ]"))
                    (str-split (read-note path) "\n"))))

  ;; meetings/2026-10-26 Budget review.md
  (defn meeting-path (title) (str "meetings/" *date* " " title ".md"))

  (defn meeting-template (title)
    (str "# " title "\n\n" *date* " " *time* "\n\n"
         "## Who\n\n- \n\n## Notes\n\n\n## Decisions\n\n- \n\n## Actions\n\n- [ ] \n"))

  ;; what the meeting key calls with your answer
  (defn new-meeting (title) (ed-new (meeting-path title) (meeting-template title)))

  ;; "call the bank" → "- [ ] call the bank"; a line that is a task already stays one
  (defn as-task (line)
    (let (text (str-trim line))
      (cond (str-starts-with text "- [") text
            (str-starts-with text "- ")  (str "- [ ] " (substr text 2 (str-len text)))
            true                        (str "- [ ] " text)))))
```

Save (**⌘S**). Nothing visible happens — the functions are simply there now. Check at the REPL:

```eelisp
(meeting-path "Budget review")      ; → "meetings/2026-10-26 Budget review.md"
(as-task "call the bank")           ; → "- [ ] call the bank"
(as-task "- call the bank")         ; → "- [ ] call the bank"
(as-task "- [x] done already")      ; → "- [x] done already"
```

(The dates in this book are from the day it was tested, 2026-10-26; yours will be today's.)

## Key 1 — a meeting note, ⌘⇧M

```eelisp keys
(bind "Mod-Shift-m" (ed-prompt "Meeting about?" new-meeting))
```

Press **⌘⇧M**, type *Budget review*, Enter: `meetings/2026-10-26 Budget review.md` opens, already
laid out with *Who*, *Notes*, *Decisions* and *Actions*. Press it again with the same title on the
same day and you land back in the same note — `ed-new` never overwrites.

`ed-prompt` takes the question and the *function* to call with the answer — `new-meeting`, with
no parentheses: you are handing the function over, not calling it.

## Key 2 — send this line to the inbox, ⌘⇧A

In the middle of a meeting note someone says *"can you check the insurance?"*. Write it down where
you are, then send it to where it will be dealt with:

```eelisp keys
(bind "Mod-Shift-a"
  (ed-append "inbox.md" (str (as-task *line-text*) "\n") "## Inbox")
  (ed-message "Sent to the inbox"))
```

`ed-append` adds the line to the end of the `## Inbox` section of `inbox.md` — open or not —
and the binding returns a second command, a message, so you know it went. A binding can return
as many commands as you like; they run in order.

You can check what a binding *would* do without pressing it — the body is just an expression:

```eelisp
(first (new-meeting "Budget review"))     ; → "new"
(second (new-meeting "Budget review"))    ; → "meetings/2026-10-26 Budget review.md"
```

## When something goes wrong

A mistake in the file doesn't stop EEditor: on save, a message says *keybindings: N problem(s)*,
and the REPL (**⌘J**) says which line. Every other binding keeps working. Fix it, save again.

## What you have now

- `.eeditor/keybindings.eelisp` with an `(on-load …)` of your own functions
- **⌘⇧M** — a meeting note from a template, named by date and title
- **⌘⇧A** — the caret's line, as a task, at the end of the inbox

The companion workspace has the whole file as it stands after this chapter:
[`.eeditor/keybindings.eelisp`](workspace/.eeditor/keybindings.eelisp).

→ Next: [Chapter 3 — The agenda](README.md#part-ii--time) *(being written)*
