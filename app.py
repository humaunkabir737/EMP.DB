# ==============================================================================
# সেকশন ১: ইম্পোর্ট এবং পেজ কনফিগারেশন
# ==============================================================================
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os

st.set_page_config(page_title="M/S Jabed Enterprise", layout="wide", initial_sidebar_state="expanded")

# ==============================================================================
# সেকশন ২: ডাটাবেজ এবং লগইন সিস্টেম (Attachment 3 এর ভিত্তি)
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "jabed_enterprise.db")

# আপনার লগইন লজিক এখানে যুক্ত করুন (Attachment 3 থেকে কপি করে)
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'page' not in st.session_state: st.session_state.page = "Dashboard"

# ==============================================================================
# সেকশন ৩: সাইডবার ড্রপডাউন মেনু
# ==============================================================================
with st.sidebar:
    st.header("🏢 Navigation")
    
    # bKash এবং GP ফোল্ডার
    for comp in ["bKash", "GP"]:
        with st.expander(f"📁 {comp} Management"):
            if st.button(f"💵 Cash", key=f"c_{comp}"): 
                st.session_state.page = "cash"; st.session_state.current_company = comp
            if st.button(f"📉 Expense", key=f"e_{comp}"): 
                st.session_state.page = "exp"; st.session_state.current_company = comp
            if st.button(f"👥 Employees", key=f"m_{comp}"): 
                st.session_state.page = "emp"; st.session_state.current_company = comp
            if st.button(f"👤 Second Party", key=f"s_{comp}"): 
                st.session_state.page = "sp"; st.session_state.current_company = comp

# ==============================================================================
# সেকশন ৪: রাউটার লজিক (মূল ফাংশন)
# ==============================================================================
comp = st.session_state.get('current_company', 'bKash')

if st.session_state.page == "cash":
    st.header(f"💵 Cash Management - {comp}")
    tab1, tab2 = st.tabs(["📝 Entry", "📊 Report"])
    with tab1:
        c1, c2 = st.columns(2)
        with c1: st.write("### Cash Receive") # এখানে আপনার রিসিভ লজিক বসবে
        with c2: st.write("### Pay Out")      # এখানে আপনার পে-আউট লজিক বসবে
    with tab2:
        st.write("📊 Cash Report content here.") # খালি না রেখে একটি টেক্সট দেওয়া হলো

elif st.session_state.page == "exp":
    st.header(f"📉 Expense Management - {comp}")
    tab1, tab2 = st.tabs(["📝 Entry", "📊 Report"])
    with tab1:
        st.write("Expense Entry Form.") # খালি না রেখে টেক্সট দেওয়া হলো
    with tab2:
        st.write("Expense Report content here.")

elif st.session_state.page == "emp":
    st.header(f"👥 Employee Management - {comp}")
    tab1, tab2, tab3 = st.tabs(["➕ Add New", "📋 View All", "📤 Upload"])
    with tab1: st.write("Add form.")
    with tab2: st.write("View list.")
    with tab3: st.write("Upload logic.")

elif st.session_state.page == "sp":
    st.header(f"👤 Second Party Management - {comp}")
    tab1, tab2 = st.tabs(["➕ Add", "📋 List"])
    with tab1: st.write("Add party form.")
    with tab2: st.write("Party list.")

else:
    st.title("M/S Jabed Enterprise")
    st.write("সাইডবার মেনু থেকে সিলেক্ট করুন।")
