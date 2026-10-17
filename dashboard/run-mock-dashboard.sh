#!/bin/bash

# Mock Dashboard Startup Script
# Starts both the mock API server and React UI with mock data

set -e

echo "🚀 Starting Neo Mission Control Dashboard (Mock Mode)"
echo "=================================================="

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies..."
  npm install
fi

if [ ! -d "ui/node_modules" ]; then
  echo "📦 Installing UI dependencies..."
  cd ui && npm install && cd ..
fi

# Start mock API server in background
echo "🔧 Starting mock API server on port 3001..."
node api/mockServer.js &
API_PID=$!

# Wait for API to start
sleep 2

# Start React UI development server
echo "⚛️  Starting React UI on port 3000..."
cd ui
REACT_APP_API_URL=http://localhost:3001 npm start &
UI_PID=$!

# Cleanup function
cleanup() {
  echo ""
  echo "🛑 Shutting down..."
  kill $API_PID 2>/dev/null || true
  kill $UI_PID 2>/dev/null || true
  wait $API_PID $UI_PID 2>/dev/null || true
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Wait for both processes
wait $API_PID $UI_PID
