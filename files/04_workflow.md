# 건강 코치 에이전트 시스템 — 워크플로우 설계
## 버전: v2.0

---

## 관련 문서

| 파일명 | 담당 영역 |
|--------|----------|
| `00_overview.md` | 전체 개요, 공통 원칙, 시스템 경계 |
| `01_frontend.md` | 프론트엔드 — 입력 UI, 출력 화면, 사용자 흐름 |
| `02_backend.md` | 백엔드 — 입력 처리, 크롤링, 데이터 파이프라인 |
| `03_agent.md` | 에이전트 — 오케스트레이터, 서브에이전트, 스킬 목록 |
| `04_workflow.md` | **현재 문서** — 전체 흐름, 단계별 상세, 상태 전이, 검증 |

---

# 1. 전체 흐름 다이어그램

```
[프론트엔드] raw_input.json 전달
    │
    ▼
[Step 1]  입력 수집 및 스키마 검증          스크립트
[Step 2]  입력 정규화                       스크립트
[Step 3]  1차 건강 목표 해석                에이전트 판단
[Step 4]  1차 음식 추천 생성               규칙 + 에이전트
[Step 5]  1차 운동/생활습관 추천 생성       규칙 + 에이전트
[Step 6]  1차 영양 성분 추천 생성          규칙 기반
[Step 7]  성분별 주의사항 초안 생성        규칙 + 에이전트
[Step 8]  추가 보정 질문 여부 판단         에이전트 판단
    │
    ├── Yes ──→ [Step 9] 보정 질문 → 프론트엔드 반환
    │                └── 응답 수신 → [Step 10] 추천 보정
    └── No  ──→ [Step 10] 보정 없이 진행
    │
    ▼
[Step 11] 위험 플래그 확인                  스크립트
    │
    ├── 고위험 ──→ safety-reviewer 호출
    └── 정상   ──→ 계속
    │
    ▼
[Step 12] 최종 통합 추천 생성              에이전트 + 스크립트
[Step 13] 최종 설명 생성                   에이전트 판단
    │
    ▼
[Step 14] 쇼핑 검색 질의 생성              에이전트 + 스크립트
[Step 15] Playwright 크롤링 수행           스크립트
          (쿠팡 → 네이버 → iHerb → 올리브영)
[Step 16] 상품 정보 정규화                 스크립트
[Step 17] 가격 비교 및 판매처 선정        스크립트
[Step 18] 쇼핑 설명 생성                   에이전트 판단
    │
    ▼
[Step 19] 최종 결과 병합                   스크립트
[Step 20] 품질 검증                        스크립트 + 서브에이전트
          ├── safety-reviewer
          └── commerce-reviewer
[Step 21] 사용자 출력 생성                 스크립트
    │
    ▼
[프론트엔드] user_result.json + user_result.md 반환
```

---

# 2. 단계별 상세 정의

## 건강 추천 파이프라인

### Step 1. 입력 수집 및 스키마 검증

| 항목 | 내용 |
|------|------|
| 목적 | 프론트엔드에서 전달된 JSON 입력의 유효성 검증 |
| 입력 | 프론트엔드 `raw_input.json` |
| 출력 | `/output/intake/raw_minimal_input.json` |
| 처리 | 스크립트 |
| 성공 기준 | `health_goal` 필드 존재. `age_group`·`gender`는 enum 값 또는 `unknown` |
| 검증 방법 | 스키마 검증 |
| 실패 처리 | 자동 재시도 2회 → 프론트엔드에 입력 오류 반환 |

### Step 2. 입력 정규화

| 항목 | 내용 |
|------|------|
| 목적 | 최소 입력을 내부 공통 포맷으로 변환 |
| 입력 | `/output/intake/raw_minimal_input.json` |
| 출력 | `/output/intake/normalized_profile.json` |
| 처리 | 스크립트 |
| 성공 기준 | 내부 enum 및 canonical form 변환 완료. unknown 허용 정책 반영 |
| 검증 방법 | 스키마 검증, 규칙 기반 검증 |
| 실패 처리 | 자동 재시도 1회 → 스킵 + 로그 |

