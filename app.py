# ==============================================================================
# সেকশন ১: ইম্পোর্ট এবং কনফিগারেশন
# ==============================================================================
import streamlit as st
import sqlite3
import pandas as pd
import os

st.set_page_config(page_title="Jabed Enterprise", layout="wide", initial_sidebar_state="expanded")

# ক্লিন ও মিনিমালিস্ট স্টাইল
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 3px; border: 1px solid #ddd; }
    div[data-testid="stExpander"] { border: 1px solid #eee; margin-bottom: 5px; }
    h1, h2, h3 { font-size: 1.2rem; color: #2d3436; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# সেকশন ২: লগইন এবং সেশন কন্ট্রোল
# ==============================================================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False

if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("### 🔐 Login")
        with st.form("login"):
            user = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if user == "admin" and pwd == "jabed2026":
                    st.session_state.logged_in = True
                    st.rerun()
    st.stop()

# ==============================================================================
# সেকশন ৩: কলাপসড সাইডবার মেনু
# ==============================================================================
with st.sidebar:
    st.header("🏢 Navigation")
    if st.button("🚪 Logout"): st.session_state.logged_in = False; st.rerun()
    
    for comp in ["bKash", "GP"]:
        with st.expander(f"📁 {comp} Management"):
            if st.button("💵 Cash", key=f"c_{comp}"): st.session_state.page = "cash"; st.session_state.comp = comp
            if st.button("📉 Expense", key=f"e_{comp}"): st.session_state.page = "exp"; st.session_state.comp = comp
            if st.button("👥 Employee", key=f"m_{comp}"): st.session_state.page = "emp"; st.session_state.comp = comp
            if st.button("👤 2nd Party", key=f"s_{comp}"): st.session_state.page = "sp"; st.session_state.comp = comp

# ==============================================================================
# সেকশন ৪: ক্যাশ ম্যানেজমেন্ট (পাশাপাশি লেআউট)
# ==============================================================================
comp = st.session_state.get('comp', 'bKash')
if st.session_state.get('page') == "cash":
    st.header(f"💵 Cash Management - {comp}")
    t1, t2 = st.tabs(["📝 Entry", "📊 Report"])
    with t1:
        c1, c2 = st.columns(2)
        with c1: st.write("### Cash Receive"); # আপনার রিসিভ লজিক এখানে বসবে
        with c2: st.write("### Pay Out"); # আপনার পে-আউট লজিক এখানে বসবে
    with t2: st.write("Report view...")

# ==============================================================================
# সেকশন ৫: এক্সপেন্স ম্যানেজমেন্ট
# ==============================================================================
elif st.session_state.get('page') == "exp":
    st.header(f"📉 Expense Management - {comp}")
    t1, t2 = st.tabs(["📝 Manual Entry", "📤 Excel Upload"])
    with t1: st.write("Expense form...")
    with t2: st.write("Excel upload...")

# ==============================================================================
# সেকশন ৬: এমপ্লয়ি ম্যানেজমেন্ট (সব ফিল্ডসহ)
# ==============================================================================
elif st.session_state.get('page') == "emp":
    st.header(f"👥 Employee Management - {comp}")
    t1, t2, t3 = st.tabs(["➕ Add New", "📋 View All", "📤 Excel"])
    with t1:
        # আপনার এমপ্লয়ি এন্ট্রি ফর্মের সব ফিল্ড এখানে বসবে
        st.text_input("Name"); st.text_input("NID"); st.number_input("Salary")
    with t2: st.write("Employee List...")
    with t3: st.write("Excel upload...")

# ==============================================================================
# সেকশন ৭: সেকেন্ড পার্টি ম্যানেজমেন্ট
# ==============================================================================
elif st.session_state.get('page') == "sp":
    st.header(f"👤 Second Party Management - {comp}")
    # লজিক এখানে...
