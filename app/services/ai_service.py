import logging
from typing import Dict, List, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    BaseMessage,
)

from app.core.config import settings
from app.database.database import get_connection, create_tables
from app.prompts.system_prompt import SEVERUS_SYSTEM_PROMPT
from app.services.search_service import search_service
from app.services.memory_service import memory_service


logger = logging.getLogger("severus.ai_service")


class AIService:
    """
    LangChain AI Service for Google Gemini.

    Maintains per-session conversation history in memory
    and persists chat messages in SQLite.
    """

    def __init__(self):
        self._sessions: Dict[str, List[BaseMessage]] = {}
        create_tables()

    # ---------------------------------------------------------
    # API KEY
    # ---------------------------------------------------------

    def get_api_key(self) -> Optional[str]:
        return settings.get_api_key()

    def _is_api_key_valid(self) -> bool:
        key = self.get_api_key()

        if not key:
            return False

        if settings.is_placeholder_value(key):
            return False

        return True

    # ---------------------------------------------------------
    # SESSION HISTORY
    # ---------------------------------------------------------

    def get_session_history(
        self,
        session_id: str
    ) -> List[BaseMessage]:
        """Load session history from memory or SQLite."""

        if session_id not in self._sessions:
            self._sessions[session_id] = []

            connection = get_connection()

            rows = connection.execute(
                """
                SELECT role, content
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,)
            ).fetchall()

            connection.close()

            for row in rows:
                if row["role"] == "user":
                    self._sessions[session_id].append(
                        HumanMessage(content=row["content"])
                    )

                elif row["role"] == "assistant":
                    self._sessions[session_id].append(
                        AIMessage(content=row["content"])
                    )

        return self._sessions[session_id]

    # ---------------------------------------------------------
    # SAVE MESSAGE
    # ---------------------------------------------------------

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None:
        """Save a chat message to SQLite."""

        connection = get_connection()

        connection.execute(
            """
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (?, ?, ?)
            """,
            (session_id, role, content)
        )

        connection.commit()
        connection.close()

    # ---------------------------------------------------------
    # CLEAR HISTORY
    # ---------------------------------------------------------

    def clear_session_history(
        self,
        session_id: str
    ) -> bool:
        """Clear session history from memory and SQLite."""

        existed = session_id in self._sessions

        self._sessions.pop(session_id, None)

        connection = get_connection()

        connection.execute(
            """
            DELETE FROM chat_messages
            WHERE session_id = ?
            """,
            (session_id,)
        )

        deleted = connection.total_changes

        connection.commit()
        connection.close()

        return existed or deleted > 0

    # ---------------------------------------------------------
    # JSON HISTORY
    # ---------------------------------------------------------

    def get_session_messages_json(
        self,
        session_id: str
    ) -> List[Dict[str, str]]:
        """Return conversation history as JSON."""

        history = self.get_session_history(session_id)

        result: List[Dict[str, str]] = []

        for msg in history:

            if isinstance(msg, HumanMessage):
                result.append({
                    "role": "user",
                    "content": self._content_to_string(msg.content),
                })

            elif isinstance(msg, AIMessage):
                result.append({
                    "role": "assistant",
                    "content": self._content_to_string(msg.content),
                })

        return result

    # ---------------------------------------------------------
    # CONTENT CONVERSION
    # ---------------------------------------------------------

    @staticmethod
    def _content_to_string(content) -> str:
        """Convert Gemini/LangChain content into plain text."""

        if content is None:
            return ""

        if isinstance(content, str):
            return content

        if isinstance(content, list):

            parts: List[str] = []

            for item in content:

                if isinstance(item, str):
                    parts.append(item)

                elif isinstance(item, dict):
                    text = item.get("text")

                    if text:
                        parts.append(str(text))

            return "".join(parts).strip()

        return str(content)

    # ---------------------------------------------------------
    # GEMINI RESPONSE
    # ---------------------------------------------------------

    async def get_response(
        self,
        session_id: str,
        message: str
    ) -> str:
        """
        Send user message to Google Gemini
        and persist the conversation.
        """

        api_key = self.get_api_key()

        # -----------------------------------------------------
        # API KEY CHECK
        # -----------------------------------------------------

        if not api_key or settings.is_placeholder_value(api_key):

            logger.warning(
                "Google Gemini API key missing or placeholder."
            )

            return (
                "**Gemini API Key Not Configured**\n\n"
                "Please set a valid `GOOGLE_API_KEY` "
                "in your `.env` file."
            )

        if not self._is_api_key_valid():

            return (
                "**Severus AI Error**\n\n"
                "Gemini API key is invalid."
            )

        try:

            # -------------------------------------------------
            # GET HISTORY
            # -------------------------------------------------

            history = self.get_session_history(session_id)

            # -------------------------------------------------
            # CREATE GEMINI MODEL
            # -------------------------------------------------

            model = ChatGoogleGenerativeAI(
                model=settings.MODEL_NAME,
                google_api_key=api_key,
                temperature=0.2,
            )

            # -------------------------------------------------
            # CHECK WEB SEARCH NEED
            # -------------------------------------------------
            augmented_message = message

            if search_service.should_search(message):
                try:
                    search_results = search_service.search(message)
                    if search_results:
                        context_parts = [f"[Web Search Results Context for query: '{message}']"]
                        sources_list = []
                        for idx, res in enumerate(search_results, start=1):
                            context_parts.append(f"{idx}. Title: {res['title']}\n   Snippet: {res['snippet']}\n   URL: {res['url']}")
                            if res.get("url"):
                                sources_list.append(f"- [{res['title']}]({res['url']})")

                        sources_formatted = "\n".join(sources_list) if sources_list else ""
                        search_context = "\n\n".join(context_parts)
                        
                        augmented_message = (
                            f"{search_context}\n\n"
                            f"User Request: {message}\n\n"
                            f"Instructions: Use the real-time web search context above to answer the user request accurately. "
                            f"At the end of your answer, include a section titled '### Sources' citing the retrieved sources:\n{sources_formatted}"
                        )
                except Exception as search_err:
                    logger.warning(f"Web search failed: {search_err}. Proceeding with standard response.")

            # -------------------------------------------------
            # ADVANCED MEMORY RETRIEVAL & FACT EXTRACTION
            # -------------------------------------------------
            try:
                memory_service.extract_and_save_facts(message)
            except Exception as mem_ex_err:
                logger.warning(f"Memory fact extraction error: {mem_ex_err}")

            system_prompt_content = SEVERUS_SYSTEM_PROMPT
            try:
                relevant_memories = memory_service.get_relevant_memories(message)
                if relevant_memories:
                    mem_lines = [f"- {m['key']}: {m['value']}" for m in relevant_memories[:10]]
                    memory_block = "\n\n[User Memory Context Across Sessions]:\n" + "\n".join(mem_lines)
                    system_prompt_content += memory_block
            except Exception as mem_ret_err:
                logger.warning(f"Memory retrieval error: {mem_ret_err}")

            # -------------------------------------------------
            # BUILD MESSAGES
            # -------------------------------------------------

            messages: List[BaseMessage] = [
                SystemMessage(
                    content=system_prompt_content
                )
            ]

            messages.extend(history)

            messages.append(
                HumanMessage(
                    content=augmented_message
                )
            )


            # -------------------------------------------------
            # GEMINI CALL
            # -------------------------------------------------

            response = await model.ainvoke(messages)

            ai_response_text = self._content_to_string(
                response.content
            )

            if not ai_response_text:
                return (
                    "**Severus AI Error**\n\n"
                    "Gemini returned an empty response."
                )

            # -------------------------------------------------
            # UPDATE MEMORY
            # -------------------------------------------------

            history.append(
                HumanMessage(content=message)
            )

            history.append(
                AIMessage(content=ai_response_text)
            )

            # -------------------------------------------------
            # SAVE TO DATABASE
            # -------------------------------------------------

            self.save_message(
                session_id=session_id,
                role="user",
                content=message,
            )

            self.save_message(
                session_id=session_id,
                role="assistant",
                content=ai_response_text,
            )

            # -------------------------------------------------
            # KEEP LAST 20 MESSAGES IN MEMORY
            # -------------------------------------------------

            if len(history) > 20:
                self._sessions[session_id] = history[-20:]

            return ai_response_text

        except Exception as e:

            error_str = str(e)

            logger.error(
                f"Error during Gemini response generation: "
                f"{error_str}"
            )

            error_lower = error_str.lower()

            if (
                "api key" in error_lower
                or "authentication" in error_lower
                or "unauthenticated" in error_lower
                or "permission denied" in error_lower
                or "invalid_argument" in error_lower
            ):

                return (
                    "**Gemini Authentication / Quota Error**\n\n"
                    "Please check your Gemini API key and "
                    "API quota."
                )

            return (
                "**Severus AI Service Error**\n\n"
                "Unable to complete the request.\n\n"
                f"Details: {error_str}"
            )


# -------------------------------------------------------------
# SINGLETON INSTANCE
# -------------------------------------------------------------

ai_service = AIService()