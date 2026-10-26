"""Markdown → HTML for the library pages, standard library only.

It reads the Markdown the two projects actually write: headings with GitHub's anchors, nested and
task lists, tables, fenced code (EELisp highlighted, Mermaid sequence diagrams drawn as inline SVG),
block quotes, rules, images, wiki links `[[note]]`, `#tags`, and the `<!-- eel: … -->` markers
around a note's live blocks. Links are handed to a callback, so the caller decides where each one
points.
"""

from __future__ import annotations

import html
import re
from typing import Callable, Optional

Link = Callable[[str], str]  # a link's target as written → the href to use


class Slugger:
    """Heading anchors as GitHub makes them: lower-case, punctuation dropped, spaces to hyphens,
    -1, -2 … on repeats — so a link written for GitHub works here too."""

    def __init__(self) -> None:
        self.seen: dict[str, int] = {}

    def slug(self, text: str) -> str:
        s = re.sub(r"<[^>]+>", "", text)
        s = re.sub(r"[`*_]", "", s.strip().lower())
        s = re.sub(r"[^\w\- ]", "", s).replace(" ", "-")
        if s in self.seen:
            self.seen[s] += 1
            return f"{s}-{self.seen[s]}"
        self.seen[s] = 0
        return s


# ── EELisp highlighting ──────────────────────────────────────────────────────

SPECIAL = {"def", "defn", "defun", "fn", "lambda", "let", "set!", "if", "cond", "and", "or", "do",
           "begin", "for-each", "loop", "recur", "quote", "quasiquote", "defmacro", "when", "unless",
           "deftable", "defform", "defrule", "defview", "defcategory", "deftemplate", "bind", "on-start",
           "on-load", "on-tick"}


def highlight_lisp(code: str, anchors: bool = False) -> str:
    """Comments, strings, keywords, numbers and special forms get a class each. With `anchors`, a
    top-level `(defn name` gets id="fn-name", so a page of source can be linked into."""
    out: list[str] = []
    i, n, prev = 0, len(code), ""
    line_start = True
    while i < n:
        c = code[i]
        if c == ";":
            j = code.find("\n", i)
            j = n if j < 0 else j
            out.append('<span class="c">' + html.escape(code[i:j]) + "</span>")
            i = j
        elif c == '"':
            j = i + 1
            while j < n and code[j] != '"':
                j += 2 if code[j] == "\\" else 1
            j = min(j + 1, n)
            out.append('<span class="s">' + html.escape(code[i:j]) + "</span>")
            i = j
        elif c == "→":
            j = code.find("\n", i)
            j = n if j < 0 else j
            out.append('<span class="r">' + html.escape(code[i:j]) + "</span>")
            i = j
        elif c in "()[]{}'`,@":
            if anchors and c == "(" and line_start:
                m = re.match(r"\((?:defn|defun|defmacro|def)\s+([^\s()]+)", code[i:])
                if m:
                    out.append(f'<span id="fn-{html.escape(m.group(1))}"></span>')
            out.append('<span class="p">' + html.escape(c) + "</span>")
            prev, line_start = c, False
            i += 1
            continue
        elif c.isspace():
            out.append(c)
            line_start = c == "\n"
            i += 1
            continue
        else:
            j = i
            while j < n and not code[j].isspace() and code[j] not in '()[]{}";':
                j += 1
            tok = code[i:j]
            esc = html.escape(tok)
            if tok.startswith(":"):
                out.append('<span class="k">' + esc + "</span>")
            elif re.fullmatch(r"-?(0x[0-9a-fA-F]+|\d+(\.\d+)?(e\d+)?%?)", tok) or tok in ("true", "false", "nil"):
                out.append('<span class="n">' + esc + "</span>")
            elif prev == "(" and tok in SPECIAL:
                out.append('<span class="f">' + esc + "</span>")
            else:
                out.append(esc)
            i = j
        prev, line_start = "", False
    return "".join(out)


# ── inline ───────────────────────────────────────────────────────────────────


LINK = re.compile(r"(!?)\[((?:[^\]`]|`[^`]*`)+)\]\(([^)\s]+)\)")


def inline(text: str, link: Link) -> str:
    # Links and images first, as whole units, so a label may hold code: [`workspace/`](workspace/)
    held: list[str] = []

    def hold(m: re.Match) -> str:
        bang, label, target = m.group(1), m.group(2), m.group(3)
        href = html.escape(link(target))
        if bang:
            held.append(f'<img alt="{html.escape(label)}" src="{href}" loading="lazy">')
        else:
            held.append(f'<a href="{href}">{inline(label, link)}</a>')
        return f"\x00{len(held) - 1}\x00"

    text = LINK.sub(hold, text)
    out_html = _inline(text, link)
    return re.sub(r"\x00(\d+)\x00", lambda m: held[int(m.group(1))], out_html)


