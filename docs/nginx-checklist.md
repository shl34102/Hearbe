# Nginx 서버 체크리스트 (확인 명령어 + 예시)

## 0) 가장 먼저 하는 공통 점검

### ✅ 설정 문법/적용 상태

```bash
sudo nginx -t
sudo systemctl status nginx --no-pager
sudo systemctl reload nginx
```

### ✅ 실제로 어떤 설정을 읽는지(풀 설정 덤프)

```bash
sudo nginx -T | less
```

---

## 1) 전역 설정 (http 블록)

### 1-1. server_tokens off

**확인**

```bash
sudo nginx -T | grep -n "server_tokens"
curl -I https://YOUR_DOMAIN | grep -i server
```

**예시**

```nginx
http {
  server_tokens off;
}
```

---

### 1-2. TLS 버전 TLSv1.2 / TLSv1.3만

**확인(설정)**

```bash
sudo nginx -T | grep -n "ssl_protocols"
```

**확인(실제 핸드셰이크)**

```bash
# TLS1.0/1.1이 실패해야 정상
echo | openssl s_client -connect YOUR_DOMAIN:443 -tls1_1 2>/dev/null | grep -E "Protocol|Cipher|alert"
echo | openssl s_client -connect YOUR_DOMAIN:443 -tls1_2 2>/dev/null | grep -E "Protocol|Cipher"
echo | openssl s_client -connect YOUR_DOMAIN:443 -tls1_3 2>/dev/null | grep -E "Protocol|Cipher"
```

**예시**

```nginx
http {
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_prefer_server_ciphers off; # TLS1.3에선 의미 적고, 보통 off 권장
}
```

---

### 1-3. rate limit zone 정의 (limit_req_zone)

**확인**

```bash
sudo nginx -T | grep -n "limit_req_zone"
sudo nginx -T | grep -n "limit_req "
```

**예시**

```nginx
http {
  # IP당 초당 10req, 버스트 20 정도
  limit_req_zone $binary_remote_addr zone=api_rl:10m rate=10r/s;
}
```

---

### 1-4. 로그 경로/권한

**확인**

```bash
sudo nginx -T | grep -n "access_log\|error_log"
ls -l /var/log/nginx
sudo -u www-data test -w /var/log/nginx && echo "writable" || echo "not writable"
```

**실시간 로그 확인**

```bash
sudo tail -n 100 /var/log/nginx/error.log
sudo tail -n 100 /var/log/nginx/access.log
```

---

### 1-5. gzip (필요할 때만)

**확인**

```bash
sudo nginx -T | grep -n "gzip"
curl -I https://YOUR_DOMAIN | grep -i "content-encoding"
```

**예시(정적/텍스트만)**

```nginx
http {
  gzip on;
  gzip_types text/plain text/css application/json application/javascript;
  gzip_min_length 1024;
}
```

---

## 2) 서버 블록 (HTTPS)

### 2-1. HSTS 적용 여부

**확인**

```bash
curl -I https://YOUR_DOMAIN | grep -i strict-transport-security
```

**예시(전체 서브도메인도 https 확실할 때만)**

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
# preload까지는 신중하게
```

---

### 2-2. Security Headers (최소 nosniff, referrer-policy)

**확인**

```bash
curl -I https://YOUR_DOMAIN | egrep -i "x-content-type-options|referrer-policy|content-security-policy|x-frame-options"
```

**예시(최소 세트)**

```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

---

### 2-3. 닷파일/숨김 경로 차단(단, /.well-known 허용)

**확인(설정 존재 여부)**

```bash
sudo nginx -T | grep -n "\.well-known\|location ~"
```

**예시**

```nginx
# /.well-known은 인증서 갱신 등에 필요할 수 있음
location ^~ /.well-known/ { allow all; }

# 나머지 dotfile 차단
location ~ /\.(?!well-known) {
  deny all;
  access_log off;
  log_not_found off;
}
```

---

### 2-4. API location에 limit_req 적용

**확인**

```bash
sudo nginx -T | grep -n "location /api\|limit_req"
```

**예시**

```nginx
location /api/ {
  limit_req zone=api_rl burst=20 nodelay;
  proxy_pass http://upstream_api;
}
```

---

### 2-5. Proxy headers 세팅

**확인**

```bash
sudo nginx -T | grep -n "proxy_set_header"
```

**예시**

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

---

## 3) TLS / Certbot

### 3-1. 인증서/키 경로 유효

**확인(nginx 설정에서 경로 확인)**

```bash
sudo nginx -T | grep -n "ssl_certificate\|ssl_certificate_key"
```

**확인(파일 존재/권한)**

```bash
sudo ls -l /etc/letsencrypt/live/YOUR_DOMAIN/
sudo openssl x509 -in /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem -noout -dates -issuer -subject
```

---

### 3-2. options-ssl-nginx.conf include 존재

**확인**

```bash
sudo nginx -T | grep -n "options-ssl-nginx.conf"
sudo ls -l /etc/letsencrypt/options-ssl-nginx.conf
```

---

### 3-3. ssl_dhparam 존재

**확인**

```bash
sudo nginx -T | grep -n "ssl_dhparam"
sudo ls -l /etc/letsencrypt/ssl-dhparams.pem
```

---

## 4) Redirects / HTTP(80)

### 4-1. HTTP → HTTPS 리다이렉트

**확인**

```bash
curl -I http://YOUR_DOMAIN
# Location: https://... 나 301/308 확인
```

**예시**

```nginx
server {
  listen 80;
  server_name YOUR_DOMAIN;

  return 301 https://$host$request_uri;
}
```

---

### 4-2. 의도치 않은 default_server 노출

**확인**

```bash
sudo nginx -T | grep -n "default_server"
```

**권장(기본 서버는 명시적으로 차단/드랍) 예시**

```nginx
server {
  listen 80 default_server;
  server_name _;
  return 444;
}
```

---

## 5) 선택 항목 (필요할 때만)

### 5-1. client_max_body_size

**확인**

```bash
sudo nginx -T | grep -n "client_max_body_size"
```

**예시**

```nginx
client_max_body_size 20m;
```

---

### 5-2. timeouts

**확인**

```bash
sudo nginx -T | grep -n "proxy_read_timeout\|proxy_connect_timeout\|proxy_send_timeout"
```

**예시**

```nginx
proxy_connect_timeout 5s;
proxy_send_timeout 30s;
proxy_read_timeout 30s;
```

---

### 5-3. IP allowlist / WAF/CDN (필요 시)

**확인(allow/deny 존재)**

```bash
sudo nginx -T | grep -n "allow\|deny"
```

**예시(관리자 엔드포인트 제한)**

```nginx
location /admin/ {
  allow 1.2.3.4;   # 사무실 IP 등
  deny all;
}
```

---

## 마지막: “지금 서버가 안전하게 떠있는지” 빠른 실전 체크 5개

```bash
# 1) HTTPS 강제 여부
curl -I http://YOUR_DOMAIN

# 2) 핵심 헤더 확인
curl -I https://YOUR_DOMAIN | egrep -i "strict-transport-security|x-content-type-options|referrer-policy"

# 3) TLS 버전 확인
echo | openssl s_client -connect YOUR_DOMAIN:443 -tls1_1 2>/dev/null | grep -E "Protocol|alert"

# 4) 설정 덤프(정답지)
sudo nginx -T | less

# 5) 에러 로그 즉시 확인
sudo tail -n 50 /var/log/nginx/error.log
```
