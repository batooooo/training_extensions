# 자동 운용 가이드 (월 적립 DCA)

이 시스템은 한 번 실행하고 끝나는 구조라, **상시/정기 자동 운용**은 본인 PC나
서버에서 스케줄러로 돌려야 합니다. (이 클라우드 세션은 종료되면 사라집니다.)

## 월 적립(DCA) 한 줄 명령

매달 한 번, 보유 평가액 + 신규 적립금($66.36 ≈ 10만 원)을 기준으로 목표 비중에
맞춰 분할매수합니다. `--from-holdings`가 수익까지 자동 반영해 복리로 굴립니다.

```bash
cd /path/to/trading_system
set -a; . ./.env; set +a            # API 키 로드
python scripts/rebalance.py --config portfolio.yaml \
    --from-holdings --contribution 66.36
```

먼저 `--dry-run`을 붙여 주문 없이 계획만 확인하는 습관을 들이세요.

## cron으로 매달 자동 실행 (Linux/macOS)

`crontab -e`에 추가 (매월 1일 미 동부 개장 직후를 노려 현지시간 조정):

```cron
# 매월 1일 23:35 (KST) 실행 -> 미 동부 약 10:35, 개장 후 안전하게 체결
35 23 1 * * cd /path/to/trading_system && bash -lc 'set -a; . ./.env; set +a; \
  python scripts/rebalance.py --config portfolio.yaml --from-holdings \
  --contribution 66.36' >> /path/to/trading_system/dca.log 2>&1
```

> ⚠️ 소수점/notional 주문은 **장중에만 체결**됩니다(장외엔 대기). 개장 시간에
> 맞춰 도는 게 안전합니다. 미국 공휴일엔 다음 영업일로 미뤄집니다.

## 적립금 환율 갱신

10만 원의 달러 환산액은 환율에 따라 달라집니다. 매달 환율을 반영하려면
`--contribution` 값을 그때그때 조정하거나, 환율 조회 후 계산해 넣으세요
(예: `python -c "print(1_000_000/$(...환율...))"`).

## 권장 운용 리듬

| 주기 | 할 일 |
|------|-------|
| 매월 | 적립 리밸런싱 1회 (`--from-holdings --contribution ...`) |
| 분기 | 비중 점검, 큰 이탈 시에만 조정 |
| 연 1회 | 적립액 상향 검토 (수입 늘면 적립도 ↑) |
| 평소 | **계좌를 매일 들여다보지 않기** — 규율이 수익을 지킵니다 |
