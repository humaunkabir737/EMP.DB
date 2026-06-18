import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

# Page Configuration
st.set_page_config(page_title="M/S Jabed Enterprise", layout="wide", initial_sidebar_state="expanded")

# Minimalist Style
st.markdown("""
<style>
    .stButton>button { width: 100%; border-radius: 3px; height: 35px; }
    div[data-testid="stExpander"] { border: 1px solid #ddd; }
    h1, h2, h3 { color: #10b981; }
</style>
""", unsafe_allow_html=True)

# Database Setup (Attachment 3 লজিক)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "jabed_enterprise.db")

# Session State
if 'page' not in st.session_state: st.session_state.page = "Dashboard"
if 'current_company' not in st.session_state: st.session_state.current_company = "bKash"

# সাইডবার ড্রপডাউন মেনু
with st.sidebar:
    st.header("🏢 Navigation")
    
    for comp in ["bKash", "GP"]:
        with st.expander(f"📁 {comp} Management"):
            if st.button(f"💵 Cash Management", key=f"c_{comp}"): 
                st.session_state.page = "cash"; st.session_state.current_company = comp
            if st.button(f"📉 Expense Management", key=f"e_{comp}"): 
                st.session_state.page = "exp"; st.session_state.current_company = comp
            if st.button(f"👥 Employee Management", key=f"m_{comp}"): 
                st.session_state.page = "emp"; st.session_state.current_company = comp
            if st.button(f"👤 Second Party Mgt", key=f"s_{comp}"): 
                st.session_state.page = "sp"; st.session_state.current_company = comp

# লজিক রাউটার
comp = st.session_state.current_company

if st.session_state.page == "cash":
    st.header(f"💵 Cash Management - {comp}")
    tab1, tab2 = st.tabs(["📝 Entry", "📊 Report"])
    with tab1:
        # পাশাপাশি লেআউট (Attachment 1 ও 2 এর স্টাইল)
        c1, c2 = st.columns(2)
        with c1: st.write("### Cash Receive (জমা)") 
        with c2: st.write("### Pay Out (খরচ/প্রদান)")
    with tab2: st.write("ক্যাশ রিপোর্ট ও খতিয়ান...")

elif st.session_state.page == "exp":
    st.header(f"📉 Expense Management - {comp}")
    tab1, tab2 = st.tabs(["📝 Entry", "📊 Report"])
    with tab1: st.write("খরচ এন্ট্রি ও এক্সেল আপলোড...")
    with tab2: st.write("খরচের খতিয়ান...")

elif st.session_state.page == "emp":
    st.header(f"👥 Employee Management - {comp}")
    tab1, tab2, tab3 = st.tabs(["➕ Add New", "📋 View All", "📤 Upload By Excel"])
    with tab1: st.write("নতুন কর্মীর ফর্ম...")
    with tab2: st.write("কর্মীদের প্রোফাইল...")
    with tab3: st.write("এক্সেল আপলোড...")

elif st.session_state.page == "sp":
    st.header(f"👤 Second Party Management - {comp}")
    tab1, tab2 = st.tabs(["➕ Add Party", "📋 List & Edit"])
    with tab1: st.write("নতুন সেকেন্ড পার্টি যুক্ত করুন...")
    with tab2: st.write("পার্টি লিস্ট ও ম্যানেজ করুন...")

else:
    st.title("Welcome to M/S Jabed Enterprise")
    st.info("বাম পাশের মেনু থেকে কোম্পানি সিলেক্ট করে কাজ শুরু করুন।")
