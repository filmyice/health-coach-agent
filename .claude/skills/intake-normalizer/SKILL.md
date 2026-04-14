# 스킬: intake-normalizer

## 역할
프론트엔드에서 전달된 최소 입력 JSON을 검증하고 내부 표준 포맷으로 변환한다.

## 트리거 조건
프론트엔드 JSON 입력 도착 시 (Step 1~2)

## 처리 방식
스크립트 (Python)

## 입력
- `output/intake/raw_minimal_input.json`

입력 스키마:
```json
{
  "health_goal": "피로 관리",
  "age_group": "30대",
  "gender": "여성"
}
```

허용 enum:
- `health_goal`: ["피로 관리", "수면 관리", "면역 관리", "눈 건강", "장 건강", "뼈 건강", "피부·항산화"]
- `age_group`: ["10대", "20대", "30대", "40대", "50대 이상", "unknown"]
- `gender`: ["여성", "남성", "unknown"]

## 출력
- `output/intake/raw_minimal_input.json` (원본 저장)
- `output/intake/normalized_profile.json` (정규화 결과)

정규화 결과 포맷:
```json
{
  "health_goal": "fatigue_management",
  "age_group": "30s",
  "gender": "female",
  "raw_health_goal": "피로 관리",
  "raw_age_group": "30대",
  "raw_gender": "여성"
}
```

## 스크립트
- `scripts/normalize.py`: 검증 + 정규화 통합 처리

## 성공 기준
- `health_goal` 필드 존재
- `age_group`, `gender`는 enum 값 또는 `unknown`
- 내부 코드값 매핑 완료

## 실패 처리
- 자동 재시도 2회
- 이후 프론트엔드에 입력 오류 반환
