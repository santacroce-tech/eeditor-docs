#!/usr/bin/env python3
"""Build the EEditor & EELisp catalog: one site with both projects' documentation and a searchable
index of everything you can call.

    python3 build.py --eeditor ../eeditor-next --eelisp ../eelisp-rs --out _site

Nothing here is written by hand except the landing page's frame (catalog/). Everything else comes
from the two repositories as they are at build time:

  eeditor/    eeditor-next/site — the manual, the tutorial, downloads, the example apps
  eelisp/     eelisp-rs/site — the EELisp book, the guide, embedding
  index.html  the catalog: a learning path, every document, and one search over
              · the EELisp builtins and prelude   eelisp-rs/docs/reference.md (generated from the engine)
              · the spreadsheet functions         eeditor-next/src/sheets/functions.eelisp
              · the snippets bundle               eeditor-next/src/snippets/*.eelisp
              · the editor commands and keys      eeditor-next/site/manual.html + keybindings/default.eelisp

Standard library only (Python 3.9+), so the GitHub Action needs nothing installed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GITHUB = "https://github.com/santacroce-tech"


# ── small helpers ────────────────────────────────────────────────────────────


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def inline_md(text: str) -> str:
    """Markdown's inline code, bold and italics → HTML, everything else escaped."""
    out = html.escape(text, quote=False)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    out = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"<i>\1</i>", out)
    return out


