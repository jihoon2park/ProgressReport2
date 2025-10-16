#!/bin/bash

###############################################################################
# Flask 서버 시작 스크립트
# 
# 사용법:
#   ./start_server.sh              # 포그라운드로 서버 시작
#   ./start_server.sh --background # 백그라운드로 서버 시작
#   ./start_server.sh --bg         # 백그라운드로 서버 시작 (단축)
#
# 작성: 2025-10-15
###############################################################################

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║     🚀 Flask 서버 시작 스크립트                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# 프로젝트 디렉토리로 이동
cd /home/itsupport/DEV_code/ProgressReport2

# 실행 중인 서버 확인
EXISTING=$(ps aux | grep "python.*app.py" | grep -v grep)
if [ ! -z "$EXISTING" ]; then
    echo "⚠️  이미 실행 중인 Flask 서버가 있습니다:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$EXISTING"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    read -p "기존 서버를 종료하고 새로 시작하시겠습니까? (y/N): " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "🔄 기존 서버 종료 중..."
        ./kill_server.sh --confirm
        sleep 2
    else
        echo "❌ 취소되었습니다."
        exit 0
    fi
fi

# 포트 5000 확인
PORT_CHECK=$(lsof -ti:5000 2>/dev/null)
if [ ! -z "$PORT_CHECK" ]; then
    echo "⚠️  포트 5000이 다른 프로그램에 의해 사용 중입니다 (PID: $PORT_CHECK)"
    echo "종료하려면: kill -9 $PORT_CHECK"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Flask 서버 시작 중..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 백그라운드 모드 확인
if [ "$1" == "--background" ] || [ "$1" == "--bg" ] || [ "$1" == "-b" ]; then
    echo "📦 백그라운드 모드로 시작..."
    LOG_FILE="/tmp/flask_server_$(date +%Y%m%d_%H%M%S).log"
    .venv/bin/python app.py > "$LOG_FILE" 2>&1 &
    SERVER_PID=$!
    
    sleep 3
    
    # 서버 시작 확인
    if ps -p $SERVER_PID > /dev/null 2>&1; then
        echo "✅ 서버가 백그라운드에서 시작되었습니다!"
        echo ""
        echo "서버 정보:"
        echo "  • PID: $SERVER_PID"
        echo "  • URL: http://127.0.0.1:5000"
        echo "  • 로그 파일: $LOG_FILE"
        echo ""
        echo "로그 모니터링:"
        echo "  tail -f $LOG_FILE"
        echo ""
        echo "서버 종료:"
        echo "  ./kill_server.sh"
        echo "  또는 kill $SERVER_PID"
    else
        echo "❌ 서버 시작 실패! 로그 확인:"
        echo "  cat $LOG_FILE"
    fi
else
    echo "📺 포그라운드 모드로 시작..."
    echo "   (종료하려면 Ctrl+C)"
    echo ""
    .venv/bin/python app.py
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

