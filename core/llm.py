"""
Ollama Brain for Jarvis (Phase 2).
Handles local LLM inference, function/tool calling, rolling context memory, and safety confirmations.
"""
import time
import json
import httpx
from typing import List, Dict, Any, Optional, Tuple

import config
from core.logger import logger
from core.tools import TOOL_DEFINITIONS, tool_executor

SYSTEM_PROMPT = f"""You are {config.ASSISTANT_NAME}, an autonomous, witty, and highly capable local AI assistant inspired by Tony Stark's JARVIS.
You assist {config.USER_NAME} on this Windows PC.

CRITICAL RULES:
1. CONVERSATION & GENERAL KNOWLEDGE:
   - When {config.USER_NAME} asks a question, definition, fact, how-to, or chats with you (e.g. "what is mobile?", "how are you?", "who are you?", "tell me about X"):
     NEVER invoke any tool! NEVER search Google! NEVER open the browser!
     Answer the question DIRECTLY and intelligently using your own knowledge in 1-2 spoken sentences.
2. SPOKEN FORMAT:
   - Your responses are read aloud via Text-To-Speech. Keep them concise (1-2 sentences).
   - NEVER use markdown formatting, bold asterisks (**), bullet points, emojis, or code blocks in spoken conversational replies.
3. EXPLICIT COMPUTER ACTIONS (Only invoke tools when {config.USER_NAME} gives an action command):
   - To play songs on Spotify: invoke media_control(platform="spotify", query="<song>", action="play").
   - To play videos on YouTube (e.g. "play X on youtube", "play minecraft"): invoke media_control(platform="youtube", query="<title>", action="play").
   - To play a specific numbered video (e.g. "play that second video"): invoke media_control(platform="youtube", query="<title>", action="play", index=2).
   - To click anything on screen (e.g. "click on first video", "click search", "click upload"): invoke click_on_text(target_text="first video" or label).
   - To scroll or swipe down/up: invoke scroll(direction="down" or "up", amount=2).
   - To inspect active screen: invoke read_screen().
   - To control apps or PC: invoke open_app, close_app, or system_control.
4. When a tool finishes executing, synthesize the result into a brief, natural spoken sentence addressing {config.USER_NAME}.
"""

