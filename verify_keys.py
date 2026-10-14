"""
Diagnostic & Validation Utility for AgentEcom Multi-Model Fallback Cascade.
Tests live authentication against Groq, Gemini, and OpenRouter APIs.

Usage:
    .\\.venv\\Scripts\\python.exe verify_keys.py
"""

import sys
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

from agentecom.config import settings, reload_settings
from agentecom.agent.providers import clean_api_key, ChatGemini, ChatOpenRouter
from agentecom.agent.middleware import modelFallbackMiddleware
from langchain_core.messages import HumanMessage

async def test_groq():
    print("\n--- 1. Testing Groq API ---")
    raw_key = clean_api_key(settings.GROQ_API_KEY)
    if not raw_key:
        print("  [SKIPPED] GROQ_API_KEY is empty or unset in .env")
        print("  Tip: Obtain a free API key at https://console.groq.com/keys")
        return False
    try:
        from langchain_groq import ChatGroq
        model = ChatGroq(model_name=settings.GROQ_MODEL_NAME, api_key=raw_key, temperature=0.1)
        resp = await model.ainvoke([HumanMessage(content="Hello")])
        print(f"  [SUCCESS] Groq authenticated successfully!")
        print(f"  Model: {settings.GROQ_MODEL_NAME}")
        print(f"  Sample response: {resp.content[:60]}...")
        return True
    except Exception as e:
        print(f"  [ERROR] Groq call failed: {e}")
        return False

async def test_gemini():
    print("\n--- 2. Testing Google Gemini API ---")
    raw_key = clean_api_key(settings.GEMINI_API_KEY)
    if not raw_key:
        print("  [SKIPPED] GEMINI_API_KEY is empty or unset in .env")
        print("  Tip: Obtain an API key from Google AI Studio at https://aistudio.google.com/app/apikey")
        return False
    try:
        model = ChatGemini(api_key=raw_key, model_name=settings.GEMINI_MODEL_NAME, temperature=0.1)
        resp = await model.ainvoke([HumanMessage(content="Hello")])
        print(f"  [SUCCESS] Google Gemini authenticated successfully!")
        print(f"  Model: {settings.GEMINI_MODEL_NAME}")
        print(f"  Sample response: {resp.content[:60]}...")
        return True
    except Exception as e:
        print(f"  [ERROR] Gemini call failed: {e}")
        print("  Troubleshooting: Ensure the key is from Google AI Studio (https://aistudio.google.com/app/apikey) and starts with 'AIzaSy'.")
        return False

async def test_openrouter():
    print("\n--- 3. Testing OpenRouter API ---")
    raw_key = clean_api_key(settings.OPENROUTER_API_KEY)
    if not raw_key:
        print("  [SKIPPED] OPENROUTER_API_KEY is empty or unset in .env")
        print("  Tip: Obtain an API key at https://openrouter.ai/keys")
        return False
    try:
        model = ChatOpenRouter(
            api_key=raw_key,
            model_name=settings.OPENROUTER_MODEL_NAME,
            base_url=settings.OPENROUTER_BASE_URL,
            temperature=0.1
        )
        resp = await model.ainvoke([HumanMessage(content="Hello")])
        print(f"  [SUCCESS] OpenRouter authenticated successfully!")
        print(f"  Model: {settings.OPENROUTER_MODEL_NAME}")
        print(f"  Sample response: {resp.content[:60]}...")
        return True
    except Exception as e:
        print(f"  [ERROR] OpenRouter call failed: {e}")
        return False

async def test_cascade():
    print("\n--- 4. Testing Fallback Middleware Cascade Execution ---")
    middleware = modelFallbackMiddleware(
        fallbackModels=settings.FALLBACK_CASCADE_ORDER,
        primary_model="groq"
    )
    res = await middleware.execute([HumanMessage(content="Test message")])
    prov = res.get("provider_used")
    fallback = res.get("fallback_active")
    reason = res.get("fallback_reason")
    print(f"  Provider Used: {prov}")
    print(f"  Fallback Active: {fallback}")
    if reason:
        print(f"  Fallback Reason: {reason}")
    if res.get("response"):
        print(f"  Response: {res['response'].content[:60]}...")

async def main():
    print("==================================================")
    print("AgentEcom LLM Provider & Fallback Diagnostic Tool")
    print("==================================================")
    reload_settings()
    await test_groq()
    await test_gemini()
    await test_openrouter()
    await test_cascade()
    print("\nDiagnostic complete.")

if __name__ == "__main__":
    asyncio.run(main())