def _inline(text: str, link: Link) -> str:
    parts = re.split(r"(`+[^`]+?`+)", text)
    out = []
    for p in parts:
        if p.startswith("`") and p.endswith("`") and len(p) > 1:
            out.append("<code>" + html.escape(p.strip("`").strip(" ") if p.startswith("``") else p[1:-1]) + "</code>")
            continue
        p = html.escape(p, quote=False)
        p = re.sub(r"&lt;(https?://[^\s&]+)&gt;", lambda m: f'<a href="{m.group(1)}">{m.group(1)}</a>', p)
        p = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]",
                   lambda m: f'<a class="wiki" href="{html.escape(link("[[" + m.group(1).strip() + "]]"))}">{m.group(2) or m.group(1)}</a>', p)
        p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
        p = re.sub(r"(?<![\w*])\*(?![\s*])(.+?)(?<![\s*])\*(?![\w*])", r"<em>\1</em>", p)
        p = re.sub(r"(?<![\w])_(?![\s_])(.+?)(?<![\s_])_(?![\w])", r"<em>\1</em>", p)
        p = re.sub(r"~~(.+?)~~", r"<del>\1</del>", p)
        # tags and item ids, in the text only — never inside a tag's attributes (href="#section")
        p = "".join(
            seg if seg.startswith("<") else
            re.sub(r"\{#(\d+)\}", r'<span class="item-id">{#\1}</span>',
                   re.sub(r"(?<![\w&{/#])#([A-Za-z][\w/-]*)", r'<span class="tag">#\1</span>', seg))
            for seg in re.split(r"(<[^>]+>)", p)
        )
        out.append(p)
    return "".join(out)


# ── blocks ───────────────────────────────────────────────────────────────────

LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")


def render_list(lines: list[str], link: Link) -> str:
    """A list and its nesting, by indentation. Lines are the list's own, blank lines removed."""

    def build(start: int, indent: int) -> tuple[str, int]:
        first = LIST_ITEM.match(lines[start])
        ordered = bool(first and first.group(2)[0].isdigit())
        tag = "ol" if ordered else "ul"
        begin = int(re.match(r"\d+", first.group(2)).group(0)) if ordered else 1
        open_tag = f'<ol start="{begin}">' if ordered and begin != 1 else f"<{tag}>"
        items: list[str] = []
        i = start
        while i < len(lines):
            m = LIST_ITEM.match(lines[i])
            ind = len(lines[i]) - len(lines[i].lstrip())
            if m and ind == indent:
                body = m.group(3)
                i += 1
                # continuation lines: indented further and not a new item
                while i < len(lines) and not LIST_ITEM.match(lines[i]) and (len(lines[i]) - len(lines[i].lstrip())) > indent:
                    body += " " + lines[i].strip()
                    i += 1
                check = re.match(r"^\[([ xX])\]\s+(.*)$", body)
                cls = ""
                if check:
                    done = check.group(1) != " "
                    body = ('<input type="checkbox" disabled' + (" checked" if done else "") + "> " + inline(check.group(2), link))
                    cls = ' class="task' + (" done" if done else "") + '"'
                else:
                    body = inline(body, link)
                sub = ""
                if i < len(lines):
                    nm = LIST_ITEM.match(lines[i])
                    nind = len(lines[i]) - len(lines[i].lstrip())
                    if nm and nind > indent:
                        sub, i = build(i, nind)
                items.append(f"<li{cls}>{body}{sub}</li>")
            elif m and ind > indent:
                sub, i = build(i, ind)  # a deeper item with no parent at this level
                items.append(f"<li>{sub}</li>")
            else:
                break
        return open_tag + "".join(items) + f"</{tag}>", i

    out, i = [], 0
    while i < len(lines):
        ind = len(lines[i]) - len(lines[i].lstrip())
        part, i = build(i, ind)
        out.append(part)
    return "".join(out)


def split_row(line: str) -> list[str]:
    cells, buf, in_code = [], [], False
    for c in line.strip().strip("|"):
        if c == "`":
            in_code = not in_code
        if c == "|" and not in_code:
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
    cells.append("".join(buf).strip())
    return cells


