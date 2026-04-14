# aws-self-hosting-ai

Personal blog + static site hosting on AWS, guided by Claude.

This repo is a template. Running `/setup` configures it as your own blog,
creates your GitHub repo, deploys the AWS infrastructure, and gets your site live.

---

## Is this a fresh clone?

Check: does `.env` exist?

```bash
ls .env 2>/dev/null && echo "configured" || echo "fresh clone — run /setup"
```

If this is a fresh clone, offer to run `/setup` and walk the user through
the complete setup. Don't assume anything is configured yet.

If `.env` exists, the user is working on their blog. Show them what they can do:

```
/draft IDEA=<title>    — move an idea into posts/ as a draft
/publish POST=<slug>   — mark a post ready to publish
/teardown              — destroy all AWS infrastructure
make dev               — local dev server → http://localhost:4321
make deploy            — build + push to S3 + invalidate CloudFront
```

---

## Prerequisites — check all of these before setup

Everything runs in Docker. The only host-machine dependencies are:

| Tool | Check | Install |
|------|-------|---------|
| Docker Desktop | `docker info` | https://www.docker.com/products/docker-desktop |
| GitHub CLI (`gh`) | `gh --version` | `brew install gh` or https://cli.github.com |
| AWS account | — | https://aws.amazon.com/free |
| Pulumi Cloud account | — | https://app.pulumi.com/signup |

`gh` can run in Docker if the user prefers not to install it locally — there's a
`gh` service in docker-compose for that. But installing locally is simpler.

---

## What gets created

```
AWS account
├── Route53 hosted zone (your domain)
├── GitHub OIDC provider (no long-lived AWS keys in CI)
├── IAM deploy role  (S3 sync + CloudFront invalidation, main branch only)
├── IAM infra role   (full site lifecycle, all branches)
├── S3 bucket        (blog content)
├── CloudFront CDN   (HTTPS, global edge)
└── ACM certificate  (auto-renewed TLS)

GitHub (your account)
└── <your-repo>      (blog content + infra code + CI/CD)

Your domain registrar
└── NS records pointing to Route53 (you do this manually, ~5 min)
```

---

## Architecture

**Two Pulumi stacks** — both live in this repo:

1. **Ingress** (`infra/pulumi-ingress/`) — Route53 zone + GitHub OIDC + shared IAM roles.
   Deploy once. All your static sites share these.

2. **Site** (`infra/pulumi/`) — S3 + CloudFront + ACM + DNS for your blog.
   References the ingress stack for zone ID and role ARNs.

**Why two stacks?** If you later add an app (e.g. `myapp.yourdomain.com`), it shares
the ingress stack — no duplicate Route53 zones or OIDC providers.

**CI/CD:** GitHub Actions uses OIDC federation to assume AWS roles. No AWS keys stored
in GitHub — only `PULUMI_ACCESS_TOKEN`.

---

## Common commands (after setup)

```bash
make dev                   # Astro dev server → http://localhost:4321
make build                 # Build to ./dist
make deploy                # Build + S3 sync + CloudFront invalidation
make infra-preview         # Preview infra changes
make infra-up              # Apply infra changes
make infra-ingress-preview # Preview ingress changes
make infra-ingress-up      # Apply ingress changes
make infra-outputs         # Show bucket + CloudFront IDs
make draft IDEA=<title>    # Graduate idea → draft post
make publish POST=<slug>   # Set draft: false + date
```

---

## Writing workflow

```
ideas/my-idea           ← stub or note
  ↓  make draft IDEA=my-idea
posts/my-idea.md        ← write here (draft: true)
  ↓  make publish POST=my-idea
posts/my-idea.md        ← draft: false, date set
  ↓  make deploy (or push to main — CI deploys automatically)
yourdomain.com/blog/my-idea  ← live
```

**Frontmatter schema:**
```yaml
---
title: "Your Title"
description: "One sentence"
date: 2026-01-01
draft: false
tags: [writing, tech]
image: /images/posts/slug.jpg   # optional hero image
---
```

---

## Adding new apps (`/new-spa`)

The ingress stack is shared. Any subdomain app you add just needs its own
Pulumi stack that references the ingress stack for `zone_id`. Run `/new-spa`
to scaffold a new SPA with its own GitHub repo, infra, and CI/CD.

---

## Phone-based blogging (Claude Dispatch)

With Claude Desktop on your Mac and Claude on your phone:
1. Pair them in Claude settings (takes 2 min)
2. Open Claude on your phone
3. Say "I have an idea for a post about X — can you draft it?"
4. Claude can draft, edit, run `make publish`, and push to GitHub — all from your phone

---

## Three Musketeers pattern

All commands run in Docker — no tools installed on the host (except Docker + gh).
`make <target>` → `docker compose run --rm <service> <command>`

Secrets flow: `.env` → docker-compose `env_file` → container env vars.
CI: GitHub Actions injects secrets directly; no `.env` file needed.
