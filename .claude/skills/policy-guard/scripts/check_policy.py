"""
policy-guard: 금지 표현 검출 및 정책 준수 검증
Step 13, 20 처리
"""
import json
import os
import re
import sys
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
from datetime import datetime, timezone

SKILL_DIR = Path(__file__).parent.parent
FORBIDDEN_PATH = SKILL_DIR / "references" / "forbidden_expressions.json"
OUTPUT_PATH = Path("output/qa/final_validation_report.json")


def load_forbidden() -> dict:
    if not FORBIDDEN_PATH.exists():
        print(f"[WARN] 금지 표현 파일 없음: {FORBIDDEN_PATH}", file=sys.stderr)
        return {}
    with open(FORBIDDEN_PATH, encoding="utf-8") as f:
        return json.load(f)


def check_text(text: str, forbidden: dict) -> tuple[list, list]:
    """텍스트에서 금지 표현 검출. (violations, warnings) 반환."""
    violations = []
    warnings = []

    for category, expressions in forbidden.items():
        for expr in expressions.get("strict", []):
            if re.search(expr, text):
                violations.append({
                    "category": category,
                    "expression": expr,
                    "severity": "violation",
                })
        for expr in expressions.get("warn", []):
            if re.search(expr, text):
                warnings.append({
                    "category": category,
                    "expression": expr,
                    "severity": "warning",
                })

    return violations, warnings


def check_required_disclaimers(text: str) -> list[str]:
    """필수 면책 문구 누락 확인."""
    missing = []
    required = [
        "의료적 진단이 아닙니다",
        "전문가 상담",
    ]
    for phrase in required:
        if phrase not in text:
            missing.append(phrase)
    return missing


def main():
    target_path = sys.argv[1] if len(sys.argv) > 1 else "output/content/final_health_summary.md"
    target = Path(target_path)

    if not target.exists():
        print(f"[ERROR] 검사 대상 파일 없음: {target}", file=sys.stderr)
        sys.exit(1)

    with open(target, encoding="utf-8") as f:
        text = f.read()

    forbidden = load_forbidden()
    violations, warnings = check_text(text, forbidden)
    missing_disclaimers = check_required_disclaimers(text)

    if missing_disclaimers:
        for d in missing_disclaimers:
            violations.append({
                "category": "required_disclaimer",
                "expression": d,
                "severity": "violation",
            })

    passed = len(violations) == 0

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "passed": passed,
        "violations": violations,
        "warnings": warnings,
        "checked_file": str(target),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    status = "[OK]" if passed else "[FAIL]"
    print(f"{status} 정책 검사 완료: violations={len(violations)}, warnings={len(warnings)}")

    if not passed:
        sys.exit(3)


if __name__ == "__main__":
    main()