class OllamaBrain:
    """Manages local LLM inference, tool execution, and context memory."""
    
    def __init__(
        self,
        model: str = "llama3.2:3b",
        base_url: str = "http://localhost:11434",
        max_history_turns: int = 10,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.chat_endpoint = f"{self.base_url}/api/chat"
        self.max_history_turns = max_history_turns
        
        self.history: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        
        # Safety confirmation state for destructive actions
        self.pending_confirmation: Optional[Tuple[str, Dict[str, Any]]] = None
        self.warmup()

    def warmup(self):
        """Preloads model weights into GPU VRAM with a 30-minute keep-alive."""
        try:
            logger.log("INFO", f"Preloading Ollama model '{self.model}' into GPU VRAM...")
            with httpx.Client(timeout=15.0) as client:
                client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": self.model, "prompt": "hi", "stream": False, "keep_alive": "30m"}
                )
            logger.log("INFO", f"Ollama model '{self.model}' is warm and ready in GPU VRAM.")
        except Exception as e:
            logger.log("WARN", f"Ollama warmup notice: {e}")

    def reset_conversation(self):
        """Clears conversation history except system prompt."""
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.pending_confirmation = None
        logger.log("INFO", "Conversation memory reset.")

    def trim_history(self):
        """Maintains rolling conversation history."""
        # Keep system prompt + last N message pairs
        if len(self.history) > (self.max_history_turns * 2) + 1:
            system_msg = self.history[0]
            self.history = [system_msg] + self.history[-(self.max_history_turns * 2):]

    def is_confirmation_response(self, text: str) -> Optional[bool]:
        """Checks if text is affirmative or negative for a pending confirmation."""
        cleaned = text.lower().strip()
        for punct in [".", "!", "?", ","]:
            cleaned = cleaned.replace(punct, "")
        
        affirmatives = ["yes", "yeah", "yep", "sure", "proceed", "confirm", "do it", "go ahead", "affirmative"]
        negatives = ["no", "nope", "cancel", "abort", "don't", "stop", "never mind", "negative"]
        
        if any(cleaned == a or cleaned.startswith(a + " ") for a in affirmatives):
            return True
        if any(cleaned == n or cleaned.startswith(n + " ") for n in negatives):
            return False
        return None

    def think_and_respond(self, user_query: str) -> Tuple[str, float]:
        """
        Sends user query to Ollama, executes any tool calls, and returns final speech response.
        Returns: (spoken_response, latency_ms)
        """
        t0 = time.perf_counter()

        # Check if awaiting spoken confirmation for a destructive action
        if self.pending_confirmation:
            confirm = self.is_confirmation_response(user_query)
            tool_name, tool_args = self.pending_confirmation
            self.pending_confirmation = None
            
            if confirm is True:
                logger.log("ACTION", f"User confirmed destructive action '{tool_name}'. Executing...")
                tool_res = tool_executor.execute(tool_name, tool_args)
                self.history.append({"role": "user", "content": user_query})
                self.history.append({"role": "assistant", "content": f"Confirmed. {tool_res}"})
                elapsed = (time.perf_counter() - t0) * 1000
                return f"Action confirmed and executed, {config.USER_NAME}. {tool_res}", elapsed
            elif confirm is False:
                logger.log("ACTION", f"User cancelled destructive action '{tool_name}'.")
                self.history.append({"role": "user", "content": user_query})
                self.history.append({"role": "assistant", "content": "Action cancelled."})
                elapsed = (time.perf_counter() - t0) * 1000
                return f"Action cancelled, {config.USER_NAME}.", elapsed
            else:
                # Ambiguous answer, re-prompt
                elapsed = (time.perf_counter() - t0) * 1000
                return f"Please confirm with yes or no: are you sure you want to proceed?", elapsed

        # Add user query to conversation history
        self.history.append({"role": "user", "content": user_query})
        self.trim_history()

        # Phase 3 & 4: Biometric Face Gate (Recognized = full tools vs Unrecognized = chat-only)
        from core.face_gate import face_gate
        CONTROL_TOOLS = {
            "open_app", "close_app", "system_control", "file_op",
            "run_command", "keyboard_mouse", "click_on_text",
            "click_at_position", "scroll", "media_search", "media_control",
            "web_search", "read_screen"
        }
        is_auth = face_gate.is_authorized() if getattr(config, "FACE_RECOGNITION_ENABLED", True) else True

        if is_auth:
            active_tools = list(TOOL_DEFINITIONS)
        else:
            # Unrecognized: filter out all system control tools (chat-only mode)
            active_tools = [t for t in TOOL_DEFINITIONS if t["function"]["name"] not in CONTROL_TOOLS]

        # Smart tool filtering: only expose web_search when user explicitly requested Google / web search
        web_search_triggers = ["google", "search google", "search the web", "search web", "look up on google", "web search"]
        if not any(trig in user_query.lower() for trig in web_search_triggers):
            active_tools = [t for t in active_tools if t["function"]["name"] != "web_search"]

        # Conversational questions (facts, definitions, how-tos, greetings):
        # Disable tool schema completely so Ollama answers directly without attempting tool executions
        question_starters = [
            "what is", "what are", "what does", "who is", "who are", "why is", "why do", "why does",
            "how do", "how does", "how are you", "tell me", "explain", "define", "do you", "are you",
            "what's", "who's", "can you explain"
        ]
        q_lower = user_query.lower().strip()
        is_general_question = any(q_lower.startswith(qs) or f" {qs} " in q_lower for qs in question_starters)
        action_keywords = [
            "time", "battery", "cpu", "ram", "memory", "wifi", "network", "brightness",
            "status", "youtube", "spotify", "play", "click", "open", "close", "scroll",
            "screen", "app", "file", "folder", "shutdown", "restart", "volume", "mute"
        ]
        if is_general_question and not any(ak in q_lower for ak in action_keywords):
            active_tools = []

        messages = list(self.history)
        if not is_auth:
            messages.append({
                "role": "system",
                "content": (
                    "SECURITY ALERT: Biometric facial recognition is currently UNAUTHORIZED / UNRECOGNIZED. "
                    "You are restricted to chat-only mode. If the user asks to open/close apps, control the system, "
                    "click on screen, or manage files, explicitly respond: 'Access denied, Sir. Biometric facial authentication required to execute system control actions.'"
                )
            })

        # Phase 5: Dynamic Screen Vision Context Injection
        vision_keywords = ["screen", "click", "scroll", "see", "look", "button", "find", "read", "page", "window"]
        if any(kw in user_query.lower() for kw in vision_keywords):
            try:
                from core.screen_monitor import screen_monitor
                screen_ctx = screen_monitor.get_screen_context()
                if screen_ctx:
                    messages.append({
                        "role": "system",
                        "content": f"[Active Screen Context]: {screen_ctx}"
                    })
            except Exception:
                pass

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,
            }
        }
        if active_tools:
            payload["tools"] = active_tools

        try:
            logger.log("THINKING", f"Querying Ollama ({self.model})...")
            with httpx.Client(timeout=30.0) as client:
                res = client.post(self.chat_endpoint, json=payload)
                res.raise_for_status()
                data = res.json()
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            err_msg = f"My reasoning core encountered a connection error with Ollama: {str(e)}"
            logger.log("ERROR", err_msg)
            return err_msg, elapsed

        message = data.get("message", {})
        tool_calls = message.get("tool_calls", [])

        # If LLM requested tool executions
        if tool_calls:
            # Secondary security guard: block control tools if unauthorized
            if not is_auth and any(tc.get("function", {}).get("name") in CONTROL_TOOLS for tc in tool_calls):
                elapsed = (time.perf_counter() - t0) * 1000
                denied_msg = (
                    f"Access denied, {config.USER_NAME}. Biometric facial authentication required "
                    f"to execute system control actions. I am restricted to chat-only mode."
                )
                logger.log("WARN", f"Face Gate blocked control action. Last status: {face_gate.last_status}")
                self.history.pop()  # remove user message to keep conversation state consistent
                return denied_msg, elapsed

            self.history.append(message)

            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", {})
                
                # Check safety gating
                destructive, reason = tool_executor.is_destructive(name, args)
                if destructive:
                    self.pending_confirmation = (name, args)
                    elapsed = (time.perf_counter() - t0) * 1000
                    confirm_prompt = f"Are you sure you want to {reason}?"
                    logger.log("WARN", f"Destructive action gated: {confirm_prompt}")
                    return confirm_prompt, elapsed

                # Execute safe tool
                result = tool_executor.execute(name, args)
                self.history.append({
                    "role": "tool",
                    "content": result,
                })

            # Send tool results back to LLM to formulate spoken response
            follow_up_payload = {
                "model": self.model,
                "messages": self.history,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                }
            }
            try:
                with httpx.Client(timeout=20.0) as client:
                    follow_res = client.post(self.chat_endpoint, json=follow_up_payload)
                    follow_res.raise_for_status()
                    follow_data = follow_res.json()
                    final_reply = follow_data.get("message", {}).get("content", "").strip()
                    self.history.append({"role": "assistant", "content": final_reply})
                    elapsed = (time.perf_counter() - t0) * 1000
                    return final_reply, elapsed
            except Exception as ex:
                elapsed = (time.perf_counter() - t0) * 1000
                return f"Task completed, {config.USER_NAME}.", elapsed

        # Conversational response
        reply = message.get("content", "").strip()
        if reply.lower().startswith("assistant\n"):
            reply = reply[10:].strip()
        elif reply.lower().startswith("assistant:"):
            reply = reply[10:].strip()
        
        # Handle cases where model emitted raw JSON in content instead of natural speech
        if reply.startswith("{") and "name" in reply:
            try:
                data_json = json.loads(reply)
                fn_name = data_json.get("name")
                fn_args = data_json.get("parameters") or data_json.get("arguments") or {}
                if fn_name and hasattr(tool_executor, f"_tool_{fn_name}"):
                    result = tool_executor.execute(fn_name, fn_args)
                    reply = f"Task completed, {config.USER_NAME}. {result}"
                else:
                    reply = f"I am {config.ASSISTANT_NAME}, your personal assistant at your service, {config.USER_NAME}."
            except Exception:
                reply = f"I am at your service, {config.USER_NAME}."

        self.history.append({"role": "assistant", "content": reply})
        elapsed = (time.perf_counter() - t0) * 1000
        return reply, elapsed
