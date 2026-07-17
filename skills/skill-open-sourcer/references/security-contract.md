# Release Security Contract

Validation, package export, candidate tests, and install checks run without GitHub tokens, credential-helper variables, repository-admin access, or live-network credentials. The release controller strips common token, password, secret, GitHub, SSH agent, and askpass variables before invoking candidate commands.

Content writes are restricted to the canonical repository and the Registry-declared mirror. Repository settings and archival use a separate short-lived administrative identity. Contribution redirect workflows use `pull_request_target` only for metadata actions, never check out or execute fork content, and request only `contents: read` plus `pull-requests: write`.
