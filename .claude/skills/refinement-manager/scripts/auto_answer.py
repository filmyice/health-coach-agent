"""
refinement-manager: 보정 질문 자동 응답 생성
Step 9 처리 (파이프라인 자동화용)
--mode auto   : 질문마다 "예"로 자동 응답 (기본)
--mode prompt : 터미널에서 사용자 입력 받기
"""
import argparse
import json
import os
import sys
os.environ.setdefault("PYTHONUTF8", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
from datetime import datetime, timezone

DECISION_PATH = Path("output/decision/refinement_needed.json")
OUTPUT_PATH   = Path("output/intake/refinement_answers.json")


def load_decision() -> dict:
    if not DECISION_PATH.exists():
        print(f"[ERROR] 보정 판단 파일 없음: {DECISION_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(DECISION_PATH, encoding="utf-8") as f:
        return json.load(f)


def auto_answer(questions: list, default: str = "예") -> list:
    return [
        {
            "question_id": q.get("id", ""),
            "question":    q.get("text", ""),
            "answer":      default,
        }
        for q in questions
    ]


def prompt_answer(questions: list) -> list:
    answers = []
    print("\n[보정 질문]")
    for q in questions:
        opts = " / ".join(q.get("options", ["예", "아니요"]))
        while True:
            ans = input(f"  {q.get('text', '')} ({opts}): ").strip()
            if ans in q.get("options", ["예", "아니요", "가끔"]):
                break
            print(f"  ⚠ 유효한 값: {opts}")
        answers.append({
            "question_id": q.get("id", ""),
            "question":    q.get("text", ""),
            "answer":      ans,
        })
    return answers


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["auto", "prompt"], default="auto",
                        help="auto: 모두 '예' / prompt: 터미널 입력")
    parser.add_argument("--default", default="예",
                        help="auto 모드에서 사용할 기본 응답 (예/아니요/가끔)")
    args = parser.parse_args()

    decision = load_decision()

    if not decision.get("refinement_needed", False):
        print("[INFO] 보정 질문 불필요. 건너뜀.")
        # 빈 answers 파일 생성 (후속 스텝이 missing 처리하지 않도록)
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump({"answers": [], "answered_at": datetime.now(timezone.utc).isoformat()}, f,
                      ensure_ascii=False, indent=2)
        sys.exit(0)

    questions = decision.get("questions", [])
    if not questions:
        print("[WARN] 보정 질문 목록이 비어 있습니다.", file=sys.stderr)
        sys.exit(0)

    if args.mode == "auto":
        answers = auto_answer(questions, default=args.default)
        for a in answers:
            print(f"[AUTO] {a['question']} → {a['answer']}")
    else:
        answers = prompt_answer(questions)

    result = {
        "answers": answers,
        "mode": args.mode,
        "answered_at": datetime.now(timezone.utc).isoformat(),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[OK] 보정 응답 저장 완료: {OUTPUT_PATH} ({len(answers)}개)")


if __name__ == "__main__":
    main()
