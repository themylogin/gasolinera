# Design

## Context

`update` in `gasolinera/gas_stations.py` reads the feed, and `_parse_feed` turns it into a list of valid stations. `_parse_feed` already raises `ParseError` when the list is empty or no entry is valid. Then one transaction deletes every row of `gas_station` and inserts the new rows. Nothing compares the new list with the store.

The MITECO feed lists about 12,000 stations. Between two runs, a few stations open or close.

## Goals / Non-Goals

**Goals:**

- Stop a run that would delete a large part of the store, whatever the cause: a truncated answer, or a format change that makes many entries fail to parse.
- Keep the old store, so the bot keeps working with older prices.

**Non-Goals:**

- Detect a stale feed, for example a `Fecha` older than the last stored one.
- Show the age of the data in the bot.
- Retry within a run, or alert the operator by any channel other than the log and the exit status.
- Add an override flag or a configuration variable for the limit.

## Decisions

### Compare with the stored count, not with a fixed minimum

The limit is relative to the store. A fixed floor such as 10,000 stations pins today's data and needs a change when the network grows or shrinks. A relative limit follows the real size.

### Count the valid stations, not the entries

The check uses the number of stations after the skips. A truncated list and a list where most entries fail to parse then give the same result. A separate limit on the skip ratio is not necessary.

### The limit is 90 %

Normal churn is far below 1 %. A 10 % drop is about 1,200 stations, so a real drop of that size in one run does not occur. A limit of 50 % lets a half list through. A limit of 99 % gives no extra protection. The value is an inline literal in the comparison, because only one place uses it.

The comparison uses integers: `len(stations) * 10 < stored * 9`. So 90 of 100 passes and 89 of 100 fails, with no float rounding.

### Check inside the replacement transaction

`update` counts `gas_station` in the same transaction as the delete and the insert. When the check fails, `update` logs an error with both counts and returns 1 before the delete. The transaction then holds no change. `main` already exits with the status that `update` returns, so `make gas-stations` exits non-zero too.

### An empty store skips the check

With 0 stored stations, the product is 0, and every non-empty list passes. The first run and a run after the operator empties the table work without a special case.

## Risks / Trade-offs

- [The feed really loses more than 10 % of its stations] → Every run fails, and the store keeps stations that no longer exist. The operator empties `gas_station` by hand and runs `make gas-stations`. The error log names both counts, so the cause is clear.
- [The check fails for many runs in a row] → The bot uses old prices and does not say so. Each failed run logs an error and exits non-zero, so the scheduler that starts the runs shows the failure.
- [A slow shrink of 5 % per run] → Each run passes, and the store follows the feed down. The check stops sudden drops only.

## Migration Plan

No schema change and no data migration. The next run applies the check. To roll back, revert the change.
