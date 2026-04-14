# 스킬: result-packager

## 역할
건강 추천 결과와 쇼핑 결과를 통합하여 프론트엔드가 소비할 수 있는 최종 결과물을 생성한다.

## 트리거 조건
모든 검수 단계 완료 후 (Step 19, 21)

## 처리 방식
스크립트 (Python)

## 입력 (Step 19)
- `output/content/final_health_summary.md`
- `output/shopping/price_comparison.json`
- `output/shopping/shopping_summary.md`
- `output/qa/safety_review.json`
- `output/qa/commerce_review.json`

## 출력
- `output/final/user_result.json`
- `output/final/user_result.md`

최종 JSON 포맷:
```json
{
  "session_id": "uuid",
  "health_goal": "피로 관리",
  "recommendations": {
    "foods": [...],
    "habits": [...],
    "nutrients": [
      {
        "name": "철분",
        "reason": "...",
        "cautions": {
          "level": "warning",
          "items": [...]
        }
      }
    ]
  },
  "shopping": {
    "available": true,
    "comparisons": [...],
    "disclaimer": "가격은 조회 시점 기준이며 실제 구매 시 다를 수 있습니다."
  },
  "disclaimers": [
    "이 내용은 의료적 진단이 아닙니다.",
    "복용 중인 약이나 임신·수유 중이라면 전문가 상담이 필요할 수 있어요."
  ],
  "generated_at": "ISO8601 timestamp"
}
```

## 스크립트
- `scripts/package_result.py`: 결과 병합 + JSON/MD 생성

## 성공 기준
- 사용자 흐름이 자연스러움
- 쇼핑은 보조 섹션으로 배치
- 필수 면책 문구 포함

## 실패 처리
- 쇼핑 섹션 제거 후 기본 건강 추천 결과만 반환
