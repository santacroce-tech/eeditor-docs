# 11. Keeping them fresh

Chapter 10 fills the `prices` table every 15 minutes. A table that only grows is a log, not
information: this chapter turns it into *what changed*. How much has bitcoin moved since the last
fetch? Is anything moving enough to tell you? And how do you keep a year of fetches from turning
the table into a haystack?

You need chapter 10's functions in your keybindings: `fetch-json`, `fetch-crypto`, `fetch-fx`,
`latest` and `refresh-prices`.

## The price before

`latest` gives the newest price. For a change you need the one before it — but not simply the row
before: one fetch writes every symbol with the same `at`, and two fetches in a row may write the
same price. *Before* means the newest price from an earlier moment than the latest one:

```eelisp
(defn latest-row (symbol)
  (first (records (query prices :where "symbol = ?" :params (list symbol)
                                :order "at" :desc true :limit 1))))

(defn previous (symbol)
  (let (last (latest-row symbol))
    (if (nil? last)
        nil
        (let (rows (records (query prices :where "symbol = ? AND at < ?"
                                          :params (list symbol (field-get last :at))
                                          :order "at" :desc true :limit 1)))
          (if (empty? rows) nil (field-get (first rows) :price))))))
```

Every fetch so far happened at the same moment, so there is nothing before yet:

```eelisp
(previous "bitcoin")    ; → nil
```

Pretend yesterday morning's fetch happened — one row, by hand — and there is:

```eelisp
(insert prices {:symbol "bitcoin" :kind "crypto" :price 76200 :currency "USD"
                :at "2026-10-25 09:30:00" :source "by hand"})
(previous "bitcoin")    ; → 76200
```

## The change, in percent

```eelisp
(defn change-pct (symbol)
  (let (now (latest symbol) before (previous symbol))
    (if (or (nil? now) (nil? before))
        nil
        (round (* 100 (/ (- now before) before)) 2))))

(change-pct "bitcoin")     ; → 5.15
(change-pct "ethereum")    ; → nil
```

Bitcoin went from 76,200 to 80,121: up 5.15%. Ethereum has only one moment so far, so there is no
change to tell — `nil`, not 0, because "no change" and "don't know" aren't the same thing.

## Telling you when it matters

Fetching every 15 minutes, most changes are noise. Write a line in today's note only when a symbol
moves more than a threshold since the moment before:

```eelisp
(def move-threshold 3)    ; percent

(defn moves ()
  (filter (fn (s) (let (c (change-pct s)) (and (not (nil? c)) (>= (abs c) move-threshold))))
          crypto-ids))

(defn move-line (symbol)
  (let (c (change-pct symbol))
    (str "- " *time* "  " symbol " " (if (> c 0) "▲" "▼") " " (abs c) "% → " (latest symbol))))

(moves)                    ; → (list "bitcoin")
(move-line "bitcoin")      ; → "- 09:30  bitcoin ▲ 5.15% → 80121"
```

`*time*` is the moment the key or tick ran — 09:30 in this book's examples.

## Keeping the table small

Four fetches an hour is 35,000 rows a year per symbol. For a personal desk, the last few days in
full and one price a day before that is plenty. `prune-prices` keeps the newest row of each day
for anything older than a week, and deletes the rest:

```eelisp
(defn day-of (at) (substr at 0 10))

(defn prune-prices ()
  (let (cutoff (date-add *date* -7 :days)
        old    (records (query prices :where "at < ?" :params (list cutoff) :order "at" :desc true))
        kept   (list)
        gone   0)
    (do (for-each r old
          (let (key (str (field-get r :symbol) " " (day-of (field-get r :at))))
            (if (some? (fn (k) (= k key)) kept)
                (do (delete prices (record-id r)) (set! gone (+ gone 1)))
                (set! kept (cons key kept)))))
        gone)))

(prune-prices)    ; → 0
```

Nothing is older than a week yet, so nothing goes. Rows are read newest first, so the one kept for
each symbol and day is the last fetch of that day.

## Every fetch, the whole round

Put it together in your keybindings — the fetch, the moves into today's note, a prune once a day:

```eelisp keys
(on-load
  (def move-threshold 3)

  (defn latest-row (symbol)
    (first (records (query prices :where "symbol = ?" :params (list symbol)
                                  :order "at" :desc true :limit 1))))

  (defn previous (symbol)
    (let (last (latest-row symbol))
      (if (nil? last)
          nil
          (let (rows (records (query prices :where "symbol = ? AND at < ?"
                                            :params (list symbol (field-get last :at))
                                            :order "at" :desc true :limit 1)))
            (if (empty? rows) nil (field-get (first rows) :price))))))

  (defn change-pct (symbol)
    (let (now (latest symbol) before (previous symbol))
      (if (or (nil? now) (nil? before)) nil (round (* 100 (/ (- now before) before)) 2))))

  (defn moves ()
    (filter (fn (s) (let (c (change-pct s)) (and (not (nil? c)) (>= (abs c) move-threshold))))
            crypto-ids))

  (defn move-line (symbol)
    (let (c (change-pct symbol))
      (str "- " *time* "  " symbol " " (if (> c 0) "▲" "▼") " " (abs c) "% → " (latest symbol))))

  (defn day-of (at) (substr at 0 10))

  (defn prune-prices ()
    (let (cutoff (date-add *date* -7 :days)
          old    (records (query prices :where "at < ?" :params (list cutoff) :order "at" :desc true))
          kept   (list)
          gone   0)
      (do (for-each r old
            (let (key (str (field-get r :symbol) " " (day-of (field-get r :at))))
              (if (some? (fn (k) (= k key)) kept)
                  (do (delete prices (record-id r)) (set! gone (+ gone 1)))
                  (set! kept (cons key kept)))))
          gone)))

  ;; fetch, then one ed-append per symbol that moved — editor commands, for a key or a tick to carry out
  (defn market-round ()
    (do (refresh-prices)
        (if (= *time* "03:00") (prune-prices) nil)
        (map (fn (s) (ed-append (str *date* ".md") (str (move-line s) "\n") "## Markets"))
             (moves)))))

;; every 15 minutes: the whole round, quietly unless something moved
(on-tick
  (when (= (mod (->number (second (str-split *time* ":"))) 15) 0)
    (market-round)))
```

This `on-tick` replaces chapter 10's — keep one or the other, not both, or every fetch happens
twice. The round returns the `ed-append`s for the symbols that moved, and a tick carries out what
it returns: the line lands under `## Markets` in today's note, open or not. When nothing moved it
returns an empty list — nothing to do, nothing written. The prune runs on the 03:00 tick, while
EEditor is open then; skip a night and the next one catches up, because it prunes by date, not
by count.

```eelisp
(length (market-round))    ; → 1
```

One line: bitcoin, still 5.15% above yesterday's hand-made price.

## What you have now

- `previous`, `change-pct`, `moves` — what changed since the fetch before
- a line in today's `## Markets` when something moves 3% or more
- `prune-prices` — the table keeps a week in full and a price a day before that
- `market-round` on the clock instead of a bare fetch

Next, the reason prices are worth having: what your holdings are worth.

→ [Chapter 12 — A portfolio sheet](12-a-portfolio-sheet.md)
