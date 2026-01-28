#!/bin/bash

###############################################################################
# Flask Server Start Script
# 
# Usage:
#   ./start_server.sh              # Start server in foreground
#   ./start_server.sh --background # Start server in background
#   ./start_server.sh --bg         # Start server in background (short)
#
# Created: 2025-10-15
###############################################################################

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║     🚀 Flask Server Start Script                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# Change to project directory
cd /home/itsupport/DEV_code/ProgressReport2

# Check for running server
EXISTING=$(ps aux | grep "python.*app.py" | grep -v grep)
if [ ! -z "$EXISTING" ]; then
    echo "⚠️  Flask server is already running:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$EXISTING"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    read -p "Do you want to stop the existing server and start a new one? (y/N): " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "🔄 Stopping existing server..."
        ./kill_server.sh --confirm
        sleep 2
    else
        echo "❌ Cancelled."
        exit 0
    fi
fi

# Check port 5000
PORT_CHECK=$(lsof -ti:5000 2>/dev/null)
if [ ! -z "$PORT_CHECK" ]; then
    echo "⚠️  Port 5000 is in use by another program (PID: $PORT_CHECK)"
    echo "To stop it: kill -9 $PORT_CHECK"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Starting Flask server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check background mode
if [ "$1" == "--background" ] || [ "$1" == "--bg" ] || [ "$1" == "-b" ]; then
    echo "📦 Starting in background mode..."
    LOG_FILE="/tmp/flask_server_$(date +%Y%m%d_%H%M%S).log"
    .venv/bin/python app.py > "$LOG_FILE" 2>&1 &
    SERVER_PID=$!
    
    sleep 3
    
    # Check server start
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "✅ Server started in background!"
        echo ""
        echo "Server information:"
        echo "  • PID: $SERVER_PID"
        echo "  • URL: http://127.0.0.1:5000"
        echo "  • Log file: $LOG_FILE"
        echo ""
        echo "Log monitoring:"
        echo "  tail -f $LOG_FILE"
        echo ""
        echo "Stop server:"
        echo "  ./kill_server.sh"
        echo "  or kill $SERVER_PID"
    else
        echo "❌ Server start failed! Check logs:"
        echo "  cat $LOG_FILE"
    fi
else
    echo "📺 Starting in foreground mode..."
    echo "   (Press Ctrl+C to stop)"
    echo ""
    .venv/bin/python app.py
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

