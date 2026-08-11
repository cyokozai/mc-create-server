# CLAUDE.md — mc-create-server

Minecraft **1.21.1 / NeoForge** サーバーを Docker で運用するリポジトリ。
Create とその addon 群を中心とした構成で、`itzg/minecraft-server` + `itzg/mc-backup` を使う。

## 最重要ルール

### 1. サーバーはローカルで起動しない

**実行環境は VM。Mac ローカルで `docker compose up` を実行してはならない。**
起動確認が必要な場合はコマンドを提示するにとどめ、実行はユーザー（VM 側）に委ねる。

```bash
# ユーザーが VM 上で実行するコマンドとして提示する
docker compose -f container/compose.yaml up -d
docker compose -f container/compose.yaml logs -f mc-create
```

### 2. シークレットファイルを読まない

`container/.env` と `container/secret.env` は **読み込み・表示・編集しない**（グローバルルール準拠）。
`.env.example` / `secret.env.example` は追跡対象で読み込み可。

| ファイル | 中身 | 追跡 |
| --- | --- | --- |
| `container/.env` | `CONTAINER_NAME` `SERVER_HOST_NAME` `LOCAL_DNS` `SERVER_MEMORY` | ✗ |
| `container/secret.env` | `RCON_PASSWORD` | ✗ |

### 3. git の破壊的操作をしない

`git add` / `commit` / `push` / `rebase` / `reset` は実行せず、コマンドを提示する。
読み取り系（`log` `show` `diff` `status`）は自由に使ってよい。

## リポジトリ構成

```
README.md                      # 唯一のドキュメント。MOD 一覧表を含む
container/
  compose.yaml                 # ★ サーバー構成の単一の情報源（MOD リストもここ）
  .env / secret.env            # 実値（gitignore）
  .env.example / secret.env.example
  minecraft/{data,mods,backups}/  # 実行時生成（gitignore、リポジトリには存在しない）
  image/server-icon.png        # compose がマウントするが未追跡
```

`installer/Windows/` は履歴上に存在したが削除済み（`da0c4da`）。
`installer.bat` は最後まで **0 バイトの空ファイル**で、実装されたことはない。
`mc-create.zip` は CurseForge 形式の modpack（`manifest.json` + `overrides/`）だった。

## MOD 管理の仕組み

`container/compose.yaml` の 2 つの環境変数が MOD 構成を決める。`minecraft/mods/` に手動配置も可能。

| 変数 | 書式 | 備考 |
| --- | --- | --- |
| `MODRINTH_PROJECTS` | Modrinth の project slug を改行区切り | `#` 以降はコメント。`slug:beta` でチャネル指定 |
| `CURSEFORGE_FILES` | CurseForge の **project ID** を改行区切り | `309927 # = Curios API` の形でコメント必須 |

`MODRINTH_DEFAULT_VERSION_TYPE: release` のため、**バージョン未指定の slug は最新 release に自動追従する**。
これは便利だが、addon の依存レンジを外れて壊れる原因になる（下記「監視すべきバージョン制約」）。

### MOD を追加・変更したときにやること

1. `compose.yaml` の該当リストに追記
2. **`README.md` の MOD 一覧表を同じ内容に更新**（表と compose の乖離が過去に何度も起きている）
3. 依存関係を下記の手順で検証
4. クライアント側（Prism）にも必要な MOD かを判定し、クライアント一覧にも反映
5. 起動確認は VM 上でユーザーに依頼

## 依存関係の検証手順（推測せず必ずこれで確認する）

MOD の前提条件は **jar 内の `META-INF/neoforge.mods.toml` が唯一の正解**。
Modrinth のページ表記や記憶に頼らない。

```bash
# 1) 1.21.1 / neoforge 向けバージョンと依存 project を取る
curl -s -H 'User-Agent: mc-create-server-docs/1.0' \
  'https://api.modrinth.com/v2/project/<slug>/version?loaders=%5B%22neoforge%22%5D&game_versions=%5B%221.21.1%22%5D' \
  | python3 -m json.tool

# 2) jar を落として宣言を直接読む（バージョンレンジはここにしかない）
unzip -p <mod>.jar META-INF/neoforge.mods.toml

# 3) 同梱ライブラリ（jarjar）の重複を確認
unzip -p <mod>.jar META-INF/jarjar/metadata.json
```

