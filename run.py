"""
건강 코치 에이전트 시스템 — 메인 파이프라인 오케스트레이터
사용법:
  python run.py                          # 전체 실행 (에이전트 스텝은 안내 출력)
  python run.py --step 1                 # 특정 스텝만 실행
  python run.py --step 1 --step 4        # 복수 스텝 실행
  python run.py --list                   # 스텝 목록 조회
  python run.py --from 4                 # N번 스텝부터 끝까지 실행
  python run.py --input path/to/raw.json # 입력 파일 지정
  python run.py --skip-shopping          # 쇼핑 크롤링 건너뜀
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Windows 콘솔 UTF-8 강제 설정
os.environ["PYTHONUTF8"] = "1"
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

PROJECT_ROOT = Path(__file__).parent
SKILLS = PROJECT_ROOT / ".claude" / "skills"

# ─────────────────────────────────────────────
# 스텝 정의
# type: "script" | "agent" | "agent+script"
# ─────────────────────────────────────────────
STEPS = [
    {
        "id": 1,
        "name": "입력 수집 및 스키마 검증",
        "type": "script",
        "script": SKILLS / "intake-normalizer/scripts/normalize.py",
        "output": "output/intake/raw_minimal_input.json",
    },
    {
        "id": 2,
        "name": "입력 정규화",
        "type": "script",
        "script": SKILLS / "intake-normalizer/scripts/normalize.py",
        "output": "output/intake/normalized_profile.json",
        "skip_if_done_by": 1,  # Step 1과 동일 스크립트
    },
    {
        "id": 3,
        "name": "1차 건강 목표 해석",
        "type": "script",
        "script": SKILLS / "goal-interpreter/scripts/interpret_goal.py",
        "output": "output/intent/primary_health_goal.json",
    },
    {
        "id": 4,
        "name": "1차 음식 추천 생성",
        "type": "script",
        "script": SKILLS / "food-recommender/scripts/recommend_food.py",
        "output": "output/recommendation/food_candidates.json",
    },
    {
        "id": 5,
        "name": "1차 운동/생활습관 추천 생성",
        "type": "script",
        "script": SKILLS / "habit-recommender/scripts/recommend_habit.py",
        "output": "output/recommendation/habit_candidates.json",
    },
    {
        "id": 6,
        "name": "1차 영양 성분 추천 생성",
        "type": "script",
        "script": SKILLS / "nutrient-recommender/scripts/recommend_nutrient.py",
        "output": "output/recommendation/nutrient_candidates.json",
    },
    {
        "id": 7,
        "name": "성분별 주의사항 초안 생성",
        "type": "script",
        "script": SKILLS / "caution-generator/scripts/generate_cautions.py",
        "output": "output/recommendation/nutrient_cautions.json",
    },
    {
        "id": 8,
        "name": "추가 보정 질문 여부 판단",
        "type": "script",
        "script": SKILLS / "refinement-manager/scripts/manage_refinement.py",
        "script_args": ["decide"],
        "output": "output/decision/refinement_needed.json",
    },
    {
        "id": 9,
        "name": "동적 보정 질문 수행 (조건부)",
        "type": "script",
        "script": SKILLS / "refinement-manager/scripts/auto_answer.py",
        "script_args": ["--mode", "auto", "--default", "예"],
        "output": "output/intake/refinement_answers.json",
    },
    {
        "id": 10,
        "name": "추천 결과 및 주의사항 보정",
        "type": "script",
        "script": SKILLS / "refinement-manager/scripts/manage_refinement.py",
        "script_args": ["refine"],
        "output": "output/recommendation/refined_recommendations.json",
    },
    {
        "id": 11,
        "name": "위험 플래그 확인",
        "type": "script",
        "script": SKILLS / "risk-flagger/scripts/flag_risks.py",
        "output": "output/risk/risk_flags.json",
    },
    {
        "id": 12,
        "name": "최종 통합 추천 생성",
        "type": "script",
        "script": SKILLS / "result-packager/scripts/assemble_health_plan.py",
        "output": "output/recommendation/final_health_plan.json",
    },
    {
        "id": 13,
        "name": "최종 설명 생성",
        "type": "script",
        "script": SKILLS / "explanation-writer/scripts/write_summary.py",
        "output": "output/content/final_health_summary.md",
    },
    {
        "id": 14,
        "name": "쇼핑 검색 질의 생성",
        "type": "script",
        "script": SKILLS / "shopping-search/scripts/generate_queries.py",
        "output": "output/shopping/search_queries.json",
        "shopping_step": True,
    },
    {
        "id": 15,
        "name": "Playwright 크롤링 수행",
        "type": "script",
        "scripts": [
            SKILLS / "shopping-search/scripts/crawl_coupang.py",
            SKILLS / "shopping-search/scripts/crawl_naver.py",
            SKILLS / "shopping-search/scripts/crawl_iherb.py",
            SKILLS / "shopping-search/scripts/crawl_oliveyoung.py",
        ],
        "output": "output/shopping/raw_product_results.json",
        "shopping_step": True,
        "require_playwright": True,
    },
    {
        "id": 16,
        "name": "상품 정보 정규화",
        "type": "script",
        "script": SKILLS / "shopping-search/scripts/normalize_products.py",
        "output": "output/shopping/normalized_products.json",
        "shopping_step": True,
    },
    {
        "id": 17,
        "name": "가격 비교 및 판매처 선정",
        "type": "script",
        "script": SKILLS / "price-compare/scripts/compare_prices.py",
        "output": "output/shopping/price_comparison.json",
        "shopping_step": True,
    },
    {
        "id": 18,
        "name": "쇼핑 설명 생성",
        "type": "script",
        "script": SKILLS / "shopping-search/scripts/write_shopping_summary.py",
        "output": "output/shopping/shopping_summary.md",
        "shopping_step": True,
    },
    {
        "id": 19,
        "name": "최종 결과 병합",
        "type": "script",
        "script": SKILLS / "result-packager/scripts/package_result.py",
        "output": "output/final/user_result.json",
    },
    {
        "id": 20,
        "name": "품질 검증",
        "type": "script",
        "script": SKILLS / "policy-guard/scripts/check_policy.py",
        "script_args": ["output/content/final_health_summary.md"],
        "output": "output/qa/final_validation_report.json",
    },
    {
        "id": 21,
        "name": "사용자 출력 생성",
        "type": "script",
        "script": SKILLS / "result-packager/scripts/package_result.py",
        "output": "output/final/user_result.md",
        "skip_if_done_by": 19,
    },
]

# ──────────────────────────────
# 색상 출력
# ──────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"{GREEN}  ✔ {msg}{RESET}")
def warn(msg):  print(f"{YELLOW}  ⚠ {msg}{RESET}")
def err(msg):   print(f"{RED}  ✘ {msg}{RESET}")
def info(msg):  print(f"{CYAN}  → {msg}{RESET}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")


def _merge_raw_crawl_results():
    """플랫폼별 raw_*_results.json → raw_product_results.json 병합."""
    import json as _json
    shopping_dir = PROJECT_ROOT / "output" / "shopping"
    merged = []
    for f in sorted(shopping_dir.glob("raw_*_results.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                data = _json.load(fh)
            merged.extend(data.get("products", []))
        except Exception:
            pass
    out = shopping_dir / "raw_product_results.json"
    with open(out, "w", encoding="utf-8") as fh:
        _json.dump({"products": merged, "total": len(merged)}, fh, ensure_ascii=False, indent=2)
    info(f"raw_product_results.json 병합 완료 ({len(merged)}개 상품)")


def run_script(script_path: Path, args: list[str] = None) -> bool:
    cmd = [sys.executable, str(script_path)] + (args or [])
    env = {**os.environ, "PYTHONUTF8": "1"}
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        cwd=PROJECT_ROOT,
    )
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            print(f"     {line}")
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines():
            warn(line)
    return result.returncode == 0


def check_playwright() -> bool:
    result = subprocess.run(
        [sys.executable, "-c", "import playwright; print('ok')"],
        capture_output=True, text=True
    )
    return result.returncode == 0


def output_exists(path_str: str) -> bool:
    return (PROJECT_ROOT / path_str).exists()


def is_conditional_skipped(step: dict) -> bool:
    cond_file = step.get("conditional")
    cond_key  = step.get("conditional_key")
    if not cond_file or not cond_key:
        return False
    cond_path = PROJECT_ROOT / cond_file
    if not cond_path.exists():
        return True
    with open(cond_path, encoding="utf-8") as f:
        data = json.load(f)
    return not data.get(cond_key, False)


def list_steps():
    header("스텝 목록")
    type_label = {"script": f"{GREEN}SCRIPT{RESET}", "agent": f"{YELLOW}AGENT {RESET}", "agent+script": f"{CYAN}A+SCR {RESET}"}
    for s in STEPS:
        label = type_label.get(s["type"], s["type"])
        shopping = " 🛒" if s.get("shopping_step") else ""
        print(f"  Step {s['id']:2d}  [{label}]  {s['name']}{shopping}")


def run_step(step: dict, skip_shopping: bool = False) -> str:
    """
    실행 결과: 'ok' | 'skip' | 'agent_required' | 'error'
    """
    step_id   = step["id"]
    step_name = step["name"]
    step_type = step["type"]

    header(f"Step {step_id:2d}  {step_name}  [{step_type.upper()}]")

    # 쇼핑 스텝 건너뜀
    if skip_shopping and step.get("shopping_step"):
        warn("--skip-shopping 옵션으로 건너뜀")
        return "skip"

    # Playwright 미설치 시 자동 건너뜀
    if step.get("require_playwright") and not check_playwright():
        warn("Playwright 미설치. 쇼핑 크롤링 건너뜀 (pip install playwright && playwright install)")
        return "skip"

    # 조건부 스텝 (ex: Step 9 보정 질문)
    if is_conditional_skipped(step):
        info("조건 불충족. 건너뜀.")
        return "skip"

    # Step 1/2 처럼 동일 스크립트로 처리되는 중복 스텝
    if step.get("skip_if_done_by"):
        info(f"Step {step['skip_if_done_by']} 에서 함께 처리됨. 건너뜀.")
        return "skip"

    # ── SCRIPT 타입 ──────────────────────────────
    if step_type == "script":
        # 복수 스크립트 (Step 15 크롤러)
        if "scripts" in step:
            all_ok = True
            for sc in step["scripts"]:
                info(f"실행: {sc.name}")
                if not run_script(sc):
                    warn(f"{sc.name} 실패 (격리 처리, 계속 진행)")
                    all_ok = False
            # 플랫폼별 raw 파일 → raw_product_results.json 병합
            _merge_raw_crawl_results()
            ok(f"완료 → {step.get('output', '')}")
            return "ok" if all_ok else "ok"  # 크롤링 실패는 격리
        else:
            info(f"실행: {step['script'].name}")
            success = run_script(step["script"], step.get("script_args"))
            if success:
                ok(f"완료 → {step.get('output', '')}")
                return "ok"
            else:
                err(f"스크립트 실패")
                return "error"

    # ── AGENT 타입 ───────────────────────────────
    if step_type == "agent":
        out = step.get("output", "")
        if output_exists(out):
            ok(f"출력 파일 이미 존재: {out}")
            return "ok"
        print(f"\n  {YELLOW}[AGENT 판단 필요]{RESET}")
        print(f"  {step['agent_instruction']}")
        print(f"  출력 파일: {BOLD}{out}{RESET}")
        return "agent_required"

    # ── AGENT+SCRIPT 타입 ────────────────────────
    if step_type == "agent+script":
        out = step.get("output", "")
        if output_exists(out):
            ok(f"출력 파일 이미 존재: {out}")
            return "ok"
        print(f"\n  {YELLOW}[AGENT+SCRIPT]{RESET}")
        print(f"  {step['agent_instruction']}")
        if "script" in step:
            info(f"스크립트: {step['script'].name}")
            success = run_script(step["script"])
            if success:
                ok(f"스크립트 완료 → {out}")
                return "ok"
            else:
                err("스크립트 실패")
                return "error"
        return "agent_required"

    return "skip"


def main():
    parser = argparse.ArgumentParser(description="건강 코치 에이전트 파이프라인 러너")
    parser.add_argument("--step",          type=int, action="append", help="실행할 스텝 번호 (복수 지정 가능)")
    parser.add_argument("--from",          type=int, dest="from_step", help="이 스텝부터 끝까지 실행")
    parser.add_argument("--list",          action="store_true", help="스텝 목록 출력")
    parser.add_argument("--skip-shopping", action="store_true", help="쇼핑 크롤링 스텝 건너뜀")
    parser.add_argument("--input",         type=str, help="입력 JSON 파일 경로")
    parser.add_argument("--reset",         action="store_true", help="output/ 하위 파일 전체 삭제 후 초기화")
    args = parser.parse_args()

    if args.list:
        list_steps()
        return

    # 리셋 처리
    if args.reset:
        output_dir = PROJECT_ROOT / "output"
        deleted = 0
        for f in output_dir.rglob("*"):
            if f.is_file() and f.name != ".gitkeep":
                f.unlink()
                deleted += 1
        ok(f"output/ 초기화 완료 ({deleted}개 파일 삭제)")
        if not args.step and not args.from_step:
            return  # --reset 단독 실행이면 종료

    # 입력 파일 처리
    if args.input:
        src = Path(args.input)
        dst = PROJECT_ROOT / "output/intake/raw_minimal_input.json"
        dst.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy(src, dst)
        ok(f"입력 파일 복사: {src} → {dst}")

    # 실행할 스텝 선택
    if args.step:
        target_steps = [s for s in STEPS if s["id"] in args.step]
    elif args.from_step:
        target_steps = [s for s in STEPS if s["id"] >= args.from_step]
    else:
        target_steps = STEPS

    print(f"\n{BOLD}{'='*50}")
    print("건강 코치 에이전트 파이프라인 시작")
    print(f"{'='*50}{RESET}")

    results = {}
    agent_required_steps = []
    pending_agent_outputs: set[str] = set()  # 에이전트가 아직 생성하지 않은 출력 파일

    for step in target_steps:
        # 이 스텝의 입력이 아직 에이전트 대기 중인 파일이면 → 스킵 (오류 아님)
        step_output = step.get("output", "")
        prereq_missing = False
        for pending in pending_agent_outputs:
            # 이전 에이전트 스텝의 출력이 현재 스텝의 전제 조건일 가능성 확인
            if not output_exists(pending):
                prereq_missing = True
                break

        if prereq_missing and step["type"] == "script":
            warn(f"Step {step['id']} {step['name']} — 에이전트 출력 대기 중, 건너뜀")
            results[step["id"]] = "skip"
            continue

        result = run_step(step, skip_shopping=args.skip_shopping)
        results[step["id"]] = result

        if result == "agent_required":
            agent_required_steps.append(step)
            if step_output:
                pending_agent_outputs.add(step_output)
        elif result == "ok":
            # 에이전트 출력 대기 목록에서 제거
            pending_agent_outputs.discard(step_output)
        elif result == "error":
            err(f"Step {step['id']} 실패. 파이프라인 중단.")
            break

    # 최종 요약
    header("실행 요약")
    for step in target_steps:
        r = results.get(step["id"], "not_run")
        icon = {"ok": "✔", "skip": "–", "agent_required": "✎", "error": "✘", "not_run": "·"}.get(r, "?")
        color = {"ok": GREEN, "skip": RESET, "agent_required": YELLOW, "error": RED, "not_run": RESET}.get(r, RESET)
        print(f"  {color}{icon} Step {step['id']:2d}  {step['name']}{RESET}")

    if agent_required_steps:
        print(f"\n{YELLOW}에이전트 판단이 필요한 스텝:{RESET}")
        for s in agent_required_steps:
            print(f"  → Step {s['id']}: {s['name']}")
        print(f"\n{CYAN}Claude Code 실행 방법: 위 스텝들에 대한 판단을 수행한 뒤 다시 실행하세요.{RESET}")

    final = PROJECT_ROOT / "output/final/user_result.json"
    if final.exists():
        print(f"\n{GREEN}{BOLD}최종 결과 파일: {final}{RESET}")


if __name__ == "__main__":
    main()
