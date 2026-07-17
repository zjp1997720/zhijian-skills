# Release security contract

Validation, candidate tests, and install checks run without GitHub tokens, credential-helper variables, repository-admin access, or live-network credentials. The release controller strips common token, password, secret, GitHub, SSH-agent, and askpass variables before candidate commands.

All content writes and Git pushes are restricted to the verified canonical `zjp1997720/zhijian-skills` repository. Repository creation is outside the publishing boundary. Tagging and repository administration use separately scoped credentials only after source and installation verification pass.
