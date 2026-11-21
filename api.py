from flask import Flask, request, jsonify
from core import check_answer, was_backup_used

app = Flask(__name__)


def _score_to_status(score):
    try:
        s = int(float(score))
    except Exception:
        s = 50
    if s >= 70:
        return "fresh"
    if s >= 40:
        return "unclear"
    return "outdated"


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "stale-answer-detector-api"})


@app.post("/verify")
def verify():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text") or data.get("answer") or "").strip()
    if not text:
        return jsonify({"error": "Missing required JSON field: 'text'"}), 400

    try:
        results = check_answer(text)
    except Exception as ex:
        return jsonify({"error": f"Verification failed: {ex}"}), 502

    statuses = [_score_to_status(r.get("score")) for r in results]
    outdated_count = statuses.count("outdated")
    unclear_count = statuses.count("unclear")
    fresh_count = statuses.count("fresh")

    if not results:
        overall = "no_time_sensitive_claims"
    elif outdated_count == 0 and unclear_count == 0:
        overall = "up_to_date"
    elif outdated_count == len(results):
        overall = "outdated"
    else:
        overall = "mixed"

    formatted_claims = [
        {
            "claim": r.get("claim", ""),
            "status": st_label,
            "score": r.get("score", 50),
            "reason": r.get("reason", ""),
            "current_info": r.get("current_info", ""),
            "source_url": r.get("source_url", ""),
        }
        for r, st_label in zip(results, statuses)
    ]

    return jsonify({
        "verdict": overall,
        "backup_model_used": was_backup_used(),
        "summary": {
            "total_claims": len(results),
            "fresh": fresh_count,
            "outdated": outdated_count,
            "unclear": unclear_count,
        },
        "claims": formatted_claims,
    })


if __name__ == "__main__":
    print("Stale-Answer Detector API running on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)