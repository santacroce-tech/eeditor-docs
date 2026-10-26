# Zero to Hero — building your own PIM in EEditor

One project, grown chapter by chapter: a personal workspace that runs your week and keeps an eye
on your money. Notes and a daily log, an agenda that files things for you, tables and forms for
your data, sheets that add it up, and prices fetched from the internet into a portfolio — all in
one folder, all in EEditor, and every piece of it EELisp you can read and change.

Each chapter ends with something that works, and the next builds on it. The code in every
chapter is run against the real engine whenever this book is built (`test_book.py`), so what you
read is what EELisp does.

**The companion workspace** — the folder as it stands at the end of the book, with its notes,
forms, sheets, keybindings and a database holding everything the chapters typed — is one download: [zero-to-hero-workspace.zip](zero-to-hero-workspace.zip). Unzip it and open the
*Zero-to-Hero* folder with **folder…** to see the finished system, or to start from any chapter. Its shortcut table, every key the
book adds, is [readable here](workspace/.eeditor/keybindings.eelisp); in the repository the folder
is `book/workspace/`.

## Part I — The workspace

1. [**A folder that is your life**](01-a-folder-that-is-your-life.md) — inbox, daily notes,
   projects, areas, reference; links, tags, and your notes seen from the REPL.
2. [**Your first shortcut**](02-your-first-shortcut.md) — the keybindings file as a program:
   a home for your functions, a meeting-note key, and a key that sends a line to the inbox.

## Part II — Time

3. [**The agenda**](03-the-agenda.md) — plain sentences, properties, things that repeat, and
   asking it questions.
4. [**Rules that file for you**](04-rules-that-file-for-you.md) — categories as paths, rules that
   file every new item, and views for the questions you ask every day.
5. [**Notes kept in step**](05-notes-kept-in-step.md) — the PIM: task lines that *are* agenda items,
   capture, refile, reminders, the clock and the tracker.
6. [**A dashboard**](06-a-dashboard.md) — live blocks for the week, money, what's late and your
   streaks, refreshed with one key.

## Part III — Data

7. [**Tables**](07-tables.md) — accounts, transactions and holdings, and a key that turns
   *coffee 3.50 #food* into a row.
8. [**Forms**](08-forms.md) — a screen for transactions: controls, handlers, validation.
9. [**Sheets**](09-sheets.md) — a Ledger poured from the table and a Budget against a plan, on
   `sumif` and `countif`.

## Part IV — Markets

10. [**Fetching prices**](10-fetching-prices.md) — crypto and exchange rates into a `prices`
    table, on a key and on the clock.
11. [**Keeping them fresh**](11-keeping-them-fresh.md) — the change since the fetch before, big
    moves in today's note, a table that stays small.
12. [**A portfolio sheet**](12-a-portfolio-sheet.md) — holdings × latest price: value, gain, the
    total in two currencies, recalculated on every fetch.
13. [**Alerts as agenda items**](13-alerts-as-agenda-items.md) — "bitcoin below 85000 — review",
    a task for today and a notification, once a day.

## Part V — Putting it together

14. [**The markets desk**](14-the-markets-desk.md) — one form, three pages: the watchlist, the
    portfolio sheet itself, and the alerts.
15. [**The weekly review**](15-the-weekly-review.md) — the PIM's review with a money section,
    all of it live.
16. [**Sharing and backup**](16-sharing-and-backup.md) — what lives where, a backup you can read,
    keys kept private, and a form as one HTML file.

## Conventions

- Keys are written for a Mac: **⌘** is Ctrl on Windows and Linux, **⌥** is Alt.
- The examples happen on **2026-10-26 at 09:30** — the day the tests pretend it is. Your dates
  will be today's.
- A block marked *keys* goes in your `.eeditor/keybindings.eelisp` (**⌘⇧K** opens it); any other
  EELisp block is for the REPL (**⌘J**).
- Where the engine or the app can't do something yet, the chapter says so, and
  [the roadmap](https://github.com/santacroce-tech/eeditor-next/blob/main/docs/ROADMAP.md) says
  what it would take.
