# Demo

These outputs come from a real Gmail account. Sender addresses and subjects are
intentionally omitted; only counts, label names, and timings are shown.

## Validate the rules

```text
$ python -m gmail_organizer check-config
OK: config/rules.yaml
  prefix: Auto
  rules: 1 (recruiting)
  categories: Recruiting
  label unmatched: False
```

## Preview before writing

```text
$ python -m gmail_organizer run --limit 20
DRY RUN — no Gmail changes were made.
would apply: 10
mode: bootstrap
fetched: 20 | classified: 10 | unmatched: 10
categories: Recruiting=10
already labeled: 0 | eligible: 10
labels applied: 0 | labels created: 0
failed: 0
state: unchanged
duration: 9.94s
```

The dry run creates no labels and writes no state file.

## Apply a bounded run

```text
$ python -m gmail_organizer run --apply --limit 20
APPLY RUN
mode: bootstrap
fetched: 20 | classified: 10 | unmatched: 10
categories: Recruiting=10
already labeled: 0 | eligible: 10
labels applied: 10 | labels created: 1
failed: 0
state: updated
duration: 17.45s
```

Gmail now shows one `Auto/Recruiting` label on 10 messages.

## Verify idempotency

```text
$ python -m gmail_organizer run --apply --full --limit 20
APPLY RUN
mode: full
fetched: 20 | classified: 10 | unmatched: 10
categories: Recruiting=10
already labeled: 10 | eligible: 0
labels applied: 0 | labels created: 0
failed: 0
state: updated
duration: 15.29s
```

A second pass applies zero duplicates.

## Quality checks

```text
$ python -m pytest -q --cov=gmail_organizer --cov-report=term
149 passed in 1.96s
TOTAL 883 53 94%
```

The CI workflow runs the same suite on Ubuntu and Windows with an 85% coverage
gate.
