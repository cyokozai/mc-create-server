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

1. `compose.yaml` の該当リストに **`<slug>:<version>` の形で**追記する（バージョン無指定で書かない）
2. `python3 tools/lock-mods.py check` を通す。固定漏れと解決失敗はここで落ちる
3. 前提 MOD とバージョンレンジを検証する（次項）
4. **下の MOD 一覧表を同じ内容に更新する**（表と compose の乖離が過去に起きている）
5. **クライアント側にも必要かを判定し、`Client` 列を埋める**
6. `python3 tools/lock-mods.py mrpack` で `client/mc-create.mrpack` を作り直してコミットする
7. VM 上で起動確認する

### バージョン固定の方針

**MOD は全てバージョンを固定する。** 以前は `MODRINTH_DEFAULT_VERSION_TYPE: release` に任せて
latest release へ自動追従していたが、上流更新でクライアントとサーバーがズレる事故が起きたため廃止した。

| リスト | 書式 | 例 |
| --- | --- | --- |
| `MODRINTH_PROJECTS` | `<slug>:<version number>` | `create:6.0.10+mc1.21.1` |
| `CURSEFORGE_FILES` | `<project id>:<file id>` | `238222:8792638` |

`MODRINTH_DEFAULT_VERSION_TYPE` は残してあるが、**固定漏れがあったときの保険**でしかない。
beta しか無い MOD（`dragonlib` `create-railways-navigator`）もバージョン番号で直接指定するので、
`:beta` のようなチャネル指定は不要。

### `tools/lock-mods.py`

`compose.yaml` を読んで検証と生成を行う。**compose.yaml が単一の情報源で、このスクリプトは書き換えない。**

```bash
python3 tools/lock-mods.py check    # 固定漏れ・解決失敗を検査（CI 向け）
python3 tools/lock-mods.py latest   # 各 MOD の最新 release と現在の固定値を比較
python3 tools/lock-mods.py mrpack   # client/mc-create.mrpack を生成
python3 tools/lock-mods.py table    # README 用の一覧表を出力（jar を落とすので遅い）
```

`mrpack` は Modrinth API の `client_side` / `server_side` を見て各 MOD に `env` を付ける。
そのため **1 つの `.mrpack` でサーバー専用とクライアント専用を正しく振り分けられる**。
Prism はクライアント側だけをインストールする。

MOD を更新するときは `latest` で差分を見て、`compose.yaml` を書き換え、`check` を通し、
`mrpack` を作り直す。この 4 手順を飛ばさないこと。

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

