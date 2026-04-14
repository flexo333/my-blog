# /new-spa — Deploy a new app at a subdomain

**SPA = Single Page App** — a self-contained web app served as static files (HTML, CSS, JS).
No server required. Loads in the browser, runs entirely client-side. Great for tools,
portfolio pieces, side projects, dashboards, or anything you want to put on the web quickly.

This command scaffolds a Hello World SPA at `<subdomain>.<your-domain>`, creates its own
GitHub repo, wires up CI/CD, sets the `PULUMI_ACCESS_TOKEN` secret, and deploys the AWS
infrastructure. It shares the ingress stack (Route53 zone + OIDC + IAM roles) already
deployed by `/setup` — no duplicate DNS zones or IAM setup needed.

**Arguments:** $ARGUMENTS (optional subdomain name, e.g. `/new-spa myapp`)

---

## Step 0 — Check setup is complete

Read `.env` and `infra/pulumi-ingress/Pulumi.prod.yaml` to find:
- DOMAIN (the root domain from ingress config)
- GITHUB_OWNER (from `Pulumi.prod.yaml` githubOwner)
- PULUMI_ORG (from the stack reference in `infra/pulumi/__main__.py`)
- AWS_DEFAULT_REGION (from `.env`)
- BUCKET_PREFIX (from ingress config bucketPrefix)

If any are missing, tell the user to run `/setup` first.

Verify ingress is deployed:
```bash
make infra-ingress-outputs
```

---

## Step 1 — Collect config

**a) App name / subdomain**
If `$ARGUMENTS` was provided, use it as the subdomain. Otherwise ask:
"What subdomain do you want? (e.g. `myapp` → `myapp.<DOMAIN>`)"

Validate: lowercase letters, numbers, hyphens only. No dots.
Store as APP_NAME. The full domain is `<APP_NAME>.<DOMAIN>`.

**b) GitHub repo name**
"GitHub repo name? (default: <APP_NAME>)"
Store as SPA_REPO.

**c) Description**
"One sentence description of this app?"
Store as SPA_DESC.

**d) Private or public repo?**
"Public or private GitHub repo? (default: public)"

---

## Step 2 — Create the SPA directory

Create a new directory `../<APP_NAME>/` (sibling to the blog repo):

```bash
mkdir -p ../<APP_NAME>/{infra/pulumi,.github/workflows}
```

---

## Step 3 — Scaffold the Hello World SPA

Create `../<APP_NAME>/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><APP_NAME></title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      background: #f5f5f5;
    }
    .card {
      background: white;
      padding: 2rem 3rem;
      border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.08);
      text-align: center;
    }
    h1 { margin: 0 0 0.5rem; font-size: 1.8rem; }
    p  { color: #666; margin: 0; }
  </style>
</head>
<body>
  <div class="card">
    <h1>👋 Hello from <APP_NAME></h1>
    <p><SPA_DESC></p>
  </div>
</body>
</html>
```

---

## Step 4 — Scaffold infra

Create `../<APP_NAME>/infra/pulumi/__main__.py`:
```python
"""
<APP_NAME> — <APP_NAME>.<DOMAIN>
S3 + CloudFront SPA, shares ingress stack (Route53 zone + OIDC + IAM roles).
"""

import pulumi
from pulumi_static_site import StaticSite

config = pulumi.Config()
domain = config.get("domain") or "<APP_NAME>.<DOMAIN>"

ingress = pulumi.StackReference("<PULUMI_ORG>/<GITHUB_OWNER>-ingress/prod")
zone_id = ingress.get_output("zone_id")

site = StaticSite(
    "<APP_NAME>",
    domain=domain,
    zone_id=zone_id,
    bucket_name="<BUCKET_PREFIX><APP_NAME>",
    spa_mode=True,
)

pulumi.export("bucket", site.bucket_name)
pulumi.export("distribution_id", site.distribution_id)
pulumi.export("cloudfront_domain", site.distribution_domain.apply(lambda d: f"https://{d}"))
pulumi.export("aws_region", pulumi.Config("aws").require("region"))
```

