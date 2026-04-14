# /setup — Full blog setup wizard

Walk the user through setting up their blog from this template. By the end they will have:
- A live blog at their domain
- GitHub repo with CI/CD
- AWS infrastructure (S3, CloudFront, Route53, OIDC)
- Pulumi Cloud managing state

**Important:** Be conversational. Explain WHY each step matters, not just what to do.
Check actual state before asking — don't ask if Docker is installed if `docker info` already works.

---

## Step 0 — Orient the user

Start by printing this overview so they know what's coming:

```
Here's what we'll do together:

  1. ✅  Check prerequisites (Docker, gh CLI, AWS, Pulumi)
  2. 🔑  Set up AWS credentials
  3. ☁️   Set up Pulumi Cloud
  4. 🌐  Collect your config (domain, GitHub username, etc.)
  5. 🏗️   Deploy AWS ingress (Route53 zone + GitHub OIDC + IAM roles)
  6. 📡  Delegate nameservers at your registrar  ← you do this bit
  7. 🚀  Deploy blog infrastructure (S3 + CloudFront + HTTPS)
  8. 📦  Create your GitHub repo
  9. 🔐  Set CI secret (PULUMI_ACCESS_TOKEN)
  10. ✍️   Add your first content (photo, about, projects, first post idea)
  11. 🌍  Push to GitHub → CI deploys → your blog is live

Each step is reversible. If anything goes wrong, we can fix it.
Run /teardown at any time to destroy the AWS infrastructure.
```

---

## Step 1 — Check prerequisites

Run these checks and report clearly what's missing:

```bash
# Docker
docker info > /dev/null 2>&1 && echo "✅ Docker" || echo "❌ Docker not running"

# gh CLI — required for repo creation and secret management
gh --version 2>/dev/null && echo "✅ gh CLI" || echo "❌ gh CLI not found"

# AWS CLI (runs in Docker — always available)
docker compose run --rm awscli aws --version 2>/dev/null && echo "✅ AWS CLI (Docker)" || echo "❌ AWS CLI (Docker) — is Docker running?"
```

**If Docker is not running:** Stop. Ask the user to start Docker Desktop and try again.

**If gh CLI is missing:**
`gh` is required — it creates the GitHub repo and sets CI secrets. Offer to install it:

```bash
# macOS
brew install gh

# Linux
(type -p wget >/dev/null || (sudo apt update && sudo apt-get install wget -y)) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  && cat $out | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
  && sudo apt update && sudo apt install gh -y
```

Or direct them to https://cli.github.com for Windows or other platforms.

After installation, verify: `gh --version`

Continue once both Docker and gh are confirmed.

---

## Step 2 — GitHub authentication

```bash
# Check if already authenticated
gh auth status 2>/dev/null && echo "✅ gh authenticated" || echo "⚠️  Not authenticated"
```

If not authenticated, run:
```bash
gh auth login
```

Walk them through the browser OAuth flow. After login:
```bash
gh api user --jq '.login'   # confirm username
```

Store the GitHub username — you'll need it in Step 4.

---

## Step 3 — AWS credentials

**Why:** The initial infra deployment (ingress stack) runs locally and needs AWS credentials
with admin-level permissions. After setup, CI uses OIDC — no keys needed.

Check if credentials exist:
```bash
docker compose run --rm awscli aws sts get-caller-identity 2>/dev/null
```

**If credentials work:** Great. Note the account ID for them.

**If not configured:** Guide them through creating an IAM user:

```
To create AWS credentials:

1. Open https://console.aws.amazon.com/iam/
2. Go to Users → Create user
3. Username: blog-admin (or anything you like)
4. Attach policy: AdministratorAccess
   (This is your personal blog. Full access is appropriate.)
5. After creating: Security credentials tab → Create access key
6. Use case: "Local code" → Next → Create
7. Download the CSV or copy the Access Key ID and Secret Access Key
```

Ask for the keys, then write them to `.env`:
```bash
cat >> .env << 'EOF'
AWS_ACCESS_KEY_ID=<their key>
AWS_SECRET_ACCESS_KEY=<their secret>
EOF
```

Verify:
```bash
docker compose run --rm awscli aws sts get-caller-identity
```

Show them their account ID. Explain: "This is the AWS account your blog will live in."

---

## Step 4 — Pulumi Cloud setup

