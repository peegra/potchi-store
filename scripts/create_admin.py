"""管理画面のログインユーザーを作る（講師用）

使い方（仮想環境を有効にしてから、potchi-store フォルダで）:
    python scripts/create_admin.py admin

パスワードを2回聞かれます。同じ login_id がすでにあれば、パスワードを上書きします。
.env に書かれた接続先の DB に登録されます。
"""

import getpass
import os
import sys

from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import get_connection  # noqa: E402


def main():
    if len(sys.argv) != 2:
        print("使い方: python scripts/create_admin.py <login_id>")
        sys.exit(1)
    login_id = sys.argv[1]

    password = getpass.getpass("パスワード: ")
    if len(password) < 8:
        print("8文字以上にしてください")
        sys.exit(1)
    if password != getpass.getpass("もう一度: "):
        print("一致しませんでした")
        sys.exit(1)

    conn = get_connection()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO admin_users (login_id, password_hash)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE password_hash = VALUES(password_hash)
                """,
                (login_id, generate_password_hash(password)),
            )
        conn.commit()
    print(f"管理ユーザー「{login_id}」を登録しました")


if __name__ == "__main__":
    main()
