# Spec Delta

## Purpose

Reads the `Horario` text of a station and tells whether the station is open, closing soon, or closed at a local arrival time, or that its schedule is unknown.

## ADDED Requirements

### Requirement: A schedule is a list of day groups with times

A schedule SHALL be one or more parts separated by `;`. Each part SHALL be `<days>: <times>`:

- `<days>` is one or more items separated by `,`. An item is a day letter, or two day letters joined by `-`.
- `<times>` is `24H`, or one or more ranges joined by ` y `. A range is `H:MM-H:MM` or `HH:MM-HH:MM`.

The day letters SHALL be `L` Monday, `M` Tuesday, `X` Wednesday, `J` Thursday, `V` Friday, `S` Saturday, `D` Sunday. White space around `-`, `:`, `,`, and `;` SHALL be allowed.

#### Scenario: Two parts

- **WHEN** the schedule is `L-V: 06:00-22:00; S-D: 07:00-22:00`
- **THEN** the station opens Monday to Friday from 06:00 to 22:00, and Saturday and Sunday from 07:00 to 22:00

#### Scenario: Two ranges in one day

- **WHEN** the schedule is `L-V: 09:00-14:00 y 15:00-18:00; S: 9:00-13:30`
- **THEN** the station is closed on Wednesday at 14:30, and open on Saturday at 09:15

#### Scenario: A space before the dash

- **WHEN** the schedule is `L-S: 8:00 -21:00`
- **THEN** the station opens Monday to Saturday from 08:00 to 21:00

### Requirement: A day that the schedule does not name is closed

A day that no part names SHALL be closed for the whole day.

#### Scenario: Closed on Sunday

- **WHEN** the schedule is `L-S: 06:00-22:00` and the arrival is on Sunday at 12:00
- **THEN** the station is closed

### Requirement: A range that ends at or before its start ends the next day

When the end of a range is at or before its start, the range SHALL end at that time on the next day. `00:00` as an end SHALL be midnight. A range from a time to the same time SHALL be the whole day.

#### Scenario: Open until midnight

- **WHEN** the schedule is `L-D: 06:00-00:00` and the arrival is at 23:30
- **THEN** the station is open

#### Scenario: Open after midnight

- **WHEN** the schedule is `V: 06:00-02:00` and the arrival is on Saturday at 01:00
- **THEN** the station is open

### Requirement: Adjacent open times join

Open times SHALL join when one ends where the next one starts, also across midnight and across the week. A range that ends at `23:59` SHALL end at midnight. A schedule that is open for the whole week SHALL have no closing time.

#### Scenario: Open all week

- **WHEN** the schedule is `L-D: 00:00-23:59`
- **THEN** the station is open at any arrival, and never closing soon

#### Scenario: 24H on every day

- **WHEN** the schedule is `L-D: 24H` and the arrival is on Sunday at 23:55
- **THEN** the station is open and not closing soon

### Requirement: The state at an arrival time

For a local arrival time, the state SHALL be:

- `closed` when the arrival is in no open time;
- `closing_soon` when the arrival is in an open time that ends less than 20 minutes after it;
- `open` otherwise.

A `closing_soon` state SHALL carry the local closing time.

#### Scenario: 19 minutes before closing

- **WHEN** the schedule is `L-D: 06:00-22:00` and the arrival is at 21:41
- **THEN** the state is `closing_soon`, with the closing time 22:00

#### Scenario: 20 minutes before closing

- **WHEN** the schedule is `L-D: 06:00-22:00` and the arrival is at 21:40
- **THEN** the state is `open`

#### Scenario: At the closing time

- **WHEN** the schedule is `L-D: 06:00-22:00` and the arrival is at 22:00
- **THEN** the state is `closed`

#### Scenario: Before opening

- **WHEN** the schedule is `L-D: 06:00-22:00` and the arrival is at 05:59
- **THEN** the state is `closed`

### Requirement: A schedule that cannot be read is unknown

The state SHALL be `unknown` when the schedule does not follow the grammar, when it is empty, when a day item goes backwards such as `D-L`, or when a time is not a time of day.

#### Scenario: Free text

- **WHEN** the schedule is `Consultar`
- **THEN** the state is `unknown`

#### Scenario: An hour that does not exist

- **WHEN** the schedule is `L-D: 06:00-25:00`
- **THEN** the state is `unknown`

### Requirement: A schedule that names only Monday is unknown

A schedule whose parts together name only Monday SHALL be `unknown`. The source has hundreds of such schedules, and they do not describe a station that opens on Monday only.

#### Scenario: Monday at any hour

- **WHEN** the schedule is `L: 24H`
- **THEN** the state is `unknown` on every day

#### Scenario: Monday and Sunday

- **WHEN** the schedule is `L: 06:00-22:00; D: 06:00-22:00` and the arrival is on Tuesday at 12:00
- **THEN** the state is `closed`
