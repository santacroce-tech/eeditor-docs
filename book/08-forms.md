# 8. Forms

A table is for the computer; a form is for you. This chapter draws a screen over the
`transactions` table — a day, an amount, a category, an account, a note, Save — with the latest
rows underneath. It's the same kind of thing as a Visual Basic form: controls you place on a
canvas, and EELisp that runs when you click them.

## A form is a file

Right-click a folder in the tree and choose **New form…**, call it *Transactions*. A
`Transactions.eeform` opens in a tab with three modes along the top:

- **Design** — the canvas, a toolbox of controls, and the selected control's properties
- **Code** — the same file as text
- **▶ run** — the form, working

The file is EELisp. Its first part, `(form …)`, is the layout the designer writes: one line per
control, with its name, where it sits and how big it is. Everything after it is yours — the
handlers the controls call. Drawing in *Design* rewrites only the `(form …)` part, so your code is
never touched, and anything you can do on the canvas you can also type in *Code*.

## The whole form

Here it is — paste it into *Code* to skip the drawing:

```eelisp form Transactions.eeform
;; Transactions.eeform — money in and out, one row at a time, with the latest rows underneath.
;; Zero to Hero, chapter 8. Needs the tables from chapter 7.

(form "Transactions" :size (600 520) :on-load tx-load
  (label    lblDay      :text "Day" :at (16 20) :size (80 24))
  (date     dtDay       :required true :at (104 16) :size (160 28))
  (label    lblAmount   :text "Amount" :at (16 56) :size (80 24))
  (textbox  txtAmount   :number true :min 0 :required true :placeholder "3.50" :at (104 52) :size (120 28))
  (checkbox chkIn       :text "money in" :at (236 56) :size (120 24))
  (label    lblCategory :text "Category" :at (16 92) :size (80 24))
  (dropdown ddCategory  :items ("food") :required true :at (104 88) :size (160 28))
  (label    lblAccount  :text "Account" :at (16 128) :size (80 24))
  (dropdown ddAccount   :items ("Card") :required true :at (104 124) :size (160 28))
  (label    lblNote     :text "Note" :at (16 164) :size (80 24))
  (textbox  txtNote     :placeholder "what for" :at (104 160) :size (300 28))
  (button   btnSave     :text "Save" :submit true :default true :at (104 200) :size (90 30) :on-click tx-save)
  (button   btnDelete   :text "Delete selected" :at (204 200) :size (130 30) :on-click tx-delete)
  (label    lblStatus   :at (344 204) :size (240 24))
  (grid     grdRecent   :columns ("day" "account" "amount" "category" "note") :sortable true :filter true
                        :at (16 244) :size (568 236))
  (label    lblTotal    :at (16 488) :size (568 24)))

(def tx-categories (list "food" "rent" "bills" "transport" "fun" "health" "salary" "savings" "other"))

(defn tx-month-start () (str (substr *date* 0 8) "01"))

(defn tx-refresh ()
  (ui-set "grdRecent" :rows (query transactions :order "day" :desc true :limit 100))
  (ui-set "lblTotal" :text (str "Spent since " (tx-month-start) ": " (spent (tx-month-start) *date*))))

(defn tx-load (f)
  (ui-set "dtDay" :value *date*)
  (ui-set "ddCategory" :items tx-categories)
  (ui-set "ddAccount" :items (map (fn (r) (field-get r :name)) (records (query accounts :order "name"))))
  (ui-set "ddAccount" :value default-account)
  (tx-refresh))

(defn tx-save (f)
  (let (amount (ui-get f "txtAmount")
        signed (if (ui-get f "chkIn") amount (- 0 amount)))
    (insert transactions {:day (ui-get f "dtDay") :account (ui-get f "ddAccount") :amount signed
                          :category (ui-get f "ddCategory") :note (or (ui-get f "txtNote") "")})
    (ui-set "txtAmount" :value "")
    (ui-set "txtNote" :value "")
    (ui-set "chkIn" :value false)
    (ui-set "lblStatus" :text (str "Saved " signed " · " (ui-get f "ddCategory")))
    (ui-focus "txtAmount")
    (tx-refresh)))

(defn tx-delete (f)
  (let (row (ui-get f "grdRecent"))
    (if (nil? row)
        (ui-message "Pick a row first")
        (do (delete transactions (dict-get row "id"))
            (ui-set "lblStatus" :text "Deleted")
            (tx-refresh)))))
```

