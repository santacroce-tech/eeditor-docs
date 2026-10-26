# EEditor & EELisp — the open catalog

**https://santacroce-tech.github.io/eeditor-docs/**

One place for everything [EEditor](https://eeditor.app) and [EELisp](https://eelisp.app) can do:

- **A path through it** — install, the first-hour tutorial, the PIM tutorial, the manual, the
  language book, embedding.
- **Every document** of both projects — the EEditor manual and tutorial, the EELisp book, guide and
  embedding notes — linked to each other.
- **The library** — every Markdown file of both repositories, the sample workspace EEditor offers a
  new folder (the welcome note, **TRY ME** — the PIM tutorial —, the dashboard, the mind map, the
  example forms) and the EELisp sources the catalog points into, each as a formatted page that links
  to the others. The files themselves are kept in [`content/`](content/README.md), readable right
  here on GitHub.
- **The catalog** — one search over every EELisp builtin and prelude function, the spreadsheet
  functions, the snippets bundle, the editor commands and the default shortcuts, each with its
  signature, what it does, an example and a link to its documentation. `#q=countif` in the address
  opens it searching. The same data is published as `catalog.json`.

- **Zero to Hero** — a book, written here in [`book/`](book/README.md): one PIM workspace grown
  chapter by chapter, with an agenda, tables, forms, sheets and live market prices. Every chapter's
  code runs against the real engine in CI (`test_book.py`), and the companion workspace is in
  [`book/workspace/`](book/workspace/).

## Nothing here is written by hand (except the book)

`build.py` reads [eeditor-next](https://github.com/santacroce-tech/eeditor-next) and
[eelisp-rs](https://github.com/santacroce-tech/eelisp-rs) and assembles the site:

| In the site | From |
|---|---|
| `eeditor/` | `eeditor-next/site` — manual, tutorial, downloads, example apps |
| `eelisp/` | `eelisp-rs/site` — the EELisp book (regenerated from the engine with `--regen`), guide, embedding |
| EELisp builtins and prelude | `eelisp-rs/docs/reference.md`, generated from the engine's own manual |
| Spreadsheet functions | `eeditor-next/src/sheets/functions.eelisp` — the `;;` comments above each `defn` |
| Snippets | `eeditor-next/src/snippets/zz-*.eelisp` |
| Commands and shortcuts | the manual's tables and `eeditor-next/src/keybindings/default.eelisp` |
| `content/` and the library | every tracked `*.md` and `LICENSE` of both repositories, the EELisp sources above, and the sample workspace |

Links between the documents stay inside the site: a link to eeditor.app, eelisp.app or a document on
GitHub that the library has is pointed at the copy here. What's left outside is what has to be — the
source repositories and the release downloads.

The sample workspace is made by `npm run pim:sample` in eeditor-next and dated the day it's made, so
it is refreshed only when asked: Actions → Catalog → Run workflow → *Make the sample workspace again*.

Only the landing page's frame lives here, in `catalog/`. To fix what a function's entry says, fix
it in the repository it comes from; the catalog picks it up on the next build.

The [Catalog workflow](.github/workflows/pages.yml) builds and publishes on every push here, every
morning, and on demand (Actions → Catalog → Run workflow).

## Building it locally

With the three repositories side by side:

```bash
python3 build.py                 # reads ../eeditor-next and ../eelisp-rs, writes _site/
python3 build.py --sync          # …and brings content/ in step with them
python3 -m http.server -d _site  # then open http://localhost:8000
```

Python 3.9 or later, standard library only.

The book's tests need the engine binary (`cargo build --release --bin eelisp` in eelisp-rs):

```bash
python3 test_book.py              # every chapter, against ../eelisp-rs's binary
python3 test_book.py --assemble   # first rewrite book/workspace's keybindings from the chapters
```

## Licence

MIT. EEditor and EELisp are developed by Roberto Santacroce Martins.
