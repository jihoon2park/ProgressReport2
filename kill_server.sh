#!/bin/bash

###############################################################################
# Flask 서버 종료 스크립트
# 
# 사용법:
#   ./kill_server.sh              # 모든 Flask 서버 종료
#   ./kill_server.sh --confirm    # 확인 없이 즉시 종료
#
# 작성: 2025-10-15
###############################################################################

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║     🛑 Flask 서버 종료 스크립트                                       ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# 실행 중인 Flask 프로세스 확인
FLASK_PROCESSES=$(ps aux | grep "python.*app.py" | grep -v grep)

if [ -z "$FLASK_PROCESSES" ]; then
    echo "ℹ️  실행 중인 Flask 서버가 없습니다."
    echo ""
    exit 0
fi

echo "실행 중인 Flask 프로세스:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$FLASK_PROCESSES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 확인 옵션이 없으면 사용자 확인 요청
if [ "$1" != "--confirm" ] && [ "$1" != "-y" ]; then
    read -p "이 프로세스들을 종료하시겠습니까? (y/N): " response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        echo "❌ 취소되었습니다."
        exit 0
    fi
fi

echo ""
echo "🔄 Flask 서버 종료 중..."
echo ""

# 1. 정상 종료 시도 (SIGTERM)
echo "1️⃣  정상 종료 시도 (SIGTERM)..."
pkill -f "python.*app.py" 2>/dev/null
sleep 2

# 2. 포트 5000 점유 프로세스 종료
echo "2️⃣  포트 5000 해제 중..."
fuser -k 5000/tcp 2>/dev/null
sleep 1

# 3. 강제 종료 (SIGKILL)
REMAINING=$(ps aux | grep "python.*app.py" | grep -v grep)
if [ ! -z "$REMAINING" ]; then
    echo "3️⃣  강제 종료 (SIGKILL)..."
    pkill -9 -f "python.*app.py" 2>/dev/null
    sleep 1
fi

# 4. 최종 확인
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FINAL_CHECK=$(ps aux | grep "python.*app.py" | grep -v grep)

if [ -z "$FINAL_CHECK" ]; then
    echo "✅ 모든 Flask 서버가 성공적으로 종료되었습니다!"
else
    echo "⚠️  일부 프로세스가 여전히 실행 중입니다:"
    echo "$FINAL_CHECK"
    echo ""
    echo "수동으로 종료하려면 다음 명령어를 사용하세요:"
    echo "  sudo kill -9 <PID>"
fi

# 5. 포트 상태 확인
echo ""
PORT_CHECK=$(lsof -ti:5000 2>/dev/null)
if [ -z "$PORT_CHECK" ]; then
    echo "✅ 포트 5000 사용 가능"
else
    echo "⚠️  포트 5000이 여전히 사용 중입니다 (PID: $PORT_CHECK)"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

