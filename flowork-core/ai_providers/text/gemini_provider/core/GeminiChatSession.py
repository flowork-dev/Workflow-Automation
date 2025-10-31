#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\ai_providers\text\gemini_provider\core\GeminiChatSession.py JUMLAH BARIS 26 
#######################################################################

import google.generativeai as genai
class GeminiChatSession:
    """Manages the state of a single, continuous chat session with a Gemini model."""
    def __init__(self, model_name="gemini-pro"):
        self.model = genai.GenerativeModel(model_name)
        self.chat_session = self.model.start_chat(history=[])
    def send_message(self, prompt: str) -> str:
        """
        Sends a message to the ongoing chat session and returns the model's response.
        """
        try:
            response = self.chat_session.send_message(prompt)
            return response.text
        except Exception as e:
            return f"Error during chat: {e}"
    @property
    def history(self):
        """Returns the current chat history."""
        return self.chat_session.history
