import logging
import hvac
import os
import re


R_PATHMAP = re.compile(r"(^(?P<target>\w+):)?(?P<path>[*./\w-]+):?(?P<key>[/\w-]+)?")
R_ENVVAR = re.compile(r"[-._a-zA-Z0-9]+")
logger = logging.getLogger("vault-k8s-mapper")


def parse_entry(entry):
    entry = entry.strip()
    result = R_PATHMAP.match(entry).groupdict()
    return result


def is_valid_envvar(target):
    if target is None:
        return True
    return R_ENVVAR.match(target) is not None


def parse_sources(sources, config):
    outputs = []
    for source in sources.split(","):
        entry = parse_entry(source)
        if entry["path"] is None:
            raise ValueError(f"Missing path from '{source}'")
        if entry["key"] is None:
            entry["key"] = config["DEFAULT_KEY"]
        if not is_valid_envvar(entry["target"]):
            raise ValueError(
                f"""Target environment variable has incompatible characters: '{entry["target"]}'"""
            )
        # Strip out /secret
        if entry["path"][:7] == "/secret":
            logging.warning("Stripping leading /secret path for %s", entry["path"])
            entry["path"] = entry["path"][7:]
        elif entry["path"][:6] == "secret":
            logging.warning("Stripping leading secret path for %s", entry["path"])
            entry["path"] = entry["path"][6:]
        outputs.append(entry)
    return outputs


def get_token():
    if "VAULT_TOKEN" in os.environ:
        logger.info("VAULT_TOKEN found in environment variables, using it for auth")
        return os.environ["VAULT_TOKEN"]
    token_path = os.environ.get(
        "TOKEN_PATH", "/var/run/secrets/kubernetes.io/serviceaccount/token"
    )
    logger.warning("Using Vault TOKEN_PATH: %s", token_path)
    with open(token_path, "r") as token_file:
        return token_file.read()


def get_client(config, token):
    client = hvac.Client(url=config["VAULT_ADDRESS"])
    client.auth_kubernetes(
        role=config["VAULT_ROLE"], jwt=token, mount_point=config["VAULT_AUTH_PATH"]
    )
    if not client.is_authenticated():
        raise Exception("Vault client failed to authenticate")
    return client


def get_secrets(config, sources, token):
    secrets = {}
    client = get_client(config, token)

    logger.info("Authenticated against Vault succesfully.")

    for source in sources:
        path = source["path"]
        key = source["key"]
        target = source["target"]

        if path.endswith("/"):
            logger.info("Found path ending in /, listing secrets for %s", path)
            key_prefix = ""
            if target is not None:
                key_prefix = f"{target}_"
                logger.info("Target set, prepending secrets with '%s_'", target)
            list_response = client.secrets.kv.v2.list_secrets(path=path)
            for sub_key in list_response["data"]["keys"]:
                if not is_valid_envvar(sub_key):
                    logger.error("Not a valid Secret mapping key, skipping: '%s'")
                    continue
                sub_path = f"{path}{sub_key}"
                logger.info("Found sub-path %s", sub_path)
                try:
                    secret_response = client.secrets.kv.v2.read_secret_version(
                        path=sub_path
                    )
                except hvac.exceptions.InvalidPath:
                    logger.warning("Sub-path %s metadata exists but contains no data, skipping.", sub_path)
                    continue
                if key not in secret_response["data"]["data"]:
                    logger.warning("Sub-path %s missing key %s, skipping", sub_path, key)
                    continue
                data = secret_response["data"]["data"][key].encode("ascii")

                secrets[f"{key_prefix}{sub_key}"] = data
        else:
            logger.info("Found direct path, fetching secret %s", path)
            try:
                secret_response = client.secrets.kv.v2.read_secret_version(path=path)
            except hvac.exceptions.InvalidPath:
                logger.critical("Sub-path %s metadata exists but contains no data, skipping.", path)
                raise
            if key not in secret_response["data"]["data"]:
                logger.warning("Path %s missing key %s, skipping", path, key)
                continue
            data = secret_response["data"]["data"][key].encode("ascii")
            env_key = path.split("/").pop()
            if target is not None:
                logger.info("Overriding target %s -> %s", env_key, target)
                secrets[target] = data
            else:
                secrets[env_key] = data
    return secrets
