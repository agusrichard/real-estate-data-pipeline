# RentCast Market Data API Reference

Summary of the RentCast `/markets` endpoint relevant to this project, based on the official docs.

---

## Endpoint

| Method | Endpoint | Description |
|---|---|---|
| GET | `/markets` | Aggregate sale and rental statistics, pricing trends, and historical data for a single US zip code |

**Coverage:** ~96% of residential listings across all 50 US states, updated daily for the current month. Monthly snapshots are finalized at month-end.

**Data availability:**
- Sale history: from **January 2024** forward
- Rental history: from **April 2020** forward

---

## GET `/markets`

### Authentication

```
X-Api-Key: <your-api-key>
```

### Request Parameters

| Parameter | Type | Required | Description |
|---|---|---|---|
| `zipCode` | string | Yes | 5-digit zip code to retrieve market data for |

### Example Request

```bash
curl --request GET \
  --url 'https://api.rentcast.io/v1/markets?zipCode=78701' \
  --header 'X-Api-Key: <your-api-key>'
```

---

## Response Structure

The response is a single JSON object with the following top-level fields:

| Field | Type | Description |
|---|---|---|
| `id` | string | 5-digit zip code used as the record identifier |
| `zipCode` | string | 5-digit zip code |
| `saleData` | object | Aggregate statistics for active sale listings |
| `rentalData` | object | Aggregate statistics for active rental listings |

Both `saleData` and `rentalData` follow the same structure, described below.

---

## `saleData` / `rentalData` Structure

Each data block contains three levels of aggregation:

1. **Top-level stats** — all properties in the zip code combined
2. **`dataByPropertyType[]`** — stats broken down by property type (Condo, Single Family, etc.)
3. **`dataByBedrooms[]`** — stats broken down by bedroom count (0 = studio, 1, 2, 3, 4, 5, 6+)
4. **`history`** — monthly snapshots keyed by `YYYY-MM`

### Statistics Fields (appear at all three levels)

#### Sale Statistics

| Field | Type | Example | Description |
|---|---|---|---|
| `averagePrice` | number | 291933 | Mean listing price |
| `medianPrice` | number | 276990 | Median listing price |
| `minPrice` | number | 20000 | Lowest listing price |
| `maxPrice` | number | 1500000 | Highest listing price |
| `averagePricePerSquareFoot` | number | 186.53 | Mean price per sq ft |
| `medianPricePerSquareFoot` | number | 178 | Median price per sq ft |
| `minPricePerSquareFoot` | number | 64.9 | Lowest price per sq ft |
| `maxPricePerSquareFoot` | number | 500 | Highest price per sq ft |
| `averageSquareFootage` | number | 1698 | Mean living area in sq ft |
| `medianSquareFootage` | number | 1600 | Median living area in sq ft |
| `minSquareFootage` | number | 610 | Smallest listing in sq ft |
| `maxSquareFootage` | number | 4588 | Largest listing in sq ft |
| `averageDaysOnMarket` | number | 67.21 | Mean days active |
| `medianDaysOnMarket` | number | 45 | Median days active |
| `minDaysOnMarket` | number | 2 | Shortest active duration |
| `maxDaysOnMarket` | number | 348 | Longest active duration |
| `newListings` | number | 21 | New listings added this period |
| `totalListings` | number | 265 | Total active listings |

#### Rental Statistics (parallel structure, rent instead of price)

| Field | Type | Example | Description |
|---|---|---|---|
| `averageRent` | number | 1521 | Mean monthly rent |
| `medianRent` | number | 1495 | Median monthly rent |
| `minRent` | number | 750 | Lowest monthly rent |
| `maxRent` | number | 2700 | Highest monthly rent |
| `averageRentPerSquareFoot` | number | 1.38 | Mean rent per sq ft |
| `medianRentPerSquareFoot` | number | 1.30 | Median rent per sq ft |
| `minRentPerSquareFoot` | number | 0.86 | Lowest rent per sq ft |
| `maxRentPerSquareFoot` | number | 2.59 | Highest rent per sq ft |
| `averageSquareFootage` | number | 1175 | Mean living area |
| `medianSquareFootage` | number | 1100 | Median living area |
| `minSquareFootage` | number | 590 | Smallest rental |
| `maxSquareFootage` | number | 2100 | Largest rental |
| `averageDaysOnMarket` | number | 25 | Mean days listed |
| `medianDaysOnMarket` | number | 8 | Median days listed |
| `minDaysOnMarket` | number | 1 | Fastest rented |
| `maxDaysOnMarket` | number | 304 | Slowest rented |
| `newListings` | number | 18 | New rentals added this period |
| `totalListings` | number | 76 | Total active rentals |

