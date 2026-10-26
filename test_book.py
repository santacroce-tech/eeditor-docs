#!/usr/bin/env python3
"""Run the book's code against the real engine, so the book can't drift from what EELisp does.

    python3 test_book.py                 # ../eelisp-rs's binary, ../eeditor-next's preludes
    python3 test_book.py --assemble      # first rewrite the companion workspace's keybindings,
                                         # and keep the database and sheets the run makes
    EELISP_BIN=… python3 test_book.py --eeditor path/to/eeditor-next

The book is one project, so it runs as one: a single `eelisp --serve` session, chapter after
chapter, in a copy of the companion workspace (book/workspace) — what a reader who followed every
chapter would have. Before the first chapter the session gets what the app loads at launch: the
editor prelude (`ed-*`), the forms prelude (`ui-*`), the spreadsheet functions (`countif`…). The
context a key press has (*date*, *time*…) is fixed to one day, and `http-get` answers from
book/fixtures instead of the network.

In a chapter:

  ```eelisp            every form is evaluated; one whose line ends in  ; → value  must equal
                       that value (both evaluated, compared with =). A comment that doesn't start
                       with → — "; e.g. …" — is only for the reader.
  ```eelisp keys       part of the keybindings file: (on-load …) bodies are evaluated first, then
                       every (bind …), (on-tick …) and (on-start …) body, which must not fail
  ```eelisp form F     the whole of the form file F: evaluated as Run does, and it must be the same
                       text as book/workspace/F
  ```eelisp keys superseded   tested like keys, but a later chapter replaces it, so it isn't in
                       the companion workspace's keybindings
  ```eelisp norun      shown, not run (needs a real key, a real network, or a person)
  <!-- test: pim -->   the PIM library (eeditor-next docs/pim/pim.eelisp) is installed here,
                       as the chapter tells the reader to do

Standard library only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK = HERE / "book"
WORKSPACE = BOOK / "workspace"
# What a run leaves behind that the companion download includes: the database and the sheets
MADE = BOOK / "workspace-made"

# The day the book's examples happen on: fixed, so a test means the same thing every day.
# (The agenda's own date words — "tomorrow" — read the real clock; the book doesn't assert those.)
DAY, TIME = "2026-10-26", "09:30"

# URL prefix → fixture file, for the stand-in http-get
FIXTURES = {
    "https://api.coingecko.com/api/v3/simple/price": "coingecko-simple-price.json",
    "https://api.frankfurter.app/latest": "frankfurter-latest.json",
}


def lisp_string(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def top_forms(src: str) -> list[tuple[str, str]]:
    """Top-level forms, each with the comment that ends its last line ("" if none)."""
    forms, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c.isspace():
            i += 1
            continue
        if c == ";":
            j = src.find("\n", i)
            i = j if j >= 0 else n
            continue
        start, depth = i, 0
        while i < n:
            c = src[i]
            if c == '"':
                i += 1
                while i < n and src[i] != '"':
                    i += 2 if src[i] == "\\" else 1
            elif c == ";":
                if depth == 0:
                    break
                j = src.find("\n", i)
                i = j if j >= 0 else n
                continue
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            elif depth == 0 and c.isspace():
                break
            i += 1
        form = src[start:i].strip()
        eol = src.find("\n", i)
        rest = src[i:eol if eol >= 0 else n]
        m = re.match(r"\s*;+\s*(.*)$", rest)
        comment = m.group(1).strip() if m else ""
        if m:
            i = eol if eol >= 0 else n
        if form:
            forms.append((form, comment))
    return forms


def head_and_body(form: str) -> tuple[str, list[str]]:
    """(bind "Mod-x" a b) → ("bind", ['"Mod-x"', 'a', 'b'])."""
    inner = form.strip()[1:-1]
    parts = [f for f, _ in top_forms(inner)]
    return (parts[0] if parts else ""), parts[1:]


class Engine:
    def __init__(self, binary: str, workspace: Path) -> None:
        self.db = workspace / ".eeditor" / "eeditor.db"
        self.db.parent.mkdir(parents=True, exist_ok=True)
        self.p = subprocess.Popen(
            [binary, "--serve", "--db", str(self.db), "--workspace", str(workspace)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=workspace,
        )

    def ev(self, src: str) -> dict:
        self.p.stdin.write(json.dumps({"src": src}) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("the engine stopped")
        return json.loads(line)

    def must(self, src: str, what: str) -> None:
        r = self.ev(src)
        if not r.get("ok"):
            raise RuntimeError(f"{what}: {r.get('error')}")

    def close(self) -> None:
        self.p.stdin.close()
        self.p.wait(timeout=10)


def context() -> str:
    return (f'(def *date* "{DAY}") (def *time* "{TIME}") (def *now* "{DAY} {TIME}:00") (def *file* "")'
            ' (def *cursor* 0) (def *line* 1) (def *col* 1) (def *lines* 1) (def *line-text* "")'
            ' (def *line-from* 0) (def *line-to* 0) (def *sel-from* 0) (def *sel-to* 0)'
            ' (def *selection* "") (def *buffer* "")')


def setup(engine: Engine, eeditor: Path) -> None:
    """What the app has loaded by the time a reader types anything."""
    for rel in ("src/keybindings/prelude.eelisp", "src/forms/prelude.eelisp", "src/sheets/functions.eelisp"):
        engine.must((eeditor / rel).read_text(encoding="utf-8"), f"loading {rel}")
    engine.must(context(), "the context")
    engine.must(
        "(def *fixtures* (list "
        + " ".join(f"(list {lisp_string(u)} {lisp_string((BOOK / 'fixtures' / f).read_text())})" for u, f in FIXTURES.items())
        + "))",
        "the fixtures",
    )
    engine.must(
        "(defn http-get (url)"
        "  (let (hit (filter (fn (f) (str-starts-with url (first f))) *fixtures*))"
        '    (if (empty? hit) {:status 404 :body "no fixture"} {:status 200 :body (second (first hit))})))',
        "the stand-in http-get",
    )


def blocks(md: str) -> list[tuple[str, str, int]]:
    """(info, code, line) for every ```eelisp block."""
    return [
        (m.group(1).strip(), m.group(2), md.count("\n", 0, m.start()) + 1)
        for m in re.finditer(r"^```eelisp([^\n]*)\n(.*?)^```", md, re.M | re.S)
    ]


def keys_parts(code: str) -> list[tuple[str, list[str]]]:
    """A keybindings file's top-level forms as (head, args), the on-load ones first — as the app runs them."""
    parsed = [head_and_body(f) for f, _ in top_forms(code)]
    return [p for p in parsed if p[0] == "on-load"] + [p for p in parsed if p[0] != "on-load"]


def run_keys(engine: Engine, code: str, where: str, only_load: bool = False) -> list[str]:
    failures = []
    for head, args in keys_parts(code):
        if only_load and head != "on-load":
            continue
        if head == "bind":
            body, label = args[1:], f"(bind {args[0]} …)"
        elif head in ("on-load", "on-tick", "on-start"):
            body, label = args, f"({head} …)"
        else:
            body, label = [f"({head} {' '.join(args)})"], head
        if not body:
            continue
        engine.ev(context())  # a key, a tick, a start: each gets its context fresh
        r = engine.ev(("(do " if head == "on-load" else "(list ") + " ".join(body) + ")")
        if not r.get("ok"):
            failures.append(f"{where}  {label}\n      → {r.get('error')}")
    return failures


def run_forms(engine: Engine, code: str, where: str) -> list[str]:
    failures = []
    for form, comment in top_forms(code):
        want = comment[1:].strip() if comment.startswith("→") else None
        r = engine.ev(f"(def *got* {form})" if want is not None else form)
        if not r.get("ok"):
            failures.append(f"{where}  {form[:70]}\n      → {r.get('error')}")
            continue
        if want is not None:
            check = engine.ev(f"(= *got* {want})")
            if not (check.get("ok") and check.get("result") is True):
                got = engine.ev("*got*").get("result")
                failures.append(f"{where}  {form[:70]}\n      expected {want}, got {json.dumps(got, ensure_ascii=False)[:160]}")
    return failures


def run_chapter(engine: Engine, path: Path, eeditor: Path) -> tuple[int, list[str]]:
    md = path.read_text(encoding="utf-8")
    failures: list[str] = []
    if "<!-- test: pim -->" in md:
        pim = (eeditor / "docs" / "pim" / "pim.eelisp").read_text(encoding="utf-8")
        failures += run_keys(engine, pim, f"{path.name} (installing the PIM)", only_load=True)
    n = 0
    for info, code, line in blocks(md):
        words = info.split()
        where = f"{path.name}:{line}"
        if "norun" in words:
            continue
        n += 1
        engine.ev(context())
        if "keys" in words:
            failures += run_keys(engine, code, where)
        elif "form" in words:
            i = words.index("form")
            name = words[i + 1] if len(words) > i + 1 else ""
            target = WORKSPACE / name
            if not name or not target.exists():
                failures.append(f"{where}  form block names {name!r}, which isn't in book/workspace")
            elif target.read_text(encoding="utf-8").strip() != code.strip():
                failures.append(f"{where}  book/workspace/{name} differs from the block — copy one over the other")
            failures += run_forms(engine, code, where)
        else:
            failures += run_forms(engine, code, where)
    return n, failures


def chapters() -> list[Path]:
    return sorted(BOOK.glob("[0-9][0-9]-*.md"))


def assemble(eeditor: Path) -> Path:
    """The companion workspace's keybindings: EEditor's defaults, then every chapter's keys blocks
    in order — with the PIM library where its chapter installs it. The file a reader has after
    following the book."""
    default = (eeditor / "src" / "keybindings" / "default.eelisp").read_text(encoding="utf-8")
    pim = (eeditor / "docs" / "pim" / "pim.eelisp").read_text(encoding="utf-8")
    parts = [default.rstrip() + "\n"]
    for ch in chapters():
        md = ch.read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", md, re.M).group(1)
        keys = [code for info, code, _ in blocks(md)
                if "keys" in info.split() and "superseded" not in info.split() and code.strip() not in default]
        section = []
        if "<!-- test: pim -->" in md:
            section.append(pim.rstrip() + "\n")
            (WORKSPACE / "pim").mkdir(exist_ok=True)
            shutil.copy(eeditor / "docs" / "pim" / "Capture.eeform", WORKSPACE / "pim" / "Capture.eeform")
        section += [k.rstrip() + "\n" for k in keys]
        if section:
            parts.append(f"\n;; ══ Zero to Hero — chapter {title} " + "═" * 30 + "\n\n" + "\n".join(section))
    out = WORKSPACE / ".eeditor" / "keybindings.eelisp"
    out.write_text("".join(parts), encoding="utf-8")
    return out


def keys_in_workspace() -> list[str]:
    """Every keys block must be in the companion workspace's keybindings, as written."""
    kb = (WORKSPACE / ".eeditor" / "keybindings.eelisp").read_text(encoding="utf-8")
    return [
        f"{ch.name}:{line}"
        for ch in chapters()
        for info, code, line in blocks(ch.read_text(encoding="utf-8"))
        if "keys" in info.split() and "superseded" not in info.split() and code.strip() not in kb
    ]


def launch_check(binary: str, eeditor: Path) -> list[str]:
    """Open the finished companion workspace the way the app does at launch — a fresh engine, the
    keybindings file and nothing typed at a REPL — then press every key, run every tick, start
    every form and recalculate every sheet. A function the book only ever defined at the REPL
    shows up here as an undefined symbol."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "Zero-to-Hero"
        shutil.copytree(WORKSPACE, ws)
        if MADE.exists():
            shutil.copytree(MADE, ws, dirs_exist_ok=True)
        engine = Engine(binary, ws)
        try:
            setup(engine, eeditor)
            kb = (ws / ".eeditor" / "keybindings.eelisp").read_text(encoding="utf-8")
            failures += run_keys(engine, kb, "launch: keybindings.eelisp")
            for form in sorted(ws.rglob("*.eeform")):
                rel = form.relative_to(ws).as_posix()
                code = form.read_text(encoding="utf-8")
                failures += run_forms(engine, code, f"launch: {rel}")
                m = re.search(r":on-load\s+([^\s()]+)", code)
                if m:
                    engine.ev(context())
                    r = engine.ev(f"(ui-run {m.group(1)} {{}})")
                    if not r.get("ok"):
                        failures.append(f"launch: {rel} :on-load {m.group(1)}\n      → {r.get('error')}")
            for sheet in sorted(ws.rglob("*.eesheet")):
                name = sheet.relative_to(ws).as_posix()[: -len(".eesheet")]
                engine.ev(context())
                r = engine.ev(f'(sheet-recalc "{name}")')
                if not r.get("ok"):
                    failures.append(f"launch: {name}.eesheet recalc\n      → {r.get('error')}")
                    continue
                bad = engine.ev(f'(filter (fn (c) (not (nil? (nth c 4)))) (dict-get (sheet-open "{name}") :cells))')
                for c in bad.get("result") or []:
                    failures.append(f"launch: {name}.eesheet row {int(c[0]) + 1} col {int(c[1]) + 1}: {c[4]}")
        finally:
            engine.close()
    return failures


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eeditor", type=Path, default=HERE.parent / "eeditor-next")
    ap.add_argument("--assemble", action="store_true",
                    help="rewrite book/workspace's keybindings from the chapters, and keep what the run makes in book/workspace-made")
    ap.add_argument("only", nargs="*", help="report only these chapters (all of them still run, in order)")
    args = ap.parse_args()
    binary = os.environ.get("EELISP_BIN") or str(HERE.parent / "eelisp-rs" / "target" / "release" / "eelisp")
    if args.assemble:
        print(f"wrote {assemble(args.eeditor).relative_to(HERE)}")

    total = 0
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "Zero-to-Hero"
        shutil.copytree(WORKSPACE, ws)
        engine = Engine(binary, ws)
        try:
            setup(engine, args.eeditor)
            for ch in chapters():
                n, failures = run_chapter(engine, ch, args.eeditor)
                total += len(failures)
                if not args.only or ch.name in args.only:
                    print(("ok    " if not failures else "FAIL  ") + f"{ch.name} — {n} blocks")
                    for f in failures:
                        print("    " + f)
        finally:
            engine.close()
        if args.assemble:
            if MADE.exists():
                shutil.rmtree(MADE)
            (MADE / ".eeditor").mkdir(parents=True)
            shutil.copy(ws / ".eeditor" / "eeditor.db", MADE / ".eeditor" / "eeditor.db")
            for sheet in ws.rglob("*.eesheet"):
                target = MADE / sheet.relative_to(ws)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(sheet, target)
            print(f"kept {sum(1 for f in MADE.rglob('*') if f.is_file())} files the run made, in {MADE.relative_to(HERE)}")

    launch = launch_check(binary, args.eeditor)
    total += len(launch)
    print(("ok    " if not launch else "FAIL  ") + "launch check — the companion workspace opened fresh: every key, tick, form and sheet")
    for f in launch:
        print("    " + f)

    missing = keys_in_workspace()
    if missing:
        print("FAIL  book/workspace/.eeditor/keybindings.eelisp is missing the keys blocks at " + ", ".join(missing)
              + " — run with --assemble")
        total += len(missing)
    else:
        print("ok    the companion workspace's keybindings hold every keys block")
    print("all passed" if total == 0 else f"{total} failed")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
