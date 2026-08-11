# Minecraft server with Create

Create とその addon 群を中心とした **Minecraft 1.21.1 / NeoForge** サーバーの Docker 構成。
`itzg/minecraft-server` でサーバー本体を、`itzg/mc-backup` で定期バックアップを動かす。

- サーバー本体の構成はすべて [container/compose.yaml](container/compose.yaml) が単一の情報源
- MOD は起動時に Modrinth / CurseForge から自動ダウンロードされる（リポジトリに jar は置かない）
- クライアント側は **Prism Launcher** で構築する → [クライアント環境の構築](#クライアント環境の構築prism-launcher)

| 項目 | 値 |
| --- | --- |
| Minecraft | 1.21.1 |
| Mod Loader | NeoForge **21.1.238 以上**（推奨 `21.1.248`。[理由](#neoforge-のバージョン要件)） |
| 難易度 | hard |
| 最大プレイヤー数 | 50 |
| 公開ポート | `25565/tcp` |

---

## サーバー構築

> **サーバーは VM 上で動かす。** ローカル（開発機）では起動しない。

```bash
# 1. 環境変数ファイルを用意
cp container/.env.example container/.env
cp container/secret.env.example container/secret.env
# container/.env と container/secret.env を編集して RCON_PASSWORD などを設定

# 2. 必要なディレクトリを作成
mkdir -p container/minecraft/{data,mods,backups}

# 3. 起動 (初回は MOD の自動ダウンロードがあるため数分かかる)
docker compose -f container/compose.yaml up -d

# 4. ログ確認
docker compose -f container/compose.yaml logs -f mc-create
```

### 起動確認のポイント

MOD 構成を変更したあとは、ログで次の 3 点を確認する。

```bash
# ダウンロードに失敗した MOD がないか
docker compose -f container/compose.yaml logs mc-create | grep -iE 'error|failed|not found'

# 依存解決に失敗していないか（NeoForge が弾いた MOD はここに出る）
docker compose -f container/compose.yaml logs mc-create | grep -iE 'missing|incompatible|Mod Loading has failed'

# 起動完了と、サーバーが解決した NeoForge のバージョン
docker compose -f container/compose.yaml logs mc-create | grep -iE 'Done \(|neoforge'
```

`Done (xx.xxxs)! For help, type "help"` が出れば起動成功。
ここで確認した NeoForge のバージョンを、クライアント側でも合わせる。

### 環境変数

| ファイル | 変数 | 用途 |
| --- | --- | --- |
| `.env` | `CONTAINER_NAME` | コンテナ名とバックアップ名の接頭辞 |
| `.env` | `SERVER_HOST_NAME` | バックアップ側から見たサーバーホスト |
| `.env` | `LOCAL_DNS` | MOD ダウンロード用 DNS（`1.1.1.1` にフォールバック） |
| `.env` | `SERVER_MEMORY` | JVM ヒープ（既定 `8G`） |
| `secret.env` | `RCON_PASSWORD` | RCON パスワード。**RCON ポートは外部公開していない** |

---

## MOD 管理

[container/compose.yaml](container/compose.yaml) の 2 つの環境変数に追記するだけで、起動時に自動ダウンロードされる。

```yaml
# Modrinth: project slug を改行区切り。# 以降はコメント
MODRINTH_PROJECTS: |
  create
  create-electro-energetics
  worldedit
MODRINTH_DEFAULT_VERSION_TYPE: release

# CurseForge: project ID を改行区切り。何の MOD かをコメントで必ず添える
CURSEFORGE_FILES: |
  309927 # = Curios API
  238222 # = Just Enough Items (JEI)
```

手動で MOD を追加したい場合は `container/minecraft/mods/` に `.jar` を配置する。

### MOD を追加・変更するときの手順

1. `compose.yaml` の該当リストに追記する
2. **下の MOD 一覧表を同じ内容に更新する**（表と compose の乖離が過去に起きている）
3. 前提 MOD とバージョンレンジを検証する（次項）
4. **クライアント側にも必要かを判定し、`Client` 列を埋める**
5. VM 上で起動確認する

### 前提 MOD の検証方法

Modrinth のページ表記ではなく、**jar 内の `META-INF/neoforge.mods.toml` が唯一の正解**。

```bash
# 1.21.1 / NeoForge 向けのバージョンと依存 project を取得
curl -s -H 'User-Agent: mc-create-server/1.0' \
  'https://api.modrinth.com/v2/project/<slug>/version?loaders=%5B%22neoforge%22%5D&game_versions=%5B%221.21.1%22%5D' \
  | python3 -m json.tool

# jar を落として依存宣言を直接読む（バージョンレンジはここにしかない）
unzip -p <mod>.jar META-INF/neoforge.mods.toml

# 同梱ライブラリ（jarjar）を確認。ここに入っていれば個別に追加しなくてよい
unzip -p <mod>.jar META-INF/jarjar/metadata.json
```

読むべき項目:

| 項目 | 意味 |
| --- | --- |
| `[[dependencies.*]]` の `modId` / `versionRange` | 前提 MOD と許容バージョン |
| `side = "BOTH"` | サーバーとクライアントの両方に必要 |
| `side = "CLIENT"` | クライアント専用。**サーバーの MOD リストに入れない** |
| `displayTest = "IGNORE_SERVER_VERSION"` | クライアント未導入でも参加可能。**サーバー専用で配れる** |
| `META-INF/jarjar/` | 同梱ライブラリ。他 MOD と同一バージョンなら NeoForge が重複排除する |

---

## MOD 一覧

`Server` / `Client` 列は、どちら側にインストールするかを表す。
**`Client` が ✅ の MOD が 1 つでも欠けているクライアントは、参加時に接続を拒否される。**

### Modrinth 管理（`MODRINTH_PROJECTS`）

| Mod名 | Project Slug | Server | Client | 備考 |
| --- | --- | :---: | :---: | --- |
| [Architectury API](https://modrinth.com/mod/architectury-api) | `architectury-api` | ✅ | ✅ | 共通ライブラリ |
| [Create](https://modrinth.com/mod/create) | `create` | ✅ | ✅ | `flywheel` / `ponder` / `Registrate` を同梱 |
| [Create: Copycats+](https://modrinth.com/mod/copycats) | `copycats` | ✅ | ✅ | |
| [Create Aeronautics](https://modrinth.com/mod/create-aeronautics) | `create-aeronautics` | ✅ | ✅ | |
| [Create: Electro Energetics](https://modrinth.com/mod/create-electro-energetics) | `create-electro-energetics` | ✅ | ✅ | **要 `create` `[6.0.7,6.1.0)`**。`sable-companion` を同梱 |
| [Create: Power Loader](https://modrinth.com/mod/create-power-loader) | `create-power-loader` | ✅ | ✅ | |
| [Steam 'n' Rails](https://modrinth.com/mod/create-steam-n-rails-1.21.1) | `create-steam-n-rails-1.21.1` | ✅ | ✅ | NeoForge 版は slug が `-1.21.1` 付き |
| [Create Stuff 'N Additions](https://modrinth.com/mod/create-stuff-additions) | `create-stuff-additions` | ✅ | ✅ | |
| [Create: Deployer API](https://modrinth.com/mod/deployer) | `deployer` | ✅ | ✅ | |
| [Create: Extra Gauges](https://modrinth.com/mod/extra-gauges) | `extra-gauges` | ✅ | ✅ | |
| [Sable](https://modrinth.com/mod/sable) | `sable` | ✅ | ✅ | 要 NeoForge `[21.1.228,)`。`veil` / `rapier` を同梱 |
| [Sophisticated Backpacks](https://modrinth.com/mod/sophisticated-backpacks) | `sophisticated-backpacks` | ✅ | ✅ | |
| [Sophisticated Core](https://modrinth.com/mod/sophisticated-core) | `sophisticated-core` | ✅ | ✅ | 上記の前提 |
| [Fzzy Config](https://modrinth.com/mod/fzzy-config) | `fzzy-config` | ✅ | ✅ | `particle-core` の前提 |
| [Kotlin for Forge](https://modrinth.com/mod/kotlin-for-forge) | `kotlin-for-forge` | ✅ | ✅ | `particle-core` の前提 |
| [EMI](https://modrinth.com/mod/emi) | `emi` | ✅ | ✅ | レシピ表示。JEI と役割が重複（下記「既知の課題」） |
| [Jade](https://modrinth.com/mod/jade) | `jade` | ✅ | ✅ | ブロック情報 HUD |
| [WorldEdit](https://modrinth.com/mod/worldedit) | `worldedit` | ✅ | — | `IGNORE_SERVER_VERSION` のため**クライアント不要** |
| [ImmediatelyFast](https://modrinth.com/mod/immediatelyfast) | `immediatelyfast` | ⚠ | ✅ | 依存が全て `side=CLIENT`。**クライアント専用** |
| [Particle Core](https://modrinth.com/mod/particle-core) | `particle-core` | ⚠ | ✅ | 依存が全て `side=CLIENT`。**クライアント専用** |
| [Create Factory Logistics](https://modrinth.com/mod/create_factory_logistics) | `create_factory_logistics:beta` | ✋ | ✋ | **Deployer と競合するため無効化中**（compose でコメントアウト） |

凡例: ✅ 必要 / — 不要 / ⚠ 現在サーバー側にも入っているが本来クライアント専用 / ✋ 無効化中

### CurseForge 管理（`CURSEFORGE_FILES`）

| Mod名 | Project ID | Server | Client | 備考 |
| --- | --- | :---: | :---: | --- |
| [Curios API](https://www.curseforge.com/minecraft/mc-mods/curios) | `309927` | ✅ | ✅ | |
| [FTB Library](https://www.curseforge.com/minecraft/mc-mods/ftb-library-forge) | `404465` | ✅ | ✅ | FTB Ultimine の前提 |
| [FTB Ultimine](https://www.curseforge.com/minecraft/mc-mods/ftb-ultimine) | `386134` | ✅ | ✅ | 一括破壊 |
| [Just Enough Items (JEI)](https://www.curseforge.com/minecraft/mc-mods/jei) | `238222` | ✅ | ✅ | EMI と役割が重複 |
| [JourneyMap](https://www.curseforge.com/minecraft/mc-mods/journeymap) | `32274` | ✅ | ✅ | ミニマップ。実質クライアント側の機能 |

---

## クライアント環境の構築（Prism Launcher）

新規参加者はこの手順でクライアントを作る。**サーバーと `Client` ✅ の MOD を完全に一致させること。**

### 1. インスタンスを作成

1. [Prism Launcher](https://prismlauncher.org/) をインストールしてログインする
2. **「インスタンスを追加」→「カスタム」** を選ぶ
3. **Minecraft `1.21.1`** を選択
4. Mod Loader に **NeoForge** を選び、**`21.1.248`** を指定する
   - **`21.1.238` 未満では JEI が読み込めず、`Error loading mods` で起動に失敗する** → [NeoForge のバージョン要件](#neoforge-のバージョン要件)
   - サーバーが使っているバージョンと一致させるのが確実。確認方法は同節に記載
5. インスタンス名を付けて作成

### 2. MOD を追加

1. インスタンスを選択して **「編集」→「Mods」タブ** を開く
2. **「Mod を追加」** を押す。Prism は **Modrinth** と **CurseForge** の両方を検索できる
3. 上の一覧の **`Client` が ✅ の MOD をすべて追加する**
   - 検索結果のフィルタが **1.21.1 / NeoForge** になっていることを毎回確認する。ここを外すと 1.20.1 版が入って起動しない
   - `create` を入れると `flywheel` / `ponder` / `Registrate` は自動で付いてくる。個別に追加しない
   - `sable` を入れると `veil` / `rapier` が付いてくる。同様に個別追加は不要
4. **`worldedit` は追加しない。** サーバー側だけで動作する
5. `create_factory_logistics` は**追加しない**（サーバー側で無効化中のため）

### 3. メモリを割り当てる

Create + Sable は描画負荷が高い。**「編集」→「設定」→「Java」** でメモリを **6〜8 GB** に上げる。
既定の 2 GB 前後だとワールド読み込み中に落ちる。

### LWJGL は変更しない

Prism では LWJGL のバージョンも変更できるが、**`3.3.3` のまま触らないこと。**
`3.3.3` は Minecraft 1.21.1 が公式に指定している値で、**MOD 側は LWJGL を一切要求していない**（全 MOD の
`neoforge.mods.toml` を確認済み）。上げても解決する問題は無く、動作確認されていない組み合わせになるだけ。

変更を検討するのは `Failed to initialize GLFW` などネイティブ層のクラッシュを踏んだ場合の回避策としてのみ。
NeoForge のバージョンとは性質が違うので混同しないこと（NeoForge は各 MOD が明示的に要求する＝不足すると
MOD が読み込まれない。LWJGL は Minecraft 本体が固定する）。

### 4. サーバーに接続

**マルチプレイ →「サーバーを追加」** でサーバーアドレスを登録する（ポートは既定の `25565`）。

### 参加できないときの切り分け

| 症状 | 原因 | 対処 |
| --- | --- | --- |
| `Error loading mods` / `Mod xxx requires neoforge NNN or above` | **NeoForge が古い** | NeoForge を `21.1.248` に上げる → [バージョン要件](#neoforge-のバージョン要件) |
| `Incompatible mod set!` / MOD 名の一覧が出る | クライアントに `Client` ✅ の MOD が欠けている | 表示された MOD を Prism で追加する |
| `Connection closed` / registry 不一致 | クライアントとサーバーの MOD バージョン差 | サーバーが解決したバージョンに合わせる |
| クライアントが起動しない（`Missing or unsupported mandatory dependencies`） | 1.20.1 版など別バージョンの MOD が混入 | Prism の Mods タブでバージョンを確認して入れ直す |
| ワールド読み込み中に落ちる | メモリ不足 | Java 設定でメモリを増やす |

---

## NeoForge のバージョン要件

**最低 `21.1.238` / 推奨 `21.1.248`（1.21.1 系の最新）。**
サーバーとクライアントで同じバージョンを使うこと。

必要バージョンは「全 MOD が要求する下限の**最大値**」で決まる。現構成では **JEI が `21.1.238`** を要求し、
これが全体の下限になっている。1 つでも要求を下回ると `Error loading mods` で起動に失敗する。

```text
Mod jei requires neoforge 21.1.238 or above
Currently, neoforge is 21.1.233
```

| MOD | 要求する NeoForge |
| --- | --- |
| **JEI** | **`[21.1.238,)`** ← 全体の下限を決めている |
| Steam 'n' Rails | `[21.1.233,)` |
| Create Aeronautics / Sable | `[21.1.228,)` |
| Create: Deployer API / Extra Gauges | `[21.1.227,)` |
| Create | `[21.1.219,)` |
| Create: Copycats+ | `[21.1.200,)` |
| Create: Electro Energetics | `[21.1.174,)` |
| Create Stuff 'N Additions | `[21.1.65,)` |
| Curios API | `[21.1.60,)` |
| その他（Jade / WorldEdit / EMI ほか） | `21.1.0` 未満 — 制約にならない |

> FTB Library / FTB Ultimine は Modrinth に無く未検証。JEI より厳しい要求があれば上記の下限は変わる。

### バージョンを確認する

```bash
# サーバーが実際に使っている NeoForge
docker compose -f container/compose.yaml logs mc-create | grep -oE 'neoforge-[0-9.]+' | head -1

# 1.21.1 向けに公開されている NeoForge の一覧（最新を知りたいとき）
curl -s 'https://maven.neoforged.net/api/maven/versions/releases/net/neoforged/neoforge' \
  | python3 -c "import json,sys; v=[x for x in json.load(sys.stdin)['versions'] if x.startswith('21.1.')]; print(v[-5:])"
```

クライアント側は Prism の **「編集」→「バージョン」** で NeoForge を選び、`Change version` で変更できる。
MOD を入れ直す必要はない。

### MOD 追加時にやること

**MOD を追加したら、その MOD の NeoForge 要求も必ず確認する。** 下限が上がっていたら
README のこの節とクライアント側インスタンスの両方を更新する。

```bash
unzip -p <mod>.jar META-INF/neoforge.mods.toml | grep -A3 'modId *= *"neoforge"'
```

---

## 既知の課題

MOD 構成に手を入れる前に把握しておくべき点。

### Create のバージョン追従リスク

`MODRINTH_DEFAULT_VERSION_TYPE: release` かつバージョン未指定のため、**MOD は最新 release に自動追従する**。
一方 **Create: Electro Energetics `1.21.1-1.1.1` は `create` `[6.0.7,6.1.0)` に固定**されている。

現状 Create は `6.0.10+mc1.21.1` で範囲内だが、**上流で Create `6.1.0` が公開された時点で起動しなくなる。**
Create のバージョンが上がったときは、Electro Energetics 側が追従しているかを先に確認すること。
必要なら `MODRINTH_PROJECTS` を `create:6.0.10+mc1.21.1` の形でバージョン固定する。

### クライアント専用 MOD がサーバーリストに入っている

`immediatelyfast` と `particle-core` は依存宣言が全て `side = "CLIENT"`（Modrinth 上も `server_side: unsupported`）で、
サーバー側には不要。現状は起動できているが、サーバーの `MODRINTH_PROJECTS` からは外し、
クライアント側だけに入れるのが本来の構成。

### レシピ表示 MOD の重複

**EMI（Modrinth）と JEI（CurseForge）が両方入っている。** どちらもレシピ表示 MOD で役割が重複する。
どちらかに寄せるのが望ましい。

### 一括破壊 MOD の不整合（過去の配布物）

削除済みのクライアント配布物 `installer/Windows/mc-create.zip` には **VeinMiner** が入っていたが、
サーバー側は **FTB Ultimine** を使っている。片側にしか無い MOD は機能しない。
現在の一覧では FTB Ultimine に統一しているので、古い zip を参照しないこと。

---

## バックアップ

`itzg/mc-backup` が毎日 **12:00 (JST)** に自動バックアップする。

| 設定 | 値 |
| --- | --- |
| 保存先 | `container/minecraft/backups/` |
| 形式 | tar + gzip |
| 保持期間 | 5 日（`PRUNE_BACKUPS_DAYS: 5`） |
| プレイヤー不在時 | スキップ（`PAUSE_IF_NO_PLAYERS: TRUE`） |
| 起動時バックアップ | 有効（`BACKUP_ON_STARTUP: TRUE`） |

`backup` サービスは `network_mode: "service:mc-create"` でサーバーとネットワークを共有するため、
RCON には `localhost:25575` で到達する。
