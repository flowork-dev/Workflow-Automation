#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\ai_providers\text\chatgpt_provider\core\ChatGPTConnection.py JUMLAH BARIS 56 
#######################################################################

import openai
class ChatGPTConnection:
    """Handles the connection and authentication to the OpenAI API."""
    def __init__(self, kernel):
        self.kernel = kernel
        self.is_configured = False
        self.client = None
    def configure(self):
        """
        Configures the openai library with the API key from Variable Manager.
        Returns True on success, False on failure.
        """
        if self.is_configured:
            return True
        variable_manager = self.kernel.get_service("variable_manager")
        if not variable_manager:
            self.kernel.write_to_log("Cannot configure ChatGPT: VariableManager service not available.", "CRITICAL") # English Log
            return False
        api_key = variable_manager.get_variable("OPENAI_API_KEY")
        if not api_key:
            self.kernel.write_to_log("OPENAI_API_KEY not found in Variable Manager.", "ERROR") # English Log
            return False
        try:
            self.client = openai.OpenAI(api_key=api_key)
            self.is_configured = True
            self.kernel.write_to_log("OpenAI (ChatGPT) has been configured successfully.", "SUCCESS") # English Log
            return True
        except Exception as e:
            self.kernel.write_to_log(f"Failed to configure OpenAI client: {e}", "ERROR") # English Log
            return False
    def get_chat_completion(self, prompt: str) -> dict:
        """
        Sends a prompt to the OpenAI API and gets a response.
        Returns a dictionary with either 'data' or 'error'.
        """
        if not self.is_configured or not self.client:
            return {"error": "OpenAI client is not configured."}
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo", # You can change the model here
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            return {"data": response.choices[0].message.content}
        except Exception as e:
            self.kernel.write_to_log(f"OpenAI API request failed: {e}", "ERROR") # English Log
            return {"error": str(e)}
