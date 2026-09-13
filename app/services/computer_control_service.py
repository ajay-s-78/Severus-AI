import os
import re
import logging
import subprocess
import webbrowser
from typing import Dict, Any, Optional

logger = logging.getLogger("severus.computer_control")

class ComputerControlService:
    """
    Safety-first Computer Control service.
    Allows user-confirmed desktop actions (open URL, open allowlisted app, open file/folder path)
    while strictly enforcing allowlists, two-step confirmation, and blocking shell/system commands.
    """

    # Explicit Allowlist of pre-approved desktop applications
    ALLOWLISTED_APPS = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "code": "code",
        "vscode": "code",
        "chrome": "chrome",
        "explorer": "explorer.exe"
    }

    # Prohibited patterns and dangerous system keywords
    BLOCKED_PATTERNS = [
        "rm ", "del ", "delete", "format", "reg ", "regedit", "powershell", "cmd",
        "sh ", "bash", "system32", "ntuser", "subst", "diskpart", "shutdown",
        "restart", "taskkill", "chmod", "chown"
    ]

    def detect_action_intent(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Parses a user message to detect intent to open a website, application, or file path.
        Returns a proposed action spec if detected, or None if standard text query.
        """
        if not message or not isinstance(message, str):
            return None

        msg_lower = message.lower().strip()

        # Check for blocked dangerous commands first
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in msg_lower:
                if any(k in msg_lower for k in ["open", "run", "execute", "start"]):
                    return {
                        "action_type": "blocked",
                        "target": message,
                        "reason": f"Action contains prohibited pattern: '{pattern}'"
                    }

        # 1. URL Opening Intent (e.g. "open https://github.com" or "open google.com")
        url_match = re.search(r'\bopen\s+(https?://[^\s]+|[a-zA-Z0-9.-]+\.(com|org|io|net|edu|dev))\b', msg_lower)
        if url_match:
            raw_url = url_match.group(1)
            target_url = raw_url if raw_url.startswith("http") else f"https://{raw_url}"
            return {
                "action_type": "open_url",
                "target": target_url
            }

        # 2. Allowlisted Application Intent (e.g. "open notepad" or "launch calculator")
        app_match = re.search(r'\b(open|launch|start|run)\s+([a-zA-Z0-9_-]+)\b', msg_lower)
        if app_match:
            app_name = app_match.group(2).lower()
            if app_name in self.ALLOWLISTED_APPS:
                return {
                    "action_type": "open_app",
                    "target": app_name
                }
            elif app_name in ["regedit", "cmd", "powershell", "terminal"]:
                return {
                    "action_type": "blocked",
                    "target": app_name,
                    "reason": f"Application '{app_name}' is not in the safe allowlist."
                }

        # 3. File or Folder Path Intent (e.g. "open path C:/Users/ELCOT/Documents")
        path_match = re.search(r'\bopen\s+(file|folder|path)\s+([^\n]+)', msg_lower)
        if path_match:
            target_path = path_match.group(2).strip()
            return {
                "action_type": "open_path",
                "target": target_path
            }

        return None

    def execute_action(self, action_type: str, target: str, confirmed: bool = False) -> Dict[str, Any]:
        """
        Safely executes a computer control action if confirmed and authorized.
        Enforces confirmation requirement and strict allowlist verification.
        """
        # Safety Check 1: Confirmation Requirement
        if not confirmed:
            return {
                "status": "confirmation_required",
                "message": f"Confirmation required before executing desktop action '{action_type}' for target '{target}'.",
                "action_type": action_type,
                "target": target
            }

        # Safety Check 2: Blocked / Prohibited Actions
        if action_type == "blocked":
            return {
                "status": "blocked",
                "message": f"Action Blocked: Safety policy prohibits executing '{target}'."
            }

        target_lower = target.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in target_lower:
                return {
                    "status": "blocked",
                    "message": f"Action Blocked: Target contains prohibited pattern '{pattern}'."
                }

        # Action 1: Open Website in Default Browser
        if action_type == "open_url":
            if not (target.startswith("http://") or target.startswith("https://")):
                target = f"https://{target}"
            try:
                webbrowser.open(target)
                return {
                    "status": "success",
                    "message": f"Opened website URL: {target}",
                    "action_type": action_type,
                    "target": target
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to open URL '{target}': {str(e)}"
                }

        # Action 2: Open Allowlisted Application
        elif action_type == "open_app":
            app_key = target.lower().strip()
            if app_key not in self.ALLOWLISTED_APPS:
                return {
                    "status": "blocked",
                    "message": f"Action Blocked: Application '{target}' is not in the pre-approved safety allowlist."
                }

            app_exe = self.ALLOWLISTED_APPS[app_key]
            try:
                subprocess.Popen([app_exe])
                return {
                    "status": "success",
                    "message": f"Launched application: '{app_key}' ({app_exe})",
                    "action_type": action_type,
                    "target": target
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to launch application '{app_key}': {str(e)}"
                }

        # Action 3: Open Explicit File or Folder Path
        elif action_type == "open_path":
            clean_path = os.path.normpath(target)
            if not os.path.exists(clean_path):
                return {
                    "status": "error",
                    "message": f"Path not found: '{target}'"
                }

            try:
                if hasattr(os, 'startfile'):
                    os.startfile(clean_path)
                else:
                    subprocess.Popen(["explorer", clean_path])

                return {
                    "status": "success",
                    "message": f"Opened file/folder path: {clean_path}",
                    "action_type": action_type,
                    "target": clean_path
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Failed to open path '{clean_path}': {str(e)}"
                }

        return {
            "status": "error",
            "message": f"Invalid action type '{action_type}'."
        }

computer_control_service = ComputerControlService()
