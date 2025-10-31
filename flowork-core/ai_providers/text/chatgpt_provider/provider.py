#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\ai_providers\text\chatgpt_provider\provider.py JUMLAH BARIS 49 
#######################################################################

from flowork_kernel.api_contract import BaseAIProvider
from .core.ChatGPTConnection import ChatGPTConnection
class ChatGPTProvider(BaseAIProvider):
    """
    Provides a connection to OpenAI's ChatGPT models.
    """
    def __init__(self, kernel, manifest: dict):
        super().__init__(kernel, manifest)
        self.connection = ChatGPTConnection(self.kernel)
    def get_provider_name(self) -> str:
        return self.loc.get("chatgpt_provider_name", fallback="OpenAI ChatGPT")
    def is_ready(self) -> tuple[bool, str]:
        """Checks if the OpenAI API key is configured."""
        if self.connection.configure():
            return (True, "")
        else:
            return (
                False,
                self.loc.get(
                    "chatgpt_provider_err_not_configured",
                    fallback="ChatGPT Provider is not configured. Check for a valid OPENAI_API_KEY in Settings.",
                ),
            )
    def generate_response(self, prompt: str) -> dict:
        """
        Processes a prompt using ChatGPT and returns a standardized dictionary.
        """
        is_ready, message = self.is_ready()
        if not is_ready:
            return {"type": "text", "data": f"ERROR: {message}"}
        response_dict = self.connection.get_chat_completion(prompt)
        if "error" in response_dict:
            return {
                "type": "text",
                "data": self.loc.get(
                    "chatgpt_api_error",
                    fallback="CHATGPT_API_ERROR: {error}",
                    error=response_dict["error"],
                ),
            }
        else:
            return {"type": "text", "data": response_dict["data"]}
