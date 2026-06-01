# 내 컴퓨터에서 운용하기 (배포 가이드)

이 시스템을 본인 PC/서버에서 띄우는 방법입니다. 코드는 GitHub의
`claude/stock-auto-trading-system-C1tIv` 브랜치에 있습니다.

---

## 1. 코드 받기

```bash
git clone https://github.com/batooooo/training_extensions.git
cd training_extensions
git checkout claude/stock-auto-trading-system-C1tIv
cd trading_system
```

(이미 받아둔 경우)
```bash
git pull origin claude/stock-auto-trading-system-C1tIv
```

## 2. 파이썬 환경 + 의존성

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 3. 키 설정 (`.env` 파일 생성)

`trading_system/.env` 파일을 만들고 본인 키를 넣습니다 (이 파일은 git에 안 올라감):

```
ALPACA_API_KEY=발급받은_키
ALPACA_API_SECRET=발급받은_시크릿
TELEGRAM_BOT_TOKEN=봇토큰
TELEGRAM_CHAT_ID=내챗id
```

## 4. 동작 확인

```bash
set -a; . ./.env; set +a            # Windows는 아래 "윈도우" 참고
python scripts/check_connection.py  # 연동 점검
python scripts/report.py            # 텔레그램으로 현재 상태 리포트
```

---

## 5. 24시간 띄워두기 (OS별)

### 🐧 Linux (systemd) — 서버에 권장
`/etc/systemd/system/trading-watch.service`:
```ini
[Unit]
Description=Trading fill watcher
After=network-online.target

[Service]
WorkingDirectory=/home/USER/training_extensions/trading_system
EnvironmentFile=/home/USER/training_extensions/trading_system/.env
ExecStart=/home/USER/training_extensions/trading_system/.venv/bin/python scripts/watch.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now trading-watch
sudo systemctl status trading-watch     # 상태 확인
journalctl -u trading-watch -f          # 로그 보기
```

### 🍎 macOS (launchd) 또는 간단히 tmux/nohup
간단 방법:
```bash
nohup bash -c 'set -a; . ./.env; set +a; python scripts/watch.py' \
    > watch.log 2>&1 &
```
PC를 껐다 켜도 자동 실행하려면 launchd(`~/Library/LaunchAgents/`)에 plist 등록.

### 🪟 Windows
1) 환경변수 로드 후 실행 (PowerShell):
```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^(.+?)=(.*)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }
.venv\Scripts\python scripts\watch.py
```
2) 상시 실행은 **작업 스케줄러(Task Scheduler)** 에 "시작 시 실행"으로 등록.

---

## 6. 정기 작업 (cron — Linux/macOS)

```cron
# 매월 1일: 10만 원(환율 반영) 적립 리밸런싱  (한국시간 23:35 ≈ 미동부 개장 후)
35 23 1 * * cd /path/trading_system && bash -lc 'set -a; . ./.env; set +a; \
  python scripts/rebalance.py --config portfolio.yaml --from-holdings --contribution 66.36'

# 매 영업일: 장 마감 후 손익 리포트 (한국시간 05:05)
5 5 * * 2-6 cd /path/trading_system && bash -lc 'set -a; . ./.env; set +a; \
  python scripts/report.py'
```

Windows는 작업 스케줄러로 같은 명령을 등록하면 됩니다.

---

## 동작 모드 요약

| 목적 | 명령 | 상시실행? |
|------|------|:--------:|
| 연동 점검 | `check_connection.py` | ✗ |
| 포트폴리오 매수/적립 | `rebalance.py` | ✗ (정기) |
| 손익 리포트 | `report.py` | ✗ (정기) |
| 실시간 체결 알림 | `watch.py` | ✓ (계속) |
| 신호 기반 매매 루프 | `run_live.py` / `run_stream.py` | ✓ (계속) |
