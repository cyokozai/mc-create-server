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

## バックアップ

`itzg/mc-backup` が毎日 12:00 (JST) に自動バックアップします。バックアップ先は `container/minecraft/backups/` です。
