#!/bin/bash

# 내부 서버 배포 스크립트
# Usage: ./deploy_internal.sh [server_ip] [app_path]

set -e

SERVER_IP=${1:-"192.168.1.100"}
APP_PATH=${2:-"/var/www/progressreport"}
APP_NAME="progressreport"

echo "🏢 회사 내부 서버 배포 시작..."
echo "📍 서버 IP: $SERVER_IP"
echo "📁 배포 경로: $APP_PATH"

# 애플리케이션 디렉토리 생성
echo "📁 애플리케이션 디렉토리 설정..."
sudo mkdir -p $APP_PATH
sudo mkdir -p $APP_PATH/logs
sudo mkdir -p $APP_PATH/static

# 파일 복사
echo "📋 애플리케이션 파일 복사..."
sudo cp -r *.py templates static $APP_PATH/
sudo cp requirements.txt $APP_PATH/
sudo cp gunicorn.conf.py $APP_PATH/
sudo cp .env $APP_PATH/

# 환경 설정 수정 (내부 서버용)
echo "⚙️ 내부 서버용 환경 설정..."
sudo tee $APP_PATH/.env > /dev/null <<EOF
ENVIRONMENT=production

# 내부 서버 설정
PROD_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(16))')
PROD_DEBUG=False
PROD_HOST=0.0.0.0
PROD_PORT=8000
PROD_LOG_LEVEL=INFO

# 내부 네트워크 설정
INTERNAL_NETWORK=true
ALLOW_INSECURE_HTTP=true

# 개발 설정 (필요시)
DEV_SECRET_KEY=dev-secret-key
DEV_DEBUG=True
DEV_HOST=127.0.0.1
DEV_PORT=5000
DEV_LOG_LEVEL=DEBUG
EOF

# Python 가상환경 생성
echo "🐍 Python 가상환경 설정..."
sudo python3 -m venv $APP_PATH/venv
sudo $APP_PATH/venv/bin/pip install --upgrade pip
sudo $APP_PATH/venv/bin/pip install -r $APP_PATH/requirements.txt

# 데이터베이스 초기화 (첫 배포 시에만)
echo "🗄️ 데이터베이스 초기화..."
cd $APP_PATH
if [ ! -f "progress_report.db" ]; then
    echo "데이터베이스가 존재하지 않음. 초기화 실행..."
    sudo -u www-data $APP_PATH/venv/bin/python init_database.py
    if [ $? -eq 0 ]; then
        echo "✅ 데이터베이스 초기화 완료"
    else
        echo "❌ 데이터베이스 초기화 실패 - 간단한 초기화 시도"
        sudo -u www-data $APP_PATH/venv/bin/python init_database_simple.py
    fi
else
    echo "✅ 기존 데이터베이스 발견 - 초기화 건너뜀"
fi

# Systemd 서비스 생성 (내부 서버용)
echo "🔧 Systemd 서비스 설정..."
sudo tee /etc/systemd/system/$APP_NAME.service > /dev/null <<EOF
[Unit]
Description=Progress Report Web Application (Internal)
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=$APP_PATH
Environment=PATH=$APP_PATH/venv/bin
EnvironmentFile=$APP_PATH/.env
ExecStart=$APP_PATH/venv/bin/gunicorn --config $APP_PATH/gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

# 내부 서버용 보안 설정 (완화)
NoNewPrivileges=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

# Nginx 설정
echo "🌐 Nginx 설정..."
sudo cp nginx_internal.conf /etc/nginx/sites-available/$APP_NAME
sudo ln -sf /etc/nginx/sites-available/$APP_NAME /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# SSL 인증서 생성 (자체 서명 - 내부용)
echo "🔐 SSL 인증서 생성 (자체 서명)..."
sudo mkdir -p /etc/nginx/ssl
if [ ! -f /etc/nginx/ssl/progressreport.crt ]; then
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /etc/nginx/ssl/progressreport.key \
        -out /etc/nginx/ssl/progressreport.crt \
        -subj "/C=AU/ST=SA/L=Adelaide/O=Company/CN=$SERVER_IP"
fi

# 권한 설정
echo "🔒 파일 권한 설정..."
sudo chown -R www-data:www-data $APP_PATH
sudo chmod -R 755 $APP_PATH
sudo chmod 600 $APP_PATH/.env

# SQLite 데이터베이스 파일 권한 설정
if [ -f "$APP_PATH/progress_report.db" ]; then
    sudo chown www-data:www-data $APP_PATH/progress_report.db
    sudo chmod 664 $APP_PATH/progress_report.db
    echo "✅ SQLite 데이터베이스 권한 설정 완료"
fi

# 데이터베이스 디렉토리 쓰기 권한 확인 (SQLite WAL 파일용)
sudo chmod 775 $APP_PATH

# 방화벽 설정 (내부 네트워크용)
echo "🔥 방화벽 설정..."
if command -v ufw &> /dev/null; then
    sudo ufw allow from 192.168.0.0/16 to any port 80
    sudo ufw allow from 192.168.0.0/16 to any port 443
    sudo ufw allow from 10.0.0.0/8 to any port 80
    sudo ufw allow from 10.0.0.0/8 to any port 443
    sudo ufw allow from 172.16.0.0/12 to any port 80
    sudo ufw allow from 172.16.0.0/12 to any port 443
fi

# 서비스 시작
echo "🚀 서비스 시작..."
sudo systemctl daemon-reload
sudo systemctl enable $APP_NAME
sudo systemctl start $APP_NAME
sudo systemctl restart nginx

# 상태 확인
echo "✅ 배포 완료!"
echo ""
echo "📊 서비스 상태:"
sudo systemctl status $APP_NAME --no-pager -l
echo ""
echo "🌐 접속 정보:"
echo "  HTTP:  http://$SERVER_IP"
echo "  HTTPS: https://$SERVER_IP (자체 서명 인증서)"
echo "  내부 도메인: http://progressreport.company.local"
echo ""
echo "📝 로그 확인:"
echo "  애플리케이션: sudo journalctl -u $APP_NAME -f"
echo "  Nginx: sudo tail -f /var/log/nginx/error.log"
echo ""
echo "🔧 관리 명령어:"
echo "  재시작: sudo systemctl restart $APP_NAME"
echo "  중지: sudo systemctl stop $APP_NAME"
echo "  상태: sudo systemctl status $APP_NAME" 