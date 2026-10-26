# 16. Sharing and backup

Sixteen chapters of work live in one folder. This last one makes sure you can't lose it, shows
what's safe to share, and how to hand someone one of your forms as a single file that runs in any
browser.

## What lives where

| What | Where | Kind of file |
|---|---|---|
| Notes, the dashboard, reviews | `*.md`, anywhere in the folder | text |
| Sheets — Ledger, Budget, Portfolio | `*.eesheet` | SQLite, one file per sheet |
| Forms — Transactions, MarketsDesk | `*.eeform` | text (EELisp) |
| Your keys and all your functions | `.eeditor/keybindings.eelisp` | text (EELisp) |
| The agenda, your tables — transactions, holdings, prices, alerts — and the PIM's clock, tracker and done log | `.eeditor/eeditor.db` | SQLite |

Everything is in the folder; nothing is kept anywhere else. `.eeditor/` is hidden from the file
tree, but it's an ordinary folder on disk.

## Backup: copy the folder

The simplest backup is the whole folder, copied somewhere else — Time Machine, an external disk, a
cloud drive. Two rules keep the databases safe:

- **Copy with EEditor closed**, or at least not in the middle of saving: a database copied while
  it's being written can come out half-written.
- **Open the folder on one computer at a time.** Syncing services copy files, not database
  transactions; two copies of EEditor writing the same `eeditor.db` through a sync service can
  lose changes.

## Backup you can read: JSON

A copied database needs EEditor (or any SQLite tool) to read. For a backup you can read in ten
years, write your tables out as JSON — text, one file per table.

The agenda has its own export, with its categories, rules and views:

```eelisp
(export-agenda "eeditor" :format :json :path (str (current-dir) "/.eeditor/agenda-export.json"))
(str-starts-with (read-note ".eeditor/agenda-export.json") "{")    ; → true
```

`"eeditor"` is the name of the folder's agenda (`(agendas)` lists them). The path is given in full,
built from `(current-dir)` — the folder — so the file lands in it and not wherever EEditor happens
to run from. It goes into `.eeditor/` because that folder always exists: `export-agenda` doesn't
create folders, and EELisp has no way to make one. `ed-write` does — so the key below exports
there first, then copies the file into the dated backup folder with `ed-write`.

Your own tables need a few lines. A row prints as a record, not as JSON, so turn each row into a
dict of its fields first:

```eelisp
(defn row->dict (r fields)
  (reduce (fn (d f) (dict-set d f (field-get r f))) {} fields))

;; a table's rows by its name — query takes the name itself, so the call is built as text
(defn table-rows (name)
  (records (eval (parse (str "(query " name ")")))))

(defn table-json (name fields)
  (json-stringify (map (fn (r) (row->dict r fields)) (table-rows name))))

(length (json-parse (table-json "holdings" (list :symbol :kind :qty :cost))))    ; → 3
```

Three holdings — the two from chapter 7 and chapter 12's purchase. One key writes them all:

```eelisp keys
(on-load
  (defn row->dict (r fields)
    (reduce (fn (d f) (dict-set d f (field-get r f))) {} fields))

  (defn table-rows (name)
    (records (eval (parse (str "(query " name ")")))))

  (defn table-json (name fields)
    (json-stringify (map (fn (r) (row->dict r fields)) (table-rows name))))

  ;; table name → its fields, for the backup
  (def backup-tables
    (list (list "accounts"     (list :name :kind :currency))
          (list "transactions" (list :day :account :amount :category :note))
          (list "holdings"     (list :symbol :kind :qty :cost))
          (list "prices"       (list :symbol :kind :price :currency :at :source))
          (list "alerts"       (list :symbol :direction :level :fired))))

  ;; one ed-write per table, one for the agenda's own export, then a message
  (defn backup-all ()
    (let (dir (str "backup/" *date*))
      (do (export-agenda "eeditor" :format :json :path (str (current-dir) "/.eeditor/agenda-export.json"))
          (append (map (fn (t) (ed-write (str dir "/" (first t) ".json") (table-json (first t) (second t))))
                       backup-tables)
                  (list (ed-write (str dir "/agenda.json") (read-note ".eeditor/agenda-export.json"))
                        (ed-message (str "Backed up " (length backup-tables) " tables and the agenda to " dir))))))))

;; ⌘⇧0 — everything as JSON, in backup/<today>/
(bind "Mod-Shift-0" (backup-all))
```

