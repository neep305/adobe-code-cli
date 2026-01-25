erDiagram
    CUSTOMERS {
        string customer_id PK
        string email
        string first_name
        string last_name
        string phone
        string date_of_birth
        string gender
        object address
        string account_created
        string account_status
    }
    EVENTS {
        string event_id PK
        string event_type
        string timestamp
        string customer_id FK
        string session_id FK
        string user_agent
        string ip_address
        object page
        object device
        object product
    }
    ORDERS {
        string order_id PK
        string order_number
        string customer_id FK
        string order_date
        string order_status
        string payment_status
        string fulfillment_status
        string channel
        string currency
        number subtotal
    }
    PRODUCTS {
        string product_id PK
        string sku
        string name
        string description
        string category
        string brand
        number price
        string currency
        number cost
        number margin
    }
    ORDERS }o--|| CUSTOMERS : "belongs_to_customers"
    EVENTS }o--|| CUSTOMERS : "belongs_to_customers"
    ORDERS }o--o{ PRODUCTS : "relates_to_products"