def render(md: str, link: Link, diagram: Optional[Callable[[str], str]] = None) -> tuple[str, list[tuple[int, str, str]]]:
    """The page body, and its headings (level, id, text) for a table of contents."""
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    toc: list[tuple[int, str, str]] = []
    para: list[str] = []
    slugger = Slugger()
    i = 0

    def flush() -> None:
        if para:
            out.append("<p>" + inline(" ".join(para), link) + "</p>")
            para.clear()

    while i < len(lines):
        line = lines[i]
        fence = re.match(r"^(\s*)(```+|~~~+)\s*([\w-]*)", line)
        if fence:
            flush()
            mark, lang = fence.group(2), fence.group(3).lower()
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith(mark):
                j += 1
            code = "\n".join(lines[i + 1:j])
            if lang == "mermaid" and diagram:
                try:
                    out.append('<figure class="diagram">' + diagram(code) + "</figure>")
                except Exception:
                    out.append(f'<pre class="mermaid"><code>{html.escape(code)}</code></pre>')
            elif lang in ("lisp", "eelisp", "clojure", "scheme"):
                out.append(f'<pre class="lisp"><code>{highlight_lisp(code)}</code></pre>')
            else:
                out.append(f'<pre class="{lang or "text"}"><code>{html.escape(code)}</code></pre>')
            i = j + 1
            continue
        h = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if h:
            flush()
            level, text = len(h.group(1)), h.group(2)
            body = inline(text, link)
            hid = slugger.slug(text)
            out.append(f'<h{level} id="{hid}">{body}<a class="anchor" href="#{hid}" aria-label="Link to this section">#</a></h{level}>')
            if 2 <= level <= 3:
                toc.append((level, hid, re.sub(r"<[^>]+>", "", body)))
            i += 1
            continue
        if re.match(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", line):
            flush()
            out.append("<hr>")
            i += 1
            continue
        c = re.match(r"^\s*<!--\s*(.*?)\s*-->\s*$", line)
        if c:
            flush()
            note = c.group(1)
            if note.startswith("eel:"):
                out.append(f'<div class="live-block">live block — <code>{html.escape(note[4:].strip())}</code> — EEditor refreshes what follows</div>')
            elif note == "/eel":
                out.append('<div class="live-block end">end of live block</div>')
            i += 1
            continue
        if line.lstrip().startswith("<!--"):  # a comment over several lines: dropped, as GitHub does
            flush()
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1]):
            flush()
            head = split_row(line)
            j = i + 2
            rows = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                rows.append(split_row(lines[j]))
                j += 1
            t = ['<div class="table-wrap"><table><thead><tr>']
            t += ["<th>" + inline(c, link) + "</th>" for c in head]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join("<td>" + inline(c, link) + "</td>" for c in r) + "</tr>")
            t.append("</tbody></table></div>")
            out.append("".join(t))
            i = j
            continue
        if LIST_ITEM.match(line):
            flush()
            block = []
            while i < len(lines):
                if LIST_ITEM.match(lines[i]) or (lines[i].startswith((" ", "\t")) and lines[i].strip() and block):
                    block.append(lines[i].replace("\t", "    "))
                    i += 1
                elif not lines[i].strip() and i + 1 < len(lines) and (LIST_ITEM.match(lines[i + 1]) or lines[i + 1].startswith("  ")) and block:
                    i += 1  # a blank line inside a loose list
                else:
                    break
            out.append(render_list(block, link))
            continue
        if line.startswith(">"):
            flush()
            quote = []
            while i < len(lines) and lines[i].startswith(">"):
                quote.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            body, _ = render("\n".join(quote), link, diagram)
            out.append("<blockquote>" + body + "</blockquote>")
            continue
        if not line.strip():
            flush()
        else:
            para.append(line.strip())
        i += 1
    flush()
    return "\n".join(out), toc


def title_and_summary(md: str, fallback: str) -> tuple[str, str]:
    """A document's first heading, and its first paragraph as plain text."""
    title = fallback
    m = re.search(r"^#\s+(.+)$", md, re.M)
    if m:
        title = re.sub(r"[`*]", "", m.group(1)).strip()
    summary = ""
    in_code = False
    para: list[str] = []
    for line in md.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or line.startswith(("#", "|", "<!--", ">", "-", "*", "!", "[")) and not para:
            continue
        if not line.strip():
            if para:
                break
            continue
        para.append(line.strip())
    summary = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", " ".join(para))
    summary = re.sub(r"[`*]|\[\[|\]\]", "", summary)
    if len(summary) > 200:
        summary = summary[:197].rsplit(" ", 1)[0] + "…"
    return title, summary
