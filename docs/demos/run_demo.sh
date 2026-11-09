#!/bin/bash
# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Jayakrishna Ichapurapu
# module-id: 12d07a5e-b783fa7c
# Quick start script for Neo live coordination demo

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$NEO_DIR"

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║          NEO LIVE COORDINATION DEMO                            ║"
echo "║     See real-time multi-developer coordination in action       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

python3 demo_live_coordination.py
