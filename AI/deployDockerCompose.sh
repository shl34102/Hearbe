#!/bin/bash

# 1. 태그 생성 (예: 20260206-bfcf96)
export TAG="$(date +%Y%m%d)-$(git rev-parse --short HEAD 2>/dev/null || echo 'no-git')"

echo "------------------------------------------"
echo "🚀 배포를 시작합니다! 태그: $TAG"
echo "------------------------------------------"

# 2. 빌드 및 실행
# --build: 코드가 바뀌었으니 다시 빌드함
# -d: 백그라운드 실행
docker compose up -d --build

echo "------------------------------------------"
echo "✅ 배포 완료! 현재 실행 중인 이미지 확인:"
docker compose images
echo "------------------------------------------"