"""
Centralised ingress
───────────────────
- Route53 hosted zone (authoritative DNS for your domain)
- GitHub Actions OIDC provider + shared CI roles

Shared roles let any <github_owner>/* repo deploy static sites without
touching this stack. Adding a new site = create a repo, copy one secret, done.

Config (in Pulumi.prod.yaml):
  domainName       — your root domain, e.g. will.dev
  githubOwner      — your GitHub username or org
  githubOwnerId    — that account's numeric GitHub ID (see the note by
                     `github_subs` below)
  bucketPrefix     — prefix for all S3 bucket names, e.g. "will-"
  homelabSubdomain — subdomain the home-lab serves under (default "home").
                     Only used to scope the ACME DNS-01 credential below.
"""

import json
import pulumi
import pulumi_aws as aws

# ── Config ─────────────────────────────────────────────────────────────────────
config = pulumi.Config()
domain_name       = config.require("domainName")
github_owner      = config.require("githubOwner")
github_owner_id   = config.require("githubOwnerId")
bucket_prefix     = config.get("bucketPrefix") or f"{github_owner}-"
homelab_subdomain = config.get("homelabSubdomain") or "home"

# GitHub stamps one of two `sub` formats into an Actions OIDC token:
#
#   legacy     repo:flexo333/juda:ref:refs/heads/main
#   immutable  repo:flexo333@3823393/juda@1342342663:ref:refs/heads/main
#
# Every repo created after 2026-07-15 gets the immutable form, which embeds the
# owner and repo IDs; older repos keep the legacy form unless they opt in. Both
# must be trusted while that mix persists — a policy matching only
# `repo:{owner}/*` rejects every newly created repo with
# "Not authorized to perform sts:AssumeRoleWithWebIdentity".
def github_subs(suffix: str = "") -> list[str]:
    return [
        f"repo:{github_owner}/*{suffix}",
        f"repo:{github_owner}@{github_owner_id}/*{suffix}",
    ]


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
                        github_subs(":ref:refs/heads/main"),
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
            {
                "Sid": "EcrAuthForDeploy",
                # Container-image deploys need a registry token, which AWS
                # only issues with Resource: "*". Pull/push are still
                # restricted to bucket_prefix* repos via EcrPushPull below.
                "Effect": "Allow",
                "Action": ["ecr:GetAuthorizationToken"],
                "Resource": "*",
            },
            {
                "Sid": "EcrPushPull",
                "Effect": "Allow",
                "Action": [
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:BatchGetImage",
                    "ecr:CompleteLayerUpload",
                    "ecr:GetDownloadUrlForLayer",
                    "ecr:InitiateLayerUpload",
                    "ecr:PutImage",
                    "ecr:UploadLayerPart",
                    "ecr:DescribeRepositories",
                    "ecr:DescribeImages",
                    "ecr:ListImages",
                ],
                "Resource": [f"arn:aws:ecr:*:{account_id}:repository/{bucket_prefix}*"],
            },
            {
                "Sid": "LambdaUpdateImageForDeploy",
                # Lets the deploy role roll a Lambda's image URI to a new
                # SHA without touching configuration. Scoped to the same
                # prefix as the IAM role definitions below.
                "Effect": "Allow",
                "Action": [
                    "lambda:UpdateFunctionCode",
                    "lambda:GetFunction",
                    "lambda:PublishVersion",
                ],
                "Resource": [f"arn:aws:lambda:*:{account_id}:function:{bucket_prefix}*"],
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
                    "token.actions.githubusercontent.com:sub": github_subs(),
                },
            },
        }],
    })),
)

