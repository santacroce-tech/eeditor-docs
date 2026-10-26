#!/usr/bin/env python3
"""Run the book's code against the real engine, chapter by chapter, so the book can't drift from
what EELisp does.

    python3 test_book.py                       # ../eelisp-rs's binary, ../eeditor-next's prelude
    EELISP_BIN=… python3 test_book.py --eeditor path/to/eeditor-next

Every chapter starts a fresh `eelisp --serve` in a copy of the companion workspace (book/workspace),
with the editor prelude loaded (so `ed-*` commands exist), the context a key press has (*date*,
*time*, *file*…) fixed to one day, and `http-get` answering from book/fixtures instead of the
network. Then each ```eelisp block runs, in order, in that one session:

  ```eelisp            every form is evaluated; a form whose line ends in  ; → value  must equal
                       that value (compared with = after evaluating both)
  ```eelisp keys       a keybindings file: each (bind …), (on-load …), (on-tick …) and (on-start …)
                       body is evaluated the way the app would — on-load first — and must not fail
  ```eelisp norun      shown, not run (a sketch, or something that needs a real key or network)

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

# The day the book's examples happen on: fixed, so a test means the same thing every day.
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
            i = src.find("\n", i) if src.find("\n", i) >= 0 else n
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
                i = src.find("\n", i) if src.find("\n", i) >= 0 else n
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
        db = workspace / ".eeditor" / "eeditor.db"
        db.parent.mkdir(parents=True, exist_ok=True)
        self.p = subprocess.Popen(
            [binary, "--serve", "--db", str(db), "--workspace", str(workspace)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=workspace,
        )

    def ev(self, src: str) -> dict:
        self.p.stdin.write(json.dumps({"src": src}) + "\n")
        self.p.stdin.flush()
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("the engine stopped")
        return json.loads(line)

    def close(self) -> None:
        self.p.stdin.close()
        self.p.wait(timeout=10)


def setup(engine: Engine, prelude: str) -> None:
    for src in (
        prelude,
        f'(def *date* "{DAY}") (def *time* "{TIME}") (def *now* "{DAY} {TIME}:00") (def *file* "")'
        ' (def *cursor* 0) (def *line* 1) (def *col* 1) (def *line-text* "") (def *selection* "") (def *buffer* "")',
        # the network, from book/fixtures
        "(def *fixtures* (list "
        + " ".join(f"(list {lisp_string(u)} {lisp_string((BOOK / 'fixtures' / f).read_text())})" for u, f in FIXTURES.items())
        + "))",
        "(defn http-get (url)"
        "  (let (hit (filter (fn (f) (str-starts-with url (first f))) *fixtures*))"
        '    (if (empty? hit) {:status 404 :body "no fixture"} {:status 200 :body (second (first hit))})))',
    ):
        r = engine.ev(src)
        if not r.get("ok"):
            raise RuntimeError(f"setup failed: {r.get('error')}")


def blocks(md: str) -> list[tuple[str, str, int]]:
    """(info, code, line) for every ```eelisp block."""
    out = []
    for m in re.finditer(r"^```eelisp([^\n]*)\n(.*?)^```", md, re.M | re.S):
        out.append((m.group(1).strip(), m.group(2), md.count("\n", 0, m.start()) + 1))
    return out


def run_chapter(path: Path, binary: str, prelude: str) -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp) / "workspace"
        shutil.copytree(BOOK / "workspace", ws)
        engine = Engine(binary, ws)
        try:
            setup(engine, prelude)
            for info, code, line in blocks(path.read_text(encoding="utf-8")):
                where = f"{path.name}:{line}"
                if "norun" in info.split():
                    continue
                if "keys" in info.split():
                    failures += run_keys(engine, code, where)
                    continue
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
                            failures.append(f"{where}  {form[:70]}\n      expected {want}, got {json.dumps(got, ensure_ascii=False)[:120]}")
        finally:
            engine.close()
    return failures


def run_keys(engine: Engine, code: str, where: str) -> list[str]:
    failures = []
    forms = [f for f, _ in top_forms(code)]
    parsed = [head_and_body(f) for f in forms]
    # on-load first, as the app does, so the bindings can call what it defines
    order = [p for p in parsed if p[0] == "on-load"] + [p for p in parsed if p[0] != "on-load"]
    for head, args in order:
        if head == "bind":
            key, body = args[0], args[1:]
            label = f"(bind {key} …)"
        elif head in ("on-load", "on-tick", "on-start"):
            body, label = args, f"({head} …)"
        else:
            body, label = [f"({head} {' '.join(args)})"], head
        if not body:
            continue
        r = engine.ev("(list " + " ".join(body) + ")" if head != "on-load" else "(do " + " ".join(body) + ")")
        if not r.get("ok"):
            failures.append(f"{where}  {label}\n      → {r.get('error')}")
    return failures


def assemble(eeditor: Path) -> Path:
    """Write the companion workspace's keybindings: EEditor's defaults, then every chapter's
    keys blocks in order — the file a reader has after following the book."""
    default = (eeditor / "src" / "keybindings" / "default.eelisp").read_text(encoding="utf-8")
    parts = [default.rstrip() + "\n"]
    for ch in sorted(BOOK.glob("[0-9][0-9]-*.md")):
        md = ch.read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", md, re.M).group(1)
        keys = [code for info, code, _ in blocks(md) if "keys" in info.split() and code.strip() not in default]
        if keys:
            parts.append(f"\n;; ══ Zero to Hero — chapter {title} " + "═" * 30 + "\n\n" + "\n".join(k.rstrip() + "\n" for k in keys))
    out = BOOK / "workspace" / ".eeditor" / "keybindings.eelisp"
    out.write_text("".join(parts), encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eeditor", type=Path, default=HERE.parent / "eeditor-next")
    ap.add_argument("chapters", nargs="*", help="only these chapter files")
    ap.add_argument("--assemble", action="store_true", help="rewrite book/workspace/.eeditor/keybindings.eelisp from the chapters, then test")
    args = ap.parse_args()
    if args.assemble:
        print(f"wrote {assemble(args.eeditor).relative_to(HERE)}")
    binary = os.environ.get("EELISP_BIN") or str(HERE.parent / "eelisp-rs" / "target" / "release" / "eelisp")
    prelude = (args.eeditor / "src" / "keybindings" / "prelude.eelisp").read_text(encoding="utf-8")
    chapters = [BOOK / c for c in args.chapters] if args.chapters else sorted(BOOK.glob("[0-9][0-9]-*.md"))
    total = 0
    for ch in chapters:
        n = sum(1 for info, _, _ in blocks(ch.read_text(encoding="utf-8")) if "norun" not in info.split())
        failures = run_chapter(ch, binary, prelude)
        total += len(failures)
        print(("ok    " if not failures else "FAIL  ") + f"{ch.name} — {n} blocks")
        for f in failures:
            print("    " + f)
    # the companion workspace's keybindings must hold every keys block the book shows
    kb = (BOOK / "workspace" / ".eeditor" / "keybindings.eelisp").read_text(encoding="utf-8")
    missing = [
        f"{ch.name}:{line}"
        for ch in sorted(BOOK.glob("[0-9][0-9]-*.md"))
        for info, code, line in blocks(ch.read_text(encoding="utf-8"))
        if "keys" in info.split() and code.strip() not in kb
    ]
    if missing:
        print("FAIL  book/workspace/.eeditor/keybindings.eelisp is missing the keys blocks at " + ", ".join(missing))
        total += len(missing)
    else:
        print("ok    the companion workspace's keybindings hold every keys block")
    print("all passed" if total == 0 else f"{total} failed")
    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