### Step 3. 1차 건강 목표 해석

| 항목 | 내용 |
|------|------|
| 목적 | 최소 입력 기준으로 추천 방향 정의 |
| 입력 | `/output/intake/normalized_profile.json` |
| 출력 | `/output/intent/primary_health_goal.json` |
| 처리 | 에이전트 판단 + 규칙 결합 |
| 성공 기준 | 대표 건강 목표 1개 결정. 보조 관심사 선택적 기록 |
| 검증 방법 | 규칙 기반, LLM 자기 검증 |
| 실패 처리 | 기본 목표만 유지 |

### Step 4. 1차 음식 추천 생성

| 항목 | 내용 |
|------|------|
| 목적 | 건강 목표에 맞는 간단한 음식 추천 생성 |
| 입력 | `/output/intent/primary_health_goal.json` |
| 출력 | `/output/recommendation/food_candidates.json` |
| 처리 | 규칙 기반 + 에이전트 보조 |
| 성공 기준 | 2~4개의 실천 가능한 식품 단위 추천 |
| 검증 방법 | 규칙 기반 검증 |
| 실패 처리 | 자동 재시도 1회 → 일반 건강식 가이드로 대체 |

### Step 5. 1차 운동/생활습관 추천 생성

| 항목 | 내용 |
|------|------|
| 목적 | 사용자가 바로 실행 가능한 행동 중심 습관 제안 |
| 입력 | `/output/intent/primary_health_goal.json` |
| 출력 | `/output/recommendation/habit_candidates.json` |
| 처리 | 규칙 기반 + 에이전트 보조 |
| 성공 기준 | 1~3개의 짧고 쉬운 행동. 생활습관 가이드 수준 (운동 처방 수준 금지) |
| 검증 방법 | 규칙 기반, LLM 자기 검증 |
| 실패 처리 | 자동 재시도 1회 → 일반 습관 가이드로 대체 |

### Step 6. 1차 영양 성분 추천 생성

| 항목 | 내용 |
|------|------|
| 목적 | 건강 목표 기준으로 보수적인 영양 성분 후보 생성 |
| 입력 | `/output/intent/primary_health_goal.json`, `/output/intake/normalized_profile.json` |
| 출력 | `/output/recommendation/nutrient_candidates.json` |
| 처리 | 규칙 기반 |
| 성공 기준 | 1~3개 성분 후보 생성. 공격적 추천 제외 |
| 검증 방법 | 스키마 검증, 규칙 기반 검증 |
| 실패 처리 | 자동 재시도 1회 → 영양 성분 추천 생략 + 로그 |

### Step 7. 성분별 주의사항 초안 생성

| 항목 | 내용 |
|------|------|
| 목적 | 추천된 영양 성분마다 기본 주의사항 생성 |
| 입력 | `/output/recommendation/nutrient_candidates.json`, `/output/intake/normalized_profile.json` |
| 출력 | `/output/recommendation/nutrient_cautions.json` |
| 처리 | 규칙 기반 + 에이전트 보조 |
| 출력 구조 | `nutrient_name`, `caution_level` (info/warning/consult), `short_cautions[]`, `interaction_flags[]`, `duplicate_risk`, `consultation_needed` |
| 성공 기준 | 모든 성분에 최소 1개 이상의 주의사항 생성. 사용자 입력과 충돌하는 경고 누락 없음 |
| 검증 방법 | 스키마 검증, 규칙 기반 검증 |
| 실패 처리 | 자동 재시도 1회 → 기본 공통 주의사항으로 대체 |

### Step 8. 추가 보정 질문 여부 판단

| 항목 | 내용 |
|------|------|
| 목적 | 추가 질문이 필요한지 판단 |
| 입력 | 1차 추천 후보 전체 (Steps 4~7 산출물) |
| 출력 | `/output/decision/refinement_needed.json` |
| 처리 | 에이전트 판단 |
| 판단 기준 | 추천 후보 간 우선순위가 애매한가 / 핵심 정보 1~2개가 추가 필요한가 / 추가 없이도 충분히 유용한 결과가 가능한가 |
| 성공 기준 | yes/no로 정리. 필요 시 어떤 질문을 할지 지정 |
| 검증 방법 | LLM 자기 검증 |
| 실패 처리 | 기본값 `no`, 추가 질문 생략 |

