// The catalog's search: one list of everything callable, filtered as you type. The data is in the
// page (#data), put there by build.py, so this works from a file as well as from the site.
(function () {
  const data = JSON.parse(document.getElementById("data").textContent);
  const items = data.items;
  const SOURCES = [
    ["EELisp", "EELisp builtins"],
    ["Sheets", "Spreadsheet functions"],
    ["Snippets", "Snippets"],
    ["Commands", "Editor commands"],
    ["Keys", "Shortcuts"],
  ];
  const PAGE = 60; // drawn at a time; "show more" adds another page

  const q = document.getElementById("q");
  const chips = document.getElementById("chips");
  const results = document.getElementById("results");
  const count = document.getElementById("count");
  const empty = document.getElementById("empty");
  const on = new Set(SOURCES.map(([k]) => k));
  let shown = PAGE;

  const text = (html) => {
    const d = document.createElement("div");
    d.innerHTML = html;
    return d.textContent || "";
  };
  for (const it of items) it._hay = [it.name, it.sig, text(it.summary), it.group, it.source, it.example].join(" ").toLowerCase();

  for (const [key, label] of SOURCES) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "chip";
    b.setAttribute("aria-pressed", "true");
    b.dataset.key = key;
    b.textContent = label;
    const n = document.createElement("b");
    n.textContent = data.counts[key] || 0;
    b.appendChild(n);
    b.addEventListener("click", () => {
      on.has(key) ? on.delete(key) : on.add(key);
      b.setAttribute("aria-pressed", String(on.has(key)));
      shown = PAGE;
      render();
    });
    chips.appendChild(b);
  }

  const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  function highlight(el, words) {
    if (!words.length) return;
    const re = new RegExp("(" + words.map(escapeRe).join("|") + ")", "gi");
    const walk = (node) => {
      for (const child of [...node.childNodes]) {
        if (child.nodeType === 3) {
          const parts = child.textContent.split(re);
          if (parts.length < 2) continue;
          const frag = document.createDocumentFragment();
          parts.forEach((p, i) => {
            if (i % 2) {
              const m = document.createElement("mark");
              m.textContent = p;
              frag.appendChild(m);
            } else if (p) frag.appendChild(document.createTextNode(p));
          });
          child.replaceWith(frag);
        } else if (child.nodeType === 1 && child.tagName !== "MARK") walk(child);
      }
    };
    walk(el);
  }

  // Name matches first: an exact name, then a name that starts with the query, then the rest.
  function score(it, words, raw) {
    const name = it.name.toLowerCase();
    if (name === raw) return 0;
    if (name.startsWith(raw)) return 1;
    if (words.every((w) => name.includes(w))) return 2;
    return 3;
  }

  function card(it, words) {
    const li = document.createElement("li");
    li.className = "item";
    const head = document.createElement("div");
    head.className = "item-head";
    const a = document.createElement("a");
    a.className = "item-name";
    a.href = it.href;
    a.textContent = it.name;
    head.appendChild(a);
    const src = document.createElement("span");
    src.className = "tag src";
    src.textContent = it.source;
    head.appendChild(src);
    if (it.group) {
      const g = document.createElement("span");
      g.className = "tag";
      g.textContent = it.group;
      head.appendChild(g);
    }
    if (it.sig && it.sig !== "(" + it.name + ")") {
      const s = document.createElement("code");
      s.className = "sig";
      s.textContent = it.sig;
      head.appendChild(s);
    }
    li.appendChild(head);
    if (it.summary) {
      const p = document.createElement("p");
      p.innerHTML = it.summary; // built from escaped text by build.py
      li.appendChild(p);
    }
    if (it.example) {
      const pre = document.createElement("pre");
      pre.textContent = it.example;
      li.appendChild(pre);
    }
    highlight(li, words);
    return li;
  }

  function render() {
    const raw = q.value.trim().toLowerCase();
    const words = raw.split(/\s+/).filter(Boolean);
    let list = items.filter((it) => on.has(it.source) && words.every((w) => it._hay.includes(w)));
    if (words.length) {
      list = list
        .map((it, i) => [score(it, words, raw), i, it])
        .sort((a, b) => a[0] - b[0] || a[1] - b[1])
        .map((x) => x[2]);
    }
    results.replaceChildren(...list.slice(0, shown).map((it) => card(it, words)));
    if (list.length > shown) {
      const li = document.createElement("li");
      li.className = "more";
      const b = document.createElement("button");
      b.type = "button";
      b.className = "btn";
      b.textContent = `Show ${Math.min(PAGE, list.length - shown)} more of ${list.length - shown}`;
      b.addEventListener("click", () => {
        shown += PAGE;
        render();
      });
      li.appendChild(b);
      results.appendChild(li);
    }
    count.textContent = `${list.length} of ${items.length}`;
    empty.hidden = list.length > 0;
  }

  let timer;
  q.addEventListener("input", () => {
    clearTimeout(timer);
    timer = setTimeout(() => {
      shown = PAGE;
      const v = q.value.trim();
      history.replaceState(null, "", v ? "#q=" + encodeURIComponent(v) : location.pathname);
      render();
    }, 80);
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "/" && document.activeElement !== q && !e.metaKey && !e.ctrlKey) {
      e.preventDefault();
      document.getElementById("catalog").scrollIntoView();
      q.focus();
    }
  });

  // #q=countif opens the catalog searching for it — a link you can share
  const m = location.hash.match(/^#q=(.*)$/);
  if (m) {
    q.value = decodeURIComponent(m[1]);
    requestAnimationFrame(() => document.getElementById("catalog").scrollIntoView());
  }
  render();
})();
