# 스킬: refinement-manager

## 역할
추가 보정 질문 필요 여부를 판단하고, 보정 질문을 관리하며, 응답을 기반으로 추천을 보정한다.

## 트리거 조건
1차 추천 세트 생성 후 (Step 8~10)

## 처리 방식
에이전트 판단 (Step 8) + 에이전트 + 프론트엔드 왕복 (Step 9) + 규칙 + 에이전트 보조 (Step 10)

## 입력 (Step 8)
- `output/recommendation/food_candidates.json`
- `output/recommendation/habit_candidates.json`
- `output/recommendation/nutrient_candidates.json`
- `output/recommendation/nutrient_cautions.json`

## 출력 (Step 8)
- `output/decision/refinement_needed.json`

출력 포맷 (Step 8):
```json
{
  "refinement_needed": true,
  "questions": [
    {
      "id": "q1",
      "text": "실내 생활이 많은가요?",
      "options": ["예", "아니요", "모르겠어요"],
      "purpose": "비타민 D 추천 우선순위 결정"
    }
  ],
  "reason": "비타민 D와 철분 중 우선순위가 불명확하여 보정 질문이 필요합니다"
}
```

## 입력 (Step 10)
- `output/intake/refinement_answers.json`
- 기존 추천 후보 전체

## 출력 (Step 10)
- `output/recommendation/refined_recommendations.json`
- `output/recommendation/refined_nutrient_cautions.json`

## 스크립트
- `scripts/manage_refinement.py`: 판단 로직 + 보정 처리

## 성공 기준 (Step 8)
- `refinement_needed` yes/no 명확 결정
- 필요 시 어떤 질문을 할지 지정 (최대 2개)

## 성공 기준 (Step 10)
- 보정이 필요한 항목만 조정
- 기존 추천 흐름과 충돌 없음

## 실패 처리
- Step 8 실패: 기본값 `refinement_needed: false`, 질문 생략
- Step 10 실패: 기존 1차 추천 및 주의사항 유지
