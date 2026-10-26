# EEditor & EELisp — the open catalog

**https://santacroce-tech.github.io/eeditor-docs/**

One place for everything [EEditor](https://eeditor.app) and [EELisp](https://eelisp.app) can do:

- **A path through it** — install, the first-hour tutorial, the PIM tutorial, the manual, the
  language book, embedding.
- **Every document** of both projects — the EEditor manual and tutorial, the EELisp book, guide and
  embedding notes — linked to each other.
- **The catalog** — one search over every EELisp builtin and prelude function, the spreadsheet
  functions, the snippets bundle, the editor commands and the default shortcuts, each with its
  signature, what it does, an example and a link to its documentation. `#q=countif` in the address
  opens it searching. The same data is published as `catalog.json`.

## Nothing here is written by hand

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

Only the landing page's frame lives here, in `catalog/`. To fix what a function's entry says, fix
it in the repository it comes from; the catalog picks it up on the next build.

The [Catalog workflow](.github/workflows/pages.yml) builds and publishes on every push here, every
morning, and on demand (Actions → Catalog → Run workflow).

## Building it locally

With the three repositories side by side:

```bash
python3 build.py                 # reads ../eeditor-next and ../eelisp-rs, writes _site/
python3 -m http.server -d _site  # then open http://localhost:8000
```

Python 3.9 or later, standard library only.

## Licence

MIT. EEditor and EELisp are developed by Roberto Santacroce Martins.
