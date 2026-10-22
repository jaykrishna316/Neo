#!/usr/bin/env bash
# Starts the Neo MCP server from the repo's own virtualenv, whatever the caller's working directory.
cd "$(dirname "$0")/.." || exit 1
exec .venv/bin/python -m ide.mcp_neo_server
