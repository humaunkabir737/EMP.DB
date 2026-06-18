# ==============================================================================
# সেকশন ১: ইম্পোর্ট এবং কনফিগারেশন
# ==============================================================================
import streamlit as st
import sqlite3
import pandas as pd
import os

st.set_page_config(page_title="M/S Jabed Enterprise", layout="wide", initial_sidebar_state="expanded")

# ডাটাবেজ পাথ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "jabed_enterprise.db")

# ==============================================================================
# সেকশন ২: লগইন সিস্টেম (আপনার Attachment 3 থেকে হুবহু)
# ==============================================================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = None

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<h3 style='text-align: center;'>🔐 M/S JABED ENTERPRISE</h3>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if username == "admin" and password == "jabed2026":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.rerun()
                # অন্যান্য ইউজার লজিক এখানে যুক্ত হবে...
                else: st.error("Invalid Username or Password!")
    st.stop()

# ==============================================================================
# সেকশন ৩: সাইডবার নেভিগেশন (ড্রপডাউন)
# ==============================================================================
with st.sidebar:
    st.header("🏢 Navigation")
    for comp in ["bKash", "GP"]:
        with st.expander(f"📁 {comp} Management"):
            if st.button(f"💵 Cash", key=f"c_{comp}"): st.session_state.page = "cash"; st.session_state.company = comp
            if st.button(f"📉 Expense", key=f"e_{comp}"): st.session_state.page = "exp"; st.session_state.company = comp
            if st.button(f"👥 Employee", key=f"m_{comp}"): st.session_state.page = "emp"; st.session_state.company = comp
            if st.button(f"👤 Second Party", key=f"s_{comp}"): st.session_state.page = "sp"; st.session_state.company = comp

# ==============================================================================
# সেকশন ৪: রাউটার ও মডিউল লজিক
# ==============================================================================
comp = st.session_state.get('company', 'bKash')

if st.session_state.page == "cash":
    st.header(f"💵 Cash Management - {comp}")
    tab1, tab2 = st.tabs(["📝 Entry", "📊 Report"])
    with tab1:
        c1, c2 = st.columns(2)
        with c1: st.subheader("Cash Receive") # Attachment 3 এর লজিক
        with c2: st.subheader("Pay Out")       # Attachment 3 এর লজিক
    with tab2: st.write("ক্যাশ রিপোর্ট...")

elif st.session_state.page == "exp":
    st.header(f"📉 Expense Management - {comp}")
    tab1, tab2 = st.tabs(["📝 Entry", "📊 Report"])
    with tab1: st.write("Expense Entry...")
    with tab2: st.write("Expense Report...")

elif st.session_state.page == "emp":
    st.header(f"👥 Employee Management - {comp}")
    tab1, tab2, tab3 = st.tabs(["➕ Add New", "📋 View All", "📤 Upload"])
    with tab1: st.write("Add...")
    with tab2: st.write("List...")
    with tab3: st.write("Upload...")

elif st.session_state.page == "sp":
    st.header(f"👤 Second Party Management - {comp}")
    tab1, tab2 = st.tabs(["➕ Add", "📋 List"])
    with tab1: st.write("Add Party...")
    with tab2: st.write("List...")

else:
    st.title("Dashboard")