### `dataByPropertyType[]` Fields

| Field | Type | Description |
|---|---|---|
| `propertyType` | string | Property category (e.g., `Single Family`, `Condo`, `Townhouse`) |
| *(all statistics fields)* | — | Same sale or rental stats fields as above |

### `dataByBedrooms[]` Fields

| Field | Type | Description |
|---|---|---|
| `bedrooms` | number | Bedroom count; `0` indicates studio |
| *(all statistics fields)* | — | Same sale or rental stats fields as above |

### `history` Object

Keyed by `YYYY-MM` (e.g., `"2025-01"`). Each entry contains the same statistics fields as the top-level, representing a finalized monthly snapshot.

```json
"history": {
  "2025-01": {
    "averagePrice": 285000,
    "medianPrice": 270000,
    "totalListings": 241,
    ...
  },
  "2025-02": { ... }
}
```

---

## Example Response (abbreviated)

```json
{
  "id": "78701",
  "zipCode": "78701",
  "saleData": {
    "lastUpdatedDate": "2025-08-15T00:00:00.000Z",
    "averagePrice": 291933,
    "medianPrice": 276990,
    "minPrice": 20000,
    "maxPrice": 1500000,
    "averagePricePerSquareFoot": 186.53,
    "medianPricePerSquareFoot": 178,
    "averageSquareFootage": 1698,
    "medianSquareFootage": 1600,
    "averageDaysOnMarket": 67.21,
    "medianDaysOnMarket": 45,
    "newListings": 21,
    "totalListings": 265,
    "dataByPropertyType": [
      {
        "propertyType": "Single Family",
        "averagePrice": 320000,
        "medianPrice": 299000,
        "totalListings": 140
      },
      {
        "propertyType": "Condo",
        "averagePrice": 245000,
        "medianPrice": 230000,
        "totalListings": 95
      }
    ],
    "dataByBedrooms": [
      {
        "bedrooms": 2,
        "averagePrice": 210000,
        "medianPrice": 199000,
        "totalListings": 80
      },
      {
        "bedrooms": 3,
        "averagePrice": 295000,
        "medianPrice": 280000,
        "totalListings": 120
      }
    ],
    "history": {
      "2025-06": {
        "averagePrice": 285000,
        "medianPrice": 270000,
        "totalListings": 241,
        "averageDaysOnMarket": 60
      },
      "2025-07": {
        "averagePrice": 288000,
        "medianPrice": 273000,
        "totalListings": 258,
        "averageDaysOnMarket": 63
      },
      "2025-08": {
        "averagePrice": 291933,
        "medianPrice": 276990,
        "totalListings": 265,
        "averageDaysOnMarket": 67
      }
    }
  },
  "rentalData": {
    "lastUpdatedDate": "2025-08-15T00:00:00.000Z",
    "averageRent": 1521,
    "medianRent": 1495,
    "minRent": 750,
    "maxRent": 2700,
    "averageRentPerSquareFoot": 1.38,
    "medianRentPerSquareFoot": 1.30,
    "totalListings": 76,
    "history": {
      "2025-06": { "averageRent": 1490, "medianRent": 1460, "totalListings": 70 },
      "2025-07": { "averageRent": 1505, "medianRent": 1475, "totalListings": 73 },
      "2025-08": { "averageRent": 1521, "medianRent": 1495, "totalListings": 76 }
    }
  }
}
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

## Fields Used in This Project

| Field | Used For |
|---|---|
| `zipCode` | Joining to `dim_location` |
| `saleData.medianPrice`, `saleData.averagePrice` | `fact_market_stats` — market price trends |
| `saleData.medianDaysOnMarket`, `saleData.totalListings` | Inventory analysis |
| `saleData.dataByPropertyType` | Per-type market breakdown |
| `saleData.history` | Market trends over time by zip code (Step 9 analytical query) |
| `rentalData.medianRent`, `rentalData.averageRent` | Optional: rent vs sale price comparison |

The nested `dataByBedrooms` and agent/contact fields are not needed for this project's analytics goals.
