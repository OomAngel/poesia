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
sops -d secrets/poesia.env.sops.yaml > .env
```

The age key is the machine key at `~/.config/sops/age/keys.txt` (back it up).
