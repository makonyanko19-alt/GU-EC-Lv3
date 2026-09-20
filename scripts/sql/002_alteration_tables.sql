USE gu_ec_mako;

-- 1. 商品・サイズ別の裾上げルール
CREATE TABLE product_size_alteration_rules (
    alteration_rule_id CHAR(36) NOT NULL DEFAULT (UUID()),
    product_id CHAR(36) NOT NULL,
    size_code VARCHAR(20) NOT NULL,
    is_alteration_available BOOLEAN NOT NULL DEFAULT FALSE,
    min_inseam_cm SMALLINT NULL,
    max_inseam_cm SMALLINT NULL,
    inseam_step_cm SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (alteration_rule_id),

    CONSTRAINT uq_alteration_rules_product_size
        UNIQUE (product_id, size_code),

    CONSTRAINT fk_alteration_rules_product
        FOREIGN KEY (product_id) REFERENCES products (product_id),

    CONSTRAINT chk_alteration_rules_available
        CHECK (is_alteration_available IN (0, 1)),

    CONSTRAINT chk_alteration_rules_min
        CHECK (min_inseam_cm >= 0),

    CONSTRAINT chk_alteration_rules_max
        CHECK (max_inseam_cm >= 0),

    CONSTRAINT chk_alteration_rules_range
        CHECK (max_inseam_cm >= min_inseam_cm),

    CONSTRAINT chk_alteration_rules_required
        CHECK (
            is_alteration_available = FALSE
            OR (
                min_inseam_cm IS NOT NULL
                AND max_inseam_cm IS NOT NULL
            )
        ),

    CONSTRAINT chk_alteration_rules_step
        CHECK (inseam_step_cm >= 1)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;


-- 2. 裾上げの仕上げ方法
CREATE TABLE alteration_methods (
    alteration_method_id CHAR(36) NOT NULL DEFAULT (UUID()),
    method_code VARCHAR(30) NOT NULL,
    method_name VARCHAR(100) NOT NULL,
    alteration_fee DECIMAL(12, 0) NOT NULL DEFAULT 0,
    additional_business_days SMALLINT NOT NULL DEFAULT 3,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (alteration_method_id),

    CONSTRAINT uq_alteration_methods_code
        UNIQUE (method_code),

    CONSTRAINT chk_alteration_methods_name
        CHECK (CHAR_LENGTH(TRIM(method_name)) > 0),

    CONSTRAINT chk_alteration_methods_fee
        CHECK (alteration_fee >= 0),

    CONSTRAINT chk_alteration_methods_days
        CHECK (additional_business_days >= 0),

    CONSTRAINT chk_alteration_methods_active
        CHECK (is_active IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;