# Running little-helper on a droplet

The collection runs unattended on a DigitalOcean droplet. A Spaces bucket is the store of record: every file `lh` commits is uploaded there and verified, and heavy files (parquet, jsonl.zst) then leave the droplet's disk. The disk holds only the clone being extracted, files waiting to upload, and small bookkeeping (cursors, git `meta.json`). How this works: [`src/little_helper/objects.py`](../src/little_helper/objects.py).

| Item | Where it lives | Notes |
|---|---|---|
| Code and environment | droplet: a checkout of this repo, built with `uv sync --frozen` | |
| Raw pages, git extracts, canonical tables, logs, manifests | Spaces bucket, under `little-helper/` | |
| Cursors (`state/`), git `meta.json` | droplet, and copied to the bucket on every save | |
| Settings | droplet: `config/local.yaml` (not committed) | |
| GitHub token | droplet: `~/.config/little-helper/github-token` | chmod 600 |
| Spaces key | droplet: `~/.aws/credentials` | chmod 600 |

Sizes measured on the slice so far: 941k commits extract to 0.15 GB, and 80k PRs plus 33k issues of raw pages take 0.12 GB. The local disk's real load is git clones, the largest about 20 GB (Kibana) in the census. Clones are deleted after extraction, and a clone never starts if it would leave less than 10 GB free (`git.reserve_free_gb` in `config/study.yaml`).

## 1. Create the bucket and the keys

1. **Space.** Create a Spaces bucket in the droplet's region. Keep it private: raw pages hold contributor logins and comment text. Don't enable the CDN or public file listing.
2. **Spaces access key.** Create one with read, write and delete access to that bucket only. You'll put it in `~/.aws/credentials` (step 3), in the usual boto3 format:
   ```ini
   [default]
   aws_access_key_id = <access key>
   aws_secret_access_key = <secret key>
   ```
3. **GitHub token.** Create a new token for this machine; don't copy the Mac's `gh` login, which has broad scopes. Use a fine-grained personal access token with *Public repositories (read-only)* access and no extra permissions. Give it at least 30 days to expire, since the census takes about two weeks. If GraphQL refuses it, a classic token with no scopes also reads public data.

## 2. Seed the bucket from the Mac (to resume rather than start over)

The slice's progress so far is on the USB drive: 20 git extracts, 80k PRs, 33k issues and the cursors. Upload it once so the droplet resumes where the Mac stopped. Skip this and the droplet starts every crawl over.

On the Mac, with the drive mounted at `/Volumes/chiikawa`, add the Spaces key to `~/.aws/credentials` under a named profile such as `[little-helper]`. Then:

```bash
export LH_S3_BUCKET=<space> LH_S3_ENDPOINT=https://<region>.digitaloceanspaces.com AWS_PROFILE=little-helper
uv run lh sync check
uv run lh sync push --dry-run | tail -3
uv run lh sync push
```

`push` uploads everything under the data directory, plus the run manifests in `data/manifests/`, and verifies each file. It is idempotent: run it again and it reports everything as already there. Without `--prune` the drive keeps its copy, which then serves as the backup.

## 3. Set up the droplet

Ubuntu 24.04 or Debian 12, at least 4 GB of RAM: the largest git extractions hold about 200k commits in memory. On a 2 GB droplet, add swap first:

