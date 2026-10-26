# 15. The weekly review

Once a week, look back before you look ahead: what got done, where the time and the money went,
what's coming. The PIM already writes most of that review for you; this chapter adds the money,
so one key on Sunday gives you the whole week on one page — and the page stays live: its blocks
refresh with **⌘⌥U** like the dashboard's.

## What ⌘⌥V writes

With the PIM installed (chapter 5), **⌘⌥V** creates `reviews/2026-10-26 week.md` — named after the
week's Monday — already filled in:

- **Done** — what you ticked off, from the PIM's `done` table
- **Time** — the clock, per task, with a total
- **Tracker** — coffee, walks, everything you logged, totalled
- **Coming up** — the next seven days of the agenda
- **Inbox** and **Undated** — what's waiting to be sorted
- **Reflection** — three questions, for you to answer

Each section is a live block, so the review can be refreshed until you're done with it.

## The money, for any stretch of days

```eelisp
(defn money-review (from to)
  (let (rows  (records (query transactions :where "day >= ? AND day <= ?" :params (list from to)))
        out   (filter (fn (r) (and (< (field-get r :amount) 0) (!= (field-get r :category) "savings"))) rows)
        in    (filter (fn (r) (> (field-get r :amount) 0)) rows)
        cats  (unique (map (fn (r) (field-get r :category)) out))
        total (fn (rs) (round (sum (map (fn (r) (abs (field-get r :amount))) rs)) 2)))
    (str "| Category | Spent | Times |\n|---|---|---|\n"
         (str-join "" (map (fn (c) (let (rs (filter (fn (r) (= (field-get r :category) c)) out))
                                     (str "| " c " | " (total rs) " | " (length rs) " |\n")))
                           cats))
         "\n**Spent** " (total out) " · **In** " (total in)
         " · **Portfolio** " (portfolio-total "E") " USD (" (portfolio-total "G") "% on cost)"
         " · **Open price alerts** " (length (records (items :category "money/markets"))))))
```

It reads the week's transactions once, then works on the list: money out (leaving transfers to
savings aside, as `spent` does), money in, one table row per category. `unique` is one of the
spreadsheet functions — they're loaded for your code as well as for sheets.

This book's examples happen on Monday 2026-10-26, the first day of the week; so far that week has
chapter 8's lunch and chapter 9's bakery:

```eelisp
(str-contains (money-review "2026-10-26" "2026-11-01") "| food | 22.4 | 2 |")    ; → true
(str-contains (money-review "2026-10-26" "2026-11-01") "**Spent** 22.4")        ; → true
(str-contains (money-review "2026-10-01" "2026-10-31") "| rent | 1200 | 1 |")   ; → true
```

The last one is the whole of October — the same function works for a month, or a year.

## ⌘⌥V, with the money

Put `money-review` in your keybindings and bind **⌘⌥V** again — a later binding for the same key
replaces the PIM's. The new one writes the PIM's review, then a *Money* section as one more block:

```eelisp keys
(on-load
  (defn money-review (from to)
    (let (rows  (records (query transactions :where "day >= ? AND day <= ?" :params (list from to)))
          out   (filter (fn (r) (and (< (field-get r :amount) 0) (!= (field-get r :category) "savings"))) rows)
          in    (filter (fn (r) (> (field-get r :amount) 0)) rows)
          cats  (unique (map (fn (r) (field-get r :category)) out))
          total (fn (rs) (round (sum (map (fn (r) (abs (field-get r :amount))) rs)) 2)))
      (str "| Category | Spent | Times |\n|---|---|---|\n"
           (str-join "" (map (fn (c) (let (rs (filter (fn (r) (= (field-get r :category) c)) out))
                                       (str "| " c " | " (total rs) " | " (length rs) " |\n")))
                             cats))
           "\n**Spent** " (total out) " · **In** " (total in)
           " · **Portfolio** " (portfolio-total "E") " USD (" (portfolio-total "G") "% on cost)"
           " · **Open price alerts** " (length (records (items :category "money/markets"))))))

  ;; the PIM's weekly review, and the money as one more live block
  (defn review-with-money (monday)
    (str (pim-weekly-template monday)
         "\n## Money\n\n"
         (pim-block (str "(money-review \"" monday "\" \"" (date-add monday 6 :days) "\")"))
         "\n")))

;; ⌘⌥V — this week's review, money included
(bind "Mod-Alt-v"
  (ed-new (str "reviews/" (pim-monday *date*) " week.md") (review-with-money (pim-monday *date*))))
```

```eelisp
(str-contains (review-with-money "2026-10-26") "## Money")                  ; → true
(str-contains (review-with-money "2026-10-26") "<!-- eel: (money-review")   ; → true
(str-starts-with (review-with-money "2026-10-26") "# Week of 2026-10-26")   ; → true
```

`pim-block` writes a block with its result already in it, so the review is complete the moment it
opens — and the markers stay, so **⌘⌥U** refreshes the money with everything else.

Press **⌘⌥V** again later in the week and it opens the same note — `ed-new` never overwrites. Press
it next Monday and it's a new week's note; last week's stays in `reviews/`, a record you can
search.

## A habit, not a chore

- **Sunday evening**, **⌘⌥V**. Read it top to bottom; write three lines under *Reflection*.
- **Tick** what's done in *Coming up*; **⌘⌥F** to refile what's lingering in the inbox.
- **Look at the money** against the plan: **⌘⇧L** refreshes the Budget sheet from chapter 9.
- **Close the alerts** that fired: they're agenda items, under `money/markets`.

The PIM guide describes the review and lists every report function you could add as another
block: [the PIM guide](https://github.com/santacroce-tech/eeditor-next/blob/main/docs/PIM.md).

## What you have now

- `money-review` — spending by category, money in, the portfolio and open alerts, for any dates
- **⌘⌥V** — the PIM's weekly review with a *Money* section, all of it live blocks

→ [Chapter 16 — Sharing and backup](16-sharing-and-backup.md)
