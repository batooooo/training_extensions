# AGENT RUNBOOK — 읽고 그대로 실행하는 자동 셋업 문서

> **사용법 (사람용):** Mac 터미널에서 `claude` 실행 후 한 줄만 입력하세요:
> *"AGENT_RUNBOOK.md 읽고 처음부터 끝까지 그대로 실행해줘. 막히거나 내 입력이
> 필요한 지점에서만 멈춰서 물어봐. 너는 베테랑 펀드매니저야."*
>
> **에이전트(Claude)에게:** 이 문서는 실행 지시서다. 위에서 아래로 STEP을 순서대로
> 수행하라. 각 STEP의 명령을 실행하고 "검증" 항목으로 성공을 확인한 뒤 다음으로
> 넘어가라. `[사용자 입력 필요]` 표시가 있는 곳에서만 멈추고 사용자에게 물어라.
> 파괴적/되돌리기 어려운 작업(레포 삭제 등) 전에는 반드시 확인을 받아라.

---

## 0. 컨텍스트

- 목적: **암호화폐 24/7 자동매매 시스템**을 Mac에서 비공개로 셋업·실행.
- 코드 출처: 공개 레포 `batooooo/training_extensions`,
  브랜치 `claude/stock-auto-trading-system-C1tIv`, 폴더 `crypto_system/`.
- 목표 비공개 레포: `batooooo/ai_crypto_trade` (없으면 생성).
- 전체 맥락/전략/원칙은 같은 폴더의 `CLAUDE.md` 참고 (먼저 읽어라).
- 거래소: Binance (ccxt). 모드: **테스트넷(paper) 우선**. 실거래는 사용자 명시 승인 시에만.
- 페르소나/원칙: 정직 우선, 수익 보장 금지, 리스크 관리·소액·페이퍼 우선, 일희일비 금지.

---

## STEP 1 — 사전 점검

```bash
git --version && python3 --version && node --version
command -v gh && gh auth status || echo "gh 없음/미인증 (STEP 3에서 대안 사용)"
```
검증: git/python3 출력되면 OK. (Homebrew/Claude Code는 이미 설치돼 있다고 가정.)

---

## STEP 2 — 코드 가져오기

```bash
cd ~
git clone https://github.com/batooooo/training_extensions.git crypto_src 2>/dev/null || (cd crypto_src && git fetch)
cd ~/crypto_src
git checkout claude/stock-auto-trading-system-C1tIv
git pull origin claude/stock-auto-trading-system-C1tIv
```
검증: `ls crypto_system/crypto` 에 `broker data engine strategies …` 가 보이면 OK.

---

## STEP 3 — 비공개 레포 `ai_crypto_trade`로 코드 이전

먼저 비공개 레포를 만든다.
- `gh` 가 인증돼 있으면:
  ```bash
  gh repo create batooooo/ai_crypto_trade --private --confirm 2>/dev/null || echo "이미 있거나 실패 -> 아래 [사용자 입력 필요] 확인"
  ```
- `gh` 가 없거나 실패하면 **[사용자 입력 필요]**: 사용자에게
  "github.com에서 비공개 레포 `ai_crypto_trade`를 (README 없이) 만들어 주세요"
  라고 요청하고, 만들었다는 답을 받은 뒤 진행.

코드만 추출해서 새 레포의 main으로 푸시:
```bash
cd ~/crypto_src
git subtree split --prefix=crypto_system -b crypto-export
git remote remove crypto 2>/dev/null; git remote add crypto https://github.com/batooooo/ai_crypto_trade.git
git push crypto crypto-export:main --force
```
검증: `https://github.com/batooooo/ai_crypto_trade` 에 `crypto/ scripts/ README.md` 가
보이면 OK. (코드는 레포 루트에 위치 — `cd crypto_system` 단계 불필요.)

---

## STEP 4 — 작업 클론 + 파이썬 환경

```bash
cd ~ && git clone https://github.com/batooooo/ai_crypto_trade.git
cd ~/ai_crypto_trade
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/ -q
```
검증: 테스트가 모두 통과(예: `5 passed`)하면 OK.

---

## STEP 5 — 실시간 시세 확인 (키 불필요)

