# 건강 코치 에이전트 시스템 — 메인 오케스트레이터

## 시스템 목적

이 시스템은 사용자의 **최소 입력**만으로 음식·생활습관·영양 성분 추천을 제공하고,
추천 성분에 대한 쇼핑 가격 비교 및 판매처를 안내하는 경량 건강 코치 시스템이다.

**비의료적 정책 경계 (절대 위반 금지):**
- 진단, 처방, 치료, 질병 확정 등의 표현을 사용하지 않는다.
- "치료된다", "완치", "의학적으로 입증" 같은 표현은 사용 금지다.
- 모든 추천은 "도움이 될 수 있습니다", "고려해 볼 수 있습니다" 수준으로 표현한다.
- 고위험 상황(임신·수유·복용약·기저질환·알레르기)에는 반드시 전문가 상담을 권고한다.

---

## 실행 환경

- 에이전트 실행: Claude Code CLI
- 입력: `output/intake/raw_minimal_input.json` (프론트엔드에서 전달된 JSON)
- 출력: `output/final/user_result.json` + `output/final/user_result.md`
- 스크립트 언어: Python / Node.js 혼용

---

## 실행 방법 — run.py 사용 (필수)

**모든 스크립트 실행은 반드시 `run.py`를 통해 수행한다.** 개별 스크립트를 직접 호출하지 않는다.

### 사용자로부터 추천 요청이 들어오면

```bash
# 1. 입력 파일 준비 확인
# output/intake/raw_minimal_input.json 이 존재하는지 확인

# 2. 파이프라인 전체 시작
python run.py --skip-shopping          # 쇼핑 제외 (기본 권장)
python run.py                          # 쇼핑 포함 (Playwright 설치 필요)

# 3. 스텝 목록 확인
python run.py --list

# 4. 에이전트 스텝 완료 후 재개 (N번 스텝부터)
python run.py --from N --skip-shopping

# 5. 특정 스텝만 실행
python run.py --step 12

# 6. 처음부터 다시 시작
python run.py --reset
```

### 에이전트가 해야 할 일 (AGENT 스텝)

`run.py` 출력에서 `[AGENT 판단 필요]` 메시지가 나타나면, 그 스텝의 지침에 따라 **직접 파일을 작성**한다.

| 스텝 | 에이전트 작업 | 출력 파일 |
|------|-------------|---------|
| Step 3 | `normalized_profile.json` + `goal_rules.json` 읽고 목표 해석 | `output/intent/primary_health_goal.json` |
| Step 9 | 보정 질문을 사용자에게 제시하고 응답 저장 (조건부) | `output/intake/refinement_answers.json` |
| Step 13 | `final_health_plan.json` 읽고 자연어 건강 요약 작성 | `output/content/final_health_summary.md` |
| Step 14 | 추천 성분별 쇼핑 검색 질의 생성 | `output/shopping/search_queries.json` |
| Step 18 | 가격 비교 결과 설명 작성 | `output/shopping/shopping_summary.md` |

에이전트 스텝 완료 후 `python run.py --from [다음 스텝 번호]`로 재개한다.

### 전형적인 실행 순서 (예시)

```
python run.py --skip-shopping
  → Step 1~2 자동 실행 (스크립트)
  → Step 3: [AGENT] primary_health_goal.json 작성
python run.py --from 4 --skip-shopping
  → Step 4~8 자동 실행 (스크립트)
  → Step 9: [AGENT] refinement_answers.json 작성 (필요 시)
python run.py --from 10 --skip-shopping
  → Step 10~12 자동 실행
  → Step 13: [AGENT] final_health_summary.md 작성
python run.py --step 19 --step 20
  → 최종 결과 생성 완료
```

---

## 전체 오케스트레이션 원칙

모든 단계는 **아래 순서를 반드시 지킨다.** 단계를 건너뛰거나 순서를 바꾸지 않는다.

### 건강 추천 파이프라인

