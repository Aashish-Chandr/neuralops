# GitHub Secrets Configuration

Before CI/CD works, configure these secrets in your GitHub repository:
**Settings → Secrets and variables → Actions → New repository secret**

## Required for CD (image push)

| Secret | Value | Where used |
|---|---|---|
| `GITHUB_TOKEN` | Auto-provided by GitHub | Push images to GHCR, update Helm values |

`GITHUB_TOKEN` is automatically available — no setup needed.

## Required for Slack alerts (optional)

| Secret | Value | Where used |
|---|---|---|
| `SLACK_WEBHOOK_URL` | `https://hooks.slack.com/services/...` | Remediation engine escalations, Alertmanager |

Get a Slack webhook: https://api.slack.com/messaging/webhooks

## Required for cloud deployment (AWS)

| Secret | Value | Where used |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | Your AWS key ID | Terraform, EKS |
| `AWS_SECRET_ACCESS_KEY` | Your AWS secret | Terraform, EKS |
| `AWS_REGION` | e.g. `us-east-1` | Terraform |

## Setting secrets via GitHub CLI

```bash
gh secret set SLACK_WEBHOOK_URL --body "https://hooks.slack.com/services/..."
gh secret set AWS_ACCESS_KEY_ID --body "AKIA..."
gh secret set AWS_SECRET_ACCESS_KEY --body "..."
gh secret set AWS_REGION --body "us-east-1"
```

## Local development

Copy `.env.example` to `.env` and fill in values:
```bash
cp .env.example .env
```

The `.env` file is gitignored — never commit it.
