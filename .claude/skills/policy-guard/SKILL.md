# 스킬: policy-guard

## 역할
추천 설명에서 금지 표현을 검출하고, 진단형 표현과 과장 표현을 제거한다.

## 트리거 조건
- 설명 생성 후 (Step 13 완료 직후)
- 최종 결과 직전 (Step 20)

## 처리 방식
스크립트 + 에이전트 보조

## 입력
- `output/content/final_health_summary.md` 또는 검토 대상 텍스트
- `references/forbidden_expressions.json` (금지 표현 목록)

## 출력
- `output/qa/final_validation_report.json` (Step 20 시)

출력 포맷:
```json
{
  "passed": true,
  "violations": [],
  "warnings": [],
  "checked_at": "ISO8601 timestamp"
}
```

## 스크립트
- `scripts/check_policy.py`: 금지 표현 검출 + 보고서 생성

## 참조 파일
- `references/forbidden_expressions.json`: 카테고리별 금지 표현 목록

## 금지 표현 카테고리

| 카테고리 | 예시 |
|---------|------|
| 진단형 표현 | "당신은 ~이 부족합니다", "~질환이 있습니다" |
| 처방형 표현 | "반드시 복용해야 합니다", "처방합니다" |
| 과장·효능 표현 | "치료된다", "완치", "의학적으로 입증" |
| 위험 과장 | "안 먹으면 위험하다", "심각한 결핍입니다" |
| 단정 표현 | "확실히 효과 있습니다", "100% 효과" |

## 성공 기준
- 금지 표현 0건
- 주의사항 누락 없음
- 가격 표시 적절

## 실패 처리
- 위반 표현 목록 반환
- 메인 에이전트가 해당 섹션 재생성 요청