# Shared CI role for <github_owner>/* repos that deploy Lambda-backed static
# sites (yt2txt, future reeds-style apps). Resource ARNs are bounded to
# bucket_prefix* and known per-app prefixes so a compromised CI in one repo
# can't touch unrelated infra.
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
            {
                "Sid": "Lambda",
                "Effect": "Allow",
                "Action": "lambda:*",
                "Resource": [
                    f"arn:aws:lambda:*:{account_id}:function:{bucket_prefix}*",
                    f"arn:aws:lambda:*:{account_id}:function:yt2txt-*",
                    f"arn:aws:lambda:*:{account_id}:function:summarise-*",
                ],
            },
            {
                "Sid": "LambdaLayersList",
                "Effect": "Allow",
                "Action": [
                    "lambda:GetLayerVersion",
                    "lambda:ListLayers",
                    "lambda:ListLayerVersions",
                ],
                "Resource": "*",
            },
            {
                "Sid": "DynamoDB",
                "Effect": "Allow",
                "Action": "dynamodb:*",
                "Resource": [
                    f"arn:aws:dynamodb:*:{account_id}:table/{bucket_prefix}*",
                    f"arn:aws:dynamodb:*:{account_id}:table/{bucket_prefix}*/index/*",
                    f"arn:aws:dynamodb:*:{account_id}:table/yt2txt-*",
                    f"arn:aws:dynamodb:*:{account_id}:table/yt2txt-*/index/*",
                ],
            },
            {
                "Sid": "IAMManageServiceRoles",
                "Effect": "Allow",
                "Action": [
                    "iam:CreateRole",
                    "iam:GetRole",
                    "iam:UpdateRole",
                    "iam:DeleteRole",
                    "iam:TagRole",
                    "iam:UntagRole",
                    "iam:ListRoleTags",
                    "iam:PutRolePolicy",
                    "iam:GetRolePolicy",
                    "iam:DeleteRolePolicy",
                    "iam:ListRolePolicies",
                ],
                "Resource": [
                    f"arn:aws:iam::{account_id}:role/{bucket_prefix}*",
                    f"arn:aws:iam::{account_id}:role/yt2txt-*",
                    f"arn:aws:iam::{account_id}:role/summarise-*",
                ],
            },
            {
                "Sid": "IAMManagedPolicyAttach",
                "Effect": "Allow",
                "Action": [
                    "iam:AttachRolePolicy",
                    "iam:DetachRolePolicy",
                    "iam:ListAttachedRolePolicies",
                ],
                "Resource": [
                    f"arn:aws:iam::{account_id}:role/{bucket_prefix}*",
                    f"arn:aws:iam::{account_id}:role/yt2txt-*",
                    f"arn:aws:iam::{account_id}:role/summarise-*",
                ],
                # ArnEqualsIfExists (not ArnEquals) — `iam:PolicyARN` is
                # only supplied for Attach/DetachRolePolicy. With plain
                # ArnEquals, ListAttachedRolePolicies (no input ARN) is
                # always denied, breaking Pulumi's refresh of any role.
                "Condition": {
                    "ArnEqualsIfExists": {
                        "iam:PolicyARN": [
                            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
                        ],
                    },
                },
            },
            {
                "Sid": "IAMPassRole",
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": [
                    f"arn:aws:iam::{account_id}:role/{bucket_prefix}*",
                    f"arn:aws:iam::{account_id}:role/yt2txt-*",
                    f"arn:aws:iam::{account_id}:role/summarise-*",
                ],
                "Condition": {
                    "StringEquals": {
                        "iam:PassedToService": "lambda.amazonaws.com",
                    },
                },
            },
            {
                "Sid": "EventBridge",
                "Effect": "Allow",
                "Action": "events:*",
                "Resource": [
                    f"arn:aws:events:*:{account_id}:rule/{bucket_prefix}*",
                    f"arn:aws:events:*:{account_id}:rule/yt2txt-*",
                ],
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:CreateLogGroup",
                    "logs:DeleteLogGroup",
                    "logs:DescribeLogGroups",
                    "logs:PutRetentionPolicy",
                    "logs:TagResource",
                    "logs:UntagResource",
                    "logs:ListTagsForResource",
                ],
                "Resource": f"arn:aws:logs:*:{account_id}:log-group:/aws/lambda/*",
            },
            {
                "Sid": "EcrAuth",
                # ECR token requests are not resource-scopable.
                "Effect": "Allow",
                "Action": ["ecr:GetAuthorizationToken"],
                "Resource": "*",
            },
            {
                "Sid": "EcrRepoLifecycle",
                "Effect": "Allow",
                "Action": "ecr:*",
                "Resource": [f"arn:aws:ecr:*:{account_id}:repository/{bucket_prefix}*"],
            },
            {
                "Sid": "SsmParameters",
                # App-config + secrets stored as SecureString parameters under
                # /<prefix>/* (e.g. /flexo333/garmin/jwt_secret).
                "Effect": "Allow",
                "Action": [
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                    "ssm:GetParametersByPath",
                    "ssm:PutParameter",
                    "ssm:DeleteParameter",
                    "ssm:AddTagsToResource",
                    "ssm:RemoveTagsFromResource",
                    "ssm:ListTagsForResource",
                    "ssm:DescribeParameters",
                ],
                "Resource": [
                    f"arn:aws:ssm:*:{account_id}:parameter/{bucket_prefix.rstrip('-')}/*",
                ],
            },
            {
                "Sid": "SsmDescribeAll",
                # DescribeParameters cannot be resource-scoped.
                "Effect": "Allow",
                "Action": ["ssm:DescribeParameters"],
                "Resource": "*",
            },
            {
                "Sid": "SecretsManager",
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:CreateSecret",
                    "secretsmanager:DeleteSecret",
                    "secretsmanager:DescribeSecret",
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:PutSecretValue",
                    "secretsmanager:UpdateSecret",
                    "secretsmanager:TagResource",
                    "secretsmanager:UntagResource",
                ],
                "Resource": [
                    f"arn:aws:secretsmanager:*:{account_id}:secret:{bucket_prefix}*",
                ],
            },
        ],
    }),
)

