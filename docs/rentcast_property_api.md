# RentCast Property Data API Reference

Summary of the RentCast `/properties` endpoints relevant to this project, based on the official docs.

---

## Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/properties` | Retrieve property records matching criteria (address, city/state/zip, or geo area) |
| GET | `/properties/{id}` | Retrieve a single property record by its RentCast ID |
| GET | `/properties/random` | Retrieve up to 500 randomly sampled property records (useful for testing) |

**Coverage:** Over 140 million properties across the US. Targets ≥96% for residential, ≥90% for 5+ unit commercial.

**Update frequency:** Individual records updated approximately once per week. Recent sales and tax assessments may take longer to appear.

**Note:** Field availability varies by county and state. The API returns all available fields for each property.

---

## GET `/properties`

### Authentication

```
X-Api-Key: <your-api-key>
```

### Request Parameters

#### Location (use one group)

| Parameter | Type | Description |
|---|---|---|
| `address` | string | Full address: `"Street, City, State, Zip"` |
| `city` + `state` | string | City name (case-sensitive) + 2-char state abbreviation |
| `zipCode` | string | 5-digit zip code |
| `latitude` + `longitude` + `radius` | number | Circular geo search; radius in miles, max 100 |

#### Property Filters

| Parameter | Type | Description |
|---|---|---|
| `propertyType` | string | `Single Family`, `Condo`, `Townhouse`, `Manufactured`, `Multi-Family`, `Apartment`, `Land` |
| `bedrooms` | string | Exact, range, or multiple values (e.g., `"3"`, `"2-4"`) |
| `bathrooms` | string | Includes fractions. Supports ranges and multiple values. |
| `squareFootage` | string | Living area in sq ft. Supports ranges and multiple values. |
| `lotSize` | string | Parcel area in sq ft. Supports ranges and multiple values. |
| `yearBuilt` | string | Construction year. Supports ranges and multiple values. |
| `saleDateRange` | string | Days since last sale, minimum 1. Supports ranges. |

#### Pagination

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 50 | Results per page, max 500 |
| `offset` | integer | 0 | Pagination index |
| `includeTotalCount` | boolean | — | If true, returns total count in `X-Total-Count` response header |

### Example Requests

```bash
# All properties in a zip code
curl --request GET \
  --url 'https://api.rentcast.io/v1/properties?zipCode=78701&limit=500' \
  --header 'X-Api-Key: <your-api-key>'

# Single family homes with 3 bedrooms in a zip code
curl --request GET \
  --url 'https://api.rentcast.io/v1/properties?zipCode=78701&propertyType=Single+Family&bedrooms=3&limit=500' \
  --header 'X-Api-Key: <your-api-key>'

# Single property by full address
curl --request GET \
  --url 'https://api.rentcast.io/v1/properties?address=5500+Grand+Lake+Dr%2C+San+Antonio%2C+TX+78244' \
  --header 'X-Api-Key: <your-api-key>'
```

---

## Response Structure

Returns a JSON array of property objects on success (HTTP 200).

### Address & Location Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique RentCast property identifier (e.g., `"5500-Grand-Lake-Dr,-San-Antonio,-TX-78244"`) |
| `formattedAddress` | string | Full address: `"Street, Unit, City, State Zip"` |
| `addressLine1` | string | Street address |
| `addressLine2` | string | Unit or apartment identifier |
| `city` | string | City name |
| `state` | string | 2-character state abbreviation |
| `stateFips` | string | 2-digit state FIPS code |
| `zipCode` | string | 5-digit postal code |
| `county` | string | County name |
| `countyFips` | string | 3-digit county FIPS code |
| `latitude` | number | Latitude coordinate |
| `longitude` | number | Longitude coordinate |

### Property Characteristic Fields

| Field | Type | Description |
|---|---|---|
| `propertyType` | string (enum) | Property category |
| `bedrooms` | number | Bedroom count |
| `bathrooms` | number | Bathroom count (includes fractions) |
| `squareFootage` | number | Living area in sq ft |
| `lotSize` | number | Parcel area in sq ft |
| `yearBuilt` | number | Year of construction |
| `assessorID` | string | County assessor / APN identifier |
| `legalDescription` | string | Parcel description from county records |
| `subdivision` | string | Subdivision name |
| `zoning` | string | Zoning code |

### Financial & Assessment Fields

| Field | Type | Description |
|---|---|---|
| `lastSaleDate` | datetime (ISO 8601) | Date of most recent sale |
| `lastSalePrice` | number | Price of most recent sale |
| `hoa.fee` | number | Monthly HOA assessment amount |
| `taxAssessments` | object | Keyed by year (`"2020"`–`"2024"`). Each entry has `value`, `land`, `improvements`. |
| `propertyTaxes` | object | Keyed by year. Each entry has `total`. |

### `features` Object

Detailed physical characteristics of the property.

