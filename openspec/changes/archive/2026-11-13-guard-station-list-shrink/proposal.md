# Proposal

## Why

A run replaces every stored station with the stations of the feed. The run already refuses an empty list and a list with no valid entry. It does not refuse a list that is much shorter than the store, for example a truncated answer with 300 of 12,000 stations. Such a run deletes most stations, and the bot cannot find fuel on most routes until a later run succeeds.

## What Changes

- Before the replacement, the run compares the number of valid stations in the feed with the number of stored stations.
- When the feed has fewer than 90 % of the stored count, the run logs both counts, changes nothing, and exits with a non-zero status. The bot keeps the old stations until a later run gets a full list.
- An empty store accepts any non-empty valid list, so the first run still works.
- The README states the new refusal.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `gas-station-inventory`: a new requirement makes a run refuse a list that is much shorter than the store.

## Impact

- `gasolinera/gas_stations.py`: `update` counts the stored stations in the replacement transaction and stops before the delete.
- `gasolinera/tests/test_gas_stations.py`: new tests for the refusal, the limit, and the empty store.
- `README.md`: one paragraph in the section "Gas stations".
- No schema change, no new dependency, no new configuration variable.