Create `../<APP_NAME>/infra/pulumi/Pulumi.yaml`:
```yaml
name: <GITHUB_OWNER>-<APP_NAME>
runtime: python
description: <APP_NAME> SPA — <APP_NAME>.<DOMAIN>
```

Create `../<APP_NAME>/infra/pulumi/Pulumi.prod.yaml`:
```yaml
config:
  aws:region: <AWS_REGION>
  <GITHUB_OWNER>-<APP_NAME>:domain: <APP_NAME>.<DOMAIN>
```

Create `../<APP_NAME>/infra/pulumi/requirements.txt`:
```
pulumi>=3.0.0,<4.0.0
pulumi-aws>=6.0.0,<7.0.0
pulumi-static-site @ git+https://github.com/lukerohde/pulumi-static-site.git@v0.1.0
```

Create `../<APP_NAME>/infra/pulumi/Dockerfile`:
Copy the Dockerfile from `infra/pulumi/Dockerfile` in the blog repo.

---

## Step 5 — Scaffold Makefile and docker-compose

Create `../<APP_NAME>/Makefile`:
```makefile
.DEFAULT_GOAL := help

ifneq (,$(wildcard .env))
  include .env
  export
endif

PULUMI_YES := $(if $(CI),--yes,)

.PHONY: help
help:
	@grep -E '^[a-zA-Z_/-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-24s\033[0m %s\n", $$1, $$2}'

.PHONY: infra-preview
infra-preview: ## Preview infra changes
	docker compose build pulumi
	docker compose run --rm pulumi preview

.PHONY: infra-up
infra-up: ## Apply infra changes
	docker compose build pulumi
	docker compose run --rm pulumi up $(PULUMI_YES)

.PHONY: infra-destroy
infra-destroy: ## Destroy infra ⚠️  careful
	docker compose run --rm pulumi destroy $(PULUMI_YES)

.PHONY: infra-outputs
infra-outputs: ## Show stack outputs
	docker compose run --rm pulumi stack output

.PHONY: deploy
deploy: ## Sync to S3 + invalidate CloudFront
	@BUCKET=$${BUCKET:-$$(docker compose run --rm -T pulumi stack output bucket 2>/dev/null | tail -1)}; \
	CFID=$${CF_DISTRIBUTION_ID:-$$(docker compose run --rm -T pulumi stack output distribution_id 2>/dev/null | tail -1)}; \
	test -n "$$BUCKET" || { echo "❌  Run 'make infra-up' first"; exit 1; }; \
	echo "→ Deploying to $$BUCKET"; \
	docker compose run --rm awscli s3 sync /app/ s3://$$BUCKET --delete \
		--exclude '.git/*' --exclude 'infra/*' --exclude '.env' --exclude '*.DS_Store'; \
	docker compose run --rm awscli cloudfront create-invalidation \
		--distribution-id $$CFID --paths '/*'
```

Create `../<APP_NAME>/docker-compose.yml`:
```yaml
services:
  pulumi:
    build: ./infra/pulumi
    working_dir: /infra
    volumes:
      - ./infra/pulumi:/infra
      - pulumi_plugins:/root/.pulumi/plugins
    env_file:
      - path: .env
        required: false
    environment:
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-}
      AWS_SESSION_TOKEN: ${AWS_SESSION_TOKEN:-}
      PULUMI_ACCESS_TOKEN: ${PULUMI_ACCESS_TOKEN:-}
      PULUMI_STACK: ${PULUMI_STACK:-prod}

  awscli:
    image: amazon/aws-cli:2.17.0
    volumes:
      - .:/app
    working_dir: /app
    env_file:
      - path: .env
        required: false
    environment:
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID:-}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY:-}
      AWS_SESSION_TOKEN: ${AWS_SESSION_TOKEN:-}
      AWS_DEFAULT_REGION: ${AWS_DEFAULT_REGION:-}

volumes:
  pulumi_plugins:
```

---

## Step 6 — Scaffold CI/CD workflows

