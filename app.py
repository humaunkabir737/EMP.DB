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
# ২. লগইন সিস্টেম (সুরক্ষার জন্য রোল-বেসড অ্যাক্সেসসহ)
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

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
# ৩. গ্লোবাল সেশন স্টেট এবং ডাটাবেজ পাথ সেটআপ
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in locals() else "."
DB_NAME = os.path.join(BASE_DIR, "jabed_enterprise.db")

# ৩ নম্বর পয়েন্ট সংশোধন: 'None' স্ট্রিং টাইপের পরিবর্তে পাইথন None অবজেক্ট ব্যবহার করে সিঙ্ক করা হয়েছে
for state_key, default_val in [('current_company', None), ('current_action', None), ('active_emp_id', None)]:
    if state_key not in st.session_state:
        st.session_state[state_key] = default_val

# সাইডবার ড্রপডাউন মেনু ট্র্যাকিং স্টেট
sub_menus = ['bk_emp_open', 'bk_fin_open', 'bk_sp_open', 'gp_emp_open', 'gp_fin_open', 'gp_sp_open']
for menu in sub_menus:
    if menu not in st.session_state:
        st.session_state[menu] = False

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # কর্মচারীদের মূল টেবিল স্ট্রাকচার
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            emp_id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT, mobile TEXT, 
            alt_contact TEXT, join_date TEXT, basic_salary REAL, variable_salary REAL, 
            total_salary REAL, company TEXT NOT NULL, father_name TEXT, mother_name TEXT, 
            nid TEXT, photo TEXT
        )
    ''')
    # সেকেন্ড পার্টি টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS second_parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, party_name TEXT NOT NULL, 
            contact_number TEXT, status TEXT DEFAULT 'Active', UNIQUE(company, party_name)
        )
    ''')
    # ট্রানজেকশন টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, company TEXT NOT NULL, 
            second_party TEXT NOT NULL, type TEXT NOT NULL, amount REAL NOT NULL, remarks TEXT
        )
    ''')
    
    # ৪ নম্বর পয়েন্টের নির্দেশানুযায়ী: No Change, শুধুমাত্র bKash-এর ডিফল্ট পার্টি ইনিশিয়েলাইজ হবে
    default_parties = ['Mother_Wallet', 'Hand_Cash', 'Petty_Cash', 'Bank_Account']
    for party in default_parties:
        cursor.execute('''
            INSERT OR IGNORE INTO second_parties (company, party_name, contact_number, status)
            VALUES ('bKash', ?, '', 'Active')
        ''', (party,))
        
    conn.commit()
    conn.close()

init_db()

# ==============================================================================
# ৪. সাইডবার ন্যাভিগেশন মেনু (১ নম্বর পয়েন্টের রিকোয়ারমেন্ট অনুযায়ী নো-চেঞ্জ)
# ==============================================================================
st.sidebar.markdown("## 📂 মেইন মেনু")
user_role = st.session_state.user_role
st.sidebar.markdown(f"ইউজার রোল: **{user_role}**")

if st.sidebar.button("🔒 Logout", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.current_company = None
    st.session_state.current_action = None
    st.rerun()

st.sidebar.markdown("---")

# bKash ফোল্ডার লজিক (App 3.5 অনুযায়ী অপরিবর্তিত)
if user_role in ["admin", "bKash_User"]:
    with st.sidebar.expander("📁 bKash Folder", expanded=(st.session_state.current_company == "bKash")):
        if st.button("📁 Employee Management", key="bk_emp_btn", use_container_width=True):
            st.session_state.bk_emp_open = not st.session_state.bk_emp_open
            st.session_state.bk_fin_open = False
        if st.session_state.bk_emp_open:
            if st.button("➕ Add New Employee (bKash)", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "Add New Employee"
            if st.button("🔍 View All Employee (bKash)", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "View All Employee"

        if st.button("📊 Financial Ledgers", key="bk_fin_btn", use_container_width=True):
            st.session_state.bk_fin_open = not st.session_state.bk_fin_open
            st.session_state.bk_emp_open = False
        if st.session_state.bk_fin_open:
            if st.button("💵 CASH RECEIVE & PAY OUT", key="bk_cm", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "Cash Management"
            if st.button("👥 Second Party Management", key="bk_sp_menu", use_container_width=True):
                st.session_state.bk_sp_open = not st.session_state.bk_sp_open
            if st.session_state.bk_sp_open:
                if st.button("➕ Add New Second Party", key="bk_asp", use_container_width=True):
                    st.session_state.current_company = "bKash"
                    st.session_state.current_action = "Add Second Party"
                if st.button("📋 View All Second Parties", key="bk_vsp", use_container_width=True):
                    st.session_state.current_company = "bKash"
                    st.session_state.current_action = "View Second Parties"

# GP ফোল্ডার লজিক (App 3.5 অনুযায়ী অপরিবর্তিত)
if user_role in ["admin", "GP_User"]:
    with st.sidebar.expander("📁 GP Folder", expanded=(st.session_state.current_company == "GP")):
        if st.button("📁 Employee Management", key="gp_emp_btn", use_container_width=True):
            st.session_state.gp_emp_open = not st.session_state.gp_emp_open
            st.session_state.gp_fin_open = False
        if st.session_state.gp_emp_open:
            if st.button("➕ Add New Employee (GP)", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_action = "Add New Employee"
            if st.button("🔍 View All Employee (GP)", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "View All Employee"

        if st.button("📊 Financial Ledgers", key="gp_fin_btn", use_container_width=True):
            st.session_state.gp_fin_open = not st.session_state.gp_fin_open
            st.session_state.gp_emp_open = False
        if st.session_state.gp_fin_open:
            if st.button("💵 CASH RECEIVE & PAY OUT", key="gp_cm", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "Cash Management"
            if st.button("👥 Second Party Management", key="gp_sp_menu", use_container_width=True):
                st.session_state.gp_sp_open = not st.session_state.gp_sp_open
            if st.session_state.gp_sp_open:
                if st.button("➕ Add New Second Party", key="gp_asp", use_container_width=True):
                    st.session_state.current_company = "GP"
                    st.session_state.current_action = "Add Second Party"
                if st.button("📋 View All Second Parties", key="gp_vsp", use_container_width=True):
                    st.session_state.current_company = "GP"
                    st.session_state.current_action = "View Second Parties"

# ==============================================================================
# ৫. ড্যাশবোর্ড মডিউল এক্সিকিউশন
# ==============================================================================
current_company = st.session_state.current_company
current_action = st.session_state.current_action

# --- মডিউল: এড এমপ্লয়ী ---
if current_action == "Add New Employee":
    st.subheader(f"👥 Add New Employee Profile ({current_company})")
    
    tab1, tab2 = st.tabs(["Manual Entry Form", "Add Employee By Upload"])
    
    with tab1:
        with st.form("emp_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            emp_id = c1.text_input("Employee ID *")
            name = c2.text_input("Full Name *")
            designation = c3.text_input("Designation")
            
            c4, c5, c6 = st.columns(3)
            mobile = c4.text_input("Mobile Number")
            alt_contact = c5.text_input("Alternative Contact")
            join_date = c6.date_input("Joining Date", value=datetime.today()).strftime("%Y-%m-%d")
            
            c7, c8 = st.columns(2)
            basic_salary = c7.number_input("Basic Salary (৳)", min_value=0.0, step=500.0)
            variable_salary = c8.number_input("Variable Salary (৳)", min_value=0.0, step=500.0)
            
            st.markdown("##### 🏡 Additional Family & Identity Details")
            c9, c10, c11 = st.columns(3)
            f_name = c9.text_input("Father's Name")
            m_name = c10.text_input("Mother's Name")
            nid_no = c11.text_input("NID Card Number")
            
            emp_photo = st.file_uploader("Upload Employee Photo", type=["jpg", "jpeg", "png"])
            submit = st.form_submit_button("💾 Save Employee Profile", use_container_width=True)
            
            if submit:
                if not emp_id or not name:
                    st.error("❌ Employee ID এবং Name দেওয়া বাধ্যতামূলক!")
                else:
                    photo_base64 = ""
                    if emp_photo is not None:
                        photo_base64 = base64.b64encode(emp_photo.read()).decode()
                        
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    try:
                        total_salary = basic_salary + variable_salary
                        cursor.execute("""
                            INSERT INTO employees (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary, company, father_name, mother_name, nid, photo)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary, current_company, f_name, m_name, nid_no, photo_base64))
                        conn.commit()
                        # ৫ নম্বর পয়েন্ট সংশোধন: ৫ নম্বর পয়েন্ট সংশোধন: টাইপো ঠিক করা হয়েছে (Successfully, Data)
                        st.success("🎉 Successfully Added New Employee Data!")
                    except sqlite3.IntegrityError:
                        st.error("❌ এই Employee ID ইতিমধ্যে ডাটাবেজে বিদ্যমান!")
                    finally:
                        conn.close()
                        
    with tab2:
        st.markdown("##### 📤 Bulk Upload Employee via Excel")
        uploaded_excel = st.file_uploader("সিলেক্ট করুন এক্সেল ফাইল (.xlsx, .xls)", type=["xlsx", "xls"], key="bulk_emp")
        if uploaded_excel:
            try:
                df = pd.read_excel(uploaded_excel)
                required_cols = ['Employee ID', 'Name', 'Designation', 'Mobile', 'Basic Salary', 'Variable Salary']
                if all(col in df.columns for col in required_cols):
                    if st.button("🚀 Start Bulk Import Process", use_container_width=True):
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        
                        # ২ নম্বর পয়েন্ট সংশোধন: ডাটা মুছে যাওয়ার ঝুঁকি রোধে সেফ চেক লজিক যুক্ত করা হয়েছে
                        for _, row in df.iterrows():
                            e_id = str(row['Employee ID']).strip()
                            e_name = str(row['Name']).strip()
                            e_des = str(row['Designation']).strip() if pd.notna(row['Designation']) else ""
                            e_mob = str(row['Mobile']).strip() if pd.notna(row['Mobile']) else ""
                            b_sal = float(row['Basic Salary']) if pd.notna(row['Basic Salary']) else 0.0
                            v_sal = float(row['Variable Salary']) if pd.notna(row['Variable Salary']) else 0.0
                            t_sal = b_sal + v_sal
                            
                            # ডাটাবেজে আইডি চেক করা হচ্ছে
                            cursor.execute("SELECT 1 FROM employees WHERE emp_id = ?", (e_id,))
                            if cursor.fetchone():
                                # আইডি থাকলে শুধু কোর কলাম আপডেট হবে, ফ্যামিলি ডাটা/ছবি অক্ষত থাকবে
                                cursor.execute("""
                                    UPDATE employees 
                                    SET name=?, designation=?, mobile=?, basic_salary=?, variable_salary=?, total_salary=?, company=?
                                    WHERE emp_id=?
                                """, (e_name, e_des, e_mob, b_sal, v_sal, t_sal, current_company, e_id))
                            else:
                                # নতুন আইডি হলে ইনসার্ট হবে
                                cursor.execute("""
                                    INSERT INTO employees (emp_id, name, designation, mobile, basic_salary, variable_salary, total_salary, company)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, (e_id, e_name, e_des, e_mob, b_sal, v_sal, t_sal, current_company))
                                
                        conn.commit()
                        conn.close()
                        # ৫ নম্বর পয়েন্ট সংশোধন: টাইপো ঠিক করা হয়েছে (Successfully)
                        st.success("🎉 Bulk Employee Data Successfully Uploaded & Updated Without Any Data Loss!")
                else:
                    st.error("❌ এক্সেল ফাইলের কলামের নাম সঠিক নয়! নিশ্চিত করুন কলামগুলো রয়েছে: " + str(required_cols))
            except Exception as e:
                st.error(f"ফাইল প্রোসেস করতে সমস্যা হয়েছে: {e}")

# --- মডিউল: ভিউ এমপ্লয়ী ---
elif current_action == "View All Employee":
    st.subheader(f"📋 Employee Directory List ({current_company})")
    conn = sqlite3.connect(DB_NAME)
    emp_df = pd.read_sql_query("SELECT emp_id, name, designation, mobile, total_salary FROM employees WHERE company = ?", conn, params=(current_company,))
    conn.close()
    
    if not emp_df.empty:
        st.dataframe(emp_df, use_container_width=True)
    else:
        st.info("কোনো কর্মচারীর প্রোফাইল ডাটা পাওয়া যায়নি।")

# --- মডিউল: সেকেন্ড পার্টি যুক্ত করা ---
elif current_action == "Add Second Party":
    st.subheader(f"👥 Add New Second Party Account ({current_company})")
    with st.form("sp_form", clear_on_submit=True):
        p_name = st.text_input("Party Name *")
        p_contact = st.text_input("Contact Number")
        p_submit = st.form_submit_button("Save Party")
        
        if p_submit and p_name:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            try:
                cursor.execute("INSERT INTO second_parties (company, party_name, contact_number, status) VALUES (?, ?, ?, 'Active')",
                               (current_company, p_name, p_contact))
                conn.commit()
                # ৫ নম্বর পয়েন্ট সংশোধন: টাইপো ঠিক করা হয়েছে (Successfully)
                st.toast("Successfully Added Second Party!", icon="✅")
            except sqlite3.IntegrityError:
                st.error("এই নাম অলরেডি রেজিস্টার্ড!")
            finally:
                conn.close()

# --- মডিউল: সেকেন্ড পার্টি ভিউ ---
elif current_action == "View Second Parties":
    st.subheader(f"📋 Second Party Master List ({current_company})")
    conn = sqlite3.connect(DB_NAME)
    sp_df = pd.read_sql_query("SELECT party_name, contact_number, status FROM second_parties WHERE company = ?", conn, params=(current_company,))
    conn.close()
    st.dataframe(sp_df, use_container_width=True)

# --- মডিউল: ক্যাশ ম্যানেজমেন্ট (ফর্মুলা সম্বলিত) ---
elif current_action == "Cash Management":
    st.title(f"💵 Cash Management Ledger ({current_company})")
    
    # পূর্বের ক্লোজিং ভল্ট অটো লোড করা (Read-Only)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT amount FROM cash_transactions WHERE company = ? AND type = 'Closing Vault' ORDER BY id DESC LIMIT 1", (current_company,))
    row = cursor.fetchone()
    conn.close()
    prev_vault = float(row[0]) if row else 0.0

    st.markdown("### 📥 CASH RECEIVE Ledger Section")
    op_cash = st.number_input("১. Opening Cash Balance Matrices [Read-Only]", value=prev_vault, disabled=True)
    bank_op = st.number_input("২. Bank Credit Account Balance (DM & DSS Bank Opening)", value=0.0)
    adv_op = st.number_input("৩. Opening Total Advanced Payments Ledger (Others Due)", value=0.0)
    mkt_op = st.number_input("৪. Opening Net Outstanding Market Due (Opening Market Due)", value=0.0)
    
    total_opening = op_cash + bank_op + adv_op + mkt_op
    st.info(f"👉 Total Opening Cash: ৳ {total_opening:,.2f}")
    
    st.markdown("##### Today's Cash Inflows Records Grid (RECEIVE)")
    rec_grid = st.data_editor(pd.DataFrame(columns=["সেকেন্ড পার্টি নাম", "Amount (৳)", "Remarks"]), num_rows="dynamic", key="rg")
    today_rec = pd.to_numeric(rec_grid["Amount (৳)"]).sum() if not rec_grid.empty else 0.0
    
    grand_rec = total_opening + today_rec
    st.success(f"📊 Grand Total (RECEIVE): ৳ {grand_rec:,.2f}")
    
    st.markdown("---")
    st.markdown("### 📤 CASH PAY OUT & CLOSING Statement Section")
    bank_cl = st.number_input("২. Tonight Closing Bank Book Multi-Account (DM & DSS Bank Closing)", value=0.0)
    adv_cl = st.number_input("৩. Tonight Closing Accumulative Advance Bills (Closing Others Due)", value=0.0)
    mkt_cl = st.number_input("৪. Tonight Closing Net Uncollected (Closing Market Due)", value=0.0)
    
    st.markdown("##### Today's Cash Outflows Records Grid (PAY OUT)")
    pay_grid = st.data_editor(pd.DataFrame(columns=["সেকেন্ড পার্টি নাম", "Amount (৳)", "Remarks"]), num_rows="dynamic", key="pg")
    today_pay = pd.to_numeric(pay_grid["Amount (৳)"]).sum() if not pay_grid.empty else 0.0
    
    # অটোমেটিক সুনির্দিষ্ট ভল্ট ক্যালকুলেশন সূত্র
    tonight_vault = grand_rec - bank_cl - adv_cl - mkt_cl - today_pay
    st.number_input("১. Tonight Closing Vault Liquid Cash Box [Read-Only]", value=float(tonight_vault), disabled=True)
    
    total_closing = tonight_vault + bank_cl + adv_cl + mkt_cl
    grand_closing = total_closing + today_pay
    st.success(f"📊 Grand Total (CLOSING): ৳ {grand_closing:,.2f}")
    
    if st.button("💾 দৈনিক ক্লোজিং ডাটা ডাটাবেজে সংরক্ষণ করুন", type="primary", use_container_width=True):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        c_date = datetime.now().strftime("%Y-%m-%d")
        
        cursor.execute("""
            INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) 
            VALUES (?, ?, 'SYSTEM_VAULT', 'Closing Vault', ?, 'Automated Daily Closing Balance')
        """, (c_date, current_company, tonight_vault))
        
        conn.commit()
        conn.close()
        # ৫ নম্বর পয়েন্ট সংশোধন: টাইপো ঠিক করা হয়েছে (Successfully)
        st.toast("Successfully Saved Daily Closing Ledger Data!", icon="🚀")

else:
    st.markdown("<h3 style='text-align: center; color: #10b981;'>Welcome to M/S Jabed Enterprise ERP</h3>", unsafe_allow_html=True)
    st.info("💡 ড্যাশবোর্ড মেনু ব্যবহার করে কাজ শুরু করুন।")