# ── Home-lab ingress — scoped key for nginx-proxy-manager's ACME DNS-01 ──────
# The homecore box (/srv) runs nginx-proxy-manager, which issues a real
# Let's Encrypt wildcard cert for *.home.willbright.link via
# certbot-dns-route53 and auto-renews it. ACM/CloudFront can't serve LAN-only
# services, so it's a genuine LE cert — but the DNS-01 challenge writes
# _acme-challenge TXT records into THIS zone, so NPM needs long-lived AWS
# credentials. Managed here so the key is IaC, least-privilege and rotatable.
#
# The write grant is narrowed three ways — hosted zone (Resource), record type
# (TXT) and exact record name — so a leak of this key cannot repoint the apex,
# MX, or any other record in willbright.link.
#
# Both names on the cert (*.home.willbright.link AND home.willbright.link)
# validate at the SAME record, _acme-challenge.home.willbright.link, because
# ACME strips the wildcard label before prefixing. So one allowed name covers
# the whole cert — and renewals, which reuse that same name.
homelab_domain      = f"{homelab_subdomain}.{domain_name}"
acme_challenge_name = f"_acme-challenge.{homelab_domain}"

npm_dns01_user = aws.iam.User("npm-route53-dns01", name="npm-route53-dns01")

aws.iam.UserPolicy(
    "npm-route53-dns01-policy",
    user=npm_dns01_user.name,
    policy=zone.arn.apply(lambda zone_arn: json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                # ListHostedZones/GetChange are not resource-scopable.
                "Sid": "ListAndPollChanges",
                "Effect": "Allow",
                "Action": ["route53:ListHostedZones", "route53:GetChange"],
                "Resource": "*",
            },
            {
                "Sid": "AcmeChallengeTxtRecordOnly",
                "Effect": "Allow",
                "Action": "route53:ChangeResourceRecordSets",
                "Resource": zone_arn,
                # ForAllValues is required, not stylistic: these are
                # multi-valued keys (one API call can carry several changes)
                # and ForAllValues demands EVERY value match. A plain
                # StringEquals would pass the whole call if any one matched.
                #
                # Not restricting ...Actions: CREATE/UPSERT/DELETE is the
                # complete set of valid actions, so allow-listing all three
                # would grant exactly what omitting it grants.
                "Condition": {
                    "ForAllValues:StringEquals": {
                        "route53:ChangeResourceRecordSetsNormalizedRecordNames": [
                            acme_challenge_name,
                        ],
                        "route53:ChangeResourceRecordSetsRecordTypes": ["TXT"],
                    },
                },
            },
        ],
    })),
)

npm_dns01_key = aws.iam.AccessKey("npm-route53-dns01-key", user=npm_dns01_user.name)

# ── Outputs ────────────────────────────────────────────────────────────────────
pulumi.export("nameservers",    zone.name_servers)
pulumi.export("zone_id",        zone.zone_id)
pulumi.export("deploy_role_arn", deploy_role.arn)
pulumi.export("infra_role_arn", infra_role.arn)
pulumi.export("aws_region",     pulumi.Config("aws").require("region"))
# Feed these into the homecore box's _ingress/route53-credentials.ini:
#   make infra-ingress-outputs                       # key id (plaintext)
#   docker compose run --rm pulumi-ingress \
#     stack output npm_dns01_secret_access_key --show-secrets
pulumi.export("npm_dns01_access_key_id",     npm_dns01_key.id)
pulumi.export("npm_dns01_secret_access_key", npm_dns01_key.secret)  # secret output
