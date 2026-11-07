# Spec Delta

## Purpose

Groups the many MITECO price fields into the three fuels a driver chooses from, and gives the price a driver pays for a group at a station.

## ADDED Requirements

### Requirement: There are exactly three fuel groups

The code SHALL define exactly three fuel groups, in this order: `gasoline_95`, `gasoline_98`, `diesel`.

#### Scenario: The list of groups

- **WHEN** a caller asks for the fuel groups
- **THEN** the answer is `gasoline_95`, `gasoline_98`, `diesel`, in that order

### Requirement: The gasoline_95 group

The group `gasoline_95` SHALL contain exactly these price fields, in this order: `Precio Gasolina 95 E5`, `Precio Gasolina 95 E10`, `Precio Gasolina 95 E5 Premium`, `Precio Gasolina Renovable`.

#### Scenario: Renewable gasoline counts as 95

- **WHEN** a station has only `"Precio Gasolina Renovable": "1,849"`
- **THEN** its `gasoline_95` price is `1.849`, from `Precio Gasolina Renovable`

### Requirement: The gasoline_98 group

The group `gasoline_98` SHALL contain exactly these price fields, in this order: `Precio Gasolina 98 E5`, `Precio Gasolina 98 E10`.

#### Scenario: E10 counts as 98

- **WHEN** a station has only `"Precio Gasolina 98 E10": "1,859"`
- **THEN** its `gasoline_98` price is `1.859`, from `Precio Gasolina 98 E10`

### Requirement: The diesel group

The group `diesel` SHALL contain exactly these price fields, in this order: `Precio Gasoleo A`, `Precio Gasoleo Premium`, `Precio Diésel Renovable`.

#### Scenario: Renewable diesel counts as diesel

- **WHEN** a station has only `"Precio Diésel Renovable": "2,065"`
- **THEN** its `diesel` price is `2.065`, from `Precio Diésel Renovable`

### Requirement: A field outside the three groups belongs to no group

No price field SHALL be in more than one group. A price field that the three groups do not name SHALL be in no group.

#### Scenario: Agricultural diesel is not diesel

- **WHEN** a station has only `"Precio Gasoleo B": "1,549"`
- **THEN** the station has no `diesel` price

#### Scenario: E85 is not gasoline

- **WHEN** a station has only `"Precio Gasolina 95 E85": "2,009"`
- **THEN** the station has no `gasoline_95` price

### Requirement: The price of a group is its cheapest field

The price of a group at a station SHALL be the lowest price among the fields of that group that the station sells. The answer SHALL name the field that gives that price. When two fields have the same lowest price, the answer SHALL name the field that is first in the order of its group. When the station sells no field of the group, the answer SHALL be empty.

#### Scenario: Two diesel fields

- **WHEN** a station has `"Precio Gasoleo A": "1,799"` and `"Precio Gasoleo Premium": "1,899"`
- **THEN** its `diesel` price is `1.799`, from `Precio Gasoleo A`

#### Scenario: Premium is cheaper

- **WHEN** a station has `"Precio Gasolina 95 E5": "1,699"` and `"Precio Gasolina 95 E5 Premium": "1,659"`
- **THEN** its `gasoline_95` price is `1.659`, from `Precio Gasolina 95 E5 Premium`

#### Scenario: Equal prices

- **WHEN** a station has `"Precio Gasolina 98 E5": "1,869"` and `"Precio Gasolina 98 E10": "1,869"`
- **THEN** its `gasoline_98` price is `1.869`, from `Precio Gasolina 98 E5`

#### Scenario: No field of the group

- **WHEN** a station has only `"Precio Gasoleo A": "1,799"`
- **THEN** its `gasoline_98` price is empty

### Requirement: A price is read exactly from the stored text

A price SHALL be read from the stored text with the decimal comma as the decimal separator, with no rounding. A text that is not a decimal number SHALL be ignored, as if the station did not sell that field.

#### Scenario: Exact value

- **WHEN** the stored text is `"1,459"`
- **THEN** the price is exactly `1.459`

#### Scenario: Text that is not a price

- **WHEN** a station has `"Precio Gasoleo A": "n/d"` and `"Precio Gasoleo Premium": "1,899"`
- **THEN** its `diesel` price is `1.899`, from `Precio Gasoleo Premium`
