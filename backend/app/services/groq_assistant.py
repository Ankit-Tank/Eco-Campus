"""
GhostWatt — services/groq_assistant.py
Calls Groq API with grounded data context. SPEC §11.
API key read from settings — NEVER exposed to frontend.
"""
from app.core.config import settings


def ask(question: str, grounded_data: dict, role: str = "student") -> dict:
    """
    Send a grounded question to Groq and return the answer.
    Falls back gracefully if Groq is unavailable.
    """
    if not settings.groq_api_key:
        return {
            "answer": "AI Assistant is not configured. Please set GROQ_API_KEY in .env.",
            "grounded": False,
            "fallback": True,
        }

    try:
        from groq import Groq
        client = Groq(api_key=settings.groq_api_key)

        system_prompt = (
            "You are GhostWatt AI, a campus energy assistant. "
            "Answer ONLY using the data provided in the user message. "
            "Never invent numbers, readings, or facts not present in the data. "
            "Be concise and actionable."
        )
        user_message = (
            f"Data from campus systems:\n{grounded_data}\n\n"
            f"Question: {question}"
        )

        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            max_tokens=400,
        )
        answer = response.choices[0].message.content
        return {"answer": answer, "grounded": True, "fallback": False}

    except Exception as exc:
        return {
            "answer": f"AI Assistant is temporarily unavailable. ({type(exc).__name__})",
            "grounded": False,
            "fallback": True,
        }
