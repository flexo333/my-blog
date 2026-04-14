"""
Blog site
─────────
S3 + CloudFront static site for the blog.

Zone, DNS, OIDC, and CI roles live in the ingress stack.
This stack only manages the blog site resources.

Prerequisites:
  Deploy the ingress stack first  →  make infra-ingress-up

Config (in Pulumi.prod.yaml):
  domainName — your root domain (must match ingress stack)

The stack reference below is updated by /setup to use your Pulumi org and GitHub username.
"""

import pulumi
from pulumi_static_site import StaticSite

# ── Config ─────────────────────────────────────────────────────────────────────
config      = pulumi.Config()
domain_name = config.require("domainName")

# ── Stack reference — filled in by /setup ──────────────────────────────────────
# Format: flexo333/flexo333-ingress/prod
ingress = pulumi.StackReference("flexo333/flexo333-ingress/prod")
zone_id = ingress.get_output("zone_id")

# ── Blog site ──────────────────────────────────────────────────────────────────
site = StaticSite(
    "blog",
    domain=domain_name,
    zone_id=zone_id,
    bucket_name="flexo333-blog",
    spa_mode=False,
)

# ── Outputs ────────────────────────────────────────────────────────────────────
pulumi.export("portfolio_bucket",           site.bucket_name)
pulumi.export("portfolio_distribution_id",  site.distribution_id)
pulumi.export("portfolio_cloudfront_domain",
    site.distribution_domain.apply(lambda d: f"https://{d}"))
pulumi.export("aws_region", pulumi.Config("aws").require("region"))
