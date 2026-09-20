source ../../support/fake-codex/setup.sh
install_codex ./codex
init_repo

# This machine has an interpreter, but not under the name the skill reaches for.
mv "$(command -v python3)" /usr/local/bin/python
ln -sf /usr/local/bin/python /usr/bin/python
