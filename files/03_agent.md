# 건강 코치 에이전트 시스템 — 에이전트 설계
## 버전: v2.0

---

## 관련 문서

| 파일명 | 담당 영역 |
|--------|----------|
| `00_overview.md` | 전체 개요, 공통 원칙, 시스템 경계 |
| `01_frontend.md` | 프론트엔드 — 입력 UI, 출력 화면, 사용자 흐름 |
| `02_backend.md` | 백엔드 — 입력 처리, 크롤링, 데이터 파이프라인 |
| `03_agent.md` | **현재 문서** — 오케스트레이터, 서브에이전트, 스킬 목록 |
| `04_workflow.md` | 워크플로우 — 전체 흐름, 단계별 상세, 상태 전이 |

---

# 1. 에이전트 구조 개요

```
health-orchestrator (메인, CLAUDE.md)
    ├── safety-reviewer     (서브에이전트, 고위험 추천 검토 시)
    └── commerce-reviewer   (서브에이전트, 쇼핑 결과 검수 시)
```

**서브에이전트 조율 원칙:**
- 메인 에이전트(CLAUDE.md)가 전체 오케스트레이션을 담당한다.
- 서브에이전트는 메인을 통해서만 호출된다. 서브에이전트 간 직접 호출은 금지한다.
- 서브에이전트는 필요한 시점에만 로드하여 컨텍스트 효율을 높인다.

---

# 2. 에이전트가 직접 수행하는 판단

스크립트가 아닌 에이전트(LLM)가 직접 처리해야 할 항목이다.

- 건강 목표 해석 및 추천 방향 설정
- 추가 보정 질문 필요 여부 판단
- 음식·생활습관·영양 추천 설명 생성
- 추천 항목 간 서술 우선순위 결정
- 주의사항의 표현 수위 조정
- 쇼핑 검색 질의 생성
- 쇼핑 결과 설명 생성
- 정성적 자기 검증 (톤, 과장 여부, 누락 여부)

---

# 3. 메인 에이전트: `health-orchestrator`

## 역할
- 전체 워크플로우 오케스트레이션
- 스킬 호출 및 상태 전이 관리
- 추천 흐름 유지 및 최종 결과 구성 제어
- 서브에이전트 safety-reviewer, commerce-reviewer 조율

## 트리거
- 시스템 시작 (프론트엔드 JSON 입력 수신 시)

## 입력
- 프론트엔드에서 전달된 JSON

## 출력
- `/output/final/user_result.json`
- `/output/final/user_result.md`

## CLAUDE.md 핵심 섹션 목록
_(구현 시 상세 작성)_

- 시스템 목적 및 비의료적 정책 경계
- 전체 오케스트레이션 원칙 (단계별 실행 순서)
- 입력 최소화 원칙 및 동적 질문 정책
- 음식/습관/영양 추천 우선순위
- 영양 성분별 주의사항 표기 원칙
- 스킬 호출 기준
- 서브에이전트 호출 기준
- 상태 전이 규칙
- 출력 파일 경로 규약
- 검증 및 실패 처리 원칙
- Human review 조건
- 로깅 원칙

---

# 4. 서브에이전트: `safety-reviewer`

## 역할
- 고위험 추천 검토
- 진단·처방처럼 보이는 표현 제거 검토
- 주의사항 누락 여부 검토
- 민감 상황에서 경고·상담 권고 필요 여부 판단

## 트리거 조건
- 위험 플래그가 1개 이상 감지되었을 때
- 설명 생성 실패가 2회 이후 에스컬레이션 발생 시

## 입력
- `/output/risk/risk_flags.json`
- `/output/content/final_health_summary.md`

## 출력
- `/output/qa/safety_review.json`

## 참조 스킬
- `policy-guard`
- `caution-generator`

## 데이터 전달 방식
- 파일 기반

## AGENT.md 핵심 섹션 목록
_(구현 시 상세 작성)_

- 역할 및 책임 범위
- 트리거 조건
- 입출력 파일 경로
- 안전 검토 기준 (금지 표현 목록, 고위험 판단 기준)
- 참조 스킬 목록
- 검토 결과 출력 포맷

---

# 5. 서브에이전트: `commerce-reviewer`

## 역할
- 가격 비교 결과의 표시 적절성 검토
- 최저가와 추천 판매처의 혼동 여부 검토
- 이상치 가격 또는 부적절 상품 노출 방지 검토

## 트리거 조건
- 쇼핑 설명 생성 완료 후

## 입력
- `/output/shopping/price_comparison.json`
- `/output/shopping/shopping_summary.md`

## 출력
- `/output/qa/commerce_review.json`

## 참조 스킬
- `price-compare`
- `policy-guard`

## 데이터 전달 방식
- 파일 기반

## AGENT.md 핵심 섹션 목록
_(구현 시 상세 작성)_

- 역할 및 책임 범위
- 트리거 조건
- 입출력 파일 경로
- 가격 표시 검토 기준 (이상치 판단, 최저가/추천 구분 기준)
- 참조 스킬 목록
- 검토 결과 출력 포맷

---

# 6. 스킬 목록

스킬은 기능 단위의 도구/스크립트 묶음이다. 여러 에이전트가 공유 가능하다.

