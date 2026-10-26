# 10. Fetching prices

Part IV turns the workspace into a small markets desk. It starts here: prices fetched from the
internet into a table of your own, with a key to refresh them and a clock that does it for you.
Everything later — the portfolio sheet, the alerts, the desk form — reads this table.

You need the `(on-load …)` from [chapter 2](02-your-first-shortcut.md) and an internet connection.
Nothing here depends on Part III — you can read Part IV first.

## Where prices come from

Two free sources that need no account and no key:

| Source | What | The address |
|---|---|---|
| **CoinGecko** | crypto prices | `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd` |
| **Frankfurter** | exchange rates (the European Central Bank's, updated once a working day) | `https://api.frankfurter.app/latest?from=USD&to=EUR,BRL,GBP` |

Both answer in JSON. Free services have limits — CoinGecko allows a few calls a minute without a
key — so fetch every few minutes at most, never in a loop. Stock prices are harder to get for
free; see [Stocks](#stocks) at the end.

## One call, by hand

At the REPL (**⌘J**):

```eelisp
(def answer (http-get "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd"))
(dict-get answer :status)    ; → 200
```

`http-get` returns a dict: the HTTP `:status`, and the `:body` as text. The body is JSON, and
`json-parse` turns it into dicts and lists:

```eelisp
(def data (json-parse (dict-get answer :body)))
(dict-get (dict-get data "bitcoin") :usd)    ; → 80121
```

JSON's keys arrive as keywords — `:bitcoin`, `:usd` — and `dict-get` accepts the name as text
too, which is handy when the name is in a variable.

A request can fail in two ways, and EELisp sees them differently:

- **The service answers, but not with a price** — a typo in the address (404), *too many
  requests* (429), the service down (5xx). `http-get` still returns its dict, with that `:status`.
- **Nothing answers** — no connection, a name that doesn't resolve, a service that hangs.
  `http-get` stops with an error, *HTTP request failed: …*.

The one function every fetch goes through handles both, and gives back `nil` instead of a price:

```eelisp
(defn fetch-json (url)
  (try (let (r (http-get url :timeout 10))
         (if (= (dict-get r :status) 200)
             (json-parse (dict-get r :body))
             nil))
    (catch e nil)))

(nil? (fetch-json "https://api.frankfurter.app/latest?from=USD&to=EUR"))    ; → false
(fetch-json "https://prices.invalid/")                                        ; → nil
```

- `:timeout 10` gives up on a service after ten seconds instead of the default thirty — a key
  or the clock waits that long at most.
- `try` runs its body and, if it stops with an error, runs `catch` instead — here, simply `nil`.
  `prices.invalid` is an address that can never resolve, which is what being offline looks like
  to `http-get`; `fetch-json` turns it into `nil` like a refused request.

## A table for prices

Prices are data, so they go in a table — not in a note. One row per price, per moment:

```eelisp
(deftable prices (symbol:string kind:string price:number currency:string at:string source:string))
```

`deftable` is safe to run again: on an existing table it changes nothing and keeps the rows.
That is what lets it sit in `(on-load …)`, which runs on every save.

## Fetching into the table

```eelisp
(def crypto-ids (list "bitcoin" "ethereum"))

(defn fetch-crypto ()
  (let (data (fetch-json (str "https://api.coingecko.com/api/v3/simple/price?ids="
                              (str-join "," crypto-ids) "&vs_currencies=usd")))
    (if (nil? data)
        0
        (length (map (fn (id)
                       (insert prices {:symbol id :kind "crypto" :currency "USD" :source "coingecko"
                                       :price (dict-get (dict-get data id) :usd) :at *now*}))
                     crypto-ids)))))

(def fx-to (list "EUR" "BRL" "GBP"))

(defn fetch-fx ()
  (let (data (fetch-json (str "https://api.frankfurter.app/latest?from=USD&to=" (str-join "," fx-to))))
    (if (nil? data)
        0
        (length (map (fn (cur)
                       (insert prices {:symbol (str "USD/" cur) :kind "fx" :currency cur :source "frankfurter"
                                       :price (dict-get (dict-get data :rates) cur) :at *now*}))
                     fx-to)))))

(fetch-crypto)    ; → 2
(fetch-fx)        ; → 3
```

Each returns how many prices it saved — 0 when the fetch failed, offline or refused, so a bad
minute costs nothing.
`*now*` is the moment as `"2026-10-26 09:30:00"`, which sorts as text in time order.

Look at what you have: `(browse prices)` at the REPL shows the table as a grid.

## The latest price

Every fetch adds rows, so "the price of bitcoin" means the newest row for it:

```eelisp
(defn latest (symbol)
  (let (rows (records (query prices :where "symbol = ?" :params (list symbol)
                                    :order "at" :desc true :limit 1)))
    (if (empty? rows) nil (field-get (first rows) :price))))

(latest "bitcoin")     ; → 80121
(latest "USD/EUR")     ; → 0.89342
(latest "dogecoin")    ; → nil
```

And a conversion, because the rates are there now:

```eelisp
(defn usd-to (currency amount)
  (let (rate (latest (str "USD/" currency)))
    (if (nil? rate) nil (round (* amount rate) 2))))

(usd-to "EUR" (latest "bitcoin"))    ; → 71581.7
```

## On a key, and on the clock

Put it all in your keybindings file, so it's there every time EEditor starts:

```eelisp keys
(on-load
  (deftable prices (symbol:string kind:string price:number currency:string at:string source:string))
  (def crypto-ids (list "bitcoin" "ethereum"))
  (def fx-to (list "EUR" "BRL" "GBP"))

  (defn fetch-json (url)
    (try (let (r (http-get url :timeout 10))
           (if (= (dict-get r :status) 200) (json-parse (dict-get r :body)) nil))
      (catch e nil)))

  (defn fetch-crypto ()
    (let (data (fetch-json (str "https://api.coingecko.com/api/v3/simple/price?ids="
                                (str-join "," crypto-ids) "&vs_currencies=usd")))
      (if (nil? data) 0
          (length (map (fn (id)
                         (insert prices {:symbol id :kind "crypto" :currency "USD" :source "coingecko"
                                         :price (dict-get (dict-get data id) :usd) :at *now*}))
                       crypto-ids)))))

  (defn fetch-fx ()
    (let (data (fetch-json (str "https://api.frankfurter.app/latest?from=USD&to=" (str-join "," fx-to))))
      (if (nil? data) 0
          (length (map (fn (cur)
                         (insert prices {:symbol (str "USD/" cur) :kind "fx" :currency cur :source "frankfurter"
                                         :price (dict-get (dict-get data :rates) cur) :at *now*}))
                       fx-to)))))

  (defn latest (symbol)
    (let (rows (records (query prices :where "symbol = ?" :params (list symbol)
                                      :order "at" :desc true :limit 1)))
      (if (empty? rows) nil (field-get (first rows) :price))))

  ;; both sources; how many prices were saved
  (defn refresh-prices () (+ (fetch-crypto) (fetch-fx))))

;; ⌘⇧Q — fetch now, and say how it went
(bind "Mod-Shift-q"
  (let (n (refresh-prices))
    (ed-message (if (= n 0) "No prices — offline, or the services said no; try again in a minute" (str n " prices saved")))))
```

And the clock:

```eelisp keys superseded
;; every 15 minutes while EEditor is open, quietly
(on-tick
  (when (= (mod (->number (second (str-split *time* ":"))) 15) 0)
    (refresh-prices)
    (ed-nothing)))
```

`(on-tick …)` runs once a minute, on the minute; the `when` lets it through at :00, :15, :30 and
:45. It ends in `(ed-nothing)` because whatever an on-tick returns is carried out as commands, and
a fetch count isn't one.

Two things to know:

- **It only runs while EEditor is open.** Nothing fetches in the background with the app closed;
  the first tick after you open it catches up.
- **A fetch holds the engine while it waits.** `http-get` is synchronous, so for the second or two
  a request takes — ten at most, with `:timeout 10` — keys and the REPL wait too. Two small requests
  every 15 minutes won't be noticed; fifty would.

## A line in today's note

Prices in a table are for sheets and forms; a line in the daily log is for you. Add a key that
writes one under `## Markets` in today's note:

```eelisp keys
(bind "Mod-Shift-y"
  (ed-append (str *date* ".md")
             (str "- " *time* "  BTC " (latest "bitcoin") " USD · EUR " (latest "USD/EUR") "\n")
             "## Markets"))
```

## Stocks

There is no stock-price service that is free, keyless and reliable, so this book doesn't depend on
one. The pattern is the same as above with a key from a provider you sign up for — Alpha Vantage,
for instance, offers a free key with a small daily allowance. Its quote endpoint looks like this,
but check the provider's own documentation: this block is **not tested** by the book, because the
test can't use a real key.

Some services want the key in the address, like this one; most want it in a header, which is what
`:headers` is for — `(http-get url :headers {"x-api-key" key})`. CoinGecko's free key, for one,
goes in `x-cg-demo-api-key`. And a service that answers in CSV instead of JSON is read with
`csv-records`: `(csv-records (dict-get r :body))` gives one dict per row, keyed by the header line,
with numbers as numbers.

```eelisp norun
(def av-key "YOUR-KEY")

(defn fetch-stock (symbol)
  (let (data (fetch-json (str "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol="
                              symbol "&apikey=" av-key)))
    (if (nil? data) 0
        (do (insert prices {:symbol symbol :kind "stock" :currency "USD" :source "alphavantage"
                            :price (->number (dict-get (dict-get data "Global Quote") "05. price"))
                            :at *now*})
            1))))
```

Keep a key out of notes you share: put it in a note of its own that you don't sync, and read it
with `(read-note …)`.

## What you have now

- a `prices` table that grows by five rows every 15 minutes while EEditor is open
- `fetch-json`, `fetch-crypto`, `fetch-fx`, `latest` and `refresh-prices` in your keybindings
- **⌘⇧Q** to fetch now, **⌘⇧Y** to log the prices in today's note

Chapter 11 makes the fetch report what changed into the agenda; chapter 12 builds the portfolio
sheet on `latest`.
