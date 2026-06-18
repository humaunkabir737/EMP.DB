import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# পেজ কনফিগারেশন
st.set_page_config(page_title="M/S Jabed Enterprise", layout="wide", initial_sidebar_state="expanded")

# স্টাইল ও সৌন্দর্য বৃদ্ধির CSS
st.markdown("""
<style>
    .main { padding: 0.5rem; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; border-radius: 5px; }
    .stButton>button { width: 100%; border-radius: 3px; font-size: 14px; }
    h1, h2, h3 { color: #10b981; }
</style>
""", unsafe_allow_html=True)

# ডাটাবেজ পাথ
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "jabed_enterprise.db")

# সেশন স্টেট ইনিশিয়ালাইজেশন
if 'page' not in st.session_state: st.session_state.page = "Dashboard"

# সাইডবার নেভিগেশন (ড্রপডাউন মেনু)
with st.sidebar:
    st.header("🏢 Navigation")
    
    # bKash মেনু
    with st.expander("📁 bKash Management"):
        if st.button("💵 Cash Management"): st.session_state.page = "bk_cash"
        if st.button("📉 Expense Management"): st.session_state.page = "bk_exp"
        if st.button("👥 Employee Management"): st.session_state.page = "bk_emp"
    
    # GP মেনু
    with st.expander("📁 GP Management"):
        if st.button("💵 GP Cash"): st.session_state.page = "gp_cash"
        if st.button("📉 GP Expense"): st.session_state.page = "gp_exp"
        if st.button("👥 GP Employees"): st.session_state.page = "gp_emp"

# মেইন লজিক রাউটার
def render_cash_ui(company):
    st.subheader(f"💵 Cash Management - {company}")
    tab1, tab2 = st.tabs(["📝 Entry", "📊 Report"])
    with tab1:
        col1, col2 = st.columns(2)
        with col1: st.info("Cash Receive Entry") # আপনার পুরনো রিসিভ লজিক এখানে বসবে
        with col2: st.info("Pay Out Entry")       # আপনার পুরনো পে-আউট লজিক এখানে বসবে
    with tab2:
        st.write("লেনদেনের রিপোর্ট টেবিল...")

def render_exp_ui(company):
    st.subheader(f"📉 Expense Management - {company}")
    tab1, tab2 = st.tabs(["📝 Entry", "📊 Report"])
    with tab1:
        st.write("খরচ এন্ট্রি ফর্ম...")
    with tab2:
        st.write("খরচের খতিয়ান...")

def render_emp_ui(company):
    st.subheader(f"👥 Employee Management - {company}")
    tab1, tab2, tab3 = st.tabs(["➕ Add New", "📋 View All", "📤 Upload By Excel"])
    with tab1: st.write("নতুন কর্মীর তথ্য...")
    with tab2: st.write("সকল কর্মীর তালিকা...")
    with tab3: st.write("এক্সেল ফাইল আপলোড...")

# পেজ রেন্ডারিং লজিক
if st.session_state.page == "bk_cash": render_cash_ui("bKash")
elif st.session_state.page == "bk_exp": render_exp_ui("bKash")
elif st.session_state.page == "bk_emp": render_emp_ui("bKash")
elif st.session_state.page == "gp_cash": render_cash_ui("GP")
# (বাকি পেজগুলো একইভাবে যুক্ত করুন)
else:
    st.title("Welcome to M/S Jabed Enterprise")
    st.write("সাইডবার মেনু থেকে যেকোনো একটি অপশন সিলেক্ট করুন।")
