# CLAUDE.md — 프로젝트 컨텍스트 & 인수인계

> 이 파일은 새 Claude Code 세션이 이 프로젝트의 전체 맥락을 즉시 이해하도록
> 돕는 문서입니다. (Claude Code는 저장소의 CLAUDE.md를 자동으로 읽습니다.)

## 이 프로젝트가 뭔가

개인용 **자동 주식 트레이딩 시스템**. 미국 브로커 **Alpaca** 연동. 처음엔
OpenVINO `training_extensions` 포크 안의 `trading_system/` 폴더로 개발했고,
이후 **비공개 레포 `batooooo/ai_auto_trade`** 로 코드만 분리·이전했다(이 레포가
그 결과물; 코드가 루트에 위치).

오너: GitHub `batooooo` (개인 계정). 운용자 페르소나: "베테랑 펀드매니저".

## 현재 상태 (2026-06-01 기준)

- **모드: 페이퍼(모의) 트레이딩** — 가짜돈. 실거래 아님. 실거래 전환은 사용자
  명시 승인 시에만.
- **가용 자본 가정: 1,000,000 KRW ≈ $663.65** (환율 1 USD=1506.83, 2026-06-01).
  페이퍼 계정 잔고는 $100k지만 `capital_base`로 운용액을 1M KRW로 제한함.
- **현재 포트폴리오: 글로벌 성장형 올웨더 (8자산, 목표비중)** — 첫날 체결 완료,
  첫날 +0.28%(약 +2,788원)로 마감.

  | 자산 | 비중 | 성격 |
  |------|----:|------|
  | VTI | 30% | 미국 전체시장 |
  | QQQ | 10% | 미국 성장/기술 |
  | IWM | 5%  | 미국 소형주 |
  | VEA | 10% | 선진국(미국 외) |
  | VWO | 5%  | 신흥국 |
  | IEF | 20% | 미국 중기채(7-10y) |
  | GLD | 12% | 금 |
  | DBC | 8%  | 원자재 |

- 소수점(notional) 주문 사용 → 소액으로도 정밀 분산.
- 포트폴리오 리밸런싱은 **추세 국면필터 없이** 매수 후 정기 리밸런싱(올웨더 원칙).

## 아키텍처 (코드 맵)

```
trading/
  strategies/   sma_crossover, rsi_reversion, bollinger, macd, trend_momentum
                (공통 Strategy 인터페이스 + 레지스트리)
  broker/       Broker 추상화 + AlpacaBroker + SimulatedBroker (notional 지원)
  data/         과거/실시간 OHLCV (CSV / Alpaca)
  risk/         포지션 사이징, 손절/익절, 일일손실 킬스위치, ATR 변동성 사이징
  engine/       Backtester, LiveEngine, StreamEngine (전략·리스크 로직 공유)
  portfolio.py  목표비중 리밸런서(plan_rebalance) + PortfolioManager(국면필터 옵션)
  notify.py     Telegram/Log/Null 알림 (stdlib만)
  report.py     포트폴리오 스냅샷 + 체결 알림 포맷
  config.py     YAML 설정 로딩
scripts/
  check_connection.py  연동 점검
  backtest.py          전략 백테스트
  rebalance.py         목표비중 리밸런싱 (+--from-holdings, --contribution DCA)
  report.py            포트폴리오 리포트 → 텔레그램
  watch.py             실시간 체결 감시(WebSocket) → 텔레그램
  run_live.py/run_stream.py  신호 기반 매매 루프
  make_sample_data.py  오프라인 백테스트용 합성 데이터
tests/          pytest 39+ (전부 통과 상태로 유지할 것)
```

## 자주 쓰는 명령

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
set -a; . ./.env; set +a                 # 키 로드
python scripts/check_connection.py        # 연동 점검
python scripts/rebalance.py --config portfolio.yaml --dry-run   # 계획만
python scripts/rebalance.py --config portfolio.yaml             # 리밸런싱
python scripts/report.py                  # 현재 손익 → 텔레그램
python scripts/rebalance.py --config portfolio.yaml --from-holdings --contribution 66.36  # 월 10만원 DCA
python -m pytest tests/ -q                # 테스트
```

> 이 레포는 코드가 루트에 있으므로 DEPLOY.md/README의 `cd trading_system` 단계는
> 건너뛴다.

## 비밀/설정 (절대 커밋 금지)

`.env` (gitignored)에 4개 키:
```
ALPACA_API_KEY=...
ALPACA_API_SECRET=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=7670050611
```
GitHub Actions 자동 리포트를 쓰려면 같은 4개를 레포 Secrets에 등록.
`config.yaml` / `portfolio.yaml`도 gitignored (예시: `*.example.yaml`).

## 핵심 결정과 이유 (히스토리)

1. 단일 종목/단일 지표 ❌ → **분산 + 리스크 관리**가 수익보다 우선.
2. 소액(1M KRW)엔 개별주보다 **광범위 ETF + 글로벌 분산**이 정답.
3. 클래식 올웨더(채권55%)는 젊은 적립 투자자에겐 너무 보수적 → **성장형
   올웨더(주식60/채권20/실물20)** 채택. 백테스트 2020-2026: ~10.7% CAGR,
   샤프 0.83, 최대낙폭 -22.3%.
4. 성장의 1순위 레버는 수익률이 아니라 **월 적립 + 시간**. 사용자 계획: **월 10만원**.
5. 실시간: 폴링 대신 WebSocket(StreamEngine/watch.py) 푸시.
6. 알림: Telegram 봇 `@batoo_fund_bot`. 사용자 chat_id 7670050611.

## 남은 할 일 (TODO)

- [ ] (확인) 비공개 레포 이전 완료 검증
- [ ] GitHub Actions: 레포에 Secrets 4개 등록 + Actions 활성화 → 매 영업일
      22:35(KST) 자동 리포트 (`.github/workflows/market-open-report.yml`)
- [ ] 실시간 체결 감시 24시간: Mac launchd로 watch.py 상시 실행 (DEPLOY.md 참고)
- [ ] 월 적립 DCA cron 등록 (AUTOMATION.md)
- [ ] 공개 포크(training_extensions)의 작업 흔적 정리/삭제 (MIGRATION.md 5번)
- [ ] 보안 위생: Alpaca 키 재발급 + Telegram /revoke (채팅 노출분 무효화)
- [ ] (미래) 실거래 전환 — 충분한 페이퍼 검증 + 사용자 명시 승인 후에만

## 운용 원칙 (페르소나 메모)

- 정직 우선: 수익 보장 ❌, 위험/한계 솔직히 고지. 백테스트로 검증 후 결정.
- "빨리 불리기" 경계: 큰 베팅 = 파산 확률. 안 망하는 게 1순위.
- 일희일비 금지: 30년 복리 게임. 매일 들여다보지 않기.
- 페이퍼 기본, 실거래는 명시 승인 시에만.
