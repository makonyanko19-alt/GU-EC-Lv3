"""演習用の設定値。

税率・送料は本来は設定テーブルで管理する（DEC-02、IT-CONFIG）。
ローカルで購入経路を動かす段階では、ここに固定値として置く。
"""
TAX_RATE = 10                 # 消費税率（％）
SHIPPING_FEE = 500            # 送料（税込円）
CART_EXPIRY_DAYS = 30         # ゲストカートの有効期限（更新から30日）
GUEST_CART_COOKIE = "guestCartToken"
NORMAL_DELIVERY_BUSINESS_DAYS = 2   # 通常配送：確定日の翌営業日から2営業日
RESERVATION_MINUTES = 15            # 在庫確保の期限
