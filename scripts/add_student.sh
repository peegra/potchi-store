#!/usr/bin/env bash
# 受講者を1人追加する（講師がサーバ上で実行）
#
#   使い方:  sudo bash scripts/add_student.sh user01
#
# やること
#   1. Linuxユーザーを作る（パスワードなし、鍵でのみログイン）
#   2. ssh用の鍵を作り、秘密鍵を /root/student-keys/<ID>/potchi_key に置く
#   3. MySQLユーザーを作る（potchi DB に SELECT / INSERT / UPDATE だけ許可）
#   4. 配布用の情報を画面に表示する
#
# 秘密鍵は scp などで講師のPCに持ってきて、受講者ごとに個別に渡してください。

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "sudo を付けて実行してください" >&2; exit 1
fi
UID_NAME="${1:-}"
if [[ ! "$UID_NAME" =~ ^[a-z][a-z0-9_]{1,31}$ ]]; then
  echo "使い方: sudo bash $0 user01   （英小文字で始まる英数字）" >&2; exit 1
fi

KEY_DIR="/root/student-keys/${UID_NAME}"

# 1. Linuxユーザー
if id "$UID_NAME" &>/dev/null; then
  echo "Linuxユーザー ${UID_NAME} はすでにあります。鍵とMySQLの設定だけやり直します。"
else
  useradd -m -s /bin/bash "$UID_NAME"
fi

# 2. ssh鍵（A5M2でも読める RSA / PEM 形式）
mkdir -p "$KEY_DIR"
chmod 700 "$KEY_DIR"
rm -f "${KEY_DIR}/potchi_key" "${KEY_DIR}/potchi_key.pub"
ssh-keygen -q -t rsa -b 4096 -m PEM -N "" -C "${UID_NAME}@potchi" -f "${KEY_DIR}/potchi_key"

HOME_DIR="$(getent passwd "$UID_NAME" | cut -d: -f6)"
install -d -m 700 -o "$UID_NAME" -g "$UID_NAME" "${HOME_DIR}/.ssh"
install -m 600 -o "$UID_NAME" -g "$UID_NAME" "${KEY_DIR}/potchi_key.pub" "${HOME_DIR}/.ssh/authorized_keys"

# 3. MySQLユーザー
DB_PASS="$(openssl rand -hex 8)"
mysql <<SQL
CREATE USER IF NOT EXISTS '${UID_NAME}'@'%' IDENTIFIED BY '${DB_PASS}';
ALTER USER '${UID_NAME}'@'%' IDENTIFIED BY '${DB_PASS}';
GRANT SELECT, INSERT, UPDATE ON potchi.* TO '${UID_NAME}'@'%';
FLUSH PRIVILEGES;
SQL

echo "${DB_PASS}" > "${KEY_DIR}/mysql_password.txt"
chmod 600 "${KEY_DIR}/mysql_password.txt"

# 4. 配布用の情報
cat <<INFO

=== ${UID_NAME} の配布情報 ==========================
受講者ID       : ${UID_NAME}
ssh 秘密鍵     : ${KEY_DIR}/potchi_key   （これを本人に渡す）
MySQL パスワード: ${DB_PASS}
                  （${KEY_DIR}/mysql_password.txt にも保存）
=====================================================
INFO
