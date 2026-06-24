# Minecraft server with Create

Docker-based setup for running a Fabric Minecraft server with the Create mod plus scheduled backups.

## Quick start

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

## MOD 管理

`container/compose.yaml` の `MODRINTH_PROJECTS` に Modrinth のスラッグを追記するだけで起動時に自動ダウンロードされます。

```yaml
MODRINTH_PROJECTS: |
  create-fabric
  fabric-api
  jei
```

手動で MOD を追加したい場合は `container/minecraft/mods/` に `.jar` を配置してください。

### Modrinth 管理Mod一覧

`MODRINTH_PROJECTS` に指定するスラグと、現在のNeoForge 1.21.1 環境における対応状況のまとめである。

| Mod名 | URL | Project Slug | 対応バージョン |
| --- | --- | --- | --- |
| Create | - | `create` | 1.21.1 (NeoForge) |
| EMI | - | `emi` | 1.21.1 (NeoForge) |
| Architectury API | - | `architectury-api` | 1.21.1 (NeoForge) |
| Particle Core | - | `particle-core` | 1.21.1 (NeoForge) |
| Fzzy Config | - | `fzzy-config` | 1.21.1 (NeoForge) |
| Kotlin for Forge | - | `kotlin-for-forge` | 1.21.1 (NeoForge) |
| ImmediatelyFast | - | `immediatelyfast` | 1.21.1 (NeoForge) |
| Create Power Loader | [https://modrinth.com/mod/create-power-loader](https://modrinth.com/mod/create-power-loader) | `create-power-loader` | 1.21.1 (NeoForge) |
| Create Factory Logistics | [https://modrinth.com/mod/create_factory_logistics](https://modrinth.com/mod/create_factory_logistics) | `create_factory_logistics` | 1.21.1 (NeoForge) |
| Extra Gauges | [https://modrinth.com/mod/extra-gauges](https://modrinth.com/mod/extra-gauges) | `extra-gauges` | 1.21.1 (NeoForge) |
| FTB Ultimine | [https://github.com/FTBTeam/FTB-Ultimine](https://github.com/FTBTeam/FTB-Ultimine) | `ftb-ultimine` | 1.21.1 (NeoForge) |
| Jade | [https://modrinth.com/mod/jade/versions?c=release&g=1.21.1&l=neoforge](https://modrinth.com/mod/jade/versions?c=release&g=1.21.1&l=neoforge) | `jade` | 1.21.1 (NeoForge) |

### CurseForge 管理Mod一覧

`CURSEFORGE_FILES` に指定するProject IDと、現在のNeoForge 1.21.1 環境における対応状況のまとめである。

| Mod名 | URL | Project ID | 対応バージョン |
| --- | --- | --- | --- |
| JourneyMap | - | `32274` | 1.21.1 (NeoForge) |
| Just Enough Items (JEI) | [https://www.curseforge.com/minecraft/mc-mods/jei](https://www.curseforge.com/minecraft/mc-mods/jei) | `238222` | 1.21.1 (NeoForge) |
| Sophisticated Backpacks | [https://www.curseforge.com/minecraft/mc-mods/sophisticated-backpacks](https://www.curseforge.com/minecraft/mc-mods/sophisticated-backpacks) | `422819` | 1.21.1 (NeoForge) |
| Curios API | [https://www.curseforge.com/minecraft/mc-mods/curios](https://www.curseforge.com/minecraft/mc-mods/curios) | `309927` | 1.21.1 (NeoForge) |
| Create Stuff & Additions | [https://www.curseforge.com/minecraft/mc-mods/create-stuff-additions](https://www.curseforge.com/minecraft/mc-mods/create-stuff-additions) | `519896` | 1.21.1 (NeoForge) |
| Create Steam 'n' Rails | [https://www.curseforge.com/minecraft/mc-mods/create-steam-n-rails](https://www.curseforge.com/minecraft/mc-mods/create-steam-n-rails) | `688231` | 1.21.1 (NeoForge) |
| Create: Copycats+ | [https://www.curseforge.com/minecraft/mc-mods/copycats](https://www.curseforge.com/minecraft/mc-mods/copycats) | `968398` | 1.21.1 (NeoForge) |
| VS: Clockwork | [https://www.curseforge.com/minecraft/mc-mods/create-clockwork](https://www.curseforge.com/minecraft/mc-mods/create-clockwork) | `807792` | 1.21.1 (NeoForge) |
| FTB Library (NeoForge) | [https://www.curseforge.com/minecraft/mc-mods/ftb-library-forge](https://www.curseforge.com/minecraft/mc-mods/ftb-library-forge) | `404465` | 1.21.1 (NeoForge) |

## バックアップ

`itzg/mc-backup` が毎日 12:00 (JST) に自動バックアップします。バックアップ先は `container/minecraft/backups/` です。
