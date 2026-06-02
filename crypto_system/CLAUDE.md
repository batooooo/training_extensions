# CLAUDE.md — 암호화폐 자동매매 프로젝트 컨텍스트

> 새 Claude Code 세션이 자동으로 읽는 프로젝트 컨텍스트. 운용자 페르소나는
> "베테랑 펀드매니저"이며, 정직·리스크관리·페이퍼 우선 원칙을 따른다.

## 이게 뭔가
주식 시스템(`trading_system`)을 재활용해 만든 **24시간 암호화폐 자동매매** 시스템.
`ccxt`로 Binance 연결. 별개 프로젝트(별도 비공개 레포로 분리 예정).

## 핵심 사실 / 현재 상태
- 거래소: **Binance** (ccxt). 견적통화 USDT. 심볼 `BTC/USDT` 형식. 24/7.
- 코인 구성: **공격적(알트코인 포함)** — 예: BTC/ETH/SOL/DOGE/AVAX.
- 수량: **소수점 코인**, notional(금액) 기반 매수. (정수 주식과 다름 — 중요)
- 모드: **페이퍼(테스트넷) 기본**. 실거래는 `mode: live` + 명시 확인 시에만.
- 운용 자본: `capital_base`로 소액(예 $300) 제한. "잃어도 되는 돈"만.
- 리스크: 한 코인 비중 상한, 손절 -15%, 익절 +40%, 일일손실 -20% 킬스위치.

## ⚠️ 환경 제약 (검증 관련)
- 글로벌 `api.binance.com` / 테스트넷은 **미국 IP에서 451 차단**. 미국 기반
  클라우드 세션에선 라이브 검증 불가. **한국 사용자 머신에선 정상 작동.**
- 따라서 라이브 연동/매매 검증은 **사용자 머신**에서 수행. 코드+오프라인
  단위테스트(5개)는 통과 상태.

## 코드 맵
```
crypto/ : broker(CcxtBroker, SimulatedBroker), data(ccxt OHLCV/CSV),
          strategies(5종), risk, engine(Backtester, LiveEngine 24/7),
          portfolio, notify, report, config
scripts/: check_connection, backtest, run_24_7, report
```
- 전략/리스크/포트폴리오/알림은 주식 시스템과 동일 코드(재사용).
- 다른 점: CcxtBroker, ccxt 데이터, **소수점/notional 사이징**, 장시간 게이팅 없음.

## 자주 쓰는 명령
```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
set -a; . ./.env; set +a
python scripts/check_connection.py --config config.yaml
python scripts/backtest.py --symbol BTC/USDT --timeframe 1h --strategy trend_momentum
python scripts/run_24_7.py --config config.yaml --dry-run --once    # 신호만
python scripts/run_24_7.py --config config.yaml                     # 테스트넷 매매
python scripts/report.py --config config.yaml                       # 리포트→텔레그램
python -m pytest tests/ -q
```

## 비밀키 (`.env`, 커밋 금지)
```
CRYPTO_API_KEY=...   CRYPTO_API_SECRET=...     # 또는 BINANCE_API_KEY/SECRET
TELEGRAM_BOT_TOKEN=...  TELEGRAM_CHAT_ID=...   # (선택) 알림
```

## 남은 할 일 (TODO)
- [ ] 사용자 머신(한국)에서 Binance 테스트넷 키로 연동 검증
- [ ] run_24_7.py를 launchd/systemd로 24시간 상시 실행
- [ ] 코인별/전략별 파라미터 튜닝 (1h 기준 trend_momentum 윈도우 등)
- [ ] 별도 비공개 레포로 분리 (주식 시스템의 MIGRATION.md 방식)
- [ ] 텔레그램 실시간 체결 알림(ccxt watch / 폴링) 보강
- [ ] (미래) 실거래 전환 — 충분한 테스트넷 검증 + 명시 승인 후에만

## 원칙
- 정직 우선, 수익 보장 ❌. 암호화폐 고위험 항상 고지.
- 페이퍼/테스트넷 기본. 소액. 일희일비 금지.
