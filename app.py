from flask import Flask, render_template, request, jsonify, session
from groq import Groq
import os
import json
import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vedicai-secret-2024")

MEMORY_FILE = "memory.json"

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
    return f"""You are a helpful personal assistant called VedicAI.
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

# Store each user's conversation separately
user_histories = {}

@app.route("/")
def home():
    # Give each user a unique session ID
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    memory = load_memory()

    # Get this user's unique ID
    user_id = session.get("user_id", str(uuid.uuid4()))

    # Get or create this user's history
    if user_id not in user_histories:
        user_histories[user_id] = []

    user_history = user_histories[user_id]
    user_input = request.json.get("message")

    user_history.append({
        "role": "user",
        "content": user_input
    })

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": build_system_prompt(memory)}
            ] + user_history,
            max_tokens=1024
        )
        reply = response.choices[0].message.content
        reply = extract_and_update_memory(reply, memory)
        user_history.append({
            "role": "assistant",
            "content": reply
        })
        user_histories[user_id] = user_history
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})

if __name__ == "__main__":
    app.run(debug=True)