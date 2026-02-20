print("RUNNING THIS APP.PY FILE")
import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from sklearn.linear_model import LinearRegression


# ================= CONFIG =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    static_folder=os.path.join(BASE_DIR, "static"),
    static_url_path="/static"
)

from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

app.secret_key = "study_tracker_secret_123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

DB_PATH = os.path.join(BASE_DIR, "study.db")


# ================= GLOBAL STACKS =================

undo_stack = []
redo_stack = []


# ================= DATABASE =================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    # Users
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            weekly_goal INTEGER DEFAULT 0
        )
    """)

    # Study Logs
    conn.execute("""
        CREATE TABLE IF NOT EXISTS study_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            subject TEXT,
            topic TEXT,
            hours REAL,
            difficulty INTEGER
        )
    """)

    # Profiles
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,

            display_name TEXT,
            bio TEXT,
            skills TEXT,
            interests TEXT,
            college TEXT,
            image TEXT,

            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# ================= ML =================

def train_model(df):

    if len(df) < 3:
        return None

    df["day"] = pd.to_datetime(df["date"])
    df = df.sort_values("day")

    df["study_day"] = range(1, len(df) + 1)

    X = df[["study_day", "hours", "difficulty"]]

    y = (df["hours"] * 10) - (df["difficulty"] * 2) + (df["study_day"] * 1.5)

    model = LinearRegression()
    model.fit(X, y)

    return model


def generate_chart(df):

    if df.empty:
        return

    data = df.groupby("subject")["hours"].sum()

    plt.figure()
    data.plot(kind="bar")

    plt.title("Total Hours per Subject")
    plt.xlabel("Subject")
    plt.ylabel("Hours")

    plt.tight_layout()
    plt.savefig("static/subject_hours.png")
    plt.close()


# ================= HOME =================

@app.route("/")
def home():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    df = pd.read_sql_query(
        "SELECT * FROM study_log WHERE user_id = ?",
        conn,
        params=(session["user_id"],)
    )

    logs = df.to_dict("records")

    # Profile
    profile = conn.execute(
        "SELECT display_name, image FROM user_profiles WHERE user_id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()


    # Analytics
    total_hours = {}

    readiness = None
    status = None


    if not df.empty:

        total_hours = df.groupby("subject")["hours"].sum().to_dict()

        generate_chart(df)

        model = train_model(df)

        if model:

            latest = df.iloc[-1]

            X_new = np.array([[
                len(df),
                latest["hours"],
                latest["difficulty"]
            ]])

            score = model.predict(X_new)[0]

            readiness = round(min(max(score, 0), 100), 2)

            if readiness >= 75:
                status = "ON TRACK 🚀"
            elif readiness >= 50:
                status = "NEEDS IMPROVEMENT ⚠️"
            else:
                status = "RISK ZONE 🔴"


    display = profile["display_name"] if profile else session["username"]

    if profile and profile["image"]:
        image = profile["image"]
    else:
        image = "default.png"


    return render_template(
        "index.html",

        logs=logs,
        total_hours=total_hours,

        readiness=readiness,
        status=status,

        display_name=display,
        profile_img=image
    )


# ================= PROFILE =================

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    df = pd.read_sql_query(
        "SELECT * FROM study_log WHERE user_id = ?",
        conn,
        params=(session["user_id"],)
    )

    conn.close()


    total_hours = round(df["hours"].sum(), 1) if not df.empty else 0
    total_days = df["date"].nunique() if not df.empty else 0
    avg_difficulty = round(df["difficulty"].mean(), 2) if not df.empty else 0


    best_subject = "N/A"

    if not df.empty:
        best_subject = df.groupby("subject")["hours"].sum().idxmax()


    # Streak
    streak = 0

    if not df.empty:

        dates = pd.to_datetime(df["date"].unique())
        dates = sorted(dates, reverse=True)

        streak = 1

        for i in range(1, len(dates)):

            if (dates[i-1] - dates[i]).days == 1:
                streak += 1
            else:
                break


    # Level
    if total_hours >= 300:
        level = "Master 👑"
    elif total_hours >= 150:
        level = "Advanced 🔥"
    elif total_hours >= 50:
        level = "Intermediate ⚡"
    else:
        level = "Beginner 🐣"


    return render_template(
        "profile.html",

        username=session["username"],

        total_hours=total_hours,
        total_days=total_days,
        avg_difficulty=avg_difficulty,
        best_subject=best_subject,
        streak=streak,
        level=level
    )


# ================= STUDY =================

@app.route("/add", methods=["POST"])
def add():

    conn = get_db()

    conn.execute("""
        INSERT INTO study_log
        (user_id, date, subject, topic, hours, difficulty)

        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        request.form["date"],
        request.form["subject"],
        request.form["topic"],
        request.form["hours"],
        request.form["difficulty"]
    ))

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/delete/<int:id>")
def delete(id):

    global undo_stack, redo_stack

    conn = get_db()

    row = conn.execute(
        "SELECT * FROM study_log WHERE id = ?",
        (id,)
    ).fetchone()

    if row:

        undo_stack.append(dict(row))
        redo_stack.clear()

        conn.execute("DELETE FROM study_log WHERE id = ?", (id,))
        conn.commit()

    conn.close()

    return redirect("/")


