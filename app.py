import requests
from flask import Flask, render_template, request, redirect
import sqlite3

# Flask app
app = Flask(__name__)

# ---------------- DATABASE SETUP ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT,
            recommendation TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ---------------- AI LOGIC (OLLAMA) ----------------
def analyze_decision(text):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": f"""
Help the user make a decision.

Situation:
{text}

Answer clearly in this format:

Conclusion: one word
Reason:
2 short lines explaining why

Only give the answer. No extra explanation.
""",
                "stream": False
            },
            timeout=120
        )

        data = response.json()
        output = data.get("response", "").strip()

        print("AI RAW OUTPUT:", output)

        # --------- CLEAN OUTPUT ----------
        output = output.replace("User,", "").replace("Assistant,", "").strip()

        conclusion = "Not clear"
        reason = "No reasoning found"

        # Extract conclusion
        if "Conclusion:" in output:
            conclusion = output.split("Conclusion:")[1].split("\n")[0].strip()
        else:
            first_line = output.split("\n")[0]
            conclusion = first_line.split(" ")[0]

        # Extract reason
        if "Reason:" in output:
            reason = output.split("Reason:")[1].strip()
        else:
            reason = output

        # Extra safety cleaning
        if conclusion.lower() in ["user", "assistant", "response", ""]:
            conclusion = "Not clear"

        if "<" in conclusion or ">" in conclusion:
            conclusion = "Not clear"

    except Exception as e:
        print("Ollama error:", e)
        conclusion = "Error"
        reason = "⚠️ AI not responding"

    return {
        "recommendation": conclusion,
        "reason": reason
    }

# ---------------- ROUTE ----------------
@app.route("/", methods=["GET", "POST"])
def home():
    user_input = ""
    result = None

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == "POST":
        user_input = request.form.get("user_input")

        if user_input:
            result = analyze_decision(user_input)

            c.execute(
                "INSERT INTO decisions (user_input, recommendation) VALUES (?, ?)",
                (user_input, result["recommendation"])
            )
            conn.commit()

    c.execute("SELECT * FROM decisions ORDER BY id DESC")
    history = c.fetchall()

    conn.close()

    return render_template(
        "index.html",
        user_input=user_input,
        result=result,
        history=history
    )

# ---------------- DELETE ROUTE ----------------
@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("DELETE FROM decisions WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)