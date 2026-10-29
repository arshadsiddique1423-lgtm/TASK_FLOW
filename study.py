
import streamlit as st
import sqlite3
import csv
import io
import time
from datetime import date, datetime, timedelta
from pathlib import Path

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="TaskFlow | Study Planner",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

DB_PATH = Path(__file__).with_name("taskflow.db")

CATEGORIES = [
    "Study", "Assignment", "Exam Preparation",
    "Project", "Personal", "Other"
]
PRIORITIES = ["High", "Medium", "Low"]

# ==================================================
# DARK UI
# ==================================================
st.markdown("""
<style>
/* Base page */
.stApp {
    background: #0b1020;
    color: #e5e7eb;
}
[data-testid="stMainBlockContainer"] {
    padding-top: 1rem;
    max-width: 1450px;
}
h1, h2, h3, h4 { color: #f8fafc !important; }
p, label, .stMarkdown { color: #d0d8e8; }

/* Remove Streamlit's top decoration/header line */
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
[data-testid="stHeader"],
header[data-testid="stHeader"] {
    border: 0 !important;
    outline: 0 !important;
    box-shadow: none !important;
    background: #0b1020 !important;
}
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
section.main,
.main {
    border-top: 0 !important;
    box-shadow: none !important;
}
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: #10182a;
    border-right: 1px solid #293650;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #141f33;
    border: 1px solid #293650;
    padding: 18px;
    border-radius: 15px;
}
[data-testid="stMetricValue"] { color: #ffffff; }
[data-testid="stMetricLabel"] { color: #a8b7d0; }
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #111b2d;
    border-color: #293650;
    border-radius: 14px;
}

/* App buttons */
.stButton button, .stDownloadButton button {
    border-radius: 10px;
    min-height: 40px;
    font-weight: 600;
}
.stButton button[kind="primary"] {
    background: #6366f1;
    border: none;
    color: white;
}
.stButton button:hover, .stDownloadButton button:hover {
    border-color: #818cf8;
    color: #c7d2fe;
}
[data-baseweb="select"] > div {
    background: #172238;
    border-color: #34445e;
}
input, textarea { border-radius: 8px !important; }
hr { border-color: #293650; }

/* Hero card: no border */
.hero {
    background: linear-gradient(120deg, #172554, #172033, #312e81);
    padding: 25px;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    border-radius: 18px;
    margin-bottom: 22px;
}
.hero p { color: #cbd5e1; }
.small-note { color: #93a4bd; font-size: 13px; }

/* Circular Streamlit sidebar and toolbar controls only */
[data-testid="stSidebarCollapseButton"] button,
[data-testid="stSidebarExpandButton"] button,
[data-testid="stToolbar"] button,
[data-testid="stHeader"] button {
    width: 38px !important;
    height: 38px !important;
    min-width: 38px !important;
    min-height: 38px !important;
    padding: 0 !important;
    border-radius: 50% !important;
    border: 1px solid #34445e !important;
    background: #172238 !important;
    color: #e5e7eb !important;
    box-shadow: none !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
}
[data-testid="stSidebarCollapseButton"] button:hover,
[data-testid="stSidebarExpandButton"] button:hover,
[data-testid="stToolbar"] button:hover,
[data-testid="stHeader"] button:hover {
    background: #293650 !important;
    border-color: #818cf8 !important;
    color: #ffffff !important;
}
</style>
""", unsafe_allow_html=True)


