# The library

Every Markdown document of EEditor and EELisp, the sample workspace the app offers a new
folder, and the EELisp sources the catalog points into — copied here by `build.py`, kept in
step with the two repositories. They read as they are on GitHub; the catalog site shows them
formatted, linked to each other: https://santacroce-tech.github.io/eeditor-docs/library/

Don't edit them here: change them where they come from, and the next build brings the change.

The folders mirror where each file lives — `eeditor/` is eeditor-next, `eelisp/` is eelisp-rs,
`sample-workspace/` is what EEditor writes into a new folder — so the links between them work.
Below, the same files by topic.

## Zero to Hero — the book

One project grown chapter by chapter: a personal workspace with an agenda, tables, forms, sheets and live market prices. Every chapter's code is tested against the engine.

- [Zero to Hero — contents](../book/README.md) — Book · `README.md`
- [1. A folder that is your life](../book/01-a-folder-that-is-your-life.md) — Book · `01-a-folder-that-is-your-life.md`
- [2. Your first shortcut](../book/02-your-first-shortcut.md) — Book · `02-your-first-shortcut.md`
- [10. Fetching prices](../book/10-fetching-prices.md) — Book · `10-fetching-prices.md`
- [The companion workspace's keybindings](../book/workspace/.eeditor/keybindings.eelisp) — Book · `workspace/.eeditor/keybindings.eelisp`

## Start here

What EEditor and EELisp are, the welcome note a new folder gets, and the hands-on tutorial.

- [Welcome to EEditor](sample-workspace/welcome.md) — Sample · `welcome.md`
- [TRY ME — the PIM tutorial](sample-workspace/TRY%20ME.md) — Sample · `TRY ME.md`
- [EEditor — README](eeditor/README.md) — EEditor · `README.md`
- [EELisp — README](eelisp/README.md) — EELisp · `README.md`
- [The EELisp book — contents](eelisp/docs/README.md) — EELisp · `docs/README.md`
- [1. Introduction](eelisp/docs/01-introduction.md) — EELisp · `docs/01-introduction.md`
- [Every shortcut — a mind map](sample-workspace/examples/EEditor.mindmap.md) — Sample · `examples/EEditor.mindmap.md`
- [Todo](sample-workspace/todo.md) — Sample · `todo.md`
- [Roadmap](sample-workspace/notes/roadmap.md) — Sample · `notes/roadmap.md`

## The EELisp language

Syntax, the language, data, how it documents itself, and every function.

- [2. Syntax and values](eelisp/docs/02-syntax.md) — EELisp · `docs/02-syntax.md`
- [3. The language](eelisp/docs/03-language.md) — EELisp · `docs/03-language.md`
- [4. Working with data](eelisp/docs/04-data.md) — EELisp · `docs/04-data.md`
- [8. A self-documenting language](eelisp/docs/08-self-documenting.md) — EELisp · `docs/08-self-documenting.md`
- [Function reference](eelisp/docs/reference.md) — EELisp · `docs/reference.md`

## Agenda and PIM

Items, categories, rules and views; the PIM's notes kept in step with the agenda; and the sample's dashboard, inbox and daily note.

- [EEditor as a PIM — org-mode habits, in EELisp](eeditor/docs/PIM.md) — EEditor · `docs/PIM.md`
- [6. The agenda](eelisp/docs/06-agenda.md) — EELisp · `docs/06-agenda.md`
- [The PIM library — pim.eelisp](eeditor/docs/pim/pim.eelisp) — EEditor · `docs/pim/pim.eelisp`
- [Dashboard](sample-workspace/dashboard.md) — Sample · `dashboard.md`
- [Daily note — 2026-10-26 · Monday](sample-workspace/2026-10-26.md) — Sample · `2026-10-26.md`
- [Inbox](sample-workspace/inbox.md) — Sample · `inbox.md`
- [Bills](sample-workspace/bills.md) — Sample · `bills.md`
- [Project note — Home](sample-workspace/projects/home.md) — Sample · `projects/home.md`
- [Project note — The new site](sample-workspace/projects/site.md) — Sample · `projects/site.md`
- [Capture form — Org-capture for EEditor](sample-workspace/pim/Capture.eeform) — Sample · `pim/Capture.eeform`

## Spreadsheets

Sheets whose formulas are EELisp: the design, sheets from code, the spreadsheet functions (countif, vlookup…), and what is still missing.

- [Spreadsheets — plan](eeditor/docs/SPREADSHEET.md) — EEditor · `docs/SPREADSHEET.md`
- [7. Sheets](eelisp/docs/07-sheets.md) — EELisp · `docs/07-sheets.md`
- [Spreadsheet functions for sheet formulas](eeditor/src/sheets/functions.eelisp) — EEditor · `src/sheets/functions.eelisp`
- [Sheets — what's missing](eeditor/docs/SHEETS-LATER.md) — EEditor · `docs/SHEETS-LATER.md`

## Database and forms

dBASE-style tables on SQLite, and forms you draw and run — with the example forms.

- [5. The database](eelisp/docs/05-database.md) — EELisp · `docs/05-database.md`
- [Forms — plan](eeditor/docs/FORMS.md) — EEditor · `docs/FORMS.md`
- [Form apps — plan](eeditor/docs/FORM-APPS.md) — EEditor · `docs/FORM-APPS.md`
- [Contacts form — An EEditor form over a table](sample-workspace/Contacts.eeform) — Sample · `Contacts.eeform`
- [Agenda form](sample-workspace/examples/Agenda.eeform) — Sample · `examples/Agenda.eeform`
- [Books form](sample-workspace/examples/Books.eeform) — Sample · `examples/Books.eeform`
- [Functions form — Every function the engine knows, its source, and a place to try it](sample-workspace/examples/Functions.eeform) — Sample · `examples/Functions.eeform`
- [Office form](sample-workspace/examples/Office.eeform) — Sample · `examples/Office.eeform`
- [Orders form](sample-workspace/examples/Orders.eeform) — Sample · `examples/Orders.eeform`
- [Spectrum form — A ZX Spectrum 48K, running in a form](sample-workspace/examples/Spectrum.eeform) — Sample · `examples/Spectrum.eeform`
- [Tables form](sample-workspace/examples/Tables.eeform) — Sample · `examples/Tables.eeform`

## Keybindings and snippets

The shortcut table is EELisp: the defaults, the editor commands it can call, and the snippets bundle.

- [The default keybindings](eeditor/src/keybindings/default.eelisp) — EEditor · `src/keybindings/default.eelisp`
- [The editor prelude — ed-* commands](eeditor/src/keybindings/prelude.eelisp) — EEditor · `src/keybindings/prelude.eelisp`
- [The sample's keybindings, with the PIM](sample-workspace/.eeditor/keybindings.eelisp) — Sample · `.eeditor/keybindings.eelisp`
- [The snippets bundle (zzeelisp)](eeditor/src/snippets/README.md) — EEditor · `src/snippets/README.md`
- [Bitcoin utilities](eeditor/src/snippets/zz-bitcoin.eelisp) — EEditor · `src/snippets/zz-bitcoin.eelisp`
- [Unit and encoding conversion utilities](eeditor/src/snippets/zz-convert.eelisp) — EEditor · `src/snippets/zz-convert.eelisp`
- [Password, hash, and cipher utilities](eeditor/src/snippets/zz-crypto.eelisp) — EEditor · `src/snippets/zz-crypto.eelisp`
- [Date and time utilities](eeditor/src/snippets/zz-date.eelisp) — EEditor · `src/snippets/zz-date.eelisp`
- [Fun and games utilities](eeditor/src/snippets/zz-fun.eelisp) — EEditor · `src/snippets/zz-fun.eelisp`
- [Math and number utilities](eeditor/src/snippets/zz-math.eelisp) — EEditor · `src/snippets/zz-math.eelisp`
- [Network utilities](eeditor/src/snippets/zz-network.eelisp) — EEditor · `src/snippets/zz-network.eelisp`
- [Lookup tables and reference utilities](eeditor/src/snippets/zz-reference.eelisp) — EEditor · `src/snippets/zz-reference.eelisp`
- [Text manipulation utilities](eeditor/src/snippets/zz-text.eelisp) — EEditor · `src/snippets/zz-text.eelisp`
- [Timezone conversion utility](eeditor/src/snippets/zz-timeat.eelisp) — EEditor · `src/snippets/zz-timeat.eelisp`

## Architecture and embedding

How the engine is built, using it from Rust, JSON or a browser, and the plan behind the rebuild.

- [9. Architecture](eelisp/docs/09-architecture.md) — EELisp · `docs/09-architecture.md`
- [10. Embedding](eelisp/docs/10-embedding.md) — EELisp · `docs/10-embedding.md`
- [eelisp-web — the engine in a browser](eelisp/web/README.md) — EELisp · `web/README.md`
- [EEditor + EELisp — Complete Analysis & Rebuild Plan](eeditor/docs/ANALYSIS.md) — EEditor · `docs/ANALYSIS.md`

## The project

The roadmap, releasing, the websites, themes, the ZX Spectrum, the app's native plugins, and the licences.

- [Roadmap](eeditor/docs/ROADMAP.md) — EEditor · `docs/ROADMAP.md`
- [Releasing EEditor](eeditor/docs/RELEASING.md) — EEditor · `docs/RELEASING.md`
- [The eeditor.app website](eeditor/site/README.md) — EEditor · `site/README.md`
- [The eelisp.app website](eelisp/site/README.md) — EELisp · `site/README.md`
- [VB6 theme: a portable spec](eeditor/docs/themes/vb6/README.md) — EEditor · `docs/themes/vb6/README.md`
- [ZX Spectrum — the plan, and where it stands](eeditor/docs/spectrum/PLAN.md) — EEditor · `docs/spectrum/PLAN.md`
- [ZX Spectrum machine — engine boundary](eeditor/docs/spectrum/ZXSPECTRUM.md) — EEditor · `docs/spectrum/ZXSPECTRUM.md`
- [The iOS files plugin](eeditor/src-tauri/plugins/ios/README.md) — EEditor · `src-tauri/plugins/ios/README.md`
- [iOS files plugin — permissions (generated)](eeditor/src-tauri/plugins/permissions/autogenerated/reference.md) — EEditor · `src-tauri/plugins/permissions/autogenerated/reference.md`
- [The app's native plugins](eeditor/src-tauri/plugins/README.md) — EEditor · `src-tauri/plugins/README.md`
- [Licence — eeditor-next](eeditor/LICENSE) — EEditor · `LICENSE`
- [Licence — eelisp-rs](eelisp/LICENSE) — EELisp · `LICENSE`
