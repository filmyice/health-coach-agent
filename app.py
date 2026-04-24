"""
건강 코치 에이전트 — Flask 웹 서버
사용법: python app.py
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, render_template, request

# .env 파일이 있으면 환경변수로 로드
def _load_dotenv():
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val

PROJECT_ROOT = Path(__file__).parent
_load_dotenv()
app = Flask(__name__)

# Vercel 환경에서는 /tmp 아래에 작업 디렉토리를 만들어 사용
_IS_VERCEL = os.environ.get("VERCEL") == "1"

# 동시 실행 방지 락
_pipeline_lock = threading.Lock()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/run", methods=["POST"])
def run_pipeline():
    if not _pipeline_lock.acquire(blocking=False):
        return jsonify({"error": "다른 추천이 진행 중입니다. 잠시 후 다시 시도해주세요."}), 429

    work_dir = None
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

        # Vercel: /tmp 아래에 요청별 임시 작업 디렉토리 생성
        if _IS_VERCEL:
            work_dir = Path("/tmp") / f"hca-{uuid.uuid4().hex}"
            work_dir.mkdir(parents=True, exist_ok=True)
        else:
            work_dir = PROJECT_ROOT

        env = {**os.environ, "PYTHONUTF8": "1", "HCA_WORKDIR": str(work_dir)}

        # 리셋 (로컬 모드에서만 의미 있음)
        if not _IS_VERCEL:
            subprocess.run(
                [sys.executable, str(PROJECT_ROOT / "run.py"), "--reset"],
                capture_output=True, cwd=PROJECT_ROOT, env=env,
            )

        # 입력 파일 생성
        intake_dir = work_dir / "output" / "intake"
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
            [sys.executable, str(PROJECT_ROOT / "run.py"), "--skip-shopping"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            cwd=PROJECT_ROOT, env=env,
        )

        if result.returncode != 0:
            combined = result.stdout + result.stderr
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
        md_path   = work_dir / "output" / "final" / "user_result.md"
        json_path = work_dir / "output" / "final" / "user_result.json"

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
        # Vercel 임시 디렉토리 정리
        if _IS_VERCEL and work_dir and work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)


@app.route("/vitamin-tracker")
def vitamin_tracker():
    return render_template("vitamin_tracker.html")


@app.route("/api/scan-vitamin", methods=["POST"])
def scan_vitamin():
    import urllib.request
    import urllib.error

    data = request.get_json(force=True) or {}
    image_b64 = data.get("image", "")
    if not image_b64:
        return jsonify({"error": "이미지가 없습니다."}), 400

    if not image_b64.startswith("data:"):
        image_b64 = "data:image/jpeg;base64," + image_b64

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        # 여러 경로에서 .env 탐색
        _candidates = [
            PROJECT_ROOT / ".env",
            Path(os.getcwd()) / ".env",
            Path(__file__).parent / ".env",
        ]
        for _env_file in _candidates:
            if _env_file.exists():
                for _line in _env_file.read_text(encoding="utf-8-sig").splitlines():
                    _line = _line.strip()
                    if _line.startswith("OPENAI_API_KEY="):
                        api_key = _line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            if api_key:
                break
    if not api_key:
        _dbg = f"PROJECT_ROOT={PROJECT_ROOT}, cwd={os.getcwd()}, .env exists={( PROJECT_ROOT / '.env').exists()}"
        return jsonify({"error": f"OPENAI_API_KEY가 설정되지 않았습니다. ({_dbg})"}), 500

    def call_openai(messages, max_tokens=600, model="gpt-4o"):
        payload = json.dumps({
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=payload,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
        return body["choices"][0]["message"]["content"].strip()

    def parse_json(text):
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1] if len(parts) > 1 else text
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())

    try:
        # ── Step 1: 이미지에서 성분표 직접 추출 시도 ──
        step1_prompt = (
            "이 비타민/영양제 사진을 분석해주세요.\n"
            "【작업 A】 Supplement Facts / 영양성분표가 보이면 모든 성분을 JSON 배열로 추출하세요.\n"
            "【작업 B】 성분표가 없고 제품 앞면만 보이면, 브랜드명과 제품명을 정확히 읽어서 "
            '{"product_name":"브랜드 제품명 전체"} 형식으로만 답하세요.\n'
            "두 경우 모두 JSON만 반환하고 다른 텍스트는 절대 쓰지 마세요.\n"
            "성분 배열 예시: "
            '[{"name":"비타민C","amount":1000,"unit":"mg"},{"name":"아연","amount":10,"unit":"mg"}]'
        )
        text1 = call_openai([{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": image_b64, "detail": "high"}},
                {"type": "text", "text": step1_prompt},
            ],
        }])

        result1 = parse_json(text1)

        # 성분 배열을 바로 받은 경우
        if isinstance(result1, list) and result1:
            return jsonify({"nutrients": result1, "source": "label"})

        # 제품명을 받은 경우 → Step 2: 웹 검색으로 성분 조회
        product_name = ""
        if isinstance(result1, dict):
            product_name = result1.get("product_name", "")

        if not product_name:
            return jsonify({"nutrients": [], "warning": "제품명을 인식하지 못했습니다. 라벨이 잘 보이도록 다시 촬영해주세요."})

        # ── Step 2: 제품명으로 성분 검색 (GPT 지식 + 웹 검색 활용) ──
        step2_prompt = (
            f'"{product_name}" 영양제의 Supplement Facts(영양성분표) 정보를 찾아주세요.\n'
            "제조사 공식 사이트나 iHerb, Examine.com 등의 정보를 기반으로 "
            "1회 제공량 기준 모든 비타민·미네랄 성분과 함량을 JSON 배열로만 반환하세요.\n"
            "형식: "
            '[{"name":"비타민A","amount":750,"unit":"mcg"},{"name":"비타민C","amount":200,"unit":"mg"},...]\n'
            "name은 반드시 한국어 성분명, amount는 숫자, unit은 mg/mcg/IU/g 중 하나.\n"
            "모든 성분을 빠짐없이 포함하고, JSON 외 다른 텍스트는 절대 쓰지 마세요."
        )
        text2 = call_openai(
            [{"role": "user", "content": step2_prompt}],
            max_tokens=1200,
        )
        nutrients = parse_json(text2)
        if not isinstance(nutrients, list):
            nutrients = []
        return jsonify({"nutrients": nutrients, "source": "search", "product_name": product_name})

    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return jsonify({"error": f"API 오류: {e.code}", "detail": err_body}), 502
    except (json.JSONDecodeError, KeyError):
        return jsonify({"nutrients": [], "warning": "성분 인식 실패 — 뒷면 라벨을 촬영하거나 다시 시도해주세요."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print("건강 코치 에이전트 서버 시작: http://localhost:8080")
    app.run(debug=False, port=8080, threaded=True)
