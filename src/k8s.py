import logging
from kubernetes import client, config

from kubernetes.client.rest import ApiException

# Configure API key authorization: BearerToken
logger = logging.getLogger("vault-k8s-mapper")


def create_or_update_secret(name, namespace, data):
    try:
        config.load_incluster_config()
    except:
        logger.warning("Couldn't load in-cluster config, defaulting to kubeconfig")
        config.load_kube_config()

    configuration = client.Configuration()
    api_instance = client.CoreV1Api(client.ApiClient(configuration))

    metadata = client.V1ObjectMeta(name=name, namespace=namespace)
    body = client.V1Secret(data=data, metadata=metadata)
    try:
        api_instance.read_namespaced_secret(name, namespace)
        logger.info("Secret %s found in %s namespace, updating.", name, namespace)
        api_instance.patch_namespaced_secret(name=name, namespace=namespace, body=body)
    except ApiException as e:
        if e.reason == "Not Found":
            logger.info(
                "Secret %s not found in %s namespace, creating.", name, namespace
            )
            try:
                api_response = api_instance.create_namespaced_secret(namespace, body)
            except ApiException as e:
                logger.exception(
                    "Exception when calling create_namespaced_secret: %s\n" % e
                )
        else:
            raise