# ==================================================
# DATABASE
# ==================================================
def connect_db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    # Create the table first, including status for new installations.
    with connect_db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                due TEXT,
                done INTEGER NOT NULL DEFAULT 0,
                created TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending'
            )
        """)

        # Add status safely to databases created by older versions.
        columns = [
            row["name"]
            for row in con.execute("PRAGMA table_info(tasks)").fetchall()
        ]
        if "status" not in columns:
            con.execute(
                "ALTER TABLE tasks ADD COLUMN status TEXT NOT NULL DEFAULT 'Pending'"
            )

        con.execute("""
            UPDATE tasks
            SET status = CASE WHEN done = 1 THEN 'Done' ELSE 'Pending' END
            WHERE status IS NULL OR status = ''
        """)


def get_tasks():
    with connect_db() as con:
        rows = con.execute(
            "SELECT * FROM tasks ORDER BY created DESC, id DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def add_task(name, category, priority, due):
    with connect_db() as con:
        con.execute("""
            INSERT INTO tasks (name, category, priority, due, done, created)
            VALUES (?, ?, ?, ?, 0, ?)
        """, (
            name, category, priority, due,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))


def update_task(task_id, name, category, priority, due, done):
    with connect_db() as con:
        con.execute("""
            UPDATE tasks
            SET name=?, category=?, priority=?, due=?, done=?
            WHERE id=?
        """, (
            name, category, priority, due,
            int(done), task_id
        ))



def set_completed(task_id, done):
    status = "Done" if done else "Pending"

    with connect_db() as con:
        con.execute(
            "UPDATE tasks SET done=?, status=? WHERE id=?",
            (int(done), status, task_id)
        )


def set_task_status(task_id, status):
    with connect_db() as con:
        con.execute(
            "UPDATE tasks SET status=?, done=? WHERE id=?",
            (
                status,
                1 if status == "Done" else 0,
                task_id
            )
        )


def delete_task(task_id):
    with connect_db() as con:
        con.execute("DELETE FROM tasks WHERE id=?", (task_id,))


def clear_completed():
    with connect_db() as con:
        con.execute("DELETE FROM tasks WHERE done=1")


init_db()


# ==================================================
# HELPERS
# ==================================================
def overdue(task):
    return (
        not task["done"]
        and bool(task["due"])
        and date.fromisoformat(task["due"]) < date.today()
    )


def due_today(task):
    return (
        not task["done"]
        and task["due"] == date.today().isoformat()
    )


def priority_rank(task):
    return {"High": 0, "Medium": 1, "Low": 2}.get(
        task["priority"], 3
    )


def export_csv(tasks):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Task ID", "Task", "Category", "Priority",
        "Due Date", "Status", "Created"
    ])

    for task in tasks:
        writer.writerow([
            task["id"],
            task["name"],
            task["category"],
            task["priority"],
            task["due"] or "Not set",
            task.get("status", "Done" if task["done"] else "Pending"),
            task["created"]
        ])

    return output.getvalue().encode("utf-8-sig")


# ==================================================
# SESSION STATE
# ==================================================
if "focus_running" not in st.session_state:
    st.session_state.focus_running = False

if "focus_end" not in st.session_state:
    st.session_state.focus_end = 0.0

if "focus_duration" not in st.session_state:
    st.session_state.focus_duration = 25

if "focus_mode" not in st.session_state:
    st.session_state.focus_mode = "Study"


def go_to_all_tasks():
    # Called before Streamlit reruns the page, so changing the radio state is safe.
    st.session_state["page"] = "All Tasks"


# ==================================================
# SIDEBAR
# ==================================================
tasks = get_tasks()

with st.sidebar:
    st.markdown("## 🎯 TaskFlow")
    st.caption("Your personal study workspace")
    st.divider()

    # Use a session-state key so dashboard quick links can change the page.
    if "page" not in st.session_state:
        st.session_state["page"] = st.session_state.get(
            "navigation_page", "Dashboard"
        )

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "All Tasks",
            "Calendar & Deadlines",
            "Focus Timer",
            "Analytics",
            "Settings"
        ],
        key="page",
        label_visibility="collapsed"
    )

    st.divider()
    st.markdown("### Quick Stats")
    st.metric("Total Tasks", len(tasks))
    st.metric("Completed", sum(t["done"] for t in tasks))
    st.metric("Overdue", sum(overdue(t) for t in tasks))

    st.caption("Small steps. Consistent progress.")


# ==================================================
# HEADER + GLOBAL STATS
# ==================================================
st.markdown("""
<div class="hero">
    <h1>🎯 TaskFlow</h1>
    <p>Plan your study day, track your progress, and focus on what matters.</p>
