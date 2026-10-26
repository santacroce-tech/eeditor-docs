# 3. The agenda

Notes are for thinking; the agenda is for *when*. It holds the things that have a date, a
priority or a repeat — *pay the rent on the 1st*, *call the bank tomorrow*, *review the portfolio
every Sunday* — and shows them in order, in a panel that is always there. This chapter fills it
the three ways you'll use every day: typing plain sentences, asking it questions, and letting
things repeat.

## The panel

The **Agenda** panel sits under the tags in the sidebar. At its top is a box: type

> pay the gas bill tomorrow !!

and press Enter. The item appears in the list with tomorrow's date and a priority badge. Click it
to open its editor — text, date, priority, notes, how it repeats, its categories — and change
anything. **📅** opens the month: drag an item to another day to move it.

Everything the panel does, the language does too — the panel is just the friendliest way to type.
The rest of this chapter is at the REPL (**⌘J**), so you can see exactly what happens.

## Plain sentences

`add` reads a sentence the way the panel's box does, taking a date, a priority and people out of
your words. `smart-parse` shows what it would read, without adding anything:

```eelisp
(dict-get (smart-parse "pay the gas bill tomorrow !!") :text)        ; → "pay the gas bill"
(dict-get (smart-parse "pay the gas bill tomorrow !!") :priority)    ; → 2
(dict-get (smart-parse "lunch with Ana in 3 days") :who)             ; → (list "Ana")
```

What it understands:

| You write | It reads |
|---|---|
| `2026-11-12` | that date |
| `today`, `tomorrow`, `yesterday`, `in 3 days`, `in 2 weeks` | a date counted from today |
| `!!!`, `!!`, `!` — or `urgent`, `asap`, `high priority`, `low priority` | priority 1, 2, 3 (or 4 for low) |
| `@sam`, or a name after *call, email, meet, text, with, for, from* | a person |

Two things it doesn't read yet: weekdays (`friday` stays in the text) and times (`at 15:00` stays in
the text — chapter 5 uses that for reminders). And it takes *the word* after *call* as a person, so
`call the bank` files a person called "the"; write `call Marta at the bank`.

Now add the week's real things:

```eelisp
(add "call Marta at the bank about the savings account tomorrow !!")
(add "renew the car insurance in 2 weeks")
(add "read the article Ana sent about index funds")
```

The panel shows all three — the last one without a date, which is fine: not everything has one.

## Saying exactly what you mean

When you'd rather not leave it to the parser, `add-item` takes each property by name:

```eelisp
(def rent (add-item "pay the rent" :when "2026-11-01" :priority 1))
(dict-get (item->dict rent) :when)        ; → "2026-11-01"
(dict-get (item->dict rent) :priority)    ; → "1"
```

Properties are stored as text — `"1"`, not `1` — which matters when you compare them. And any
property can be added later with `item-set`, including ones you make up:

```eelisp
(def rent-id (dict-get (item->dict rent) :id))
(item-set rent-id :notes "from the joint account" :amount "1200")
(dict-get (item->dict (item-get rent-id)) :amount)     ; → "1200"
```

## Things that repeat

Rent is due every month. Give the item a recurrence:

```eelisp
(item-set rent-id :recurrence (every 1 :months))
(dict-get (item->dict (item-get rent-id)) :recurrence)    ; → "every:1:months"
```

`(every n unit)` takes `:days`, `:weeks` or `:months`. Now, when you mark it done, it doesn't go
away — it moves to the next month:

```eelisp
(item-done rent-id)
(map (fn (r) (field-get r :when)) (records (items :search "pay the rent")))    ; → (list "2026-12-01")
```

A weekly one for Part IV — a portfolio review every Sunday — goes in the same way:

```eelisp
(add-item "review the portfolio" :when "2026-11-01" :priority 2 :recurrence (every 1 :weeks))
```

## Asking it questions

`items` answers with a result set — a grid at the REPL — and its filters combine:

```eelisp
(items)                                        ; everything
(items :priority 1)                            ; the urgent ones
(items :search "insurance")                    ; by words in the text
(items-between "2026-11-01" "2026-11-30")      ; November, both ends included
(items :when-before "2026-12-01")              ; due before December
```

To work with the answer — count it, map over it — turn it into a list with `records`. An item's
id is `(record-id r)`; its other fields are `(field-get r :when)` and friends:

```eelisp
(length (records (items :search "portfolio")))                                  ; → 1
(map (fn (r) (field-get r :text)) (records (items-between "2026-11-01" "2026-11-01")))  ; → (list "review the portfolio")
```

## A key: put this line on the agenda

You'll often write a task in a note before you think of the agenda. One key sends the line there,
read the way the panel's box reads it — date, priority and all:

```eelisp keys
(on-load
  ;; "- [ ] pay the gas bill tomorrow !!" → the words, without the list marker
  (defn line-words (line)
    (let (t (str-trim line))
      (cond (str-starts-with t "- [ ] ") (substr t 6 (str-len t))
            (str-starts-with t "- ")     (substr t 2 (str-len t))
            true                        t)))

  (defn agenda-this (line)
    (let (d (item->dict (add (line-words line))))
      (ed-message (str "On the agenda"
                       (if (nil? (dict-get d :when)) "" (str " for " (dict-get d :when)))
                       ": " (dict-get d :text))))))

;; ⌘⇧G — get this line on the agenda
(bind "Mod-Shift-g" (agenda-this *line-text*))
```

```eelisp
(line-words "- [ ] pay the gas bill tomorrow !!")    ; → "pay the gas bill tomorrow !!"
(line-words "  call the plumber")                    ; → "call the plumber"
```

The line stays as you wrote it; the agenda gets a copy. Chapter 5 goes further: the line and the
item become one — tick either and both are done.

## What you have now

- the agenda panel, the month view, and items typed as sentences
- `add`, `add-item`, `item-set`, `item-done`, `items` and `records` at the REPL
- rent that renews itself every month, and a weekly portfolio review for Part IV
- **⌘⇧G** — the caret's line, on the agenda

→ [Chapter 4 — Rules that file for you](04-rules-that-file-for-you.md)
