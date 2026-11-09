#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Jayakrishna Ichapurapu
# module-id: 12d07a5e-9fc91c13
# Starts the Neo MCP server from the repo's own virtualenv, whatever the caller's working directory.
cd "$(dirname "$0")/.." || exit 1
exec .venv/bin/python -m ide.mcp_neo_server
