USE gu_ec_mako;

-- 1. 商品
CREATE TABLE products (
    product_id CHAR(36) NOT NULL DEFAULT (UUID()),
    product_code VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (product_id),
    CONSTRAINT uq_products_code UNIQUE (product_code),
    CONSTRAINT chk_products_name
        CHECK (CHAR_LENGTH(TRIM(product_name)) > 0),
    CONSTRAINT chk_products_published
        CHECK (is_published IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;


-- 2. 色・サイズ別の商品（SKU）
CREATE TABLE skus (
    sku_id CHAR(36) NOT NULL DEFAULT (UUID()),
    product_id CHAR(36) NOT NULL,
    sku_code VARCHAR(50) NOT NULL,
    color_code VARCHAR(30) NOT NULL,
    color_name VARCHAR(100) NOT NULL,
    size_code VARCHAR(20) NOT NULL,
    selling_price DECIMAL(12, 0) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (sku_id),
    CONSTRAINT uq_skus_code UNIQUE (sku_code),
    CONSTRAINT uq_skus_product_color_size
        UNIQUE (product_id, color_code, size_code),
    CONSTRAINT fk_skus_product
        FOREIGN KEY (product_id) REFERENCES products (product_id),
    CONSTRAINT chk_skus_price
        CHECK (selling_price >= 0),
    CONSTRAINT chk_skus_active
        CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;


-- 3. SKUごとの在庫
CREATE TABLE inventories (
    inventory_id CHAR(36) NOT NULL DEFAULT (UUID()),
    sku_id CHAR(36) NOT NULL,
    on_hand_quantity INT NOT NULL DEFAULT 0,
    reserved_quantity INT NOT NULL DEFAULT 0,
    version INT NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (inventory_id),
    CONSTRAINT uq_inventories_sku UNIQUE (sku_id),
    CONSTRAINT fk_inventories_sku
        FOREIGN KEY (sku_id) REFERENCES skus (sku_id),
    CONSTRAINT chk_inventories_on_hand
        CHECK (on_hand_quantity >= 0),
    CONSTRAINT chk_inventories_reserved
        CHECK (
            reserved_quantity >= 0
            AND reserved_quantity <= on_hand_quantity
        ),
    CONSTRAINT chk_inventories_version
        CHECK (version >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;