</div>
""", unsafe_allow_html=True)

st.caption(
    "📅 " + date.today().strftime("%A, %d %B %Y")
)

tasks = get_tasks()
total = len(tasks)
completed = sum(t["done"] for t in tasks)
pending = total - completed
late = sum(overdue(t) for t in tasks)
today_count = sum(due_today(t) for t in tasks)
progress = completed / total if total else 0


# ==================================================
# DASHBOARD
# ==================================================
if page == "Dashboard":

    st.subheader("Your Overview")

    a, b, c, d = st.columns(4)
    a.metric("📚 Total Tasks", total)
    b.metric("✅ Completed", completed)
    c.metric("⏳ Pending", pending)
    d.metric("⚠️ Overdue", late)

    st.markdown("### Overall Progress")
    st.progress(progress)
    st.caption(f"{progress * 100:.0f}% of your tasks completed")

    st.divider()

    left, right = st.columns([1.1, 1])

    with left:
        st.markdown("### ➕ Add a New Task")

        with st.form("new_task", clear_on_submit=True):
            name = st.text_input(
                "Task name",
                placeholder="e.g. Revise Human Anatomy"
            )
            category = st.selectbox("Category", CATEGORIES)
            priority = st.selectbox("Priority", PRIORITIES)

            has_due = st.checkbox("Set a deadline")
            due_date = st.date_input(
                "Due date",
                value=date.today(),
                min_value=date.today(),
                disabled=not has_due
            )

            submit = st.form_submit_button(
                "＋ Add Task",
                type="primary",
                use_container_width=True
            )

            if submit:
                if name.strip():
                    add_task(
                        name.strip(),
                        category,
                        priority,
                        due_date.isoformat() if has_due else None
                    )
                    st.success("Task saved to your database!")
                    st.rerun()
                else:
                    st.warning("Please enter a task name.")

    with right:
        st.markdown("### 📌 Today's Focus")

        if late:
            st.error(
                f"You have {late} overdue task(s). "
                "Review their deadlines."
            )
        elif today_count:
            st.info(f"You have {today_count} task(s) due today.")
        elif pending:
            st.info("Choose a pending task and start working.")
        else:
            st.success("All clear! Enjoy your progress 🎉")

        high = [
            t for t in tasks
            if not t["done"] and t["priority"] == "High"
        ]

        st.markdown("#### 🔥 High Priority Tasks")
        if high:
            for task in high[:5]:
                st.write(f"• {task['name']}")
        else:
            st.caption("No pending high-priority tasks.")

        st.markdown("#### ⚡ Quick Actions")
        st.button(
            "Open All Tasks",
            use_container_width=True,
            on_click=go_to_all_tasks
        )

    st.divider()
    st.markdown("### 📝 Recent Tasks")

    if not tasks:
        st.info("Your task list is empty. Add your first task above.")
    else:
        for task in tasks[:5]:
            with st.container(border=True):
                left, right = st.columns([3, 1])

                with left:
                    st.markdown(f"**{task['name']}**")
                    st.caption(
                    f"{task['category']} · {task['priority']} priority"
                    )

                    current_status = task.get("status", "Pending")

                    if current_status == "Done":
                        st.success("✓ DONE")
                    elif current_status == "Fail":
                        st.error("✕ FAILED")
                    elif overdue(task):
                        st.warning(f"⚠ Overdue · {task['due']}")
                    elif task["due"]:
                        st.caption(f"📅 Due: {task['due']}")
                    else:
                        st.caption("Pending")

                with right:
                    if st.button(
                        "✓ DONE",
                        key=f"recent_done_{task['id']}",
                        type="primary",
                        use_container_width=True
                    ):
                        set_task_status(task["id"], "Done")
                        st.rerun()
    
                    if st.button(
                        "✕ FAIL",
                        key=f"recent_fail_{task['id']}",
                        use_container_width=True
                    ):
                        set_task_status(task["id"], "Fail")
                        st.rerun()



# ==================================================
# ALL TASKS
# ==================================================
elif page == "All Tasks":

    st.subheader("📋 Manage Your Tasks")

    search = st.text_input(
        "🔎 Search",
        placeholder="Find a task by name..."
    )

    f1, f2, f3 = st.columns(3)

    status = f1.selectbox(
        "Status",
        ["All", "Pending", "Completed", "Failed", "Overdue", "Due Today"]
    )
    priority_filter = f2.selectbox(
        "Priority", ["All"] + PRIORITIES
    )
    category_filter = f3.selectbox(
        "Category", ["All"] + CATEGORIES
    )

    sort = st.selectbox(
        "Sort tasks",
        ["Newest First", "Deadline", "Highest Priority", "Alphabetical"]
    )

    filtered = []

    for task in tasks:
        if search.lower() not in task["name"].lower():
            continue
        if priority_filter != "All" and task["priority"] != priority_filter:
            continue
        if category_filter != "All" and task["category"] != category_filter:
            continue
        if status == "Pending" and task["done"]:
            continue
        if status == "Completed" and not task["done"]:
            continue
        if status == "Failed" and task.get("status") != "Fail":
            continue
        if status == "Pending" and task.get("status", "Pending") != "Pending":
            continue
        if status == "Overdue" and not overdue(task):
            continue
        if status == "Due Today" and not due_today(task):
            continue

        filtered.append(task)

    if sort == "Deadline":
        filtered.sort(key=lambda t: t["due"] or "9999-12-31")
    elif sort == "Highest Priority":
        filtered.sort(key=priority_rank)
    elif sort == "Alphabetical":
        filtered.sort(key=lambda t: t["name"].lower())
    else:
        filtered.sort(key=lambda t: t["created"], reverse=True)

    st.caption(f"{len(filtered)} matching task(s)")

    if not filtered:
        st.info("No matching tasks found.")
    else:
        for task in filtered:
            with st.container(border=True):
                c1, c2, c3 = st.columns([4, 1, 1])

                with c1:
                    checked = st.checkbox(
                        task["name"],
                        value=bool(task["done"]),
                        key=f"list_{task['id']}"
                    )
                    if checked != bool(task["done"]):
                        set_completed(task["id"], checked)
                        st.rerun()

                    st.caption(
                        f"{task['category']} · "
                        f"{task['priority']} priority"
                    )

                    if task["done"]:
                        st.success("Completed")
                    elif task.get("status") == "Fail":
                        st.error("✕ Failed")
                    elif overdue(task):
                        st.error(f"Overdue · Due {task['due']}")
                    elif task["due"]:
                        st.caption(f"📅 Due: {task['due']}")

                with c2:
                    if st.button("✏️ Edit", key=f"edit_{task['id']}"):
                        st.session_state["editing_id"] = task["id"]

                with c3:
                    if st.button("🗑️ Delete", key=f"delete_{task['id']}"):
                        delete_task(task["id"])
                        st.rerun()

            if st.session_state.get("editing_id") == task["id"]:
                with st.form(f"edit_form_{task['id']}"):
                    edited_name = st.text_input(
                        "Task name", value=task["name"]
                    )

                    edited_category = st.selectbox(
                        "Category",
                        CATEGORIES,
                        index=CATEGORIES.index(task["category"])
                    )

                    edited_priority = st.selectbox(
                        "Priority",
                        PRIORITIES,
                        index=PRIORITIES.index(task["priority"])
                    )

                    has_due = st.checkbox(
                        "Set deadline",
                        value=bool(task["due"])
                    )

                    original_due = (
                        date.fromisoformat(task["due"])
                        if task["due"] else date.today()
                    )

                    edited_due = st.date_input(
                        "Deadline",
                        value=original_due,
                        disabled=not has_due
                    )

                    save = st.form_submit_button("Save Changes")

                    if save:
                        if edited_name.strip():
                            update_task(
                                task["id"],
                                edited_name.strip(),
                                edited_category,
                                edited_priority,
                                edited_due.isoformat() if has_due else None,
                                task["done"]
                            )
                            del st.session_state["editing_id"]
                            st.rerun()
                        else:
                            st.error("Task name cannot be empty.")

    st.divider()

    x, y = st.columns(2)

    with x:
        st.download_button(
            "⬇️ Export CSV",
            data=export_csv(tasks),
            file_name="taskflow_tasks.csv",
            mime="text/csv",
            use_container_width=True
        )

    with y:
        if st.button("🧹 Clear Completed", use_container_width=True):
            clear_completed()
            st.rerun()


# ==================================================
# CALENDAR & DEADLINES
# ==================================================
elif page == "Calendar & Deadlines":

    st.subheader("📅 Deadlines & Schedule")

    today = date.today()
    end_date = today + timedelta(days=7)

    today_tasks = [t for t in tasks if due_today(t)]
    upcoming = [
        t for t in tasks
        if not t["done"]
        and t["due"]
        and today < date.fromisoformat(t["due"]) <= end_date
    ]
    overdue_tasks = [t for t in tasks if overdue(t)]

    a, b, c = st.columns(3)
    a.metric("Due Today", len(today_tasks))
    b.metric("Next 7 Days", len(upcoming))
    c.metric("Overdue", len(overdue_tasks))

    sections = [
        ("⚠️ Overdue", overdue_tasks),
        ("🔥 Due Today", today_tasks),
        ("📆 Upcoming 7 Days", sorted(
            upcoming, key=lambda t: t["due"]
        ))
    ]

    for heading, section_tasks in sections:
        st.markdown(f"### {heading}")

        if not section_tasks:
            st.caption("Nothing to show here.")
            continue

        for task in section_tasks:
            with st.container(border=True):
                x, y = st.columns([4, 1])
                x.markdown(f"**{task['name']}**")
                x.caption(
                    f"{task['due']} · {task['category']} · "
                    f"{task['priority']} priority"
                )

                checked = y.checkbox(
                    "Done",
                    value=bool(task["done"]),
                    key=f"deadline_{task['id']}"
                )
                if checked != bool(task["done"]):
                    set_completed(task["id"], checked)
                    st.rerun()

    st.caption(
        "Deadlines are displayed from the dates assigned to your tasks."
    )


# ==================================================
# FOCUS TIMER
# ==================================================
elif page == "Focus Timer":

    st.subheader("⏱️ Pomodoro Focus Timer")
    st.write(
        "Study with focus, then take a short break. "
        "Keep this page open during your session."
    )

    mode = st.radio(
        "Session type",
        ["Study", "Short Break"],
        horizontal=True,
        key="focus_mode"
    )

    default_minutes = 25 if mode == "Study" else 5

    if not st.session_state.focus_running:
        minutes = st.select_slider(
            "Duration in minutes",
            options=[5, 10, 15, 20, 25, 30, 45, 60],
            value=default_minutes
        )
        st.session_state.focus_duration = minutes

    if st.session_state.focus_running:
        remaining = max(
            0, int(st.session_state.focus_end - time.time())
        )
    else:
        remaining = st.session_state.focus_duration * 60

    mm, ss = divmod(remaining, 60)

    st.markdown(
        f"<div style='text-align:center;padding:30px;"
        f"background:#141f33;border:1px solid #293650;"
        f"border-radius:20px;'>"
        f"<div style='font-size:64px;font-weight:750;color:#a5b4fc;'>"
        f"{mm:02d}:{ss:02d}</div>"
        f"<div style='font-size:18px;color:#cbd5e1;'>"
        f"{'Focus Session' if mode == 'Study' else 'Break Time'}"
        f"</div></div>",
        unsafe_allow_html=True
    )

    st.write("")

    x, y = st.columns(2)

    with x:
        if not st.session_state.focus_running:
            if st.button("▶ Start Timer", type="primary",
                         use_container_width=True):
                st.session_state.focus_end = (
                    time.time() + st.session_state.focus_duration * 60
                )
                st.session_state.focus_running = True
                st.rerun()
        else:
            if st.button("⏸ Pause / Reset", use_container_width=True):
                st.session_state.focus_running = False
                st.session_state.focus_duration = default_minutes
                st.rerun()

    with y:
        if st.button("↻ Reset Timer", use_container_width=True):
            st.session_state.focus_running = False
            st.session_state.focus_duration = default_minutes
            st.rerun()

    if st.session_state.focus_running:
        if remaining <= 0:
            st.session_state.focus_running = False
            st.success("Session complete! Take a break or start again.")
            st.rerun()
        else:
            st.info(
                "Timer is running. Click below to refresh the countdown."
            )
            if st.button("Refresh Countdown"):
                st.rerun()

    st.caption(
        "Note: The timer uses browser-triggered reruns, "
        "not a guaranteed background notification. "
        "Keep the app open and refresh the countdown to update it."
    )


# ==================================================
# ANALYTICS
# ==================================================

elif page == "Analytics":

    st.subheader("📊 Your Productivity")

    tasks = get_tasks()
    total = len(tasks)
    completed = sum(1 for t in tasks if t["done"])
    pending = total - completed
    late = sum(1 for t in tasks if overdue(t))

    # Main productivity metrics
    a, b, c = st.columns(3)

    a.metric(
        "Completion Rate",
        f"{completed / total * 100:.1f}%" if total else "0%"
    )
    b.metric("Completed", completed)
    c.metric("Overdue", late)

    st.markdown("### Tasks by Status")

    status_data = {
        "Completed": completed,
        "Pending": pending,
        "Overdue": late
    }

    for label, count in status_data.items():
        st.write(f"**{label}:** {count} task(s)")

    st.markdown("### Pending Tasks by Priority")

    priority_data = {
        level: sum(
            1 for t in tasks
            if not t["done"] and t["priority"] == level
        )
        for level in PRIORITIES
    }

    for level, count in priority_data.items():
        st.write(f"**{level}:** {count} task(s)")

    st.markdown("### Tasks by Category")

    category_data = {
        category: sum(
            1 for t in tasks
            if t["category"] == category
        )
        for category in CATEGORIES
    }

    for category, count in category_data.items():
        st.write(f"**{category}:** {count} task(s)")

    if not tasks:
        st.info("Add tasks to generate analytics.")



# ==================================================
# SETTINGS
# ==================================================
elif page == "Settings":

    st.subheader("⚙️ Settings & Data")

    st.markdown("### Database")
    st.write(f"Local database file: `{DB_PATH.name}`")
    st.caption(
        "Keep a backup of this file if you run TaskFlow locally. "
        "It contains your saved task records."
    )

    st.markdown("### Export Backup")
    st.download_button(
        "⬇️ Download All Tasks",
        data=export_csv(tasks),
        file_name=f"taskflow_backup_{date.today().isoformat()}.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.divider()
    st.markdown("### Danger Zone")

    confirm = st.checkbox("I understand this deletes all my tasks.")

    if st.button("Delete All Tasks", disabled=not confirm):
        with connect_db() as con:
            con.execute("DELETE FROM tasks")
        st.session_state.pop("editing_id", None)
        st.success("All tasks have been deleted.")
        st.rerun()


# ==================================================
# FOOTER
# ==================================================
st.divider()

st.markdown(
    "<p style='text-align:center;color:#8292ac;font-size:13px;'>"
    "TaskFlow · Build better habits, one task at a time."
    "</p>",
    unsafe_allow_html=True
)
