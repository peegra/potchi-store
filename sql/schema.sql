-- ぽちっとストア テーブル定義
-- 講師がサーバで1回だけ実行します:  sudo mysql < sql/schema.sql

CREATE DATABASE IF NOT EXISTS potchi
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_general_ci;

USE potchi;

-- 商品
CREATE TABLE IF NOT EXISTS products (
  id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  name          VARCHAR(100)  NOT NULL,
  price         INT UNSIGNED  NOT NULL,
  description   TEXT          NULL,
  stock         INT UNSIGNED  NOT NULL DEFAULT 0,
  is_published  TINYINT(1)    NOT NULL DEFAULT 1,
  created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);

-- 注文（1回の購入につき1行）
CREATE TABLE IF NOT EXISTS orders (
  id             INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  customer_name  VARCHAR(100)  NOT NULL,
  email          VARCHAR(255)  NOT NULL,
  address        VARCHAR(255)  NOT NULL,
  total_price    INT UNSIGNED  NOT NULL,
  status         VARCHAR(20)   NOT NULL DEFAULT 'new',   -- new / shipped
  created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
);

-- 注文の明細（買った商品ごとに1行）
CREATE TABLE IF NOT EXISTS order_items (
  id            INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  order_id      INT UNSIGNED  NOT NULL,
  product_id    INT UNSIGNED  NOT NULL,
  product_name  VARCHAR(100)  NOT NULL,   -- 買った時点の商品名
  unit_price    INT UNSIGNED  NOT NULL,   -- 買った時点の値段
  quantity      INT UNSIGNED  NOT NULL,
  PRIMARY KEY (id),
  KEY idx_order_items_order (order_id),
  CONSTRAINT fk_order_items_order   FOREIGN KEY (order_id)   REFERENCES orders (id),
  CONSTRAINT fk_order_items_product FOREIGN KEY (product_id) REFERENCES products (id)
);

-- 管理画面にログインできる人
CREATE TABLE IF NOT EXISTS admin_users (
  id             INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  login_id       VARCHAR(50)   NOT NULL,
  password_hash  VARCHAR(255)  NOT NULL,
  created_at     DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_admin_users_login (login_id)
);
