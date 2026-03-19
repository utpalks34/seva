# complaints/chatbot_service.py
"""
SCFMS Civic Complaint Chatbot Service
Uses Gemini API to answer citizens' questions about their complaints
and guide them through the complaint submission process.
"""

import logging
import google.generativeai as genai
from django.conf import settings

logger = logging.getLogger(__name__)

# ── System prompt ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a helpful AI assistant for the Smart Civic Feedback Management System (SCFMS) — a government platform for citizens to report civic issues.

Your role:
- Help citizens understand how to file complaints (potholes, garbage, utilities, public buildings, other civic issues)
- Explain complaint statuses: Pending → In Progress → Resolved
- Guide citizens through the complaint submission form fields (title, description, location, photo)
- Answer questions about how complaints are routed to government departments
- Provide estimated resolution timelines (typically 7-14 days)
- Encourage citizens to be specific and include photos for faster resolution
- If asked about a specific complaint, tell them to check their dashboard for real-time updates

Complaint categories in SCFMS:
- Roads & Potholes (RO)
- Garbage & Waste (GA)
- Utilities – Water/Power (UT)
- Public Buildings (PB)
- Other (OT)

Severity scoring: complaints are automatically scored 1-100 based on keywords and AI image analysis. Scores ≥70 are flagged as high priority.

Rules:
- Be friendly, concise, and helpful
- Answer only civic/complaint related questions
- If asked about something unrelated, gently redirect to civic topics
- Do NOT make up specific data about any real complaint — tell users to check their dashboard
- Reply in the same language as the user's message when possible
- Keep responses under 200 words
"""


class ChatbotService:

    @staticmethod
    def get_response(user_message: str, conversation_history: list = None) -> str:
        """
        Send a message to Gemini and return the assistant's reply.

        Args:
            user_message: The citizen's latest message.
            conversation_history: List of {"role": "user"|"model", "parts": [text]}
                                  for multi-turn context. Pass [] or None for fresh sessions.

        Returns:
            Assistant reply string, or an error message.
        """
        try:
            api_key = settings.GEMINI_API_KEY
            if not api_key:
                return "⚠️ Chatbot is currently unavailable (API key not configured)."

            genai.configure(api_key=api_key)

            model = genai.GenerativeModel(
                model_name="gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT,
            )

            # Build the chat history
            history = conversation_history or []

            # Start / continue a chat session
            chat = model.start_chat(history=history)

            response = chat.send_message(user_message)
            return response.text.strip()

        except Exception as exc:
            logger.error(f"Chatbot error: {exc}")
            return (
                "Sorry, I'm having trouble connecting right now. "
                "Please try again in a moment, or visit the Help section for assistance."
            )
