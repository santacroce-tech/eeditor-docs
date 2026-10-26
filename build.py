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
import importlib.util
import os
import posixpath
import urllib.parse
from pathlib import Path

import mdrender

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
                "href": site_path(f"eeditor/src/snippets/{f.name}") + f"#fn-{name}",
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


def copy_site(src: Path, dest: Path, linker: "Linker") -> None:
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("README.md", ".DS_Store"))
    for page in dest.glob("*.html"):  # the site's own pages; apps/ are exported forms, left alone
        text = read(page)
        text = text.replace('href="/"', 'href="index.html"')
        for old, new in CROSS_LINKS.items():
            text = text.replace(f'href="{old}"', f'href="{new}"')

        def local(m: re.Match) -> str:
            inside = linker.internal(html.unescape(m.group(1)))
            return f'href="../{inside}"' if inside else m.group(0)

        text = re.sub(r'href="(https?://[^"]+)"', local, text)
        text = re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + BACK_LINK, text, count=1)
        page.write_text(text, encoding="utf-8")


def redirect(to: str, title: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<meta http-equiv="refresh" content="0; url={to}"><link rel="canonical" href="{to}"></head>
<body><p>Moved to <a href="{to}">{to}</a>.</p></body></html>
"""


# ── the library: every Markdown file, and the EELisp the catalog points into ─

GROUPS = [
    ("eeditor", "EEditor", "eeditor-next"),
    ("eelisp", "EELisp", "eelisp-rs"),
    ("sample-workspace", "Sample workspace", None),
]
GROUP_LABEL = {g: label for g, label, _ in GROUPS}
REPO_OF = {g: repo for g, _, repo in GROUPS}
TEXT = (".md", ".eelisp", ".eeform", "LICENSE")
# Files the app writes for itself or that say nothing on their own
# workspace/ is what the sample workspace is made from; the library has the sample as the app writes it
SKIP = ("workspace/", "node_modules/")

# The library is read by topic, not by repository. Each file lands in the first topic with a
# pattern that matches its "group/path", in the order the patterns are listed — so a topic reads
# from its introduction to its details. "Other" catches anything new, so nothing goes missing.
TOPICS = [
    ("start", "Start here", "What EEditor and EELisp are, the welcome note a new folder gets, and the hands-on tutorial.",
     [("The tutorial — your first hour", "eeditor/tutorial.html"), ("The manual", "eeditor/manual.html")],
     [r"sample-workspace/welcome\.md", r"sample-workspace/TRY ME\.md", r"eeditor/README\.md", r"eelisp/README\.md",
      r"eelisp/docs/README\.md", r"eelisp/docs/01-", r"sample-workspace/examples/.*\.mindmap\.md",
      r"sample-workspace/todo\.md", r"sample-workspace/notes/"]),
    ("language", "The EELisp language", "Syntax, the language, data, how it documents itself, and every function.",
     [("The EELisp book", "eelisp/docs.html"), ("Search the catalog", "index.html#catalog")],
     [r"eelisp/docs/02-", r"eelisp/docs/03-", r"eelisp/docs/04-", r"eelisp/docs/08-", r"eelisp/docs/reference\.md"]),
    ("agenda", "Agenda and PIM", "Items, categories, rules and views; the PIM's notes kept in step with the agenda; and the sample's dashboard, inbox and daily note.",
     [("Manual — the agenda", "eeditor/manual.html#agenda")],
     [r"eeditor/docs/PIM\.md", r"eelisp/docs/06-", r"eeditor/docs/pim/", r"sample-workspace/dashboard\.md",
      r"sample-workspace/\d{4}-\d\d-\d\d\.md", r"sample-workspace/inbox\.md", r"sample-workspace/bills\.md",
      r"sample-workspace/projects/", r"sample-workspace/pim/"]),
    ("spreadsheets", "Spreadsheets", "Sheets whose formulas are EELisp: the design, sheets from code, the spreadsheet functions (countif, vlookup…), and what is still missing.",
     [("Manual — sheets", "eeditor/manual.html#sheets"), ("Spreadsheet functions in the catalog", "index.html#q=countif")],
     [r"eeditor/docs/SPREADSHEET\.md", r"eelisp/docs/07-", r"eeditor/src/sheets/", r"eeditor/docs/SHEETS-LATER\.md"]),
    ("forms", "Database and forms", "dBASE-style tables on SQLite, and forms you draw and run — with the example forms.",
     [("Manual — forms", "eeditor/manual.html#forms"), ("The Office app", "eeditor/apps/Office.html")],
     [r"eelisp/docs/05-", r"eeditor/docs/FORMS\.md", r"eeditor/docs/FORM-APPS\.md", r"sample-workspace/.*\.eeform"]),
    ("keys", "Keybindings and snippets", "The shortcut table is EELisp: the defaults, the editor commands it can call, and the snippets bundle.",
     [("Manual — keybindings", "eeditor/manual.html#keybindings")],
     [r"eeditor/src/keybindings/default", r"eeditor/src/keybindings/", r"sample-workspace/\.eeditor/",
      r"eeditor/src/snippets/README\.md", r"eeditor/src/snippets/"]),
    ("architecture", "Architecture and embedding", "How the engine is built, using it from Rust, JSON or a browser, and the plan behind the rebuild.",
     [("Embedding", "eelisp/embed.html")],
     [r"eelisp/docs/09-", r"eelisp/docs/10-", r"eelisp/web/", r"eeditor/docs/ANALYSIS\.md"]),
    ("project", "The project", "Releasing, the websites, themes, the ZX Spectrum, the app's native plugins, and the licences.",
     [("Download", "eeditor/download.html")],
     [r"eeditor/docs/RELEASING\.md", r".*/site/README\.md", r"eeditor/docs/themes/", r"eeditor/docs/spectrum/",
      r"eeditor/src-tauri/", r".*/LICENSE$"]),
    ("other", "Other", "Documents not filed under a topic yet.", [], [r".*"]),
]
TOPIC_LABEL = {t[0]: t[1] for t in TOPICS}


def topic_of(key: str) -> tuple[str, int]:
    """The topic a file belongs to, and where it comes within it."""
    for slug, _, _, _, patterns in TOPICS:
        for n, pat in enumerate(patterns):
            if re.match(pat, key):
                return slug, n
    return "other", 0


def by_topic(keys: list[str]) -> list[tuple[tuple, list[str]]]:
    """Topics in order, each with its files in reading order; empty topics left out."""
    out = []
    for t in TOPICS:
        mine = [k for k in keys if topic_of(k)[0] == t[0]]
        mine.sort(key=lambda k: (topic_of(k)[1], k.lower()))
        if mine:
            out.append((t, mine))
    return out


ORIGIN = {"eeditor": "EEditor", "eelisp": "EELisp", "sample-workspace": "Sample"}
EEDITOR_CODE = ["src/sheets/functions.eelisp", "src/keybindings/default.eelisp", "src/keybindings/prelude.eelisp", "docs/pim/pim.eelisp"]


def tracked(repo: Path, *patterns: str) -> list[str]:
    try:
        out = subprocess.run(["git", "-C", str(repo), "ls-files", *patterns], capture_output=True, text=True, check=True).stdout
        return [f for f in out.splitlines() if f]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return [str(p.relative_to(repo)) for pat in patterns for p in repo.glob("**/" + pat)]


def gather(eeditor: Path, eelisp: Path, sample: Path | None) -> dict[str, Path]:
    """"group/path" → the file it comes from."""
    files: dict[str, Path] = {}
    for rel in tracked(eeditor, "*.md"):
        if not rel.startswith(SKIP):
            files[f"eeditor/{rel}"] = eeditor / rel
    for rel in ["LICENSE"] + EEDITOR_CODE + sorted(str(p.relative_to(eeditor)) for p in (eeditor / "src" / "snippets").glob("zz-*.eelisp")):
        if (eeditor / rel).exists():
            files[f"eeditor/{rel}"] = eeditor / rel
    for rel in tracked(eelisp, "*.md", "docs/assets/*", "LICENSE"):
        if not rel.startswith(SKIP):
            files[f"eelisp/{rel}"] = eelisp / rel
    # The sample workspace: freshly made (--sample), or the copy already kept in content/
    root = sample if sample else HERE / "content" / "sample-workspace"
    if root.exists():
        for f in sorted(root.rglob("*")):
            if f.is_file() and f.suffix in TEXT and f.name != "README.md":
                files[f"sample-workspace/{f.relative_to(root).as_posix()}"] = f
    return files


def sync_content(files: dict[str, Path], made: str) -> list[str]:
    """Keep content/ in this repository the same as the sources: written, updated, or removed."""
    content = HERE / "content"
    wanted = {content / key: src for key, src in files.items()}
    changed = []
    for dest, src in wanted.items():
        data = src.read_bytes()
        if not dest.exists() or dest.read_bytes() != data:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            changed.append(str(dest.relative_to(HERE)))
    if content.exists():
        for f in sorted(content.rglob("*")):
            if f.is_file() and f not in wanted and f.name != "README.md":
                f.unlink()
                changed.append(f"- {f.relative_to(HERE)}")
    readme = content_readme(files, made)
    target = content / "README.md"
    if not target.exists() or read(target) != readme:
        target.write_text(readme, encoding="utf-8")
        changed.append("content/README.md")
    sample_readme = content / "sample-workspace" / "README.md"
    if sample_readme.parent.exists():
        text = SAMPLE_README.format(made=made)
        if not sample_readme.exists():
            sample_readme.write_text(text, encoding="utf-8")
            changed.append(str(sample_readme.relative_to(HERE)))
    return changed


SAMPLE_README = """# The sample workspace

What EEditor puts in an empty folder when you accept its samples: the welcome note, the PIM
tutorial (**TRY ME.md**) with an agenda and notes linked to it, the example forms, a mind map of
every shortcut, and the keybindings the PIM uses (`.eeditor/keybindings.eelisp`).

This copy was made on {made} with `npm run pim:sample` in eeditor-next. In the app the dates are
relative to the day you add the samples, so they will differ from the ones here.
"""


def content_readme(files: dict[str, Path], made: str) -> str:
    lines = [
        "# The library",
        "",
        "Every Markdown document of EEditor and EELisp, the sample workspace the app offers a new",
        "folder, and the EELisp sources the catalog points into — copied here by `build.py`, kept in",
        "step with the two repositories. They read as they are on GitHub; the catalog site shows them",
        "formatted, linked to each other: https://santacroce-tech.github.io/eeditor-docs/library/",
        "",
        "Don't edit them here: change them where they come from, and the next build brings the change.",
        "",
    ]
    lines += [
        "The folders mirror where each file lives — `eeditor/` is eeditor-next, `eelisp/` is eelisp-rs,",
        "`sample-workspace/` is what EEditor writes into a new folder — so the links between them work.",
        "Below, the same files by topic.",
        "",
    ]
    for (slug, label, blurb, _, _), keys in by_topic([k for k in files if k.endswith(TEXT)]):
        lines += [f"## {label}", "", blurb, ""]
        for k in keys:
            group, rel = k.split("/", 1)
            title = doc_title(files[k], rel, k)
            lines.append(f"- [{title}]({urllib.parse.quote(k)}) — {ORIGIN[group]} · `{rel}`")
        lines.append("")
    return "\n".join(lines)


def order_keys(keys: list[str]) -> list[str]:
    """READMEs, the welcome note and the tutorial first, then by path."""
    first = ("README.md", "welcome.md", "TRY ME.md")

    def rank(k: str) -> tuple:
        name = k.rsplit("/", 1)[-1]
        depth = k.count("/")
        return (0 if name in first and depth <= 1 else 1, first.index(name) if name in first else 9, k.endswith(".md") is False, k.lower())

    return sorted(keys, key=rank)


# Where a file's own title says too little once it sits among sixty others
TITLES = {
    "eeditor/README.md": "EEditor — README",
    "eelisp/README.md": "EELisp — README",
    "eelisp/docs/README.md": "The EELisp book — contents",
    "sample-workspace/TRY ME.md": "TRY ME — the PIM tutorial",
    "sample-workspace/examples/EEditor.mindmap.md": "Every shortcut — a mind map",
    "sample-workspace/.eeditor/keybindings.eelisp": "The sample's keybindings, with the PIM",
    "eeditor/src/keybindings/default.eelisp": "The default keybindings",
    "eeditor/src/keybindings/prelude.eelisp": "The editor prelude — ed-* commands",
    "eeditor/src-tauri/plugins/README.md": "The app's native plugins",
    "eeditor/src-tauri/plugins/ios/README.md": "The iOS files plugin",
    "eeditor/src-tauri/plugins/permissions/autogenerated/reference.md": "iOS files plugin — permissions (generated)",
    "eeditor/site/README.md": "The eeditor.app website",
    "eelisp/site/README.md": "The eelisp.app website",
    "eeditor/docs/pim/pim.eelisp": "The PIM library — pim.eelisp",
    "eeditor/src/snippets/README.md": "The snippets bundle (zzeelisp)",
}


def code_title(text: str, name: str) -> str:
    """What an EELisp file's opening comment says it is: ";; zz-math.eelisp / ;; Math and number
    utilities — ported from …" → "Math and number utilities"."""
    lines = [re.sub(r"^;+\s*|[═─]+", "", l).strip() for l in text.splitlines()[:4] if l.startswith(";;")]
    lines = [l for l in lines if l]
    for l in lines:
        l = re.sub(r"^" + re.escape(name) + r"\s*(—\s*)?", "", l).strip()
        if l:
            l = re.split(r" — |\. ", l)[0].strip().rstrip(".")
            return l[:1].upper() + l[1:]
    return name


def doc_title(src: Path, rel: str, key: str = "") -> str:
    if key in TITLES:
        return TITLES[key]
    name = rel.rsplit("/", 1)[-1]
    if rel.endswith(".md"):
        title, _ = mdrender.title_and_summary(read(src), rel)
        title = re.sub(r"\s+#[A-Za-z][\w/-]*", "", title).strip()  # a note's tags aren't its name
        if re.fullmatch(r"\d{4}-\d\d-\d\d\.md", name):
            return f"Daily note — {title}"
        if key.startswith("sample-workspace/projects/"):
            return f"Project note — {title}"
        return title
    if name == "LICENSE":
        return f"Licence — {REPO_OF[key.split('/', 1)[0]] or 'sample'}"
    stem = name.rsplit(".", 1)[0]
    what = code_title(read(src), name)
    if name.endswith(".eeform"):
        return f"{stem} form" + (f" — {what}" if what != name and len(what) < 70 else "")
    return what if what != name else name


def site_path(key: str) -> str:
    """Where a library file is published: no dotted folders (GitHub Pages hides them), no spaces."""
    parts = [re.sub(r"^\.", "_", p).replace(" ", "-") for p in key.split("/")]
    path = "library/" + "/".join(parts)
    if path.endswith(".md"):
        return path[:-3] + ".html"
    if path.endswith((".eelisp", ".eeform", "/LICENSE")):
        return path + ".html"
    return path  # an image or other asset, as it is


def raw_path(key: str) -> str:
    """The file itself, published next to its page so "view the source" stays on this site."""
    parts = [re.sub(r"^\.", "_", p).replace(" ", "-") for p in key.split("/")]
    return "library/" + "/".join(parts)


def rel_href(from_page: str, to: str) -> str:
    return posixpath.relpath(to, posixpath.dirname(from_page) or ".")


class Linker:
    """Where a link in a library page should point: another page of this site whenever the target
    is one — a document, an image, one of the two project sites — and outside only when it has to."""

    def __init__(self, files: dict[str, Path]) -> None:
        self.files = files
        self.by_name: dict[tuple[str, str], str] = {}
        for k in files:
            g = k.split("/", 1)[0]
            name = k.rsplit("/", 1)[-1]
            if name.endswith(".md"):
                self.by_name.setdefault((g, name[:-3].lower()), k)

    def internal(self, url: str) -> str | None:
        """A site-root path for an absolute URL that this site has a copy of."""
        u = urllib.parse.urlsplit(url)
        host, path, frag = u.netloc.lower(), u.path, ("#" + u.fragment if u.fragment else "")
        for domain, folder in (("eeditor.app", "eeditor"), ("eelisp.app", "eelisp")):
            if host in (domain, "www." + domain):
                page = path.strip("/") or "index.html"
                if folder == "eelisp" and page == "reference.html":
                    return "eelisp/docs.html#reference"
                return f"{folder}/{page}{frag}"
        m = re.match(r"^/santacroce-tech/(eeditor-next|eelisp-rs)/(?:blob|tree)/[^/]+/(.+)$", path) if host == "github.com" else None
        if m:
            group = "eeditor" if m.group(1) == "eeditor-next" else "eelisp"
            key = f"{group}/{m.group(2)}"
            if key in self.files:
                return site_path(key) + frag
        return None

    def for_page(self, key: str):
        page = site_path(key)
        group = key.split("/", 1)[0]
        repo = REPO_OF[group]

        def link(target: str) -> str:
            if target.startswith("[["):
                name = target[2:-2].strip().lower().removesuffix(".md")
                hit = self.by_name.get((group, name)) or self.by_name.get((group, name.rsplit("/", 1)[-1]))
                return rel_href(page, site_path(hit)) if hit else "#"
            if re.match(r"^[a-z]+:", target):
                inside = self.internal(target) if target.startswith("http") else None
                return rel_href(page, inside) if inside else target
            if target.startswith("#"):
                return target
            path, _, frag = target.partition("#")
            here = posixpath.dirname(key)
            resolved = posixpath.normpath(posixpath.join(here, urllib.parse.unquote(path)))
            frag = "#" + frag if frag else ""
            if resolved in self.files:
                return rel_href(page, site_path(resolved)) + frag
            if repo and resolved.startswith(group + "/"):
                # source code and other files the library doesn't hold: the repository has them
                return f"{GITHUB}/{repo}/blob/main/{resolved[len(group) + 1:]}{frag}"
            return target

        return link


def load_diagram(eelisp: Path):
    """The EELisp book's Mermaid sequence-diagram → SVG drawer, so diagrams need no script."""
    script = eelisp / "scripts" / "build-docs.py"
    if not script.exists():
        return None
    spec = importlib.util.spec_from_file_location("eelisp_build_docs", script)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
        return getattr(mod, "sequence_svg", None)
    except Exception:
        return None


def nav_html(files: dict[str, Path], current: str, page: str) -> str:
    out = []
    here = topic_of(current)[0] if current else ""
    for (slug, label, _, _, _), keys in by_topic([k for k in files if k.endswith(TEXT)]):
        open_attr = " open" if slug == here else ""
        items = []
        for k in keys:
            group, rel = k.split("/", 1)
            name = doc_title(files[k], rel, k)
            cls = ' class="here" aria-current="page"' if k == current else ""
            items.append(
                f'<li><a{cls} href="{html.escape(rel_href(page, site_path(k)))}" title="{html.escape(ORIGIN[group] + " · " + rel)}">'
                f'{html.escape(name)}<span class="origin {group}">{ORIGIN[group]}</span></a></li>'
            )
        out.append(f'<details{open_attr}><summary>{label} <span>{len(keys)}</span></summary><ul>{"".join(items)}</ul></details>')
    return "".join(out)


def page_html(title: str, page: str, body: str, nav: str, toc: list, source: str, source_label: str) -> str:
    root = "../" * page.count("/")
    toc_html = ""
    if len(toc) > 1:
        toc_html = '<aside class="toc"><b>On this page</b><ul>' + "".join(
            f'<li class="l{lvl}"><a href="#{hid}">{text}</a></li>' for lvl, hid, text in toc
        ) + "</ul></aside>"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — EEditor &amp; EELisp library</title>
<link rel="icon" href="{root}favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{root}catalog.css">
</head>
<body class="lib">
<header class="top">
  <div class="wrap wide top-row">
    <a class="brand" href="{root}index.html"><span class="logo" aria-hidden="true">λ</span><span class="brand-text">EEditor &amp; EELisp</span></a>
    <nav>
      <a href="{root}index.html#start">Start</a>
      <a href="{root}library/index.html">Library</a>
      <a href="{root}index.html#catalog">Catalog</a>
    </nav>
  </div>
</header>
<div class="wrap wide lib-grid">
  <nav class="lib-nav" aria-label="Library"><a class="lib-home" href="{root}library/index.html">All documents</a>{nav}</nav>
  <main class="lib-main">
    <article class="doc-body">
{body}
    </article>
    <p class="source">Source: <a href="{html.escape(source)}">{html.escape(source_label)}</a></p>
  </main>
  {toc_html}
</div>
<footer><div class="wrap wide">EEditor and EELisp are free software under the MIT licence, developed by Roberto Santacroce Martins. © 2026</div></footer>
</body>
</html>
"""


def build_library(files: dict[str, Path], out: Path, eelisp: Path) -> list[dict]:
    linker = Linker(files)
    diagram = load_diagram(eelisp)
    index: list[dict] = []
    for key, src in files.items():
        page = site_path(key)
        raw = raw_path(key)
        (out / raw).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, out / raw)  # the file itself, for "source"
        if not key.endswith(TEXT):
            continue
        group, rel = key.split("/", 1)
        text = read(src)
        if key.endswith(".md"):
            body, toc = mdrender.render(text, linker.for_page(key), diagram)
            _, summary = mdrender.title_and_summary(text, rel)
            title = doc_title(src, rel, key)
        elif key.endswith("LICENSE"):
            body = f'<h1 id="top">Licence — {html.escape(REPO_OF[group] or group)}</h1><pre class="text">{html.escape(text)}</pre>'
            toc, title = [], doc_title(src, rel, key)
            summary = text.strip().splitlines()[0]
        else:
            body = f'<h1 id="top">{html.escape(rel.rsplit("/", 1)[-1])}</h1><pre class="lisp source-file"><code>{mdrender.highlight_lisp(text, anchors=True)}</code></pre>'
            toc = []
            title = doc_title(src, rel, key)
            first = [l[2:].strip() for l in text.splitlines()[:6] if l.startswith(";;") and l[2:].strip()]
            summary = " ".join(first[1:3] if len(first) > 1 else first)[:200]
        label = f"content/{key}" + (f" · from {REPO_OF[group]}/{rel}" if REPO_OF[group] else "")
        nav = nav_html(files, key, page)
        (out / page).write_text(page_html(title, page, body, nav, toc, rel_href(page, raw), label), encoding="utf-8")
        index.append({"key": key, "group": group, "title": title, "summary": summary, "href": page, "path": rel})
    write_library_index(index, files, out)
    for d in index:
        d["topic"] = topic_of(d["key"])[0]
    return index


def write_library_index(index: list[dict], files: dict[str, Path], out: Path) -> None:
    page = "library/index.html"
    sections = []
    jump = []
    by_key = {d["key"]: d for d in index}
    for (slug, label, blurb, related, _), keys in by_topic(list(by_key)):
        cards = "".join(
            f'<article class="doc"><h3><a href="{html.escape(rel_href(page, by_key[k]["href"]))}">{html.escape(by_key[k]["title"])}</a></h3>'
            f'<p class="doc-path"><span class="origin {by_key[k]["group"]}">{ORIGIN[by_key[k]["group"]]}</span> <code>{html.escape(by_key[k]["path"])}</code></p>'
            + (f"<p>{html.escape(by_key[k]['summary'])}</p>" if by_key[k]["summary"] else "")
            + "</article>"
            for k in keys
        )
        also = ""
        if related:
            also = '<p class="related">Also: ' + " · ".join(
                f'<a href="{html.escape(rel_href(page, href))}">{html.escape(text)}</a>' for text, href in related
            ) + "</p>"
        sections.append(
            f'<section class="lib-group" id="{slug}"><h2>{html.escape(label)} <span class="where">{len(keys)}</span></h2>'
            f'<p class="blurb">{html.escape(blurb)}</p>{also}<div class="doc-grid">{cards}</div></section>'
        )
        jump.append(f'<a href="#{slug}">{html.escape(label)}</a>')
    body = (
        '<h1 id="top">The library</h1>'
        "<p class=\"lede\">Every Markdown document of both projects, the sample workspace EEditor offers a new folder — "
        "the welcome note and the <b>TRY ME</b> tutorial among them — and the EELisp sources the catalog points into. "
        "Each page links to the others, and to the file it was made from.</p>"
        + '<nav class="topic-jump" aria-label="Topics">' + "".join(jump) + "</nav>"
        + "".join(sections)
    )
    nav = nav_html(files, "", page)
    (out / page).write_text(page_html("The library", page, body, nav, [], rel_href(page, "library/"), "content/ in this repository"), encoding="utf-8")


# ── the build ────────────────────────────────────────────────────────────────


def build(eeditor: Path, eelisp: Path, out: Path, regen: bool, sample: Path | None = None, sync: bool = False) -> dict:
    if regen:
        # The EELisp book and reference are generated from the engine's source; make sure they
        # match it, whatever was last committed.
        subprocess.run([sys.executable, "scripts/build-docs.py"], cwd=eelisp, check=True, stdout=subprocess.DEVNULL)

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    files = gather(eeditor, eelisp, sample)
    linker = Linker(files)
    copy_site(eeditor / "site", out / "eeditor", linker)
    copy_site(eelisp / "site", out / "eelisp", linker)
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

    library = build_library(files, out, eelisp)
    synced = sync_content(files, sample_made(files)) if sync else []

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
        "{{LIBRARY_COUNT}}": str(len(library)),
        "{{TOPICS}}": "".join(
            f'<a href="library/index.html#{t[0]}">{html.escape(t[1])} <b>{sum(1 for d in library if d["topic"] == t[0])}</b></a>'
            for t in TOPICS if any(d["topic"] == t[0] for d in library)
        ),
        "{{PIM_TUTORIAL}}": site_path("sample-workspace/TRY ME.md") if "sample-workspace/TRY ME.md" in files else site_path("eeditor/docs/PIM.md"),
        "{{PIM_GUIDE}}": site_path("eeditor/docs/PIM.md"),
        "{{WELCOME}}": site_path("sample-workspace/welcome.md"),
    }
    for k, v in replacements.items():
        page = page.replace(k, v)
    (out / "index.html").write_text(page, encoding="utf-8")
    for static in ("catalog.css", "catalog.js", "favicon.svg"):
        shutil.copy(HERE / "catalog" / static, out / static)
    (out / "catalog.json").write_text(json.dumps({"items": items, "meta": meta}, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    return {"items": len(items), "counts": counts, "meta": meta, "library": len(library), "synced": synced}


def sample_made(files: dict[str, Path]) -> str:
    """The day the sample workspace was made: its daily note is named after it."""
    days = [re.match(r"sample-workspace/(\d{4}-\d{2}-\d{2})\.md$", k) for k in files]
    days = [d.group(1) for d in days if d]
    return max(days) if days else "an unknown date"


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
    ap.add_argument("--sample", type=Path, help="a freshly made sample workspace (npm run pim:sample) to use instead of content/sample-workspace")
    ap.add_argument("--sync", action="store_true", help="bring content/ in this repository in step with the sources")
    args = ap.parse_args()
    summary = build(args.eeditor.resolve(), args.eelisp.resolve(), args.out.resolve(), args.regen,
                    args.sample.resolve() if args.sample else None, args.sync)
    print(f"{summary['items']} entries — " + ", ".join(f"{k} {v}" for k, v in summary["counts"].items()))
    print(f"library: {summary['library']} pages" + (f"; content/ changed: {len(summary['synced'])} files" if summary["synced"] else ""))
    m = summary["meta"]
    print(f"EEditor {m['eeditor']['version']} ({m['eeditor']['sha']}) · EELisp {m['eelisp']['version']} ({m['eelisp']['sha']}) → {args.out}")


if __name__ == "__main__":
    main()
