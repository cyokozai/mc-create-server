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

### README用: Modrinth 管理Mod一覧

| Mod名 | URL | Project Slug | 対応バージョン |
| --- | --- | --- | --- |
| Architectury API | - | `architectury-api` | 1.21.1 (NeoForge) |
| Create: Copycats+ | [https://modrinth.com/mod/copycats/versions](https://modrinth.com/mod/copycats/versions) | `copycats` | 1.21.1 (NeoForge) |
| Create | - | `create` | 1.21.1 (NeoForge) |
| Create Aeronautics | [https://www.curseforge.com/minecraft/mc-mods/create-aeronautics](https://www.curseforge.com/minecraft/mc-mods/create-aeronautics) | `create-aeronautics` | 1.21.1 (NeoForge) |
| Create Power Loader | [https://modrinth.com/mod/create-power-loader](https://modrinth.com/mod/create-power-loader) | `create-power-loader` | 1.21.1 (NeoForge) |
| Create Steam 'n' Rails | [https://modrinth.com/mod/create-steam-n-rails-1.21.1](https://modrinth.com/mod/create-steam-n-rails-1.21.1) | `create-steam-n-rails-1.21.1` | 1.21.1 (NeoForge) |
| Create Stuff & Additions | [https://modrinth.com/mod/create-stuff-additions](https://modrinth.com/mod/create-stuff-additions) | `create-stuff-additions` | 1.21.1 (NeoForge) |
| Create Factory Logistics | [https://modrinth.com/mod/create_factory_logistics](https://modrinth.com/mod/create_factory_logistics) | `create_factory_logistics:beta` | 1.21.1 (NeoForge) |
| Deployer API | [https://modrinth.com/mod/deployer](https://modrinth.com/mod/deployer) | `deployer` | 1.21.1 (NeoForge) |
| EMI | - | `emi` | 1.21.1 (NeoForge) |
| Extra Gauges | [https://modrinth.com/mod/extra-gauges](https://modrinth.com/mod/extra-gauges) | `extra-gauges` | 1.21.1 (NeoForge) |
| Fzzy Config | - | `fzzy-config` | 1.21.1 (NeoForge) |
| ImmediatelyFast | - | `immediatelyfast` | 1.21.1 (NeoForge) |
| Jade | [https://modrinth.com/mod/jade](https://modrinth.com/mod/jade) | `jade` | 1.21.1 (NeoForge) |
| Kotlin for Forge | - | `kotlin-for-forge` | 1.21.1 (NeoForge) |
| Particle Core | - | `particle-core` | 1.21.1 (NeoForge) |
| Sable | [https://modrinth.com/mod/sable](https://modrinth.com/mod/sable) | `sable` | 1.21.1 (NeoForge) |
| Sophisticated Backpacks | [https://modrinth.com/mod/sophisticated-backpacks](https://modrinth.com/mod/sophisticated-backpacks) | `sophisticated-backpacks` | 1.21.1 (NeoForge) |
| Sophisticated Core | [https://modrinth.com/mod/sophisticated-core](https://modrinth.com/mod/sophisticated-core) | `sophisticated-core` | 1.21.1 (NeoForge) |

### README用: CurseForge 管理Mod一覧

(※CurseForge側のリストに変更はないが、最新の状態として再掲する)

| Mod名 | URL | Project ID | 対応バージョン |
| --- | --- | --- | --- |
| Curios API | [https://www.curseforge.com/minecraft/mc-mods/curios](https://www.curseforge.com/minecraft/mc-mods/curios) | `309927` | 1.21.1 (NeoForge) |
| FTB Library (NeoForge) | [https://www.curseforge.com/minecraft/mc-mods/ftb-library-forge](https://www.curseforge.com/minecraft/mc-mods/ftb-library-forge) | `404465` | 1.21.1 (NeoForge) |
| FTB Ultimine (NeoForge) | [https://github.com/FTBTeam/FTB-Ultimine](https://github.com/FTBTeam/FTB-Ultimine) | `386134` | 1.21.1 (NeoForge) |
| JourneyMap | - | `32274` | 1.21.1 (NeoForge) |
| Just Enough Items (JEI) | [https://www.curseforge.com/minecraft/mc-mods/jei](https://www.curseforge.com/minecraft/mc-mods/jei) | `238222` | 1.21.1 (NeoForge) |

## バックアップ

`itzg/mc-backup` が毎日 12:00 (JST) に自動バックアップします。バックアップ先は `container/minecraft/backups/` です。