### Step 9. 동적 보정 질문 수행 (조건부)

| 항목 | 내용 |
|------|------|
| 목적 | 필요할 경우 1~2개의 보정 질문을 프론트엔드에 반환하고 응답 수신 |
| 입력 | `/output/decision/refinement_needed.json` |
| 출력 | `/output/intake/refinement_answers.json` |
| 처리 | 에이전트 + 프론트엔드 왕복 |
| 성공 기준 | 선택형 응답 수집. 질문 수 최대 2개 |
| 검증 방법 | 스키마 검증 |
| 실패 처리 | 스킵 + 로그, 1차 추천 유지 |

### Step 10. 추천 결과 및 주의사항 보정

| 항목 | 내용 |
|------|------|
| 목적 | 추가 답변을 바탕으로 음식·습관·영양 추천과 주의사항 재정렬 |
| 입력 | `/output/intake/refinement_answers.json` + 기존 추천 후보들 |
| 출력 | `/output/recommendation/refined_recommendations.json`, `/output/recommendation/refined_nutrient_cautions.json` |
| 처리 | 규칙 기반 + 에이전트 보조 |
| 성공 기준 | 보정이 필요한 항목만 조정. 기존 추천 흐름과 충돌 없음 |
| 검증 방법 | 규칙 기반, LLM 자기 검증 |
| 실패 처리 | 기존 1차 추천 및 주의사항 유지 |

### Step 11. 위험 플래그 확인

| 항목 | 내용 |
|------|------|
| 목적 | 민감한 추천 전에 안전상 주의사항 점검 |
| 입력 | `/output/intake/normalized_profile.json` + 안전 질문 응답 (있을 경우) + 보정된 주의사항 |
| 출력 | `/output/risk/risk_flags.json` |
| 처리 | 규칙 기반 중심 |
| 주요 위험 플래그 | `has_medication` / `pregnancy_or_breastfeeding` / `chronic_condition` / `allergy` / `duplicate_supplement` / `consult_required` |
| 성공 기준 | 고위험 조건 누락 없이 식별 |
| 검증 방법 | 스키마 검증, 규칙 기반 검증 |
| 실패 처리 | 자동 재시도 1회 → 불확실하면 에스컬레이션 플래그 → `safety-reviewer` 호출 |

### Step 12. 최종 통합 추천 생성

| 항목 | 내용 |
|------|------|
| 목적 | 음식, 습관, 영양 성분, 주의사항을 하나의 결과로 통합 |
| 입력 | 보정된 추천 결과 + 보정된 주의사항 + 위험 플래그 |
| 출력 | `/output/recommendation/final_health_plan.json` |
| 처리 | 에이전트 + 스크립트 혼합 |
| 성공 기준 | 네 축이 논리적으로 연결됨. 영양 성분이 음식·습관을 압도하지 않음. 주의사항이 별도 구조로 분리됨 |
| 검증 방법 | 스키마 검증, 규칙 기반 검증 |
| 실패 처리 | 자동 재시도 1회 → 영양 성분 섹션 생략 가능 |

### Step 13. 최종 설명 생성

| 항목 | 내용 |
|------|------|
| 목적 | 사용자가 이해하기 쉬운 자연어 설명 생성 |
| 입력 | `/output/recommendation/final_health_plan.json`, `/output/risk/risk_flags.json` |
| 출력 | `/output/content/final_health_summary.md` |
| 처리 | 에이전트 판단 |
| 생성 원칙 | 과장 금지 / 의료적 진단처럼 말하지 않음 / 음식→습관→영양→주의사항 순서 |
| 성공 기준 | 추천 이유 빠짐 없음. 금지 표현 없음. 주의사항 누락 없음 |
| 검증 방법 | LLM 자기 검증, 규칙 기반 금지 표현 체크 |
| 실패 처리 | 자동 재시도 최대 2회 → 에스컬레이션 |

---

## 쇼핑 연동 파이프라인

