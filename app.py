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

        age_group = (data.get("age_group") or "").strip()
        gender    = (data.get("gender")    or "").strip()

        if not all([health_goal, age_group, gender]):
            return jsonify({"error": "모든 항목을 선택해주세요."}), 400

        env = {**os.environ, "PYTHONUTF8": "1"}

        # 리셋
        subprocess.run(
            [sys.executable, "run.py", "--reset"],
            capture_output=True, cwd=PROJECT_ROOT, env=env,
        )

        # 입력 파일 생성 (primary goal만 파이프라인에 전달)
        intake_dir = PROJECT_ROOT / "output" / "intake"
        intake_dir.mkdir(parents=True, exist_ok=True)
        with open(intake_dir / "raw_minimal_input.json", "w", encoding="utf-8") as f:
            json.dump(
                {
                    "health_goal":  health_goal,
                    "health_goals": health_goals,
                    "age_group":    age_group,
                    "gender":       gender,
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
            return jsonify({"error": f"파이프라인 실행 실패\n{result.stderr[-500:]}"}), 500

        # 결과 읽기
        md_path   = PROJECT_ROOT / "output" / "final" / "user_result.md"
        json_path = PROJECT_ROOT / "output" / "final" / "user_result.json"

        markdown = ""
        if md_path.exists():
            with open(md_path, encoding="utf-8") as f:
                markdown = f.read()

        meta = {}
        if json_path.exists():
            with open(json_path, encoding="utf-8") as f:
                meta = json.load(f)

        return jsonify({"success": True, "markdown": markdown, "meta": meta})

    finally:
        _pipeline_lock.release()


if __name__ == "__main__":
    print("건강 코치 에이전트 서버 시작: http://localhost:5000")
    app.run(debug=False, port=5000, threaded=True)
