# MindForge one-click commands
# Run `just --list` to see all available commands.

# Run fake dogfood end-to-end (no API keys, no network)
dogfood:
    bash scripts/fake_dogfood.sh

# Default: run dogfood
default: dogfood
