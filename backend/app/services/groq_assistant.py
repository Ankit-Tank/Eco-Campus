"""
Eco-Campus — services/groq_assistant.py
AI Sustainability Assistant powered by Groq Function Calling.
SPEC §11:
- Reads GROQ_API_KEY and GROQ_MODEL from environment variables only (never exposed).
- Uses Groq function calling so model chooses one whitelisted backend tool.
- Backend executes the tool and passes structured data back to the model.
- Model writes a concise explanation using ONLY the returned data.
- Number Guard: Every number in the answer must appear in the tool output;
  otherwise the LLM text is discarded and the template fallback is used.
- Fallback: On timeout (8s), invalid key, rate limit, number guard failure,
  or unsupported question, returns template-based answer or friendly message.
- Response format: {answer, data_used, source: "groq" | "fallback"}.
"""
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import models
from app.services.assistant_tools import (
    TOOL_DEFINITIONS,
    TOOLS_MAP,
    detect_tool_intent,
    generate_template_answer,
    get_supported_questions_message,
)

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 8.0

SYSTEM_PROMPT = (
    "You are Eco-Campus AI, an expert campus energy and sustainability assistant. "
    "Your objective is to diagnose campus electricity waste, ghost loads, verified savings, "
    "block consumption comparisons, water leak complaints, and prioritized switch-off actions.\n\n"
    "CRITICAL RULES:\n"
    "1. You MUST call exactly one appropriate tool to answer the user's question.\n"
    "2. If the user's question is completely unrelated to campus energy, ghost load, "
    "water leaks, or sustainability, do NOT call any tool.\n"
    "3. When narrating the tool output, use ONLY the numbers and facts provided in the tool response.\n"
    "4. NEVER invent, hallucinate, extrapolate, or estimate any numbers, percentages, costs, or dates.\n"
    "5. Provide a short, direct explanation (1-3 sentences). Do not use bullet points or numbered lists."
)


# ---------------------------------------------------------------------------
# Number Guard: Verification of LLM Grounding
# ---------------------------------------------------------------------------
def extract_numbers_from_obj(obj: Any, numbers: Optional[Set[float]] = None) -> Set[float]:
    """Recursively extracts all numeric values found in a JSON-like object."""
    if numbers is None:
        numbers = set()

    if isinstance(obj, (int, float)):
        numbers.add(float(obj))
    elif isinstance(obj, str):
        # Find all numbers including decimals and room/code numbers
        clean = obj.replace(",", "")
        for m in re.findall(r"\b\d+(?:\.\d+)?\b", clean):
            try:
                numbers.add(float(m))
            except ValueError:
                pass
    elif isinstance(obj, dict):
        for v in obj.values():
            extract_numbers_from_obj(v, numbers)
    elif isinstance(obj, (list, tuple, set)):
        for item in obj:
            extract_numbers_from_obj(item, numbers)

    return numbers


def extract_numbers_from_text(text: str) -> List[float]:
    """Extracts all numeric tokens from natural language text."""
    clean = text.replace(",", "")
    tokens = re.findall(r"\b\d+(?:\.\d+)?\b", clean)
    result = []
    for t in tokens:
        try:
            result.append(float(t))
        except ValueError:
            pass
    return result


def validate_number_guard(answer: str, tool_data: Any) -> bool:
    """
    Every number in the answer must appear in the tool output.
    Returns True if valid, False if hallucinated numbers are present.
    """
    tool_numbers = extract_numbers_from_obj(tool_data)
    text_numbers = extract_numbers_from_text(answer)

    for n in text_numbers:
        matched = False
        for tn in tool_numbers:
            # Match with small tolerance for float representations or rounding
            if abs(n - tn) < 0.15 or round(tn) == round(n):
                matched = True
                break
        if not matched:
            logger.warning("Number guard rejected answer: number %s not in tool output %s", n, tool_numbers)
            return False

    return True


