# Tasks

## 1. The shrink check

- [x] 1.1 In `update` in `gasolinera/gas_stations.py`, count `gas_station` inside the replacement transaction. When `len(stations) * 10 < stored * 9`, log an error with both counts and return 1 before the delete. Verify with `make test`: the existing tests still pass.
- [x] 1.2 In `gasolinera/tests/test_gas_stations.py`, add tests for the four scenarios of the spec delta: 89 of 100 refused, 90 of 100 stored, 11 of 100 entries skipped refused, and 2 stations into an empty store. Build the stored rows with `insert_station` and the list from copies of a valid sample entry with new `IDEESS` values. Assert the exit status, the stored rows, and the literal counts in the log. Verify with `make test`.
- [x] 1.3 In the section "Gas stations" of `README.md`, state that a run changes nothing and exits non-zero when the list has fewer than 90 % of the stored stations. Verify that the text matches the spec delta.

## Workflow follow-up

- Archive the change after review. The archive merges the new requirement into `openspec/specs/gas-station-inventory/spec.md`.
