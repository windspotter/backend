"""AWS Lambda entry point.

The point of this file: the core `enrich_spot()` is deployment-agnostic, so the
same module that powers the CLI and the Streamlit demo runs in Lambda unchanged.

In production this runs ASYNCHRONOUSLY — triggered by SQS/EventBridge after a
user adds a custom spot — NOT synchronously behind API Gateway, because the
agentic research loop can exceed API Gateway's 29-second integration timeout
(Lambda itself allows up to 15 minutes). The API key is read from an env var
injected from SSM Parameter Store / Secrets Manager; no VPC is required, since
the Anthropic API, DynamoDB, and SNS are all reachable over plain HTTPS + IAM.
"""

from __future__ import annotations

import json

from spot_consultant import enrich_spot


def handler(event, context):
    # Accept a direct invoke {"query": "..."} or an SQS record batch.
    queries: list[str] = []
    if "Records" in event:  # SQS trigger
        for record in event["Records"]:
            body = json.loads(record.get("body", "{}"))
            if body.get("query"):
                queries.append(body["query"])
    elif event.get("query"):
        queries.append(event["query"])

    results = [enrich_spot(q).model_dump(mode="json") for q in queries]

    # In production: write each result to DynamoDB and queue anything with
    # needs_human_review == True for moderation before it goes live.
    return {"statusCode": 200, "body": json.dumps({"results": results})}