### Step 14. 쇼핑 검색 질의 생성

| 항목 | 내용 |
|------|------|
| 목적 | 추천 성분에 맞는 상품 검색 질의 생성 |
| 입력 | `/output/recommendation/final_health_plan.json` |
| 출력 | `/output/shopping/search_queries.json` |
| 처리 | 에이전트 + 스크립트 |
| 성공 기준 | 성분별 1개 이상 질의 생성 |
| 검증 방법 | 규칙 기반 검증 |
| 실패 처리 | 기본 질의 템플릿 사용 |

### Step 15. Playwright 크롤링 수행

| 항목 | 내용 |
|------|------|
| 목적 | 각 쇼핑 플랫폼에서 상품 후보 수집 |
| 입력 | `/output/shopping/search_queries.json` |
| 출력 | `/output/shopping/raw_product_results.json` |
| 처리 | Playwright 스크립트 |
| 크롤링 순서 | 1. 쿠팡 → 2. 네이버 쇼핑 → 3. iHerb → 4. 올리브영 |
| 성공 기준 | 상품명·가격·판매처·링크가 있는 상품 최소 1개 확보 |
| 검증 방법 | 스키마 검증 |
| 실패 처리 | 플랫폼별 재시도 1회 → 실패 플랫폼 생략 + 로그 → 전체 실패 시 쇼핑 섹션 생략 |

### Step 16. 상품 정보 정규화

| 항목 | 내용 |
|------|------|
| 목적 | 상품 정보를 비교 가능한 구조로 변환 |
| 입력 | `/output/shopping/raw_product_results.json` |
| 출력 | `/output/shopping/normalized_products.json` |
| 처리 | 스크립트 중심 |
| 성공 기준 | 가격 비교에 필요한 핵심 필드(상품명, 가격, 배송비, 판매처, 링크) 정리 |
| 검증 방법 | 스키마 검증, 규칙 기반 검증 |
| 실패 처리 | 필수 필드 부족 상품 제거 후 일부 상품만 유지 |

### Step 17. 가격 비교 및 판매처 선정

| 항목 | 내용 |
|------|------|
| 목적 | 최저가·가성비·추천 판매처 산정 |
| 입력 | `/output/shopping/normalized_products.json` |
| 출력 | `/output/shopping/price_comparison.json` |
| 처리 | 스크립트 중심 |
| 비교 기준 | 총 판매가 / 배송비 포함 실구매가 / 1개월분 기준 가격 / 1정·1캡슐당 가격 / 공식몰 여부 |
| 성공 기준 | 성분별 1개 이상의 우선 판매처 결정 |
| 검증 방법 | 규칙 기반 검증 |
| 실패 처리 | 가격 비교 실패 시 상품 후보만 제공 |

### Step 18. 쇼핑 설명 생성

| 항목 | 내용 |
|------|------|
| 목적 | 가격 비교 결과를 사용자에게 이해하기 쉽게 정리 |
| 입력 | `/output/shopping/price_comparison.json` |
| 출력 | `/output/shopping/shopping_summary.md` |
| 처리 | 에이전트 판단 |
| 성공 기준 | 최저가와 추천 판매처를 혼동하지 않음. 가격 변동 가능성 안내 |
| 검증 방법 | LLM 자기 검증, 규칙 기반 검증 |
| 실패 처리 | JSON만 반환, 요약 설명 생략 |

---

## 최종 처리 파이프라인

### Step 19. 최종 결과 병합

| 항목 | 내용 |
|------|------|
| 목적 | 건강 추천 결과와 쇼핑 결과 통합 |
| 입력 | `/output/content/final_health_summary.md` + `/output/shopping/price_comparison.json` + `/output/shopping/shopping_summary.md` |
| 출력 | `/output/final/user_result.json`, `/output/final/user_result.md` |
| 처리 | 스크립트 중심 |
| 성공 기준 | 사용자 흐름이 자연스러움. 쇼핑은 보조 섹션으로 배치 |
| 검증 방법 | 스키마 검증, 규칙 기반 검증 |
| 실패 처리 | 쇼핑 섹션 제거 후 기본 건강 추천 결과 반환 |