Reading it from the top:

- **The layout.** `date`, `textbox`, `checkbox`, `dropdown`, `button`, `label` and `grid` are
  controls; each has a name (`txtAmount`), `:at (x y)` and `:size (w h)`. `:number true` makes the
  amount box hand your code a number; `:required true` refuses to save while it's empty. The grid
  is `:sortable` (click a column) and `:filter` (a box that narrows the rows as you type).
- **Events name functions.** `:on-load tx-load` runs when the form starts; `:on-click tx-save`
  when Save is pressed. `:submit true` means Save checks the required fields first; `:default true`
  means Enter in any box presses it.
- **A handler gets the form.** `f` is a dict of every control's value: `(ui-get f "txtAmount")`
  is the amount, `(ui-get f "grdRecent")` the selected row — a dict with its `"id"`.
- **A handler changes the form by asking.** `(ui-set "lblStatus" :text "Saved")` queues a change;
  EEditor applies them in order when the handler returns. `:rows` fills a grid straight from a
  `query`, `:items` fills a dropdown, `:value` sets what a control holds.

The handlers use what you already have: the `accounts` and `transactions` tables, `spent` and
`default-account` from chapter 7. Forms run on the same engine as your keybindings, so everything
in your `on-load` is there.

## Run it

Press **▶ run**. The day is today, the account is your default, the grid shows October. Type
`12.50`, pick *food*, note *lunch*, Enter: the row appears at the top of the grid and the total
underneath goes up. Tick *money in* for income. Select a row and **Delete selected** removes it.
**stop** goes back to *Design*.

A handler is a plain function, so you can try one at the REPL without the form. `ui-run` calls it
with a form's values and returns the changes it asked for:

```eelisp
(length (ui-run tx-load {}))    ; → 6

(ui-run tx-save {"txtAmount" 12.5 "chkIn" false "dtDay" "2026-10-26"
                 "ddCategory" "food" "ddAccount" "Card" "txtNote" "lunch"})
(count-records transactions :where "note = ?" :params (list "lunch"))    ; → 1
(spent "2026-10-01" "2026-10-31")    ; → 1591.6
```

October's spending was 1576.10 in chapter 7; the fuel correction (+3) and this lunch (+12.50)
make it 1591.60.

## Open it from a key

A form doesn't need its tab: `(ed-form "Transactions")` opens it in a window of its own, floating
beside whatever note you're in.

```eelisp keys
;; ⌘⇧U — the transactions form, in its own window
(bind "Mod-Shift-u" (ed-form "Transactions"))
```

## Going further with forms

- **Validation beyond required:** `:min`, `:max` and `:pattern` on boxes, and an `:on-validate`
  handler on a button that returns a message to refuse the save.
- **Pages:** a `tabs` control with `:pages`, and `:page "Details"` on the controls that belong to a
  page — chapter 14's markets desk uses them.
- **A sheet inside a form:** the `sheet` control shows a `.eesheet` beside the form, live —
  chapter 14 again.
- **The example forms** in EEditor's samples (Office, Books, Orders, Tables, Agenda) show every
  control; the [forms guide](https://github.com/santacroce-tech/eeditor-next/blob/main/docs/FORMS.md)
  lists them all.

## What you have now

- `Transactions.eeform`: add income and spending with a screen, see the latest rows, delete one
- handlers as plain functions — `tx-load`, `tx-save`, `tx-delete` — testable with `ui-run`
- **⌘⇧U** — the form, in its own window

→ [Chapter 9 — Sheets](09-sheets.md)