| Field | Type | Description |
|---|---|---|
| `architectureType` | string | Architectural style (60+ values, e.g., `"Ranch"`, `"Victorian"`, `"Colonial"`) |
| `cooling` | boolean | Has cooling system |
| `coolingType` | string | e.g., `"Central"`, `"Evaporative"`, `"Split System"`, `"Geo-Thermal"` |
| `exteriorType` | string | Exterior material (50+ values, e.g., `"Brick"`, `"Vinyl Siding"`, `"Stucco"`) |
| `fireplace` | boolean | Has fireplace |
| `fireplaceType` | string | Fireplace style (e.g., `"1 Story"`, `"Stacked Stone"`) |
| `floorCount` | number | Number of floors |
| `foundationType` | string | e.g., `"Slab"`, `"Concrete Block"`, `"Pier"`, `"Raised"` |
| `garage` | boolean | Has garage |
| `garageSpaces` | number | Number of garage spaces |
| `garageType` | string | e.g., `"Attached"`, `"Detached"`, `"Carport"`, `"Underground"` |
| `heating` | boolean | Has heating system |
| `heatingType` | string | e.g., `"Forced Air"`, `"Heat Pump"`, `"Solar"` |
| `pool` | boolean | Has pool |
| `poolType` | string | Pool type (24+ values, e.g., `"Above-Ground"`, `"In-Ground"`, `"Hot Tub"`, `"Vinyl"`) |
| `roofType` | string | Roofing material |
| `roomCount` | number | Total room count |
| `unitCount` | number | Number of units (relevant for multi-family) |
| `viewType` | string | View classification (e.g., `"City"`) |

### `history` Object

Keyed by sale date (`YYYY-MM-DD`). Records confirmed sale transactions.

| Field | Type | Description |
|---|---|---|
| `event` | string | Currently always `"Sale"` |
| `date` | datetime (ISO 8601) | Sale transaction date |
| `price` | number | Sale transaction price |

### `owner` Object

| Field | Type | Description |
|---|---|---|
| `owner.names` | array of strings | Owner name(s) |
| `owner.type` | string | `"Individual"` or organization type |
| `owner.mailingAddress` | object | Full mailing address of the owner |
| `ownerOccupied` | boolean | Whether the owner currently occupies the property |

---

## Example Response (abbreviated)

```json
[
  {
    "id": "5500-Grand-Lake-Dr,-San-Antonio,-TX-78244",
    "formattedAddress": "5500 Grand Lake Dr, San Antonio, TX 78244",
    "addressLine1": "5500 Grand Lake Dr",
    "addressLine2": null,
    "city": "San Antonio",
    "state": "TX",
    "zipCode": "78244",
    "county": "Bexar",
    "latitude": 29.476,
    "longitude": -98.374,
    "propertyType": "Single Family",
    "bedrooms": 4,
    "bathrooms": 2,
    "squareFootage": 2100,
    "lotSize": 7200,
    "yearBuilt": 2003,
    "assessorID": "05076-001-0220",
    "legalDescription": "LOT 22 BLK 1 GRAND LAKE ESTATES UT-1",
    "subdivision": "Grand Lake Estates",
    "zoning": "R-4",
    "lastSaleDate": "2021-06-15T00:00:00.000Z",
    "lastSalePrice": 295000,
    "hoa": { "fee": 45 },
    "features": {
      "architectureType": "Ranch",
      "cooling": true,
      "coolingType": "Central",
      "exteriorType": "Brick",
      "fireplace": false,
      "floorCount": 1,
      "foundationType": "Slab",
      "garage": true,
      "garageSpaces": 2,
      "garageType": "Attached",
      "heating": true,
      "heatingType": "Forced Air",
      "pool": false,
      "roomCount": 8
    },
    "taxAssessments": {
      "2022": { "value": 278000, "land": 42000, "improvements": 236000 },
      "2023": { "value": 291000, "land": 44000, "improvements": 247000 },
      "2024": { "value": 305000, "land": 46000, "improvements": 259000 }
    },
    "propertyTaxes": {
      "2022": { "total": 5560 },
      "2023": { "total": 5820 },
      "2024": { "total": 6100 }
    },
    "history": {
      "2021-06-15": {
        "event": "Sale",
        "date": "2021-06-15T00:00:00.000Z",
        "price": 295000
      },
      "2016-03-22": {
        "event": "Sale",
        "date": "2016-03-22T00:00:00.000Z",
        "price": 210000
      }
    },
    "owner": {
      "names": ["John A Smith", "Mary B Smith"],
      "type": "Individual",
      "mailingAddress": {
        "addressLine1": "5500 Grand Lake Dr",
        "city": "San Antonio",
        "state": "TX",
        "zipCode": "78244"
      }
    },
    "ownerOccupied": true
  }
]
```

### Error Response (401)

```json
{
  "status": 401,
  "error": "auth/api-key-invalid",
  "message": "No API key provided in request..."
}
```

---

## Key Difference vs `/listings/sale`

| | `/properties` | `/listings/sale` |
|---|---|---|
| Data source | County assessor records + RentCast model | MLS feeds |
| Coverage | All ~140M US properties | Only listed/recently listed properties |
| Price field | `lastSalePrice` (last recorded sale) | `price` (current asking price) |
| Valuation | Tax assessment history via `taxAssessments` | No model estimate |
| Use case | Property attributes, ownership, sale history | Market inventory, days on market |

---

## Fields Used in This Project

| Field | Used For |
|---|---|
| `id`, `zipCode`, `city`, `state` | Joining to `dim_location` |
| `propertyType` | Joining to `dim_property_type` |
| `bedrooms`, `bathrooms`, `squareFootage`, `yearBuilt` | `fact_property_details` attributes |
| `lastSalePrice`, `lastSaleDate` | Price gap analysis vs Kaggle asking prices |
| `taxAssessments` | Year-over-year value trends |
| `latitude`, `longitude` | Geo enrichment |
| `features.cooling`, `features.garage`, `features.pool` | Optional property quality attributes |

Owner, legal description, zoning, and `propertyTaxes` fields are not needed for this project's analytics goals.
