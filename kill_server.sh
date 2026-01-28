#!/bin/bash

###############################################################################
# Flask Server Stop Script
# 
# Usage:
#   ./kill_server.sh              # Stop all Flask servers
#   ./kill_server.sh --confirm    # Stop immediately without confirmation
#
# Created: 2025-10-15
###############################################################################

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║     🛑 Flask Server Stop Script                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check for running Flask processes
FLASK_PROCESSES=$(ps aux | grep "python.*app.py" | grep -v grep)

if [ -z "$FLASK_PROCESSES" ]; then
    echo "ℹ️  No Flask server is running."
    echo ""
    exit 0
fi

echo "Running Flask processes:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$FLASK_PROCESSES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# # Request user confirmation if no confirm option
# if [ "$1" != "--confirm" ] && [ "$1" != "-y" ]; then
#     read -p "Do you want to stop these processes? (y/N): " response
#     if [[ ! "$response" =~ ^[Yy]$ ]]; then
#         echo "❌ Cancelled."
#         exit 0
#     fi
# fi

echo ""
echo "🔄 Stopping Flask server..."
echo ""

# 1. Try graceful shutdown (SIGTERM)
echo "1️⃣  Attempting graceful shutdown (SIGTERM)..."
pkill -f "python.*app.py" 2>/dev/null
sleep 2

# 2. Stop processes occupying port 5000
echo "2️⃣  Releasing port 5000..."
fuser -k 5000/tcp 2>/dev/null
sleep 1

# 3. Force kill (SIGKILL)
REMAINING=$(ps aux | grep "python.*app.py" | grep -v grep)
if [ ! -z "$REMAINING" ]; then
    echo "3️⃣  Force kill (SIGKILL)..."
    pkill -9 -f "python.*app.py" 2>/dev/null
    sleep 1
fi

# 4. Final check
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FINAL_CHECK=$(ps aux | grep "python.*app.py" | grep -v grep)

if [ -z "$FINAL_CHECK" ]; then
    echo "✅ All Flask servers stopped successfully!"
else
    echo "⚠️  Some processes are still running:"
    echo "$FINAL_CHECK"
    echo ""
    echo "To stop manually, use the following command:"
    echo "  sudo kill -9 <PID>"
fi

# 5. Check port status
echo ""
PORT_CHECK=$(lsof -ti:5000 2>/dev/null)
if [ -z "$PORT_CHECK" ]; then
    echo "✅ Port 5000 is available"
else
    echo "⚠️  Port 5000 is still in use (PID: $PORT_CHECK)"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

