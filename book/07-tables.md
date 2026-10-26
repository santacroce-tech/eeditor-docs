# 7. Tables

Part III is about money, and money is data: amounts, days, accounts, categories, the same shape
row after row. A note is the wrong place for that — you can't add up a paragraph. EELisp has
tables for it: dBASE-style tables on SQLite, in the same database as your agenda
(`.eeditor/eeditor.db`), so they're in the folder, backed up with it, and readable by sheets and
forms. This chapter makes the three tables the rest of the book stands on.

## Three tables

```eelisp
(deftable accounts (name:string kind:string currency:string))

(deftable transactions
  (day:string account:string amount:number
   (category :type string :default "other")
   note:string))

(deftable holdings
  (symbol:string (kind :type choice :choices ("crypto" "stock" "fx")) qty:number cost:number))
```

A field is `name:type`, or a list when it needs more: a `:default`, `:required true`, `:choices`.
The types are `string`, `number`, `bool`, `date`, `memo` (long text) and `choice`. Choices guide
the forms that edit a table (chapter 8 shows a dropdown); `insert` itself doesn't refuse a value
outside them.

- **transactions** — money in is positive, money out is negative; `day` is `"2026-10-05"`, which
  sorts and compares as text in date order
- **holdings** — what you own, for Part IV: how much, and what it cost you in total (in USD)

`deftable` is safe to repeat — on an existing table it keeps the rows — so it can live in your
keybindings' `on-load` (below).

## Rows in

```eelisp
(insert accounts {:name "Checking" :kind "bank" :currency "USD"})
(insert accounts {:name "Savings" :kind "bank" :currency "USD"})
(insert accounts {:name "Card" :kind "credit" :currency "USD"})

(insert transactions {:day "2026-10-01" :account "Checking" :amount 3200 :category "salary"})
(insert transactions {:day "2026-10-01" :account "Checking" :amount -1200 :category "rent"})
(insert transactions {:day "2026-10-03" :account "Card" :amount -86.4 :category "food" :note "market"})
(insert transactions {:day "2026-10-07" :account "Card" :amount -42 :category "transport" :note "fuel"})
(insert transactions {:day "2026-10-09" :account "Card" :amount -64.3 :category "food" :note "market"})
(insert transactions {:day "2026-10-12" :account "Checking" :amount -58 :category "bills" :note "electricity"})
(insert transactions {:day "2026-10-15" :account "Checking" :amount -500 :category "savings"})
(insert transactions {:day "2026-10-15" :account "Savings" :amount 500 :category "savings"})
(insert transactions {:day "2026-10-18" :account "Card" :amount -35 :category "fun" :note "cinema"})
(insert transactions {:day "2026-10-21" :account "Card" :amount -71.9 :category "food" :note "market"})
(insert transactions {:day "2026-10-24" :account "Card" :amount -18.5})

(insert holdings {:symbol "bitcoin" :kind "crypto" :qty 0.05 :cost 3100})
(insert holdings {:symbol "ethereum" :kind "crypto" :qty 1.2 :cost 2900})
```

A dict literal like `{:day "2026-10-01" …}` is one row. The last transaction has no category:
it gets the default, `"other"`. `insert` returns the row it made, id included.

**`(browse transactions)`** at the REPL shows the table as a grid — sortable, scrollable. It's the
quickest way to look.

## Rows out

`query` asks; `records` turns the answer into a list:

```eelisp
(count-records transactions)                                            ; → 11
(count-records transactions :where "category = ?" :params (list "food")) ; → 3

(def food (records (query transactions :where "category = ?" :params (list "food") :order "day")))
(map (fn (r) (field-get r :amount)) food)       ; → (list -86.4 -64.3 -71.9)
(sum (map (fn (r) (field-get r :amount)) food)) ; → -222.6
```

`:where` is SQL, with `?` where a value goes and the values in `:params` — always pass values
that way, never by gluing text into the condition. `:order` sorts (`:desc true` for newest
first), `:limit` keeps the first few.

Two functions you'll use from now on — the total of a category, and spending over a period:

```eelisp
(defn amounts (rows) (map (fn (r) (field-get r :amount)) rows))

(defn spent (from to)
  (round (- 0 (sum (filter (fn (a) (< a 0))
                           (amounts (records (query transactions
                                                    :where "day >= ? AND day <= ? AND category != ?"
                                                    :params (list from to "savings")))))))
         2))

(spent "2026-10-01" "2026-10-31")    ; → 1576.1
```

