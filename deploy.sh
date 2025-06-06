#!/bin/bash

# Progress Report 배포 스크립트
# Ubuntu/Debian 서버용

set -e  # 에러 발생 시 스크립트 중단

echo "🚀 Progress Report 배포 시작..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 변수 설정
APP_DIR="/var/www/progressreport"
SERVICE_NAME="progressreport"
NGINX_CONFIG="/etc/nginx/sites-available/progressreport"
DOMAIN="your-domain.com"

# 1. 시스템 업데이트
echo -e "${YELLOW}📦 시스템 패키지 업데이트...${NC}"
sudo apt update && sudo apt upgrade -y

# 2. 필요한 패키지 설치
echo -e "${YELLOW}📦 필요한 패키지 설치...${NC}"
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git

# 3. 애플리케이션 디렉토리 생성
echo -e "${YELLOW}📁 애플리케이션 디렉토리 설정...${NC}"
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# 4. 소스 코드 복사 (git clone 또는 파일 복사)
echo -e "${YELLOW}📋 소스 코드 배포...${NC}"
cp -r . $APP_DIR/
cd $APP_DIR

# 5. Python 가상환경 설정
echo -e "${YELLOW}🐍 Python 가상환경 설정...${NC}"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 6. 환경변수 설정
echo -e "${YELLOW}⚙️ 환경변수 설정...${NC}"
if [ ! -f .env ]; then
    echo "ENVIRONMENT=production" > .env
    echo "SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')" >> .env
    echo "PROD_HOST=0.0.0.0" >> .env
    echo "PROD_PORT=8000" >> .env
    echo "PROD_FLASK_DEBUG=False" >> .env
    echo "PROD_LOG_LEVEL=WARNING" >> .env
fi

# 7. 로그 디렉토리 생성
echo -e "${YELLOW}📝 로그 디렉토리 생성...${NC}"
sudo mkdir -p /var/log/progressreport
sudo chown www-data:www-data /var/log/progressreport

# 8. Systemd 서비스 파일 생성
echo -e "${YELLOW}🔧 Systemd 서비스 설정...${NC}"
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Gunicorn instance to serve Progress Report
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn.conf.py app:app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 9. Nginx 설정
echo -e "${YELLOW}🌐 Nginx 설정...${NC}"
sudo cp nginx.conf $NGINX_CONFIG
sudo sed -i "s/your-domain.com/$DOMAIN/g" $NGINX_CONFIG
sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# 10. SSL 인증서 발급 (Let's Encrypt)
echo -e "${YELLOW}🔒 SSL 인증서 발급...${NC}"
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# 11. 서비스 시작
echo -e "${YELLOW}🚀 서비스 시작...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME
sudo systemctl enable nginx
sudo systemctl restart nginx

# 12. 상태 확인
echo -e "${YELLOW}✅ 배포 상태 확인...${NC}"
sudo systemctl status $SERVICE_NAME --no-pager
sudo systemctl status nginx --no-pager

echo -e "${GREEN}🎉 배포 완료!${NC}"
echo -e "${GREEN}웹사이트: https://$DOMAIN${NC}"
echo -e "${YELLOW}서비스 관리 명령어:${NC}"
echo -e "  서비스 재시작: sudo systemctl restart $SERVICE_NAME"
echo -e "  로그 확인: sudo journalctl -u $SERVICE_NAME -f"
echo -e "  Nginx 재시작: sudo systemctl restart nginx" 