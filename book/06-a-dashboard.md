# 6. A dashboard

Everything so far answers a question when you ask it. A dashboard asks for you: one note that
shows the week ahead, what's late, what's about money and how your streaks are going — refreshed
with one key. It is an ordinary Markdown note with *live blocks* in it, so it's searchable,
linkable and printable like any other.

## A live block

A live block is a pair of comment lines with EELisp in the first:

```markdown
<!-- eel: (pim-agenda 7) -->
<!-- /eel -->
```

When the note is refreshed, whatever the expression returns — text, Markdown — is written between
the two lines, replacing what was there. Everything outside the blocks is left exactly as you
wrote it. Any expression that returns text can be a block: a PIM function, a view, one of your
own functions from chapter 2.

The comment lines are invisible when the note is shown formatted, so the dashboard reads cleanly.

## The dashboard note

Make `dashboard.md` with a block for each thing you want to see:

```markdown
# Dashboard

## The next 7 days

<!-- eel: (pim-agenda 7) -->
<!-- /eel -->

## Money

<!-- eel: (pim-lines (records (show money)) "_nothing about money_") -->
<!-- /eel -->

## Late

<!-- eel: (pim-lines (records (show late)) "_nothing late_") -->
<!-- /eel -->

## Inbox

<!-- eel: (str (open-tasks "inbox.md") " open in inbox.md · " (length (records (items :category "inbox"))) " captured") -->
<!-- /eel -->

## Streaks

<!-- eel: (str "Exercise " (pim-streak "exercise") " days · drinks logged " (pim-streak "drink") " days running") -->
<!-- /eel -->
```

- `pim-agenda` — overdue items, then the next *n* days, as task lines with their `{#id}`
- `pim-lines` — any list of agenda rows, as task lines; here the `money` and `late` views from
  chapter 4
- `open-tasks` — your own function from chapter 2, counting `- [ ]` lines in a note
- `pim-streak` — days in a row with a kind of thing logged, from the tracker

## Refreshing it

With the dashboard open, **⌘⌥U** recomputes every block in it. Then **⌘E** switches to the
formatted view — headings, checkboxes, no comment lines — which is the way to *read* a dashboard;
**⌘E** again to edit.

Better still, one key that refreshes the note on disk and opens it, from wherever you are:

```eelisp keys
;; ⌘⇧D — the dashboard, fresh
(bind "Mod-Shift-d"
  (ed-write "dashboard.md" (pim-update-blocks (read-note "dashboard.md")))
  (ed-open "dashboard.md"))
```

`read-note` gives the note's text as saved, `pim-update-blocks` recomputes its blocks, `ed-write`
writes the result back and `ed-open` shows it. The same three steps work on any note with blocks.

You can see the blocks fill at the REPL:

```eelisp
(str-contains (pim-update-blocks (read-note "dashboard.md")) "open in inbox.md")    ; → true
(str-contains (pim-update-blocks (read-note "dashboard.md")) "pay the rent")        ; → true
```

The rent is there because it's in the `money` view.

## Blocks anywhere

Blocks aren't only for the dashboard. In a project note, `(pim-category "home")` keeps the
project's tasks in front of you; in today's note, **⌘⌥W** inserts a block of the next seven days
and **⌘⌥R** today's tracker log. Each note's blocks refresh with **⌘⌥U** in that note.

A block can be your own question, too:

```eelisp
(defn has-text (s) (and (string? s) (!= s "")))

(defn money-due (days)
  (let (until (date-add *date* days :days)
        due   (filter (fn (r) (has-text (field-get r :when)))
                      (records (show money))))
    (str (length (filter (fn (r) (<= (date-diff (field-get r :when) until) 0)) due))
         " money items due in the next " days " days")))

(str-ends-with (money-due 60) "due in the next 60 days")    ; → true
```

```markdown
<!-- eel: (money-due 14) -->
<!-- /eel -->
```

A block runs whenever the note is refreshed — tomorrow, after a restart — so a function it calls
belongs in your keybindings' `on-load`, not just typed at the REPL.

`date-diff a b` is the days from `b` to `a` — compare dates with it, because `<` and `>` only
compare numbers, not `"2026-11-01"`-style text.

## What you have now

- `dashboard.md`: the week, money, what's late, the inbox, your streaks
- **⌘⇧D** — refresh the dashboard and open it; **⌘⌥U** in any note with blocks; **⌘E** to read it
- blocks that are any expression, your own functions included

→ Part III starts with [Chapter 7 — Tables](07-tables.md)
