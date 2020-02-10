#!/usr/bin/env python3

import kubernetes
import hvac
import os
import yaml
import sys
import logging

import k8s
import vault

from base64 import b64encode, b64decode
from dotenv import load_dotenv

logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
logger = logging.getLogger("vault-k8s-mapper")
load_dotenv()

REQUIRED_ENV_VARS = (
    "NAMESPACE",
    "VAULT_ADDRESS",
    "VAULT_ROLE",
    "VAULT_AUTH_PATH",
    "SECRET_TARGET",
    "SECRET_SOURCES",
)

DEFAULT_CONFIG = {"DEFAULT_KEY": "value"}


def get_config():
    config = DEFAULT_CONFIG.copy()
    for key in REQUIRED_ENV_VARS:
        if os.environ.get(key, "") == "":
            raise IndexError("Requried environment variable {key} not set")
        config[key] = os.environ[key]
    return config


def main():
    try:
        config = get_config()
    except IndexError as e:
        logger.exception(e)
        sys.exit(1)

    try:
        vault_token = vault.get_token()
    except Exception as e:
        logger.exception("Could not read vault token: %s", e)
        sys.exit(1)

    sources = vault.parse_sources(config["SECRET_SOURCES"], config)
    logger.info("Secret source mappings: %s", sources)

    secrets = vault.get_secrets(config, sources, vault_token)
    k8s.create_or_update_secret(config["SECRET_TARGET"], config["NAMESPACE"], secrets)


if __name__ == "__main__":
    main()
