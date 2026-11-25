"""MySQL につなぐ係

.env に書いた接続情報を読み込んで、MySQL への接続を作ります。
SQL は app.py の中にそのまま書いてあります（A5M2 で打つ SQL と同じ形です）。
"""

import os

import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    """MySQL への接続を1本作って返す"""
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ.get("DB_NAME", "potchi"),
        charset="utf8mb4",
        # 結果を {"id": 1, "name": "..."} のような辞書で受け取る
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5,
    )


def query_all(sql, params=None):
    """SELECT して、全部の行をリストで返す"""
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def query_one(sql, params=None):
    """SELECT して、1行だけ返す（なければ None）"""
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql, params=None):
    """INSERT / UPDATE を1つ実行して確定する。INSERT なら新しい id を返す"""
    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            new_id = cur.lastrowid
        conn.commit()
        return new_id
