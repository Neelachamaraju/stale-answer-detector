## 🔍 Stale Answer Detector

Catch outdated facts in AI answers.

AI shouldn't just be smart. It should be current.

Stale Answer Detector is an AI-powered application that identifies outdated or potentially inaccurate information in AI-generated answers by checking individual claims against live web evidence.

Instead of blindly trusting AI-generated responses, users can verify facts, explore sources, view corrected answers, and understand why an AI answer may have gone wrong.

Team: Duck Can Do Anything

## 🚀 Problem Statement

AI models can generate confident answers that contain outdated information.

Information such as software versions, prices, statistics, and public facts changes over time. Users may unknowingly rely on old information because AI-generated answers do not always reflect the latest updates.

Stale Answer Detector addresses this problem by checking claims against current web evidence.

## 💡 Our Solution

Our application provides a structured way to check the freshness of AI-generated information.

Users can paste an answer or upload a document. The application identifies individual claims, checks them against live web sources, and provides clear verdicts with evidence and corrected information.

## ✨ Key Features

1. Claim-by-Claim Verification

Breaks AI-generated answers into individual factual claims.

Checks each claim independently.

Identifies potentially outdated information.

2. Freshness Verdicts

Every claim receives one of three labels:

🟢 Fresh – Information supported by current evidence.

🔴 Outdated – Information appears outdated.

🟡 Unclear – Available evidence is insufficient to establish freshness.

3. Live Source Links

Provides evidence from live web searches.

Displays source links under individual claims.

Helps users independently verify information.

4. Corrected Answers

Provides updated replacement information for claims identified as outdated.

5. Why Did It Go Wrong?

Helps investigate why an AI-generated answer may have become incorrect by examining expected and actual information.

6. Ask and Audit

Ask a question, receive an AI-generated answer, and then audit it for outdated information.

7. Document Checking

Upload PDF or TXT documents.

Identify time-sensitive claims.

Check up to 12 claims per document.

Supports files up to 200 MB.

8. AI Model Comparison

Compare AI models through an 8-question freshness benchmark using time-sensitive questions.

9. PDF Report Generation

Generate and download detailed PDF reports containing verification findings.

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

## 📊 AI Model Benchmarking

Stale Answer Detector includes an AI model comparison feature.

Uses 8 time-sensitive questions.

Compares model responses.

Evaluates freshness accuracy.

Categorizes findings as Fresh, Outdated, or Unclear.

The benchmark helps demonstrate how different AI models handle information that changes over time.

## 🎯 Use Cases

Students: Verify facts in AI-generated study material.

Developers: Check software versions and technical information.

Researchers: Review time-sensitive information.

Professionals: Verify information before using it in reports.

Everyday users: Make more informed decisions when using AI.

## 💻 How to Run Locally

### Step 1: Clone the repository

```
https://github.com/Neelachamaraju/stale-answer-detector.git

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