| 단계 | 작업 | 처리 주체 | 스크립트 |
|------|------|----------|---------|
| Step 1 | 입력 수집 및 스키마 검증 | 스크립트 | `.claude/skills/intake-normalizer/scripts/normalize.py` |
| Step 2 | 입력 정규화 | 스크립트 | `.claude/skills/intake-normalizer/scripts/normalize.py` |
| Step 3 | 1차 건강 목표 해석 | 에이전트 + 규칙 | `.claude/skills/goal-interpreter/` 참조 |
| Step 4 | 1차 음식 추천 생성 | 규칙 + 에이전트 보조 | `.claude/skills/food-recommender/scripts/recommend_food.py` |
| Step 5 | 1차 운동/생활습관 추천 생성 | 규칙 + 에이전트 보조 | `.claude/skills/habit-recommender/scripts/recommend_habit.py` |
| Step 6 | 1차 영양 성분 추천 생성 | 규칙 기반 | `.claude/skills/nutrient-recommender/scripts/recommend_nutrient.py` |
| Step 7 | 성분별 주의사항 초안 생성 | 규칙 + 에이전트 보조 | `.claude/skills/caution-generator/scripts/generate_cautions.py` |
| Step 8 | 추가 보정 질문 여부 판단 | 에이전트 판단 | `.claude/skills/refinement-manager/scripts/manage_refinement.py` |
| Step 9 | 동적 보정 질문 수행 (조건부) | 에이전트 + 프론트엔드 왕복 | — |
| Step 10 | 추천 결과 및 주의사항 보정 | 규칙 + 에이전트 보조 | `.claude/skills/refinement-manager/scripts/manage_refinement.py` |
| Step 11 | 위험 플래그 확인 | 스크립트 중심 | `.claude/skills/risk-flagger/scripts/flag_risks.py` |
| Step 12 | 최종 통합 추천 생성 | 에이전트 + 스크립트 | — |
| Step 13 | 최종 설명 생성 | 에이전트 판단 | `.claude/skills/explanation-writer/` 참조 |

### 쇼핑 연동 파이프라인

| 단계 | 작업 | 처리 주체 | 스크립트 |
|------|------|----------|---------|
| Step 14 | 쇼핑 검색 질의 생성 | 에이전트 + 스크립트 | — |
| Step 15 | Playwright 크롤링 수행 | Playwright 스크립트 | `.claude/skills/shopping-search/scripts/` |
| Step 16 | 상품 정보 정규화 | 스크립트 | `.claude/skills/shopping-search/scripts/normalize_products.py` |
| Step 17 | 가격 비교 및 판매처 선정 | 스크립트 | `.claude/skills/price-compare/scripts/compare_prices.py` |
| Step 18 | 쇼핑 설명 생성 | 에이전트 판단 | — |

### 최종 처리 파이프라인

| 단계 | 작업 | 처리 주체 | 스크립트 |
|------|------|----------|---------|
| Step 19 | 최종 결과 병합 | 스크립트 | `.claude/skills/result-packager/scripts/package_result.py` |
| Step 20 | 품질 검증 | 스크립트 + 서브에이전트 | `.claude/skills/policy-guard/scripts/check_policy.py` |
| Step 21 | 사용자 출력 생성 | 스크립트 | `.claude/skills/result-packager/scripts/package_result.py` |

---

## 입력 최소화 원칙 및 동적 질문 정책

- 초기 입력은 `health_goal`, `age_group`, `gender` 3가지만 받는다.
- 추가 질문(보정 질문)은 Step 8 판단 결과 `refinement_needed = true`일 때만 노출한다.
- 보정 질문은 **최대 2개**를 초과하지 않는다.
- 안전 확인 질문(Level 3)은 위험 플래그 감지 시에만 요청한다.
- 질문이 불필요하면 건너뛰고 1차 추천으로 진행한다.

---

## 추천 우선순위 (절대 순서)

최종 결과는 반드시 다음 순서로 제시한다:

```
1. 음식 추천 (2~4개)
2. 운동/생활습관 추천 (1~3개)
3. 영양 성분 추천 (1~3개)
4. 성분별 주의사항 (성분마다 분리 표기)
5. 쇼핑 정보 (보조 섹션, 실패 시 생략 가능)
```

영양 성분이 음식·생활습관 추천을 압도하지 않도록 균형을 유지한다.

---

## 영양 성분별 주의사항 표기 원칙

- 모든 추천 성분에는 반드시 주의사항 섹션이 포함된다.
- 주의사항은 추천 이유와 **반드시 분리**해서 별도 섹션으로 표시한다.
- `caution_level` 기준:
  - `info`: 일반 정보 수준 (회색/파란색)
  - `warning`: 주의 필요 (주황색)
  - `consult`: 전문가 상담 권고 (빨간색)
- 주의사항은 1~3개의 핵심 bullet 형태로 작성한다.

---

## 스킬 호출 기준

| 스킬명 | 호출 시점 |
|--------|----------|
| `intake-normalizer` | Step 1~2: 프론트엔드 JSON 수신 직후 |
| `goal-interpreter` | Step 3: 정규화 프로필 준비 완료 시 |
| `food-recommender` | Step 4: 대표 건강 목표 결정 후 |
| `habit-recommender` | Step 5: 대표 건강 목표 결정 후 |
| `nutrient-recommender` | Step 6: 대표 건강 목표 결정 후 |
| `caution-generator` | Step 7: 영양 성분 후보 생성 직후 |
| `refinement-manager` | Step 8~10: 1차 추천 세트 생성 후 |
| `risk-flagger` | Step 11: 최종 추천 전 안전 확인 단계 |
| `explanation-writer` | Step 13: 최종 건강 추천 세트 확정 후 |
| `shopping-search` | Step 15: 최종 추천 성분 목록 확정 후 |
| `price-compare` | Step 17: 상품 검색 결과 준비 완료 후 |
| `policy-guard` | Step 20: 설명 생성 후 / 최종 결과 직전 |
| `result-packager` | Step 19, 21: 모든 검수 완료 후 |

