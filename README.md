# aws-self-hosting-ai

Personal blog on AWS, set up and managed by Claude.

**~$1–2/month.** No subscriptions, no platform lock-in. You own everything.

```bash
git clone https://github.com/lukerohde/aws-self-hosting-ai my-blog
cd my-blog
claude
```

Claude walks you through the complete setup and gets your blog live.

---

## Cost

This runs on AWS pay-per-use services. For a typical personal blog:

| Service | Cost |
|---------|------|
| Route53 hosted zone | $0.50/month |
| S3 storage | ~$0.02/month |
| CloudFront CDN | free (1TB/month free tier) |
| ACM TLS certificate | free |
| **Total** | **~$1/month** |

Compare that to Substack (takes a cut of paid subscriptions), Ghost Pro ($9–25/month),
or Medium (you don't own your audience). Here you pay for the infrastructure directly —
no middleman, no lock-in, full control.

If you add subdomain apps later (a side project, a tool, a portfolio piece), each one
adds ~$0.50/month for its S3 bucket and CloudFront distribution. The Route53 zone and
CI roles are shared — you pay for those once regardless of how many sites you run.

---

## What you'll end up with

- Blog at your own domain (e.g. `will.dev`)
- S3 + CloudFront CDN + HTTPS with auto-renewed certificates
- GitHub CI/CD — push to main → deploys in ~2 minutes
- No AWS keys stored in GitHub (OIDC federation — CI assumes a role via a short-lived token)
- Expandable — add apps at subdomains without duplicating any infrastructure
- Everything runs in Docker — no tools to install on your machine beyond Docker and Claude

---

## Architecture

This is the part worth understanding, because it shapes everything else.

### Two stacks, not one

Infrastructure is split into two Pulumi stacks:

```
┌─────────────────────────────────────────────────────┐
│  Ingress stack  (infra/pulumi-ingress/)              │
│                                                      │
│  Route53 hosted zone  — authoritative DNS            │
│  GitHub OIDC provider — CI identity, no keys         │
│  IAM deploy role      — S3 sync + CF invalidation    │
│  IAM infra role       — full site lifecycle (PRs)    │
└──────────────────────┬──────────────────────────────┘
                       │  shared by all sites
          ┌────────────┴────────────┐
          ▼                         ▼
┌──────────────────┐     ┌──────────────────────────┐
│  Site stack      │     │  Any future app stack     │
│  (infra/pulumi/) │     │  e.g. myapp.yourdomain    │
│                  │     │                           │
│  S3 bucket       │     │  S3 bucket                │
│  CloudFront CDN  │     │  CloudFront CDN            │
│  ACM certificate │     │  ACM certificate           │
│  DNS record      │     │  DNS record               │
└──────────────────┘     └──────────────────────────┘
```

**Why separate?** The ingress stack is the shared foundation. It creates your Route53 DNS zone
(the authoritative source for your domain) and the GitHub OIDC provider (which lets CI deploy
without storing AWS credentials). You deploy this once and it rarely changes.

The site stack — and any future app stack — is lightweight by comparison. It just creates an
S3 bucket, a CloudFront distribution, and a certificate, then creates a DNS record in the
zone the ingress stack owns. Each site is independent: you can tear one down without touching
the others, and deploying a new site doesn't require touching the ingress stack at all.

### Adding new apps

When you want to deploy something at `myapp.yourdomain.com`, run `/new-spa`. Claude:
- Creates a new GitHub repo for the app
- Scaffolds a Hello World SPA with its own Makefile, Docker setup, and CI/CD
- Creates a new Pulumi stack that references your ingress stack for the zone ID
- Deploys it — your app is live at the subdomain in ~10 minutes

The DNS zone and OIDC roles cost nothing extra. The new app adds ~$0.50/month.

### CI/CD without AWS keys

GitHub Actions never stores your AWS access key. Instead:
1. When a workflow runs, GitHub mints a short-lived OIDC token proving "this is repo X, branch Y"
2. The workflow exchanges that token for temporary AWS credentials by assuming the deploy or infra role
3. The role's trust policy only allows assumption from your specific GitHub username — nobody else can use it

The only secret stored in GitHub is `PULUMI_ACCESS_TOKEN` (for Pulumi Cloud state).

---

## Prerequisites

| Tool | Install |
|------|---------|
| Docker Desktop | https://www.docker.com/products/docker-desktop |
| Claude Code | https://claude.ai/download |
| GitHub CLI (`gh`) | `brew install gh` or https://cli.github.com |
| GitHub account | https://github.com |
| AWS account | https://aws.amazon.com/free |
| Pulumi Cloud account | https://app.pulumi.com/signup (free) |
| A domain name | Claude can buy one for you — see below |

`gh` is required — it creates your GitHub repo, sets CI secrets, and handles auth. If it's
not installed when you run `/setup`, Claude will offer to install it via Homebrew.

### Getting a domain

Claude can **check availability and buy a domain via AWS Route53** during `/setup` —
just say you don't have one yet. Route53 purchases automatically wire up DNS,
skipping the manual nameserver step entirely.

If you already have a domain at another registrar, that works too. You'll point its
nameservers at Route53 during setup (a ~5 minute manual step).

---

## After setup

```bash
make dev                   # local dev server → http://localhost:4321
make draft IDEA=my-idea    # start a new post
make publish POST=my-post  # mark post ready to publish
make deploy                # build + push to S3 + invalidate CDN

# Claude commands (run: claude)
/edit my-post              # feedback, sanitising, editing
/draft my-idea             # AI-assisted drafting
/publish my-post           # publish with one command
/new-spa                   # add a new app at a subdomain
/teardown                  # destroy all AWS infrastructure
```

## Phone-based blogging

With Claude Desktop on your Mac and Claude on iOS/Android:
1. Pair them in Claude settings (2 minutes)
2. Open Claude on your phone
3. "I have an idea for a post about X — can you draft it?"
4. Claude drafts it, you review on your phone, say "looks good, publish it"
5. Claude runs `make publish` + `git push` — your post is live

## Teardown

```bash
/teardown           # guided — confirms before destroying anything

# or manually:
make infra-destroy          # site stack first
make infra-ingress-destroy  # then ingress (deletes DNS zone + OIDC)
```

Your code and posts are never deleted — only the AWS resources.