```eelisp
(length (backup-all))    ; → 7
```

Six `ed-write`s and a message: **⌘⇧0** writes `backup/2026-10-26/transactions.json` and the rest,
and the agenda's export beside them as `agenda.json`. Run it weekly — on Sunday, after the review.

Reading one back is the same in reverse — `json-parse` the file, `insert` each dict:

```eelisp norun
(map (fn (d) (insert holdings d)) (json-parse (read-note "backup/2026-10-26/holdings.json")))
(import-agenda (str (current-dir) "/backup/2026-10-26/agenda.json"))
```

(Into an empty table — inserting into one that still has the rows doubles them.)

## Keep keys out of what you share

Chapter 10's stock prices needed an API key. Never write a key into your keybindings or a note you
share: put it in a note of its own, in a folder you don't share, and read it:

```eelisp norun
(def av-key (str-trim (read-note "private/alphavantage-key.md")))
```

When you share the folder, leave `private/` out. (A proper place for secrets is on
[the roadmap](https://github.com/santacroce-tech/eeditor-next/blob/main/docs/ROADMAP.md).)

## Sharing the system, not your data

Your notes and forms are text; your money is in `eeditor.db`. To give someone the *system* — the
keys, the forms, the dashboard, the sheets' layout — share the folder without
`.eeditor/eeditor.db`, without `private/`, and with notes they shouldn't see removed. When they
open it, EEditor makes a fresh, empty database; their `on-load` creates the tables; they type their
own transactions.

## A form as one file: Export as HTML

Right-click a form in the tree and choose **Export as HTML…**: EEditor writes one `.html` file
beside it that runs in any browser, offline — the EELisp engine is inside it, compiled to
WebAssembly, with the form, every form it opens, and the sheets it shows. Email it, put it on a
USB stick.

What doesn't go with it — and why the markets desk won't work exported as it is:

- **Your keybindings don't.** The exported file has the form's own code and nothing else. The desk
  calls `latest`, `change-pct`, `refresh-prices`, `portfolio-total` — all from your keybindings.
  A form meant for export defines what it uses *in the form file*.
- **The network doesn't.** The WebAssembly engine has no `http-get` (a browser has its own rules
  about the network), so an exported form can show prices it was given, not fetch new ones.
- **Your data doesn't, at first.** The exported app keeps its own data in the browser that runs
  it. Its **Save data…** downloads that data as a SQLite file and **Open data…** loads one — that's
  how data moves between people and computers.

So the forms worth exporting are the self-contained ones: a calculator, a small database screen
that defines its own tables, a viewer for numbers someone sends along. EEditor's samples include
two to try in the browser — the Office app and the Functions browser.

## The end — and what's next

You started with an empty folder. You have:

- a structure for notes, a daily log, an inbox, and keys of your own
- an agenda that files things for you, notes kept in step with it, a dashboard
- tables, a form and sheets for your money, a budget against a plan
- live prices, a portfolio worth knowing, alerts that become tasks, a desk to see it all
- a weekly review, and a backup you can read in ten years

All of it EELisp you wrote and can change. Where to go from here:

- **The catalog** — every function and command, searchable: [the catalog](../../index.html#catalog)
- **The EELisp book** — the whole language: [EELisp documentation](https://eelisp.app/docs.html)
- **The roadmap** — what's coming, and what you could help build:
  [ROADMAP.md](https://github.com/santacroce-tech/eeditor-next/blob/main/docs/ROADMAP.md)

← [Contents](README.md)