**Why:** Pulumi Cloud stores your infrastructure state (what's deployed, resource IDs, etc.)
It's free for personal use. Think of it like a database for your infrastructure.

Check:
```bash
# PULUMI_ACCESS_TOKEN in .env?
grep -q PULUMI_ACCESS_TOKEN .env 2>/dev/null && echo "✅ token found" || echo "⚠️  not set"
```

**If not set:**

```
To create a Pulumi Cloud account and access token:

1. Go to https://app.pulumi.com/signup
2. Sign up (GitHub login is easiest)
3. Your org name = your username (e.g. "will" if you signed up as "will")
   Note: you can use your domain name as org name if you like — but they're independent.
4. After signup: click your avatar → Access Tokens → Create token
5. Name: "blog-deploy" → Create → Copy the token
```

Ask for the token and org name. Write to `.env`:
```
PULUMI_ACCESS_TOKEN=<their token>
```

Verify:
```bash
docker compose run --rm pulumi-ingress pulumi whoami
```

---

## Step 5 — Collect configuration

Ask these questions. Explain each one:

**a) Domain name**
"What domain will your blog live at? (e.g. will.dev, myname.com)"

If they say they don't have a domain yet, or aren't sure:

**Offer to find and buy one via AWS Route53 — the most seamless option since you're already here.**

Ask: "Got a name in mind? I can check if it's available and buy it for you right now using your AWS credentials."

If they give a name, check availability:
```bash
docker compose run --rm awscli aws route53domains check-domain-availability \
  --domain-name <their-domain> --region us-east-1
```

If `AVAILABLE`:
  - Get the price:
    ```bash
    docker compose run --rm awscli aws route53domains list-prices \
      --tld <tld> --region us-east-1 --query 'Prices[0].RegistrationPrice'
    ```
  - Show them: "✅ <domain> is available — $X/year. Want me to register it?"
  - If yes, collect the required contact details (Route53 needs these for WHOIS):
    - First name, last name
    - Email address
    - Phone number (format: +1.2025551234)
    - Street address, city, state/province, postal code, country code (e.g. AU, US, GB)
  - Register it:
    ```bash
    docker compose run --rm awscli aws route53domains register-domain \
      --domain-name <domain> \
      --duration-in-years 1 \
      --auto-renew \
      --admin-contact 'FirstName=<>,LastName=<>,ContactType=PERSON,OrganizationName="",AddressLine1=<>,City=<>,State=<>,CountryCode=<>,ZipCode=<>,PhoneNumber=<>,Email=<>' \
      --registrant-contact 'FirstName=<>,LastName=<>,ContactType=PERSON,OrganizationName="",AddressLine1=<>,City=<>,State=<>,CountryCode=<>,ZipCode=<>,PhoneNumber=<>,Email=<>' \
      --tech-contact 'FirstName=<>,LastName=<>,ContactType=PERSON,OrganizationName="",AddressLine1=<>,City=<>,State=<>,CountryCode=<>,ZipCode=<>,PhoneNumber=<>,Email=<>' \
      --privacy-protect-admin-contact \
      --privacy-protect-registrant-contact \
      --privacy-protect-tech-contact \
      --region us-east-1
    ```
    Note: `--privacy-protect-*` flags are strongly recommended — they hide your contact details from public WHOIS lookups.
  - Registration takes a few minutes. AWS will send a confirmation email.
  - **Skip the nameserver delegation step later** — AWS automatically creates a Route53 hosted zone and sets NS records when you buy a domain through Route53. Just confirm the zone exists after purchase.

If `UNAVAILABLE`:
  - Suggest variations: try different TLDs (.dev, .io, .net), hyphenated versions, or slightly different names
  - Let them pick and check again

If they already have a domain at another registrar:
  - That's fine — they'll delegate NS records to Route53 in Step 8 (5-minute manual step)
  - If they're at GoDaddy or Squarespace, warn that NS changes can be buried in their UI
  - Namecheap and most others are straightforward

After they choose/confirm, store as DOMAIN.

**b) GitHub username**
Already known from Step 2 — confirm it. Store as GITHUB_OWNER.

**c) GitHub repo name**
"What do you want to call your blog repo on GitHub? (default: my-blog)"
This will be `github.com/<username>/<repo-name>`. Store as REPO_NAME.

**d) Pulumi org**
Already known from Step 4. Store as PULUMI_ORG.

