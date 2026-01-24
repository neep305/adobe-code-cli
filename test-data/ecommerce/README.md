# E-commerce Test Data

This directory contains realistic mock data for testing Adobe Experience Platform schema generation and data ingestion.

## Data Files

### 1. `customers.json`
Customer profile data with demographics, contact information, and loyalty metrics.

**Fields:**
- Customer ID, email, name, phone
- Address (street, city, state, postal code, country)
- Account details (created date, status, tier)
- Purchase metrics (total orders, lifetime value, loyalty points)
- Marketing preferences (email, SMS, push notifications)

**Use Case:** Generate XDM Profile schemas for customer identity and segmentation.

### 2. `events.json`
Customer interaction events across the purchase journey.

**Event Types:**
- `page_view` - Website page visits
- `product_view` - Product detail page views
- `search` - Product searches
- `add_to_cart` - Items added to shopping cart
- `add_to_wishlist` - Items saved for later
- `checkout_started` - Checkout process initiated
- `purchase` - Completed transactions
- `cart_abandoned` - Shopping carts left without purchase

**Use Case:** Generate XDM ExperienceEvent schemas for behavioral analytics.

### 3. `products.json`
Product catalog with detailed attributes and inventory information.

**Fields:**
- Product ID, SKU, name, description
- Category hierarchy, brand
- Pricing (price, cost, margin, currency)
- Inventory quantity, dimensions, weight
- Product attributes (color, size, specifications)
- Images, ratings, reviews
- Status and tags

**Use Case:** Generate product catalog schemas for merchandising and recommendations.

### 4. `orders.json`
Transaction records with line items and fulfillment details.

**Fields:**
- Order ID, order number, customer ID
- Order status (processing, completed, cancelled)
- Payment details (method, status, card info)
- Shipping and billing addresses
- Line items (products, quantities, prices)
- Shipping method, tracking, delivery dates
- Discounts, taxes, totals

**Use Case:** Generate order schemas for revenue analytics and fulfillment tracking.

## Testing Scenarios

### Basic Schema Generation
```bash
# Generate customer profile schema
adobe-aep schema create \
  --name "Customer Profile" \
  --from-sample test-data/ecommerce/customers.json \
  --output schemas/customer-profile.json

# Generate event schema with AI recommendations
adobe-aep schema create \
  --name "Customer Events" \
  --from-sample test-data/ecommerce/events.json \
  --use-ai \
  --output schemas/customer-events.json
```

### Multi-Entity Schema Design
```bash
# Product catalog schema
adobe-aep schema create \
  --name "Product Catalog" \
  --from-sample test-data/ecommerce/products.json \
  --description "E-commerce product catalog with inventory"

# Order transaction schema
adobe-aep schema create \
  --name "Order Transactions" \
  --from-sample test-data/ecommerce/orders.json \
  --description "E-commerce order and fulfillment data"
```

### Schema Upload to AEP
```bash
# Generate and upload directly to AEP
adobe-aep schema create \
  --name "E-commerce Customer Profile" \
  --from-sample test-data/ecommerce/customers.json \
  --use-ai \
  --upload
```

## Data Relationships

```
customers.json (customer_id)
    ↓
events.json (customer_id)
    ↓
orders.json (customer_id, order_id)
    ↓
products.json (product_id)
```

## Identity Fields

**Primary Identities:**
- `customers.json`: `email` (Email namespace)
- `events.json`: `customer_id` (CRM_ID namespace)
- `orders.json`: `customer_id` (CRM_ID namespace)

**Secondary Identities:**
- `customers.json`: `customer_id`, `phone`
- `events.json`: `session_id`, `ip_address`

## Data Quality Notes

- All dates are in ISO 8601 format
- Currency values use USD
- Phone numbers in E.164 format
- Email addresses are validated format
- Customer IDs follow `CUST###` pattern
- Product IDs follow `PROD###` pattern
- Order IDs follow `ORD_YYYYMMDD_###` pattern

## Next Steps

1. Generate XDM schemas from each file
2. Review AI-generated identity recommendations
3. Upload schemas to AEP Schema Registry
4. Create datasets based on schemas
5. Ingest data using batch ingestion
