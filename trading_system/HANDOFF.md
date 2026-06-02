# 자동 트레이딩 프로젝트 — 전체 대화/작업 인수인계

> 이 문서는 "베테랑 펀드매니저" Claude와 함께 진행한 전 과정을 정리한 것입니다.
> 새 Claude Code 세션에 이 파일(또는 CLAUDE.md)을 주면 맥락을 그대로 이어받습니다.
> 작성일: 2026-06-01

---

## 0. 한 줄 요약

개인용 **자동 주식 트레이딩 시스템**을 Alpaca(미국 브로커) 기반으로 구축하고,
페이퍼(모의) 계정에 **1,000,000원어치를 글로벌 올웨더 8자산에 분산 매수**까지 완료.
월 적립·텔레그램 알림·실시간 체결 감시·자동 리포트까지 갖춤. 코드는 비공개 레포
`batooooo/ai_auto_trade` 로 이전 중.

---

## 1. 진행 순서 (시간순 스토리)

1. **요구사항 결정**: 해외주식(Alpaca), 백테스트→페이퍼→실거래 풀스택, 전략은
   매니저가 제안.
2. **시스템 구축**: 전략 4종(SMA/RSI/볼린저/MACD) + 브로커 추상화 + 백테스터 +
   라이브 엔진 + 리스크 매니저. 테스트 통과.
3. **실제 연동**: Alpaca 페이퍼 키로 접속 성공(잔고 $100k). 실시간 시세 확인.
4. **첫 주문**: SMA 신호로 AAPL 매수 → 이후 "100만원만 운용" 요청에 맞춰
   `capital_base`(환율 반영 $663.65) 기능 추가.
5. **전략 고도화**: "최고의 전략" 요청 → 단일지표의 한계를 정직히 설명하고
   **trend_momentum**(200일선 국면필터+EMA추세+모멘텀+RSI) 추가. 백테스트로
   "단일종목 착시"와 분산의 중요성 입증.
6. **분산 운용**: 100만원을 한 종목 ❌ → 코어/새틀라이트 → 최종 **글로벌 성장형
   올웨더 8자산**으로. 소수점(notional) 주문으로 정밀 분산.
7. **자동화/알림**: 월 적립 DCA, 텔레그램 봇(@batoo_fund_bot) 알림, 실시간 체결
   감시(watch.py), 포트폴리오 리포트(report.py), GitHub Actions 자동 리포트.
8. **배포 준비**: Mac launchd/cron 가이드(DEPLOY.md, AUTOMATION.md).
9. **비공개 이전**: 공개 포크라 비공개 전환 불가 → 새 비공개 레포
   `ai_auto_trade` 로 코드만 분리 이전(MIGRATION.md).
10. **첫날 결과**: 22:30(KST) 개장과 함께 8자산 전부 체결. **첫날 +0.28%
    (약 +2,788원)로 플러스 마감.**

---

## 2. 현재 포트폴리오 (목표비중)

| 자산 | 비중 | 성격 |
|------|----:|------|
| VTI | 30% | 미국 전체시장 |
| QQQ | 10% | 미국 성장/기술 |
| IWM | 5%  | 미국 소형주 |
| VEA | 10% | 선진국(미국 외) |
| VWO | 5%  | 신흥국 |
| IEF | 20% | 미국 중기채(7-10년) |
| GLD | 12% | 금 |
| DBC | 8%  | 원자재 |

- 주식 60 / 채권 20 / 실물 20. 백테스트(2020-2026): ~10.7% CAGR, 샤프 0.83,
  최대낙폭 -22.3%.
- 운용 자본: 1,000,000원 가정($663.65, 환율 1506.83). 페이퍼 계정.

---

## 3. 핵심 결정과 이유

- 단일 종목/지표 ❌ → **분산 + 리스크 관리**가 수익보다 우선.
- 소액엔 **광범위 ETF + 글로벌 분산**이 정답.
- 클래식 올웨더(채권55%)는 젊은 적립자에겐 보수적 → **성장형 올웨더** 채택.
- 성장의 1순위 레버 = **월 적립 + 시간** (사용자 계획: 월 10만원).
- "빨리 불리기"는 파산 확률 ↑ → **안 망하는 것**이 최우선.
- 실시간은 폴링 대신 WebSocket 푸시.

---

## 4. 운용 명령 (치트시트)

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
set -a; . ./.env; set +a
python scripts/check_connection.py                                   # 연동 점검
python scripts/rebalance.py --config portfolio.yaml --dry-run        # 계획만
python scripts/rebalance.py --config portfolio.yaml                  # 리밸런싱
python scripts/report.py                                             # 손익 리포트→텔레그램
python scripts/rebalance.py --config portfolio.yaml --from-holdings --contribution 66.36  # 월 10만원 DCA
python scripts/watch.py                                              # 실시간 체결 감시
python -m pytest tests/ -q                                           # 테스트
```

---

## 5. 비밀키 (절대 커밋 금지 / `.env`)

```
ALPACA_API_KEY=...
ALPACA_API_SECRET=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=7670050611
```
GitHub Actions 자동 리포트용으로 동일 4개를 레포 Secrets에도 등록.
텔레그램 봇: `@batoo_fund_bot`.

---

## 6. 남은 할 일 (TODO)

- [ ] 비공개 레포 `ai_auto_trade` 이전 완료 확인
- [ ] GitHub Actions: Secrets 4개 등록 + Actions 활성화 → 매 영업일 22:35(KST)
      자동 리포트
- [ ] Mac launchd로 watch.py 24시간 상시 실행 (DEPLOY.md)
- [ ] 월 적립 DCA cron 등록 (AUTOMATION.md)
- [ ] 공개 포크(training_extensions)의 작업 흔적 정리/삭제 (MIGRATION.md 5번)
- [ ] 보안: Alpaca 키 재발급 + Telegram /revoke (채팅 노출분 무효화)
- [ ] (미래) 실거래 전환 — 충분한 페이퍼 검증 + 명시 승인 후에만

---

## 7. 새 Claude Code 세션에서 이어받기

1. `ai_auto_trade` 레포로 새 세션 시작 (웹) 또는 `git clone` 후 `claude` 실행(CLI).
2. 첫 메시지 예시:
   > "CLAUDE.md / HANDOFF.md 읽고 이 트레이딩 프로젝트를 이어서 운용해줘.
   > 너는 베테랑 펀드매니저야. 남은 TODO부터 도와줘."

---

## 8. 운용 원칙 (페르소나)

- 정직 우선: 수익 보장 ❌, 위험·한계 솔직히. 백테스트로 검증 후 결정.
- 일희일비 금지: 30년 복리 게임. 매일 안 봐도 됨.
- 페이퍼 기본, 실거래는 명시 승인 시에만.
