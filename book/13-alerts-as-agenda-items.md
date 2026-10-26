# 13. Alerts as agenda items

A price that crosses a line you care about — bitcoin under 50,000, ether over 3,000 — shouldn't be
a line in a log you might read tonight. It should be a task, today, at the top of the agenda, with
a notification: *bitcoin below 50000 — review*. Then it lives where everything else you have to do
lives, and ticking it off is part of your day like the rest.

## Alerts are rows

```eelisp
(deftable alerts (symbol:string direction:string level:number fired:string))

(insert alerts {:symbol "bitcoin"  :direction "below" :level 85000 :fired ""})
(insert alerts {:symbol "ethereum" :direction "above" :level 3000  :fired ""})
```

`direction` is `"below"` or `"above"`; `fired` is the day the alert last went off, so it goes off
once a day at most, not on every fetch while the price stays past the line.

(85,000 is far above today's 80,121 — so the example has something to show. Set your own.)

## Checking

```eelisp
(defn crossed? (a)
  (let (p (latest (field-get a :symbol)))
    (and (not (nil? p))
         (if (= (field-get a :direction) "below")
             (< p (field-get a :level))
             (> p (field-get a :level))))))

(defn alert-text (a)
  (str (field-get a :symbol) " " (field-get a :direction) " " (field-get a :level) " — review"))

(map crossed? (records (query alerts)))    ; → (list true false)
(alert-text (first (records (query alerts))))    ; → "bitcoin below 85000 — review"
```

## Firing: an agenda item and a notification

When an alert crosses and hasn't fired today, three things happen: an agenda item for today,
priority 1, filed under `money/markets`; the alert's `fired` becomes today; and a notification.

```eelisp
(defcategory money/markets)

(defn fire (a)
  (do (add-item (alert-text a) :when *date* :priority 1 :category "money/markets")
      (update alerts (record-id a) {:fired *date*})
      (ed-notify "Price alert" (str (alert-text a) " — now " (latest (field-get a :symbol))))))

(defn check-alerts ()
  (map fire (filter (fn (a) (and (crossed? a) (!= (field-get a :fired) *date*)))
                    (records (query alerts)))))

(length (check-alerts))    ; → 1
(length (check-alerts))    ; → 0
(length (records (items :search "bitcoin below 85000")))    ; → 1
```

The first check fires bitcoin's alert; the second finds it already fired today and does nothing —
one item, not one every 15 minutes. `check-alerts` returns the notifications, as editor commands:
from a key or a tick, EEditor shows them — a message in the window, and a system notification
when EEditor isn't in front.

The item is an ordinary agenda item: it's in the panel, on the dashboard's *money* view (chapter 4
files `money/markets` under `money`), and ticking it — in the panel, or **⌘⌥T** on its line —
closes it like any other.

## On every fetch

Chapter 11's `market-round` returns the editor commands for the moves; add the alerts' to them.
Redefine it — the later definition wins:

```eelisp keys
(on-load
  (deftable alerts (symbol:string direction:string level:number fired:string))
  (defcategory money/markets)

  (defn crossed? (a)
    (let (p (latest (field-get a :symbol)))
      (and (not (nil? p))
           (if (= (field-get a :direction) "below")
               (< p (field-get a :level))
               (> p (field-get a :level))))))

  (defn alert-text (a)
    (str (field-get a :symbol) " " (field-get a :direction) " " (field-get a :level) " — review"))

  (defn fire (a)
    (do (add-item (alert-text a) :when *date* :priority 1 :category "money/markets")
        (update alerts (record-id a) {:fired *date*})
        (ed-notify "Price alert" (str (alert-text a) " — now " (latest (field-get a :symbol))))))

  (defn check-alerts ()
    (map fire (filter (fn (a) (and (crossed? a) (!= (field-get a :fired) *date*)))
                      (records (query alerts)))))

  ;; replaces chapter 11's: the moves, and the alerts
  (defn market-round ()
    (do (refresh-prices)
        (if (= *time* "03:00") (prune-prices) nil)
        (append (map (fn (s) (ed-append (str *date* ".md") (str (move-line s) "\n") "## Markets"))
                     (moves))
                (check-alerts)))))

;; ⌘⇧J — fetch now, log the moves, check the alerts — and say so, even when nothing happened
(bind "Mod-Shift-j"
  (let (done (market-round))
    (append done (list (ed-message (if (empty? done)
                                       "Prices fetched — no moves, no alerts"
                                       (str "Prices fetched — " (length done) " moves or alerts")))))))
```

```eelisp
(def ether-alert (first (records (query alerts :where "symbol = ?" :params (list "ethereum")))))
(update alerts (record-id ether-alert) {:level 2000})
(length (market-round))    ; → 2
```

Ether's alert is now *above 2000*, which today's 2,319.90 is: the round returns two commands —
bitcoin's move line from chapter 11, and ether's notification. Bitcoin's alert stays quiet: it
fired already today.

## Managing alerts

At the REPL, an alert is a row: `insert` to add, `(update alerts id {:level …})` to move the line,
`(delete alerts id)` to drop it, `(browse alerts)` to see them all. Chapter 14 gives them a page of
the markets desk.

## What you have now

- an `alerts` table — a symbol, a direction, a level
- `check-alerts` — an agenda item for today, priority 1, under `money/markets`, and a notification;
  once a day per alert
- the 15-minute round now fetches, logs the moves and checks the alerts; **⌘⇧J** does it now

→ Part V: [Chapter 14 — The markets desk](14-the-markets-desk.md)