**e) AWS region**
"Which AWS region? (default: us-east-1)"
- us-east-1 (N. Virginia) — cheapest, good global performance
- eu-west-1 (Ireland) — best for European audiences  
- ap-southeast-2 (Sydney) — best for Australian audiences
Store as AWS_REGION.

**f) Blog author name**
"Your name, as it will appear on the blog?" Store as AUTHOR_NAME.

**g) Bucket prefix**
Set automatically as a slugified version of their GitHub username, e.g. `will-` for user `will`.
This scopes all S3 buckets to avoid naming conflicts. Store as BUCKET_PREFIX.

---

## Step 6 — Configure the repo

Now update all the template placeholders with real values.

**Update infra/pulumi-ingress/Pulumi.prod.yaml:**
Write this file:
```yaml
config:
  aws:region: <AWS_REGION>
  lukerohde-ingress:domainName: <DOMAIN>
  lukerohde-ingress:githubOwner: <GITHUB_OWNER>
  lukerohde-ingress:bucketPrefix: <BUCKET_PREFIX>
```

**Update infra/pulumi-ingress/Pulumi.yaml** — change the stack name:
```yaml
name: <GITHUB_OWNER>-ingress
runtime: python
description: Centralised ingress — Route53 zone, GitHub OIDC + CI roles
```

**Update infra/pulumi/Pulumi.yaml:**
```yaml
name: <GITHUB_OWNER>-site
runtime: python
description: Blog site infrastructure — S3 + CloudFront + ACM + Route53
```

**Update infra/pulumi/Pulumi.prod.yaml:**
```yaml
config:
  aws:region: <AWS_REGION>
  <GITHUB_OWNER>-site:domainName: <DOMAIN>
```

**Update infra/pulumi/__main__.py** — replace the StackReference:
Change `lukerohde/lukerohde-ingress/prod` → `<PULUMI_ORG>/<GITHUB_OWNER>-ingress/prod`

**Update infra/pulumi/__main__.py** — replace bucket name:
Change `lukerohde-portfolio` → `<BUCKET_PREFIX>blog`

**Update .github/workflows/deploy-infra.yml** — replace all stack references:
Change `lukerohde/lukerohde-ingress/prod` → `<PULUMI_ORG>/<GITHUB_OWNER>-ingress/prod`
Change `lukerohde/lukerohde-site/prod` → `<PULUMI_ORG>/<GITHUB_OWNER>-site/prod`

**Update .github/workflows/deploy-site.yml** — same stack reference replacements.

**Update astro.config.mjs:**
Change `site: 'https://lukeroh.de'` → `site: 'https://<DOMAIN>'`

**Update package.json:**
Change `"name": "lukerohde-site"` → `"name": "<REPO_NAME>"`

**Write DOMAIN to .env:**
```
AWS_DEFAULT_REGION=<AWS_REGION>
```

Confirm all edits, then show a summary of what was changed.

---

## Step 7 — Deploy the ingress stack

**Why:** This creates your Route53 hosted zone (authoritative DNS for your domain),
the GitHub OIDC provider (so CI can deploy without storing AWS keys), and the
shared IAM roles. It runs once and rarely needs to change.

```bash
make infra-ingress-up
```

This takes 1-3 minutes. Watch for errors.

On success, show the nameservers:
```bash
make infra-ingress-outputs
```

Copy the 4 nameserver values (they look like `ns-123.awsdns-45.com`).

---

## Step 8 — Delegate nameservers at your registrar

**If you bought the domain via Route53 in Step 5:** AWS automatically wires up the hosted zone
and nameservers. Skip the manual delegation — just verify the zone exists:
```bash
make infra-ingress-outputs
```
If `zone_id` appears in the output, you're done. Continue to Step 9.

---

**If you're using a domain from another registrar:** This is the one manual step. The user must:

1. Log into their domain registrar (Namecheap, Route53, etc.)
2. Find the DNS / Nameserver settings for their domain
3. Replace the default nameservers with the 4 AWS ones from the previous step

Show registrar-specific instructions:

**Namecheap:**
- Dashboard → Domain List → Manage → Nameservers
- Change dropdown to "Custom DNS"
- Enter all 4 nameservers (without trailing dot)

**Route53 (if they bought the domain there):**
- Route53 Console → Registered Domains → your domain
- "Add or edit name servers" — replace with the hosted zone's NS records

