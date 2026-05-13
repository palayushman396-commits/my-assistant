from flask import Flask, render_template, request, jsonify, session
from groq import Groq
import os
import json
import datetime
import uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "vedicai-secret-2024")

MEMORY_FILE = "memory.json"

# ---------------- MEMORY FUNCTIONS ---------------- #

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def get_user_memory(user_id):
    memory = load_memory()
    return memory.get(user_id, {})

def update_user_memory(user_id, new_data):
    memory = load_memory()

    if user_id not in memory:
        memory[user_id] = {}

    memory[user_id].update(new_data)
    save_memory(memory)

# ---------------- SYSTEM PROMPT ---------------- #

def build_system_prompt(memory):
    now = datetime.datetime.now().strftime("%A, %B %d %Y at %I:%M %p")

    memory_text = ""

    if memory:
        memory_text = "\n\nThings you remember about this user:\n"

        for key, value in memory.items():
            memory_text += f"- {key}: {value}\n"

    return f"""
You are a helpful personal assistant called VedicAI.

Current date and time: {now}

{memory_text}

When the user shares personal info (name, preferences, goals),
remember it by including a JSON block at the END like:

<memory>{{"key":"value"}}</memory>

Only include memory when something NEW is learned.
"""

# ---------------- MEMORY EXTRACTION ---------------- #

def extract_and_update_memory(response_text, user_id):

    if "<memory>" in response_text and "</memory>" in response_text:

        start = response_text.index("<memory>") + len("<memory>")
        end = response_text.index("</memory>")

        try:
            memory_json = response_text[start:end].strip()
            new_facts = json.loads(memory_json)

            update_user_memory(user_id, new_facts)

        except Exception as e:
            print("Memory Error:", e)

        response_text = (
            response_text[:response_text.index("<memory>")]
            + response_text[end + len("</memory>"):]
        )

    return response_text.strip()

# ---------------- USER CHAT HISTORY ---------------- #

user_histories = {}

# ---------------- ROUTES ---------------- #

@app.route("/")
def home():

    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():

    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    user_id = session["user_id"]

    # Load THIS user's memory only
    memory = get_user_memory(user_id)

    # Create separate history per user
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
                {
                    "role": "system",
                    "content": build_system_prompt(memory)
                }
            ] + user_history[-10:],

            max_tokens=1024
        )

        reply = response.choices[0].message.content

        # Save memory per user
        reply = extract_and_update_memory(reply, user_id)

        user_history.append({
            "role": "assistant",
            "content": reply
        })

        user_histories[user_id] = user_history

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"})

# ---------------- MAIN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)