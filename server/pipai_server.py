import os
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Dict
import time
import uuid
import json
import re
from dotenv import load_dotenv
import requests
import sys

# 环境变量加载（如有需要）
load_dotenv()

# OpenAI/Deepseek API 配置（可选）
OPENAI_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
OPENAI_API_BASE = os.getenv('OPENAI_API_BASE', 'https://api.deepseek.com/v1')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'deepseek-chat')

app = FastAPI()

# 存储错误日志的目录
os.makedirs('pipai_logs', exist_ok=True)

class AnalyzeErrorRequest(BaseModel):
    machine_id: str
    error_context: str

def test_ai_connection():
    print(f"\nAttempting to connect to AI service at {OPENAI_API_BASE} with model {OPENAI_MODEL}...")
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "Test connection."},
            {"role": "user", "content": "Hello!"}
        ],
        "temperature": 0.1,
        "max_tokens": 5
    }
    try:
        resp = requests.post(f"{OPENAI_API_BASE}/chat/completions", headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            print("AI service connection successful!")
            # Optionally log the first few characters of the response for confirmation
            # print(f"AI Response snippet: {resp.json()['choices'][0]['message']['content'][:50]}...")
        else:
            print(f"\n--- ERROR: Failed to connect to AI service ---")
            print(f"Status Code: {resp.status_code}")
            try:
                print(f"Response Body: {resp.text}")
            except Exception:
                print("Response body could not be decoded.")
            print("Please check your OPENAI_API_BASE, OPENAI_MODEL, and DEEPSEEK_API_KEY environment variables.")
            print("Exiting server.")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"\n--- ERROR: Failed to connect to AI service (Network/Request Error) ---")
        print(f"Error details: {e}")
        print("Please check your network connection and the OPENAI_API_BASE URL.")
        print("Exiting server.")
        sys.exit(1)
    except Exception as e:
        print(f"\n--- ERROR: An unexpected error occurred during AI connection test ---")
        print(f"Error details: {e}")
        print("Exiting server.")
        sys.exit(1)

@app.on_event("startup")
async def startup_event():
    test_ai_connection()

@app.post('/analyze_error')
async def analyze_error(data: AnalyzeErrorRequest):
    request_id = str(uuid.uuid4()) # Generate a unique ID for this request
    print(f"\n[{request_id}] Received request for machine_id: {data.machine_id}")

    # 1. 日志记录
    log_entry = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'machine_id': data.machine_id,
        'error_context': data.error_context
    }
    log_path = os.path.join('pipai_logs', f'{data.machine_id}.log')
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

    # 2. 生成 AI 提示
    prompt = f"""
You are an expert Python package installation troubleshooter.
The user encountered an error trying to install a Python package using pip.
Here is the relevant error log:

--- ERROR LOG ---
{data.error_context}
--- END ERROR LOG ---

Please analyze this error and suggest ONE or TWO specific, single-line command-line commands that might fix this issue.
Focus ONLY on `pip install ...` commands or `python -m pip install ...` commands. For example, suggest upgrading pip/setuptools/wheel, installing missing build dependencies available on PyPI, or using flags like --no-cache-dir.
Do NOT suggest system package manager commands (apt, yum, brew, etc.) or commands requiring sudo.
Do NOT suggest commands that modify files or environment variables.
Format EACH suggested command clearly on its own line, enclosed in triple backticks. Example:
pip install --upgrade setuptools wheel
pip install some-build-dependency
If you are absolutely certain no simple `pip` command can fix this (e.g., it's clearly a compiler issue needing system libraries, or a typo in a requirements file like `requirments.txt: misspelled-package==1.0`), respond ONLY with the word "UNCERTAIN".
"""

    # 3. 调用 OpenAI/Deepseek API
    print(f"[{request_id}] Calling AI API: {OPENAI_API_BASE}/chat/completions with model {OPENAI_MODEL}")
    suggestion = ""
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": "You are an expert Python package installation troubleshooter focused ONLY on pip command solutions."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.6,
            "max_tokens": 150
        }
        resp = requests.post(f"{OPENAI_API_BASE}/chat/completions", headers=headers, json=payload, timeout=20)
        print(f"[{request_id}] AI API response status code: {resp.status_code}")
        try:
            print(f"[{request_id}] AI API response text: {resp.text[:500]}...") # Log first 500 chars
        except Exception as log_e:
            print(f"[{request_id}] Failed to log AI API response text: {log_e}")

        if resp.status_code == 200:
            ai_data = resp.json()
            suggestion = ai_data['choices'][0]['message']['content'].strip()
            print(f"[{request_id}] AI suggestion obtained: '{suggestion[:100]}...' ")
        else:
            suggestion = f"UNCERTAIN (API error {resp.status_code})"
            print(f"[{request_id}] AI API call failed. Setting suggestion to: {suggestion}")
    except requests.exceptions.RequestException as e:
        suggestion = f"UNCERTAIN (RequestException: {str(e)})"
        print(f"[{request_id}] AI API call failed due to RequestException: {e}. Setting suggestion to: {suggestion}")
    except Exception as e:
        suggestion = f"UNCERTAIN (Exception: {str(e)})"
        print(f"[{request_id}] AI API call failed due to unexpected Exception: {e}. Setting suggestion to: {suggestion}")

    # 4. 返回建议
    response_payload = {"suggestion": suggestion}
    print(f"[{request_id}] Returning response to client: {response_payload}")
    return response_payload

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
