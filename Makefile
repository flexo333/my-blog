.DEFAULT_GOAL := help

# ── Load .env into Make ───────────────────────────────────────────────────────
ifneq (,$(wildcard .env))
  include .env
  export
endif

# GitHub Actions sets CI=true → skips confirmation prompts
PULUMI_YES := $(if $(CI),--yes,)

# ── Help ──────────────────────────────────────────────────────────────────────
.PHONY: help
help: ## Show available targets
	@grep -E '^[a-zA-Z_/-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2}'

# ── Site ──────────────────────────────────────────────────────────────────────
.PHONY: install
install: ## Install npm dependencies
	docker compose run --rm node npm install

.PHONY: dev
dev: ## Start Astro dev server → http://localhost:4321
	docker compose up node-dev

.PHONY: build
build: ## Build Astro site to ./dist
	docker compose run --rm node npm run build

# ── Writing workflow ──────────────────────────────────────────────────────────
.PHONY: draft
draft: ## Graduate an idea → posts/ draft. Usage: make draft IDEA=my-idea
	@test -n "$(IDEA)" || (echo "❌  IDEA not set. Usage: make draft IDEA=idea-slug" && exit 1)
	@test ! -f posts/$(IDEA).md || (echo "❌  posts/$(IDEA).md already exists" && exit 1)
	@if [ -f ideas/$(IDEA).md ]; then \
		mv ideas/$(IDEA).md posts/$(IDEA).md; \
		echo "✅  Moved ideas/$(IDEA).md → posts/$(IDEA).md"; \
	elif [ -f ideas/$(IDEA) ]; then \
		mv ideas/$(IDEA) posts/$(IDEA).md; \
		echo "✅  Moved ideas/$(IDEA) → posts/$(IDEA).md"; \
	else \
		touch posts/$(IDEA).md; \
		echo "✅  Created posts/$(IDEA).md"; \
	fi; \
	if ! head -1 posts/$(IDEA).md | grep -q '^---'; then \
		TITLE=$$(echo "$(IDEA)" | sed 's/-/ /g' | awk '{for(i=1;i<=NF;i++) $$i=toupper(substr($$i,1,1)) tolower(substr($$i,2)); print}'); \
		{ printf -- '---\ntitle: "%s"\ndescription: ""\ndraft: true\ntags: []\n---\n\n' "$$TITLE"; cat posts/$(IDEA).md; } > posts/$(IDEA).md.tmp \
			&& mv posts/$(IDEA).md.tmp posts/$(IDEA).md; \
		echo "   Frontmatter added (title: \"$$TITLE\", draft: true)"; \
	fi

.PHONY: publish
publish: ## Mark a post as published. Usage: make publish POST=my-post
	@test -n "$(POST)" || (echo "❌  POST not set. Usage: make publish POST=post-slug" && exit 1)
	docker compose run --rm node node scripts/publish.mjs $(POST)

.PHONY: generate-image
generate-image: ## Generate a DALL-E 3 hero image. Usage: make generate-image POST=my-post
	@test -n "$(POST)"           || (echo "❌  POST not set. Usage: make generate-image POST=post-slug" && exit 1)
	@test -n "$(OPENAI_API_KEY)" || (echo "❌  OPENAI_API_KEY not set in .env" && exit 1)
	docker compose run --rm node node scripts/generate-image.mjs $(POST)

# ── Pulumi — ingress (Route53 zone, OIDC, CI roles) ──────────────────────────
.PHONY: infra-ingress-preview
infra-ingress-preview: ## Preview ingress infra changes
	docker compose build pulumi-ingress
	docker compose run --rm pulumi-ingress preview

.PHONY: infra-ingress-up
infra-ingress-up: ## Apply ingress infra changes
	docker compose build pulumi-ingress
	docker compose run --rm pulumi-ingress up $(PULUMI_YES)

.PHONY: infra-ingress-destroy
infra-ingress-destroy: ## Destroy ingress infra ⚠️  careful
	docker compose run --rm pulumi-ingress destroy $(PULUMI_YES)

.PHONY: infra-ingress-outputs
infra-ingress-outputs: ## Show ingress outputs (nameservers, role ARNs)
	docker compose run --rm pulumi-ingress stack output

# ── Pulumi — site (S3 + CloudFront) ──────────────────────────────────────────
.PHONY: infra-preview
infra-preview: ## Preview site infra changes
	docker compose build pulumi
	docker compose run --rm pulumi preview

.PHONY: infra-up
infra-up: ## Apply site infra changes
	docker compose build pulumi
	docker compose run --rm pulumi up $(PULUMI_YES)

.PHONY: infra-destroy
infra-destroy: ## Destroy site infra ⚠️  careful
	docker compose run --rm pulumi destroy $(PULUMI_YES)

.PHONY: infra-outputs
infra-outputs: ## Show site stack outputs (bucket name, CF distribution ID)
	docker compose run --rm pulumi stack output

# ── Deploy ────────────────────────────────────────────────────────────────────
.PHONY: deploy
deploy: build ## Build + sync to S3 + invalidate CloudFront
	@BUCKET=$${SITE_BUCKET:-$$(docker compose run --rm -T pulumi stack output portfolio_bucket 2>/dev/null | tail -1)}; \
	CFID=$${CF_DISTRIBUTION_ID:-$$(docker compose run --rm -T pulumi stack output portfolio_distribution_id 2>/dev/null | tail -1)}; \
	test -n "$$BUCKET" || { echo "❌  Could not determine SITE_BUCKET — run 'make infra-up' first"; exit 1; }; \
	test -n "$$CFID"   || { echo "❌  Could not determine CF_DISTRIBUTION_ID — run 'make infra-up' first"; exit 1; }; \
	echo "→ Deploying to $$BUCKET (CF: $$CFID)"; \
	docker compose run --rm awscli s3 sync /app/dist/ s3://$$BUCKET --delete --exclude '.DS_Store'; \
	docker compose run --rm awscli cloudfront create-invalidation --distribution-id $$CFID --paths '/*'

# ── GitHub CLI (Docker fallback) ──────────────────────────────────────────────
.PHONY: gh
gh: ## Run gh CLI via Docker. Usage: make gh ARGS='repo list'
	docker compose run --rm gh gh $(ARGS)
