# RentCast API Reference

Summary of the RentCast API endpoints relevant to this project, based on the official docs.

---

## Available Listing Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/listings/sale` | Sale listings matching criteria (city, state, zip, geo area) |
| GET | `/listings/sale/{id}` | A single sale listing by its RentCast ID |
| GET | `/listings/rental/long-term` | Long-term rental listings matching criteria |
| GET | `/listings/rental/long-term/{id}` | A single rental listing by its RentCast ID |

**Coverage:** RentCast aims for ≥96% sale and rental listing coverage across all 50 US states for residential properties.

---

## GET `/listings/sale`

Retrieve active or inactive sale listings filtered by location and property attributes.

### Authentication

All requests require an API key passed as a request header:

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
| `propertyType` | string | `Single Family`, `Condo`, `Townhouse`, `Manufactured`, `Multi-Family`, `Apartment`, `Land`. Supports multiple values. |
| `bedrooms` | string | Exact count, range, or multiple values (e.g., `"3"`, `"2-4"`) |
| `bathrooms` | string | Includes fractions. Supports ranges and multiple values. |
| `squareFootage` | string | Living area in sq ft. Supports ranges and multiple values. |
| `lotSize` | string | Parcel area in sq ft. Supports ranges and multiple values. |
| `yearBuilt` | string | Construction year. Supports ranges and multiple values. |
| `price` | string | Listed price. Supports ranges and multiple values. |
| `status` | string | `Active` (default) or `Inactive` |
| `daysOld` | string | Days on market, minimum 1. Supports ranges. |

#### Pagination

| Parameter | Type | Default | Description |
|---|---|---|---|
| `limit` | integer | 50 | Results per page, max 500 |
| `offset` | integer | 0 | Pagination index |
| `includeTotalCount` | boolean | — | If true, returns total count in `X-Total-Count` response header |

### Example Request

```bash
curl --request GET \
  --url 'https://api.rentcast.io/v1/listings/sale?zipCode=78701&status=Active&limit=500' \
  --header 'X-Api-Key: <your-api-key>'
```

### Response

Returns a JSON array of listing objects. HTTP 200 on success.

#### Example Response (abbreviated)

```json
[
  {
    "id": "123-Main-St-Austin-TX-78701",
    "formattedAddress": "123 Main St, Austin, TX 78701",
    "addressLine1": "123 Main St",
    "addressLine2": null,
    "city": "Austin",
    "state": "TX",
    "zipCode": "78701",
    "county": "Travis",
    "latitude": 30.267,
    "longitude": -97.743,
    "propertyType": "Single Family",
    "bedrooms": 3,
    "bathrooms": 2,
    "squareFootage": 1850,
    "lotSize": 6500,
    "yearBuilt": 1998,
    "hoa": { "fee": 120 },
    "status": "Active",
    "price": 549000,
    "listingType": "Standard",
    "listedDate": "2024-01-15T00:00:00.000Z",
    "removedDate": null,
    "createdDate": "2024-01-15T08:00:00.000Z",
    "lastSeenDate": "2024-03-01T08:00:00.000Z",
    "daysOnMarket": 45,
    "mlsName": "Austin Board of Realtors",
    "mlsNumber": "ABC123456",
    "listingAgent": {
      "name": "Jane Smith",
      "phone": "512-555-0100",
      "email": "jane@realty.com",
      "website": "https://realty.com"
    },
    "listingOffice": {
      "name": "Austin Realty Group",
      "phone": "512-555-0200",
      "email": "office@realty.com",
      "website": "https://realty.com"
    },
    "history": {
      "2024-01-15": {
        "event": "Listed",
        "price": 560000,
        "listingType": "Standard",
        "listedDate": "2024-01-15T00:00:00.000Z",
        "removedDate": null,
        "daysOnMarket": 0
      },
      "2024-02-01": {
        "event": "Price Change",
        "price": 549000,
        "listingType": "Standard",
        "listedDate": "2024-01-15T00:00:00.000Z",
        "removedDate": null,
        "daysOnMarket": 17
      }
    }
  }
]
```

#### Error Response (401)

```json
{
  "status": 401,
  "error": "auth/api-key-invalid",
  "message": "No API key provided in request..."
}
```

