# Deploying Spot Consultant to AWS

A serverless MVP: one Lambda behind a Function URL, secrets in SSM, a cost budget,
and no VPC. Idle cost ≈ $0 — you only pay for Anthropic calls when it runs.

```
client ──(POST, x-api-token header)──▶ Lambda Function URL ──▶ Lambda ──▶ enrich_spot()
                                                                  │
                                                                  └─ reads Anthropic key from SSM (SecureString)
```

## Prerequisites

- A **personal AWS account** with billing set up. *(This is the only real gate.)*
- **AWS CLI** configured with credentials:
  ```bash
  aws configure        # access key + secret for a personal IAM user, region eu-north-1
  aws sts get-caller-identity   # confirms creds work
  ```
- **SAM CLI**: `brew install aws-sam-cli`
- **Python 3.12** (used by the Docker-free build). No Docker required.
- Your **Anthropic API key** (`sk-ant-...`).

## 1. Store secrets in SSM

```bash
REGION=eu-north-1
aws ssm put-parameter --region $REGION --type SecureString \
  --name /spot-consultant/anthropic-api-key --value 'sk-ant-REPLACE_ME'

# A shared secret the Function URL will require (save the printed value):
TOKEN=$(openssl rand -hex 16); echo "API token: $TOKEN"
aws ssm put-parameter --region $REGION --type SecureString \
  --name /spot-consultant/api-token --value "$TOKEN"
```

## 2. Build & deploy

```bash
cd infra
sam build                       # Docker-free; fetches Linux/arm64 wheels
sam deploy --guided             # stack name: spot-consultant, region: eu-north-1
                                # it will prompt for AlertEmail (for the budget alert)
```

`sam deploy` prints the **FunctionUrl** output. (`--guided` saves your answers to
`samconfig.toml`, so later deploys are just `sam deploy`.)

## 3. Test it

```bash
URL="<the EnrichFunctionUrl output>"
curl -s -X POST "$URL" \
  -H "x-api-token: $TOKEN" \
  -H "content-type: application/json" \
  -d '{"query":"Mellsten, Espoo, Finland"}' | jq
```

A wrong/missing `x-api-token` returns `401`. A non-spot returns the validation
rejection. A real spot returns the full validated report.

## 4. Cost controls (already wired in)

- **Model defaults to `claude-haiku-4-5`** (cents/call). Override per-deploy with
  `sam deploy --parameter-overrides SpotModel=claude-sonnet-4-6`.
- **Reserved concurrency = 2** — a public URL can't fan out and run up the bill.
- **$10/month AWS Budget** emails you at 80%.
- Capped web searches in the pipeline (`max_uses`) keep each run cheap.

## 5. Teardown

```bash
sam delete --stack-name spot-consultant --region eu-north-1
aws ssm delete-parameter --name /spot-consultant/anthropic-api-key --region eu-north-1
aws ssm delete-parameter --name /spot-consultant/api-token --region eu-north-1
```

## Notes

- **Docker-free packaging:** `infra/Makefile` runs `pip --platform manylinux2014_aarch64
  --only-binary=:all:` so `pydantic-core` (compiled) ships a Lambda-compatible wheel.
- **No VPC:** the Anthropic API, OSM, and SSM are all reached over HTTPS + IAM —
  nothing to expose. (See the security discussion in the project history.)
- **Next iteration (production scale):** move from sync to async — API Gateway →
  SQS → worker Lambda → DynamoDB + a poll endpoint — so slow runs don't hold a
  connection open and results are cached. `lambda_handler.py` already sketches the
  async worker shape.