Create `../<APP_NAME>/.github/workflows/deploy-infra.yml`:
```yaml
name: Deploy Infrastructure

on:
  push:
    branches: [main]
    paths: ["infra/pulumi/**"]
  pull_request:
    paths: ["infra/pulumi/**"]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    name: Infra ${{ github.event_name == 'pull_request' && 'Preview' || 'Up' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pulumi/setup-pulumi@v2

      - name: Get infra role
        id: roles
        env:
          PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}
        run: |
          pulumi login
          echo "INFRA_ROLE_ARN=$(pulumi stack output infra_role_arn -s <PULUMI_ORG>/<GITHUB_OWNER>-ingress/prod)" >> $GITHUB_OUTPUT
          echo "AWS_REGION=$(pulumi stack output aws_region -s <PULUMI_ORG>/<GITHUB_OWNER>-ingress/prod)" >> $GITHUB_OUTPUT

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ steps.roles.outputs.INFRA_ROLE_ARN }}
          aws-region: ${{ steps.roles.outputs.AWS_REGION }}

      - name: Preview
        env:
          PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}
        run: make infra-preview

      - name: Apply
        if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'
        env:
          PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}
        run: make infra-up
```

Create `../<APP_NAME>/.github/workflows/deploy-site.yml`:
```yaml
name: Deploy Site

on:
  push:
    branches: [main]
    paths: ["index.html", "*.css", "*.js", "public/**"]
  workflow_dispatch:

permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pulumi/setup-pulumi@v2

      - name: Get config
        id: config
        env:
          PULUMI_ACCESS_TOKEN: ${{ secrets.PULUMI_ACCESS_TOKEN }}
        run: |
          pulumi login
          echo "DEPLOY_ROLE_ARN=$(pulumi stack output deploy_role_arn -s <PULUMI_ORG>/<GITHUB_OWNER>-ingress/prod)" >> $GITHUB_OUTPUT
          echo "BUCKET=$(pulumi stack output bucket -s <PULUMI_ORG>/<GITHUB_OWNER>-<APP_NAME>/prod)" >> $GITHUB_OUTPUT
          echo "CF_DISTRIBUTION_ID=$(pulumi stack output distribution_id -s <PULUMI_ORG>/<GITHUB_OWNER>-<APP_NAME>/prod)" >> $GITHUB_OUTPUT
          echo "AWS_REGION=$(pulumi stack output aws_region -s <PULUMI_ORG>/<GITHUB_OWNER>-<APP_NAME>/prod)" >> $GITHUB_OUTPUT

      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ steps.config.outputs.DEPLOY_ROLE_ARN }}
          aws-region: ${{ steps.config.outputs.AWS_REGION }}

      - name: Deploy
        env:
          BUCKET: ${{ steps.config.outputs.BUCKET }}
          CF_DISTRIBUTION_ID: ${{ steps.config.outputs.CF_DISTRIBUTION_ID }}
        run: make deploy
```

---

## Step 7 — Copy .env from blog repo

```bash
cp .env ../<APP_NAME>/.env
```

The SPA uses the same AWS credentials and PULUMI_ACCESS_TOKEN.

---

## Step 8 — Deploy the SPA infrastructure

```bash
cd ../<APP_NAME>
make infra-up
```

Takes 5-10 minutes.

---

## Step 9 — Create GitHub repo and push

```bash
cd ../<APP_NAME>
git init
git add -A
git commit -m "Initial <APP_NAME> SPA"
gh repo create <GITHUB_OWNER>/<SPA_REPO> --public --description "<SPA_DESC>" --source=. --remote=origin

PULUMI_TOKEN=$(grep PULUMI_ACCESS_TOKEN .env | cut -d= -f2)
gh secret set PULUMI_ACCESS_TOKEN --body "$PULUMI_TOKEN" --repo <GITHUB_OWNER>/<SPA_REPO>

git push -u origin main
```

---

## Step 10 — First deploy and verification

```bash
make deploy
```

Show them:
```
✅  <APP_NAME> is live!

CloudFront URL (immediate): <cloudfront-domain>
Your subdomain (after DNS): https://<APP_NAME>.<DOMAIN>

DNS should propagate within a few minutes since Route53
already controls your zone.

To update the app:
  edit index.html → git push → CI deploys automatically
  or: make deploy  (deploys immediately from local)

To destroy this app's infra:
  make infra-destroy  (run from ../<APP_NAME>/)
```
