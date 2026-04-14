# 스킬: risk-flagger

## 역할
사용자 프로필과 안전 질문 응답을 기반으로 위험 조건을 추출하고 플래그를 생성한다.

## 트리거 조건
최종 추천 전 안전 확인 단계 도달 시 (Step 11)

## 처리 방식
규칙 기반 중심

## 입력
- `output/intake/normalized_profile.json`
- `output/intake/safety_answers.json` (있을 경우)
- `output/recommendation/refined_nutrient_cautions.json` 또는 `output/recommendation/nutrient_cautions.json`

## 출력
- `output/risk/risk_flags.json`

출력 포맷:
```json
{
  "flags": {
    "has_medication": false,
    "pregnancy_or_breastfeeding": false,
    "chronic_condition": false,
    "allergy": false,
    "duplicate_supplement": false,
    "consult_required": false
  },
  "flag_details": [],
  "safety_questions_needed": false,
  "safety_questions": [],
  "evaluated_at": "ISO8601 timestamp"
}
```

## 스크립트
- `scripts/flag_risks.py`: 위험 플래그 계산

## 주요 위험 플래그

| 플래그 | 트리거 조건 |
|--------|-----------|
| `has_medication` | 복용 중인 약 있음 |
| `pregnancy_or_breastfeeding` | 임신·수유 중 |
| `chronic_condition` | 기저질환 있음 |
| `allergy` | 알레르기 있음 |
| `duplicate_supplement` | 기존 복용 영양제 중복 가능성 |
| `consult_required` | 위 조건 중 1개 이상 해당 시 자동 설정 |

## 성공 기준
- 고위험 조건 누락 없이 식별

## 실패 처리
- 자동 재시도 1회
- 불확실하면 에스컬레이션 플래그 → `safety-reviewer` 호출
