# 🏢 회사 내부 서버 배포 가이드

## 📋 사전 준비사항

### 서버 요구사항
- **OS**: Ubuntu 20.04+ 또는 CentOS 8+
- **RAM**: 최소 1GB (권장 2GB)
- **Storage**: 최소 10GB
- **Network**: 내부 네트워크 접근 가능

### 필수 소프트웨어 설치
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx openssl

# CentOS/RHEL
sudo yum update -y
sudo yum install -y python3 python3-pip nginx openssl
```

## 🚀 배포 실행

### 1. 파일 업로드
서버에 모든 애플리케이션 파일을 업로드합니다:
```bash
# SCP 사용 예시
scp -r ProgressReport/ username@192.168.1.100:/tmp/
```

### 2. 배포 스크립트 실행
```bash
# 서버에서 실행
cd /tmp/ProgressReport
chmod +x deploy_internal.sh

# 기본 설정으로 배포 (IP: 192.168.1.100)
sudo ./deploy_internal.sh

# 또는 사용자 정의 IP로 배포
sudo ./deploy_internal.sh 192.168.1.50

# 또는 사용자 정의 IP와 경로로 배포
sudo ./deploy_internal.sh 192.168.1.50 /opt/progressreport
```

### 3. 접속 확인
배포 완료 후 다음 URL로 접속:
- **HTTP**: `http://192.168.1.100`
- **HTTPS**: `https://192.168.1.100` (자체 서명 인증서)

> ⚠️ **SSL 경고**: 자체 서명 인증서를 사용하므로 브라우저에서 보안 경고가 나타납니다. "고급" → "안전하지 않음으로 이동"을 클릭하여 접속하세요.

## ⚙️ 설정 수정

### IP 주소 변경
`nginx_internal.conf` 파일의 `server_name` 수정:
```nginx
server_name progressreport.company.local 192.168.1.100;  # 여기서 변경
```

### 내부 도메인 사용
회사 DNS에 다음 레코드 추가:
```
progressreport.company.local    A    192.168.1.100
```

### 방화벽 허용 IP 대역 변경
`nginx_internal.conf`에서 허용할 IP 대역 수정:
```nginx
allow 192.168.0.0/16;   # 회사 네트워크 대역으로 변경
allow 10.0.0.0/8;       # 필요한 대역만 유지
deny all;
```

## 🔧 관리 명령어

### 서비스 관리
```bash
# 상태 확인
sudo systemctl status progressreport

# 재시작
sudo systemctl restart progressreport

# 중지
sudo systemctl stop progressreport

# 시작
sudo systemctl start progressreport

# 자동 시작 비활성화
sudo systemctl disable progressreport
```

### 로그 확인
```bash
# 애플리케이션 로그 (실시간)
sudo journalctl -u progressreport -f

# Nginx 에러 로그
sudo tail -f /var/log/nginx/error.log

# Nginx 액세스 로그
sudo tail -f /var/log/nginx/access.log
```

### 업데이트
```bash
# 애플리케이션 업데이트
cd /var/www/progressreport
sudo git pull  # Git 사용시
sudo systemctl restart progressreport

# 또는 파일 직접 교체
sudo cp /tmp/new_app.py /var/www/progressreport/
sudo systemctl restart progressreport
```

## 🔒 보안 고려사항

### 내부 네트워크만 접근 허용
- Nginx 설정에서 내부 IP 대역만 허용
- 방화벽에서 내부 네트워크만 허용

### 정기적인 업데이트
```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y  # Ubuntu
sudo yum update -y                       # CentOS

# Python 패키지 업데이트
cd /var/www/progressreport
sudo ./venv/bin/pip install --upgrade -r requirements.txt
sudo systemctl restart progressreport
```

### 백업
```bash
# 애플리케이션 백업
sudo tar -czf /backup/progressreport_$(date +%Y%m%d).tar.gz /var/www/progressreport

# 데이터베이스 백업 (SQLite)
sudo cp /var/www/progressreport/*.db /backup/
```

## 🆘 문제 해결

### 서비스가 시작되지 않음
```bash
# 로그 확인
sudo journalctl -u progressreport --no-pager

# 설정 파일 검증
sudo /var/www/progressreport/venv/bin/python /var/www/progressreport/app.py
```

### Nginx 오류
```bash
# 설정 파일 검증
sudo nginx -t

# 재시작
sudo systemctl restart nginx
```

### 포트 충돌
```bash
# 포트 사용 확인
sudo netstat -tlnp | grep :8000
sudo ss -tlnp | grep :8000
```

## 📞 지원 정보

문제 발생시 다음 정보를 수집하여 지원팀에 전달:
1. 에러 로그: `sudo journalctl -u progressreport --no-pager`
2. 시스템 정보: `uname -a && cat /etc/os-release`
3. 서비스 상태: `sudo systemctl status progressreport nginx` 