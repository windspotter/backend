"""Lambda handler for the spot-enrichment function (behind a Function URL).

A thin adapter: load secrets via the shared loader, enforce the API token, then
hand off to the same `enrich_spot()` the CLI and Streamlit app use. All business
logic lives in the `spot_consultant` core package — this file only translates an
HTTP event to a function call and back.
"""

from __future__ import annotations

import json
import os

from spot_consultant.config import get_secret

# Cold start (runs once per container): load secrets, set the key, import the pipeline.
_API_TOKEN = get_secret(os.environ["API_TOKEN_PARAM"])
os.environ["ANTHROPIC_API_KEY"] = get_secret(os.environ["ANTHROPIC_KEY_PARAM"])

from spot_consultant import enrich_spot  # noqa: E402  (import after the key is set)


def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if headers.get("x-api-token") != _API_TOKEN:
        return {"statusCode": 401, "body": json.dumps({"error": "unauthorized"})}

    # Accept {"query": "..."} in the POST body, or ?q=... on the URL.
    query = None
    if event.get("body"):
        try:
            query = json.loads(event["body"]).get("query")
        except (ValueError, TypeError):
            pass
    query = query or (event.get("queryStringParameters") or {}).get("q")
    if not query:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "provide 'query' in the JSON body or 'q' in the query string"}),
        }

    result = enrich_spot(query)
    return {
        "statusCode": 200,
        "headers": {"content-type": "application/json"},
        "body": result.model_dump_json(),
    }
