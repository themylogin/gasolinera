# gas-station-inventory Specification

## Purpose

Keeps a copy of every Spanish fuel station that the MITECO REST service publishes, with its position, address, opening hours, and prices, and finds the stations in an area.

## Requirements

### Requirement: A run reads the full station list in one request

A run SHALL send one GET request to `https://sedeaplicaciones.minetur.gob.es/ServiciosRESTCarburantes/PreciosCarburantes/EstacionesTerrestres/` with the header `Accept: application/json`. It SHALL NOT use the province or community filters.

#### Scenario: One request per run

- **WHEN** a run completes
- **THEN** it sent exactly one request, to the full list address

### Requirement: The station id is the key

The stored id SHALL be the integer value of `IDEESS`.

#### Scenario: A listed station

- **WHEN** the list has an entry with `"IDEESS": "4375"`
- **THEN** the store has a station with id `4375`

### Requirement: The position is stored as numbers

The stored latitude SHALL be `Latitud`, and the stored longitude SHALL be `Longitud (WGS84)`. Each SHALL be converted from the decimal comma of the feed to a number.

#### Scenario: A decimal comma

- **WHEN** an entry has `"Latitud": "39,211417"` and `"Longitud (WGS84)": "-1,539167"`
- **THEN** the stored latitude is `39.211417` and the stored longitude is `-1.539167`

### Requirement: A station with a position outside Spain is skipped

A run SHALL skip an entry whose latitude is not between 27.0 and 44.0, or whose longitude is not between -18.5 and 4.5. It SHALL also skip an entry whose id or position cannot be read. It SHALL log the id and the reason of each skipped entry. A skipped entry SHALL NOT make the run fail.

#### Scenario: A station at 0,0

- **WHEN** an entry has `"Latitud": "0,000000"` and `"Longitud (WGS84)": "0,000000"`
- **THEN** the run stores no station for that entry, logs its id, and exits with the status 0

#### Scenario: Swapped coordinates

- **WHEN** an entry has `"Latitud": "-8,659472"` and `"Longitud (WGS84)": "42,037472"`
- **THEN** the run stores no station for that entry and logs its id

#### Scenario: A station in the Canary Islands

- **WHEN** an entry has `"Latitud": "27,7"` and `"Longitud (WGS84)": "-18,0"`
- **THEN** the run stores that station

### Requirement: The descriptive fields are stored as text

The store SHALL keep these fields of each entry as text, unchanged: `Rótulo` as the name, `Dirección` as the address, `C.P.` as the postal code, `Localidad`, `Municipio`, `Provincia`, and `Horario` as the opening hours.

#### Scenario: The fields of a station

- **WHEN** an entry has `"Rótulo": "Nº 10.935"`, `"Dirección": "AVENIDA CASTILLA LA MANCHA, 26"`, and `"Horario": "L-D: 07:00-22:00"`
- **THEN** the stored name, address, and opening hours are those three texts

### Requirement: The prices are stored as the feed sends them

The stored prices SHALL be a JSON object. It SHALL have one member for each field of the entry whose name starts with `Precio ` and whose value is not empty. The member name SHALL be the field name, and the member value SHALL be the field text, both unchanged.

#### Scenario: Two sold fuels

- **WHEN** an entry has `"Precio Gasoleo A": "1,799"`, `"Precio Gasolina 95 E5": "1,649"`, and every other price field empty
- **THEN** the stored prices are `{"Precio Gasoleo A": "1,799", "Precio Gasolina 95 E5": "1,649"}`

#### Scenario: A price field that the code does not know

- **WHEN** an entry has `"Precio Gasolina 100": "2,100"`
- **THEN** the stored prices contain `"Precio Gasolina 100": "2,100"`

### Requirement: The update time records the run

The stored `updated_at` of each station SHALL be the UTC time at which the run received the list.

#### Scenario: Every row has the time of the run

- **WHEN** a run stores 11,000 stations
- **THEN** all of them have the same `updated_at`, in UTC, between the start and the end of the run

### Requirement: The store equals the latest valid list

A successful run SHALL replace the stored stations with the stations of the list, in one transaction. A stored station that the list does not contain SHALL be deleted. A reader SHALL see either the old set or the new set, never a mix.

#### Scenario: A station leaves the list

- **GIVEN** a stored station with id `9999` that the new list does not contain
- **WHEN** the run completes
- **THEN** the store has no station with id `9999`

#### Scenario: A station changes its price

- **GIVEN** a stored station with `"Precio Gasoleo A": "1,799"`
- **WHEN** the list gives `"Precio Gasoleo A": "1,759"` for it and the run completes
- **THEN** the stored price is `"1,759"`

