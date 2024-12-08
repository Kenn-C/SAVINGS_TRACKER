import streamlit as st
import sqlite3
from datetime import date
import pandas as pd
import plotly.express as px
from streamlit_option_menu import option_menu


st.set_page_config(page_title="Savings Tracker", page_icon="💰", layout="wide")

st.markdown("""
    <style>
        .main {background: linear-gradient(135deg, #f3f4f6, #ffffff);}
        .sidebar .sidebar-content {background-color: #F0F2F6;}
        h1 {color: #4CAF50; text-align: center; font-family: Arial, sans-serif;}
        .footer {position: fixed; bottom: 0; width: 100%; text-align: center; font-size: 12px; color: grey;}
    </style>
""", unsafe_allow_html=True)

conn = sqlite3.connect("savings_tracker.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    goal_name TEXT,
    target_amount REAL,
    achieved_amount REAL DEFAULT 0,
    FOREIGN KEY(user_id) REFERENCES users(id)
)''')

c.execute('''CREATE TABLE IF NOT EXISTS savings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    date DATE,
    amount REAL,
    goal_id INTEGER,
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(goal_id) REFERENCES goals(id)
)''')

try:
    c.execute("SELECT goal_id FROM savings LIMIT 1")
except sqlite3.OperationalError:
    c.execute("ALTER TABLE savings ADD COLUMN goal_id INTEGER")
    conn.commit()


def create_user(username, password):
    try:
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(username, password):
    c.execute("SELECT id FROM users WHERE username = ? AND password = ?", (username, password))
    return c.fetchone()

def add_savings(user_id, amount, goal_id=None):
    today = date.today()
    c.execute("INSERT INTO savings (user_id, date, amount, goal_id) VALUES (?, ?, ?, ?)", 
              (user_id, today, amount, goal_id))
    conn.commit()
    if goal_id:
        update_goal_progress(goal_id, amount)

def get_savings(user_id):
    c.execute("SELECT date, amount, goal_id FROM savings WHERE user_id = ?", (user_id,))
    return c.fetchall()

def create_goal(user_id, goal_name, target_amount):
    c.execute("INSERT INTO goals (user_id, goal_name, target_amount) VALUES (?, ?, ?)", 
              (user_id, goal_name, target_amount))
    conn.commit()

def update_goal_progress(goal_id, amount):
    c.execute("UPDATE goals SET achieved_amount = achieved_amount + ? WHERE id = ?", (amount, goal_id))
    conn.commit()

def get_goals(user_id):
    try:
        c.execute("SELECT id, goal_name, target_amount, achieved_amount FROM goals WHERE user_id = ?", (user_id,))
        return c.fetchall()
    except Exception as e:
        st.error(f"Error fetching goals: {e}")
        return []

st.title("💰 Savings Tracker")

if "user_id" not in st.session_state:
    st.subheader("Welcome! Please Log In or Sign Up")
    
    tabs = st.tabs(["Login", "Sign Up"])
    
    with tabs[0]:
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        if st.button("Login"):
            if username and password:
                with st.spinner("Authenticating..."):
                    user = authenticate_user(username, password)
                if user:
                    st.session_state["user_id"] = user[0]
                    st.session_state["logged_in"] = True 
                    st.success("Logged in successfully!")
                else:
                    st.error("Invalid username or password.")
            else:
                st.error("Please enter both username and password.")

    with tabs[1]:
        new_username = st.text_input("Create Username")
        new_password = st.text_input("Create Password", type="password")
        if st.button("Sign Up"):
            if new_username and new_password:
                with st.spinner("Creating your account..."):
                    success = create_user(new_username, new_password)
                if success:
                    st.success("Account created successfully! You can now log in.")
                    st.session_state["signup_status"] = True  
                else:
                    st.error("Username already exists.")
            else:
                st.error("Please enter both username and password.")

else:
    user_id = st.session_state["user_id"]

    with st.sidebar:
        st.image("https://via.placeholder.com/150", caption="Welcome to Savings Tracker!", use_container_width=True)
        menu = option_menu(
            "Main Menu",
            ["Dashboard", "Add Savings", "Set Goals", "View Goals", "Logout"],
            icons=["house", "piggy-bank", "bullseye", "list-task", "box-arrow-right"],
            menu_icon="cast",
            default_index=0,
        )

    if menu == "Dashboard":
        st.subheader("Your Savings Dashboard")
        savings = get_savings(user_id)
        if savings:
            df = pd.DataFrame(savings, columns=["Date", "Amount", "Goal ID"])
            df["Amount"] = df["Amount"].round(2)

            goals = get_goals(user_id)
            goal_dict = {goal[0]: goal[1] for goal in goals}    
            df["Goal"] = df["Goal ID"].map(goal_dict).fillna("No Goal")
            df = df.drop("Goal ID", axis=1)
            
            st.table(df)
            st.subheader("Savings Trends")
            if not df.empty:
                fig = px.line(df, x="Date", y="Amount", color="Goal", title="Savings Over Time")
                st.plotly_chart(fig)
            else:
                st.info("No data available to display trends.")
        else:
            st.info("No savings data found. Add some entries!")


    elif menu == "Add Savings":
        st.subheader("Add Savings Entry")
        amount = st.number_input("Amount", min_value=0.0, step=0.01)
   
        goals = get_goals(user_id)
        if goals:
            goal_options = {f"{goal[1]} (Target: ${goal[2]})": goal[0] for goal in goals}
            selected_goal = st.selectbox("Select Goal to Allocate Savings", ["None"] + list(goal_options.keys()))
            if selected_goal != "None":
                goal_id = goal_options[selected_goal]
            else:
                goal_id = None
        else:
            st.info("No goals found. Please set a goal first.")
            goal_id = None

        if st.button("Add"):
            if amount > 0:
                add_savings(user_id, amount, goal_id)
                st.success("Savings entry added successfully!")
            else:
                st.error("Please enter a valid amount.")

    elif menu == "Set Goals":
        st.subheader("Set a New Savings Goal")
        goal_name = st.text_input("Goal Name")
        target_amount = st.number_input("Target Amount", min_value=0.0, step=0.01)
        if st.button("Set Goal"):
            if goal_name and target_amount > 0:
                create_goal(user_id, goal_name, target_amount)
                st.success("Goal created successfully!")
            else:
                st.error("Please enter a valid goal name and target amount.")

    elif menu == "View Goals":
        st.subheader("Your Savings Goals")
        try:
            goals = get_goals(user_id)
            if goals:
                df = pd.DataFrame(goals, columns=["ID", "Goal Name", "Target Amount", "Achieved Amount"])
                df["Target Amount"] = df["Target Amount"].round(2)
                df["Achieved Amount"] = df["Achieved Amount"].round(2)
                st.table(df[["Goal Name", "Target Amount", "Achieved Amount"]])
                for _, row in df.iterrows():
                    if row["Target Amount"] > 0:
                        progress = min(int((row["Achieved Amount"] / row["Target Amount"]) * 100), 100)
                        st.write(f"**{row['Goal Name']}**: {progress}% achieved")
                        st.progress(progress)
            else:
                st.info("No goals set yet.")
        except Exception as e:
            st.error(f"Error displaying goals: {e}")

    elif menu == "Logout":
        del st.session_state["user_id"]
        st.success("Logged out successfully!")
        st.rerun()

# Footer
st.markdown('<div class="footer">© 2024 Savings Tracker</div>', unsafe_allow_html=True)

conn.close()
