# Cloud agents

Set up a Claude Code cloud environment so an agent can build and verify this
repo. Configure it at [claude.ai/code](https://claude.ai/code); the [cloud
environments](https://code.claude.com/docs/en/cloud-environments) page is the
reference.

## Runtimes

- **Node** comes from the image's nvm. `.node-version` pins the major version,
  and the environment's SessionStart hook activates it in each session.
- **Python** comes from uv, which installs the version the project pins. uv
  ships with the image.

If an environment lacks the Node hook, its setup script installs the pinned
version:

```bash
source /opt/nvm/nvm.sh
nvm install "$(cat <repo>/.node-version)"
```

A SessionStart hook then activates it and exports its bin directory, since
`CLAUDE_ENV_FILE` exists only inside a hook:

```bash
source /opt/nvm/nvm.sh
nvm use "$(cat "$CLAUDE_PROJECT_DIR/.node-version")" >/dev/null
echo "export PATH=\"$NVM_BIN:\$PATH\"" >> "$CLAUDE_ENV_FILE"
```

## Setup script

The setup script runs as root from the directory above the checkouts, before
the session starts. Install the repo's dependencies there:

```bash
if [ -d <repo> ]; then (cd <repo> && <install>); fi
```

## Network and secrets

- **Network:** the package registries, plus `nodejs.org` only when nvm has to
  download a Node version.
- **Secrets:** none. `<test>` and `<lint>` need no credentials. Save any API
  key a task needs as a network secret on the environment, never as an
  environment variable.

## Verify

```bash
<test>
<lint>
```
