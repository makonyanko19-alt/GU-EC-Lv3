USE gu_ec_mako;
-- 1. 注文（金額・配送先は確定時の値を保存する）
CREATE TABLE orders (
order_id CHAR(36) NOT NULL DEFAULT (UUID()),
order_number VARCHAR(30) NOT NULL,
source_cart_id CHAR(36) NOT NULL,
guest_access_token_hash CHAR(64) NULL,
status VARCHAR(20) NOT NULL,
subtotal DECIMAL(12, 0) NOT NULL,
alteration_fee_total DECIMAL(12, 0) NOT NULL,
shipping_fee DECIMAL(12, 0) NOT NULL,
tax_rate SMALLINT NOT NULL,
tax_amount DECIMAL(12, 0) NOT NULL,
total_amount DECIMAL(12, 0) NOT NULL,
recipient_name VARCHAR(100) NOT NULL,
contact_email VARCHAR(254) NOT NULL,
postal_code VARCHAR(8) NOT NULL,
prefecture VARCHAR(20) NOT NULL,
city VARCHAR(100) NOT NULL,
address_line1 VARCHAR(200) NOT NULL,
address_line2 VARCHAR(200) NULL,
phone_number VARCHAR(20) NOT NULL,
delivery_method VARCHAR(20) NOT NULL,
estimated_delivery_date DATE NOT NULL,
confirmed_at DATETIME NULL,
access_expires_at DATETIME NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
ON UPDATE CURRENT_TIMESTAMP,
PRIMARY KEY (order_id),
CONSTRAINT uq_orders_number UNIQUE (order_number),
CONSTRAINT uq_orders_source_cart UNIQUE (source_cart_id),
CONSTRAINT fk_orders_cart FOREIGN KEY (source_cart_id) REFERENCES carts (cart_id),
CONSTRAINT chk_orders_status CHECK (
status IN ('DRAFT', 'PAYMENT_PENDING', 'CONFIRMED', 'PAYMENT_FAILED', 'CANCELLED')
),
CONSTRAINT chk_orders_amounts CHECK (
subtotal >= 0 AND alteration_fee_total >= 0 AND shipping_fee >= 0
AND tax_amount >= 0 AND total_amount >= 0
)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;
-- 2. 注文明細（商品名・価格・裾上げを注文時の値で保存する）
CREATE TABLE order_items (
order_item_id CHAR(36) NOT NULL DEFAULT (UUID()),
order_id CHAR(36) NOT NULL,
product_id CHAR(36) NOT NULL,
sku_id CHAR(36) NOT NULL,
product_name VARCHAR(255) NOT NULL,
sku_code VARCHAR(50) NOT NULL,
color_name VARCHAR(100) NOT NULL,
size_code VARCHAR(20) NOT NULL,
unit_price DECIMAL(12, 0) NOT NULL,
quantity INT NOT NULL,
alteration_status VARCHAR(10) NOT NULL,
alteration_method_id CHAR(36) NULL,
alteration_method_name VARCHAR(100) NULL,
alteration_fee DECIMAL(12, 0) NOT NULL DEFAULT 0,
inseam_cm SMALLINT NULL,
line_total DECIMAL(12, 0) NOT NULL,
PRIMARY KEY (order_item_id),
CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders (order_id),
CONSTRAINT chk_order_items_quantity CHECK (quantity BETWEEN 1 AND 10)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;
-- 3. 在庫確保（決済が終わるまで在庫を押さえる）
CREATE TABLE stock_reservations (
reservation_id CHAR(36) NOT NULL DEFAULT (UUID()),
order_item_id CHAR(36) NOT NULL,
sku_id CHAR(36) NOT NULL,
quantity INT NOT NULL,
status VARCHAR(20) NOT NULL,
expires_at DATETIME NOT NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
ON UPDATE CURRENT_TIMESTAMP,
PRIMARY KEY (reservation_id),
CONSTRAINT fk_reservations_item
FOREIGN KEY (order_item_id) REFERENCES order_items (order_item_id),
CONSTRAINT chk_reservations_status
CHECK (status IN ('RESERVED', 'CONSUMED', 'RELEASED')),
CONSTRAINT chk_reservations_quantity CHECK (quantity >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;
-- 4. 決済（試行ごとに1行。再試行はattempt_noを増やして新しい行にする）
CREATE TABLE payments (
payment_id CHAR(36) NOT NULL DEFAULT (UUID()),
order_id CHAR(36) NOT NULL,
attempt_no INT NOT NULL,
provider VARCHAR(20) NOT NULL,
amount DECIMAL(12, 0) NOT NULL,
status VARCHAR(20) NOT NULL,
provider_transaction_id VARCHAR(100) NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
ON UPDATE CURRENT_TIMESTAMP,
PRIMARY KEY (payment_id),
CONSTRAINT uq_payments_attempt UNIQUE (order_id, attempt_no),
CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders (order_id),
CONSTRAINT chk_payments_status CHECK (
status IN ('REQUESTED', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'UNKNOWN')
)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;