### Step 20. 품질 검증

| 항목 | 내용 |
|------|------|
| 목적 | 안전성·정책 준수·쇼핑 표시 적절성 최종 점검 |
| 입력 | `/output/final/user_result.json` |
| 출력 | `/output/qa/final_validation_report.json` |
| 처리 | 스크립트 + 서브에이전트 |
| 담당 | `safety-reviewer` (안전·표현 검토) + `commerce-reviewer` (쇼핑 표시 검토) |
| 성공 기준 | 금지 표현 없음. 주의사항 누락 없음. 가격 표시 적절 |
| 검증 방법 | 규칙 기반 + 서브에이전트 검토 |
| 실패 처리 | 해당 섹션 재생성 또는 에스컬레이션 |

### Step 21. 사용자 출력 생성

| 항목 | 내용 |
|------|------|
| 목적 | 최종 결과를 프론트엔드가 소비할 수 있는 형태로 반환 |
| 입력 | `/output/final/user_result.json` + `/output/qa/final_validation_report.json` |
| 출력 | 프론트엔드에 JSON 응답 반환 |
| 처리 | 스크립트 |

---

# 3. 상태 전이 정의

```
RAW_INPUT_RECEIVED
  → INPUT_NORMALIZED
  → PRIMARY_GOAL_IDENTIFIED
  → INITIAL_RECOMMENDATIONS_READY
  → CAUTIONS_DRAFTED
  → REFINEMENT_DECIDED
  → REFINEMENT_COMPLETED     (보정 있을 때)
  → RISK_CHECKED
  → RISK_FLAGGED             (고위험 감지 시)
  → RISK_CLEAR               (정상 시)
  → FINAL_HEALTH_PLAN_READY
  → HEALTH_SUMMARY_GENERATED
  → SHOPPING_QUERY_BUILT
  → PRODUCTS_FETCHED
  → PRODUCTS_NORMALIZED
  → PRICE_COMPARED
  → FINAL_RESULT_PACKAGED
  → VALIDATED
  → DONE

  (실패 시) → ESCALATED 또는 FAILED
```

---

# 4. 단계별 성공 기준·검증·실패 처리 요약

| 단계 | 성공 기준 | 검증 방법 | 실패 처리 |
|------|----------|----------|----------|
| 입력 수집 | `health_goal` 필드 존재 | 스키마 검증 | 재시도 2회 |
| 입력 정규화 | canonical form 완성 | 스키마/규칙 | 재시도 1회 / 로그 |
| 목표 해석 | 대표 목표 1개 결정 | 규칙/LLM | 기본값 사용 |
| 음식 추천 | 2~4개 음식 생성 | 규칙 | 일반 가이드 대체 |
| 습관 추천 | 1~3개 행동 생성 | 규칙/LLM | 일반 가이드 대체 |
| 영양 추천 | 1~3개 성분 생성 | 스키마/규칙 | 생략 가능 |
| 주의사항 생성 | 성분별 경고 생성 | 스키마/규칙 | 공통 주의사항 대체 |
| 보정 질문 판단 | yes/no 명확 | LLM 검증 | no 처리 |
| 추천 보정 | 우선순위 정리 | 규칙/LLM | 기존 추천 유지 |
| 위험 체크 | 고위험 누락 없음 | 스키마/규칙 | 에스컬레이션 |
| 설명 생성 | 과장·진단형 표현 없음 | LLM/규칙 | 재시도 2회 / 에스컬레이션 |
| 쇼핑 질의 생성 | 성분별 질의 생성 | 규칙 | 기본 템플릿 사용 |
| 크롤링 | 상품 후보 최소 1개 | 스키마 | 플랫폼별 재시도 / 생략 |
| 가격 비교 | 판매처 선정 완료 | 규칙 | 상품 후보만 제공 |
| 최종 패키징 | 구조 완성 | 스키마/규칙 | 쇼핑 제거 후 반환 |
| 품질 검증 | 금지 표현 없음 / 주의사항 누락 없음 | 규칙 + 서브에이전트 | 재생성 / 에스컬레이션 |
