from flask import Flask, render_template, request, jsonify
from google import genai
import os
import json
import datetime

app = Flask(__name__)
client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

MEMORY_FILE = "memory.json"
conversation_history = []

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def build_system_prompt(memory):
    now = datetime.datetime.now().strftime("%A, %B %d %Y at %I:%M %p")
    memory_text = ""
    if memory:
        memory_text = "\n\nThings you remember about the user:\n"
        for key, value in memory.items():
            memory_text += f"- {key}: {value}\n"
    return f"""You are a helpful personal assistant.
Current date and time: {now}
{memory_text}
When the user shares personal info (name, preferences, goals),
remember it by including a JSON block at the END like:
<memory>{{"key": "value"}}</memory>
Only include <memory> when there is something NEW to remember."""

def extract_and_update_memory(response_text, memory):
    if "<memory>" in response_text and "</memory>" in response_text:
        start = response_text.index("<memory>") + len("<memory>")
        end = response_text.index("</memory>")
        try:
            new_facts = json.loads(response_text[start:end].strip())
            memory.update(new_facts)
            save_memory(memory)
        except:
            pass
        response_text = response_text[:response_text.index("<memory>")] + response_text[end + len("</memory>"):]
    return response_text.strip()

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    memory = load_memory()
    user_input = request.json.get("message")
    conversation_history.append({
        "role": "user",
        "parts": [{"text": user_input}]
    })
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=conversation_history,
            config={"system_instruction": build_system_prompt(memory)}
        )
        reply = extract_and_update_memory(response.text, memory)
        conversation_history.append({
            "role": "model",
            "parts": [{"text": reply}]
        })
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)