```bash
fallocate -l 4G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile && echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Then, as the user who will run the collection:

```bash
git clone https://github.com/rhawrami/little-helper.git
cd little-helper
git switch collection-pipeline
LH_S3_BUCKET=<space> LH_S3_ENDPOINT=https://<region>.digitaloceanspaces.com bash deploy/bootstrap.sh
```

The `git switch` line is needed until that branch is merged into main.

The bootstrap does the following, and is safe to re-run:

- installs git, curl, tmux and uv 0.12.10
- builds the environment from `uv.lock` (Python 3.13, from `.python-version`)
- writes `config/local.yaml` from [`local.yaml.example`](local.yaml.example)
- creates an empty `~/.config/little-helper/github-token` with mode 600
- installs the `lh-collect@` systemd user service and enables linger, so the service survives logout and starts at boot
- runs the test suite

It lists what is still to do at the end. Then:

1. Log out and back in, or run `source ~/.local/bin/env`, so `uv` is on your PATH.
2. Paste the GitHub token into the token file:
   ```bash
   nano ~/.config/little-helper/github-token
   ```
3. Put the Spaces key in `~/.aws/credentials` under `[default]`, then:
   ```bash
   chmod 600 ~/.aws/credentials
   ```

## 4. Check access, pull the cursors, start

```bash
uv run lh sync check                    # writes, reads and deletes a probe object
uv run lh sync pull                     # cursors, git meta.json, derived/ selection tables
uv run lh status --set slice            # should show where the Mac stopped
uv run lh collect github zlib           # smoke test: a short refresh of a finished repo
systemctl --user enable --now lh-collect@github
```

- **`lh status`:** it should show numpy PRs at 15,635 of 19,050 and six projects complete.
- **Smoke test:** the zlib refresh proves the token works with GraphQL and that uploads land in the bucket.
- **`sync pull` is required:** collecting on a machine that hasn't synced with a non-empty bucket is refused, with a message saying to run it.

The service runs `uv run --frozen lh collect github --set slice`. When some repos fail (network, GitHub outages), it restarts five minutes later and resumes from the saved cursors. A run that finishes cleanly stops the service.

- **Git collection:** the slice's git collection is already done. For a later set, use `lh-collect@git`.
- **Another project set:**
  ```bash
  systemctl --user edit lh-collect@github
  ```
  then add `[Service]` and `Environment=LH_SET=<set>`.

## 5. Watch it

```bash
uv run lh status --set slice                          # progress and time left, per kind
journalctl --user -u lh-collect@github -f             # live output
tail -f "$(ls -t ~/lh-data/logs/github-*.log | head -1)"
df -h ~                                               # local disk
```

Logs are also uploaded to the bucket every 10 minutes, under `little-helper/logs/`.

- **Stopping is safe at any time.** `systemctl --user stop lh-collect@github` works like Ctrl-C: the open chunk is committed and the cursor saved.
- **Reboots:** after a reboot the service starts again by itself and resumes.

## 6. When the slice finishes

```bash
uv run lh normalize git --set slice
uv run lh normalize github --set slice
uv run lh plot numpy                     # data/plots/numpy-timeseries.html
```

- **Normalize** downloads each raw chunk only while reading it. The canonical tables it writes go to the bucket.
- **The plot:** to view it on the Mac:
  ```bash
  scp <droplet>:little-helper/data/plots/numpy-timeseries.html .
  ```
- **Run manifests** are written into the droplet's checkout under `data/manifests/` and uploaded to the bucket. To commit them from the Mac:
  ```bash
  scp -r <droplet>:little-helper/data/manifests/github data/manifests/
  ```

## Settings

All of these go in `config/local.yaml`. Environment variables override them.

| `local.yaml` key | Environment variable | Meaning |
|---|---|---|
| `data_dir` | `LH_DATA_DIR` | local working copy of the data |
| `work_dir` | `LH_WORK_DIR` | transient bare clones |
| `github_token_file` | `LH_GITHUB_TOKEN_FILE` | file holding the GitHub token; `GITHUB_TOKEN` takes precedence |
| `s3_bucket` | `LH_S3_BUCKET` | Space name; setting it turns object storage on |
| `s3_endpoint` | `LH_S3_ENDPOINT` | `https://<region>.digitaloceanspaces.com`. Optional if `~/.aws/config` sets `endpoint_url` |
| `s3_prefix` | `LH_S3_PREFIX` | key prefix in the bucket; default `little-helper` |
| `s3_profile` | `AWS_PROFILE` | profile in `~/.aws/credentials`; default `[default]` |
| `keep_local` | `LH_KEEP_LOCAL` | `true` keeps heavy files on disk after upload |

## Getting everything back onto a Mac or drive

```bash
LH_S3_BUCKET=<space> LH_S3_ENDPOINT=https://<region>.digitaloceanspaces.com AWS_PROFILE=little-helper \
  uv run lh sync pull --all
```

This downloads everything the local data directory is missing, verifying each file's sha256.
