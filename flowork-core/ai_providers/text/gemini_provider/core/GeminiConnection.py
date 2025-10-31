#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\ai_providers\text\gemini_provider\core\GeminiConnection.py JUMLAH BARIS 36 
#######################################################################

import google.generativeai as genai
class GeminiConnection:
    """Handles the connection and authentication to the Google AI API."""
    def __init__(self, kernel):
        self.kernel = kernel
        self.is_configured = False
    def configure(self):
        """
        Configures the genai library with the API key from Variable Manager.
        Returns True on success, False on failure.
        """
        if self.is_configured:
            return True
        variable_manager = self.kernel.get_service("variable_manager")
        if not variable_manager:
            self.kernel.write_to_log("Cannot configure Gemini: VariableManager service not available.", "CRITICAL") # English Log
            return False
        api_key = variable_manager.get_variable("GEMINI_API_KEY")
        if not api_key:
            self.kernel.write_to_log("GEMINI_API_KEY not found in Variable Manager.", "ERROR")
            return False
        try:
            genai.configure(api_key=api_key)
            self.is_configured = True
            self.kernel.write_to_log("Google AI (Gemini) has been configured successfully.", "SUCCESS")
            return True
        except Exception as e:
            self.kernel.write_to_log(f"Failed to configure Gemini: {e}", "ERROR")
            return False