---

## Property Listing Schema

Full field reference for any listing object returned by the endpoints above.

### Address Fields

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique RentCast property identifier |
| `formattedAddress` | string | Full address: `"Street, Unit, City, State Zip"` |
| `addressLine1` | string | Street address |
| `addressLine2` | string | Unit or apartment identifier |
| `city` | string | City name |
| `state` | string | 2-character state abbreviation |
| `stateFips` | string | 2-digit state FIPS code |
| `zipCode` | string | 5-digit postal code |
| `county` | string | County name |
| `countyFips` | string | 3-digit county FIPS code |

### Geographic Fields

| Field | Type | Description |
|---|---|---|
| `latitude` | number | Latitude coordinate |
| `longitude` | number | Longitude coordinate |

### Property Attribute Fields

| Field | Type | Description |
|---|---|---|
| `propertyType` | string (enum) | Property category (see values above) |
| `bedrooms` | number | Bedroom count |
| `bathrooms` | number | Bathroom count (includes fractions, e.g. 2.5) |
| `squareFootage` | number | Living area in sq ft |
| `lotSize` | number | Parcel area in sq ft |
| `yearBuilt` | number | Year of construction |
| `hoa.fee` | number | Monthly HOA assessment amount |

### Listing Fields

| Field | Type | Description |
|---|---|---|
| `status` | string (enum) | `Active` or `Inactive` |
| `price` | number | Listed price (sale) or rent (rental) |
| `listingType` | string (enum) | `Standard`, `New Construction`, `Foreclosure`, or `Short Sale` |
| `listedDate` | datetime (ISO 8601) | Date the listing first appeared |
| `removedDate` | datetime (ISO 8601) | Date the listing was removed; null if still active |
| `createdDate` | datetime (ISO 8601) | Date the record was created in RentCast |
| `lastSeenDate` | datetime (ISO 8601) | Date the listing was last observed active |
| `daysOnMarket` | number | Number of days the listing has been active |
| `mlsName` | string | MLS the listing is sourced from |
| `mlsNumber` | string | MLS listing identifier |

### Agent & Office Fields

| Field | Type | Description |
|---|---|---|
| `listingAgent.name` | string | Agent full name |
| `listingAgent.phone` | string | Agent phone number |
| `listingAgent.email` | string | Agent email address |
| `listingAgent.website` | string | Agent website URL |
| `listingOffice.name` | string | Brokerage name |
| `listingOffice.phone` | string | Brokerage phone number |
| `listingOffice.email` | string | Brokerage email address |
| `listingOffice.website` | string | Brokerage website URL |

### Builder Fields (New Construction only)

| Field | Type | Description |
|---|---|---|
| `builder.name` | string | Builder company name |
| `builder.development` | string | Development or community name |
| `builder.phone` | string | Builder phone number |
| `builder.website` | string | Builder website URL |

### History Field

| Field | Type | Description |
|---|---|---|
| `history` | object | Keys are dates (`YYYY-MM-DD`). Each entry records a listing event (price change, status change, etc.) with `event`, `price`, `listingType`, `listedDate`, `removedDate`, and `daysOnMarket`. |

---

## Pagination Notes

- Default page size: **50**; maximum: **500**
- Use `offset` to page through results: first page is `offset=0`, second is `offset=500`, etc.
- Set `includeTotalCount=true` to get the total record count in the `X-Total-Count` response header — useful for knowing how many pages to fetch
- The Lambda handler must loop until fewer than `limit` results are returned (or `offset >= total_count`)

---

## Fields Used in This Project

Not all fields are needed. The columns relevant to our analytical goals:

| Field | Used For |
|---|---|
| `id`, `zipCode`, `city`, `state` | Joining to `dim_location` |
| `propertyType` | Joining to `dim_property_type` |
| `price`, `listingType`, `status` | `fact_listings` measures |
| `bedrooms`, `bathrooms`, `squareFootage`, `yearBuilt` | Property attributes |
| `daysOnMarket`, `listedDate` | Inventory analysis |
| `history` | Price gap analysis (listing price over time) |
| `latitude`, `longitude` | Optional geo enrichment |
