"""ぽちっとストア

起動:  flask run --debug
  ストア    http://127.0.0.1:5000/
  管理画面  http://127.0.0.1:5000/admin

このファイルの読み方
  - @app.get("/...") / @app.post("/...") が「このURLに来たら、この関数を動かす」という対応表です。
  - 関数の中では SQL を発行して、結果を templates/ の HTML に渡しています。
  - カートの中身は DB ではなく、ブラウザごとの session（Cookie）に入れています。
"""

import os
from functools import wraps

import pymysql
from dotenv import load_dotenv
from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from db import execute, get_connection, query_all, query_one

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or "dev-only-change-me"


@app.template_filter("yen")
def yen(value):
    """1800 → 1,800円"""
    return f"{int(value):,}円"


@app.context_processor
def inject_cart_count():
    """全部の画面で、ヘッダーにカートの個数を出せるようにする"""
    return {"cart_count": sum(session.get("cart", {}).values())}


@app.errorhandler(pymysql.err.OperationalError)
def db_error(e):
    """DB につながらないときに、わかりやすい画面を出す"""
    return render_template("db_error.html", error=e), 500


# =========================================================
#  ストア（お客さん向け）
# =========================================================

@app.get("/")
def index():
    products = query_all(
        """
        SELECT id, name, price, description, stock
        FROM products
        WHERE is_published = 1
        ORDER BY id DESC
        """
    )
    return render_template("shop/index.html", products=products)


@app.get("/products/<int:product_id>")
def product_detail(product_id):
    product = query_one("SELECT * FROM products WHERE id = %s", (product_id,))
    if product is None:
        abort(404)
    # 非公開の商品は、管理画面にログインしている人にだけ見せる（プレビュー）
    if not product["is_published"] and not session.get("admin_id"):
        abort(404)
    return render_template("shop/product.html", product=product)


@app.post("/cart/add")
def cart_add():
    product_id = request.form.get("product_id", type=int)
    quantity = max(1, request.form.get("quantity", 1, type=int))
    product = query_one(
        "SELECT id, name FROM products WHERE id = %s AND is_published = 1", (product_id,)
    )
    if product is None:
        abort(404)

    cart = session.get("cart", {})
    key = str(product_id)
    cart[key] = cart.get(key, 0) + quantity
    session["cart"] = cart
    flash(f"「{product['name']}」をカートに入れました")
    return redirect(url_for("cart"))


def load_cart_items():
    """session のカート {商品id: 個数} を、DB の商品情報と合わせた一覧にする"""
    cart = session.get("cart", {})
    if not cart:
        return [], 0

    ids = [int(k) for k in cart]
    placeholders = ", ".join(["%s"] * len(ids))
    rows = query_all(
        f"SELECT id, name, price, stock FROM products WHERE is_published = 1 AND id IN ({placeholders})",
        ids,
    )
    items = []
    for row in rows:
        qty = cart[str(row["id"])]
        items.append({**row, "quantity": qty, "subtotal": row["price"] * qty})
    total = sum(item["subtotal"] for item in items)
    return items, total


@app.get("/cart")
def cart():
    items, total = load_cart_items()
    return render_template("shop/cart.html", items=items, total=total)


@app.post("/cart/update")
def cart_update():
    product_id = request.form.get("product_id", type=int)
    quantity = request.form.get("quantity", 0, type=int)
    cart = session.get("cart", {})
    if quantity <= 0:
        cart.pop(str(product_id), None)
    else:
        cart[str(product_id)] = quantity
    session["cart"] = cart
    return redirect(url_for("cart"))


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    items, total = load_cart_items()
    if not items:
        return redirect(url_for("cart"))

    if request.method == "GET":
        return render_template("shop/checkout.html", items=items, total=total, form={})

    form = {
        "customer_name": request.form.get("customer_name", "").strip(),
        "email": request.form.get("email", "").strip(),
        "address": request.form.get("address", "").strip(),
    }
    if not all(form.values()):
        flash("お名前・メールアドレス・住所をすべて入力してください", "error")
        return render_template("shop/checkout.html", items=items, total=total, form=form)

    # ---- ここから「注文を確定する」処理 ----
    # 注文・明細・在庫は、全部まとめて成功するか、全部なかったことにするかのどちらか。
    # これを「トランザクション」と呼びます。
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. 注文を1行作る
            cur.execute(
                """
                INSERT INTO orders (customer_name, email, address, total_price)
                VALUES (%s, %s, %s, %s)
                """,
                (form["customer_name"], form["email"], form["address"], total),
            )
            order_id = cur.lastrowid

            for item in items:
                # 2. 在庫を減らす（在庫が足りなければ 0 行しか更新されない）
                cur.execute(
                    "UPDATE products SET stock = stock - %s WHERE id = %s AND stock >= %s",
                    (item["quantity"], item["id"], item["quantity"]),
                )
                if cur.rowcount == 0:
                    raise OutOfStock(item["name"])

                # 3. 明細を1行ずつ作る
                cur.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, product_name, unit_price, quantity)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (order_id, item["id"], item["name"], item["price"], item["quantity"]),
                )
        conn.commit()  # ここで初めて DB に確定する
    except OutOfStock as e:
        conn.rollback()  # 途中までの INSERT も含めて、全部取り消す
        flash(f"「{e}」の在庫が足りませんでした。個数を減らしてください", "error")
        return redirect(url_for("cart"))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    session.pop("cart", None)
    return redirect(url_for("complete", order_id=order_id))


