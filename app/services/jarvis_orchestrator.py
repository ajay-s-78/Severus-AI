import logging
import re
from typing import Dict, Any, Optional
from app.services.ai_service import ai_service
from app.services.search_service import search_service
from app.services.computer_control_service import computer_control_service
from app.services.memory_service import memory_service
from app.services.analytics_service import analytics_service
from app.services.speaker_verification_service import speaker_verification_service

logger = logging.getLogger("severus.jarvis_orchestrator")


class JarvisOrchestrator:
    """
    Advanced JARVIS Assistant Orchestration Service for Severus-AI.
    Classifies user intent, enforces speaker identity authorization,
    routes requests to appropriate sub-services, supports combined workflows,
    and formats concise responses.
    """

    def strip_wake_word(self, message: str) -> str:
        """Strips leading assistant wake words like 'Severus,' or 'Hey Severus'."""
        if not message:
            return ""
        return re.sub(r'^(hey\s+severus|severus)[,\s:]*', '', message, flags=re.IGNORECASE).strip()

    def classify_intent(self, message: str, has_image: bool = False) -> Dict[str, Any]:
        """
        Classifies user request intent and identifies required capabilities.
        """
        clean_msg = self.strip_wake_word(message)
        msg_lower = clean_msg.lower() if clean_msg else ""

        needs_search = search_service.should_search(clean_msg) if clean_msg else False
        action_intent = computer_control_service.detect_action_intent(clean_msg) if clean_msg else None

        is_memory_query = any(
            kw in msg_lower for kw in [
                "remember that", "my name is", "i prefer", "what do you remember",
                "my project", "stored memory", "saved memory", "what do you know about"
            ]
        )

        is_ml_query = any(
            kw in msg_lower for kw in [
                "classification model", "predict whether", "predict churn", "predict",
                "regression model", "train a model", "train model", "train a random forest",
                "train logistic regression", "evaluate model", "model recommendation",
                "which algorithm", "best model for this dataset", "best model",
                "logistic regression", "random forest", "linear regression", "decision tree",
                "k-nearest neighbors", "knn", "accuracy score", "f1 score", "confusion matrix",
                "r2 score", "rmse", "mae", "mse", "machine learning", "supervised learning"
            ]
        )
        is_analytics_query = any(
            kw in msg_lower for kw in [
                "analytics",
                "visualize",
                "visualization",
                "chart",
                "plot",
                "graph",
                "histogram",
                "scatter plot",
                "box plot",
                "bar chart",
                "line chart",
                "heatmap",
                "outlier",
                "correlation analysis",
                "advanced eda"
            ]
        )

        is_ds_query = any(
            kw in msg_lower for kw in [
                "dataset", "dataframe", "eda", "summary statistics", "rows", "columns",
                "missing values", "null values", "highest average", "correlation",
                "data types", "duplicates", "feature engineering", "explore data"
            ]
        ) and not is_ml_query

        # Primary Intent Classification
        if action_intent:
            primary = "computer_control"
        elif has_image and needs_search:
            primary = "vision_search"
        elif has_image:
            primary = "vision"
        elif is_ml_query:
            primary = "machine_learning"
        elif is_analytics_query:
            primary = "analytics"
        elif is_ds_query:
            primary = "data_analysis"
        elif needs_search:
            primary = "web_search"
        elif is_memory_query:
            primary = "memory"
        else:
            primary = "general"

        return {
            "primary_intent": primary,
            "has_image": has_image,
            "needs_search": needs_search,
            "action_intent": action_intent,
            "is_memory_query": is_memory_query,
            "is_ds_query": is_ds_query,
            "is_ml_query": is_ml_query,
            "is_analytics_query": is_analytics_query
        }

    async def orchestrate(
        self,
        session_id: str,
        message: str,
        image_bytes: Optional[bytes] = None,
        image_mime: Optional[str] = None,
        speaker_status: str = "VERIFICATION_UNAVAILABLE"
    ) -> Dict[str, Any]:
        """
        Orchestrates request processing across underlying Severus capability services.
        Enforces Phase 11 speaker authorization for computer control & private owner memory.
        Returns structured payload containing response text, session ID, action_required, and intent info.
        """
        clean_msg = self.strip_wake_word(message)
        has_image = bool(image_bytes and image_mime)
        intent_info = self.classify_intent(clean_msg, has_image=has_image)

        # ---------------------------------------------------------
        # Security Policy 1: Private Owner Memory Access Protection
        # ---------------------------------------------------------
        if speaker_verification_service.is_private_owner_query(clean_msg):
            if speaker_status != "AUTHORIZED_OWNER":
                return {
                    "response": "🔒 **Privacy Restriction**: Private owner information and stored personal memories can only be accessed by the verified owner.",
                    "session_id": session_id,
                    "action_required": None,
                    "intent": "memory",
                    "status_text": "Privacy Guard Active"
                }

        if speaker_verification_service.is_owner_self_query(clean_msg):
            if speaker_status != "AUTHORIZED_OWNER":
                return {
                    "response": "🔒 **Privacy Restriction**: Stored personal memories can only be accessed by the verified owner.",
                    "session_id": session_id,
                    "action_required": None,
                    "intent": "memory",
                    "status_text": "Privacy Guard Active"
                }

        # ---------------------------------------------------------
        # Security Policy 2: Desktop Action Intent / Computer Control
        # ---------------------------------------------------------
        action_intent = intent_info.get("action_intent")
        if action_intent:
            # Backend Authorization Gate
            if speaker_status != "AUTHORIZED_OWNER":
                return {
                    "response": "⚠️ **Access Restricted**: Desktop computer control capabilities are restricted to the verified owner.",
                    "session_id": session_id,
                    "action_required": None,
                    "intent": "computer_control",
                    "status_text": "Unauthorized Speaker"
                }

            # Safety Check: Prohibited Action Patterns
            if action_intent.get("action_type") == "blocked":
                reason = action_intent.get("reason", "Prohibited by safety policy.")
                blocked_msg = f"⚠️ **Action Blocked**: {reason}"
                return {
                    "response": blocked_msg,
                    "session_id": session_id,
                    "action_required": None,
                    "intent": "computer_control",
                    "status_text": "Action Blocked"
                }
            else:
                act_type = action_intent["action_type"]
                target = action_intent["target"]
                prompt_msg = f"🖥️ **Confirmation Required**: Would you like me to proceed with `{act_type}` on target `{target}`?"
                return {
                    "response": prompt_msg,
                    "session_id": session_id,
                    "action_required": {"action_type": act_type, "target": target},
                    "intent": "computer_control",
                    "status_text": "Awaiting Confirmation"
                }

        # ---------------------------------------------------------
        # Capabilities Routing: Analytics & Visualization
        # ---------------------------------------------------------
        if intent_info["primary_intent"] == "analytics":
            return {
                "response": "📊 Analytics mode detected. Please upload a dataset to perform advanced analysis or visualization.",
                "session_id": session_id,
                "action_required": None,
                "intent": "analytics",
                "status_text": "Analytics Ready"
            }

        # ---------------------------------------------------------
        # Capabilities Routing: Standard Chat / AI Response
        # ---------------------------------------------------------
        try:
            response_text = await ai_service.get_response(
                session_id=session_id,
                message=clean_msg,
                image_bytes=image_bytes,
                image_mime=image_mime
            )

            status_text = "Ready" if speaker_status == "AUTHORIZED_OWNER" else "Ready"

            return {
                "response": response_text,
                "session_id": session_id,
                "action_required": None,
                "intent": intent_info["primary_intent"],
                "status_text": status_text
            }
        except Exception as e:
            logger.error(f"Orchestration error during response generation: {str(e)}")
            raise e


jarvis_orchestrator = JarvisOrchestrator()
