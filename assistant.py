from google import genai
import os
import json
import datetime

client = genai.Client(api_key=os.environ.get("GOOGLE_API_KEY"))

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

def main():
    memory = load_memory()
    system_prompt = build_system_prompt(memory)
    history = []

    print("\n=============================")
    print("   🤖 AI Personal Assistant  ")
    print("   Type /quit to exit        ")
    print("   Type /memory to see facts ")
    print("=============================\n")

    if memory:
        print(f"👋 Welcome back! I remember {len(memory)} things about you.\n")
    else:
        print("👋 Hello! I am your personal AI assistant.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input == "/quit":
            print("\n👋 Goodbye!\n")
            break
        if user_input == "/memory":
            if memory:
                print("\n📝 What I remember:")
                for k, v in memory.items():
                    print(f"  • {k}: {v}")
                print()
            else:
                print("\n📝 Nothing saved yet.\n")
            continue

        history.append({"role": "user", "parts": [{"text": user_input}]})

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config={"system_instruction": system_prompt}
        )

        reply_text = response.text
        reply_text = extract_and_update_memory(reply_text, memory)

        history.append({"role": "model", "parts": [{"text": reply_text}]})

        print(f"\nAssistant: {reply_text}\n")

if __name__ == "__main__":
    main()