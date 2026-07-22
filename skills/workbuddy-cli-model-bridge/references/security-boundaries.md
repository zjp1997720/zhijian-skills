# Security boundaries

The bridge handles subscription OAuth credentials and a local client key. Treat it as credential-bearing infrastructure.

## Network exposure

- Bind CLIProxyAPI to `127.0.0.1` or another explicit loopback address.
- Keep remote management disabled.
- Do not open the service through a tunnel, public reverse proxy, LAN bind, or firewall rule as part of this Skill.
- A pre-existing non-loopback bind is a conflict. Explain the impact before changing it.

## Credential separation

Three credential classes have separate lifecycles:

1. native CLI login state
2. CLIProxyAPI Provider OAuth files
3. WorkBuddy's local proxy client key

Do not rotate the WorkBuddy key when only Provider OAuth expired. Do not copy native CLI token contents into CLIProxyAPI. Do not put Provider credentials in WorkBuddy.

The bridge stores its dedicated proxy client key in a mode-`0600` local file and writes the same key into CLIProxyAPI and managed WorkBuddy entries. Reports expose only existence, counts, and a one-way digest.

## Files and backups

Apply mode `0600` to:

- bridge secret and state files
- CLIProxyAPI config when it contains client keys
- CLIProxyAPI OAuth JSON files
- WorkBuddy `models.json`
- backups of any credential-bearing file

Backups stay beside their source with a timestamp. Do not copy them into a repository, shared folder, cloud-synced workspace, or generated report.

## Provider and subscription boundaries

- Use accounts owned and authorized by the user.
- Respect Provider terms, plan limits, concurrency limits, and rate limits.
- Do not automate block resets, bypass quota enforcement, disguise unsupported clients, or pool credentials without explicit Provider support.
- Do not promise that a subscription permits third-party proxy use. Report the integration method and let the user verify their agreement when terms are unclear.

## Manifest trust

Provider manifests may supply a CLIProxyAPI login flag. The bridge passes it directly as a single subprocess argument and never evaluates it in a shell. Even so:

- inspect local override manifests before authorization
- accept only `--flag` values
- prefer official CLIProxyAPI flags
- never add install commands, arbitrary shell, environment-variable expansion, or credentials to manifests

## Logs and output

Do not print:

- API keys or Authorization headers
- OAuth token contents
- one-time device codes after the user has authorized
- account email addresses
- raw prompts, images, or WorkBuddy conversation content

Diagnostic output may include local file paths, model IDs, Provider IDs, status codes, redacted error messages, and backup paths.
