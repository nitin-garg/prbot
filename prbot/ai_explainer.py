from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from openai import OpenAI
import requests
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

AI_SCHEMA = {
  "type": "object",
  "additionalProperties": False,
  "properties": {
    "decision": {"type": "string", "enum": ["YES", "NO", "UNCLEAR"]},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    "summary": {"type": "string"},
    "key_risks": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
    "mitigations": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
    "suggested_toggle": {
      "type": "object",
      "additionalProperties": False,
      "properties": {
        "recommended": {"type": "boolean"},
        "scope": {"type": "string", "enum": ["per-tenant","percentage-rollout","admin-only","internal-only","none"]},
        "default_state": {"type": "string", "enum": ["off","on","n/a"]},
        "rollout_steps": {"type": "array", "items": {"type": "string"}, "maxItems": 8}
      },
      "required": ["recommended","scope","default_state","rollout_steps"]
    },
    "questions_for_author": {"type": "array", "items": {"type": "string"}, "maxItems": 6}
  },
  "required": ["decision","confidence","summary","key_risks","mitigations","suggested_toggle","questions_for_author"]
}

def ai_explain(pr_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    pr_context should be a compact, grounded dict. Keep it small.
    """
    model = os.getenv("OPENAI_MODEL", "gpt-5")
    
    system = (
        "You are a senior software engineer doing PR risk review. "
        "You must ONLY use the provided signals; do not invent facts. "
        "If signals conflict or are weak, choose decision UNCLEAR and ask clarifying questions. "
        "Be concise, specific, and practical."
    )
    print("pr_context")
    """
    url = "https://api.euron.one/api/v1/euri/chat/completions"
    token = "euri-526789f89842b3047fa66d27054decfe6a43995c274f6659eb0af4314936fca9"
    payload = {
        "messages":[
        {"role": "system", "content": system},
        {"role": "user", "content": f"Analyze this PR risk context and return JSON only:\n{pr_context}"}
        ],
        "model": "gpt-5"
    }
    
    response = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
    print(response.json())
"""
    # Structured Outputs (json_schema) via Responses API
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Analyze this PR risk context and return JSON only:\n{pr_context}"},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "pr_review_ai_summary",   # <-- REQUIRED
                "schema": AI_SCHEMA,              # <-- NOTE: schema, not json_schema
            }
        },
    )
    print("aaa")
    print(resp)
    # Responses API returns text; with json_schema it will be valid JSON.
    # The SDK exposes it as output_text.
    import json
    return json.loads(resp.output_text)
