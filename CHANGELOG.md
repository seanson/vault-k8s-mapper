### 0.3.1

- Updated handling for scenarios where vault KV is missing the target key or secret has been deleted and metadata remains
- Added more specific logging for targeting a specific broken secret path

### 0.3.0

- **Breaking** Set secret update method to "replace" rather than "patch" so deleted Vault secrets will no longer be present

### 0.2.4

- Reworked internal representation of vault path parsing
- Added support for environment variable targeting
- Added safeguard to skip vault keys that won't validate as k8s secret keys

### 0.1.2

- Initial release