| Mod名 | Slug | 固定バージョン | Server | Client | 備考 |
| --- | --- | --- | :---: | :---: | --- |
| [Architectury API](https://modrinth.com/mod/architectury-api) | `architectury-api` | `13.0.11+neoforge` | ✅ | ✅ | 共通ライブラリ。`dragonlib` の前提 |
| [DragonLib](https://modrinth.com/mod/dragonlib) | `dragonlib` | `1.21.1-beta-3.0.28` | ✅ | ✅ | Railways Navigator の前提。**release チャネルなし** |
| [Fzzy Config](https://modrinth.com/mod/fzzy-config) | `fzzy-config` | `0.7.7+1.21+neoforge` | ✅ | ✅ | `particle-core` / `immersive-paintings` の前提 |
| [Kotlin for Forge](https://modrinth.com/mod/kotlin-for-forge) | `kotlin-for-forge` | `5.12.0` | ✅ | ✅ | `particle-core` の前提 |
| [Create](https://modrinth.com/mod/create) | `create` | `6.0.10+mc1.21.1` | ✅ | ✅ | `flywheel` / `ponder` / `Registrate` を同梱 |
| [Create: Copycats+](https://modrinth.com/mod/copycats) | `copycats` | `3.0.9+mc.1.21.1-neoforge` | ✅ | ✅ |  |
| [Create Aeronautics](https://modrinth.com/mod/create-aeronautics) | `create-aeronautics` | `1.3.2+mc1.21.1` | ✅ | ✅ |  |
| [Create: Coasters Simulated](https://modrinth.com/mod/create-coasters-simulated) | `create-coasters-simulated` | `0.1.5` | ✅ | ✅ | 要 `create` `[6.0.10,)` / `sable` `[2.0.0,)` |
| [Create: Electro Energetics](https://modrinth.com/mod/create-electro-energetics) | `create-electro-energetics` | `1.21.1-1.1.2` | ✅ | ✅ | **要 `create` `[6.0.7,6.1.0)`**。Create 6.1.0 が出ると破綻 |
| [Create: Power Loader](https://modrinth.com/mod/create-power-loader) | `create-power-loader` | `2.0.5-mc1.21.1` | ✅ | ✅ |  |
| [Create Railways Navigator](https://modrinth.com/mod/create-railways-navigator) | `create-railways-navigator` | `1.21.1-beta-0.10.0-C6` | ✅ | ✅ | 電光行先表示器。**beta のみ**。要 `dragonlib` |
| [Steam 'n' Rails Neoforge](https://modrinth.com/mod/create-steam-n-rails-1.21.1) | `create-steam-n-rails-1.21.1` | `0.2.1+neoforge-mc1.21.1` | ✅ | ✅ | NeoForge 版は slug が `-1.21.1` 付き |
| [Create Stuff 'N Additions](https://modrinth.com/mod/create-stuff-additions) | `create-stuff-additions` | `2.1.4.b` | ✅ | ✅ |  |
| [CreateTrainWebAPI](https://modrinth.com/mod/createtrainwebapi) | `createtrainwebapi` | `1.1.0` | ✅ | — | 列車位置の HTTP API。既定 8080。BlueMap 連携可 |
| [Create: Deployer API](https://modrinth.com/mod/deployer) | `deployer` | `0.1.3` | ✅ | ✅ |  |
| [Create: Extra Gauges](https://modrinth.com/mod/extra-gauges) | `extra-gauges` | `2.1.3` | ✅ | ✅ |  |
| [Corail Tombstone](https://modrinth.com/mod/corail-tombstone) | `corail-tombstone` | `neoforge-1.21.1-9.5.6` | ✅ | ✅ | 死亡時の墓。`iris` は optional |
| [Immersive Paintings](https://modrinth.com/mod/immersive-paintings) | `immersive-paintings` | `0.7.9+1.21.1` | ✅ | ✅ | PNG を絵画として貼る。要 `fzzy-config` |
| [Sable](https://modrinth.com/mod/sable) | `sable` | `2.0.5+mc1.21.1` | ✅ | ✅ | `veil` / `rapier` を同梱 |
| [Sophisticated Backpacks](https://modrinth.com/mod/sophisticated-backpacks) | `sophisticated-backpacks` | `1.21.1-3.26.6.2174` | ✅ | ✅ |  |
| [Sophisticated Core](https://modrinth.com/mod/sophisticated-core) | `sophisticated-core` | `1.21.1-1.5.2.2343` | ✅ | ✅ | Sophisticated Backpacks の前提 |
| [BlueMap](https://modrinth.com/mod/bluemap) | `bluemap` | `5.7-neoforge` | ✅ | — | Web 地図。既定 8100。`IGNORE_SERVER_VERSION` |
| [EMI](https://modrinth.com/mod/emi) | `emi` | `1.1.24+1.21.1+neoforge` | ✅ | ✅ | レシピ表示。JEI と役割が重複 |
| [Jade 🔍](https://modrinth.com/mod/jade) | `jade` | `15.10.6+neoforge` | ✅ | ✅ | ブロック情報 HUD |
| [WorldEdit](https://modrinth.com/mod/worldedit) | `worldedit` | `7.3.8` | ✅ | — | `IGNORE_SERVER_VERSION` のため**クライアント不要** |
| [ImmediatelyFast](https://modrinth.com/mod/immediatelyfast) | `immediatelyfast` | `1.6.14+1.21.1-neoforge` | ⚠ | ✅ | 依存が全て `side=CLIENT`。**実質クライアント専用** |
| [Particle Core](https://modrinth.com/mod/particle-core) | `particle-core` | `0.3.3+1.21+neoforge` | ⚠ | ✅ | 依存が全て `side=CLIENT`。**実質クライアント専用** |
| [Sodium](https://modrinth.com/mod/sodium) | `sodium` | `mc1.21.1-0.8.13-neoforge` | — | ✅ | **クライアント専用**。サーバーの MOD リストに入れない。`embeddium` と非互換 |

凡例: ✅ 必要 / — 不要 / ⚠ 現在サーバー側にも入っているが本来クライアント専用 / ✋ 無効化中

### CurseForge 管理（`CURSEFORGE_FILES`）

| Mod名 | Project:File | 固定バージョン | Server | Client | 備考 |
| --- | --- | --- | :---: | :---: | --- |
| [Curios API](https://www.curseforge.com/minecraft/mc-mods/curios) | `309927:6529130` | 9.5.1 | ✅ | ✅ | |
| [FTB Library](https://www.curseforge.com/minecraft/mc-mods/ftb-library-forge) | `404465:9008089` | 2101.1.37 | ✅ | ✅ | FTB Ultimine の前提 |
| [FTB Ultimine](https://www.curseforge.com/minecraft/mc-mods/ftb-ultimine) | `386134:8231400` | 2101.1.15 | ✅ | ✅ | 一括破壊 |
| [Just Enough Items (JEI)](https://www.curseforge.com/minecraft/mc-mods/jei) | `238222:8792638` | 19.51.0.418 | ✅ | ✅ | **NeoForge `[21.1.238,)` を要求。全体の下限** |
| [JourneyMap](https://www.curseforge.com/minecraft/mc-mods/journeymap) | `32274:8923668` | 6.0.9 | ✅ | ✅ | ミニマップ |
| [Create: Station Voices](https://www.curseforge.com/minecraft/mc-mods/create-station-voices) | `1666057:8943256` | 1.0.2 | ✅ | ✅ | 発車ベル・放送。**jar 53MB**（Piper TTS 同梱）|

> CurseForge の MOD は `.mrpack` に含められない（Modrinth の許可ドメイン外）。
> **Prism には上の 6 件を手動で追加する。** バージョンはこの表の値に合わせること。

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

### 2. MOD を追加（`.mrpack` をインポートする）

**MOD を 1 つずつ手で探さない。** バージョン取り違えが起動失敗の最大の原因なので、
リポジトリが生成した `.mrpack` を読み込ませてバージョンごと固定する。

1. `client/mc-create.mrpack` を取得する（リポジトリに追跡済み）
2. Prism の **「インスタンスを追加」→「Modrinth」タブ →「ファイルからインポート」** で選ぶ
   - 既存インスタンスに入れ直す場合は作り直した方が早い
3. `.mrpack` に入っているのは **Modrinth 管理の MOD だけ**。
   **CurseForge 管理の 6 件は手動で追加する** → [CurseForge の表](#curseforge-管理curseforge_files)の
   バージョンに合わせること。同梱の `MANUAL-CURSEFORGE.txt` にも同じ一覧がある
4. 検索して追加するときは **1.21.1 / NeoForge** のフィルタを毎回確認する

`.mrpack` には `env` が入っているので、**サーバー専用の MOD は Prism 側に入らない**
（`worldedit` `bluemap` `createtrainwebapi`）。逆に `sodium` `immediatelyfast` `particle-core` は
クライアントにだけ入る。手で選り分ける必要はない。

`create` を入れると `flywheel` / `ponder` / `Registrate`、`sable` を入れると `veil` / `rapier` が
付いてくる。個別に追加しない。`create_factory_logistics` は**追加しない**（サーバー側で無効化中）。

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
| Create Aeronautics / Sable / Create: Coasters Simulated | `[21.1.228,)` |
| Create: Deployer API / Extra Gauges | `[21.1.227,)` |
| Create | `[21.1.219,)` |
| CreateTrainWebAPI | `[21.1.206,)` |
| Create: Copycats+ | `[21.1.200,)` |
| Create: Electro Energetics | `[21.1.174,)` |
| Immersive Paintings | `[21.1.154,)` |
| Sodium（クライアントのみ） | `[21.1.82,)` |
| Create Stuff 'N Additions | `[21.1.65,)` |
| Curios API | `[21.1.60,)` |
| その他（Jade / WorldEdit / EMI / BlueMap / Corail Tombstone / Station Voices / Railways Navigator ほか） | `21.1.0` 未満 — 制約にならない |

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

## Web 連携（BlueMap / CreateTrainWebAPI）

| MOD | 既定ポート | 役割 |
| --- | --- | --- |
| BlueMap | `8100` | ワールドを 3D / 2D の Web 地図として配信 |
| CreateTrainWebAPI | `8080` | Create の列車位置を JSON で返す HTTP API |

CreateTrainWebAPI は BlueMap のオーバーレイとして列車を地図上に出せる。
**どちらもクライアントには不要**（`client_side: unsupported`）。

### ポートの扱い

`compose.yaml` では **`127.0.0.1` に束縛している。**

```yaml
- "127.0.0.1:8100:8100/tcp"   # BlueMap web
- "127.0.0.1:8080:8080/tcp"   # CreateTrainWebAPI
```

外から見られるようにする場合は **リバースプロキシを前段に置く**こと。
`0.0.0.0` で直接晒すと、BlueMap の Web UI と列車 API が認証なしで公開される。

### 初回起動時の注意

BlueMap は初回にワールド全体をレンダリングするため **CPU を長時間使う**。
既存ワールドが大きい場合、`limits.cpus: "3.5"` の枠を食ってサーバー本体が重くなる。
プレイヤーが居ない時間帯に初回レンダリングを済ませること。

設定は `container/minecraft/data/config/bluemap/` と
`container/minecraft/data/config/createtrainwebapi/` に生成される。どちらも gitignore 対象。

## 既知の課題

MOD 構成に手を入れる前に把握しておくべき点。

### Create のバージョン追従リスク

バージョン固定を入れたので**勝手に壊れることは無くなった**が、更新するときの制約は残っている。

| MOD | 要求 | 現在の固定値 |
| --- | --- | --- |
| Create: Electro Energetics `1.1.2` | `create` **`[6.0.7,6.1.0)`** | Create `6.0.10+mc1.21.1` |
| Create: Coasters Simulated `0.1.5` | `create` **`[6.0.10,)`** / `sable` `[2.0.0,)` | Create `6.0.10`（**下限ちょうど**） |
| Create Railways Navigator `0.10.0-C6` | `create` `[6.0.8,)` / `dragonlib` `[3.0.28,)` | |

**Create を上げるときは Electro Energetics が `6.1.0` に追従しているかを先に確認する。**
Coasters Simulated は逆に Create の下限ちょうどなので、**Create を下げることはできない。**

`python3 tools/lock-mods.py latest` で上流の最新と現在の固定値を並べて確認できる。

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
