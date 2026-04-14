"""
전체 건강 목표 자동 테스트
사용법:
  python test_all_goals.py              # 7개 목표 전체 테스트
  python test_all_goals.py --goal 수면  # 특정 목표만
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

os.environ["PYTHONUTF8"] = "1"
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

PROJECT_ROOT = Path(__file__).parent
OUTPUT_DIR   = PROJECT_ROOT / "output"

GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# 테스트 케이스 정의
TEST_CASES = [
    {"health_goal": "피로 관리",    "age_group": "30대",    "gender": "여성"},
    {"health_goal": "수면 관리",    "age_group": "40대",    "gender": "남성"},
    {"health_goal": "면역 관리",    "age_group": "20대",    "gender": "여성"},
    {"health_goal": "눈 건강",      "age_group": "50대 이상","gender": "남성"},
    {"health_goal": "장 건강",      "age_group": "30대",    "gender": "남성"},
    {"health_goal": "뼈 건강",      "age_group": "50대 이상","gender": "여성"},
    {"health_goal": "피부·항산화",  "age_group": "20대",    "gender": "여성"},
]

# 각 테스트 후 확인할 필수 출력 파일
REQUIRED_OUTPUTS = [
    "output/intake/normalized_profile.json",
    "output/intent/primary_health_goal.json",
    "output/recommendation/food_candidates.json",
    "output/recommendation/habit_candidates.json",
    "output/recommendation/nutrient_candidates.json",
    "output/recommendation/nutrient_cautions.json",
    "output/decision/refinement_needed.json",
    "output/intake/refinement_answers.json",
    "output/recommendation/refined_recommendations.json",
    "output/risk/risk_flags.json",
    "output/recommendation/final_health_plan.json",
    "output/content/final_health_summary.md",
    "output/final/user_result.json",
    "output/final/user_result.md",
    "output/qa/final_validation_report.json",
]

# 검증 규칙
def validate_outputs(tc: dict) -> list[str]:
    errors = []

    # 1. 필수 파일 존재 여부
    for rel in REQUIRED_OUTPUTS:
        if not (PROJECT_ROOT / rel).exists():
            errors.append(f"파일 없음: {rel}")

    # 2. normalized_profile 검증
    np_path = PROJECT_ROOT / "output/intake/normalized_profile.json"
    if np_path.exists():
        with open(np_path, encoding="utf-8") as f:
            np = json.load(f)
        if not np.get("health_goal"):
            errors.append("normalized_profile: health_goal 누락")

    # 3. final_health_plan 검증 — 음식/습관/영양 각 1개 이상
    plan_path = PROJECT_ROOT / "output/recommendation/final_health_plan.json"
    if plan_path.exists():
        with open(plan_path, encoding="utf-8") as f:
            plan = json.load(f)
        if not plan.get("foods"):
            errors.append("final_health_plan: foods 비어 있음")
        if not plan.get("habits"):
            errors.append("final_health_plan: habits 비어 있음")
        if not plan.get("nutrients"):
            errors.append("final_health_plan: nutrients 비어 있음")
        for n in plan.get("nutrients", []):
            if not n.get("caution"):
                errors.append(f"final_health_plan: {n.get('name')} caution 누락")

    # 4. final_health_summary 금지 표현 검사
    summary_path = PROJECT_ROOT / "output/content/final_health_summary.md"
    if summary_path.exists():
        with open(summary_path, encoding="utf-8") as f:
            text = f.read()
        forbidden = ["치료된다", "완치", "의학적으로 입증", "처방", "확실히 효과"]
        for word in forbidden:
            if word in text:
                errors.append(f"final_health_summary: 금지 표현 발견 '{word}'")
        if "의료적 진단이 아닙니다" not in text:
            errors.append("final_health_summary: 면책 문구 누락")

    # 5. policy guard 통과 여부
    qa_path = PROJECT_ROOT / "output/qa/final_validation_report.json"
    if qa_path.exists():
        with open(qa_path, encoding="utf-8") as f:
            qa = json.load(f)
        v = qa.get("violations", 0)
        v_count = len(v) if isinstance(v, list) else int(v or 0)
        if v_count > 0:
            errors.append(f"policy_guard: violations={v}")

    return errors


def run_pipeline(tc: dict) -> tuple[bool, float, list[str]]:
    """파이프라인 실행 후 (성공여부, 소요시간, 오류목록) 반환."""
    # 리셋
    subprocess.run(
        [sys.executable, "run.py", "--reset"],
        capture_output=True, cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONUTF8": "1"}
    )
    # 입력 파일 생성
    intake_dir = PROJECT_ROOT / "output" / "intake"
    intake_dir.mkdir(parents=True, exist_ok=True)
    with open(intake_dir / "raw_minimal_input.json", "w", encoding="utf-8") as f:
        json.dump(tc, f, ensure_ascii=False)

    start = time.time()
    result = subprocess.run(
        [sys.executable, "run.py", "--skip-shopping"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=PROJECT_ROOT,
        env={**os.environ, "PYTHONUTF8": "1"}
    )
    elapsed = time.time() - start

    if result.returncode != 0:
        return False, elapsed, [f"파이프라인 종료코드 {result.returncode}"]

    # 출력에서 에러 라인 추출
    run_errors = [
        line.strip() for line in result.stdout.splitlines()
        if "✘" in line or "[ERROR]" in line
    ]

    errors = validate_outputs(tc)
    errors.extend(run_errors)
    return len(errors) == 0, elapsed, errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--goal", help="특정 건강 목표만 테스트 (부분 일치)")
    args = parser.parse_args()

    cases = TEST_CASES
    if args.goal:
        cases = [tc for tc in TEST_CASES if args.goal in tc["health_goal"]]
        if not cases:
            print(f"{RED}해당 목표 없음: {args.goal}{RESET}")
            sys.exit(1)

    print(f"\n{BOLD}{'='*55}")
    print(f"  건강 목표 전체 테스트  ({len(cases)}개 케이스)")
    print(f"{'='*55}{RESET}\n")

    results = []
    for i, tc in enumerate(cases, 1):
        label = f"{tc['health_goal']} / {tc['age_group']} {tc['gender']}"
        print(f"{CYAN}[{i}/{len(cases)}] {label}{RESET}")

        ok, elapsed, errors = run_pipeline(tc)
        results.append((tc, ok, elapsed, errors))

        if ok:
            print(f"  {GREEN}✔ PASS  ({elapsed:.1f}s){RESET}")
        else:
            print(f"  {RED}✘ FAIL  ({elapsed:.1f}s){RESET}")
            for e in errors:
                print(f"    {YELLOW}· {e}{RESET}")
        print()

    # 최종 요약
    passed = sum(1 for _, ok, _, _ in results if ok)
    failed = len(results) - passed
    total_time = sum(e for _, _, e, _ in results)

    print(f"{BOLD}{'='*55}")
    print(f"  결과: {GREEN}{passed}개 통과{RESET}{BOLD}  /  {RED if failed else ''}{failed}개 실패{RESET}{BOLD}  (총 {total_time:.1f}s)")
    print(f"{'='*55}{RESET}\n")

    if failed:
        print(f"{RED}실패한 케이스:{RESET}")
        for tc, ok, _, errors in results:
            if not ok:
                print(f"  · {tc['health_goal']}")
                for e in errors:
                    print(f"      {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