### Requirement: A run that cannot read the list changes nothing

The run SHALL exit with a non-zero status and SHALL NOT change the store when one of these occurs:

- the request fails or takes more than 120 seconds;
- the status is not 200;
- the body is not a JSON object;
- `ResultadoConsulta` is not `OK`;
- `ListaEESSPrecio` is missing or empty, or no entry is valid.

#### Scenario: The service is down

- **WHEN** the request returns the status 503
- **THEN** the run exits with a non-zero status and every stored row is unchanged

#### Scenario: An empty list

- **WHEN** the body is `{"ResultadoConsulta": "OK", "ListaEESSPrecio": []}`
- **THEN** the run exits with a non-zero status and every stored row is unchanged

#### Scenario: A failed query

- **WHEN** `ResultadoConsulta` is `Error`
- **THEN** the run exits with a non-zero status and every stored row is unchanged

### Requirement: A list much shorter than the store changes nothing

When the store holds stations, a run SHALL count the valid stations of the list. When that count is less than 90 % of the stored count, the run SHALL NOT change the store, SHALL log both counts, and SHALL exit with a non-zero status. An empty store SHALL accept any list with at least one valid station.

#### Scenario: A truncated list

- **GIVEN** a store with 100 stations
- **WHEN** the list gives 89 valid stations
- **THEN** the run exits with a non-zero status, every stored row is unchanged, and the log names 89 and 100

#### Scenario: A list at the limit

- **GIVEN** a store with 100 stations
- **WHEN** the list gives 90 valid stations
- **THEN** the run exits with the status 0 and the store holds those 90 stations

#### Scenario: Many entries that cannot be read

- **GIVEN** a store with 100 stations
- **WHEN** the list has 100 entries and 11 of them are skipped
- **THEN** the run exits with a non-zero status and every stored row is unchanged

#### Scenario: The first run

- **GIVEN** an empty store
- **WHEN** the list gives 2 valid stations
- **THEN** the run exits with the status 0 and the store holds those 2 stations

### Requirement: The run logs the feed date and the counts

The run SHALL log the `Fecha` of the feed, the number of entries, the number of stored stations, and the number of skipped entries.

#### Scenario: A normal run

- **WHEN** a run completes
- **THEN** its log names the feed date and the three counts

### Requirement: A caller finds the stations in an area through a geographic index

A caller SHALL be able to ask for the stations in a box, given by its south, west, north, and east bounds. The answer SHALL contain each station whose stored position is in the box or on its edge, and no other station. The query SHALL use the geographic index and SHALL NOT scan the station table.

#### Scenario: Only the stations in the box

- **GIVEN** a station at latitude `40.42`, longitude `-3.70`, and a station at latitude `41.39`, longitude `2.17`
- **WHEN** a caller asks for the box with south `40.0`, west `-4.0`, north `41.0`, and east `-3.0`
- **THEN** the answer contains the first station only

#### Scenario: A station on the edge

- **GIVEN** a station at latitude `40.0`, longitude `-3.0`
- **WHEN** a caller asks for the box with south `40.0`, west `-4.0`, north `41.0`, and east `-3.0`
- **THEN** the answer contains that station

#### Scenario: The query uses the index

- **WHEN** the query plan of an area query is inspected
- **THEN** it reads the geographic index and does not scan the whole station table

### Requirement: The index always agrees with the station table

The index SHALL hold exactly one entry for each stored station, at its stored position. This SHALL be true after each insert, update, and delete of a station row, whichever code makes the change.

#### Scenario: A new station is indexed

- **WHEN** a station row is inserted
- **THEN** the index has one entry for it, at its position

#### Scenario: A moved station is indexed at its new position

- **WHEN** the position of a stored station changes
- **THEN** its index entry is at the new position

#### Scenario: A deleted station leaves the index

- **WHEN** a station row is deleted
- **THEN** the index has no entry for it

### Requirement: The update is a one-shot Compose service

`docker-compose.yml` SHALL define the service `gas-stations`, built from the application image. `make gas-stations` SHALL start one run. The service SHALL use the `cache` volume and SHALL start only after `migrate` completes with success. A plain `docker compose up` SHALL NOT start it. It SHALL publish no port.

#### Scenario: The operator starts a run

- **WHEN** the operator runs `make gas-stations`
- **THEN** `migrate` completes, then one run starts, and the command exits with the status of that run

#### Scenario: Plain compose up does not start it

- **WHEN** `docker compose up -d` is run
- **THEN** the `gas-stations` service does not start
