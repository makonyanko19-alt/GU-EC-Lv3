USE gu_ec_mako;
-- 1. カート（ゲストはトークンのハッシュで識別する）
CREATE TABLE carts (
cart_id CHAR(36) NOT NULL DEFAULT (UUID()),
user_id CHAR(36) NULL,
guest_token_hash CHAR(64) NULL,
status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
expires_at DATETIME NOT NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
ON UPDATE CURRENT_TIMESTAMP,
PRIMARY KEY (cart_id),
CONSTRAINT uq_carts_guest_token UNIQUE (guest_token_hash),
CONSTRAINT chk_carts_status
CHECK (status IN ('ACTIVE', 'CONVERTED', 'ABANDONED', 'EXPIRED')),
CONSTRAINT chk_carts_owner
CHECK (user_id IS NOT NULL OR guest_token_hash IS NOT NULL)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;
-- 2. カート明細（同じSKU・同じ裾上げ指定は1明細にまとめる）
CREATE TABLE cart_items (
cart_item_id CHAR(36) NOT NULL DEFAULT (UUID()),
cart_id CHAR(36) NOT NULL,
sku_id CHAR(36) NOT NULL,
quantity INT NOT NULL,
alteration_status VARCHAR(10) NOT NULL,
alteration_method_id CHAR(36) NULL,
inseam_cm SMALLINT NULL,
cart_line_key VARCHAR(120) NOT NULL,
created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
ON UPDATE CURRENT_TIMESTAMP,
PRIMARY KEY (cart_item_id),
CONSTRAINT uq_cart_items_line UNIQUE (cart_id, cart_line_key),
CONSTRAINT fk_cart_items_cart
FOREIGN KEY (cart_id) REFERENCES carts (cart_id),
CONSTRAINT fk_cart_items_sku
FOREIGN KEY (sku_id) REFERENCES skus (sku_id),
CONSTRAINT fk_cart_items_method
FOREIGN KEY (alteration_method_id)
REFERENCES alteration_methods (alteration_method_id),
CONSTRAINT chk_cart_items_quantity
CHECK (quantity BETWEEN 1 AND 10),
CONSTRAINT chk_cart_items_alteration
CHECK (
(alteration_status = 'NONE'
AND alteration_method_id IS NULL AND inseam_cm IS NULL)
OR (alteration_status = 'SELECTED'
AND alteration_method_id IS NOT NULL AND inseam_cm IS NOT NULL)
)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;
