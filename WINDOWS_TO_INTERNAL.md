# 💻 윈도우에서 내부 서버로 배포하기

## 🎯 개요
윈도우 개발 환경에서 회사 내부 Linux 서버로 애플리케이션을 배포하는 방법입니다.

## 📋 필요한 도구

### 1. WinSCP (파일 전송)
- **다운로드**: https://winscp.net/
- **용도**: 윈도우에서 Linux 서버로 파일 전송

### 2. PuTTY (SSH 접속)
- **다운로드**: https://www.putty.org/
- **용도**: Linux 서버에 원격 접속

### 3. PowerShell (선택사항)
- 윈도우 내장, SCP 명령어 사용 가능

## 🚀 배포 단계별 진행

### **1단계: 파일 준비**
```powershell
# PowerShell에서 프로젝트 디렉토리로 이동
cd C:\Users\it.support\PycharmProjects\ProgressReport

# 배포용 파일들이 있는지 확인
ls deploy_internal.sh, nginx_internal.conf, requirements.txt
```

### **2단계: WinSCP로 파일 전송**

#### WinSCP 설정:
1. **Host name**: `192.168.1.100` (내부 서버 IP)
2. **User name**: 서버 계정 (예: `ubuntu`, `admin`)
3. **Password**: 서버 비밀번호
4. **Port**: `22` (SSH 기본 포트)

#### 파일 전송:
```
로컬 디렉토리: C:\Users\it.support\PycharmProjects\ProgressReport\
원격 디렉토리: /tmp/ProgressReport/

전송할 파일들:
- *.py (모든 Python 파일)
- templates/ (폴더)
- static/ (폴더)
- requirements.txt
- gunicorn.conf.py
- deploy_internal.sh
- nginx_internal.conf
- .env
```

### **3단계: PuTTY로 서버 접속**

#### PuTTY 설정:
1. **Host Name**: `192.168.1.100`
2. **Port**: `22`
3. **Connection type**: `SSH`

#### 서버 접속 후 실행:
```bash
# 업로드된 디렉토리로 이동
cd /tmp/ProgressReport

# 스크립트 실행 권한 부여
chmod +x deploy_internal.sh

# 배포 실행
sudo ./deploy_internal.sh 192.168.1.100
```

### **4단계: PowerShell 사용 (고급)**

```powershell
# SCP로 직접 파일 전송 (PowerShell 7+ 필요)
scp -r C:\Users\it.support\PycharmProjects\ProgressReport\ username@192.168.1.100:/tmp/

# SSH로 서버 접속하여 명령 실행
ssh username@192.168.1.100 "cd /tmp/ProgressReport && chmod +x deploy_internal.sh && sudo ./deploy_internal.sh"
```

## ⚙️ 내부 서버 설정 맞춤화

### IP 주소 변경
회사 내부 서버 IP에 맞게 설정:

**nginx_internal.conf** 수정:
```bash
# 서버에서 실행
sudo nano /etc/nginx/sites-available/progressreport

# server_name 줄을 찾아서 수정
server_name progressreport.company.local 192.168.1.50;  # 실제 서버 IP
```

### 방화벽 허용 IP 대역
회사 네트워크 대역에 맞게 수정:
```nginx
# 192.168.1.0/24 대역만 허용하는 경우
allow 192.168.1.0/24;
deny all;

# 여러 대역 허용하는 경우
allow 192.168.1.0/24;    # 개발팀
allow 192.168.2.0/24;    # 의료진
allow 10.0.0.0/8;        # VPN
deny all;
```

## 🔧 배포 후 관리

### 접속 확인
```bash
# 서버 상태 확인
sudo systemctl status progressreport

# 웹 서비스 테스트
curl http://localhost
curl http://192.168.1.100
```

### 로그 모니터링
```bash
# 실시간 로그 확인
sudo journalctl -u progressreport -f

# 최근 에러 확인
sudo journalctl -u progressreport --since "1 hour ago" | grep ERROR
```

### 업데이트 방법
1. **WinSCP**로 수정된 파일들 다시 전송
2. **PuTTY**로 서버 접속
3. 파일 복사 및 서비스 재시작:
```bash
# 수정된 파일 복사
sudo cp /tmp/ProgressReport/app.py /var/www/progressreport/
sudo cp /tmp/ProgressReport/templates/* /var/www/progressreport/templates/

# 서비스 재시작
sudo systemctl restart progressreport
```

## 🌐 접속 정보

배포 완료 후 다음 주소로 접속:

### 직접 IP 접속
- **HTTP**: `http://192.168.1.100`
- **HTTPS**: `https://192.168.1.100`

### 내부 도메인 (DNS 설정 필요)
```
# 회사 DNS 서버에 추가
progressreport.company.local    A    192.168.1.100

# 접속 주소
http://progressreport.company.local
https://progressreport.company.local
```

### 윈도우 hosts 파일 수정 (임시방법)
```
# C:\Windows\System32\drivers\etc\hosts 파일에 추가
192.168.1.100    progressreport.company.local

# 그 후 접속
http://progressreport.company.local
```

## 🔒 보안 고려사항

### SSL 인증서 경고
- 자체 서명 인증서 사용으로 브라우저 경고 발생
- 브라우저에서 "고급" → "안전하지 않음으로 이동" 클릭

### 회사 보안 정책 준수
```bash
# 로그 보존 기간 설정
sudo journalctl --vacuum-time=30d

# 자동 업데이트 설정
sudo crontab -e
# 매주 일요일 새벽 2시 보안 업데이트
0 2 * * 0 apt update && apt upgrade -y
```

## 📞 문제 해결

### 연결 안됨
1. **방화벽 확인**: 내부 네트워크에서 80, 443 포트 허용되는지
2. **IP 확인**: `ping 192.168.1.100`
3. **서비스 상태**: `sudo systemctl status progressreport nginx`

### 권한 에러
```bash
# 파일 권한 재설정
sudo chown -R www-data:www-data /var/www/progressreport
sudo chmod -R 755 /var/www/progressreport
```

### 포트 충돌
```bash
# 포트 사용 확인
sudo netstat -tlnp | grep :8000
sudo netstat -tlnp | grep :80

# 다른 포트로 변경 필요시
sudo nano /var/www/progressreport/gunicorn.conf.py
``` 