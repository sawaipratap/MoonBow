import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(__file__), "llm_responses.log")

def log_llm_response(node_name: str, response_content: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n" + "="*50 + "\n")
        f.write(f"[{datetime.now().isoformat()}] NODE: {node_name}\n")
        f.write("-" * 50 + "\n")
        f.write(response_content)
        f.write("\n" + "="*50 + "\n")
