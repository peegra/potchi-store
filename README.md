# ぽちっとストア

IT勉強会用の、小さなECサイトです。Python（Flask）と MySQL で動きます。

- **ストア**：商品一覧 → 商品詳細 → カート → 注文フォーム → 注文完了（決済はありません）
- **管理画面**：ログイン、商品の登録・編集・公開/非公開、注文一覧・詳細、発送済みにする

**受講者の方へ**：手順は、ハンズオン手順書 https://peegra.github.io/potchi-store/ に沿って進めてください。このREADMEの後半は講師向けです。

---

## 動かし方（Windows / PowerShell）

まず、DB につなぐための SSH トンネルを別のターミナルで開いておきます（開いたままにする）。

```powershell
ssh -i ~\.ssh\potchi_key -N -L 13306:127.0.0.1:3306 student@<サーバIP>
```

次に、もう1つのターミナルでアプリを起動します。

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
│   ├── add_student.sh 受講者IDを作る（講師がサーバで実行）
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

**接続の考え方**：受講者はリモートから参加するので、MySQL の 3306 番はインターネットに開けません。
外に開けるのは SSH（22番、鍵でのみログイン可）だけで、MySQL へは必ず SSH トンネル経由でつなぎます。

```
受講者のPC  ──ssh(22)──▶  potchi-server  ──▶  MySQL (127.0.0.1:3306)
  アプリ / A5M2 は「自分のPCの 13306 番」につなぐと、トンネルを通ってサーバの MySQL に届く
```

### 1. VM を作る

Google Cloud CLI（gcloud）で作る場合の例です。コンソールから作っても同じです。

```bash
P=potchi-store-lesson
gcloud projects create $P
gcloud billing projects link $P --billing-account=<請求先アカウントID>
gcloud services enable compute.googleapis.com --project $P
gcloud compute addresses create potchi-ip --region us-west1 --project $P   # 固定IP
gcloud compute instances create potchi-server --project $P --zone us-west1-b \
  --machine-type e2-micro --image-family ubuntu-2404-lts-amd64 --image-project ubuntu-os-cloud \
  --boot-disk-size 30GB --boot-disk-type pd-standard \
  --address potchi-ip --metadata enable-oslogin=FALSE
gcloud compute firewall-rules delete default-allow-rdp --project $P   # 使わないので閉じる
```

| 項目 | 値 |
|---|---|
| 名前 | `potchi-server`（受講者のプロンプトに出るホスト名になります） |
| リージョン | `us-west1` / `us-central1` / `us-east1` のどれか（無料枠の対象） |
| マシンタイプ | `e2-micro` |
| ブートディスク | Ubuntu 24.04 LTS、標準永続ディスク 30GB |

- 外部 IP は手順書の `SERVER_IP` に入れる値です。固定IPにしておくと、VM を再起動しても変わりません。
- OS Login は有効にしないでください（受講者の鍵でログインできなくなるため）。
- 無料枠の e2-micro は、請求先アカウントごとに1台分です。ほかのプロジェクトですでに e2-micro を動かしていると、こちらは課金されます。外部 IP にも少額の料金がかかる場合があります。

### 2. ファイアウォール

既定のルールで SSH（22番）だけが開いています。**3306 番を開けるルールは作りません。**

### 3. MySQL を入れる（講師が VM に SSH して）

```bash
gcloud compute ssh potchi-server --project potchi-store-lesson --zone us-west1-b
```

```bash
sudo apt update && sudo apt install -y mysql-server git

# メモリ 1GB のための swap（1GB）
sudo fallocate -l 1G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# サーバの中からの接続だけ受け付け、メモリ使用量を抑える
sudo tee /etc/mysql/mysql.conf.d/potchi.cnf <<'EOF'
[mysqld]
bind-address            = 127.0.0.1
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

### 6. 受講者用のIDを作る（全員共通・1回だけ）

受講者は全員、同じID `student` で Linux と MySQL にログインします。毎回人数分を作る手間をなくすためです。

```bash
sudo bash scripts/add_student.sh student
```

Linux ユーザー・ssh 鍵・MySQL ユーザー（`SELECT / INSERT / UPDATE` のみ）を作ります。
鍵とパスワードは `/root/student-keys/student/` に置かれます。講師の PC に持ってきて、社内の連絡手段で全員に配ります（GitHub には上げないこと）。

```bash
# 講師の PC で受け取る
gcloud compute ssh potchi-server --zone us-west1-b --command 'sudo cat /root/student-keys/student/potchi_key' > potchi_key
gcloud compute ssh potchi-server --zone us-west1-b --command 'sudo cat /root/student-keys/student/mysql_password.txt'
```

- 同じIDで何人同時にログインしても問題ありません。Linux のホームフォルダは共有になるので、手順書では各自の名前のフォルダを作って練習します。
- 鍵を変えたいとき（参加者が入れ替わった、鍵が外に出たかもしれない、など）は、同じコマンドをもう一度実行します。鍵と MySQL パスワードが新しくなり、古い鍵は使えなくなります。
- 個人ごとにIDを分けたい場合は `sudo bash scripts/add_student.sh user01` のように別名で作れます。

### 7. 勉強会が終わったら

```bash
sudo mysql potchi < sql/reset.sql && sudo mysql potchi < sql/seed.sql
```

データが最初の状態に戻ります（管理画面のユーザーは残ります）。

## 権限の設計メモ

- 受講者の MySQL ユーザーは `DELETE` / `DROP` ができません。全員で1つの DB を共有しても、誰かが全部消してしまう事故が起きないようにするためです。
- そのため、管理画面には「削除」がなく、代わりに「非公開にする」があります。
- 注文の確定（注文・明細・在庫の更新）は1つのトランザクションで行います。在庫が足りなければ、全部取り消します。

## 手順書の更新

手順書は `docs/index.html` で、GitHub Pages（https://peegra.github.io/potchi-store/ ）として公開しています。書き換えて main に push すると、数分で反映されます。
