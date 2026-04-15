"""
건강 코치 에이전트 — Flask 웹 서버
사용법: python app.py
"""
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

from flask import Flask, jsonify, render_template, request

PROJECT_ROOT = Path(__file__).parent
app = Flask(__name__)

# 동시 실행 방지 락
_pipeline_lock = threading.Lock()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def run_pipeline():
    if not _pipeline_lock.acquire(blocking=False):
        return jsonify({"error": "다른 추천이 진행 중입니다. 잠시 후 다시 시도해주세요."}), 429

    try:
        data = request.get_json(force=True) or {}
        # Support both array (health_goals) and legacy scalar (health_goal)
        health_goals_raw = data.get("health_goals") or []
        if not health_goals_raw:
            single = (data.get("health_goal") or "").strip()
            health_goals_raw = [single] if single else []
        health_goals = [g.strip() for g in health_goals_raw if g and g.strip()]
        health_goal  = health_goals[0] if health_goals else ""

        age_group  = (data.get("age_group") or "").strip()
        gender     = (data.get("gender")    or "").strip()
        allergies  = data.get("allergies")  or []
        conditions = data.get("conditions") or []
        medications= data.get("medications")or []
        extra_note = (data.get("extra_note") or "").strip()

        if not all([health_goal, age_group, gender]):
            return jsonify({"error": "모든 항목을 선택해주세요."}), 400

        env = {**os.environ, "PYTHONUTF8": "1"}

        # 리셋
        subprocess.run(
            [sys.executable, "run.py", "--reset"],
            capture_output=True, cwd=PROJECT_ROOT, env=env,
        )

        # 입력 파일 생성
        intake_dir = PROJECT_ROOT / "output" / "intake"
        intake_dir.mkdir(parents=True, exist_ok=True)
        with open(intake_dir / "raw_minimal_input.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "health_goal":  health_goal,
                    "health_goals": health_goals,
                    "age_group":    age_group,
                    "gender":       gender,
                    "allergies":    allergies,
                    "conditions":   conditions,
                    "medications":  medications,
                    "extra_note":   extra_note,
                },
                f, ensure_ascii=False,
            )

        # 파이프라인 실행
        result = subprocess.run(
            [sys.executable, "run.py", "--skip-shopping"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            cwd=PROJECT_ROOT, env=env,
        )

        if result.returncode != 0:
            # stdout/stderr 모두에서 에러 메시지 추출
            combined = result.stdout + result.stderr
            # normalize.py가 stdout에 JSON 에러를 출력하는 경우 파싱
            for line in result.stdout.splitlines():
                try:
                    obj = json.loads(line)
                    if obj.get("error") == "INPUT_VALIDATION_FAILED":
                        details = obj.get("details", [])
                        return jsonify({"error": "입력값이 올바르지 않습니다: " + ", ".join(details)}), 400
                except (ValueError, AttributeError):
                    pass
            err_lines = [l.strip() for l in combined.splitlines()
                         if any(k in l for k in ("[ERROR]", "허용되지 않은", "필수 필드"))]
            err_msg = err_lines[0] if err_lines else "파이프라인 실행에 실패했습니다. 잠시 후 다시 시도해주세요."
            return jsonify({"error": err_msg}), 400

        # 결과 읽기
        md_path   = PROJECT_ROOT / "output" / "final" / "user_result.md"
        json_path = PROJECT_ROOT / "output" / "final" / "user_result.json"

        if not json_path.exists():
            return jsonify({"error": "결과 파일을 생성하지 못했습니다. 입력값을 확인해주세요."}), 500

        markdown = ""
        if md_path.exists():
            with open(md_path, encoding="utf-8") as f:
                markdown = f.read()

        meta = {}
        with open(json_path, encoding="utf-8") as f:
            meta = json.load(f)

        return jsonify({"success": True, "markdown": markdown, "meta": meta})

    finally:
        _pipeline_lock.release()


if __name__ == "__main__":
    print("건강 코치 에이전트 서버 시작: http://localhost:8080")
    app.run(debug=False, port=8080, threaded=True)
