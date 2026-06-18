import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
from PIL import Image

# পেজ কনফিগারেশন
st.set_page_config(page_title="M/S Jabed Enterprise", layout="wide", initial_sidebar_state="expanded")

# স্টাইল
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 3px; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; }
</style>
""", unsafe_allow_html=True)

# ডাটাবেজ পাথ (Attachment 3 লজিক)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "jabed_enterprise.db")

# সেশন স্টেট
if 'page' not in st.session_state: st.session_state.page = "Dashboard"
if 'current_company' not in st.session_state: st.session_state.current_company = "bKash"

# মেনু স্ট্রাকচার
with st.sidebar:
    st.header("🏢 Navigation")
    
    # bKash
    with st.expander("📁 bKash Management"):
        if st.button("💵 Cash Management"): st.session_state.page = "cash"; st.session_state.current_company = "bKash"
        if st.button("📉 Expense Management"): st.session_state.page = "exp"; st.session_state.current_company = "bKash"
        if st.button("👥 Employee Management"): st.session_state.page = "emp"; st.session_state.current_company = "bKash"
    
    # GP
    with st.expander("📁 GP Management"):
        if st.button("💵 Cash Management", key="gp_cash"): st.session_state.page = "cash"; st.session_state.current_company = "GP"
        if st.button("📉 Expense Management", key="gp_exp"): st.session_state.page = "exp"; st.session_state.current_company = "GP"
        if st.button("👥 Employee Management", key="gp_emp"): st.session_state.page = "emp"; st.session_state.current_company = "GP"

# লজিক রাউটার
comp = st.session_state.current_company

if st.session_state.page == "cash":
    st.header(f"💵 Cash Management - {comp}")
    tab1, tab2 = st.tabs(["📝 Entry", "📊 Report"])
    with tab1:
        # এখানে Attachment 3 এর ক্যাশ এন্ট্রি ফর্ম কোড বসবে (পাশে পাশাপাশি কলামসহ)
        col1, col2 = st.columns(2)
        with col1: st.write("### Cash Receive")
        with col2: st.write("### Pay Out")
    with tab2: st.write("ক্যাশ রিপোর্ট...")

elif st.session_state.page == "exp":
    st.header(f"📉 Expense Management - {comp}")
    tab1, tab2 = st.tabs(["📝 Entry", "📊 Report"])
    with tab1: st.write("খরচ এন্ট্রি...")
    with tab2: st.write("খরচ রিপোর্ট...")

elif st.session_state.page == "emp":
    st.header(f"👥 Employee Management - {comp}")
    # আপনার চাহিদা অনুযায়ী আলাদা ট্যাব
    tab1, tab2, tab3 = st.tabs(["➕ Add New", "📋 View All", "📤 Upload By Excel"])
    with tab1: st.write("নতুন কর্মী যুক্ত করার ফর্ম...")
    with tab2: st.write("কর্মীদের তালিকা...")
    with tab3: st.write("এক্সেল আপলোডের জায়গা...")

else:
    st.title("Welcome to M/S Jabed Enterprise")
