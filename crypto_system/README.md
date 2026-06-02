# 암호화폐 24/7 자동매매 시스템 (Binance / ccxt)

주식 시스템(`trading_system`)의 검증된 아키텍처(전략·리스크·포트폴리오·알림)를
그대로 재활용해, **24시간 거래되는 암호화폐**용으로 만든 자동매매 시스템입니다.
`ccxt`로 Binance(및 대부분의 거래소)에 연결합니다.

> ⚠️ **고위험 경고**: 암호화폐, 특히 알트코인은 변동성이 극심합니다(하루 ±30%,
> -90%도 가능). **잃어도 되는 돈**으로만, **테스트넷(paper)** 으로 충분히 검증한 뒤
> 소액으로 시작하세요. 실거래(`mode: live`)는 명시적으로 켜야만 동작합니다.

## 주식 시스템과 다른 점
- **거래소**: Alpaca → **ccxt(Binance)**. 24시간이라 장 시간 게이팅 없음.
- **수량**: 정수 주(株) → **소수점 코인**(notional 금액 기반 매수). 0.0123 BTC처럼.
- **심볼**: `BTC/USDT`, `ETH/USDT` 형식. 견적통화 기본 USDT.
- 전략/리스크/포트폴리오/백테스터/알림 코드는 **동일**(재사용).

## 구조
```
crypto/
  broker/   Broker 추상화 + CcxtBroker(Binance 등) + SimulatedBroker
  data/     ccxt OHLCV + CSV
  strategies/ sma_crossover, rsi_reversion, bollinger, macd, trend_momentum
  risk/     사이징, 손절/익절, 일일손실 킬스위치 (+notional/소수점)
  engine/   Backtester, LiveEngine (24/7 루프)
  portfolio.py  목표비중 리밸런서
  notify.py / report.py  텔레그램 알림 / 리포트
  config.py
scripts/
  check_connection.py  연동 점검
  backtest.py          백테스트 (ccxt/CSV)
  run_24_7.py          24시간 전략 매매 루프
  report.py            포트폴리오 리포트 → 텔레그램
```

## 설치
```bash
cd crypto_system
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 키 설정 (`.env`)
```
CRYPTO_API_KEY=...      # Binance API 키 (또는 BINANCE_API_KEY)
CRYPTO_API_SECRET=...
TELEGRAM_BOT_TOKEN=...  # (선택) 알림
TELEGRAM_CHAT_ID=...
```
- 페이퍼: Binance Spot **테스트넷**(https://testnet.binance.vision) 키 + `mode: paper`
- ⚠️ 글로벌 binance.com은 일부 지역(미국 등)에서 접속이 막힙니다. 한국에선 정상.

## 빠른 시작
```bash
cp config.example.yaml config.yaml         # 거래소·코인·전략·리스크 편집
set -a; . ./.env; set +a
python scripts/check_connection.py --config config.yaml          # 연동 점검
python scripts/backtest.py --symbol BTC/USDT --timeframe 1h --strategy trend_momentum
python scripts/run_24_7.py --config config.yaml --dry-run --once  # 주문 없이 신호만
python scripts/run_24_7.py --config config.yaml --dry-run         # 24/7 루프(로그만)
python scripts/run_24_7.py --config config.yaml                   # 테스트넷 실매매
```

## 24시간 상시 실행
- 신호 기반 매매 루프(`run_24_7.py`)를 Mac launchd / Linux systemd로 상시 실행.
  (주식 시스템의 `DEPLOY.md` 방식과 동일, 경로만 이 레포로.)

## 테스트
```bash
pip install pytest && python -m pytest tests/ -q
```

## ⚠️ 리스크 관리 기본 장착
- 한 코인 최대 비중 상한 + **손절(-15%)·익절(+40%)** + 일일손실 한도(-20%).
- `capital_base`로 "잃어도 되는 금액"만 운용. 기본 설정은 소액($300) 가정.
- 그래도 **암호화폐는 전액 손실 가능**합니다. 절대 무리하지 마세요.
