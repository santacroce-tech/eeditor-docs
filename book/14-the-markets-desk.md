# 14. The markets desk

Part IV built the parts: prices in a table, what changed, a portfolio sheet, alerts in the agenda.
They live in four places. This chapter puts them on one screen — a form with three pages:

- **Watchlist** — every symbol, its latest price, its change since the fetch before
- **Portfolio** — the portfolio sheet itself, live, inside the form
- **Alerts** — the alerts table, with a way to add and remove them

and a **Fetch now** button, with the view refreshing itself every minute.

## The form

Make `MarketsDesk.eeform` (right-click → **New form…**) and paste this into *Code*:

```eelisp form MarketsDesk.eeform
;; MarketsDesk.eeform — prices, the portfolio and the alerts on one screen.
;; Zero to Hero, chapter 14. Needs chapters 10–13 in your keybindings.

(form "Markets desk" :size (720 580) :on-load desk-load
  (tabs     tabMain      :pages ("Watchlist" "Portfolio" "Alerts") :at (16 16) :size (688 492))
  (grid     grdWatch     :columns ("symbol" "price" "change %" "at") :sortable true :page "Watchlist"
                         :at (32 56) :size (656 392))
  (label    lblWatch     :page "Watchlist" :at (32 456) :size (656 24))
  (sheet    shtPortfolio :file "Portfolio" :toolbar false :page "Portfolio" :at (32 56) :size (656 424))
  (grid     grdAlerts    :columns ("symbol" "direction" "level" "fired") :page "Alerts"
                         :at (32 56) :size (656 316))
  (dropdown ddSymbol     :items ("bitcoin") :required true :page "Alerts" :at (32 384) :size (160 28))
  (dropdown ddDirection  :items ("below" "above") :value "below" :page "Alerts" :at (200 384) :size (100 28))
  (textbox  txtLevel     :number true :min 0 :required true :placeholder "level" :page "Alerts"
                         :at (308 384) :size (120 28))
  (button   btnAddAlert  :text "Add alert" :submit true :page "Alerts" :at (436 382) :size (110 30)
                         :on-click desk-add-alert)
  (button   btnDelAlert  :text "Delete selected" :page "Alerts" :at (554 382) :size (134 30)
                         :on-click desk-delete-alert)
  (button   btnFetch     :text "Fetch now" :at (16 524) :size (110 32) :on-click desk-fetch)
  (label    lblStatus    :at (140 530) :size (564 24))
  (timer    tmrShow      :interval 60000 :at (680 530) :on-tick desk-tick))

(defn desk-watch-rows ()
  (map (fn (s) (let (r (latest-row s))
                 {:symbol s :price (latest s) :change (or (change-pct s) "") :at (if (nil? r) "" (field-get r :at))}))
       (append crypto-ids (map (fn (c) (str "USD/" c)) fx-to))))

(defn desk-show ()
  (ui-set "grdWatch" :rows (map (fn (d) {"symbol" (dict-get d :symbol) "price" (dict-get d :price)
                                         "change %" (dict-get d :change) "at" (dict-get d :at)})
                                (desk-watch-rows)))
  (ui-set "lblWatch" :text (str "Portfolio " (portfolio-total "E") " USD · " (portfolio-total "G")
                                "% · " (count-records prices) " prices kept"))
  (ui-set "grdAlerts" :rows (query alerts :order "symbol")))

(defn desk-tick (f) (desk-show))

(defn desk-load (f)
  (ui-set "ddSymbol" :items crypto-ids)
  (desk-show))

(defn desk-fetch (f)
  (let (n (refresh-prices))
    (desk-show)
    (ui-set "lblStatus" :text (if (= n 0) "No prices — the services said no; try again in a minute"
                                  (str n " prices at " *time*)))))

(defn desk-add-alert (f)
  (insert alerts {:symbol (ui-get f "ddSymbol") :direction (ui-get f "ddDirection")
                  :level (ui-get f "txtLevel") :fired ""})
  (ui-set "txtLevel" :value "")
  (ui-set "lblStatus" :text (str "Alert: " (ui-get f "ddSymbol") " " (ui-get f "ddDirection") " " (ui-get f "txtLevel")))
  (desk-show))

(defn desk-delete-alert (f)
  (let (row (ui-get f "grdAlerts"))
    (if (nil? row)
        (ui-message "Pick an alert first")
        (do (delete alerts (dict-get row "id"))
            (ui-set "lblStatus" :text "Alert deleted")
            (desk-show)))))
```

What's new since chapter 8:

- **`tabs`** with `:pages` makes the three pages; a control with `:page "Alerts"` shows only on
  that page. Controls stay listed flat in the file, each with its own position — draw them inside
  the tabs' box.
- **`sheet`** shows `Portfolio.eesheet`, beside the form, as the real grid — scrollable, formulas
  and formats and all; `:toolbar false` hides its toolbar. It's the same sheet as in its own tab:
  change a cell here and it's changed there.
- **`timer`** is invisible; every `:interval` milliseconds it calls `:on-tick` — `desk-tick`, which
  re-reads the tables. The fetching itself stays in your keybindings' 15-minute round (chapter 11);
  the timer only redraws what's there, so the desk is never more than a minute behind.
- **A grid can show any rows**, not only a query: `desk-show` builds the watchlist as a list of
  dicts — one per symbol, from `latest`, `change-pct` and `latest-row` — keyed by the column names.

Every handler uses functions from your keybindings: `latest`, `change-pct`, `refresh-prices`,
`portfolio-total`, and the `alerts` table. The form is the screen; the logic stays in one place.

## Try it

Run it (▶ run, or the key below). The watchlist shows bitcoin and ether, and the three exchange
rates, with bitcoin's change since yesterday's price from chapter 11. The *Portfolio* page is the
sheet. On *Alerts*, pick *ethereum*, *above*, type `2500`, **Add alert**: the row appears, and the
next round will test it.

At the REPL, through `ui-run`:

```eelisp
(length (desk-watch-rows))                                ; → 5
(dict-get (first (desk-watch-rows)) :price)               ; → 80121
(dict-get (first (desk-watch-rows)) :change)              ; → 5.15

(ui-run desk-add-alert {"ddSymbol" "ethereum" "ddDirection" "above" "txtLevel" 2500})
(count-records alerts)                                    ; → 3
```

## Open it from a key

```eelisp keys
;; ⌘⇧M is meetings (chapter 2); the desk is ⌘⇧9 — nine to five, markets hours
(bind "Mod-Shift-9" (ed-form "MarketsDesk"))
```

`ed-form` opens it in a window of its own, beside whatever you're writing. Asking again brings the
window forward rather than opening a second one.

## What you have now

- `MarketsDesk.eeform` — watchlist, portfolio and alerts on three pages, refreshing every minute
- a `sheet` control showing a live `.eesheet` inside a form, and a `timer`
- **⌘⇧9** — the desk, in its own window

→ [Chapter 15 — The weekly review](15-the-weekly-review.md)
