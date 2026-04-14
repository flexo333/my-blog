"""
Centralised ingress
───────────────────
- Route53 hosted zone (authoritative DNS for your domain)
- GitHub Actions OIDC provider + shared CI roles

Shared roles let any <github_owner>/* repo deploy static sites without
touching this stack. Adding a new site = create a repo, copy one secret, done.

Config (in Pulumi.prod.yaml):
  domainName    — your root domain, e.g. will.dev
  githubOwner   — your GitHub username or org
  bucketPrefix  — prefix for all S3 bucket names, e.g. "will-"
"""

import json
import pulumi
import pulumi_aws as aws

# ── Config ─────────────────────────────────────────────────────────────────────
config = pulumi.Config()
domain_name   = config.require("domainName")
github_owner  = config.require("githubOwner")
bucket_prefix = config.get("bucketPrefix") or f"{github_owner}-"

# ── Route 53 hosted zone ───────────────────────────────────────────────────────
zone = aws.route53.Zone("zone", name=domain_name)

# ── GitHub Actions OIDC ───────────────────────────────────────────────────────
# One provider per AWS account — shared by all static sites.
oidc_provider = aws.iam.OpenIdConnectProvider(
    "github-oidc",
    url="https://token.actions.githubusercontent.com",
    client_id_lists=["sts.amazonaws.com"],
    thumbprint_lists=["6938fd4d98bab03faadb97b34396831e3780aea1"],
)

caller     = aws.get_caller_identity()
account_id = caller.account_id

# ── Deploy role — S3 sync + CloudFront invalidation only ─────────────────────
# Trust: any <github_owner>/* repo, main branch only
deploy_role = aws.iam.Role(
    "static-site-deploy",
    assume_role_policy=oidc_provider.arn.apply(lambda arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Federated": arn},
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub":
                        f"repo:{github_owner}/*:ref:refs/heads/main",
                },
            },
        }],
    })),
)

aws.iam.RolePolicy(
    "static-site-deploy-policy",
    role=deploy_role.id,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3Sync",
                "Effect": "Allow",
                "Action": ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket_prefix}*"],
            },
            {
                "Sid": "CloudFrontInvalidation",
                "Effect": "Allow",
                "Action": ["cloudfront:CreateInvalidation"],
                "Resource": f"arn:aws:cloudfront::{account_id}:distribution/*",
            },
        ],
    }),
)

# ── Infra role — full static-site lifecycle (S3, CF, ACM, Route53 records) ───
# Trust: any <github_owner>/* repo, any branch (PRs need preview)
infra_role = aws.iam.Role(
    "static-site-infra",
    assume_role_policy=oidc_provider.arn.apply(lambda arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Federated": arn},
            "Action": "sts:AssumeRoleWithWebIdentity",
            "Condition": {
                "StringEquals": {
                    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                },
                "StringLike": {
                    "token.actions.githubusercontent.com:sub":
                        f"repo:{github_owner}/*",
                },
            },
        }],
    })),
)

aws.iam.RolePolicy(
    "static-site-infra-policy",
    role=infra_role.id,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3Full",
                "Effect": "Allow",
                "Action": "s3:*",
                "Resource": [f"arn:aws:s3:::{bucket_prefix}*"],
            },
            {
                "Sid": "CloudFront",
                "Effect": "Allow",
                "Action": "cloudfront:*",
                "Resource": f"arn:aws:cloudfront::{account_id}:*",
            },
            {
                "Sid": "ACM",
                "Effect": "Allow",
                "Action": "acm:*",
                "Resource": "*",
            },
            {
                "Sid": "Route53Records",
                "Effect": "Allow",
                "Action": [
                    "route53:ChangeResourceRecordSets",
                    "route53:GetHostedZone",
                    "route53:ListResourceRecordSets",
                    "route53:GetChange",
                ],
                "Resource": [
                    "arn:aws:route53:::hostedzone/*",
                    "arn:aws:route53:::change/*",
                ],
            },
            {
                "Sid": "Route53List",
                "Effect": "Allow",
                "Action": "route53:ListHostedZones",
                "Resource": "*",
            },
        ],
    }),
)

# ── Outputs ────────────────────────────────────────────────────────────────────
pulumi.export("nameservers",    zone.name_servers)
pulumi.export("zone_id",        zone.zone_id)
pulumi.export("deploy_role_arn", deploy_role.arn)
pulumi.export("infra_role_arn", infra_role.arn)
pulumi.export("aws_region",     pulumi.Config("aws").require("region"))
