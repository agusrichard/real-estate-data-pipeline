# RentCast Property Valuation API Reference

Summary of the RentCast `/avm` endpoints relevant to this project, based on the official docs.

---

## Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/avm/value` | AVM-generated sale value estimate for a property, with comparable sale listings |
| GET | `/avm/rent/long-term` | AVM-generated long-term rental estimate for a property, with comparable rental listings |

**How it works:** RentCast scans sale and rental listings across the US, identifies comparable properties (matching type, size, attributes, and location), and applies a proprietary weighted average formula to produce the estimate.

**Key notes:**
- By default (`lookupSubjectAttributes=true`), the API automatically looks up the property's attributes (beds, baths, sq ft, type) from its records. You can override with manual values via query parameters.
- Value estimates apply to the **entire building** for multi-family properties. Rent estimates apply to **individual units**.
- Confidence interval: the `Low`/`High` range fields represent an **85% confidence interval** — the estimate is expected to fall within that range 85% of the time.

---

## GET `/avm/value`

Retrieve a current sale value estimate (AVM) for a specific property.

### Authentication

```
X-Api-Key: <your-api-key>
```

### Request Parameters

#### Location (one required)

| Parameter | Type | Required | Description |
|---|---|---|---|
| `address` | string | Conditional | Full address: `"Street, City, State, Zip"` |
| `latitude` + `longitude` | number | Conditional | Coordinates of the property |

#### Property Attribute Overrides (optional — used when `lookupSubjectAttributes=false`)

| Parameter | Type | Description |
|---|---|---|
| `propertyType` | string | `Single Family`, `Condo`, `Townhouse`, `Manufactured`, `Multi-Family`, `Apartment`, `Land` |
| `bedrooms` | number | Bedroom count; use `0` for studio |
| `bathrooms` | number | Bathroom count; supports fractions (e.g., `2.5`) |
| `squareFootage` | number | Living area in sq ft |

#### Comparables Tuning (optional)

| Parameter | Type | Default | Description |
|---|---|---|---|
| `maxRadius` | number | — | Max distance in miles for comparable selection |
| `daysOld` | integer | — | Max age in days of comparable listings (minimum 1) |
| `compCount` | integer | 15 | Number of comparables to return (5–25) |
| `lookupSubjectAttributes` | boolean | true | Auto-lookup property attributes from RentCast records |

### Example Requests

```bash
# Estimate by full address (attributes auto-looked up)
curl --request GET \
  --url 'https://api.rentcast.io/v1/avm/value?address=5500+Grand+Lake+Dr%2C+San+Antonio%2C+TX%2C+78244' \
  --header 'X-Api-Key: <your-api-key>'

# Estimate with manual attribute override
curl --request GET \
  --url 'https://api.rentcast.io/v1/avm/value?address=5500+Grand+Lake+Dr%2C+San+Antonio%2C+TX%2C+78244&bedrooms=4&bathrooms=2&squareFootage=2100&propertyType=Single+Family' \
  --header 'X-Api-Key: <your-api-key>'
```

---

## Response Structure

### Top-Level Fields

| Field | Type | Description |
|---|---|---|
| `price` | number | AVM estimate of current market value |
| `priceRangeLow` | number | Lower bound of the 85% confidence interval |
| `priceRangeHigh` | number | Upper bound of the 85% confidence interval |
| `subjectProperty` | object | Property record used as the basis for the estimate |
| `comparables` | array | Comparable sale listings used in the AVM calculation |

### `subjectProperty` Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | RentCast property identifier |
| `formattedAddress` | string | Full formatted address |
| `addressLine1`, `addressLine2` | string | Address components |
| `city`, `state` | string | Location |
| `stateFips`, `zipCode`, `county`, `countyFips` | string | Geographic identifiers |
| `latitude`, `longitude` | number | Coordinates |
| `propertyType` | string (enum) | Property category |
| `bedrooms`, `bathrooms` | number | Unit counts |
| `squareFootage`, `lotSize` | number | Area measurements in sq ft |
| `yearBuilt` | number | Construction year |
| `lastSaleDate` | datetime (ISO 8601) | Date of most recent recorded sale |
| `lastSalePrice` | number | Price of most recent recorded sale |

> **Note:** Fields returned in `subjectProperty` vary based on query parameters provided and availability of property record data in RentCast's database.

### `comparables[]` Fields

Each comparable is a sale listing similar to the subject property, used to calculate the AVM.

