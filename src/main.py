#!/usr/bin/env python3

import kubernetes
import hvac
import os
import yaml
import sys
import logging

import k8s

from base64 import b64encode
from dotenv import load_dotenv


logger = logging.getLogger("vault-k8s-mapper")
logger.setLevel(logging.DEBUG)
load_dotenv(verbose=True)


def get_token():
    if "VAULT_TOKEN" in os.environ:
        return os.environ["VAULT_TOKEN"]
    token_path = os.environ.get(
        "TOKEN_PATH", "/var/run/secrets/kubernetes.io/serviceaccount/token"
    )
    with open(token_path, "r") as token_file:
        return token_file.read()


def get_yaml_config():
    config_path = os.environ.get("CONFIG_PATH", "config.yaml")
    return yaml.load(config_path)


def parse_sources(sources):
    #  /secret/path:key
    outputs = []
    for source in sources.split(","):
        path, key = source.split(":")
        path = path.strip()
        key = key.strip()
        if path == "" or key == "":
            raise ValueError(
                f"Incorrect source configuration '{source}', should be in form /secret/path:key"
            )
        if path.startswith("/secret"):
            logging.warning("Stripping leading /secret path for %s", path)
            path = path[7:]
        outputs.append([path, key])
    return outputs


def main():
    for env in [
        "NAMESPACE",
        "VAULT_ADDRESS",
        "VAULT_ROLE",
        "VAULT_AUTH_PATH",
        "SECRET_TARGET",
        "SECRET_SOURCES",
    ]:
        if env not in os.environ:
            print(f"Requried var {env} not found in environment variables, exiting.")
            sys.exit(1)
    try:
        vault_token = get_token()
    except IOError:
        print("Could not open vault token, exiting.")
        sys.exit(1)
    sources = parse_sources(os.environ["SECRET_SOURCES"])
    secret_target = os.environ["SECRET_TARGET"]
    namespace = os.environ["NAMESPACE"]
    logger.info("Secret source mappings: %s", sources)

    vault_address = os.environ["VAULT_ADDRESS"]
    vault_role = os.environ["VAULT_ROLE"]
    vault_auth_path = os.environ["VAULT_AUTH_PATH"]

    client = hvac.Client(url=vault_address)
    client.auth_kubernetes(
        role=vault_role, jwt=vault_token, mount_point=vault_auth_path
    )
    if not client.is_authenticated():
        logger.error("Vault client failed to authenticate, exiting.")
        sys.exit(1)
    logger.info("Authenticated against Vault succesfully.")
    secrets = {}

    for source in sources:
        path, key = source
        if path.endswith("/"):
            logger.info("Found path ending in /, listing secrets")
            list_response = client.secrets.kv.v2.list_secrets(path=path)
            for sub_key in list_response["data"]["keys"]:
                sub_path = f"{path}{sub_key}"
                logger.info("Found sub-path %s", sub_path)
                secret_response = client.secrets.kv.v2.read_secret_version(
                    path=sub_path
                )
                data = secret_response["data"]["data"][key].encode("ascii")
                secrets[sub_key] = b64encode(data).decode("ascii")

    k8s.create_or_update_secret(secret_target, namespace, secrets)


if __name__ == "__main__":
    main()
