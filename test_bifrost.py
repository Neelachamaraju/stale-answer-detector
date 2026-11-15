import os
import requests
from dotenv import load_dotenv

load_dotenv()
resp = requests.post(
    "http://localhost:8080/v1/chat/completions",
    headers={"x-bf-vk": os.getenv("BIFROST_VK")},
    json={
        "model": "gemini/gemini-3.5-flash-lite",
        "messages": [{"role": "user", "content": "Say hello in one short sentence."}],
        "max_tokens": 200,
    },
    timeout=180,
)
print(resp.status_code)
print(resp.json())