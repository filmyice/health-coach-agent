# 스킬: nutrient-recommender

## 역할
건강 목표 기준으로 보수적인 영양 성분 후보를 생성한다.
공격적 추천은 제외하며, 안전하고 일반적인 성분만 포함한다.

## 트리거 조건
대표 건강 목표 결정 후 (Step 6)

## 처리 방식
규칙 기반

## 입력
- `output/intent/primary_health_goal.json`
- `output/intake/normalized_profile.json`
- `references/nutrient_rules.json` (영양 성분 룰셋)

## 출력
- `output/recommendation/nutrient_candidates.json`

출력 포맷:
```json
{
  "health_goal": "fatigue_management",
  "nutrients": [
    {
      "name": "철분",
      "name_en": "Iron",
      "priority": 1,
      "reason_seed": "피로 관리에 관련된 대표 영양 성분",
      "target_profile": ["여성", "20대", "30대", "40대"],
      "caution_seed": ["공복 복용 시 위장 불편감 가능"]
    }
  ],
  "generated_at": "ISO8601 timestamp"
}
```

## 스크립트
- `scripts/recommend_nutrient.py`: 룰셋 조회 + 후보 생성

## 참조 파일
- `references/nutrient_rules.json`: 영양 성분 룰셋 (목표별)

## 성공 기준
- 1~3개 성분 후보 생성
- 공격적 추천 제외

## 실패 처리
- 자동 재시도 1회
- 이후 영양 성분 추천 생략 + 로그
