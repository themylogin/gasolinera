# Spec Delta

## ADDED Requirements

### Requirement: The 24-step gauge

The 24-step gauge SHALL have four rows. Each row SHALL be one quarter of the tank, from its top to its bottom, one button for each step:

1. `1`, `.`, `.`, `|`, `.`, `.`, `3/4` for 24 down to 18;
2. `3/4`, `.`, `.`, `|`, `.`, `.`, `1/2` for 18 down to 12;
3. `1/2`, `.`, `.`, `|`, `.`, `.`, `1/4` for 12 down to 6;
4. `1/4`, `.`, `.`, `|`, `.`, `.`, `0` for 6 down to 0.

#### Scenario: The rows

- **WHEN** the car has a gauge of 24 steps and the bot asks the fuel question
- **THEN** the rows are `1 . . | . . 3/4`, `3/4 . . | . . 1/2`, `1/2 . . | . . 1/4`, and `1/4 . . | . . 0`

### Requirement: The 16-step gauge

The 16-step gauge SHALL have four rows. Each row SHALL be one quarter of the tank, from its top to its bottom, one button for each step:

1. `1`, `.`, `|`, `,`, `3/4` for 16 down to 12;
2. `3/4`, `.`, `|`, `,`, `1/2` for 12 down to 8;
3. `1/2`, `.`, `|`, `,`, `1/4` for 8 down to 4;
4. `1/4`, `.`, `|`, `,`, `0` for 4 down to 0.

#### Scenario: The rows

- **WHEN** the car has a gauge of 16 steps and the bot asks the fuel question
- **THEN** the rows are `1 . | , 3/4`, `3/4 . | , 1/2`, `1/2 . | , 1/4`, and `1/4 . | , 0`

### Requirement: The 12-step gauge

The 12-step gauge SHALL have two rows. Each row SHALL be one half of the tank, from its top to its bottom, one button for each step:

1. `1`, `.`, `5/6`, `.`, `2/3`, `.`, `1/2` for 12 down to 6;
2. `1/2`, `.`, `1/3`, `.`, `1/6`, `.`, `0` for 6 down to 0.

#### Scenario: The rows

- **WHEN** the car has a gauge of 12 steps and the bot asks the fuel question
- **THEN** the rows are `1 . 5/6 . 2/3 . 1/2` and `1/2 . 1/3 . 1/6 . 0`

### Requirement: The 0 mark plans the stop at the origin

A press on `0` SHALL start the refuel search with 0 L. The search point is then the origin, because the tank holds 5 L or less there.

#### Scenario: An empty tank

- **GIVEN** a car with a tank of 50 L
- **WHEN** the user presses `0`
- **THEN** the question becomes `Combustible: 0 (0 L)`, and the search looks for stations near the origin

## MODIFIED Requirements

### Requirement: The fuel question shows a gauge

The fuel question SHALL have the inline keyboard of the gauge of the car: the 24-step, the 16-step, or the 12-step gauge. A row SHALL repeat the label that ends the row before it, and both buttons SHALL have the same value.

#### Scenario: The keyboard

- **GIVEN** a car with a gauge of 12 steps
- **WHEN** the bot asks the fuel question
- **THEN** the keyboard is the 12-step gauge

#### Scenario: Two buttons with one value

- **GIVEN** a car with a gauge of 16 steps
- **WHEN** the user presses the `3/4` at the end of the first row, or the `3/4` at the start of the second row
- **THEN** the fuel is three quarters of the tank in both cases

### Requirement: A gauge press gives the fuel in the tank

A press SHALL start the refuel search with the tank volume multiplied by the step of the button and divided by the steps of the gauge, in liters. The question SHALL become `Combustible: <mark> (<liters> L)` with no buttons. `<mark>` SHALL be the button label, or the reduced fraction of the step for a `.`, `,`, or `|` button. `<liters>` SHALL be rounded to one decimal, with a comma and no trailing zero.

#### Scenario: Half a tank

- **GIVEN** a car with a tank of 50 L and a gauge of 16 steps
- **WHEN** the user presses `1/2`
- **THEN** the question becomes `Combustible: 1/2 (25 L)`, and the search starts with 25 L

#### Scenario: A mark between two labels

- **GIVEN** a car with a tank of 50 L and a gauge of 24 steps
- **WHEN** the user presses the `|` for step 21
- **THEN** the question becomes `Combustible: 7/8 (43,8 L)`, and the search starts with 43.75 L

#### Scenario: A full tank

- **GIVEN** a car with a tank of 50 L and a gauge of 12 steps
- **WHEN** the user presses `1`
- **THEN** the question becomes `Combustible: 1 (50 L)`
