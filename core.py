import os, json, re, datetime
import requests
from dotenv import load_dotenv
from tavily import TavilyClient
from pypdf import PdfReader

load_dotenv()
PRIMARY_MODEL = "gemini/gemini-3.5-flash-lite"
BACKUP_MODEL = "gemini/gemini-3.1-flash-lite"
BIFROST_URL = "http://localhost:8080/v1/chat/completions"
BENCHMARK_FILE = "benchmark_results.json"
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

USED_BACKUP = False

BENCHMARK_QUESTIONS = [
    "Who is the current CEO of Twitter (X)?",
    "What is the latest stable version of Python?",
    "How much does a standard ChatGPT Plus subscription cost per month?",
    "Who is the current captain of the Indian men's national cricket team?",
    "What is the latest flagship iPhone model released by Apple?",
    "Who is the current Prime Minister of the United Kingdom?",
    "What is the latest major version of React?",
    "Who won the most recent ICC Men's T20 World Cup?",
]


def reset_backup_flag():
    global USED_BACKUP
    USED_BACKUP = False


def was_backup_used():
    return USED_BACKUP


def _call_bifrost(model_name, prompt):
    resp = requests.post(
        BIFROST_URL,
        headers={"x-bf-vk": os.getenv("BIFROST_VK")},
        json={
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2000,
        },
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def ask_ai(prompt, model=None):
    """Send a prompt to Gemini through Bifrost, with automatic backup fallback."""
    global USED_BACKUP
    if model:
        return _call_bifrost(model, prompt)
    try:
        return _call_bifrost(PRIMARY_MODEL, prompt)
    except Exception:
        USED_BACKUP = True
        return _call_bifrost(BACKUP_MODEL, prompt)


def parse_json(text):
    if not isinstance(text, str):
        return text
    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        m = re.search(r"(\[.*\]|\{.*\})", cleaned, re.DOTALL)
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except Exception:
            return None


def extract_claims(answer, max_claims=5):
    today = datetime.date.today()
    prompt = (
        "Today's date is " + today.isoformat() + ". Read this text and list up to "
        + str(max_claims) + " factual claims that could become outdated over time (prices, software versions, "
        "laws, company leaders, product features). Ignore timeless facts.\n"
        "For each claim write a short web search query that includes the word latest or current "
        "and the year " + str(today.year) + ". If a company or product was renamed, use the "
        "new name in the query too.\n"
        "Return ONLY a JSON list like: "
        '[{"claim": "...", "search_query": "..."}]\n'
        "If there are none, return [].\n\nTEXT:\n" + str(answer)
    )
    parsed = parse_json(ask_ai(prompt))
    if not isinstance(parsed, list):
        return []
    valid = [
        item for item in parsed
        if isinstance(item, dict) and item.get("claim") and item.get("search_query")
    ]
    return valid[:max_claims]


def search_web(query):
    """Live web search with Tavily."""
    r = tavily.search(str(query), max_results=5)
    return [{"title": x["title"], "url": x["url"], "content": x["content"][:600]}
            for x in r["results"]]


def judge_claim(claim, evidence):
    today = datetime.date.today().isoformat()
    prompt = (
        "Today's date is " + today + ". Check this claim using ONLY the web evidence below.\n"
        "CLAIM: " + str(claim) + "\n\nEVIDENCE:\n" + json.dumps(evidence, indent=1) + "\n\n"
        "Rules:\n"
        "- Web pages can be old. If the evidence mentions several versions, prices or people, "
        "use the MOST RECENT one.\n"
        "- If the evidence does not clearly show what is true today, set verdict to unclear, "
        "score to 50, and current_info to: Could not confirm the latest information. "
        "Check the source link.\n"
        "- current_info must be one full sentence stating the correct fact, with the year if "
        "the evidence shows one.\n"
        "Return ONLY JSON like: "
        '{"score": 0-100, "verdict": "up_to_date" or "outdated" or "unclear", '
        '"reason": "one short sentence", "current_info": "one full sentence", '
        '"source_url": "best url from the evidence"}\n'
        "Score: 90-100 evidence confirms the claim, 0-30 evidence contradicts it, "
        "40-60 not enough evidence."
    )
    parsed = parse_json(ask_ai(prompt))
    return parsed if isinstance(parsed, dict) else {}


def verify_claim_item(claim_obj):
    """Verify a single extracted claim dict on the live web."""
    try:
        evidence = search_web(claim_obj["search_query"])
        verdict = judge_claim(claim_obj["claim"], evidence) or {}
    except Exception as e:
        verdict = {
            "score": 50,
            "verdict": "unclear",
            "reason": "Check failed: " + str(e),
            "current_info": "",
            "source_url": "",
        }
    verdict["claim"] = claim_obj["claim"]
    return verdict


def check_answer(answer):
    reset_backup_flag()
    results = []
    for c in extract_claims(answer, max_claims=5):
        results.append(verify_claim_item(c))
    return results


def read_document_text(uploaded_file):
    """Extract plain text from an uploaded .txt or .pdf file."""
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(uploaded_file)
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    return uploaded_file.read().decode("utf-8", errors="replace").strip()


def extract_document_claims(text, max_total=12):
    """Split long document text into chunks and extract up to max_total time-sensitive claims."""
    reset_backup_flag()
    chunk_size = 3500
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)][:4]
    all_claims = []
    seen = set()
    per_chunk = max(3, max_total // max(1, len(chunks)))
    for chunk in chunks:
        if len(all_claims) >= max_total:
            break
        for c in extract_claims(chunk, max_claims=per_chunk):
            key = str(c.get("claim", "")).strip().lower()
            if key and key not in seen:
                seen.add(key)
                all_claims.append(c)
                if len(all_claims) >= max_total:
                    break
    return all_claims


def answer_question(question, model=None):
    if not model:
        reset_backup_flag()
    return ask_ai(
        "Answer this question clearly in 2 to 3 sentences. Be specific with facts "
        "such as prices, versions, names and dates.\n\nQUESTION: " + str(question),
        model=model,
    )


def explain_failure(question, expectation, answer, results):
    """Guess the most likely reason an answer went wrong."""
    summary = json.dumps(
        [{"claim": r.get("claim"), "verdict": r.get("verdict"), "reason": r.get("reason")}
         for r in results], indent=1)
    prompt = (
        "A user asked an AI a question and got an answer that may have problems. "
        "Decide the MOST LIKELY reason.\n"
        "USER QUESTION: " + (question or "(not given)") + "\n"
        "WHAT THE USER EXPECTED: " + (expectation or "(not given)") + "\n"
        "AI ANSWER:\n" + str(answer) + "\n\nFRESHNESS CHECK RESULTS:\n" + summary + "\n\n"
        "Choose ONE cause: unclear_question (question was vague or missing details), "
        "outdated_knowledge (the AI used old information), ai_mistake (the AI got it wrong "
        "or made something up), answer_looks_fine.\n"
        'Return ONLY JSON like: {"cause": "unclear_question", '
        '"explanation": "2 short sentences", "tip": "one short tip for asking better next time"}'
    )
    parsed = parse_json(ask_ai(prompt))
    return parsed if isinstance(parsed, dict) else {}


def generate_topic_brief(source_text, results):
    """Generate rich topic context, key takeaways, and next-step advice for the PDF report."""
    today = datetime.date.today().isoformat()
    findings = json.dumps(
        [{"claim": r.get("claim"), "verdict": r.get("verdict"), "current_info": r.get("current_info")}
         for r in results],
        indent=1,
    )
    prompt = (
        f"Today's date is {today}. You are writing the background & insights sections of an executive "
        "fact-check PDF report for a reader.\n"
        f"TEXT CHECKED:\n{str(source_text)[:1500]}\n\nVERIFICATION FINDINGS:\n{findings}\n\n"
        "Return ONLY valid JSON with these 4 fields:\n"
        '{"topic_title": "Short 4-7 word title describing the topic", '
        '"topic_overview": "3 to 4 clear sentences explaining the broader topic, background context, '
        'and why facts in this subject area change over time.", '
        '"key_insights": ["Insight 1 (1 sentence)", "Insight 2 (1 sentence)", "Insight 3 (1 sentence)"], '
        '"recommendations": ["Practical tip 1 for verifying or updating this info", '
        '"Practical tip 2 for avoiding stale data in the future"]}'
    )
    try:
        parsed = parse_json(ask_ai(prompt))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def load_benchmark():
    """Load saved model comparison benchmark from disk if available."""
    if not os.path.exists(BENCHMARK_FILE):
        return None
    try:
        with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def evaluate_single_benchmark_question(question, models=None):
    """Fetch live web evidence once per question, then audit each model's answer against it."""
    models = models or [PRIMARY_MODEL, BACKUP_MODEL]
    evidence = search_web(question + " " + str(datetime.date.today().year))
    row = {"question": question, "models": {}}
    for m in models:
        try:
            ans = answer_question(question, model=m)
            verdict = judge_claim(ans, evidence) or {}
            score = int(float(verdict.get("score", 50)))
            status = "Fresh" if score >= 70 else ("Unclear" if score >= 40 else "Outdated")
            row["models"][m] = {
                "answer": ans,
                "status": status,
                "score": score,
                "reason": verdict.get("reason", ""),
            }
        except Exception as ex:
            row["models"][m] = {
                "answer": f"Error: {ex}",
                "status": "Unclear",
                "score": 50,
                "reason": "Model call failed",
            }
    return row


def save_benchmark(rows, models=None):
    """Aggregate and persist benchmark results to benchmark_results.json."""
    models = models or [PRIMARY_MODEL, BACKUP_MODEL]
    summary = {}
    for m in models:
        statuses = [r["models"][m]["status"] for r in rows if m in r["models"]]
        total = max(1, len(statuses))
        fresh = statuses.count("Fresh")
        outdated = statuses.count("Outdated")
        unclear = statuses.count("Unclear")
        summary[m] = {
            "total": len(statuses),
            "fresh": fresh,
            "outdated": outdated,
            "unclear": unclear,
            "fresh_pct": round((fresh / total) * 100),
            "outdated_pct": round((outdated / total) * 100),
        }
    payload = {
        "run_date": datetime.date.today().isoformat(),
        "models": models,
        "summary": summary,
        "rows": rows,
    }
    with open(BENCHMARK_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload