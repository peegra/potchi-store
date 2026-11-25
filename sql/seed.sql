-- ぽちっとストア 初期データ
-- 講師がサーバで実行します:  sudo mysql potchi < sql/seed.sql
-- 勉強会のあとに「最初の状態に戻したい」ときは sql/reset.sql → このファイルの順に実行します。

INSERT INTO products (name, price, description, stock, is_published) VALUES
  ('ぽちっとマグカップ',     1800, '朝のコーヒーがちょっとだけおいしくなる、まるいマグカップ。', 20, 1),
  ('エンジニアの靴下',        900, 'かかとに「Hello, World!」と刺繍された靴下。左右で色違い。',     30, 1),
  ('付箋100枚セット',         350, 'TODOを書いて貼って、終わったらはがす。気持ちいい。',           50, 1),
  ('静音キーボード',         6800, '夜中に打ってもバレない。たぶん。',                               5, 1),
  ('ラバーダック',            500, '話しかけるとバグが見つかる（と言われている）アヒル。',          15, 1),
  ('お昼寝クッション',       2400, 'デスクに置いて、5分だけ。',                                       8, 1),
  ('非公開のテスト商品',     9999, 'is_published = 0 なのでストアには表示されません。',              1, 0);

INSERT INTO orders (customer_name, email, address, total_price, status, created_at) VALUES
  ('見本 花子', 'hanako@example.com', '東京都千代田区1-1-1', 2700, 'shipped', NOW() - INTERVAL 2 DAY),
  ('見本 太郎', 'taro@example.com',   '大阪府大阪市北区2-2-2',  500, 'new',     NOW() - INTERVAL 1 DAY);

INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity) VALUES
  (1, 1, 'ぽちっとマグカップ', 1800, 1),
  (1, 2, 'エンジニアの靴下',    900, 1),
  (2, 5, 'ラバーダック',        500, 1);