# ---------------------------------------------------------------------------
# Fallback Dispatcher
# ---------------------------------------------------------------------------
def execute_fallback(
    question: str,
    user: models.User,
    db: Session,
    tool_name: Optional[str] = None,
    tool_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Produce a deterministic template-based answer or friendly supported questions list.
    """
    # If tool was already executed and yielded data
    if tool_name and tool_data is not None:
        answer = generate_template_answer(tool_name, tool_data, user)
        return {
            "answer": answer,
            "data_used": tool_data,
            "source": "fallback",
        }

    # Enforce student role restrictions on fallback
    if user.role == "student":
        q_lower = question.lower()
        if any(p in q_lower for p in ("admin operation", "change setting", "reset sim", "assign complaint", "maintenance assignment")):
            return {
                "answer": "Access denied: Students are not permitted to query or execute administrative operations.",
                "data_used": {"refusal": "Access denied: Administrative operations are restricted to administrators."},
                "source": "fallback",
            }

    # Otherwise detect intent from question heuristics
    detected_tool, tool_args = detect_tool_intent(question)
    if detected_tool and detected_tool in TOOLS_MAP:
        try:
            clean_args = {k: v for k, v in tool_args.items() if v is not None}
            data = TOOLS_MAP[detected_tool](db=db, user=user, **clean_args)
            answer = generate_template_answer(detected_tool, data, user)
            return {
                "answer": answer,
                "data_used": data,
                "source": "fallback",
            }
        except Exception as exc:
            logger.error("Error running fallback tool %s: %s", detected_tool, exc)

    # Question is outside supported scope
    return {
        "answer": get_supported_questions_message(),
        "data_used": {},
        "source": "fallback",
    }


# ---------------------------------------------------------------------------
# Core Assistant Entry Point
# ---------------------------------------------------------------------------
def ask(
    question: str,
    user: models.User,
    db: Session,
    timeout_sec: float = TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    """
    Primary AI Assistant workflow using Groq function calling, number guard, and fallbacks.
    Returns:
        {
            "answer": str,
            "data_used": dict,
            "source": "groq" | "fallback",
        }
    """
    # 1. Environment lookup for credentials
    api_key = os.environ.get("GROQ_API_KEY", "").strip() or getattr(settings, "groq_api_key", "").strip()
    model = os.environ.get("GROQ_MODEL", "").strip() or getattr(settings, "groq_model", "openai/gpt-oss-120b").strip()

    if not api_key or api_key in ("invalid_key", "test_invalid_key", "disabled"):
        logger.info("Groq API key unavailable or test-invalid; invoking fallback.")
        return execute_fallback(question, user, db)
    try:
        import importlib
        groq_lib = importlib.import_module("groq")
        client = groq_lib.Groq(api_key=api_key)

        # 2. Initial tool selection turn
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            timeout=timeout_sec,
        )

        choice = response.choices[0]
        message = choice.message

        # Check if the model chose a tool
        if not message.tool_calls:
            logger.info("Model did not select any tool; invoking fallback.")
            return execute_fallback(question, user, db)

        tool_call = message.tool_calls[0]
        fn_name = tool_call.function.name

        if fn_name not in TOOLS_MAP:
            logger.warning("Model requested non-whitelisted function: %s", fn_name)
            return execute_fallback(question, user, db)

        # Parse arguments safely
        try:
            fn_args = json.loads(tool_call.function.arguments or "{}")
            if not isinstance(fn_args, dict):
                fn_args = {}
        except Exception:
            fn_args = {}

        # Enforce student privacy and role restrictions
        if user.role == "student":
            q_lower = question.lower()
            if any(p in q_lower for p in ("admin operation", "change setting", "reset sim", "assign complaint", "maintenance assignment")):
                return {
                    "answer": "Access denied: Students are not permitted to query or execute administrative operations.",
                    "data_used": {"refusal": "Access denied: Administrative operations are restricted to administrators."},
                    "source": "fallback",
                }
            if fn_name == "open_complaints":
                if any(p in q_lower for p in ("other student", "another student", "someone else", "different student", "all students", "everyone's complaint")):
                    tool_data = {
                        "refusal": "Access denied: Students are only permitted to view their own complaints.",
                        "role": user.role,
                        "count": 0,
                    }
                    return {
                        "answer": tool_data["refusal"],
                        "data_used": tool_data,
                        "source": "fallback",
                    }

        # 3. Backend executes whitelisted tool with user role enforcement
        tool_fn = TOOLS_MAP[fn_name]
        tool_data = tool_fn(db=db, user=user, **fn_args)

        # Immediate refusal for unauthorized access
        if "refusal" in tool_data:
            return {
                "answer": tool_data["refusal"],
                "data_used": tool_data,
                "source": "fallback",
            }

        # 4. Model writes short explanation using ONLY returned data
        messages.append(message)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "name": fn_name,
            "content": json.dumps(tool_data),
        })
        messages.append({
            "role": "user",
            "content": (
                "Using strictly and ONLY the data provided above, write a concise factual 1-3 sentence summary. "
                "Do NOT use bullet lists or numbered points. Do NOT invent or add any numbers."
            ),
        })

        narration_response = client.chat.completions.create(
            model=model,
            messages=messages,
            timeout=timeout_sec,
        )

        llm_answer = narration_response.choices[0].message.content or ""
        llm_answer = llm_answer.strip()

        # 5. Number Guard Verification
        if not validate_number_guard(llm_answer, tool_data):
            logger.warning("Number guard triggered: Hallucinated number detected in LLM text.")
            return execute_fallback(question, user, db, tool_name=fn_name, tool_data=tool_data)

        return {
            "answer": llm_answer,
            "data_used": tool_data,
            "source": "groq",
        }

    except Exception as exc:
        logger.warning("Groq Assistant exception (%s: %s); falling back to deterministic answer.", type(exc).__name__, exc)
        return execute_fallback(question, user, db)
