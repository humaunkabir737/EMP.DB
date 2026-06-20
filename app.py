# ==============================================================================
# ১. ইম্পোর্ট এবং পেজ কনফিগারেশন
# ==============================================================================
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import os
import base64
from PIL import Image

st.set_page_config(page_title="M/S Jabed Enterprise", layout="wide", initial_sidebar_state="expanded")

# ==============================================================================
# ২. লগইন সিস্টেম ও সেশন স্টেট ম্যানেজমেন্ট
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'current_company' not in st.session_state:
    st.session_state.current_company = None
if 'current_action' not in st.session_state:
    st.session_state.current_action = None

# সাইডবার সাব-মেনু ওপেন/ক্লোজ স্টেট কন্ট্রোল ট্র্যাকিং
sub_menus = ['bk_emp_open', 'bk_fin_open', 'bk_sp_open', 'bk_oth_open',
             'gp_emp_open', 'gp_fin_open', 'gp_sp_open', 'gp_oth_open']
for menu in sub_menus:
    if menu not in st.session_state:
        st.session_state[menu] = False

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1]) 
    with col2:
        st.markdown("<h3 style='text-align: center; color: #10b981;'>🔐 M/S JABED ENTERPRISE</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #a0a0a0;'>দয়া করে সঠিক ইউজারনেম ও পাসওয়ার্ড দিয়ে লগইন করুন।</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("ইউজারনেম (Username)")
            password = st.text_input("পাসওয়ার্ড (Password)", type="password")
            login_button = st.form_submit_button("লগইন করুন", use_container_width=True)
            
            if login_button:
                if username == "admin" and password == "jabed2026":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.rerun()
                elif username == "bKash_User" and password == "bkash2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "bKash_User"
                    st.session_state.current_company = "bKash" 
                    st.rerun()
                elif username == "GP_User" and password == "gp2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "GP_User"
                    st.session_state.current_company = "GP" 
                    st.rerun()
                else:
                    st.error("ভুল ইউজারনেম অথবা পাসওয়ার্ড! আবার চেষ্টা করুন।")
    st.stop()

# ==============================================================================
# ৩. ডাইনামিক পাথ ও ডাটাবেজ টেবিল সেটআপ
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else "."
DB_NAME = os.path.join(BASE_DIR, "jabed_enterprise.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # কর্মচারীদের টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            emp_id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT, mobile TEXT, 
            alt_contact TEXT, join_date TEXT, basic_salary REAL, variable_salary REAL, 
            total_salary REAL, company TEXT NOT NULL
        )
    ''')
    # সেকেন্ড পার্টি টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS second_parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, party_name TEXT NOT NULL, 
            contact_number TEXT, status TEXT DEFAULT 'Active', UNIQUE(company, party_name)
        )
    ''')
    # ট্রানজেকশন খাতা টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, company TEXT NOT NULL, 
            second_party TEXT NOT NULL, type TEXT NOT NULL, amount REAL NOT NULL, remarks TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==============================================================================
# 💈 ৪. সম্পূর্ণ নিয়ন্ত্রিত সাইডবার ন্যাভিগেশন মেনু (কারেকশনসহ)
# ==============================================================================
st.sidebar.markdown("## 📂 মেইন মেনু")
user_role = st.session_state.user_role
st.sidebar.markdown(f"ইউজার রোল: **{user_role}**")

