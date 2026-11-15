import os, json, re, datetime
import requests
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()
MODEL = "gemini/gemini-3.5-flash-lite"
BIFROST_URL = "http://localhost:8080/v1/chat/completions"
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def ask_ai(prompt):
    """Send a prompt to Gemini THROUGH Bifrost."""
    resp = requests.post(
        BIFROST_URL,
        headers={"x-bf-vk": os.getenv("BIFROST_VK")},
        json={"model": MODEL,
              "messages": [{"role": "user", "content": prompt}],
              "max_tokens": 2000},
        timeout=180,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def parse_json(text):
    text = re.sub(r"```(?:json)?", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        return json.loads(m.group(1)) if m else None


def extract_claims(answer):
    today = datetime.date.today()
    prompt = (
        "Today's date is " + today.isoformat() + ". Read this AI-generated answer and list up to "
        "5 factual claims that could become outdated over time (prices, software versions, "
        "laws, company leaders, product features). Ignore timeless facts.\n"
        "For each claim write a short web search query that includes the word latest or current "
        "and the year " + str(today.year) + ". If a company or product was renamed, use the "
        "new name in the query too.\n"
        "Return ONLY a JSON list like: "
        '[{"claim": "...", "search_query": "..."}]\n'
        "If there are none, return [].\n\nANSWER:\n" + answer
    )
    return parse_json(ask_ai(prompt)) or []


def search_web(query):
    """Live web search with Tavily."""
    r = tavily.search(query, max_results=5)
    return [{"title": x["title"], "url": x["url"], "content": x["content"][:600]}
            for x in r["results"]]


def judge_claim(claim, evidence):
    today = datetime.date.today().isoformat()
    prompt = (
        "Today's date is " + today + ". Check this claim using ONLY the web evidence below.\n"
        "CLAIM: " + claim + "\n\nEVIDENCE:\n" + json.dumps(evidence, indent=1) + "\n\n"
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
    return parse_json(ask_ai(prompt))


def check_answer(answer):
    results = []
    for c in extract_claims(answer):
        try:
            evidence = search_web(c["search_query"])
            verdict = judge_claim(c["claim"], evidence) or {}
        except Exception as e:
            verdict = {"score": 50, "verdict": "unclear", "reason": "Check failed: " + str(e),
                       "current_info": "", "source_url": ""}
        verdict["claim"] = c["claim"]
        results.append(verdict)
    return results


def answer_question(question):
    return ask_ai("Answer this question clearly in 4 to 6 sentences. Be specific with facts "
                  "such as prices, versions, names and dates.\n\nQUESTION: " + question)


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
        "AI ANSWER:\n" + answer + "\n\nFRESHNESS CHECK RESULTS:\n" + summary + "\n\n"
        "Choose ONE cause: unclear_question (question was vague or missing details), "
        "outdated_knowledge (the AI used old information), ai_mistake (the AI got it wrong "
        "or made something up), answer_looks_fine.\n"
        'Return ONLY JSON like: {"cause": "unclear_question", '
        '"explanation": "2 short sentences", "tip": "one short tip for asking better next time"}'
    )
    return parse_json(ask_ai(prompt)) or {}