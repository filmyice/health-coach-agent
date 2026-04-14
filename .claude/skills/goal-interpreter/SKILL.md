# 스킬: goal-interpreter

## 역할
사용자의 건강 목표를 해석하고 1차 추천 방향을 설정한다.
에이전트가 직접 판단하는 스킬이다 (LLM 판단 + 규칙 결합).

## 트리거 조건
정규화 프로필(`normalized_profile.json`) 준비 완료 시 (Step 3)

## 처리 방식
에이전트 판단 + 규칙 기반

## 입력
- `output/intake/normalized_profile.json`
- `references/goal_rules.json` (건강 목표별 도메인 지식)

## 출력
- `output/intent/primary_health_goal.json`

출력 포맷:
```json
{
  "primary_goal": "fatigue_management",
  "primary_goal_label": "피로 관리",
  "secondary_goals": [],
  "interpretation_notes": "30대 여성의 피로 관리 — 철분·비타민 B군 중심으로 접근",
  "recommendation_direction": {
    "food_focus": ["철분 함유 식품", "비타민 B군 함유 식품"],
    "habit_focus": ["수면 규칙화", "과로 방지"],
    "nutrient_focus": ["철분", "비타민 B12", "마그네슘"]
  }
}
```

## 참조 파일
- `references/goal_rules.json`: 건강 목표별 기본 추천 방향, 주요 성분, 주의사항 시드

## 성공 기준
- 대표 건강 목표 1개 결정
- 보조 관심사 선택적 기록
- 추천 방향(`recommendation_direction`) 생성 완료

## 실패 처리
- 기본 목표만 유지 (secondary_goals, interpretation_notes 생략)
