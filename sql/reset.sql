-- ぽちっとストア データを空にする（講師用）
-- 実行後に seed.sql を流すと、最初の状態に戻ります:
--   sudo mysql potchi < sql/reset.sql && sudo mysql potchi < sql/seed.sql
-- admin_users は消しません。

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE order_items;
TRUNCATE TABLE orders;
TRUNCATE TABLE products;
SET FOREIGN_KEY_CHECKS = 1;
