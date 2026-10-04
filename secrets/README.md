# Encrypted Secrets

This directory stores the encrypted credential transport file for poesia.

Tracked files may include:

- `poesia.env.sops.yaml` — Cloudflare + LLM provider + postgres (MLflow) creds
- `poesia.env.template.yaml`
- `README.md`

Do not commit plaintext `.env`, `.yaml`, or `.yml` files here. Use `sops` to edit
encrypted values:

```bash
sops secrets/poesia.env.sops.yaml
```

For headless runs, decrypt into the gitignored repo-root `.env`:

```bash
sops -d --output-type dotenv secrets/poesia.env.sops.yaml > .env
```

The age key at `~/.config/sops/age/keys.txt` is the same key for every repository; a
recovery key is the second recipient. How to get it onto a new machine: `LOCAL_ONLY.md`
"Secrets on another machine".
