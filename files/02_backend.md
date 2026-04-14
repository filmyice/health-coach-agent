# 건강 코치 에이전트 시스템 — 백엔드 설계
## 버전: v2.0

---

## 관련 문서

| 파일명 | 담당 영역 |
|--------|----------|
| `00_overview.md` | 전체 개요, 공통 원칙, 시스템 경계 |
| `01_frontend.md` | 프론트엔드 — 입력 UI, 출력 화면, 사용자 흐름 |
| `02_backend.md` | **현재 문서** — 입력 처리, 크롤링, 데이터 파이프라인 |
| `03_agent.md` | 에이전트 — 오케스트레이터, 서브에이전트, 스킬 목록 |
| `04_workflow.md` | 워크플로우 — 전체 흐름, 단계별 상세, 상태 전이 |

---

# 1. 백엔드 역할

백엔드는 에이전트가 직접 판단하지 않아도 되는 **결정론적 처리**를 담당한다.

- 프론트엔드 JSON 입력의 스키마 검증 및 정규화
- 규칙 기반 추천 후보 계산 (영양 성분, 위험 플래그)
- Playwright 기반 쇼핑 크롤링 및 상품 정규화
- 가격 비교 및 판매처 선정 계산
- 중간 산출물 및 최종 결과 파일 저장
- 로그 생성

---

# 2. 입력 처리

## 2.1 입력 스키마 검증

프론트엔드에서 전달된 JSON을 검증한다.

**필수 조건:**
- `health_goal` 필드가 반드시 존재한다.
- `age_group`, `gender`는 지정된 enum 값 또는 `"unknown"`이어야 한다.

**허용 enum:**

```json
{
  "health_goal": ["피로 관리", "수면 관리", "면역 관리", "눈 건강", "장 건강", "뼈 건강", "피부·항산화"],
  "age_group": ["10대", "20대", "30대", "40대", "50대 이상", "unknown"],
  "gender": ["여성", "남성", "unknown"]
}
```

**실패 처리:** 자동 재시도 2회 → 이후 프론트엔드에 입력 오류 반환

## 2.2 입력 정규화

검증된 입력을 내부 처리에 적합한 canonical form으로 변환한다.

- 선택지 텍스트를 내부 코드값으로 매핑한다 (예: `"피로 관리"` → `"fatigue_management"`)
- `unknown` 허용 정책을 반영한다.
- 정규화 결과를 `/output/intake/normalized_profile.json`에 저장한다.

---

# 3. 규칙 기반 처리

## 3.1 추천 룰 계산

에이전트가 추천 설명을 생성하기 전에, 스크립트가 먼저 **후보 풀**을 계산한다.

| 입력 | 처리 | 출력 |
|------|------|------|
| `normalized_profile.json` + `primary_health_goal.json` | 건강 목표 × 나이대 × 성별 기반 룰셋 조회 | `food_candidates.json`, `habit_candidates.json`, `nutrient_candidates.json` |

룰셋 파일은 각 스킬의 `/references/` 폴더에서 관리한다.

## 3.2 위험 플래그 계산

사용자 프로필과 안전 질문 응답을 기반으로 위험 조건을 추출한다.

**주요 위험 플래그:**

| 플래그 | 트리거 조건 |
|--------|-----------|
| `has_medication` | 복용 중인 약 있음 |
| `pregnancy_or_breastfeeding` | 임신·수유 중 |
| `chronic_condition` | 기저질환 있음 |
| `allergy` | 알레르기 있음 |
| `duplicate_supplement` | 기존 복용 영양제 중복 가능성 |
| `consult_required` | 위 조건 중 1개 이상 해당 시 자동 설정 |

출력: `/output/risk/risk_flags.json`

## 3.3 주의사항 룰 조회

영양 성분 후보 각각에 대해 룰 DB에서 주의사항을 조회한다.

**주의사항 구조:**

```json
{
  "nutrient_name": "비타민 D",
  "caution_level": "warning",
  "short_cautions": ["과다 복용 시 고칼슘혈증 가능", "신장 질환자는 주의"],
  "interaction_flags": ["칼슘 보충제와 병용 시 용량 조절 필요"],
  "duplicate_risk": false,
  "consultation_needed": false
}
```