class OutOfStock(Exception):
    pass


@app.get("/complete/<int:order_id>")
def complete(order_id):
    order = query_one("SELECT id, customer_name, total_price FROM orders WHERE id = %s", (order_id,))
    if order is None:
        abort(404)
    return render_template("shop/complete.html", order=order)


# =========================================================
#  管理画面
# =========================================================

def login_required(view):
    """管理画面のページに付ける目印。ログインしていなければログイン画面へ"""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapper


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        login_id = request.form.get("login_id", "")
        password = request.form.get("password", "")
        user = query_one("SELECT * FROM admin_users WHERE login_id = %s", (login_id,))
        if user and check_password_hash(user["password_hash"], password):
            session["admin_id"] = user["id"]
            session["admin_login_id"] = user["login_id"]
            next_url = request.args.get("next", "")
            if not next_url.startswith("/admin"):
                next_url = url_for("admin_products")
            return redirect(next_url)
        flash("ログインIDかパスワードが違います", "error")
    return render_template("admin/login.html")


@app.get("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_login_id", None)
    return redirect(url_for("admin_login"))


@app.get("/admin")
@login_required
def admin_home():
    return redirect(url_for("admin_products"))


@app.get("/admin/products")
@login_required
def admin_products():
    products = query_all("SELECT * FROM products ORDER BY id DESC")
    return render_template("admin/products.html", products=products)


def read_product_form():
    """商品フォームの入力を取り出して、まちがいがあればエラー文を返す"""
    form = {
        "name": request.form.get("name", "").strip(),
        "price": request.form.get("price", "").strip(),
        "description": request.form.get("description", "").strip(),
        "stock": request.form.get("stock", "").strip(),
        "is_published": 1 if request.form.get("is_published") else 0,
    }
    errors = []
    if not form["name"]:
        errors.append("商品名を入力してください")
    if not form["price"].isdigit():
        errors.append("価格は0以上の整数で入力してください")
    if not form["stock"].isdigit():
        errors.append("在庫は0以上の整数で入力してください")
    return form, errors


@app.route("/admin/products/new", methods=["GET", "POST"])
@login_required
def admin_product_new():
    if request.method == "GET":
        return render_template(
            "admin/product_form.html",
            form={"name": "", "price": "", "description": "", "stock": "10", "is_published": 1},
            product=None,
        )

    form, errors = read_product_form()
    if errors:
        for message in errors:
            flash(message, "error")
        return render_template("admin/product_form.html", form=form, product=None)

    new_id = execute(
        """
        INSERT INTO products (name, price, description, stock, is_published)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (form["name"], int(form["price"]), form["description"], int(form["stock"]), form["is_published"]),
    )
    flash(f"「{form['name']}」を登録しました（id = {new_id}）")
    return redirect(url_for("admin_products"))


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def admin_product_edit(product_id):
    product = query_one("SELECT * FROM products WHERE id = %s", (product_id,))
    if product is None:
        abort(404)

    if request.method == "GET":
        return render_template("admin/product_form.html", form=product, product=product)

    form, errors = read_product_form()
    if errors:
        for message in errors:
            flash(message, "error")
        return render_template("admin/product_form.html", form=form, product=product)

    execute(
        """
        UPDATE products
        SET name = %s, price = %s, description = %s, stock = %s, is_published = %s
        WHERE id = %s
        """,
        (form["name"], int(form["price"]), form["description"], int(form["stock"]),
         form["is_published"], product_id),
    )
    flash(f"「{form['name']}」を更新しました")
    return redirect(url_for("admin_products"))


@app.post("/admin/products/<int:product_id>/toggle")
@login_required
def admin_product_toggle(product_id):
    # 削除の代わりに「非公開」にする（受講者のDBユーザーには DELETE の権限がないため）
    execute("UPDATE products SET is_published = 1 - is_published WHERE id = %s", (product_id,))
    return redirect(url_for("admin_products"))


@app.get("/admin/orders")
@login_required
def admin_orders():
    orders = query_all(
        """
        SELECT o.id, o.customer_name, o.total_price, o.status, o.created_at,
               COUNT(oi.id) AS item_count
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        GROUP BY o.id, o.customer_name, o.total_price, o.status, o.created_at
        ORDER BY o.id DESC
        """
    )
    return render_template("admin/orders.html", orders=orders)


@app.get("/admin/orders/<int:order_id>")
@login_required
def admin_order_detail(order_id):
    order = query_one("SELECT * FROM orders WHERE id = %s", (order_id,))
    if order is None:
        abort(404)
    items = query_all(
        "SELECT * FROM order_items WHERE order_id = %s ORDER BY id", (order_id,)
    )
    return render_template("admin/order_detail.html", order=order, items=items)


@app.post("/admin/orders/<int:order_id>/ship")
@login_required
def admin_order_ship(order_id):
    execute("UPDATE orders SET status = 'shipped' WHERE id = %s", (order_id,))
    flash(f"注文 #{order_id} を発送済みにしました")
    return redirect(url_for("admin_order_detail", order_id=order_id))


if __name__ == "__main__":
    app.run(debug=True)
