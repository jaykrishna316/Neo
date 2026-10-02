#!/bin/bash
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
