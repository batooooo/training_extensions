# 주식 자동 트레이딩 시스템 (Alpaca)

전략을 플러그인처럼 갈아끼우며 **백테스트 → 페이퍼(모의) → 실거래**로 단계적으로
검증·운영할 수 있는 모듈형 자동매매 시스템입니다. 미국 주식 브로커
[Alpaca](https://alpaca.markets/)를 기본 연동하며, 브로커 계층이 추상화되어 있어
IBKR 등 다른 브로커도 같은 인터페이스로 추가할 수 있습니다.

> ⚠️ **투자 위험 고지**: 자동매매는 실제 금전 손실로 이어질 수 있습니다. 이 코드는
> 교육·연구 목적이며 수익을 보장하지 않습니다. 반드시 **페이퍼 트레이딩으로 충분히
> 검증한 뒤** 본인 책임 하에 소액으로 시작하세요. 기본 모드는 항상 페이퍼입니다.

## 구조

```
trading/
├── strategies/   # 신호 생성 (SMA·RSI·Bollinger·MACD) — 플러그인 레지스트리
├── broker/       # Broker 추상화 + AlpacaBroker + SimulatedBroker(테스트용)
├── data/         # 과거·실시간 OHLCV (CSV / Alpaca)
├── risk/         # 포지션 사이징, 손절·익절, 일일 손실 한도(킬 스위치)
├── engine/       # Backtester + LiveEngine (전략·리스크 로직 공유)
└── config.py     # YAML 설정 로딩
scripts/
├── backtest.py        # 전략 백테스트
├── run_live.py        # 라이브/페이퍼 엔진 실행
└── make_sample_data.py# API 없이 시험용 합성 데이터 생성
```

핵심 설계 원칙: **전략은 신호만, 리스크는 사이즈·안전장치, 엔진은 주문 실행**으로
역할을 분리. 덕분에 백테스터에서 검증한 전략·리스크 로직이 라이브에서 그대로 동작합니다.

## 전략

| 이름 | 유형 | 매수 / 매도 조건 |
|------|------|------------------|
| `sma_crossover` | 추세추종 | 단기 SMA > 장기 SMA(골든크로스) 매수 / 하향 매도 |
| `rsi_reversion` | 평균회귀 | RSI < 30 매수 / RSI > 70 매도 |
| `bollinger`     | 평균회귀 | 하단 밴드 이탈 매수 / 상단 밴드 이탈 매도 |
| `macd`          | 모멘텀   | MACD선 > 시그널선 매수 / 하향 매도 |

`trading/strategies/`에 `Strategy`를 상속한 클래스를 추가하고 레지스트리에 등록하면
새 전략을 바로 쓸 수 있습니다.

## 설치

```bash
cd trading_system
pip install -r requirements.txt
```

## 빠른 시작 (API 키 없이 백테스트)

```bash
# 1) 합성 데이터 생성
python scripts/make_sample_data.py --out data/SAMPLE.csv --days 600

# 2) 백테스트
python scripts/backtest.py --csv data/SAMPLE.csv \
    --strategy sma_crossover --params fast=20 slow=50 \
    --max-position-pct 1.0
```

출력 예: 총수익률, 샤프지수, 최대낙폭(MDD), 거래수, 승률.

## 페이퍼/실거래

1. [Alpaca](https://app.alpaca.markets/)에서 **페이퍼 트레이딩 키**(무료) 발급
2. 자격증명을 환경변수로 설정:
   ```bash
   cp .env.example .env   # 편집 후
   export ALPACA_API_KEY=...  ALPACA_API_SECRET=...
   ```
3. 설정 파일 작성: `cp config.example.yaml config.yaml` (전략·종목·리스크 편집)
4. 실행:
   ```bash
   # 주문은 내지 않고 의도만 로그로 확인 (가장 안전)
   python scripts/run_live.py --config config.yaml --dry-run --once

   # 페이퍼 계좌에 실제 모의 주문
   python scripts/run_live.py --config config.yaml
   ```

**실거래(real money)** 는 `config.yaml`의 `mode: live` 로 명시적으로 켜야 하며,
시작 시 `I UNDERSTAND` 를 입력해야만 진행됩니다.

## 리스크 관리

`config.yaml`의 `risk` 섹션에서 제어:

- `max_position_pct`: 한 종목 최대 비중 (예 0.10 = 자산의 10%)
- `stop_loss_pct` / `take_profit_pct`: 진입가 대비 손절/익절
- `max_daily_loss_pct`: 당일 손실이 이 비율을 넘으면 신규 진입 중단(킬 스위치)

리스크 매니저를 통과하지 않은 주문은 엔진이 내보내지 않습니다.

## 테스트

```bash
pip install pytest
pytest tests/ -v
```

## 로드맵 / 확장 아이디어

- 다중 전략 앙상블·종목별 전략 매핑
- 공매도(short) 지원, 지정가/OCO 주문
- 워크포워드 최적화, 파라미터 그리드 서치
- IBKR 브로커 어댑터, 한국투자증권(KIS) 어댑터
- 실시간 WebSocket 스트리밍 기반 분봉 트레이딩, 알림(Slack/텔레그램)
```
