"""Shared runtime config — secrets loading for Lambda handlers.

Lives in the core package so every function reuses one loader instead of
duplicating SSM code per handler. (When the package is renamed to `windspotter`,
this becomes `windspotter/common/config.py`.)

`boto3` is imported lazily and results are cached, so importing this module is
free locally (no boto3 needed) and each secret is fetched once per cold start.
"""

from __future__ import annotations

import functools


@functools.lru_cache(maxsize=1)
def _ssm():
    import boto3  # provided by the Lambda runtime; lazy so local imports don't need it

    return boto3.client("ssm")


@functools.lru_cache(maxsize=None)
def get_secret(param_name: str) -> str:
    """Fetch and decrypt an SSM SecureString parameter (cached per cold start)."""
    return _ssm().get_parameter(Name=param_name, WithDecryption=True)["Parameter"]["Value"]