Moving money to savings isn't spending, so `spent` leaves the `savings` category out. And it
rounds to cents: numbers are binary fractions underneath, so adding up a column of amounts can
give `1576.1000000000001`. Round a sum of money before you show it or compare it.

## Changing and removing

```eelisp
(def fuel (first (records (query transactions :where "note = ?" :params (list "fuel")))))
(update transactions (record-id fuel) {:amount -45})
(field-get (first (records (query transactions :where "note = ?" :params (list "fuel")))) :amount)   ; → -45
```

`update` changes the fields you name and leaves the rest; `(delete transactions id)` removes a row.
A row's id is `(record-id r)`.

## A key: this line is a transaction

You'll spend money all day and you won't open a form for a coffee. Write it in today's *Log*, the
way you'd say it — `coffee 3.50 #food`, `+3200 salary #salary` — and send it to the table with
**⌘⇧E**:

```eelisp keys
(on-load
  (deftable accounts (name:string kind:string currency:string))
  (deftable transactions
    (day:string account:string amount:number (category :type string :default "other") note:string))
  (deftable holdings
    (symbol:string (kind :type choice :choices ("crypto" "stock" "fx")) qty:number cost:number))

  (defn amounts (rows) (map (fn (r) (field-get r :amount)) rows))
  (defn spent (from to)
    (round (- 0 (sum (filter (fn (a) (< a 0))
                             (amounts (records (query transactions
                                                      :where "day >= ? AND day <= ? AND category != ?"
                                                      :params (list from to "savings")))))))
           2))

  (def default-account "Card")

  ;; "coffee 3.50 #food" → {:amount -3.5 :category "food" :note "coffee"}
  ;; "+3200 salary #salary" → money in: {:amount 3200 …}
  (defn parse-spend (line)
    (let (words (filter (fn (w) (!= w "")) (str-split (line-words line) " "))
          num   (first (filter (fn (w) (str-matches w "^[+-]?[0-9]+([.,][0-9]+)?$")) words))
          tag   (first (filter (fn (w) (str-starts-with w "#")) words))
          rest  (filter (fn (w) (and (!= w num) (!= w tag))) words))
      (if (nil? num)
          nil
          {:amount   (let (n (->number (str-replace (str-replace num "+" "") "," ".")))
                       (if (str-starts-with num "+") n (- 0 n)))
           :category (if (nil? tag) "other" (substr tag 1 (str-len tag)))
           :note     (str-join " " rest)})))

  (defn spend-line (line)
    (let (t (parse-spend line))
      (if (nil? t)
          (ed-message "No amount on this line — write it like: coffee 3.50 #food")
          (do (insert transactions (dict-merge t {:day *date* :account default-account}))
              (ed-message (str (if (> (dict-get t :amount) 0) "In: " "Spent: ")
                               (abs (dict-get t :amount)) " · " (dict-get t :category))))))))

;; ⌘⇧E — the caret's line, as a transaction
(bind "Mod-Shift-e" (spend-line *line-text*))
```

```eelisp
(parse-spend "coffee 3.50 #food")       ; → {:amount -3.5 :category "food" :note "coffee"}
(parse-spend "- +3200 salary #salary")  ; → {:amount 3200 :category "salary" :note "salary"}
(parse-spend "lunch with Ana")          ; → nil
```

The file has `amounts` and `spent` from above as well. A function you typed at the REPL is gone
when EEditor quits — anything a key, a form or a sheet will call belongs in `on-load`, and the
next chapters call `spent`.

`parse-spend` reuses `line-words` from chapter 3, so a `- ` list marker is ignored. A comma works as the
decimal point too: `3,50`. Every transaction lands on `default-account` — change it in the
file to whichever you use most.

## What you have now

- three tables — `accounts`, `transactions`, `holdings` — defined at every launch
- October's transactions, and two holdings for Part IV
- `query`, `records`, `count-records`, `update`, `delete`, `browse`; `amounts` and `spent`
- **⌘⇧E** — *coffee 3.50 #food* becomes a transaction

Typing rows at the REPL is fine for you and no one else. Chapter 8 gives the table a proper
screen.

→ [Chapter 8 — Forms](08-forms.md)