| Field | Type | Description |
|---|---|---|
| `id` | string | RentCast property identifier |
| `formattedAddress` | string | Full formatted address |
| `latitude`, `longitude` | number | Coordinates |
| `propertyType` | string | Property category |
| `bedrooms`, `bathrooms` | number | Unit counts |
| `squareFootage` | number | Living area in sq ft |
| `yearBuilt` | number | Construction year |
| `status` | string (enum) | Listing status |
| `price` | number | Listed price of the comparable |
| `listingType` | string (enum) | e.g., `Standard`, `New Construction` |
| `listedDate` | datetime (ISO 8601) | Date first listed |
| `removedDate` | datetime (ISO 8601) | Date removed; null if still active |
| `lastSeenDate` | datetime (ISO 8601) | Date last observed active |
| `daysOnMarket` | number | Days the listing was active |
| `distance` | number | Distance from subject property in miles |
| `daysOld` | number | Age of the listing in days at time of estimate |
| `correlation` | number | Similarity score to the subject (0–1, where 1 = identical match) |

---

## Example Response (abbreviated)

```json
{
  "price": 250000,
  "priceRangeLow": 195000,
  "priceRangeHigh": 304000,
  "subjectProperty": {
    "id": "5500-Grand-Lake-Dr,-San-Antonio,-TX-78244",
    "formattedAddress": "5500 Grand Lake Dr, San Antonio, TX 78244",
    "addressLine1": "5500 Grand Lake Dr",
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
    "lastSaleDate": "2021-06-15T00:00:00.000Z",
    "lastSalePrice": 295000
  },
  "comparables": [
    {
      "id": "5210-Walzem-Rd,-San-Antonio,-TX-78218",
      "formattedAddress": "5210 Walzem Rd, San Antonio, TX 78218",
      "latitude": 29.481,
      "longitude": -98.380,
      "propertyType": "Single Family",
      "bedrooms": 4,
      "bathrooms": 2,
      "squareFootage": 2050,
      "yearBuilt": 2001,
      "status": "Inactive",
      "price": 245000,
      "listingType": "Standard",
      "listedDate": "2024-09-01T00:00:00.000Z",
      "removedDate": "2024-11-15T00:00:00.000Z",
      "lastSeenDate": "2024-11-15T00:00:00.000Z",
      "daysOnMarket": 75,
      "distance": 0.8,
      "daysOld": 120,
      "correlation": 0.94
    },
    {
      "id": "5800-Timberhill-Dr,-San-Antonio,-TX-78244",
      "formattedAddress": "5800 Timberhill Dr, San Antonio, TX 78244",
      "latitude": 29.472,
      "longitude": -98.370,
      "propertyType": "Single Family",
      "bedrooms": 3,
      "bathrooms": 2,
      "squareFootage": 1950,
      "yearBuilt": 2005,
      "status": "Active",
      "price": 255000,
      "listingType": "Standard",
      "listedDate": "2025-01-10T00:00:00.000Z",
      "removedDate": null,
      "lastSeenDate": "2025-03-01T00:00:00.000Z",
      "daysOnMarket": 50,
      "distance": 0.4,
      "daysOld": 51,
      "correlation": 0.89
    }
  ]
}
```

### Error Response (401)

```json
{
  "status": 401,
  "error": "auth/api-key-invalid",
  "message": "No API key provided in request. An API key must be provided in the 'X-Api-Key' header"
}
```

---

## How This Differs from `/properties`

| | `/avm/value` | `/properties` |
|---|---|---|
| Price field | `price` — model-generated current value estimate | `lastSalePrice` — last recorded transaction price |
| Data source | RentCast AVM (comparable-based algorithm) | County assessor / public records |
| Freshness | Reflects current market conditions | Last sale may be years old |
| Confidence range | `priceRangeLow` / `priceRangeHigh` (85% CI) | Not applicable |
| Comparables | Included — shows what the estimate is based on | Not included |

---

## Fields Used in This Project

| Field | Used For |
|---|---|
| `price` | AVM estimate — core input for price gap analysis vs Kaggle asking prices |
| `priceRangeLow`, `priceRangeHigh` | Confidence interval around the estimate |
| `subjectProperty.zipCode`, `subjectProperty.city`, `subjectProperty.state` | Joining to `dim_location` |
| `subjectProperty.propertyType` | Joining to `dim_property_type` |
| `subjectProperty.bedrooms`, `subjectProperty.bathrooms`, `subjectProperty.squareFootage` | `fact_property_details` attributes |
| `subjectProperty.lastSalePrice`, `subjectProperty.lastSaleDate` | Historical sale anchor for price gap analysis |
| `comparables[].correlation`, `comparables[].distance` | Optional: AVM confidence diagnostics |

The `comparables` array in full is not stored — only the subject property fields and the top-level estimate are needed for `fact_property_details`.
