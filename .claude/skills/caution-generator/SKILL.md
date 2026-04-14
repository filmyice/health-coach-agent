# 스킬: caution-generator

## 역할
추천된 영양 성분마다 주의사항을 생성한다.
금기, 중복 섭취 위험, 상호작용 정보를 포함한다.

## 트리거 조건
영양 성분 후보 생성 직후 (Step 7)

## 처리 방식
규칙 기반 + 에이전트 보조

## 입력
- `output/recommendation/nutrient_candidates.json`
- `output/intake/normalized_profile.json`
- `references/caution_rules.json` (금기·상호작용 룰 DB)

## 출력
- `output/recommendation/nutrient_cautions.json`

출력 포맷:
```json
{
  "cautions": [
    {
      "nutrient_name": "철분",
      "caution_level": "warning",
      "short_cautions": [
        "공복 복용 시 위장 불편감이 생길 수 있습니다",
        "변비를 유발할 수 있습니다"
      ],
      "interaction_flags": [
        "칼슘 보충제와 동시 복용 시 흡수 저하 가능"
      ],
      "duplicate_risk": false,
      "consultation_needed": false
    }
  ],
  "generated_at": "ISO8601 timestamp"
}
```

## 스크립트
- `scripts/generate_cautions.py`: 룰 DB 조회 + 주의사항 생성

## 참조 파일
- `references/caution_rules.json`: 성분별 금기·상호작용 룰 DB

## 성공 기준
- 모든 성분에 최소 1개 이상의 주의사항 생성
- 사용자 입력과 충돌하는 경고 누락 없음

## 실패 처리
- 자동 재시도 1회
- 이후 기본 공통 주의사항으로 대체
