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

## 2. Start fresh, or carry over the Mac's progress

**The plan for the slice is to start fresh on the droplet**, so every run comes from one machine, one token and one version of the code. That costs about 8 hours of GitHub crawling the Mac had already done, and an hour or two of git. Skip to step 3.

The Mac's partial run stays on the USB drive as the record of the pilot. Its manifests are committed in `data/manifests/`. Don't push the drive's data to the droplet's prefix: the bucket would then hold two sets of runs for the same repos. Normalize would still give the right answer, since it keeps the latest version of each item, but the record of where each file came from gets muddled. To keep a copy of the drive in the bucket, give it its own prefix. On the Mac, with the drive mounted and the Spaces key in `~/.aws/credentials` under a profile such as `[little-helper]`:

```bash
export LH_S3_BUCKET=<space> LH_S3_ENDPOINT=https://<region>.digitaloceanspaces.com AWS_PROFILE=little-helper
LH_S3_PREFIX=little-helper-mac uv run lh sync push
```

**To resume the Mac's run instead:** push to the default prefix (`uv run lh sync push`, without `LH_S3_PREFIX`), then run `uv run lh sync pull` on the droplet before anything else in step 4. `push` uploads everything under the data directory, plus the run manifests, and verifies each file. It is idempotent. Without `--prune` the drive keeps its copy.

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

## 4. Check access, smoke test, start

```bash
uv run lh sync check                    # writes, reads and deletes a probe object
uv run lh collect github zlib           # smoke test: zlib's full pass, a few minutes
uv run lh status --set slice            # zlib done; the other 19 projects at 0
systemctl --user enable --now lh-collect@git lh-collect@github
```

- **Smoke test:** zlib is 744 PRs and 616 issues. It proves the token works with GraphQL and that uploads land in the bucket. The Space's file browser in the control panel then shows `little-helper/raw/github/...`.
- **First run:** with an empty bucket, the first collect makes the droplet the starting point. `lh sync pull` is needed only when resuming from a bucket that already holds data. Without it, collecting is refused with a message saying to run it.
- **Both services can run at once.** Git clones don't compete with the GitHub crawl for bandwidth on a droplet.

| Service | Runs | Time |
|---|---|---|
| `lh-collect@git` | `lh collect git --set slice` | 20 repos, about 10.6 GB downloaded, an hour or two |
| `lh-collect@github` | `lh collect github --set slice` | about 190k PRs and 65k issues at 10–13k PRs and about 40k issues an hour, so roughly 17–21 hours |

When some repos fail (network, GitHub outages), a service restarts five minutes later and resumes from the saved cursors. A run that finishes cleanly exits and the service stops.

Never run `lh collect github` by hand while `lh-collect@github` is running. GitHub expects one stream of requests per token.

To collect another project set:

```bash
systemctl --user edit lh-collect@github
```

then add `[Service]` and `Environment=LH_SET=<set>`.

## 5. Watch it

```bash
uv run lh status --set slice                          # progress and time left, per kind
journalctl --user -u lh-collect@github -f             # live output (or lh-collect@git)
systemctl --user status lh-collect@git lh-collect@github
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
