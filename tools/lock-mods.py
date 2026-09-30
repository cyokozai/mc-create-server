#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""compose.yaml の MOD リストを検証し、Prism 用 .mrpack と一覧表を生成する。

compose.yaml が単一の情報源。このスクリプトは読むだけで書き換えない。

  python3 tools/lock-mods.py check     # 固定漏れ・バージョン不整合を検査
  python3 tools/lock-mods.py latest    # 各 MOD の最新 release を表示（更新候補）
  python3 tools/lock-mods.py mrpack    # client/mc-create.mrpack を生成
  python3 tools/lock-mods.py table     # README 貼り付け用の一覧表を出力
"""
import json, os, re, sys, urllib.parse, urllib.request, zipfile

MC = "1.21.1"
LOADER = "neoforge"
UA = {"User-Agent": "mc-create-server/lock-mods"}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPOSE = os.path.join(ROOT, "container", "compose.yaml")

# Modrinth に無い、または CurseForge 管理のまま運用する MOD。
# Prism には手動で追加する必要があるため、ここに正解のバージョンを書いておく。
CF_MANUAL = [
    ("Curios API",             "309927",  "6529130", "9.5.1",        True),
    ("FTB Library (NeoForge)", "404465",  "9008089", "2101.1.37",    True),
    ("FTB Ultimine",           "386134",  "8231400", "2101.1.15",    True),
    ("JourneyMap",             "32274",   "8923668", "6.0.9",        True),
    ("Just Enough Items",      "238222",  "8792638", "19.51.0.418",  True),
    ("Create: Station Voices", "1666057", "8943256", "1.0.2",        True),
]

# サーバーに置かないクライアント専用 MOD（server_side: unsupported）。
# mrpack には env.server=unsupported で入れる。
CLIENT_ONLY = [("sodium", "mc1.21.1-0.8.13-neoforge")]


def api(path, **params):
    url = "https://api.modrinth.com/v2/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return json.load(r)


def parse_compose():
    """MODRINTH_PROJECTS から (slug, pinned_version|None) を取り出す。"""
    text = open(COMPOSE, encoding="utf-8").read()
    m = re.search(r"MODRINTH_PROJECTS: \|\n((?:[ \t]+.*\n)+?)[ \t]+#|MODRINTH_PROJECTS: \|\n((?:[ \t]+.*\n)+)", text)
    block = re.search(r"MODRINTH_PROJECTS: \|\n((?:[ ]{8}.*\n)+)", text).group(1)
    out = []
    for line in block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        slug, _, ver = line.partition(":")
        out.append((slug.strip(), ver.strip() or None))
    return out


def versions(slug):
    return api("project/%s/version" % slug,
               loaders=json.dumps([LOADER]), game_versions=json.dumps([MC]))


def resolve(slug, pinned):
    vs = versions(slug)
    if pinned:
        for v in vs:
            if v["version_number"] == pinned or v["id"] == pinned:
                return v, None
        return None, "pinned version %r not found for %s/%s" % (pinned, MC, LOADER)
    rel = [v for v in vs if v["version_type"] == "release"] or vs
    if not rel:
        return None, "no version for %s/%s" % (MC, LOADER)
    return rel[0], "NOT PINNED"


def neoforge_req(url):
    """jar を落として neoforge.mods.toml の neoforge 要求レンジを読む。"""
    import tempfile
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        data = r.read()
    with tempfile.NamedTemporaryFile(suffix=".jar", delete=False) as f:
        f.write(data)
        path = f.name
    try:
        with zipfile.ZipFile(path) as z:
            toml = z.read("META-INF/neoforge.mods.toml").decode("utf-8", "replace")
    except Exception:
        return None
    finally:
        os.unlink(path)
    blocks = re.split(r"\[\[dependencies", toml)
    for b in blocks[1:]:
        if re.search(r'modId\s*=\s*"neoforge"', b):
            m = re.search(r'versionRange\s*=\s*"([^"]+)"', b)
            if m:
                return m.group(1)
    return None


def cmd_check():
    bad = 0
    for slug, pinned in parse_compose():
        v, note = resolve(slug, pinned)
        if v is None:
            print("FAIL  %-34s %s" % (slug, note)); bad += 1
        elif note:
            print("WARN  %-34s %s (resolved %s)" % (slug, note, v["version_number"])); bad += 1
        else:
            print("ok    %-34s %s" % (slug, v["version_number"]))
    print("\n%d problem(s)" % bad)
    return 1 if bad else 0


def cmd_latest():
    for slug, pinned in parse_compose():
        vs = versions(slug)
        rel = [v for v in vs if v["version_type"] == "release"] or vs
        if not rel:
            print("%-34s -- none --" % slug); continue
        newest = rel[0]["version_number"]
        flag = "" if newest == pinned else "  <-- UPDATE"
        print("%-34s pinned=%-30s latest=%s%s" % (slug, pinned, newest, flag))


def cmd_table():
    print("| MOD | Slug | 固定バージョン | Server | Client | NeoForge 要求 |")
    print("| --- | --- | --- | :---: | :---: | --- |")
    for slug, pinned in parse_compose():
        v, _ = resolve(slug, pinned)
        if v is None:
            continue
        proj = api("project/%s" % slug)
        nf = neoforge_req(v["files"][0]["url"]) or "-"
        srv = "✅" if proj["server_side"] != "unsupported" else "—"
        cli = "✅" if proj["client_side"] != "unsupported" else "—"
        print("| [%s](https://modrinth.com/mod/%s) | `%s` | `%s` | %s | %s | `%s` |"
              % (proj["title"], slug, slug, v["version_number"], srv, cli, nf))


def cmd_mrpack():
    files = []
    for slug, pinned in parse_compose() + CLIENT_ONLY:
        v, note = resolve(slug, pinned)
        if v is None:
            print("skip %s: %s" % (slug, note), file=sys.stderr); continue
        proj = api("project/%s" % slug)
        f = v["files"][0]
        files.append({
            "path": "mods/" + urllib.parse.unquote(f["url"].rsplit("/", 1)[-1]),
            "hashes": {"sha1": f["hashes"]["sha1"], "sha512": f["hashes"]["sha512"]},
            "env": {
                "client": "required" if proj["client_side"] != "unsupported" else "unsupported",
                "server": "required" if proj["server_side"] != "unsupported" else "unsupported",
            },
            "downloads": [f["url"]],
            "fileSize": f["size"],
        })
    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": "1.21.1-" + os.environ.get("PACK_VERSION", "dev"),
        "name": "mc-create-server",
        "summary": "cyokozai/mc-create-server のクライアント構成",
        "files": sorted(files, key=lambda x: x["path"]),
        "dependencies": {"minecraft": MC, "neoforge": "21.1.248"},
    }
    out_dir = os.path.join(ROOT, "client")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "mc-create.mrpack")
    notes = ["CurseForge 管理の MOD は .mrpack に含められないため、Prism で手動追加すること。", ""]
    for name, pid, fid, ver, client in CF_MANUAL:
        if client:
            notes.append("- %s  %s  (project %s / file %s)" % (name, ver, pid, fid))
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("modrinth.index.json", json.dumps(index, indent=2, ensure_ascii=False))
        z.writestr("overrides/MANUAL-CURSEFORGE.txt", "\n".join(notes))
    print("wrote %s (%d mods)" % (out, len(files)))


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    fn = {"check": cmd_check, "latest": cmd_latest,
          "mrpack": cmd_mrpack, "table": cmd_table}.get(cmd)
    if not fn:
        print(__doc__); return 2
    return fn() or 0


if __name__ == "__main__":
    sys.exit(main())