출력: `/output/recommendation/nutrient_cautions.json`

---

# 4. 쇼핑 크롤링 파이프라인

## 4.1 크롤링 도구

**Playwright** (Python 또는 Node.js)

선택 이유:
- 쿠팡·네이버 쇼핑은 JS 렌더링이 필요하다.
- 전체 플랫폼을 단일 도구로 통일해 유지보수를 단순화한다.
- Claude Code 환경에서 `playwright install` 후 바로 실행 가능하다.

## 4.2 크롤링 대상 및 우선순위

| 순위 | 플랫폼 | 특성 |
|------|--------|------|
| 1 | 쿠팡 | 로켓배송 중심, 가격 신뢰도 높음 |
| 2 | 네이버 쇼핑 | 가격비교 통합, 다양한 판매처 |
| 3 | iHerb | 건강기능식품 전문, 해외 제품 |
| 4 | 올리브영 | 국내 헬스·뷰티 전문 |

## 4.3 크롤링 흐름

```
[검색 질의 생성] → search_queries.json
    ↓
[Playwright 실행] — 플랫폼별 순차 크롤링
    ├── 쿠팡 크롤러
    ├── 네이버 크롤러
    ├── iHerb 크롤러
    └── 올리브영 크롤러
    ↓
[raw_product_results.json] — 원본 결과 저장
    ↓
[상품 정규화] — 비교 가능한 구조로 변환
    ↓
[normalized_products.json]
    ↓
[가격 비교 계산]
    ↓
[price_comparison.json]
```

## 4.4 크롤링 유의사항

- 쿠팡·네이버는 봇 차단 정책이 있으므로 User-Agent 설정 및 지연 처리(wait) 필수
- 각 플랫폼의 CSS 선택자와 대기 전략은 `/.claude/skills/shopping-search/references/`에 플랫폼별로 관리
- 크롤링 실패는 **플랫폼 단위로 격리** 처리 (전체 워크플로우 중단 금지)

**실패 처리:**

| 상황 | 처리 |
|------|------|
| 플랫폼 크롤링 일시 실패 | 해당 플랫폼 재시도 1회 |
| 재시도 후 실패 | 해당 플랫폼 생략 + 로그 기록 |
| 모든 플랫폼 실패 | 쇼핑 섹션 전체 생략, 건강 추천 결과만 반환 |

## 4.5 상품 정규화 필드

크롤링 결과를 다음 구조로 정규화한다.

```json
{
  "product_name": "상품명",
  "nutrient": "비타민 D",
  "price": 15000,
  "shipping_fee": 0,
  "total_price": 15000,
  "price_per_unit": 50,
  "unit_type": "정",
  "monthly_supply": 300,
  "price_per_month": 15000,
  "platform": "coupang",
  "seller": "판매자명",
  "is_official": true,
  "url": "https://...",
  "crawled_at": "2025-01-01T12:00:00Z"
}
```

## 4.6 가격 비교 기준

| 비교 항목 | 설명 |
|----------|------|
| 총 판매가 | 상품 기본가 |
| 배송비 포함 실구매가 | 총 판매가 + 배송비 |
| 1개월분 기준 가격 | 용량 기준 월 비용 환산 |
| 1정·1캡슐당 가격 | 단위 비용 비교 |
| 공식몰 여부 | 신뢰도 가중치 |

**결과 유형:** 최저가 판매처 / 가성비 판매처 / 추천 판매처

---

# 5. 산출물 파일 목록