def strip_tags(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def git_info(repo: Path) -> dict:
    def run(*args: str) -> str:
        try:
            return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    return {"sha": run("rev-parse", "--short", "HEAD"), "date": run("log", "-1", "--format=%cs")}


# ── what can be called ───────────────────────────────────────────────────────


def docs_anchors(book_html: str) -> dict[str, str]:
    """name → its anchor in the EELisp book's function reference (the book's own table of contents)."""
    anchors = {}
    for href, name in re.findall(r'<li class="l2 fn"><a href="#(reference-[^"]*)">([^<]*)</a>', book_html):
        anchors.setdefault(html.unescape(name), href)
    return anchors


def eelisp_functions(reference_md: str, anchors: dict[str, str]) -> list[dict]:
    """Every builtin, special form and prelude function, from the generated reference."""
    entries: list[dict] = []
    group = ""
    cur: dict | None = None
    in_code = False
    code: list[str] = []
    for line in reference_md.splitlines():
        if line.startswith("```"):
            if in_code and cur is not None and not cur["example"]:
                cur["example"] = "\n".join(code).strip()
            in_code, code = not in_code, []
            continue
        if in_code:
            code.append(line)
            continue
        if line.startswith("## "):
            group = line[3:].strip()
            cur = None
            continue
        if line.startswith("### "):
            name = line[4:].strip()
            cur = {
                "name": name,
                "source": "EELisp",
                "group": group,
                "sig": "",
                "summary": "",
                "example": "",
                "href": f"eelisp/docs.html#{anchors[name]}" if name in anchors else "eelisp/docs.html#reference",
            }
            entries.append(cur)
            continue
        if cur is None or group == "Index":
            continue
        text = line.strip()
        if not text:
            continue
        if not cur["sig"] and text.startswith("`(") and text.endswith("`"):
            cur["sig"] = text.strip("`")
        elif not cur["summary"]:
            cur["summary"] = inline_md(text)
    return [e for e in entries if e["group"] != "Index"]


def sheet_functions(src: str) -> list[dict]:
    """The spreadsheet functions: each `defn` with the `;;` lines above it. A defn that is only a
    helper — its name appears in no example — is left out; one comment can serve two definitions
    (`var` and `varp`), so it is kept until the next comment starts."""
    entries: list[dict] = []
    group = ""
    block: list[str] = []
    fresh = False  # the last line was a comment, so a new block is being read
    for line in src.splitlines():
        m = re.match(r";;\s*─+\s*(.+?)\s*─+\s*$", line)
        if m:
            group = m.group(1).capitalize()
            block, fresh = [], False
            continue
        if line.startswith(";;"):
            if not fresh:
                block, fresh = [], True
            block.append(line[2:].strip())
            continue
        fresh = False
        m = re.match(r"\(defn\s+(\S+)\s+\(([^)]*)\)", line)
        if not m:
            continue
        name, params = m.group(1), m.group(2).strip()
        if not any(f"({name} " in b or f"({name})" in b for b in block):
            continue
        examples = [b for b in block if b.startswith("(")]
        prose = " ".join(b for b in block if b and not b.startswith("("))
        mine = [e for e in examples if f"({name} " in e or f"({name})" in e]
        summary = re.sub(r"\s+", " ", prose)
        if not summary and mine:
            summary = example_note(mine[0], name)
        entries.append({
            "name": name,
            "source": "Sheets",
            "group": group,
            "sig": f"({name}{' ' + params if params else ''})",
            "summary": inline_md(summary),
            "example": "\n".join(mine or examples),
            "href": "eeditor/manual.html#sheets",
        })
    return entries


def example_note(line: str, name: str) -> str:
    """What an example line says about `name`: in "(var B1:B9)  sample variance · (varp B1:B9)
    population", the words after varp's own call. "→ 3.15" is kept — a result says what it does."""
    for seg in line.split(" · "):
        start = seg.find(f"({name}")
        if start < 0:
            continue
        depth, i = 0, start
        for i in range(start, len(seg)):
            depth += {"(": 1, ")": -1}.get(seg[i], 0)
            if depth == 0:
                break
        rest = seg[i + 1:].strip()
        if rest.startswith("("):
            return ""  # another call follows, not a description
        return re.sub(r"\s+", " ", re.sub(r"^—\s*", "", rest))
    return ""


def snippet_functions(snippets: Path) -> list[dict]:
    """The standard snippets bundle: `;; ─── zzname — what it does ───` heads each function."""
    entries: list[dict] = []
    for f in sorted(snippets.glob("zz-*.eelisp")):
        module = f.stem
        lines = read(f).splitlines()
        for i, line in enumerate(lines):
            m = re.match(r";;\s*─+\s*(\S+)\s+—\s+(.+?)\s*─*\s*$", line)
            if not m:
                continue
            name, title = m.group(1), m.group(2)
            notes, examples = [], []
            for nxt in lines[i + 1:]:
                if not nxt.startswith(";;"):
                    break
                body = nxt[2:].strip()
                (examples if body.startswith("(") else notes).append(body)
            sig = ""
            for nxt in lines[i + 1:]:
                d = re.match(r"\(defn\s+(\S+)\s+\(([^)]*)\)", nxt)
                if d:
                    sig = f"({d.group(1)}{' ' + d.group(2).strip() if d.group(2).strip() else ''})"
                    break
            entries.append({
                "name": name,
                "source": "Snippets",
                "group": module,
                "sig": sig,
                "summary": inline_md(title + (". " + " ".join(notes) if notes else "")),
                "example": "\n".join(examples),
                "href": f"{GITHUB}/eeditor-next/blob/main/src/snippets/{f.name}",
            })
    return entries


def editor_commands(manual: str, default_keys: str) -> list[dict]:
    """The commands a keybinding can name with (ed-cmd "…"): the manual's table, then whatever the
    default keybindings file lists that the table doesn't."""
    described: dict[str, str] = {}
    section = re.search(r"<h3>Built-in commands</h3>(.*?)</table>", manual, re.S)
    if section:
        for row in re.findall(r"<tr><td>(.*?)</td><td>(.*?)</td></tr>", section.group(1), re.S):
            names = [strip_tags(n) for n in re.findall(r"<code>(.*?)</code>", row[0])]
            for n in names:
                described.setdefault(n, row[1].strip())
    listed: dict[str, str] = {}
    block = re.search(r";; ── built-in commands ─+\n(.*?)\n\n", default_keys + "\n\n", re.S)
    if block:
        for line in block.group(1).splitlines():
            # "open-file   pick a file …", "theme-dark · theme-light   pick a theme", "save · search"
            # — names joined by ·, and after the last one, maybe, what they do
            chunks = [c.strip() for c in line[2:].split("·")]
            last = chunks[-1].split(None, 1)
            note = html.escape(re.sub(r"\s+", " ", last[1])) if len(last) > 1 else ""
            for n in [c.split(None, 1)[0] for c in chunks if c]:
                if re.fullmatch(r"[a-z][\w-]*", n):
                    listed.setdefault(n, note)
    names = list(described) + [n for n in listed if n not in described]
    return [
        {
            "name": n,
            "source": "Commands",
            "group": "Editor command",
            "sig": f'(ed-cmd "{n}")',
            "summary": described.get(n) or listed.get(n) or "",
            "example": "",
            "href": "eeditor/manual.html#keybindings",
        }
        for n in names
    ]


def shortcuts(manual: str) -> list[dict]:
    section = re.search(r'<section id="shortcuts".*?</section>', manual, re.S)
    out = []
    for key, does in re.findall(r"<tr><td>(.*?)</td><td>(.*?)</td></tr>", section.group(0) if section else "", re.S):
        out.append({
            "name": strip_tags(key),
            "source": "Keys",
            "group": "Default shortcut",
            "sig": "",
            "summary": does.strip(),
            "example": "",
            "href": "eeditor/manual.html#shortcuts",
        })
    return out


# ── the documents ────────────────────────────────────────────────────────────


def chapters(page: str, limit: int = 16) -> list[str]:
    heads = [strip_tags(h) for h in re.findall(r"<h2[^>]*>(.*?)</h2>", page, re.S)]
    heads = [re.sub(r"#$", "", h).strip() for h in heads]
    return [h for h in heads if h and h.lower() not in {"contents"}][:limit]


# ── copying the two sites into one ───────────────────────────────────────────

BACK_LINK = (
    '<a href="../index.html" style="position:fixed;left:12px;bottom:12px;z-index:9999;'
    "font:600 12px/1 system-ui,sans-serif;padding:8px 12px;border-radius:999px;"
    "background:#1f2937;color:#fff;text-decoration:none;box-shadow:0 2px 8px rgba(0,0,0,.25);"
    'opacity:.92">← Catalog</a>'
)

# Links that leave one site for the other become links inside the catalog.
CROSS_LINKS = {
    "https://eelisp.app/reference.html": "../eelisp/docs.html#reference",
    "https://eelisp.app/docs.html": "../eelisp/docs.html",
    "https://eelisp.app/guide.html": "../eelisp/guide.html",
    "https://eelisp.app/embed.html": "../eelisp/embed.html",
    "https://eeditor.app/manual.html": "../eeditor/manual.html",
    "https://eeditor.app/tutorial.html": "../eeditor/tutorial.html",
    "https://eeditor.app/download.html": "../eeditor/download.html",
}


def copy_site(src: Path, dest: Path) -> None:
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("README.md", ".DS_Store"))
    for page in dest.glob("*.html"):  # the site's own pages; apps/ are exported forms, left alone
        text = read(page)
        text = text.replace('href="/"', 'href="index.html"')
        for old, new in CROSS_LINKS.items():
            text = text.replace(f'href="{old}"', f'href="{new}"')
        text = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + BACK_LINK, text, count=1)
        page.write_text(text, encoding="utf-8")


