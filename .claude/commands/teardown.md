# /teardown — Destroy all AWS infrastructure

⚠️  This destroys:
- Your CloudFront distribution
- Your S3 bucket (and all site content stored there)
- Your ACM certificate
- Your Route53 hosted zone (and all DNS records)
- Your GitHub OIDC provider and IAM roles

Your code and blog posts (in this Git repo) are NOT deleted.
You can redeploy everything with `/setup` after teardown.

---

## Step 1 — Confirm

Ask clearly:
"This will destroy all AWS infrastructure for your blog. Your domain will stop working.
Your code and posts are safe — just the AWS resources will be deleted.

Are you sure? Type YES to continue."

Only proceed if they type exactly `YES`.

---

## Step 2 — Destroy site stack first

The site stack must be destroyed before the ingress stack (it references the zone).

```bash
make infra-destroy
```

Watch for errors. If Pulumi says resources are "in use" or there are dependencies,
help diagnose and resolve before continuing.

---

## Step 3 — Destroy ingress stack

```bash
make infra-ingress-destroy
```

This deletes the Route53 zone, OIDC provider, and IAM roles.

**After this, your domain will stop resolving.** NS records at your registrar
now point to a zone that no longer exists. To restore: run `/setup` again
and re-delegate nameservers.

---

## Step 4 — Clean up local config (optional)

Ask: "Do you want to remove `.env` as well? (Your AWS keys and Pulumi token will be deleted from this machine)"

If yes:
```bash
rm .env
echo "✅  .env removed"
```

---

## Step 5 — Confirm and summarise

```
✅  All AWS infrastructure destroyed.

What's gone:
  - CloudFront distribution
  - S3 bucket and contents
  - ACM certificate
  - Route53 hosted zone (all DNS records)
  - GitHub OIDC provider and IAM roles

What's still here:
  - This Git repo and all your code
  - Your blog posts in posts/
  - Your GitHub repo (if you want to delete it: gh repo delete <repo>)

To start fresh: run /setup
```

Note the estimated final AWS bill: teardown is not instant — S3, CloudFront,
and Route53 are billed by the month and will show one last partial-month charge.
