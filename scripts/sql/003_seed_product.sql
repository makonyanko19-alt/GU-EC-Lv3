USE gu_ec_mako;

-- まとめて登録し、結果を確認してから確定する
START TRANSACTION;

-- 確認時に同じ商品を指定できるよう、固定のIDを使う
SET @product_id = '11111111-1111-4111-8111-111111111111';
SET @sku_s = '22222222-2222-4222-8222-222222222221';
SET @sku_m = '22222222-2222-4222-8222-222222222222';


-- 1. 商品を1件登録する
INSERT INTO products (
    product_id,
    product_code,
    product_name,
    description,
    is_published
)
VALUES (
    @product_id,
    'TEST-PANTS-001',
    '動作確認用パンツ',
    '商品詳細APIと裾上げ指定の動作確認に使う架空の商品です。',
    TRUE
);


-- 2. ブラックのSサイズとMサイズを登録する
INSERT INTO skus (
    sku_id,
    product_id,
    sku_code,
    color_code,
    color_name,
    size_code,
    selling_price,
    is_active
)
VALUES
(
    @sku_s, @product_id,
    'TEST-PANTS-001-BLACK-S',
    'BLACK', 'ブラック', 'S', 1000, TRUE
),
(
    @sku_m, @product_id,
    'TEST-PANTS-001-BLACK-M',
    'BLACK', 'ブラック', 'M', 1000, TRUE
);


-- 3. サイズごとの在庫を登録する
INSERT INTO inventories (
    sku_id,
    on_hand_quantity,
    reserved_quantity
)
VALUES
    (@sku_s, 10, 0),
    (@sku_m, 20, 0);


-- 4. サイズごとの裾上げ条件を登録する
INSERT INTO product_size_alteration_rules (
    product_id,
    size_code,
    is_alteration_available,
    min_inseam_cm,
    max_inseam_cm,
    inseam_step_cm
)
VALUES
    (@product_id, 'S', TRUE, 65, 80, 1),
    (@product_id, 'M', TRUE, 70, 85, 1);


-- 5. 仕上げ方法を登録する
INSERT INTO alteration_methods (
    method_code,
    method_name,
    alteration_fee,
    additional_business_days,
    is_active
)
VALUES
    ('MACHINE', 'ミシン仕上げ', 300, 3, TRUE),
    ('CHAIN', 'チェーン仕上げ', 560, 3, TRUE);

-- ここではまだCOMMITしない。
-- エラーがないことと登録内容を確認してから確定する。