**GoDaddy:**
- My Products → DNS → Nameservers → Change → Enter my own nameservers

Tell them: "DNS propagation takes 5-60 minutes (sometimes up to 24 hours globally).
You don't have to wait — let's continue and come back to verify."

Ask: "Have you set the nameservers? (y/n)"

---

## Step 9 — Deploy the blog site stack

**Why:** This creates the S3 bucket (stores your site files), CloudFront distribution
(CDN that serves your site globally over HTTPS), and requests an ACM TLS certificate
(auto-renewed, free). DNS validation for the certificate is automatic — it creates
Route53 records to prove you own the domain.

**Note:** If NS delegation isn't complete yet, the ACM certificate validation may hang.
It polls every 30 seconds and will succeed once DNS propagates. This is safe to leave running.

```bash
make infra-up
```

Takes 5-15 minutes (CloudFront distribution creation is the slow part).

On success:
```bash
make infra-outputs
```

Show them the CloudFront domain (something like `d1234abcd.cloudfront.net`).
This is their site's CDN address. Once DNS propagates, their domain will point here.

---

## Step 10 — Create the GitHub repo and configure CI

**a) Reinitialise git with their identity:**
```bash
rm -rf .git
git init
git add -A
git commit -m "Initial blog setup for <DOMAIN>"
```

**b) Create GitHub repo:**
```bash
gh repo create <GITHUB_OWNER>/<REPO_NAME> --public --description "Personal blog at <DOMAIN>" --source=. --remote=origin
```

If they want a private repo, use `--private` instead.

**c) Set the CI secret:**
```bash
# Get PULUMI_ACCESS_TOKEN from .env
PULUMI_TOKEN=$(grep PULUMI_ACCESS_TOKEN .env | cut -d= -f2)
gh secret set PULUMI_ACCESS_TOKEN --body "$PULUMI_TOKEN" --repo <GITHUB_OWNER>/<REPO_NAME>
```

**d) Push:**
```bash
git push -u origin main
```

This triggers CI (deploy-infra runs preview only since it's the first push to main — 
that's correct behaviour. The infra is already deployed locally, so CI will show "no changes").

Show them the GitHub Actions URL:
```bash
echo "CI: https://github.com/<GITHUB_OWNER>/<REPO_NAME>/actions"
```

---

## Step 11 — Add initial content

Ask these optional questions to make the blog feel personal from day one.

**Profile photo:**
"Do you have a photo you'd like to use on the blog? (optional — you can add this later)
If yes, what's the file path? I'll copy it to public/avatar.jpg."

If provided, copy it to `public/avatar.jpg`.

**A first post idea:**
"What's one thing you've been meaning to write about?
I can create a stub in ideas/ so you don't forget."

If they give a title, run:
```bash
make draft IDEA=<slugified-title>
```

Show them the created file and tell them to open it in their editor.

**Projects:**
"Do you have any projects you'd like to list on the site?
(GitHub repos, side projects, tools — anything you want to show off)"

For each project they mention, create `projects/<name>.md`:
```markdown
---
name: "Project Name"
url: "https://..."
isNew: true
order: 1
---

One sentence description.
```

---

## Step 12 — First deploy and verification

```bash
make deploy
```

This builds the Astro site and syncs to S3.

Then tell them:

```
Your blog is deployed! Here's what to check:

1. CloudFront URL (works immediately):
   https://<cloudfront-domain>

2. Your domain (works after NS propagation):
   https://<DOMAIN>

To check if DNS has propagated:
   dig +short NS <DOMAIN>
   (should return your 4 AWS nameservers)

If the domain isn't working yet, check back in 30-60 minutes.
```

---

## Step 13 — What's next

Summarise what was built, then show the ongoing workflow:

```
✅  Your blog is live at https://<DOMAIN>

Day-to-day blogging:
  make draft IDEA=<your-idea>    — start a new post
  make publish POST=<slug>       — mark it ready
  make deploy                    — push to S3
  git push                       — CI deploys automatically

To add a new app at <subdomain>.<DOMAIN>:
  /new-spa

To take everything down:
  /teardown

Phone-based blogging:
  Pair Claude Desktop with the Claude mobile app in Claude settings.
  Then you can start a session from your phone: "draft a post about X"
  and Claude can write, publish, and push to GitHub without touching your laptop.
```
