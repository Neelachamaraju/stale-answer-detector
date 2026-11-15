# 🔍 Stale Answer Detector

**Catch outdated facts in AI-generated answers.**

AI tools can sound confident even when they provide outdated information. Stale Answer Detector helps identify potentially outdated facts by checking individual claims against live web sources.

It shows what's current, what's outdated, and what the correct information should be.

**Team:** Duck Can Do Anything

## 🚀 Features

### 1. Check Freshness
Paste any AI-generated answer and click **Check Now**. The application checks whether the facts are still accurate.

### 2. Claim-by-Claim Analysis
The application splits an answer into individual claims and checks each one separately.

Each claim receives one of three labels:
- 🟢 Fresh
- 🔴 Outdated
- 🟡 Unclear

### 3. Summary Cards
View a quick summary showing:
- Total claims checked
- Potentially outdated claims
- Overall verdict (Fresh, Mixed, or Outdated)

### 4. Source Links
Every analyzed claim includes source links so users can verify the supporting evidence.

### 5. Corrected Answers
For outdated or incorrect claims, the application provides updated information based on the available evidence.

### 6. Why Did the AI Go Wrong?
Enter your original question and expected answer. The application analyzes the likely reason behind the incorrect response.

### 7. Ask and Audit
Ask a question directly in the application. It generates an AI answer and checks that answer for potentially outdated information.

### 8. Download My Report
Download the analysis results for future reference or sharing.

### 9. Check Another
Clear previous results and analyze another AI-generated answer.

## 💡 Example

| AI-generated claim | Verification result |
|---|---|
| An outdated software version is the latest release | Shows the currently verified release |
| An old exchange rate is today's rate | Shows the latest available exchange rate |

*Examples are illustrative. Actual results depend on live search evidence.*

## ⚙️ How It Works

1. The user pastes an AI-generated answer or asks a question.
2. The application divides the answer into individual claims.
3. Tavily searches the live web for relevant evidence.
4. Bifrost analyzes the evidence and determines the freshness of each claim.
5. The application displays verdicts, source links and corrected information.

## 🛠️ Tech Stack

- **Python** – Core programming language
- **Streamlit** – Web application interface
- **Tavily API** – Live web search and evidence collection
- **Bifrost API** – AI-powered evidence analysis

## 🔑 API Keys Required

This application uses two external services:

**1. Tavily API Key**
- Enables live internet searches.
- Helps verify claims using current web information.

**2. Bifrost API Key**
- Enables AI-powered evidence analysis.
- Helps classify claims as Fresh, Outdated or Unclear.

API keys are private credentials and should never be uploaded to GitHub.

Users must provide their own API keys to run the application.

## 💻 How to Run Locally

### Step 1: Clone the repository

```
https://github.com/Neelachamaraju/stale-answer-detector/
```

### Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Configure API keys

Create a `.env` file in the project folder and add:

```env
TAVILY_API_KEY=your_key_here
BIFROST_API_KEY=your_key_here
```

Replace the example values with your actual API keys.

### Step 4: Run the application

```bash
streamlit run app.py
```

### Step 5: Open the application

Visit:

```text
http://localhost:8501
```

## 📁 Project Structure

```text
stale-answer-detector/
│
├── app.py
├── core.py
├── requirements.txt
├── .gitignore
└── README.md
```

## 🎥 Demo

**Demo Video:** Coming soon

## 👥 Team

**Duck Can Do Anything**

---

*Built to make AI-generated information more reliable, transparent and up to date.*
