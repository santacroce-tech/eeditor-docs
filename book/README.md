# Zero to Hero — building your own PIM in EEditor

One project, grown chapter by chapter: a personal workspace that runs your week and keeps an eye
on your money. Notes and a daily log, an agenda that files things for you, tables and forms for
your data, sheets that add it up, and prices fetched from the internet into a portfolio — all in
one folder, all in EEditor, and every piece of it EELisp you can read and change.

Each chapter ends with something that works, and the next builds on it. The code in every
chapter is run against the real engine whenever this book is built (`test_book.py`), so what you
read is what EELisp does.

**The companion workspace** — the folder as it stands after the chapters written so far — is one
download: [zero-to-hero-workspace.zip](zero-to-hero-workspace.zip). Unzip it and open the
*Zero-to-Hero* folder with **folder…** to start from any chapter. Its shortcut table, every key the
book adds, is [readable here](workspace/.eeditor/keybindings.eelisp); in the repository the folder
is `book/workspace/`.

## Part I — The workspace

1. [**A folder that is your life**](01-a-folder-that-is-your-life.md) — inbox, daily notes,
   projects, areas, reference; links, tags, and your notes seen from the REPL.
2. [**Your first shortcut**](02-your-first-shortcut.md) — the keybindings file as a program:
   a home for your functions, a meeting-note key, and a key that sends a line to the inbox.

## Part II — Time

3. **The agenda** — capture, dates, priorities, recurring items. *Being written.*
4. **Rules that file for you** — categories and `defrule`. *Being written.*
5. **Notes kept in step** — the PIM library: tasks in notes, refile, the clock, the tracker. *Being written.*
6. **A dashboard** — live blocks for the week, the inbox and your streaks. *Being written.*

## Part III — Data

7. **Tables** — accounts, holdings and transactions with `deftable`. *Being written.*
8. **Forms** — a data-entry screen for transactions. *Being written.*
9. **Sheets** — a budget on `sumif`, and where the money went. *Being written.*

## Part IV — Markets

10. [**Fetching prices**](10-fetching-prices.md) — crypto and exchange rates into a `prices`
    table, on a key and every 15 minutes.
11. **Keeping them fresh** — what changed, logged to the agenda. *Being written.*
12. **A portfolio sheet** — holdings × latest price, profit and loss. *Being written.*
13. **Alerts as agenda items** — "BTC below 50k — review", with a reminder. *Being written.*

## Part V — Putting it together

14. **The markets desk** — one form: a watchlist, the portfolio sheet, refresh and add buttons. *Being written.*
15. **The weekly review** — one key that writes the week's review note. *Being written.*
16. **Sharing and backup** — the desk as one HTML file, CSV in and out, what lives where. *Being written.*

## Conventions

- Keys are written for a Mac: **⌘** is Ctrl on Windows and Linux, **⌥** is Alt.
- The examples happen on **2026-10-26 at 09:30** — the day the tests pretend it is. Your dates
  will be today's.
- A block marked *keys* goes in your `.eeditor/keybindings.eelisp` (**⌘⇧K** opens it); any other
  EELisp block is for the REPL (**⌘J**).
- Where the engine or the app can't do something yet, the chapter says so, and
  [the roadmap](https://github.com/santacroce-tech/eeditor-next/blob/main/docs/ROADMAP.md) says
  what it would take.
