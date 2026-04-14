# 스킬: food-recommender

## 역할
건강 목표에 맞는 음식 추천을 생성한다.
사용자가 바로 실천할 수 있는 식품 단위 추천을 제공한다.

## 트리거 조건
대표 건강 목표 결정 후 (Step 4)

## 처리 방식
규칙 기반 + 에이전트 보조

## 입력
- `output/intent/primary_health_goal.json`
- `references/food_rules.json` (건강 목표별 음식 룰셋)

## 출력
- `output/recommendation/food_candidates.json`

출력 포맷:
```json
{
  "health_goal": "fatigue_management",
  "foods": [
    {
      "name": "시금치",
      "category": "채소",
      "reason": "철분과 엽산이 풍부하여 피로 회복에 도움이 될 수 있습니다",
      "serving_suggestion": "샐러드 또는 나물로 주 3회 이상"
    }
  ],
  "generated_at": "ISO8601 timestamp"
}
```

## 스크립트
- `scripts/recommend_food.py`: 룰셋 조회 + 후보 생성

## 참조 파일
- `references/food_rules.json`: 건강 목표별 음식 룰셋

## 성공 기준
- 2~4개의 실천 가능한 식품 단위 추천

## 실패 처리
- 자동 재시도 1회
- 이후 일반 건강식 가이드로 대체