| 파일 경로 | 형식 | 생성 주체 | 용도 |
|----------|------|----------|------|
| `/output/intake/raw_minimal_input.json` | JSON | 스크립트 | 최소 입력 원본 |
| `/output/intake/normalized_profile.json` | JSON | 스크립트 | 정규화 프로필 |
| `/output/intent/primary_health_goal.json` | JSON | 에이전트 | 대표 건강 목표 |
| `/output/decision/refinement_needed.json` | JSON | 에이전트 | 보정 질문 필요 여부 |
| `/output/intake/refinement_answers.json` | JSON | 스크립트 (FE 수신) | 추가 질문 응답 |
| `/output/recommendation/food_candidates.json` | JSON | 스크립트 | 음식 추천 후보 |
| `/output/recommendation/habit_candidates.json` | JSON | 스크립트 | 생활습관 추천 후보 |
| `/output/recommendation/nutrient_candidates.json` | JSON | 스크립트 | 영양 성분 후보 |
| `/output/recommendation/nutrient_cautions.json` | JSON | 스크립트 | 성분별 주의사항 초안 |
| `/output/recommendation/refined_recommendations.json` | JSON | 스크립트+에이전트 | 보정 추천 |
| `/output/recommendation/refined_nutrient_cautions.json` | JSON | 스크립트+에이전트 | 보정된 주의사항 |
| `/output/risk/risk_flags.json` | JSON | 스크립트 | 위험 플래그 |
| `/output/recommendation/final_health_plan.json` | JSON | 에이전트+스크립트 | 최종 건강 추천 결과 |
| `/output/content/final_health_summary.md` | Markdown | 에이전트 | 사용자용 건강 요약 |
| `/output/shopping/search_queries.json` | JSON | 에이전트+스크립트 | 쇼핑 검색 질의 |
| `/output/shopping/raw_product_results.json` | JSON | Playwright | 상품 원본 결과 |
| `/output/shopping/normalized_products.json` | JSON | 스크립트 | 정규화된 상품 정보 |
| `/output/shopping/price_comparison.json` | JSON | 스크립트 | 가격 비교 결과 |
| `/output/shopping/shopping_summary.md` | Markdown | 에이전트 | 쇼핑 설명 |
| `/output/final/user_result.json` | JSON | 스크립트 | 최종 사용자 결과 |
| `/output/final/user_result.md` | Markdown | 스크립트 | 최종 사용자 리포트 |
| `/output/qa/safety_review.json` | JSON | 서브에이전트 | 안전 검토 보고서 |
| `/output/qa/commerce_review.json` | JSON | 서브에이전트 | 쇼핑 검토 보고서 |
| `/output/qa/final_validation_report.json` | JSON | 스크립트+에이전트 | 최종 검증 결과 |

---

# 6. 데이터 전달 패턴

| 방식 | 사용 시점 |
|------|----------|
| **파일 기반** | 구조화 데이터(JSON), 설명 초안(MD), 주의사항 세트, 검증 보고서, 상품 목록, 가격 비교 결과 |
| **프롬프트 인라인** | 간단한 상태값, yes/no 플래그, 소규모 메타데이터 |

중간 산출물은 `/output/` 하위에 저장하고 파일 경로 기반으로 에이전트에 전달한다.

---

# 7. 폴더 구조 (스크립트 관련)

```
/project-root
  ├── /output
  │   ├── /intake          # 입력 수집·정규화 결과
  │   ├── /intent          # 건강 목표 해석 결과
  │   ├── /decision        # 보정 질문 판단 결과
  │   ├── /recommendation  # 추천 후보·보정·최종 결과
  │   ├── /risk            # 위험 플래그
  │   ├── /content         # 설명 생성 결과
  │   ├── /shopping        # 크롤링·가격비교·쇼핑 설명
  │   ├── /final           # 최종 사용자 결과
  │   └── /qa              # 검증·검토 보고서
  └── /.claude
      └── /skills
          ├── intake-normalizer/scripts/      # 검증·정규화 스크립트
          ├── nutrient-recommender/scripts/   # 영양 성분 룰 계산
          ├── caution-generator/scripts/      # 주의사항 룰 조회
          ├── risk-flagger/scripts/           # 위험 플래그 계산
          ├── shopping-search/scripts/        # Playwright 크롤러
          │   ├── crawl_coupang.py
          │   ├── crawl_naver.py
          │   ├── crawl_iherb.py
          │   └── crawl_oliveyoung.py
          ├── price-compare/scripts/          # 가격 비교 계산
          ├── policy-guard/scripts/           # 금지 표현 검출
          └── result-packager/scripts/        # 최종 결과 패키징
```
