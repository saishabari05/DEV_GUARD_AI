import os
import google.generativeai as genai
from typing import Dict, Any, List, Callable

class GeminiClient:
    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("Missing GEMINI_API_KEY environment variable")
        genai.configure(api_key=api_key)
        self.chat = None

    def start_chat(self, system_instruction: str, tools: List[Callable] = None):
        model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        
        self.model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_instruction,
            tools=tools
        )
        self.chat = self.model.start_chat(enable_automatic_function_calling=False)

    def send_message(self, message: str) -> Any:
        if not self.chat:
            raise RuntimeError("Chat not started")
        return self.chat.send_message(message)
        
    def send_function_response(self, function_name: str, response: Dict[str, Any]) -> Any:
        return self.chat.send_message(
            genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=function_name,
                    response=response
                )
            )
        )
