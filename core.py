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
    today = datetime.date.today().isoformat()
    prompt = (
        "Today's date is " + today + ". Read this AI-generated answer and list up to 5 "
        "factual claims that could become outdated over time (prices, software versions, "
        "laws, company leaders, product features). Ignore timeless facts.\n"
        "Return ONLY a JSON list like: "
        '[{"claim": "...", "search_query": "short web search query to verify it"}]\n'
        "If there are none, return [].\n\nANSWER:\n" + answer
    )
    return parse_json(ask_ai(prompt)) or []


def search_web(query):
    """Live web search with Tavily."""
    r = tavily.search(query, max_results=3)
    return [{"title": x["title"], "url": x["url"], "content": x["content"][:500]}
            for x in r["results"]]


def judge_claim(claim, evidence):
    today = datetime.date.today().isoformat()
    prompt = (
        "Today's date is " + today + ". Check this claim using ONLY the web evidence below.\n"
        "CLAIM: " + claim + "\n\nEVIDENCE:\n" + json.dumps(evidence, indent=1) + "\n\n"
        "Return ONLY JSON like: "
        '{"score": 0-100, "verdict": "up_to_date" or "outdated" or "unclear", '
        '"reason": "one short sentence", "current_info": "what is true now, short", '
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


if __name__ == "__main__":
    sample = "The CEO of Twitter is Parag Agrawal. Python 3.9 is the latest version of Python."
    for r in check_answer(sample):
        print(json.dumps(r, indent=2))