---

## 서브에이전트 호출 기준

| 서브에이전트 | 호출 파일 | 호출 조건 |
|-------------|----------|----------|
| `safety-reviewer` | `.claude/agents/safety-reviewer/AGENT.md` | 위험 플래그 1개 이상 감지 시 / 설명 생성 2회 실패 시 |
| `commerce-reviewer` | `.claude/agents/commerce-reviewer/AGENT.md` | 쇼핑 설명 생성 완료 후 |

서브에이전트 조율 원칙:
- 메인 에이전트(이 파일)가 전체 오케스트레이션을 담당한다.
- 서브에이전트는 메인을 통해서만 호출된다. 서브에이전트 간 직접 호출은 금지한다.
- 서브에이전트는 필요한 시점에만 로드한다.

---

## 상태 전이 규칙

진행 상태는 아래 순서를 따른다. 이전 상태가 완료되지 않으면 다음으로 진행하지 않는다.

```
RAW_INPUT_RECEIVED
  → INPUT_NORMALIZED
  → PRIMARY_GOAL_IDENTIFIED
  → INITIAL_RECOMMENDATIONS_READY
  → CAUTIONS_DRAFTED
  → REFINEMENT_DECIDED
  → REFINEMENT_COMPLETED     (보정 있을 때만)
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

## 출력 파일 경로 규약

| 파일 경로 | 생성 시점 |
|----------|----------|
| `output/intake/raw_minimal_input.json` | Step 1 |
| `output/intake/normalized_profile.json` | Step 2 |
| `output/intent/primary_health_goal.json` | Step 3 |
| `output/decision/refinement_needed.json` | Step 8 |
| `output/intake/refinement_answers.json` | Step 9 (조건부) |
| `output/recommendation/food_candidates.json` | Step 4 |
| `output/recommendation/habit_candidates.json` | Step 5 |
| `output/recommendation/nutrient_candidates.json` | Step 6 |
| `output/recommendation/nutrient_cautions.json` | Step 7 |
| `output/recommendation/refined_recommendations.json` | Step 10 |
| `output/recommendation/refined_nutrient_cautions.json` | Step 10 |
| `output/risk/risk_flags.json` | Step 11 |
| `output/recommendation/final_health_plan.json` | Step 12 |
| `output/content/final_health_summary.md` | Step 13 |
| `output/shopping/search_queries.json` | Step 14 |
| `output/shopping/raw_product_results.json` | Step 15 |
| `output/shopping/normalized_products.json` | Step 16 |
| `output/shopping/price_comparison.json` | Step 17 |
| `output/shopping/shopping_summary.md` | Step 18 |
| `output/final/user_result.json` | Step 19 |
| `output/final/user_result.md` | Step 19 |
| `output/qa/safety_review.json` | Step 20 (safety-reviewer) |
| `output/qa/commerce_review.json` | Step 20 (commerce-reviewer) |
| `output/qa/final_validation_report.json` | Step 20 |

---

## 검증 및 실패 처리 원칙

| 방식 | 사용 시점 |
|------|----------|
| 자동 재시도 | 형식 오류, 누락, 크롤링 일시 실패 (최대 2회) |
| 에스컬레이션 | 판단 불확실, 정책 경계, 고위험 사례 |
| 스킵 + 로그 | 쇼핑 크롤링 최종 실패, 비핵심 단계 실패 |

쇼핑 크롤링 실패는 전체 워크플로우를 중단하지 않는다.
건강 추천 결과만으로도 완성된 결과를 반환할 수 있다.

---

## Human Review 조건

아래 상황에서는 자동 진행하지 않고 사용자 확인을 요청한다:

- 위험 플래그가 `consult_required = true`인 경우
- 설명 생성 재시도 2회 이후에도 policy-guard 검증 실패 시
- 입력 스키마 검증이 2회 재시도 후에도 실패 시

---

## 로깅 원칙

- 각 단계 완료 시 상태 전이 로그를 남긴다.
- 스킵/실패한 단계는 이유와 함께 기록한다.
- 크롤링 실패는 플랫폼별로 개별 기록한다.
- 로그 파일 경로: `output/logs/run.log` (없으면 stdout 출력)
