# 9. Sheets

The transactions table knows every coffee; it doesn't know where the month went. A sheet does
that: a grid where the formulas are EELisp, so `sumif` and `countif` sit next to anything you've
written yourself. This chapter builds two — a **Ledger** that mirrors the table, and a **Budget**
that adds it up by category, against a plan — and a key that brings both up to date.

## Two sheets, two jobs

A sheet is a file: `Budget.eesheet`, next to your notes. Right-click a folder and choose
**New sheet…**, or at the REPL:

```eelisp
(sheet-new "Ledger")
(sheet-new "Budget")
```

Why two? The Ledger is *data* — rewritten from the table whenever you like. The Budget is
*formulas* — written once, reading the Ledger. Keeping them apart means refreshing the data never
disturbs the formulas.

## The Ledger: a table, poured into a sheet

`sheet-put` writes a block of values with its top-left corner at a cell. Given a query, it writes a
header row and then the rows:

```eelisp
(sheet-put "Ledger" "A1" (query transactions :order "day"))
(first (sheet-rows "Ledger" "A1:E1"))    ; → (list "day" "account" "amount" "category" "note")
(length (sheet-rows "Ledger" "A:A"))     ; → 13
```

Day in A, account in B, amount in C, category in D, note in E: thirteen rows, the header and twelve
transactions. `A:A` means *the whole of column A* — down to the last filled row, however many
there are. Open `Ledger.eesheet` and it's all there, sortable by eye, with an empty note as an
empty cell.

## The Budget: formulas that read the Ledger

A formula is a cell that starts with `=`, followed by one EELisp expression. Cell names in capitals
are values: `B2` is what's in B2, `B2:B8` a list of them, `Ledger!C:C` column C of the Ledger.

Type into **Budget** — one row per category, and what you planned to spend:

| | A | B | C | D | E | F |
|---|---|---|---|---|---|---|
| **1** | Category | Plan | Spent | Left | Times | Average |
| **2** | food | 400 | `=(round (- 0 (sumif Ledger!D:D A2 Ledger!C:C)) 2)` | `=(round (- B2 C2) 2)` | `=(countif Ledger!D:D A2)` | *(below)* |

- `sumif` adds up column C (amount) on the rows where column D (category) is what A2 says.
  Spending is negative in the table, so `(- 0 …)` turns it into a positive amount spent, and
  `round … 2` keeps it to cents (chapter 7 says why).
- `countif` counts the rows where column D says *food*.
- **Left** is the plan minus what's spent.

Then copy row 2 down for the other categories: select B2:F2, drag the fill handle (the square at
the selection's corner) down — `A2` becomes `A3`, `A4`… in each copy. Or type them all at once from
the REPL, which is what this does — `sheet-set` given a list of rows types a block:

```eelisp
(def budget-plan (list (list "food" 400) (list "rent" 1200) (list "bills" 150) (list "transport" 120)
                       (list "fun" 100) (list "health" 60) (list "other" 80)))

(defn budget-row (n category plan)
  (list category plan
        (str "=(round (- 0 (sumif Ledger!D:D A" n " Ledger!C:C)) 2)")
        (str "=(round (- B" n " C" n ") 2)")
        (str "=(countif Ledger!D:D A" n ")")
        (str "=(let (a (averageif Ledger!D:D A" n " Ledger!C:C)) (if (nil? a) 0 (round (- 0 a) 2)))")))

(sheet-set "Budget" "A1"
  (cons (list "Category" "Plan" "Spent" "Left" "Times" "Average")
        (map (fn (i) (budget-row (+ i 2) (first (nth budget-plan i)) (second (nth budget-plan i))))
             (range (length budget-plan)))))

(sheet-set "Budget" "A10" (list (list "Total" "=(sum B2:B8)" "=(round (sum C2:C8) 2)" "=(round (- B10 C10) 2)")))
```

**Average** is the one formula that has to be careful: `averageif` gives `nil` when a category has
no rows, and `(round nil 2)` is an error. So it checks first — `(if (nil? a) 0 …)`. (EELisp can't
catch an error yet, so there's no `iferror`; it's on the
[roadmap](https://github.com/santacroce-tech/eeditor-next/blob/main/docs/ROADMAP.md).)

What October looks like:

```eelisp
(sheet-get "Budget" "C2")     ; → 235.1
(sheet-get "Budget" "D2")     ; → 164.9
(sheet-get "Budget" "E2")     ; → 4
(sheet-get "Budget" "C10")    ; → 1591.6
(sheet-get "Budget" "D10")    ; → 518.4
```

Food: 235.10 spent of 400 over four trips — the three markets and chapter 8's lunch. The total
matches `spent` from chapter 7, as it should; 518.40 of the plan is left.

## A formula can call anything

Formulas aren't limited to spreadsheet functions. Your own functions are there — `spent` from
chapter 7, straight from the table:

```eelisp
(sheet-set "Budget" "H1" "Spent in October (from the table)")
(sheet-set "Budget" "H2" "=(spent \"2026-10-01\" \"2026-10-31\")")
(sheet-get "Budget" "H2")     ; → 1591.6
```

One thing to know: a formula that reads a *table* — not other cells — isn't recalculated when the
table changes. EEditor doesn't know it read the table. Press **↻** in the sheet's toolbar, or
`(sheet-recalc "Budget")`, to bring those up to date. Cells read from other cells, and from other
sheets that are open, update by themselves.

## A key: bring the Ledger and the Budget up to date

New transactions arrive all month — from **⌘⇧E**, from the form. One key pours the table into the
Ledger again and recalculates the Budget:

```eelisp keys
(on-load
  ;; rewrite the Ledger from the transactions table, then recalculate the Budget
  (defn ledger-refresh ()
    (let (old (length (sheet-rows "Ledger" "A:A")))
      (do (if (> old 0) (sheet-delete-rows "Ledger" 1 old) nil)
          (sheet-put "Ledger" "A1" (query transactions :order "day"))
          (sheet-recalc "Budget")
          (count-records transactions)))))

;; ⌘⇧L — the Ledger and the Budget, up to date
(bind "Mod-Shift-l" (ed-message (str "Ledger: " (ledger-refresh) " transactions")))
```

It deletes the Ledger's old rows first — writing fewer rows over more would leave the old ones
behind — then writes the table, then recalculates the Budget, so even the formulas that read the
table directly are current.

```eelisp
(insert transactions {:day "2026-10-26" :account "Card" :amount -9.9 :category "food" :note "bakery"})
(ledger-refresh)              ; → 13
(sheet-get "Budget" "C2")     ; → 245
```

## Sharing a sheet

- **PDF** in the toolbar prints the sheet as a table, formats and all.
- **Export as CSV** in the tree's right-click menu writes the values for any other program, and
  **Import as sheet** brings a CSV in.
- A sheet opens showing the values it was saved with — opening one runs no code, even a sheet
  someone sent you. Formulas run when you change what they read, or press ↻.

## What you have now

- `Ledger.eesheet` — the transactions table as a sheet, rewritten on demand
- `Budget.eesheet` — plan, spent, left, times and average per category, with totals
- formulas with `sumif`, `countif`, `averageif`, cross-sheet references and your own functions
- **⌘⇧L** — the Ledger and the Budget up to date

That's Part III. Part IV turns to markets — it starts with
[Chapter 10 — Fetching prices](10-fetching-prices.md).