@app.route("/undo")
def undo():

    if not undo_stack:
        return redirect("/")

    last = undo_stack.pop()

    conn = get_db()

    conn.execute("""
        INSERT INTO study_log
        (id, user_id, date, subject, topic, hours, difficulty)

        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        last["id"],
        last["user_id"],
        last["date"],
        last["subject"],
        last["topic"],
        last["hours"],
        last["difficulty"]
    ))

    conn.commit()
    conn.close()

    redo_stack.append(last)

    return redirect("/")


@app.route("/redo")
def redo():

    if not redo_stack:
        return redirect("/")

    last = redo_stack.pop()

    conn = get_db()

    conn.execute("DELETE FROM study_log WHERE id = ?", (last["id"],))

    conn.commit()
    conn.close()

    undo_stack.append(last)

    return redirect("/")


# ================= AUTH =================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        conn = get_db()

        try:

            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (
                    request.form["username"],
                    generate_password_hash(request.form["password"])
                )
            )

            conn.commit()

        except:

            conn.close()
            return "Username already exists"

        conn.close()
        return redirect("/login")


    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (request.form["username"],)
        ).fetchone()

        conn.close()


        if user and check_password_hash(user["password"], request.form["password"]):

            session["user_id"] = user["id"]
            session["username"] = user["username"]

            return redirect("/")


        return "Invalid credentials"


    return render_template("login.html")


@app.route("/logout")
def logout():

    session.clear()
    return redirect("/login")


# ================= PROFILE EDIT =================

@app.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    c = conn.cursor()


    if request.method == "POST":

        img = request.files.get("image")

        filename = None

        if img and img.filename:

            filename = f"user_{session['user_id']}.png"

            path = os.path.join(app.config["UPLOAD_FOLDER"], filename)

            img.save(path)


        c.execute("""
            INSERT OR REPLACE INTO user_profiles
            (user_id, display_name, bio, skills, interests, college, image)

            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (

            session["user_id"],

            request.form["display_name"],
            request.form["bio"],
            request.form["skills"],
            request.form["interests"],
            request.form["college"],

            filename

        ))

        conn.commit()
        conn.close()

        return redirect("/profile")


    profile = c.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    return render_template("edit_profile.html", profile=profile)


# ================= GOAL =================

@app.route("/set_goal", methods=["POST"])
def set_goal():

    conn = get_db()

    conn.execute(
        "UPDATE users SET weekly_goal = ? WHERE id = ?",
        (request.form.get("goal", 0), session["user_id"])
    )

    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/reset_goal")
def reset_goal():

    conn = get_db()

    conn.execute(
        "UPDATE users SET weekly_goal = 0 WHERE id = ?",
        (session["user_id"],)
    )

    conn.commit()
    conn.close()

    return redirect("/")


# ================= RUN =================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)
@app.route("/debug-static")
def debug_static():
    return {
        "cwd": os.getcwd(),
        "base_dir": BASE_DIR,
        "static_exists": os.path.exists(os.path.join(BASE_DIR, "static")),
        "favicon_exists": os.path.exists(os.path.join(BASE_DIR, "static", "favicon.png"))
    }
