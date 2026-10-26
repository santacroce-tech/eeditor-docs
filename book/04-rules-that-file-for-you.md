# 4. Rules that file for you

An agenda with fifty items is a list; an agenda where every bill is already under *money* and
every call under *calls* is a system. This chapter gives your items categories, then writes the
rules that hand them out — so you type *send the invoice to Bob* and it lands under
*money/bills* without you doing anything. Then it saves the questions you ask most as views.

## Categories are paths

A category is a name like `money/bills`: the part before the slash is its parent. Filing an item
under `money/bills` puts it under `money` too, as far as every question is concerned.

```eelisp
(defcategory money/bills)
(defcategory money/savings)
(defcategory money/insurance)
(defcategory home)
(defcategory health)
(categories)    ; e.g. "health\nhome\nmoney\n  money/bills\n  money/insurance\n  money/savings"
```

`categories` prints the tree. File an item by hand with `assign` (and take it back with
`unassign`):

```eelisp
(def insurance (first (records (items :search "car insurance"))))
(assign (record-id insurance) "money/insurance")
(length (records (items :category "money")))    ; → 1
```

Asking for `money` found the item filed under `money/insurance` — the parent includes its
children. The **⚙** button on the agenda panel does all of this with the mouse: categories on
one side, rules on the other.

## Rules

A rule is a condition and what to do when it holds, both in EELisp. The condition sees the
item's fields as plain names — `text`, `notes`, `when`, `priority`, `who` — plus a few helpers:

```eelisp
(defrule bills
  :when (str-matches text "(?i)invoice|bill|rent")
  :assign "money/bills")

(defrule savings
  :when (str-matches text "(?i)bank|savings")
  :assign "money/savings")

(defrule doctors
  :when (str-matches text "(?i)dentist|doctor|pharmacy")
  :assign "health")
```

`(?i)` makes the match ignore case. Rules don't run by themselves yet: `apply-rules` runs every
rule over every item, and says how many it changed.

```eelisp
(apply-rules)                                     ; e.g. 2 — the bank call and the rent
(length (records (items :category "money/savings")))    ; → 1
```

A rule can do more than file: `:action` runs any EELisp, with the item's `id` at hand.

```eelisp
(defrule bills-are-urgent-near-the-1st
  :when (and (has-category "money/bills") (overdue?))
  :action (item-set id :priority 1))
```

`(has-category "money")` and `(overdue?)` — the date is past — are two of the helpers; the
EELisp book's agenda chapter lists the rest. A rule whose condition fails with an error is skipped,
so one bad rule never stops the others.

## Rules on every new item

Running `apply-rules` by hand gets old. Turn it on for good:

```eelisp
(auto-categorize true)
(dict-get (item->dict (add "send the invoice to Bob tomorrow")) :categories)    ; → (list "money/bills")
```

Every item `add` or `add-item` makes now goes through the rules as it's added — the panel's box
and **⌘⇧G** included.

`auto-categorize` lasts until EEditor quits; rules, categories and views are kept in the database.
So the definitions go in your keybindings file — `on-load` runs on every launch and every save,
and defining a rule or a view again under the same name replaces it rather than adding a second:

```eelisp keys
(on-load
  (defcategory money/bills)
  (defcategory money/savings)
  (defcategory money/insurance)
  (defcategory home)
  (defcategory health)
  (defrule bills    :when (str-matches text "(?i)invoice|bill|rent") :assign "money/bills")
  (defrule savings  :when (str-matches text "(?i)bank|savings")      :assign "money/savings")
  (defrule doctors  :when (str-matches text "(?i)dentist|doctor|pharmacy") :assign "health")
  (defview money    :filter (has-category "money") :sort-by when)
  (defview late     :filter (overdue?) :sort-by when)
  (defview urgent   :filter (= priority "1") :sort-by when)
  (auto-categorize true))
```

## Views: the questions you ask every day

A view is a saved question. Its filter is a condition, like a rule's:

```eelisp
(defview money  :filter (has-category "money") :sort-by when)
(defview late   :filter (overdue?) :sort-by when)
(defview urgent :filter (= priority "1") :sort-by when)    ; properties are text: "1", not 1

(show money)                                  ; everything about money, by date
(length (records (show money)))               ; → 4
(views)                                       ; their names
```

The four in *money*: the rent, the bank call, the insurance and Bob's invoice. Chapter 6 puts
views like these on a dashboard that refreshes with a key.

## What you have now

- categories as a tree: `money/bills`, `money/savings`, `money/insurance`, `home`, `health`
- three rules that file items as they're added, and `auto-categorize` on at every launch
- views — `money`, `late`, `urgent` — for the questions you ask every day

→ [Chapter 5 — Notes kept in step](05-notes-kept-in-step.md)
