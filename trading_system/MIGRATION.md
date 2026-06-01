# 비공개 레포(ai_auto_trade)로 이사하기 — 내일 Mac에서 1분

이 클라우드 세션은 `training_extensions` 레포에만 접근 권한이 있어서 새 비공개
레포로 직접 옮기지 못합니다. 아래 명령을 **본인 Mac 터미널**에서 그대로 실행하면
주식 코드만 깔끔하게 `ai_auto_trade`(비공개)로 옮겨집니다.

## 1. 코드 추출해서 비공개 레포로 푸시

```bash
# 공개 레포를 임시로 받아서, trading_system 폴더만 추출해 비공개 레포로 push
git clone https://github.com/batooooo/training_extensions.git tmp_te
cd tmp_te
git checkout claude/stock-auto-trading-system-C1tIv
git subtree split --prefix=trading_system -b export-main
git remote add aiauto https://github.com/batooooo/ai_auto_trade.git
git push aiauto export-main:main
cd ..
rm -rf tmp_te
```

이제 `https://github.com/batooooo/ai_auto_trade` 에 코드가 **루트 기준**으로
들어갑니다 (`trading/`, `scripts/`, `tests/` …). 알림 워크플로
(`.github/workflows/market-open-report.yml`)도 함께 옮겨집니다.

## 2. 비공개 레포에서 실제로 돌리기

```bash
git clone https://github.com/batooooo/ai_auto_trade.git
cd ai_auto_trade
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# .env 파일 생성 (키 4개) 후
set -a; . ./.env; set +a
python scripts/check_connection.py
python scripts/report.py
```

> 새 레포는 코드가 **루트**에 있으므로, DEPLOY.md/README의 `cd trading_system`
> 단계는 **건너뛰면** 됩니다 (이미 레포 루트가 그 폴더예요).

## 3. 자동 알림(GitHub Actions) — 비공개 레포에서

1. `ai_auto_trade` → **Settings → Secrets and variables → Actions** 에서 4개 추가:
   `ALPACA_API_KEY`, `ALPACA_API_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
2. **Actions 탭** 활성화 → "Market-open portfolio report" → **Run workflow** 로 테스트
3. 이후 매 영업일 한국시간 22:35 자동 리포트

## 4. 실시간 체결 감시(24시간) — 비공개 레포에서

`DEPLOY.md`의 macOS launchd 가이드를 그대로 따르되, 경로만 `ai_auto_trade`로.

## 5. 공개 흔적 지우기 (이사 확인 후 마지막에)

비공개 레포에서 잘 도는 걸 확인한 다음, 공개 레포의 작업 흔적을 삭제:

```bash
# 공개 레포에서 우리 작업 브랜치 삭제
git push https://github.com/batooooo/training_extensions.git \
    --delete claude/stock-auto-trading-system-C1tIv
```

master에 올라간 워크플로 파일은 GitHub 웹에서 삭제하거나, 신경 쓰이면
`training_extensions` 포크 자체를 **Settings → Delete this repository** 로
삭제해도 됩니다 (인텔 원본과 무관한 사장님 포크라 지워도 안전).
