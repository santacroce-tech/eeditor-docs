# 12. A portfolio sheet

You own some bitcoin and some ether — the two rows of the `holdings` table from chapter 7: how
much, and what it cost you. The `prices` table knows what each is worth now. A sheet puts them
together: value, gain, gain in percent, a total, and the total in euros — recalculated every time
prices arrive.

## The sheet

```eelisp
(sheet-new "Portfolio")
```

One row per holding, with formulas that do the work:

| | A | B | C | D | E | F | G |
|---|---|---|---|---|---|---|---|
| **1** | Symbol | Qty | Cost | Price | Value | Gain | Gain % |
| **2** | bitcoin | 0.05 | 3100 | `=(latest A2)` | `=(round (* B2 D2) 2)` | `=(round (- E2 C2) 2)` | `=(round (* 100 (/ F2 C2)) 1)` |

- **Price** calls `latest` — your own function from chapter 10, reading the `prices` table. A
  formula can call anything your keybindings define.
- **Value** is quantity times price; **Gain** is value minus what it cost; **Gain %** is the gain
  as a share of the cost. Each rounds, for the reason chapter 7 gives.

Rather than typing a row per holding, write them from the table — so a holding you add later is a
refresh away from the sheet:

```eelisp
(defn portfolio-row (n h)
  (list (field-get h :symbol) (field-get h :qty) (field-get h :cost)
        (str "=(latest A" n ")")
        (str "=(round (* B" n " D" n ") 2)")
        (str "=(round (- E" n " C" n ") 2)")
        (str "=(round (* 100 (/ F" n " C" n ")) 1)")))

(defn portfolio-write ()
  (let (hs   (records (query holdings :order "symbol"))
        last (+ 1 (length hs))
        tot  (+ 2 last))
    (do (sheet-clear "Portfolio" "A:G")
        (sheet-set "Portfolio" "A1"
          (append (list (list "Symbol" "Qty" "Cost" "Price" "Value" "Gain" "Gain %"))
                  (map (fn (i) (portfolio-row (+ i 2) (nth hs i))) (range (length hs)))
                  (list (list "" "" "" "" "" "" ""))))
        (sheet-set "Portfolio" (str "A" tot)
          (list (list "Total" "" (str "=(sum C2:C" last ")") ""
                      (str "=(round (sum E2:E" last ") 2)")
                      (str "=(round (sum F2:F" last ") 2)")
                      (str "=(round (* 100 (/ F" tot " C" tot ")) 1)"))
                (list "In EUR" "" "" "" (str "=(usd-to \"EUR\" E" tot ")"))))
        tot)))
```

It needs `usd-to` from chapter 10 in your keybindings (below). Then:

```eelisp
(defn usd-to (currency amount)
  (let (rate (latest (str "USD/" currency)))
    (if (nil? rate) nil (round (* amount rate) 2))))

(portfolio-write)                  ; → 5
(sheet-get "Portfolio" "E2")       ; → 4006.05
(sheet-get "Portfolio" "G2")       ; → 29.2
(sheet-get "Portfolio" "G3")       ; → -4
(sheet-get "Portfolio" "E5")       ; → 6789.93
(sheet-get "Portfolio" "G5")       ; → 13.2
(sheet-get "Portfolio" "E6")       ; → 6066.26
```

Bitcoin — 0.05 at 80,121 — is worth 4,006.05 against 3,100 paid: up 29.2%. Ether is down 4%. All
told, 6,789.93 dollars for 6,000 spent, up 13.2%; 6,066.26 in euros at today's rate. The rows go
header, one per holding, a blank line, the total, the euros — so with two holdings the total is
row 5, and `portfolio-write` returns where it put it.

## Recalculating when prices arrive

`latest` reads a *table*, and a formula that reads a table isn't recalculated when the table
changes (chapter 9). So the fetch should finish by recalculating the sheet. Redefine
`refresh-prices` — a definition later in the file replaces the earlier one:

```eelisp keys
(on-load
  (defn usd-to (currency amount)
    (let (rate (latest (str "USD/" currency)))
      (if (nil? rate) nil (round (* amount rate) 2))))

  (defn portfolio-row (n h)
    (list (field-get h :symbol) (field-get h :qty) (field-get h :cost)
          (str "=(latest A" n ")")
          (str "=(round (* B" n " D" n ") 2)")
          (str "=(round (- E" n " C" n ") 2)")
          (str "=(round (* 100 (/ F" n " C" n ")) 1)")))

  (defn portfolio-write ()
    (let (hs   (records (query holdings :order "symbol"))
          last (+ 1 (length hs))
          tot  (+ 2 last))
      (do (sheet-clear "Portfolio" "A:G")
        (sheet-set "Portfolio" "A1"
            (append (list (list "Symbol" "Qty" "Cost" "Price" "Value" "Gain" "Gain %"))
                    (map (fn (i) (portfolio-row (+ i 2) (nth hs i))) (range (length hs)))
                    (list (list "" "" "" "" "" "" ""))))
          (sheet-set "Portfolio" (str "A" tot)
            (list (list "Total" "" (str "=(sum C2:C" last ")") ""
                        (str "=(round (sum E2:E" last ") 2)")
                        (str "=(round (sum F2:F" last ") 2)")
                        (str "=(round (* 100 (/ F" tot " C" tot ")) 1)"))
                  (list "In EUR" "" "" "" (str "=(usd-to \"EUR\" E" tot ")"))))
          tot)))

  ;; a column of the Total row, wherever it is now
  (defn portfolio-total (column)
    (let (labels (map first (sheet-rows "Portfolio" "A:A"))
          at     (first (filter (fn (i) (= (nth labels i) "Total")) (range (length labels)))))
      (if (nil? at) nil (sheet-get "Portfolio" (str column (+ at 1))))))

  ;; replaces chapter 10's: fetch, then bring the portfolio up to date
  (defn refresh-prices ()
    (let (n (+ (fetch-crypto) (fetch-fx)))
      (do (sheet-recalc "Portfolio") n))))

;; ⌘⇧P — rewrite the portfolio from the holdings table (after you buy or sell)
(bind "Mod-Shift-p"
  (do (portfolio-write)
      (ed-message (str "Portfolio: " (count-records holdings) " holdings, worth " (portfolio-total "E") " USD"))))
```

Now **⌘⇧Q** and the 15-minute round both end with the portfolio recalculated. **⌘⇧P** is for
when the holdings change: it writes the rows again from the table. (`refresh-prices` assumes
`Portfolio.eesheet` exists — make it before you save this, or the fetch will stop with an error.)

A holding you buy:

```eelisp
(insert holdings {:symbol "bitcoin" :kind "crypto" :qty 0.01 :cost 790})
(portfolio-write)                 ; → 6
(sheet-get "Portfolio" "E6")      ; → 7591.14
```

Two bitcoin rows now — two purchases at two prices, each with its own gain — and the total moves
to row 6. `portfolio-write` empties the sheet first (`sheet-clear` on columns A to G), so selling a
holding leaves no stale row behind either.

## On the dashboard

The total row moves as holdings come and go, so a block shouldn't name a cell. Find the row that
says *Total* instead:

```eelisp
(defn portfolio-total (column)
  (let (labels (map first (sheet-rows "Portfolio" "A:A"))
        at     (first (filter (fn (i) (= (nth labels i) "Total")) (range (length labels)))))
    (if (nil? at) nil (sheet-get "Portfolio" (str column (+ at 1))))))

(portfolio-total "E")    ; → 7591.14
(portfolio-total "G")    ; → 11.8
```

and a block in `dashboard.md` puts the portfolio next to the agenda:

```markdown
## Portfolio

<!-- eel: (str "Worth " (portfolio-total "E") " USD · " (portfolio-total "G") "% on what it cost") -->
<!-- /eel -->
```

Add `portfolio-total` to your keybindings' `on-load` with the rest.

## What you have now

- `Portfolio.eesheet` — each holding's price, value, gain and gain %, a total, and the total in EUR
- formulas calling your own functions — `latest`, `usd-to`
- `refresh-prices` that recalculates the portfolio after every fetch
- **⌘⇧P** — the portfolio rewritten from the holdings table

→ [Chapter 13 — Alerts as agenda items](13-alerts-as-agenda-items.md)
