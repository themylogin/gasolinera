# Spec Delta

## ADDED Requirements

### Requirement: One command renders the gauge picture

`make gauge-image` SHALL render `gasolinera/assets/gauges.png` from `gauge/12.png`, `gauge/8.jpg`, and `gauge/6.webp`, in a container. Each gauge SHALL be scaled to the same square size and SHALL keep its proportions. The gauges SHALL be in the order of the buttons `24`, `16`, `12`, and the picture SHALL have no text. The rendered picture SHALL be committed, and the bot SHALL NOT render it at run time.

#### Scenario: A fresh render

- **WHEN** `make gauge-image` runs
- **THEN** `gasolinera/assets/gauges.png` holds three gauges of one size side by side, with no text

#### Scenario: The bot image needs no image library

- **WHEN** the application image is built
- **THEN** `requirements.txt` names no image library
