#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\workers\ai_worker.py JUMLAH BARIS 52 
#######################################################################

import sys
import json
import io # (ADDED) Import the io module
from llama_cpp import Llama
def main():
    """
    This worker script is designed to be called by a subprocess.
    It loads a GGUF model, takes a prompt from stdin,
    generates a response, and prints the response to stdout.
    This isolates the memory-intensive AI operations from the main application.
    """
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Worker requires model_path and n_gpu_layers arguments."}))
        sys.exit(1)
    model_path = sys.argv[1]
    try:
        n_gpu_layers_from_arg = int(sys.argv[2])
    except (ValueError, TypeError):
        print(json.dumps({"error": f"Invalid n_gpu_layers argument received: {sys.argv[2]}"}))
        sys.exit(1)
    print(f"AI Worker: Initializing. Loading model: {model_path} with n_gpu_layers={n_gpu_layers_from_arg}", file=sys.stderr)
    try:
        prompt = sys.stdin.read()
        llm = Llama(
            model_path=model_path,
            n_ctx=8192,
            n_gpu_layers=n_gpu_layers_from_arg,
            verbose=False
        )
        messages = [{"role": "user", "content": prompt}]
        response = llm.create_chat_completion(
            messages=messages,
            max_tokens=2048,
            temperature=0.2
        )
        raw_suggestions = response['choices'][0]['message']['content'].strip()
        print(raw_suggestions)
    except Exception as e:
        error_response = {"error": f"AI Worker failed: {e}", "traceback": str(e)}
        print(json.dumps(error_response), file=sys.stderr)
        sys.exit(1)
if __name__ == "__main__":
    main()