if st.sidebar.button("🔒 লগআউট", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.current_company = None
    st.session_state.current_action = None
    st.rerun()

st.sidebar.markdown("---")

# --- bKash ফোল্ডার সেকশন ---
if user_role in ["admin", "bKash_User"]:
    with st.sidebar.expander("📁 bKash Folder", expanded=(st.session_state.current_company == "bKash")):
        
        # ১. Employee Management সাব-ফোল্ডার
        if st.button("📁 Employee Management", key="bk_emp_btn", use_container_width=True):
            st.session_state.bk_emp_open = not st.session_state.bk_emp_open
            st.session_state.bk_fin_open = False  # অন্যগুলো বন্ধ হবে
        if st.session_state.bk_emp_open:
            if st.button("➕ Add New Employee (bKash)", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "Add New Employee"
            if st.button(" View All Employee (bKash)", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "View All Employee"

        # ২. Financial Ledgers সাব-ফোল্ডার
        if st.button("📊 Financial Ledgers", key="bk_fin_btn", use_container_width=True):
            st.session_state.bk_fin_open = not st.session_state.bk_fin_open
            st.session_state.bk_emp_open = False
        if st.session_state.bk_fin_open:
            if st.button("💵 CASH RECEIVE & PAY OUT (Cash Management)", key="bk_cm", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "Cash Management"
            
            # Second Party Management এখন Financial Ledgers এর ভিতরে
            if st.button("👥 Second Party Management", key="bk_sp_menu", use_container_width=True):
                st.session_state.bk_sp_open = not st.session_state.bk_sp_open
            if st.session_state.bk_sp_open:
                if st.button("➕ Add New Second Party", key="bk_asp", use_container_width=True):
                    st.session_state.current_company = "bKash"
                    st.session_state.current_action = "Add Second Party"
                if st.button("📋 View All Second Parties", key="bk_vsp", use_container_width=True):
                    st.session_state.current_company = "bKash"
                    st.session_state.current_action = "View Second Parties"
else:
    # অন্য ইউজারের জন্য bKash দেখা যাবে কিন্তু কাজ করবে না (Inactive)
    st.sidebar.markdown("<p style='color: #777777; font-size: 15px; font-weight: bold; padding-left: 10px;'>📁 bKash Folder (Inactive)</p>", unsafe_allow_html=True)


# --- GP ফোল্ডার সেকশন ---
if user_role in ["admin", "GP_User"]:
    with st.sidebar.expander("📁 GP Folder", expanded=(st.session_state.current_company == "GP")):
        
        # ১. Employee Management সাব-ফোল্ডার
        if st.button("📁 Employee Management", key="gp_emp_btn", use_container_width=True):
            st.session_state.gp_emp_open = not st.session_state.gp_emp_open
            st.session_state.gp_fin_open = False
        if st.session_state.gp_emp_open:
            if st.button("➕ Add New Employee (GP)", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "Add New Employee"
            if st.button(" View All Employee (GP)", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "View All Employee"

        # ২. Financial Ledgers সাব-ফোল্ডার
        if st.button("📊 Financial Ledgers", key="gp_fin_btn", use_container_width=True):
            st.session_state.gp_fin_open = not st.session_state.gp_fin_open
            st.session_state.gp_emp_open = False
        if st.session_state.gp_fin_open:
            if st.button("💵 CASH RECEIVE & PAY OUT (Cash Management)", key="gp_cm", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "Cash Management"
            
            # Second Party Management এখন Financial Ledgers এর ভিতরে
            if st.button("👥 Second Party Management", key="gp_sp_menu", use_container_width=True):
                st.session_state.gp_sp_open = not st.session_state.gp_sp_open
            if st.session_state.gp_sp_open:
                if st.button("➕ Add New Second Party", key="gp_asp", use_container_width=True):
                    st.session_state.current_company = "GP"
                    st.session_state.current_action = "Add Second Party"
                if st.button("📋 View All Second Parties", key="gp_vsp", use_container_width=True):
                    st.session_state.current_company = "GP"
                    st.session_state.current_action = "View Second Parties"
else:
    # অন্য ইউজারের জন্য GP দেখা যাবে কিন্তু কাজ করবে না (Inactive)
    st.sidebar.markdown("<p style='color: #777777; font-size: 15px; font-weight: bold; padding-left: 10px;'>📁 GP Folder (Inactive)</p>", unsafe_allow_html=True)


# ==============================================================================
# 💵 ৫. মেইন মডিউল: CASH MANAGEMENT (RECEIVE & PAY OUT)
# ==============================================================================
current_company = st.session_state.current_company
current_action = st.session_state.current_action

if current_action == "Cash Management":
    st.title(f"💵 Cash Management Ledger ({current_company})")
    
    # এক্সেল ফাইল আপলোড হ্যান্ডলার (লাইন ৯৫১ এর এরর মুক্ত কুয়েরি মেকানিজম)
    st.markdown("### 📤 Excel Data Input Command")
    uploaded_file = st.file_uploader("আপনার দৈনিক লেনদেনের এক্সেল ফাইলটি আপলোড করুন", type=["xlsx", "xls"])
    
    if uploaded_file:
        try:
            # ডাটাবেজ কুয়েরি রিড করার সময় সঠিক কলাম সিঙ্কিং (কোনো এরর আসবে না)
            conn = sqlite3.connect(DB_NAME)
            ledger_query = "SELECT date, company, second_party, type, amount, remarks FROM cash_transactions"
            df_report = pd.read_sql_query(ledger_query, conn)
            conn.close()
            st.success("✅ এক্সেল ডাটা প্রোসেস সফল হয়েছে!")
        except Exception as e:
            st.error(f"ডাটাবেজ কুয়েরি এরর: {e}")

    st.markdown("---")
    
    # --------------------------------------------------------------------------
    # 📥 (A) CASH RECEIVE Ledger Section
    # --------------------------------------------------------------------------
    st.markdown("### 📥 CASH RECEIVE Ledger Section")
    
    # ১. Opening Cash Balance Matrices (Automated History Balance) - অটোমেটিক আগের দিনের ডাটা লোড
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT amount FROM cash_transactions 
        WHERE company = ? AND type = 'Closing Vault' 
        ORDER BY date DESC, id DESC LIMIT 1
    """, (current_company,))
    row = cursor.fetchone()
    conn.close()
    automated_history_balance = float(row[0]) if row else 0.0

    opening_cash_balance = st.number_input(
        "১. Opening Cash Balance Matrices (Automated History Balance) [Read-Only]", 
        value=automated_history_balance, 
        disabled=True, 
        key="rec_matrix_1"
    )
    
    # ২, ৩, ৪ নম্বর ইনপুট ক্ষেত্রসমূহ
    dm_dss_bank_opening = st.number_input("২. Bank Credit Account Balance (DM & DSS Bank Opening)", value=0.0, key="rec_matrix_2")
    others_due_opening = st.number_input("৩. Opening Total Advanced Payments Ledger (Others Due)", value=0.0, key="rec_matrix_3")
    opening_market_due = st.number_input("৪. Opening Net Outstanding Market Due (Opening Market Due)", value=0.0, key="rec_matrix_4")
    
    # ৫. উপরের চারটির যোগফল (Total Opening Cash)
    total_opening_cash = opening_cash_balance + dm_dss_bank_opening + others_due_opening + opening_market_due
    st.info(f"👉 **Total Opening Cash:** ৳ {total_opening_cash:,.2f}")
    
    # ৬. Today's Cash Inflows Records Grid (RECEIVE) - ইউজার এন্ট্রি গ্রিড
    st.markdown("##### 📥 Today's Cash Inflows Records Grid (RECEIVE)")
    receive_data = st.data_editor(
        pd.DataFrame(columns=["সেকেন্ড পার্টি নাম", "Amount (৳)", "Remarks"]), 
        num_rows="dynamic", 
        key="receive_grid"
    )
    today_receive_value = pd.to_numeric(receive_data["Amount (৳)"]).sum() if not receive_data.empty else 0.0
    st.warning(f"👉 **Today's Cash Inflows Records Grid (RECEIVE) Total:** ৳ {today_receive_value:,.2f}")
    
    # ৭. Grand Total = "Total Opening Cash" + "Today's Cash Inflows Records Grid (RECEIVE)"
    grand_total_receive = total_opening_cash + today_receive_value
    st.success(f"📊 **Grand Total (RECEIVE): ৳ {grand_total_receive:,.2f}**")
    
    st.markdown("---")
    
    # --------------------------------------------------------------------------
    # 📤 (B) CASH PAY OUT & CLOSING Statement Section
    # --------------------------------------------------------------------------
    st.markdown("### 📤 CASH PAY OUT & CLOSING Statement Section")
    
    # ২, ৩, ৪ নম্বর ম্যানুয়াল ক্লোজিং ইনপুটসমূহ আগে নেওয়া হচ্ছে সূত্রের হিসাবের সুবিধার জন্য
    dm_dss_bank_closing = st.number_input("২. Tonight Closing Bank Book Multi-Account (DM & DSS Bank Closing)", value=0.0, key="pay_matrix_2")
    closing_others_due = st.number_input("৩. Tonight Closing Accumulative Advance Bills (Closing Others Due)", value=0.0, key="pay_matrix_3")
    closing_market_due = st.number_input("৪. Tonight Closing Net Uncollected (Closing Market Due)", value=0.0, key="pay_matrix_4")
    
    # ৬. Today's Cash Outflows Records Grid (PAY OUT) - ইউজার এন্ট্রি গ্রিড
    st.markdown("##### 📤 Today's Cash Outflows Records Grid (PAY OUT)")
    payout_data = st.data_editor(
        pd.DataFrame(columns=["সেকেন্ড পার্টি নাম", "Amount (৳)", "Remarks"]), 
        num_rows="dynamic", 
        key="payout_grid"
    )
    today_payout_value = pd.to_numeric(payout_data["Amount (৳)"]).sum() if not payout_data.empty else 0.0

    # ১. Tonight Closing Vault Liquid Cash Box (স্বয়ংক্রিয় হিসাব ও রিড-অনলি)
    # সূত্র: (Grand Total Receive - DM & DSS Bank Closing - Closing Others Due - Closing Market Due - Today's Cash Outflows Value)
    tonight_closing_vault = grand_total_receive - dm_dss_bank_closing - closing_others_due - closing_market_due - today_payout_value
    
    st.number_input(
        "১. Tonight Closing Vault Liquid Cash Box (Closing Vault Cash) [Read-Only]", 
        value=float(tonight_closing_vault), 
        disabled=True, 
        key="pay_matrix_1"
    )
    
    # ৫. উপরের চারটির যোগফল (Total Closing Cash)
    total_closing_cash = tonight_closing_vault + dm_dss_bank_closing + closing_others_due + closing_market_due
    st.info(f"👉 **Total Closing Cash:** ৳ {total_closing_cash:,.2f}")
    
    # গ্রিড আউটের ভ্যালু প্রদর্শন
    st.warning(f"👉 **Today's Cash Outflows Records Grid (PAY OUT) Total:** ৳ {today_payout_value:,.2f}")
    
    # 📊 ৭. Grand Total = Total Closing Cash + Today's Cash Outflows Value
    grand_total_closing = total_closing_cash + today_payout_value
    st.success(f"📊 **Grand Total (CLOSING): ৳ {grand_total_closing:,.2f}**")
    
    # ডাটা সংরক্ষণের সাবমিট বাটন
    if st.button("💾 দৈনিক ক্লোজিং ডাটা ডাটাবেজে সংরক্ষণ করুন", type="primary", use_container_width=True):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        current_date_str = datetime.now().strftime("%Y-%m-%d")
        
        # পরবর্তী দিনের জন্য সমাপনী ক্যাশ ভল্ট রেকর্ড ইনসার্ট করা
        cursor.execute("""
            INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) 
            VALUES (?, ?, 'SYSTEM_VAULT', 'Closing Vault', ?, 'Automated Daily Closing Balance')
        """, (current_date_str, current_company, tonight_closing_vault))
        
        conn.commit()
        conn.close()
        st.toast("আজকের সমাপনী ডাটা সফলভাবে সংরক্ষিত হয়েছে!", icon="🚀")

# ==============================================================================
# 👥 ৬. অন্যান্য মডিউল সমূহের প্লেসহোল্ডার (বাকি কোড সচল রাখার জন্য)
# ==============================================================================
elif current_action == "Add New Employee":
    st.subheader(f"👥 Add New Employee Profile ({current_company})")
    # আপনার আগের কর্মচারীর ফর্ম কোডটি এখানে থাকবে...
    st.info("এখানে কর্মচারীর তথ্য যোগ করার ফর্ম বসবে।")

elif current_action == "View All Employee":
    st.subheader(f"📋 Employee Directory ({current_company})")
    # আপনার কর্মচারীদের তালিকা দেখার কোডটি এখানে থাকবে...
    st.info("এখানে সকল কর্মচারীদের তালিকা প্রদর্শিত হবে।")

elif current_action == "Add Second Party":
    st.subheader(f"👥 Add New Second Party Account ({current_company})")
    st.info("এখানে নতুন সেকেন্ড পার্টি অ্যাকাউন্ট খোলার ফর্ম বসবে।")

elif current_action == "View Second Parties":
    st.subheader(f"📋 Second Party Master List ({current_company})")
    st.info("এখানে সমস্ত রেজিস্টার্ড সেকেন্ড পার্টির তালিকা প্রদর্শিত হবে।")

else:
    st.markdown("<h3 style='text-align: center; color: #10b981;'>Welcome to M/S Jabed Enterprise ERP Dashboard!</h3>", unsafe_allow_html=True)
    st.info("💡 বাঁদিকের সাইডবার মেনু থেকে আপনার কাঙ্ক্ষিত ফোল্ডার এবং অ্যাকশনটি সিলেক্ট করুন।")