def redirect(to: str, title: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<meta http-equiv="refresh" content="0; url={to}"><link rel="canonical" href="{to}"></head>
<body><p>Moved to <a href="{to}">{to}</a>.</p></body></html>
"""


# ── the build ────────────────────────────────────────────────────────────────


def build(eeditor: Path, eelisp: Path, out: Path, regen: bool) -> dict:
    if regen:
        # The EELisp book and reference are generated from the engine's source; make sure they
        # match it, whatever was last committed.
        subprocess.run([sys.executable, "scripts/build-docs.py"], cwd=eelisp, check=True, stdout=subprocess.DEVNULL)

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    copy_site(eeditor / "site", out / "eeditor")
    copy_site(eelisp / "site", out / "eelisp")
    # Hand-written and behind the engine; the book's reference is generated from it.
    (out / "eelisp" / "reference.html").write_text(redirect("docs.html#reference", "EELisp function reference"), encoding="utf-8")

    manual = read(eeditor / "site" / "manual.html")
    book = read(eelisp / "site" / "docs.html")
    items = (
        eelisp_functions(read(eelisp / "docs" / "reference.md"), docs_anchors(book))
        + sheet_functions(read(eeditor / "src" / "sheets" / "functions.eelisp"))
        + snippet_functions(eeditor / "src" / "snippets")
        + editor_commands(manual, read(eeditor / "src" / "keybindings" / "default.eelisp"))
        + shortcuts(manual)
    )

    pkg = json.loads(read(eeditor / "package.json"))
    cargo = re.search(r'^version\s*=\s*"([^"]+)"', read(eelisp / "Cargo.toml"), re.M)
    meta = {
        "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "eeditor": {"version": pkg["version"], **git_info(eeditor)},
        "eelisp": {"version": cargo.group(1) if cargo else "", **git_info(eelisp)},
    }

    docs = {
        "eeditor": [
            ("Tutorial — your first hour", "eeditor/tutorial.html", "Seven steps from an empty folder to linked notes, an agenda that files things for you, a shortcut of your own and a form.", chapters(read(eeditor / "site" / "tutorial.html"))),
            ("Manual", "eeditor/manual.html", "Everything the app does, chapter by chapter, with a shortcut reference at the end.", chapters(manual)),
            ("Download and release notes", "eeditor/download.html", "Installers for macOS, Windows and Linux, and what changed in each version.", []),
            ("Example apps", "eeditor/apps/Office.html", "Forms exported as single HTML files that run in your browser — Office and Functions — and the example .eeform files.", []),
            ("eeditor.app home", "eeditor/index.html", "What EEditor is, in one page.", []),
        ],
        "eelisp": [
            ("The EELisp book", "eelisp/docs.html", "The whole language in ten chapters, from syntax to embedding, with the full function reference.", chapters(book)),
            ("Guide", "eelisp/guide.html", "A shorter tour of the language, one topic per section.", chapters(read(eelisp / "site" / "guide.html"))),
            ("Embedding", "eelisp/embed.html", "Using the engine from Rust, from any language over --serve, or in a browser.", chapters(read(eelisp / "site" / "embed.html"))),
            ("eelisp.app home", "eelisp/index.html", "What EELisp is, in one page.", []),
        ],
    }

    page = read(HERE / "catalog" / "index.html")
    counts = {}
    for it in items:
        counts[it["source"]] = counts.get(it["source"], 0) + 1
    replacements = {
        "{{DATA}}": json.dumps({"items": items, "meta": meta, "counts": counts}, ensure_ascii=False).replace("</", "<\\/"),
        "{{EEDITOR_DOCS}}": doc_cards(docs["eeditor"]),
        "{{EELISP_DOCS}}": doc_cards(docs["eelisp"]),
        "{{EEDITOR_VERSION}}": html.escape(meta["eeditor"]["version"]),
        "{{EELISP_VERSION}}": html.escape(meta["eelisp"]["version"]),
        "{{BUILT}}": html.escape(meta["built"]),
        "{{EEDITOR_SHA}}": html.escape(meta["eeditor"]["sha"]),
        "{{EELISP_SHA}}": html.escape(meta["eelisp"]["sha"]),
        "{{TOTAL}}": str(len(items)),
    }
    for k, v in replacements.items():
        page = page.replace(k, v)
    (out / "index.html").write_text(page, encoding="utf-8")
    for static in ("catalog.css", "catalog.js", "favicon.svg"):
        shutil.copy(HERE / "catalog" / static, out / static)
    (out / "catalog.json").write_text(json.dumps({"items": items, "meta": meta}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    return {"items": len(items), "counts": counts, "meta": meta}


def doc_cards(docs: list[tuple[str, str, str, list[str]]]) -> str:
    cards = []
    for title, href, about, heads in docs:
        toc = ""
        if heads:
            names = [html.escape(re.sub(r"^\d+\.\s*", "", h)) for h in heads]
            toc = f"<details><summary>{len(heads)} chapters</summary><ol>" + "".join(f"<li>{n}</li>" for n in names) + "</ol></details>"
        cards.append(
            f'<article class="doc"><h3><a href="{href}">{html.escape(title)}</a></h3>'
            f"<p>{html.escape(about)}</p>{toc}</article>"
        )
    return "\n".join(cards)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--eeditor", type=Path, default=HERE.parent / "eeditor-next")
    ap.add_argument("--eelisp", type=Path, default=HERE.parent / "eelisp-rs")
    ap.add_argument("--out", type=Path, default=HERE / "_site")
    ap.add_argument("--regen", action="store_true", help="rebuild the EELisp book from the engine's source first")
    args = ap.parse_args()
    summary = build(args.eeditor.resolve(), args.eelisp.resolve(), args.out.resolve(), args.regen)
    print(f"{summary['items']} entries — " + ", ".join(f"{k} {v}" for k, v in summary["counts"].items()))
    m = summary["meta"]
    print(f"EEditor {m['eeditor']['version']} ({m['eeditor']['sha']}) · EELisp {m['eelisp']['version']} ({m['eelisp']['sha']}) → {args.out}")


if __name__ == "__main__":
    main()
