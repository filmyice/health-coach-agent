# 스킬: habit-recommender

## 역할
건강 목표에 맞는 생활습관·운동 추천을 생성한다.
사용자가 바로 실행 가능한 행동 중심 제안을 제공한다.

## 트리거 조건
대표 건강 목표 결정 후 (Step 5)

## 처리 방식
규칙 기반 + 에이전트 보조

## 입력
- `output/intent/primary_health_goal.json`
- `references/habit_rules.json` (건강 목표별 습관 룰셋)

## 출력
- `output/recommendation/habit_candidates.json`

출력 포맷:
```json
{
  "health_goal": "fatigue_management",
  "habits": [
    {
      "title": "취침 시간 규칙화",
      "description": "매일 같은 시간에 자고 일어나면 수면의 질이 높아져 피로 회복에 도움이 될 수 있습니다",
      "difficulty": "쉬움",
      "frequency": "매일"
    }
  ],
  "generated_at": "ISO8601 timestamp"
}
```

## 스크립트
- `scripts/recommend_habit.py`: 룰셋 조회 + 후보 생성

## 참조 파일
- `references/habit_rules.json`: 건강 목표별 생활습관 룰셋

## 성공 기준
- 1~3개의 짧고 쉬운 행동 제안
- 생활습관 가이드 수준 (운동 처방 수준 금지)

## 실패 처리
- 자동 재시도 1회
- 이후 일반 습관 가이드로 대체
