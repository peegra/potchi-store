# ぽちっとストア

IT勉強会用の、小さなECサイトです。Python（Flask）と MySQL で動きます。

- **ストア**：商品一覧 → 商品詳細 → カート → 注文フォーム → 注文完了（決済はありません）
- **管理画面**：ログイン、商品の登録・編集・公開/非公開、注文一覧・詳細、発送済みにする

**受講者の方へ**：手順は、配布されたハンズオン手順書（ぽちっとストア ハンズオン）に沿って進めてください。このREADMEの後半は講師向けです。

---

## 動かし方（Windows / PowerShell）

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env      # .env を開いて接続先を書き換える
flask run --debug
```

- ストア：http://127.0.0.1:5000/
- 管理画面：http://127.0.0.1:5000/admin

## ファイルの構成

```
potchi-store/
├── app.py             アプリの入口。URLごとの処理と SQL が書いてある
├── db.py              MySQL につなぐ係
├── templates/
│   ├── shop/          ストア（お客さん向け）の画面
│   └── admin/         管理画面
├── static/style.css   見た目
├── sql/
│   ├── schema.sql     テーブルを作る
│   ├── seed.sql       最初の商品・注文を入れる
│   └── reset.sql      データを空にする（講師用）
├── scripts/
│   ├── add_student.sh 受講者を追加する（講師がサーバで実行）
│   └── create_admin.py 管理画面のユーザーを作る（講師用）
├── requirements.txt   必要なライブラリの一覧表
├── .env.example       接続設定のひな形
└── .gitignore         GitHub に上げないものリスト
```

## テーブル

| テーブル | 中身 |
|---|---|
| `products` | 商品。`is_published = 0` のものはストアに出ない |
| `orders` | 注文（1回の購入につき1行）。`status` は `new` / `shipped` |
| `order_items` | 注文の明細（買った商品ごとに1行）。買った時点の商品名と値段を持つ |
| `admin_users` | 管理画面にログインできる人。パスワードはハッシュ化して保存 |

---

## 講師向け：サーバの準備

全員で1台の MySQL を共有します。Google Cloud の無料枠（e2-micro）で足ります。

### 1. VM を作る（Google Cloud コンソール）

| 項目 | 値 |
|---|---|
| 名前 | `potchi-server`（受講者のプロンプトに出るホスト名になります） |
| リージョン | `us-west1` / `us-central1` / `us-east1` のどれか（無料枠の対象） |
| マシンタイプ | `e2-micro` |
| ブートディスク | Ubuntu 24.04 LTS、標準永続ディスク 30GB |

VM の「外部 IP」を控えておきます（手順書の `SERVER_IP` に入れる値）。OS Login は有効にしないでください（受講者の鍵でログインできなくなるため）。

### 2. ファイアウォールで 3306 を会社からだけ開ける

VPC ネットワーク → ファイアウォール → ルールを作成

| 項目 | 値 |
|---|---|
| ターゲット | 指定されたターゲットタグ `mysql-server`（VM にも同じタグを付ける） |
| ソース IPv4 範囲 | 会社のグローバル IP（例 `203.0.113.10/32`） |
| プロトコルとポート | TCP `3306` |

SSH（22番）は Google Cloud の既定ルールで開いています。鍵でしかログインできない設定なので、そのままで大丈夫です。

### 3. MySQL を入れる（VM に SSH して）

```bash
sudo apt update && sudo apt install -y mysql-server git

# メモリ 1GB のための swap（1GB）
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 外からの接続を受け付け、メモリ使用量を抑える
sudo tee /etc/mysql/mysql.conf.d/potchi.cnf <<'EOF'
[mysqld]
bind-address            = 0.0.0.0
performance_schema      = OFF
innodb_buffer_pool_size = 128M
max_connections         = 60
EOF
sudo systemctl restart mysql
```

### 4. テーブルと初期データを入れる

```bash
git clone https://github.com/peegra/potchi-store.git
cd potchi-store
sudo mysql < sql/schema.sql
sudo mysql potchi < sql/seed.sql
```

講師用の MySQL ユーザー（全部の権限あり）も作っておきます。

```bash
sudo mysql -e "CREATE USER 'teacher'@'%' IDENTIFIED BY '長いパスワード'; GRANT ALL ON potchi.* TO 'teacher'@'%';"
```

### 5. 管理画面のログインユーザーを作る

講師の PC で、`.env` を `teacher` ユーザーの設定にしてから実行します。

```powershell
python scripts/create_admin.py admin
```

### 6. 受講者を追加する（人数分）

```bash
sudo bash scripts/add_student.sh user01
sudo bash scripts/add_student.sh user02
```

それぞれ、Linux ユーザー・ssh 鍵・MySQL ユーザー（`SELECT / INSERT / UPDATE` のみ）を作ります。
鍵とパスワードは `/root/student-keys/<ID>/` に置かれるので、講師の PC に持ってきて1人ずつ渡します。

```bash
# サーバ上で、取り出しやすい場所にまとめる
sudo tar czf ~/student-keys.tgz -C /root student-keys && sudo chown $USER ~/student-keys.tgz
```

```powershell
# 講師の PC で受け取る
scp -i <講師の鍵> <講師のユーザー>@<サーバIP>:student-keys.tgz .
```

受け取ったら、サーバ側の `~/student-keys.tgz` は消しておきます。

### 7. 勉強会が終わったら

```bash
sudo mysql potchi < sql/reset.sql && sudo mysql potchi < sql/seed.sql
```

データが最初の状態に戻ります（管理画面のユーザーは残ります）。

## 権限の設計メモ

- 受講者の MySQL ユーザーは `DELETE` / `DROP` ができません。全員で1つの DB を共有しても、誰かが全部消してしまう事故が起きないようにするためです。
- そのため、管理画面には「削除」がなく、代わりに「非公開にする」があります。
- 注文の確定（注文・明細・在庫の更新）は1つのトランザクションで行います。在庫が足りなければ、全部取り消します。