```bash
python scripts/live_monitor.py --symbols BTC/USDT ETH/USDT SOL/USDT --interval 5
```
검증: 5초마다 가격/변동/신호 표가 갱신되면 OK (Ctrl-C로 종료).
> 이 환경(미국)에선 거래소가 지역차단될 수 있으나, 한국 Mac에선 정상.

---

## STEP 6 — 백테스트로 감 잡기

```bash
python scripts/backtest.py --symbol BTC/USDT --timeframe 1d --strategy trend_momentum
python scripts/backtest.py --symbol ETH/USDT --timeframe 1d --strategy sma_crossover
```
검증: 수익률·샤프·최대낙폭·거래수가 출력되면 OK.
참고(과거 19코인 분석 결론): 알트 단순보유는 평균 낙폭 ~-78%. **추세추종 + 코인별
국면필터 + 메이저 위주**가 핵심. 물타기(저점매수) 금지.

---

## STEP 7 — 키 설정 (.env)

**[사용자 입력 필요]** 다음을 사용자에게 요청:
- Binance **테스트넷** 키: https://testnet.binance.vision (mode: paper용)
- (선택) 텔레그램 봇 토큰/chat id (알림용 — 주식과 동일하게 재사용 가능)

받은 값으로 `~/ai_crypto_trade/.env` 생성:
```
CRYPTO_API_KEY=...
CRYPTO_API_SECRET=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
```
검증: `.env`가 `.gitignore`에 포함돼 커밋되지 않는지 확인 (`git check-ignore .env`).

---

## STEP 8 — 설정 파일 + 연동 점검

```bash
cp portfolio.example.yaml portfolio.yaml    # 데이터기반 메이저 바스켓 + 국면필터
cp config.example.yaml config.yaml          # (신호기반 24/7 매매용)
set -a; . ./.env; set +a
python scripts/check_connection.py --config config.yaml
```
검증: `[2/3] account OK`, `[3/3] market data OK` 가 뜨면 연동 성공.

---

## STEP 9 — 페이퍼(테스트넷) 매매

먼저 주문 없이 의도만 확인:
```bash
python scripts/run_24_7.py --config config.yaml --dry-run --once     # 신호기반
# 또는 목표비중 리밸런싱:
python scripts/rebalance.py --config portfolio.yaml --dry-run
```
이상 없으면 테스트넷 실주문:
```bash
python scripts/rebalance.py --config portfolio.yaml                  # 1회 리밸런싱
python scripts/run_24_7.py --config config.yaml                      # 24/7 루프
```
검증: 로그에 ORDER … ACCEPTED, 텔레그램 알림 도착(설정 시).

---

## STEP 10 — 24시간 상시 실행 (Mac launchd)

`run_24_7.py`(또는 주기적 rebalance)를 LaunchAgent로 등록해 상시 가동.
패턴은 주식 시스템 `DEPLOY.md`의 macOS launchd 가이드와 동일하되 경로를
`~/ai_crypto_trade`로, 실행 스크립트를 `scripts/run_24_7.py`로 바꾼다.
plist 예시를 만들고 `~/Library/LaunchAgents/`에 넣은 뒤
`launchctl load -w ...` 로 등록. 로그는 레포 내 `*.log`.
검증: `launchctl list | grep crypto` 에 항목이 보이면 OK.

---

## STEP 11 — 마무리 / 안전

- 보안: 사용자에게 Binance 키는 **테스트넷 우선**, 실거래 키는 출금권한 끄기 권고.
- 리스크 원칙 재고지: 크립토는 전체 자산의 **소액 별동대(<10%)**, 손절 준수,
  물타기 금지, +수익에도 비중 키우지 않기.
- 실거래 전환은 **충분한 테스트넷 검증 + 사용자 명시 승인** 후에만. 절대 임의로 하지 말 것.
- (선택) 사용자가 원하면 공개 레포 `training_extensions`의 작업 흔적 정리(브랜치 삭제).
  **파괴적 작업이므로 반드시 사용자 확인 후.**

---

## 완료 보고

모든 STEP 성공 시 사용자에게 요약 보고:
- 비공개 레포 `ai_crypto_trade` 생성/이전 완료
- 실시간 모니터·백테스트·연동·페이퍼 매매 동작 확인
- 상시 실행(launchd) 등록 여부
- 남은 선택지(코인/전략 튜닝, 실거래 전환은 승인 후)