| 스킬명 | 역할 | 트리거 조건 | 처리 방식 |
|--------|------|------------|----------|
| `intake-normalizer` | 최소 입력 수집 결과를 내부 표준 포맷으로 변환 | 프론트엔드 JSON 입력 도착 시 | 스크립트 |
| `goal-interpreter` | 사용자 건강 목표 해석 및 1차 추천 방향 설정 | 정규화 프로필 준비 시 | 에이전트 + 규칙 |
| `food-recommender` | 건강 목표에 맞는 음식 추천 생성 | 대표 건강 목표 결정 시 | 규칙 + 에이전트 보조 |
| `habit-recommender` | 건강 목표에 맞는 생활습관·운동 추천 생성 | 대표 건강 목표 결정 시 | 규칙 + 에이전트 보조 |
| `nutrient-recommender` | 영양 성분 후보 생성 및 정렬 | 대표 건강 목표 결정 시 | 규칙 기반 |
| `caution-generator` | 추천 성분별 주의사항 생성 (금기, 중복, 상호작용) | 영양 성분 후보 생성 시 | 규칙 + 에이전트 보조 |
| `refinement-manager` | 추가 질문 필요 여부 판단, 보정 질문 후보 관리, 추천 보정 | 1차 추천 세트 생성 시 | 에이전트 |
| `risk-flagger` | 안전 플래그 추출, 중복 섭취 위험 확인 | 최종 추천 전 안전 확인 단계 도달 시 | 스크립트 중심 |
| `explanation-writer` | 음식·습관·영양 추천 결과 설명 생성, 주의사항 문구 정리 | 최종 건강 추천 세트 확정 시 | 에이전트 |
| `shopping-search` | Playwright 기반 쿠팡→네이버→iHerb→올리브영 크롤링 | 최종 추천 성분 목록 확정 시 | Playwright 스크립트 |
| `price-compare` | 가격 정규화, 1정당 가격 계산, 판매처 비교·선정 | 상품 검색 결과 준비 시 | 스크립트 |
| `policy-guard` | 금지 표현 차단, 진단형 표현 검출, 주의사항 과장 표현 검수 | 설명 생성 후 / 최종 결과 직전 | 스크립트 + 에이전트 |
| `result-packager` | 사용자용 결과 JSON·Markdown 생성, 최종 파일 저장 | 모든 검수 단계 완료 시 | 스크립트 |

---

# 7. 스킬 폴더 구조

```
/.claude
  ├── /skills
  │   ├── intake-normalizer
  │   │   ├── SKILL.md
  │   │   └── /scripts
  │   ├── goal-interpreter
  │   │   ├── SKILL.md
  │   │   └── /references       # 건강 목표별 도메인 지식
  │   ├── food-recommender
  │   │   ├── SKILL.md
  │   │   ├── /scripts
  │   │   └── /references       # 건강 목표별 음식 룰셋
  │   ├── habit-recommender
  │   │   ├── SKILL.md
  │   │   ├── /scripts
  │   │   └── /references       # 건강 목표별 습관 룰셋
  │   ├── nutrient-recommender
  │   │   ├── SKILL.md
  │   │   ├── /scripts
  │   │   └── /references       # 영양 성분 룰셋 (목표별)
  │   ├── caution-generator
  │   │   ├── SKILL.md
  │   │   ├── /scripts
  │   │   └── /references       # 금기·상호작용 룰 DB
  │   ├── refinement-manager
  │   │   ├── SKILL.md
  │   │   └── /scripts
  │   ├── risk-flagger
  │   │   ├── SKILL.md
  │   │   └── /scripts
  │   ├── explanation-writer
  │   │   └── SKILL.md
  │   ├── shopping-search
  │   │   ├── SKILL.md
  │   │   ├── /scripts           # Playwright 크롤러 (플랫폼별)
  │   │   └── /references        # 플랫폼별 CSS 선택자·봇 대응 전략
  │   ├── price-compare
  │   │   ├── SKILL.md
  │   │   └── /scripts
  │   ├── policy-guard
  │   │   ├── SKILL.md
  │   │   ├── /scripts
  │   │   └── /references        # 금지 표현 목록
  │   └── result-packager
  │       ├── SKILL.md
  │       └── /scripts
  └── /agents
      ├── safety-reviewer
      │   └── AGENT.md
      └── commerce-reviewer
          └── AGENT.md
```

---

# 8. 스킬 vs 서브에이전트 구분 기준

| 구분 | 스킬 | 서브에이전트 |
|------|------|-------------|
| 단위 | 도구·기능 단위 (작음) | 역할·책임 단위 (큼) |
| 공유 | 여러 에이전트가 공유 가능 | 특정 워크플로우 전용 |
| 지침 크기 | SKILL.md (짧음) | AGENT.md (도메인 지식 포함) |
| 예시 | `caution-generator`, `price-compare` | `safety-reviewer`, `commerce-reviewer` |

서브에이전트 분리 이유:
- 건강 추천·안전 검토·쇼핑 검토의 관심사가 다르다.
- 정책·안전 지침은 필요한 시점에만 로드하는 것이 컨텍스트 효율상 유리하다.
- 가격 비교 검수는 별도 책임으로 분리하는 편이 유지보수에 유리하다.