読むべきポイント:

- `[[dependencies.*]]` の `modId` / `versionRange` / `type` → 前提 MOD と許容レンジ
- `side = "BOTH" | "CLIENT" | "SERVER"` → どちら側に必要か
- **`displayTest = "IGNORE_SERVER_VERSION"`** → クライアント未導入でも参加可能。つまり
  **サーバー専用で配れる**（WorldEdit がこれに該当）
- `META-INF/jarjar/` → 同梱ライブラリ。他 MOD と同一バージョンなら NeoForge が重複排除するので衝突しない

### クライアント／サーバーどちら側かの判定

Modrinth API の `client_side` / `server_side` を一次情報として使う。

```bash
curl -s -H 'User-Agent: x/1.0' 'https://api.modrinth.com/v2/project/<slug>' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["client_side"], d["server_side"])'
```

- `client_side: required` → **Prism 側にも必ず入れる**。入れないと参加時に弾かれる
- `server_side: unsupported` → **サーバーの MOD リストに入れてはいけない**（クライアント専用）
- `unknown` → API 未整備。jar の `neoforge.mods.toml` を読んで判断する

## 監視すべきバージョン制約

`MODRINTH_PROJECTS` は latest release に追従するため、以下は上流更新で壊れうる。
Create 本体を上げるときは必ず addon 側のレンジを再確認する。

| MOD | 制約 | 現状 |
| --- | --- | --- |
| Create: Electro Energetics `1.21.1-1.1.1` | `create` **`[6.0.7,6.1.0)`** | Create `6.0.10+mc1.21.1` で範囲内。**Create 6.1.0 が出ると破綻** |
| Sable `2.0.3` | NeoForge `[21.1.228,)` | クライアント側 NeoForge は `21.1.233` で充足 |
| Create: Electro Energetics | NeoForge `[21.1.174,)` | 同上 |

`create_factory_logistics` は **Deployer と競合するため無効化中**（`compose.yaml` にコメントで残す）。
有効化を提案する前にこの経緯を確認すること。

## クライアント側（Prism Launcher）

新規参加者は **Prism Launcher** でクライアントを作る前提。ローダーは **NeoForge 21.1.233 / MC 1.21.1**。

サーバーとクライアントで **`side = BOTH` の MOD は完全に一致させる必要がある**。
一致していないと参加時に registry / channel 不一致で接続を拒否される。
サーバー一覧をそのままコピーするのは誤り — 以下の 2 方向のズレを必ず切り分ける。

- サーバーにあってクライアントに不要: `worldedit`（`IGNORE_SERVER_VERSION`）
- クライアント専用でサーバーに入れてはいけない: `immediatelyfast` `particle-core`（`server_side: unsupported`）

## バックアップ

`itzg/mc-backup` が毎日 12:00 JST に `container/minecraft/backups/` へ tar+gzip で保存。
`PRUNE_BACKUPS_DAYS: 5` で 5 日より古いものは削除される。
`PAUSE_IF_NO_PLAYERS: TRUE` のためプレイヤー不在時はスキップ。
`.mc-backup-lock` は gitignore 済み（`1fce8cc` で無効化対応）。

`backup` サービスは `network_mode: "service:mc-create"` で mc-create のネットワークを共有するため、
RCON は `localhost:25575` で届く。

## ネットワーク上の注意

- `com.docker.network.driver.mtu: 1280` — VPN 経由を想定した MTU 縮小。安易に戻さない
- `dns` に `${LOCAL_DNS}` → `1.1.1.1` のフォールバック順。MOD ダウンロードが DNS で失敗しやすいための措置
- 公開ポートは `25565/tcp` のみ。**RCON `25575` は公開していない**（コンテナ内部のみ）

## アシストの方針

- **MOD 構成の変更を依頼されたら**: compose.yaml → README 表 → クライアント一覧の 3 点セットで更新する。
  片方だけ直すと必ず後で食い違う
- **依存関係を聞かれたら**: 記憶で答えず上記の API + jar 検証を実行する
- **起動確認を求められたら**: 実行せずコマンドを提示し、VM 上での実行を依頼する
- **「動かない」と言われたら**: まず client / server の MOD 差分と、`create` のバージョンレンジを疑う
