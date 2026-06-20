# ==============================================================================
# ১. ইম্পোর্ট এবং পেজ কনফিগারেশন (Imports & Page Settings)
# ==============================================================================
# এই সেকশনে অ্যাপ্লিকেশনের জন্য প্রয়োজনীয় সকল এক্সটার্নাল লাইব্রেরি ইম্পোর্ট করা হয়েছে।
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import os
import base64
from PIL import Image

# স্ট্রিমলিট পেজের টাইটেল, লেআউট (Wide Mode) এবং সাইডবার ডিফল্ট পজিশন সেট করা হচ্ছে।
st.set_page_config(page_title="M/S Jabed Enterprise", layout="wide", initial_sidebar_state="expanded")

# ==============================================================================
# ২. ইউজার অথেনটিকেশন ও লগইন সিস্টেম (Role-Based Login System)
# ==============================================================================
# সেশন স্টেট ইনিশিয়ালাইজেশন: লগইন স্ট্যাটাস এবং ইউজারের রোল ট্র্যাক করার জন্য।
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

# ইউজার লগইন না করে থাকলে তাকে লগইন স্ক্রিন দেখানো হবে এবং বাকি কোড এক্সিকিউশন বন্ধ থাকবে (st.stop)।
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1]) 
    with col2:
        st.markdown("<h3 style='text-align: center; color: #10b981;'>🔐 M/S JABED ENTERPRISE</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #a0a0a0;'>Please enter correct username and password to log in.</p>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                # এডমিন রোলের ক্রেডেনশিয়াল চেক
                if username == "admin" and password == "jabed2026":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.session_state.current_action = None 
                    st.success("Welcome Admin!")
                    import time; time.sleep(0.5); st.rerun()
                # বিকাশ ইউজারের ক্রেডেনশিয়াল চেক
                elif username == "bKash_User" and password == "bkash2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "bKash_User"
                    st.session_state.current_company = "bKash" 
                    st.session_state.current_action = None 
                    st.success("Welcome bKash User!")
                    import time; time.sleep(0.5); st.rerun()
                # জিপি ইউজারের ক্রেডেনশিয়াল চেক
                elif username == "GP_User" and password == "gp2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "GP_User"
                    st.session_state.current_company = "GP" 
                    st.session_state.current_action = None 
                    st.success("Welcome GP User!")
                    import time; time.sleep(0.5); st.rerun()
                else:
                    st.error("Wrong Username & Password. Please try again.")
    st.stop()

# ==============================================================================
# ৩. ডাইনামিক পাথ এবং ফোল্ডার স্ট্রাকচার (Dynamic Paths & Directory Setup)
# ==============================================================================
# অ্যাপের মূল ডিরেক্টরি এবং ডেটাবেজ ফাইলের নিখুঁত পাথ নির্ধারণ করা হচ্ছে।
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "jabed_enterprise.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploaded_docs")
IMAGE_DIR = os.path.join(BASE_DIR, "Related Image")

# কর্মচারীদের ছবি, এনআইডি এবং গ্যারান্টরের ডকুমেন্টস রাখার নির্দিষ্ট সাব-ফোল্ডার পাথ।
PHOTO_DIR = os.path.join(BASE_DIR, "employee_photos")
EMP_NID_DIR = os.path.join(BASE_DIR, "nid_photos")
GUAR_PHOTO_DIR = os.path.join(BASE_DIR, "guarantor_photos")
GUAR_NID_DIR = os.path.join(BASE_DIR, "guarantor_nids")

# ==============================================================================
# ৪. ডাটাবেজ টেবিল এবং অটো-মাইগ্রেশন (Database Tables & Migration Logic)
# ==============================================================================
def init_db():
    """অ্যাপ্লিকেশন চালুর সময় স্বয়ংক্রিয়ভাবে ফোল্ডার এবং প্রয়োজনীয় টেবিল গঠন করার ফাংশন।"""
    # কোনো ফোল্ডার মিসিং থাকলে তা অটো-তৈরি করে নেবে।
    for folder in [UPLOAD_DIR, IMAGE_DIR, PHOTO_DIR, EMP_NID_DIR, GUAR_PHOTO_DIR, GUAR_NID_DIR]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # কর্মচারীদের মূল টেবিল তৈরি (Employees Table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            emp_id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT, mobile TEXT, alt_contact TEXT, 
            join_date TEXT, basic_salary REAL, variable_salary REAL, total_salary REAL, company TEXT NOT NULL, father_name TEXT,
            father_nid TEXT, mother_name TEXT, emp_nid TEXT, guarantor_name TEXT, guarantor_nid TEXT, guarantor_mobile TEXT
        )
    ''')
    
    # সেকেন্ড পার্টি টেবিল স্কিমা মাইগ্রেশন এবং কলাম সংযোজন ট্র্যাকিং লজিক
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='second_parties'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(second_parties)")
        existing_sp_columns = [col[1] for col in cursor.fetchall()]
        if 'company' not in existing_sp_columns:
            has_status = 'status' in existing_sp_columns
            cursor.execute("ALTER TABLE second_parties RENAME TO old_second_parties")
            cursor.execute('''
                CREATE TABLE second_parties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, party_name TEXT NOT NULL, 
                    contact_number TEXT, comments_01 TEXT, comments_02 TEXT, status TEXT DEFAULT 'Active', UNIQUE(company, party_name)
                )
            ''')
            if has_status:
                cursor.execute("INSERT INTO second_parties (id, company, party_name, contact_number, comments_01, comments_02, status) SELECT id, 'bKash', party_name, contact_number, comments_01, comments_02, IFNULL(status, 'Active') FROM old_second_parties")
            else:
                cursor.execute("INSERT INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) SELECT 'bKash', party_name, contact_number, comments_01, comments_02, 'Active' FROM old_second_parties")
            cursor.execute("DROP TABLE old_second_parties")
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS second_parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, party_name TEXT NOT NULL, 
                contact_number TEXT, comments_01 TEXT, comments_02 TEXT, status TEXT DEFAULT 'Active', UNIQUE(company, party_name)
            )
        ''')
    
    # ডিফল্ট প্রয়োজনীয় সেকেন্ড পার্টিসমূহ স্বয়ংক্রিয়ভাবে ইনসার্ট করা হচ্ছে (যদি না থাকে)
    default_parties = ["Mother_Wallet", "Hand_Cash", "Petty_Cash", "Bank", "BGP", "Dulal", "Shafayat", "Madina", "Owner", 
                       "GAS", "Auto_Rice", "Others", "bKash", "Commission", "Al_Arafa", "Rekit", "DMCBL", "Kabita_Mami", "Ashim_Da", "Al_Amin"]
    for party in default_parties:
        cursor.execute("INSERT OR IGNORE INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) VALUES ('bKash', ?, '', '', '', 'Active')", (party,))
    
    # ক্যাশ ট্রানজেকশন ডাটা রাখার মূল টেবিল (Cash Transactions Table)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, company TEXT NOT NULL, second_party TEXT NOT NULL, type TEXT NOT NULL, amount REAL NOT NULL, remarks TEXT
        )
    ''')
    
    # পুরনো ডাটাবেজে কোনো নতুন কলাম মিসিং থাকলে তা ডাইনামিকালি যোগ করার লজিক (Safe Migration)
    cursor.execute("PRAGMA table_info(employees)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    required_cols = {'company': "TEXT DEFAULT 'bKash'", 'father_name': "TEXT", 'father_nid': "TEXT", 'mother_name': "TEXT", 'emp_nid': "TEXT", 'guarantor_name': "TEXT", 'guarantor_nid': "TEXT", 'guarantor_mobile': "TEXT"}
    for col_name, col_type in required_cols.items():
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type}")
            
    conn.commit()
    conn.close()

init_db()

# ==============================================================================
# ৫. গ্লোবাল সেশন স্টেট এবং হেল্পার ফাংশন (Global State & Balance Utilities)
# ==============================================================================
# অ্যাপের বিভিন্ন পেজের অ্যাকশন ও ডেটা ট্র্যাকিং স্টেট ইনিশিয়েশন।
for state_key, default_val in [('current_company', 'None'), ('current_action', None), ('active_emp_id', None), ('dialog_edit_mode', False), ('active_party_id', None), ('party_edit_mode', False)]:
    if state_key not in st.session_state:
        st.session_state[state_key] = default_val

# ডায়ালগ বক্স কন্ট্রোলের ছোট ২টি ব্যাকএন্ড ফাংশন।
def open_edit_mode(): st.session_state.dialog_edit_mode = True
def close_edit_mode(): st.session_state.dialog_edit_mode = False

def get_historical_closing_balances(company, target_date_str):
    """নির্দিষ্ট তারিখের পূর্বের দিনের সর্বশেষ ক্লোজিং ব্যালেন্স (Vault, Bank, etc.) হিসাব করে নিয়ে আসার কুয়েরি ফাংশন।"""
    conn = sqlite3.connect(DB_NAME)
    row = conn.execute("""
        SELECT date FROM cash_transactions 
        WHERE company=? AND date < ? AND second_party LIKE '__SYS_%'
        ORDER BY date DESC LIMIT 1
    """, (company, target_date_str)).fetchone()
    
    balances = {"vault": 0.0, "bank": 0.0, "advance": 0.0, "due": 0.0}
    if row:
        last_recorded_date = row[0]
        for key, sys_code in [("vault", "__SYS_VAULT__"), ("bank", "__SYS_BANK__"), ("advance", "__SYS_ADVANCE__"), ("due", "__SYS_DUE__")]:
            val = conn.execute("""
                SELECT amount FROM cash_transactions 
                WHERE company=? AND date=? AND second_party=? LIMIT 1
            """, (company, last_recorded_date, sys_code)).fetchone()
            if val:
                balances[key] = val[0]
    conn.close()
    return balances

def render_no_image_frame(title):
    """কোনো ইমেজ আপলোড করা না থাকলে UI-তে একটি সুন্দর ড্যাশড ফ্রেম প্রদর্শন করার HTML হেল্পার।"""
    return f"""
    <div style="border: 2px dashed #444444; border-radius: 8px; background-color: #1e1e1e; 
                height: 145px; display: flex; flex-direction: column; justify-content: center; 
                align-items: center; color: #888888; text-align: center; margin-bottom: 15px; padding: 5px;">
        <span style="font-size: 26px; margin-bottom: 2px;">🖼️</span>
        <b style="font-size: 13px; color: #cccccc;">No Image Loaded</b>
        <span style="font-size: 11px; color: #666666; margin-top: 2px;">({title})</span>
    </div>
    """

# ==============================================================================
# ৬. ব্র্যান্ড হেডার ডিজাইন (Brand Header Component)
# ==============================================================================
def render_header():
    """পেজের একদম উপরে কোম্পানির লোগো এবং অফিসিয়াল অ্যাড্রেস সম্বলিত একটি মার্জিত ব্যানার তৈরি করে।"""
    logo_html = ""
    has_logo = False
    for ext in ["png", "jpg", "jpeg"]:
        logo_path = os.path.join(IMAGE_DIR, f"logo.{ext}")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            logo_html = f'<img src="data:image/{ext};base64,{encoded}" style="height:55px; vertical-align: middle;">'
            has_logo = True; break
    title_text = '<h1 style="color: white; margin: 0; font-family:\'Times New Roman\', serif; font-size: 38px; font-weight: bold;">M/S JABED ENTERPRISE</h1>'
    header_content = f'<div style="display: flex; justify-content: center; align-items: center; gap: 12px;">{logo_html}{title_text}</div>' if has_logo else title_text
    st.markdown(f"""
        <div style="text-align: center; margin-top: -15px; margin-bottom: 2px;">
            {header_content}
            <p style="color: #a0a0a0; margin: 6px 0 0 0; font-size: 14.5px;">394 Anima Plaza, Nagerbazar, Bagerhat Sadar, Bagerhat.</p>
        </div>
        <hr style="border: 1px solid #10b981; margin-top: 15px; margin-bottom: 25px;">
    """, unsafe_allow_html=True)

# ==============================================================================
# ৭. পপআপ ডায়ালগ মডিউল (Interactive Pop-up Dialogs)
# ==============================================================================
# --- সাব সেকশন: সেকেন্ড পার্টি প্রোফাইল ও এডিট ডায়ালগ ---
@st.dialog("Second Party Details", width="medium")
def show_second_party_details(party_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, party_name, contact_number, comments_01, comments_02, status FROM second_parties WHERE id = ?", (party_id,))
    party = cursor.fetchone()
    conn.close()
    if not party:
        st.error("Second Party record not found!")
        st.session_state.active_party_id = None; return
    p_id, p_name, p_contact, p_c1, p_c2, p_status = party
    p_status = p_status or "Active"
    
    col_t1, col_t2 = st.columns([6, 2])
    with col_t1:
        if not st.session_state.party_edit_mode:
            if st.button("✏️ Edit Details", key="sp_edit_toggle_btn"): st.session_state.party_edit_mode = True; st.rerun()
        else:
            if st.button("⬅️ Back to View", key="sp_view_toggle_btn"): st.session_state.party_edit_mode = False; st.rerun()
    with col_t2:
        if st.button("❌ Close Panel", use_container_width=True, key="sp_close_popup_btn"):
            st.session_state.active_party_id = None; st.session_state.party_edit_mode = False; st.rerun()
    st.markdown("---")
    
    if not st.session_state.party_edit_mode:
        st.markdown(f"### **Party Name:** {p_name}")
        st.markdown(f"**Contact Number:** {p_contact or '-'}")
        st.markdown(f"**Primary Comments:** {p_c1 or '-'}")
        st.markdown(f"**Secondary Comments:** {p_c2 or '-'}")
        status_color = "#10b981" if p_status == "Active" else "#ef4444"
        st.markdown(f"**Account Status:** <span style='color:{status_color}; font-weight:bold; font-size:16px;'>{p_status}</span>", unsafe_allow_html=True)
    else:
        with st.form("edit_second_party_form_v1"):
            st.markdown("#### 📝 Update Second Party Profile")
            new_p_name = st.text_input("Second Party Name *", value=p_name)
            new_p_contact = st.text_input("Contact Number", value=p_contact)
            new_p_c1 = st.text_input("Primary Comments", value=p_c1)
            new_p_c2 = st.text_input("Secondary Comments", value=p_c2)
            new_p_status = st.selectbox("Account Status", ["Active", "Inactive"], index=0 if p_status == "Active" else 1)
            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                if not new_p_name.strip(): st.error("Second Party Name cannot be empty!")
                else:
                    try:
                        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                        cursor.execute("UPDATE second_parties SET party_name=?, contact_number=?, comments_01=?, comments_02=?, status=? WHERE id=?", 
                                       (new_p_name.strip(), new_p_contact.strip(), new_p_c1.strip(), new_p_c2.strip(), new_p_status, party_id))
                        conn.commit(); conn.close()
                        st.toast("Second Party details updated successfully!", icon="✅")
                        st.session_state.active_party_id = None; st.session_state.party_edit_mode = False
                        import time; time.sleep(0.5); st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("A duplicate second party with this name already exists under this company profile!")

# --- সাব সেকশন: কর্মচারীর প্রোফাইল ডিটেইলস ও এডিট ডায়ালগ ---
@st.dialog("Employee Profile Details", width="large")
def show_employee_details(emp_id, company):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("""
        SELECT emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary,
               father_name, father_nid, mother_name, emp_nid, guarantor_name, guarantor_nid, guarantor_mobile 
        FROM employees WHERE emp_id = ? AND company = ?
    """, (emp_id, company))
    emp = cursor.fetchone(); conn.close()
    
    if not emp:
        st.error("Employee profile not found!")
        st.session_state.active_emp_id = None; return
        
    (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary,
     father_name, father_nid, mother_name, emp_nid, guarantor_name, guarantor_nid, guarantor_mobile) = emp
    
    col_t1, col_t2 = st.columns([6, 2])
    with col_t1:
        if not st.session_state.dialog_edit_mode: st.button("✏️ Edit Profile Info", type="secondary", key="popup_edit_btn", on_click=open_edit_mode)
        else: st.button("⬅️ Back to View Profile", type="secondary", key="popup_back_btn", on_click=close_edit_mode)
    with col_t2:
        if st.button("❌ Close Window", type="primary", use_container_width=True, key="popup_close_btn"):
            st.session_state.active_emp_id = None; close_edit_mode(); st.rerun()
    st.markdown("---")
    
    # নথিপত্রের ফাইল পাথ কনফিগারেশন
    photo_path = os.path.join(PHOTO_DIR, f"{emp_id}.png")
    nid_path = os.path.join(EMP_NID_DIR, f"{emp_id}.png")
    guar_photo_path = os.path.join(GUAR_PHOTO_DIR, f"{emp_id}.png")
    guar_nid_path = os.path.join(GUAR_NID_DIR, f"{emp_id}.png")
    
    if not st.session_state.dialog_edit_mode:
        m_col1, m_col2 = st.columns([5, 3])
        with m_col1:
            st.markdown(f"### **Name:** {name} | <span style='font-size:16px; color:#10b981;'>ID: {emp_id}</span>", unsafe_allow_html=True)
            st.markdown(f"**Designation:** {designation or '-'}")
            st.markdown(f"**Mobile No:** {mobile or '-'} | **Alternative Contact:** {alt_contact or '-'}")
            st.markdown(f"**Joining Date:** {join_date or '-'}")
            st.markdown("---")
            st.markdown(f"**Father's Name:** {father_name or '-'} | **Father's NID:** {father_nid or '-'}")
            st.markdown(f"**Mother's Name:** {mother_name or '-'} | **Employee NID No:** {emp_nid or '-'}")
            st.markdown("---")
            st.markdown(f"**Guarantor Name:** {guarantor_name or '-'}")
            st.markdown(f"**Guarantor NID No:** {guarantor_nid or '-'}")
            st.markdown(f"**Guarantor Mobile:** {guarantor_mobile or '-'}")
        with m_col2:
            g_img_c1, g_img_c2 = st.columns(2)
            with g_img_c1:
                if os.path.exists(photo_path): st.image(photo_path, caption="Employee Photo", use_container_width=True)
                else: st.markdown(render_no_image_frame("Employee Photo"), unsafe_allow_html=True)
            with g_img_c2:
                if os.path.exists(nid_path): st.image(nid_path, caption="Employee NID", use_container_width=True)
                else: st.markdown(render_no_image_frame("Employee NID"), unsafe_allow_html=True)
            
            g_img_c3, g_img_c4 = st.columns(2)
            with g_img_c3:
                if os.path.exists(guar_photo_path): st.image(guar_photo_path, caption="Guar Photo", use_container_width=True)
                else: st.markdown(render_no_image_frame("Guar Photo"), unsafe_allow_html=True)
            with g_img_c4:
                if os.path.exists(guar_nid_path): st.image(guar_nid_path, caption="Guar NID", use_container_width=True)
                else: st.markdown(render_no_image_frame("Guar NID"), unsafe_allow_html=True)
                
        st.markdown("<br>", unsafe_allow_html=True)
        st.success(f"**Salary Structure:** Basic: {basic_salary:,.1f} ৳ | Variable: {variable_salary:,.1f} ৳ | **Total Guaranteed Package: {total_salary:,.1f} ৳**")
    else:
        # কর্মচারী তথ্য এডিট করার ফর্ম
        with st.form("edit_employee_form_v2", clear_on_submit=False):
            st.markdown("#### 📝 Modify Employee Directory Records")
            c_1, c_2, c_3 = st.columns(3)
            e_name = c_1.text_input("Employee Name *", value=name)
            e_desg = c_2.text_input("Designation", value=designation)
            e_mob = c_3.text_input("Primary Mobile", value=mobile)
            
            c_4, c_5, c_6 = st.columns(3)
            e_alt = c_4.text_input("Alternative Contact", value=alt_contact)
            e_jdate = c_5.text_input("Joining Date (YYYY-MM-DD)", value=join_date)
            e_f_name = c_6.text_input("Father's Name", value=father_name)
            
            c_7, c_8, c_9 = st.columns(3)
            e_f_nid = c_7.text_input("Father's NID No", value=father_nid)
            e_m_name = c_8.text_input("Mother's Name", value=mother_name)
            e_emp_nid = c_9.text_input("Employee NID No", value=emp_nid)
            
            c_10, c_11, c_12 = st.columns(3)
            e_g_name = c_10.text_input("Guarantor Name", value=guarantor_name)
            e_g_nid = c_11.text_input("Guarantor NID No", value=guarantor_nid)
            e_g_mob = c_12.text_input("Guarantor Mobile No", value=guarantor_mobile)
            
            c_s1, c_s2 = st.columns(2)
            e_basic = c_s1.number_input("Basic Fixed Salary (৳)", value=float(basic_salary or 0.0), step=500.0)
            e_var = c_s2.number_input("Variable Allowances (৳)", value=float(variable_salary or 0.0), step=500.0)
            
            # নতুন ডকুমেন্ট আপলোড অপশন (সিঙ্গেল উইন্ডোতে এডিটের স্বার্থে)
            st.markdown("---")
            st.markdown("##### 📥 Replace Attachments (Upload only if you want to overwrite previous file)")
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            u_p = f_col1.file_uploader("New Profile Image", type=["png", "jpg", "jpeg"], key="u_p_edit")
            u_n = f_col2.file_uploader("New Employee NID", type=["png", "jpg", "jpeg"], key="u_n_edit")
            u_gp = f_col3.file_uploader("New Guarantor Photo", type=["png", "jpg", "jpeg"], key="u_gp_edit")
            u_gn = f_col4.file_uploader("New Guarantor NID", type=["png", "jpg", "jpeg"], key="u_gn_edit")
            
            if st.form_submit_button("💾 Save Employee Changes", use_container_width=True):
                if not e_name.strip(): st.error("Employee Name field cannot be empty!")
                else:
                    e_total = e_basic + e_var
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE employees SET name=?, designation=?, mobile=?, alt_contact=?, join_date=?,
                                       basic_salary=?, variable_salary=?, total_salary=?, father_name=?, father_nid=?,
                                       mother_name=?, emp_nid=?, guarantor_name=?, guarantor_nid=?, guarantor_mobile=?
                        WHERE emp_id=? AND company=?
                    """, (e_name.strip(), e_desg.strip(), e_mob.strip(), e_alt.strip(), e_jdate.strip(),
                          e_basic, e_var, e_total, e_f_name.strip(), e_f_nid.strip(), e_m_name.strip(),
                          e_emp_nid.strip(), e_g_name.strip(), e_g_nid.strip(), e_g_mob.strip(), emp_id, company))
                    conn.commit(); conn.close()
                    
                    # নতুন ফাইল ওভাররাইট সংরক্ষণ প্রসেসিং
                    for file_obj, target_p in [(u_p, photo_path), (u_n, nid_path), (u_gp, guar_photo_path), (u_gn, guar_nid_path)]:
                        if file_obj is not None:
                            try: img = Image.open(file_obj); img.save(target_p, "PNG")
                            except Exception: pass
                            
                    st.toast("Employee records successfully updated!", icon="✅")
                    st.session_state.active_emp_id = None; close_edit_mode()
                    import time; time.sleep(0.5); st.rerun()

# ==============================================================================
# ৮. সাইডবার নেভিগেশন কন্ট্রোল প্যানেল (Sidebar Control Panel)
# ==============================================================================
# সিস্টেমের গ্লোবাল ইউজার রোল ট্র্যাকিং
user_role = st.session_state.user_role

# সাইডবার হেডার এবং বর্তমান ইউজারের স্ট্যাটাস
st.sidebar.markdown(f"### Welcome, <span style='color:#10b981;'>{user_role}</span> 👋", unsafe_allow_html=True)

# সাইডবার ডিসপ্লেতে লগআউট বাটন অ্যাকশন
if st.sidebar.button("🔓 Log Out from System", use_container_width=True):
    st.session_state.logged_in = False; st.session_state.user_role = None
    st.session_state.current_company = None; st.session_state.current_action = None; st.rerun()

st.sidebar.markdown("<hr style='margin: 10px 0px; border-color: #444;'>", unsafe_allow_html=True)

# মেনু আইটেমসমূহের তালিকা কনফিগারেশন
menu_options_emp = ["Add New Employee", "Add Employee By Upload", "View All Employee"]
menu_options_sp = ["Add New Second Party", "View All Second Parties"]
menu_options_fin = ["Cash Management", "Expense Management", "Others"]

def set_action(comp, act):
    """সাইডবার বাটনে ক্লিকের সাথে সাথে কোম্পানির ভেরিয়েবল এবং অ্যাকশন রুট পরিবর্তন করার জন্য হেল্পার।"""
    st.session_state.current_company = comp
    st.session_state.current_action = act

# --- সাব সেকশন: bKash কোম্পানির সাইডবার ফোল্ডার ---
if user_role in ["admin", "bKash_User"]:
    with st.sidebar.expander("📁 bKash Folder", expanded=(st.session_state.get('current_company') == "bKash")):
        st.markdown("<p style='color:#10b981; font-weight:bold; font-size:12px; margin-bottom:2px;'>👥 Employee Management</p>", unsafe_allow_html=True)
        for opt in menu_options_emp:
            if st.button(f"▪️ {opt}", key=f"bkash_emp_{opt}", use_container_width=True): set_action("bKash", opt); st.rerun()
            
        st.markdown("<p style='color:#10b981; font-weight:bold; font-size:12px; margin-top:10px; margin-bottom:2px;'>🤝 Second Party Management</p>", unsafe_allow_html=True)
        for opt in menu_options_sp:
            if st.button(f"▪️ {opt}", key=f"bkash_sp_{opt}", use_container_width=True): set_action("bKash", opt); st.rerun()
            
        st.markdown("<p style='color:#10b981; font-weight:bold; font-size:12px; margin-top:10px; margin-bottom:2px;'>💰 Financial Ledgers</p>", unsafe_allow_html=True)
        for opt in menu_options_fin:
            if st.button(f"▪️ {opt}", key=f"bkash_fin_{opt}", use_container_width=True): set_action("bKash", opt); st.rerun()
else:
    # এক্সেস না থাকলে ফোল্ডারটি লকড/ডিজেবল অবস্থায় সাইডবারে ইন-অ্যাক্টিভ দেখাবে।
    with st.sidebar.expander("🔒 bKash Folder (Inactive)", expanded=False):
        st.info("Access Denied for your profile.")

# --- সাব সেকশন: GP কোম্পানির সাইডবার ফোল্ডার ---
if user_role in ["admin", "GP_User"]:
    with st.sidebar.expander("📁 GP Folder", expanded=(st.session_state.get('current_company') == "GP")):
        st.markdown("<p style='color:#3498db; font-weight:bold; font-size:12px; margin-bottom:2px;'>👥 Employee Management</p>", unsafe_allow_html=True)
        for opt in menu_options_emp:
            if st.button(f"▪️ {opt}", key=f"gp_emp_{opt}", use_container_width=True): set_action("GP", opt); st.rerun()
            
        st.markdown("<p style='color:#3498db; font-weight:bold; font-size:12px; margin-top:10px; margin-bottom:2px;'>🤝 Second Party Management</p>", unsafe_allow_html=True)
        for opt in menu_options_sp:
            if st.button(f"▪️ {opt}", key=f"gp_sp_{opt}", use_container_width=True): set_action("GP", opt); st.rerun()
            
        st.markdown("<p style='color:#3498db; font-weight:bold; font-size:12px; margin-top:10px; margin-bottom:2px;'>💰 Financial Ledgers</p>", unsafe_allow_html=True)
        for opt in menu_options_fin:
            if st.button(f"▪️ {opt}", key=f"gp_fin_{opt}", use_container_width=True): set_action("GP", opt); st.rerun()
else:
    # এক্সেস না থাকলে ফোল্ডারটি লকড/ডিজেবল অবস্থায় সাইডবারে ইন-অ্যাক্টিভ দেখাবে।
    with st.sidebar.expander("🔒 GP Folder (Inactive)", expanded=False):
        st.info("Access Denied for your profile.")

# ==============================================================================
# ৯. কোর মডিউল রউটিং এবং পেজ হ্যান্ডলিং (Main App Core Actions Router)
# ==============================================================================
current_company = st.session_state.current_company
current_action = st.session_state.current_action

render_header() # ব্র্যান্ড লোগো ও হেডার লোড করা হলো

if not current_action:
    st.info("💡 Please select a module action from the left sidebar navigation tree to start.")

# ------------------------------------------------------------------------------
# 👥 সেকশন: কর্মচারীর নতুন এন্ট্রি (Action: Add New Employee)
# ------------------------------------------------------------------------------
elif current_action == "Add New Employee":
    st.markdown(f"### 👥 Add New Employee Profile ({current_company})")
    with st.form("add_employee_form_main", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        emp_id = col1.text_input("Employee Personal ID *")
        name = col2.text_input("Full Name *")
        designation = col3.text_input("Designation")
        
        col4, col5, col6 = st.columns(3)
        mobile = col4.text_input("Primary Mobile Number")
        alt_contact = col5.text_input("Alternative Contact")
        join_date = col6.date_input("Joining Date", value=datetime.today()).strftime('%Y-%m-%d')
        
        col7, col8, col9 = st.columns(3)
        father_name = col7.text_input("Father's Name")
        father_nid = col8.text_input("Father's NID No")
        mother_name = col9.text_input("Mother's Name")
        
        col10, col11, col12 = st.columns(3)
        emp_nid = col10.text_input("Employee NID No")
        guarantor_name = col11.text_input("Guarantor Name")
        guarantor_nid = col12.text_input("Guarantor NID No")
        
        col13, col14, col15 = st.columns(3)
        guarantor_mobile = col13.text_input("Guarantor Mobile No")
        basic_salary = col14.number_input("Basic Fixed Salary (৳)", min_value=0.0, step=500.0)
        variable_salary = col15.number_input("Variable Allowances (৳)", min_value=0.0, step=500.0)
        
        st.markdown("---")
        st.markdown("##### 📥 Document Attachments (Images Only)")
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        up_photo = f_col1.file_uploader("Upload Employee Photo", type=["png", "jpg", "jpeg"])
        up_nid = f_col2.file_uploader("Upload Employee NID Card", type=["png", "jpg", "jpeg"])
        up_gphoto = f_col3.file_uploader("Upload Guarantor Photo", type=["png", "jpg", "jpeg"])
        up_gnid = f_col4.file_uploader("Upload Guarantor NID Card", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("💾 Save Profile Data", use_container_width=True):
            if not emp_id.strip() or not name.strip():
                st.error("Employee ID and Name are strictly required fields!")
            else:
                total_salary = basic_salary + variable_salary
                try:
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO employees (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary, company, father_name, father_nid, mother_name, emp_nid, guarantor_name, guarantor_nid, guarantor_mobile)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (emp_id.strip(), name.strip(), designation.strip(), mobile.strip(), alt_contact.strip(), join_date, basic_salary, variable_salary, total_salary, current_company, father_name.strip(), father_nid.strip(), mother_name.strip(), emp_nid.strip(), guarantor_name.strip(), guarantor_nid.strip(), guarantor_mobile.strip()))
                    conn.commit(); conn.close()
                    
                    # ফাইল ডিরেক্টরিতে ছবি সংরক্ষণের প্রসেস
                    mapping = [(up_photo, PHOTO_DIR), (up_nid, EMP_NID_DIR), (up_gphoto, GUAR_PHOTO_DIR), (up_gnid, GUAR_NID_DIR)]
                    for file_obj, dir_path in mapping:
                        if file_obj is not None:
                            img = Image.open(file_obj)
                            img.save(os.path.join(dir_path, f"{emp_id.strip()}.png"), "PNG")
                            
                    st.success(f"Profile for '{name}' successfully integrated into {current_company} directory!")
                except sqlite3.IntegrityError:
                    st.error("An employee record with this specific ID already exists in the ledger database!")

# ------------------------------------------------------------------------------
# 👥 সেকশন: বাল্ক এক্সেল ইমপোর্ট (Action: Add Employee By Upload)
# ------------------------------------------------------------------------------
elif current_action == "Add Employee By Upload":
    st.markdown(f"### 📥 Bulk Employee Import via Excel File ({current_company})")
    st.markdown("""
        <div style='background-color:#1e293b; padding:12px; border-radius:6px; font-size:13px; margin-bottom:15px;'>
        <b>💡 Excel Template Scheme Requirements:</b> The excel worksheet must contain columns: 
        <code>emp_id</code>, <code>name</code>, <code>designation</code>, <code>mobile</code>, <code>basic_salary</code>, <code>variable_salary</code>
        </div>
    """, unsafe_allow_html=True)
    
    excel_file = st.file_uploader("Select Bulk Excel Document File", type=["xlsx", "xls"])
    if excel_file is not None:
        if st.button("🚀 Execute Excel Upload Parser", use_container_width=True, type="primary"):
            try:
                df = pd.read_excel(excel_file)
                required_cols = ['emp_id', 'name']
                if not all(col in df.columns for col in required_cols):
                    st.error("Excel format error. Missing standard 'emp_id' or 'name' columns.")
                else:
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    for idx, row in df.iterrows():
                        e_id = str(row['emp_id']).strip()
                        e_name = str(row['name']).strip()
                        if e_id and e_name and e_id != 'nan' and e_name != 'nan':
                            cursor.execute("SELECT emp_id FROM employees WHERE emp_id=?", (e_id,))
                            if not cursor.fetchone():
                                cursor.execute("""
                                    INSERT INTO employees (emp_id, name, designation, mobile, join_date, basic_salary, variable_salary, total_salary, company)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (e_id, e_name, row.get('designation', 'SR'), str(row.get('mobile', '')), str(datetime.now().date()), float(row.get('basic_salary', 0)), float(row.get('variable_salary', 0)), float(row.get('basic_salary', 0))+float(row.get('variable_salary', 0)), current_company))
                    conn.commit(); conn.close()
                    st.success("Excel sheet parsed and records integrated perfectly!")
            except Exception as e:
                st.error(f"Invalid file structure format: {e}")

# ------------------------------------------------------------------------------
# 👥 সেকশন: কর্মচারী ডিরেক্টরি ভিউ (Action: View All Employee)
# ------------------------------------------------------------------------------
elif current_action == "View All Employee":
    st.markdown(f"### 📋 Employee Directory Registry ({current_company})")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT emp_id as 'ID', name as 'Name', designation as 'Designation', mobile as 'Mobile', total_salary as 'Total Package (৳)' FROM employees WHERE company=?", conn, params=(current_company,))
    conn.close()
    
    if df.empty:
        st.info("No active employee profiles registered yet for this corporate entity.")
    else:
        # সার্চ বার ইন্টিগ্রেশন
        search_q = st.text_input("🔍 Filter & Search Employee by Name, ID, or Designation Field")
        if search_q:
            df = df[df['Name'].str.contains(search_q, case=False, na=False) | 
                    df['ID'].str.contains(search_q, case=False, na=False) | 
                    df['Designation'].str.contains(search_q, case=False, na=False)]
                    
        st.markdown(f"**Total Records Found:** {len(df)}")
        
        # গ্রিড হেডার ডিজাইন
        h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([1.5, 3.5, 2.5, 2.5, 2])
        h_col1.markdown("**Employee ID**")
        h_col2.markdown("**Employee Info**")
        h_col3.markdown("**Contact No**")
        h_col4.markdown("**Guaranteed Salary**")
        h_col5.markdown("**Action**")
        st.markdown("<hr style='margin:4px 0px; border-color:#333;'>", unsafe_allow_html=True)
        
        # কার্ড ইন্টারফেসে প্রতি লাইনে ডাটা রেন্ডারিং
        for _, row in df.iterrows():
            c1, c2, c3, c4, c5 = st.columns([1.5, 3.5, 2.5, 2.5, 2])
            c1.markdown(f"`{row['ID']}`")
            c2.markdown(f"**{row['Name']}** ({row['Designation']})")
            c3.markdown(f"📞 {row['Mobile'] or '-'}")
            c4.markdown(f"**{row['Total Package (৳)']:,.1f} ৳**")
            
            # ডায়ালগ প্রোফাইল দেখার বাটন ট্রিগার
            if c5.button("👁️ View Profile", key=f"v_emp_{row['ID']}", use_container_width=True):
                st.session_state.active_emp_id = row['ID']
                st.rerun()
            st.markdown("<hr style='margin:2px 0px; border-color:#222; border-style:dashed;'>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 🤝 সেকশন: নতুন সেকেন্ড পার্টি এন্ট্রি (Action: Add New Second Party)
# ------------------------------------------------------------------------------
elif current_action == "Add New Second Party":
    st.markdown(f"### 🤝 Register New Second Party Account Ledger ({current_company})")
    with st.form("add_sp_form_main", clear_on_submit=True):
        party_name = st.text_input("Second Party Corporate Name *")
        contact_number = st.text_input("Primary Contact / Mobile Number")
        comments_01 = st.text_input("Primary Comments / Description")
        comments_02 = st.text_input("Secondary Alternative Details")
        
        if st.form_submit_button("💾 Save Account Ledger", use_container_width=True):
            if not party_name.strip():
                st.error("Second Party Corporate Name is a mandatory field!")
            else:
                try:
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status)
                        VALUES (?, ?, ?, ?, ?, 'Active')
                    """, (current_company, party_name.strip(), contact_number.strip(), comments_01.strip(), comments_02.strip()))
                    conn.commit(); conn.close()
                    st.success(f"Second party ledger '{party_name}' successfully indexed into directory database.")
                except sqlite3.IntegrityError:
                    st.error("An identical account ledger name already exists under this enterprise segment profile!")

# ------------------------------------------------------------------------------
# 🤝 সেকশন: সেকেন্ড পার্টি রেজিস্ট্রি ভিউ (Action: View All Second Parties)
# ------------------------------------------------------------------------------
elif current_action == "View All Second Parties":
    st.markdown(f"### 📖 Second Party Account Directory Registry ({current_company})")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, party_name, contact_number, comments_01, status FROM second_parties WHERE company=?", conn)
    conn.close()
    
    if df.empty:
        st.info("No ledger account profiles configured yet for this business entity.")
    else:
        search_q = st.text_input("🔍 Filter Registry by Party Name or Phone Number Fields")
        if search_q:
            df = df[df['party_name'].str.contains(search_q, case=False, na=False) | 
                    df['contact_number'].str.contains(search_q, case=False, na=False)]
                    
        st.markdown(f"**Total Indexed Ledger Parties:** {len(df)}")
        
        h_c1, h_c2, h_c3, h_c4 = st.columns([4, 3, 2, 2])
        h_c1.markdown("**Account Ledger Name**")
        h_c2.markdown("**Contact Reference**")
        h_c3.markdown("**Current Status**")
        h_c4.markdown("**Action**")
        st.markdown("<hr style='margin:4px 0px; border-color:#333;'>", unsafe_allow_html=True)
        
        for _, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([4, 3, 2, 2])
            c1.markdown(f"**{row['party_name']}** <br><small style='color:#777;'>{row['comments_01'] or ''}</small>", unsafe_allow_html=True)
            c2.markdown(f"📞 {row['contact_number'] or '-'}")
            
            p_status = row['status'] or "Active"
            st_color = "#10b981" if p_status == "Active" else "#ef4444"
            c3.markdown(f"<span style='color:{st_color}; font-weight:bold;'>{p_status}</span>", unsafe_allow_html=True)
            
            if c4.button("⚙️ Access Profile", key=f"v_party_{row['id']}", use_container_width=True):
                st.session_state.active_party_id = row['id']
                st.rerun()
            st.markdown("<hr style='margin:2px 0px; border-color:#222; border-style:dashed;'>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 💰 সেকশন: ক্যাশ খাতা ও ব্যালেন্স শিট ম্যানেজমেন্ট (Action: Cash Management)
# ------------------------------------------------------------------------------
elif current_action == "Cash Management":
    # সিএসএস স্টাইল ইন্টিগ্রেশন
    st.markdown("""
        <style>
        .hdr-green { background-color: #0d533f; color: white; padding: 8px 15px; border-radius: 4px; font-weight: bold; font-size: 14px; text-align: center; }
        .hdr-red { background-color: #7a1c1c; color: white; padding: 8px 15px; border-radius: 4px; font-weight: bold; font-size: 14px; text-align: center; }
        .folder-lbl { color: #f39c12; font-weight: bold; font-size: 14px; margin-top: 10px; margin-bottom: 10px; }
        .meta-label-vertical { line-height: 38px; font-size: 13.5px; color: #bbb; font-weight: 500; }
        .meta-value-vertical { line-height: 38px; font-size: 15px; color: white; font-weight: bold; text-align: right; padding-right: 10px; }
        .table-column-title { background-color: #262626; padding: 6px; text-align: center; font-size: 12px; font-weight: bold; color: #00ff88; border-radius: 3px; border: 1px solid #333; margin-bottom: 8px; }
        </style>
    """, unsafe_allow_html=True)
    
    st.markdown(f"### 💰 Core Daily Cash Book Ledger System ({current_company})")
    
    tab1, tab2 = st.tabs(["📥 Daily Data Entry Grid Panel", "📖 Historical Dynamic Ledger Reports"])
    
    # ----------------------------------------------------------------------
    # 📥 ট্যাব ১: দৈনিক ক্যাশ ইনপুট গ্রিড (Tab 1: Daily Grid Input)
    # ----------------------------------------------------------------------
    with tab1:
        # টপ লেভেল কন্ট্রোল: তারিখ সিলেকশন বার
        m_col_a, m_col_b = st.columns([3, 5])
        date_str = m_col_a.date_input("📆 Select Ledger Accounting Date", value=datetime.today(), key="cash_ledger_master_date").strftime('%Y-%m-%d')
        
        # সেশন স্টেটে ডাইনামিক রো কাউন্টার ইনিশিয়ালাইজেশন (ডিফল্ট ৫টি করে রো সেট করা হচ্ছে)
        if "num_rows_in" not in st.session_state: st.session_state.num_rows_in = 5
        if "num_rows_out" not in st.session_state: st.session_state.num_rows_out = 5
        
        # ডাটাবেজ থেকে একটিভ সেকেন্ড পার্টিদের ড্রপডাউন লিস্টের জন্য পুল করা
        db_conn = sqlite3.connect(DB_NAME)
        party_tuples = db_conn.execute("SELECT party_name FROM second_parties WHERE company=? AND status='Active' ORDER BY party_name ASC", (current_company,)).fetchall()
        db_conn.close()
        active_parties_list = [""] + [p[0] for p in party_tuples]
        
        # এক্সেল আপলোড এবং বাল্ক কন্ট্রোল এক্সপ্যান্ডার
        with m_col_b.expander("⚙️ Advanced Excel Sheet Import & Data Synchronization Tools"):
            excel_file = st.file_uploader("📥 Upload Automated Backup Excel Document File", type=["xlsx"], key="cash_excel_file_uploader")
            accept_all_dates = st.multiselect("⚙️ Excel Import Filter Configuration Options:", ["Import for all excel worksheet dates"], default=[])
            
            col_b1, col_b2 = st.columns(2)
            # ফর্ম ক্লিয়ার বাটন (রিসেট হয়ে আবার ডিফল্ট ৫টি রো-তে ফিরে আসবে)
            if col_b1.button("🧹 Reset Form (Clear Sheet Grid)", key="reset_cash_form_btn", use_container_width=True):
                st.session_state.num_rows_in = 5
                st.session_state.num_rows_out = 5
                for i in range(200):
                    st.session_state[f"c_p_in_{i}"] = ""; st.session_state[f"c_a_in_{i}"] = 0.0; st.session_state[f"c_r_in_{i}"] = ""
                    st.session_state[f"c_p_out_{i}"] = ""; st.session_state[f"c_a_out_{i}"] = 0.0; st.session_state[f"c_r_out_{i}"] = ""
                st.rerun()
                
            if excel_file is not None:
                if col_b2.button("📊 Load Excel Data Into Input Grid", type="secondary", use_container_width=True):
                    try:
                        df = pd.read_excel(excel_file)
                        if len(df.columns) < 5:
                            st.error("Excel table mismatch. Must contain 5 standard columns: [Date, Type, Second Party, Amount, Detail].")
                        else:
                            df.columns = ['Date', 'Type', 'Second Party', 'Amount', 'Detail']
                            df['Date'] = df['Date'].astype(str).str.strip()
                            
                            # কন্ডিশনাল ডেট ফিল্টারিং লজিক
                            if "Import for all excel worksheet dates" not in accept_all_dates:
                                df = df[df['Date'] == date_str]
                                
                            df_in = df[df['Type'].str.lower().str.contains('in', na=False)]
                            df_out = df[df['Type'].str.lower().str.contains('out', na=False)]
                            
                            # নতুন রো সাইজ ডাইনামিক এসাইনমেন্ট (মিনিমাম ৫ টি)
                            st.session_state.num_rows_in = max(5, len(df_in))
                            st.session_state.num_rows_out = max(5, len(df_out))
                            
                            for idx, r in enumerate(df_in.to_dict(orient='records')):
                                st.session_state[f"c_p_in_{idx}"] = str(r['Second Party']) if str(r['Second Party']) in active_parties_list else ""
                                st.session_state[f"c_a_in_{idx}"] = float(r['Amount'] or 0.0)
                                st.session_state[f"c_r_in_{idx}"] = str(r['Detail'] or "") if str(r['Detail']) != 'nan' else ""
                                
                            for idx, r in enumerate(df_out.to_dict(orient='records')):
                                st.session_state[f"c_p_out_{idx}"] = str(r['Second Party']) if str(r['Second Party']) in active_parties_list else ""
                                st.session_state[f"c_a_out_{idx}"] = float(r['Amount'] or 0.0)
                                st.session_state[f"c_r_out_{idx}"] = str(r['Detail'] or "") if str(r['Detail']) != 'nan' else ""
                            st.rerun()
                    except Exception as ex:
                        st.error(f"Error parsing bulk excel sheet metadata: {ex}")
        
        # পূর্ববর্তী দিনের সমাপনী ব্যালেন্স হিসাব করে অটো লোড
        hist = get_historical_closing_balances(current_company, date_str)
        op_vault_val = hist["vault"]
        op_bank_val = hist["bank"]
        op_adv_val = hist["advance"]
        op_due_val = hist["due"]
        
        # বর্তমান দিনের এডিটেবল ওপেনিং ওভাররাইট কন্ট্রোল সিস্টেম
        conn = sqlite3.connect(DB_NAME)
        for key, sys_code, default_v in [("vault", "__SYS_OP_VAULT__", op_vault_val), ("bank", "__SYS_OP_BANK__", op_bank_val), ("advance", "__SYS_OP_ADVANCE__", op_adv_val), ("due", "__SYS_OP_DUE__", op_due_val)]:
            exist_val = conn.execute("SELECT amount FROM cash_transactions WHERE company=? AND date=? AND second_party=? LIMIT 1", (current_company, date_str, sys_code)).fetchone()
            if exist_val: hist[key] = exist_val[0]
            else: hist[key] = default_v
        conn.close()
        
        # মূল ২ কলাম লে-আউট গ্রিড রেন্ডারিং
        main_col1, main_col2 = st.columns(2)
        
        # 🟢 বাম কলাম: CASH RECEIVE (জমা)
        with main_col1:
            st.markdown('<div class="hdr-green">🛸 CASH RECEIVE Ledger Section</div>', unsafe_allow_html=True)
            st.markdown('<div class="folder-lbl">📁 Opening Cash Balance Matrices (Automated History Balance):</div>', unsafe_allow_html=True)
            
            l_r1_c1, l_r1_c2 = st.columns([7, 5])
            l_r1_c1.markdown('<div class="meta-label-vertical">Opening Vault Cash Balance:</div>', unsafe_allow_html=True)
            v_vault = l_r1_c2.number_input("Vault Opening Overwrite", value=float(hist["vault"]), label_visibility="collapsed", key="v_op_vault", step=500.0)
            
            l_r2_c1, l_r2_c2 = st.columns([7, 5])
            l_r2_c1.markdown('<div class="meta-label-vertical">Opening Bank Credit Account Balance:</div>', unsafe_allow_html=True)
            v_bank = l_r2_c2.number_input("Bank Opening Overwrite", value=float(hist["bank"]), label_visibility="collapsed", key="v_op_bank", step=500.0)
            
            l_r3_c1, l_r3_c2 = st.columns([7, 5])
            l_r3_c1.markdown('<div class="meta-label-vertical">Opening Total Advanced Payments Ledger:</div>', unsafe_allow_html=True)
            v_advance = l_r3_c2.number_input("Advance Opening Overwrite", value=float(hist["advance"]), label_visibility="collapsed", key="v_op_advance", step=500.0)
            
            l_r4_c1, l_r4_c2 = st.columns([7, 5])
            l_r4_c1.markdown('<div class="meta-label-vertical">Opening Net Outstanding Market Due Balance:</div>', unsafe_allow_html=True)
            v_due = l_r4_c2.number_input("Due Opening Overwrite", value=float(hist["due"]), label_visibility="collapsed", key="v_op_due", step=500.0)
            
            total_opening_calc = v_vault + v_bank + v_advance + v_due
            st.markdown(f"<p style='text-align:right; font-weight:bold; color:#00ff88; margin-top:5px; padding-right:15px;'>Aggregate Initial Opening Cap: {total_opening_calc:,.2f} ৳</p>", unsafe_allow_html=True)
            
        # 🔴 ডান কলাম: CASH PAY OUT / CLOSING (খরচ ও সমাপনী)
        with main_col2:
            st.markdown('<div class="hdr-red">🛸 CASH PAY OUT & CLOSING Statement Section</div>', unsafe_allow_html=True)
            st.markdown('<div class="folder-lbl">📁 Closing Cash Balance Matrices (Calculate Physical Status):</div>', unsafe_allow_html=True)
            
            r_r1_c1, r_r1_c2 = st.columns([7, 5])
            r_r1_c1.markdown('<div class="meta-label-vertical">Tonight Closing Vault Liquid Cash Box:</div>', unsafe_allow_html=True)
            m_vault = r_r1_c2.number_input("Closing Vault Cash Inflow", value=0.0, step=500.0, label_visibility="collapsed", key="v_cl_vault")
            
            r_r2_c1, r_r2_c2 = st.columns([7, 5])
            r_r2_c1.markdown('<div class="meta-label-vertical">Tonight Closing Bank Book Multi-Account:</div>', unsafe_allow_html=True)
            m_bank = r_r2_c2.number_input("Closing Bank Balance Inflow", value=0.0, step=500.0, label_visibility="collapsed", key="v_cl_bank")
            
            r_r3_c1, r_r3_c2 = st.columns([7, 5])
            r_r3_c1.markdown('<div class="meta-label-vertical">Tonight Closing Accumulative Advance Bills:</div>', unsafe_allow_html=True)
            m_advance = r_r3_c2.number_input("Closing Advance Inflow", value=0.0, step=500.0, label_visibility="collapsed", key="v_cl_advance")
            
            r_r4_c1, r_r4_c2 = st.columns([7, 5])
            r_r4_c1.markdown('<div class="meta-label-vertical">Tonight Closing Net Uncollected Outstanding Market Dues:</div>', unsafe_allow_html=True)
            m_due = r_r4_c2.number_input("Closing Due Inflow", value=0.0, step=500.0, label_visibility="collapsed", key="v_cl_due")
            
            total_closing_calc = m_vault + m_bank + m_advance + m_due
            st.markdown(f"<p style='text-align:right; font-weight:bold; color:#ff5555; margin-top:5px; padding-right:15px;'>Aggregate Final Closing Asset: {total_closing_calc:,.2f} ৳</p>", unsafe_allow_html=True)
            
        st.markdown("<hr style='margin:15px 0px; border-color:#444;'>", unsafe_allow_html=True)
        
        # ডাইনামিক ছক এন্ট্রি মডিউল গ্রিড লেআউট
        grid_col1, grid_col2 = st.columns(2)
        
        # জমার ডাইনামিক রো তৈরি
        with grid_col1:
            st.markdown('<p style="color:#00ff88; font-weight:bold; margin-bottom:0;">➕ Today\'s Cash Inflows Records Grid (RECEIVE):</p>', unsafe_allow_html=True)
            h_r1, h_r2, h_r3 = st.columns([5, 3, 4])
            h_r1.markdown('<div class="table-column-title">Second Party Account</div>', unsafe_allow_html=True)
            h_r2.markdown('<div class="table-column-title">Amount ৳</div>', unsafe_allow_html=True)
            h_r3.markdown('<div class="table-column-title">Transaction Remarks</div>', unsafe_allow_html=True)
            
            inputs_in = []
            for i in range(st.session_state.num_rows_in):
                r_r1, r_r2, r_r3 = st.columns([5, 3, 4])
                p_val = r_r1.selectbox("Party", active_parties_list, key=f"c_p_in_{i}", label_visibility="collapsed")
                a_val = r_r2.number_input("Amount", min_value=0.0, step=100.0, key=f"c_a_in_{i}", label_visibility="collapsed")
                r_val = r_r3.text_input("Remarks", key=f"c_r_in_{i}", label_visibility="collapsed")
                if p_val and a_val > 0:
                    inputs_in.append({'party': p_val, 'amount': a_val, 'remarks': r_val.strip()})
            if st.button("➕ Add 1 More Inflow Row", key="add_row_in_btn"):
                st.session_state.num_rows_in += 1; st.rerun()
                
        # খরচের ডাইনামিক রো তৈরি  
        with grid_col2:
            st.markdown('<p style="color:#ff5555; font-weight:bold; margin-bottom:0;">➖ Today\'s Cash Outflows Records Grid (PAY OUT):</p>', unsafe_allow_html=True)
            h_r1, h_r2, h_r3 = st.columns([5, 3, 4])
            h_r1.markdown('<div class="table-column-title">Second Party Account</div>', unsafe_allow_html=True)
            h_r2.markdown('<div class="table-column-title">Amount ৳</div>', unsafe_allow_html=True)
            h_r3.markdown('<div class="table-column-title">Transaction Remarks</div>', unsafe_allow_html=True)
            
            inputs_out = []
            for i in range(st.session_state.num_rows_out):
                r_r1, r_r2, r_r3 = st.columns([5, 3, 4])
                p_val = r_r1.selectbox("Party", active_parties_list, key=f"c_p_out_{i}", label_visibility="collapsed")
                a_val = r_r2.number_input("Amount", min_value=0.0, step=100.0, key=f"c_a_out_{i}", label_visibility="collapsed")
                r_val = r_r3.text_input("Remarks", key=f"c_r_out_{i}", label_visibility="collapsed")
                if p_val and a_val > 0:
                    inputs_out.append({'party': p_val, 'amount': a_val, 'remarks': r_val.strip()})
            if st.button("➕ Add 1 More Outflow Row", key="add_row_out_btn"):
                st.session_state.num_rows_out += 1; st.rerun()
                
        # সাবমিশন ও ডাটাবেজ কমিট এক্সিকিউশন বাটন
        st.markdown("<hr style='margin:20px 0px; border-color:#ff5555;'>", unsafe_allow_html=True)
        if st.button("🚀 Commit Sheet & Synchronize Complete Cash Book", type="primary", use_container_width=True):
            try:
                conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                cursor.execute("DELETE FROM cash_transactions WHERE company=? AND date=?", (current_company, date_str))
                
                # সিস্টেম ওপেনিং ও সমাপনী ব্যালেন্স এন্ট্রি সংরক্ষণ লজিক
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_OP_VAULT__', 'System System', ?, 'Opening Vault')", (date_str, current_company, v_vault))
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_OP_BANK__', 'System System', ?, 'Opening Bank')", (date_str, current_company, v_bank))
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_OP_ADVANCE__', 'System System', ?, 'Opening Advance')", (date_str, current_company, v_advance))
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_OP_DUE__', 'System System', ?, 'Opening Due')", (date_str, current_company, v_due))
                
                # টেবিল গ্রিড ডেটা লুপ চালিয়ে সংরক্ষণ
                for r in inputs_in:
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash In', ?, ?)", (date_str, current_company, r['party'], r['amount'], r['remarks']))
                for r in inputs_out:
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash Out', ?, ?)", (date_str, current_company, r['party'], r['amount'], r['remarks']))
                    
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_VAULT__', 'System Balance', ?, 'Closing Vault')", (date_str, current_company, m_vault))
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_BANK__', 'System Balance', ?, 'Closing Bank')", (date_str, current_company, m_bank))
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_ADVANCE__', 'System Balance', ?, 'Closing Advance')", (date_str, current_company, m_advance))
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_DUE__', 'System Balance', ?, 'Closing Due')", (date_str, current_company, m_due))
                
                conn.commit()
                st.toast(f"Success! Complete digital records for {date_str} committed and fully synced.", icon="✅")
                import time; time.sleep(0.4); st.rerun()
            except Exception as e:
                st.error(f"Error executing database synchronization transaction: {e}")
            finally: conn.close()
            
    # ----------------------------------------------------------------------
    # 📖 ট্যাব ২: ডাইনামিক ফিল্টার খতিয়ান (Tab 2: Advanced Ledger Filter Reports)
    # ----------------------------------------------------------------------
    with tab2:
        st.markdown("##### 📊 Dynamic Cash Ledger Directory & Analytical Statements")
        c_r1, c_r2, c_r3 = st.columns(3)
        start_d = c_r1.date_input("Start Date Filter", value=datetime.today())
        end_d = c_r2.date_input("End Date Filter", value=datetime.today())
        
        # সেকেন্ড পার্টি ড্রপডাউন কালেকশন পুল
        conn = sqlite3.connect(DB_NAME)
        db_parties = [p[0] for p in conn.execute("SELECT DISTINCT second_party FROM cash_transactions WHERE company=? AND second_party NOT LIKE '__SYS_%' ORDER BY second_party ASC", (current_company,)).fetchall()]
        conn.close()
        sel_party = c_r3.selectbox("Filter Target Account Party Profile", options=["All Account Ledgers combined"] + db_parties)
        
        # নির্দিষ্ট ফিল্টার প্যারামিটার অনুযায়ী ডাইনামিক ডাটা কুয়েরি
        ledger_query = """
            SELECT date as 'Date', second_party as 'Account Name', type as 'Flow Type', amount as 'Amount (৳)', remarks as 'Particular Description'
            FROM cash_transactions
            WHERE company=? AND type IN ('Cash In', 'Cash Out') AND date BETWEEN ? AND ?
        """
        params = [current_company, str(start_d), str(end_d)]
        if sel_party != "All Account Ledgers combined":
            ledger_query += " AND second_party=?"
            params.append(sel_party)
        ledger_query += " ORDER BY date DESC, id DESC"
        
        conn = sqlite3.connect(DB_NAME); df_report = pd.read_sql_query(ledger_query, conn); conn.close()
        
        if df_report.empty:
            st.info("No corporate statements matching selected ledger bounds found.")
        else:
            st.dataframe(df_report, use_container_width=True, hide_index=True)
            
            # পার্টি-ভিত্তিক ডাইনামিক পুঞ্জীভূত সারসংক্ষেপ হিসাব বিবরণী
            summary_query = """
                SELECT second_party as 'Second Party Account', 
                       SUM(CASE WHEN type='Cash In' THEN amount ELSE 0 END) as 'Total Cash Receipts (৳)', 
                       SUM(CASE WHEN type='Cash Out' THEN amount ELSE 0 END) as 'Total Cash Payments (৳)' 
                FROM cash_transactions 
                WHERE company=? AND type IN ('Cash In', 'Cash Out') AND date BETWEEN ? AND ?
            """
            sum_params = [current_company, str(start_d), str(end_d)]
            if sel_party != "All Account Ledgers combined":
                summary_query += " AND second_party=?"; sum_params.append(sel_party)
            summary_query += " GROUP BY second_party ORDER BY second_party ASC"
            
            conn = sqlite3.connect(DB_NAME); sum_df = pd.read_sql_query(summary_query, conn, params=sum_params); conn.close()
            sum_df['Net Operational Balance (৳)'] = sum_df['Total Cash Receipts (৳)'] - sum_df['Total Cash Payments (৳)']
            
            st.markdown("<br>📊 **Party-wise Aggregated Summary Ledger:**", unsafe_allow_html=True)
            st.dataframe(sum_df, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# 📉 সেকশন: কর্পোরেট খরচ হিসাব ও পেটি ক্যাশ (Action: Expense Management)
# ------------------------------------------------------------------------------
elif current_action == "Expense Management":
    st.markdown(f"### 📉 Corporate Expense Directory & Petty Cash Sub-Ledger ({current_company})")
    st.markdown("💡 *All expenses recorded under this module automatically reflect as cash outflows ('Cash Out') inside the system core 'Petty_Cash' control ledger.*")
    
    exp_tab1, exp_tab2 = st.tabs(["📥 Manual Entry & Document Upload Panel", "📖 Historical Expense Ledgers Directory"])
    
    # 📥 ট্যাব ১: বাল্ক ও ম্যানুয়াল খরচ এন্ট্রি (Tab 1: Entry & Excel Processing)
    with exp_tab1:
        st.markdown("##### ⚙️ Configuration & Bulk Excel Sheet Sync")
        exp_file = st.file_uploader("Upload Integrated Excel Document Sheet", type=["xlsx"], key="bulk_exp_uploader_file")
        if exp_file is not None:
            if st.button("🚀 Process Bulk Expense Compilation", type="secondary", use_container_width=True):
                try:
                    edf = pd.read_excel(exp_file)
                    reqs = ['date', 'type', 'category', 'amount']
                    if not all(c in edf.columns for c in reqs):
                        st.error("Excel sheet columns layout invalid. Requires: [date, type, category, sub_category, amount, description]")
                    else:
                        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                        count = 0
                        for _, r in edf.iterrows():
                            r_date = str(r['date']).strip()
                            r_type = str(r['type']).strip()
                            r_cat = str(r['category']).strip()
                            r_subcat = str(r.get('sub_category', '')).strip()
                            r_rem = str(r.get('description', '')).strip()
                            r_amt = float(r['amount'] or 0.0)
                            
                            if r_date and r_date != 'nan' and r_cat and r_cat != 'nan' and r_amt > 0:
                                formatted_remarks = f"[{r_type} -> {r_cat} -> {r_subcat}] {r_rem}".strip()
                                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)", (r_date, current_company, r_amt, formatted_remarks))
                                count += 1
                        conn.commit(); conn.close()
                        if count > 0: st.success(f"Successfully processed and synced {count} bulk expenses records into ledger.")
                        else: st.error("No valid entry lines discovered inside the uploaded workbook sheet.")
                except Exception as ex: st.error(f"Error parsing bulk excel datasheet rows: {ex}")
                
        st.markdown("<hr style='margin:15px 0px; border-color:#333;'>", unsafe_allow_html=True)
        st.markdown("##### 📝 Manual Multi-Row Expense Statement Grid Entry")
        
        # খরচ এন্ট্রির জন্য ম্যানুয়াল মাল্টি-রো উইজেট ফর্ম
        with st.form("manual_expense_entry_form_v1", clear_on_submit=True):
            e_date = st.date_input("Expense Accounting Date", value=datetime.today())
            
            h_col1, h_col2, h_col3, h_col4 = st.columns(4)
            e_type = h_col1.selectbox("Expense Class Type", ["Office Expense", "Staff Welfare", "Marketing", "Logistics", "Utility Bills", "Others"])
            e_category = h_col2.text_input("Primary Expense Category Title *")
            e_subcategory = h_col3.text_input("Sub-Category Details")
            e_amount = h_col4.number_input("Net Expense Amount (৳) *", min_value=0.0, step=500.0)
            e_remarks = st.text_input("Detailed Particular Narrative Description")
            
            if st.form_submit_button("💾 Save Manual Expense Entry", use_container_width=True):
                if not e_category.strip() or e_amount <= 0:
                    st.error("Expense Category Title and a positive valid Net Amount are required parameters.")
                else:
                    formatted_remarks = f"[{e_type} -> {e_category.strip()} -> {e_subcategory.strip()}] {e_remarks.strip()}".strip()
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)", (str(e_date), current_company, e_amount, formatted_remarks))
                    conn.commit(); conn.close()
                    st.success("Manual operational expense line successfully debited to Petty Cash system.")
                    
    # 📖 ট্যাব ২: খরচ খতিয়ান ডিরেক্টরি (Tab 2: View History Reports)
    with exp_tab2:
        st.markdown("##### 📊 Corporate Expenses Directory Balance Logs (Petty Cash Ledger)")
        conn = sqlite3.connect(DB_NAME)
        exp_df = pd.read_sql_query("""
            SELECT date as 'Date Stamp', amount as 'Disbursed Amount (৳)', remarks as 'Description Narrative Details' 
            FROM cash_transactions WHERE company = ? AND second_party = 'Petty_Cash' AND type = 'Cash Out' ORDER BY date DESC, id DESC
        """, conn, params=(current_company,))
        conn.close()
        
        if not exp_df.empty:
            st.metric("💰 Accumulative Total Company Expenses (Petty Cash Pool)", f"{exp_df['Disbursed Amount (৳)'].sum():,.1f} ৳")
            st.dataframe(exp_df, use_container_width=True, hide_index=True)
        else:
            st.info("No corporate expense records matching standard parameters registered in this workspace block.")

# ------------------------------------------------------------------------------
# 📁 সেকশন: বিবিধ ও ফুটকর অ্যাকাউন্টস (Action: Others)
# ------------------------------------------------------------------------------
elif current_action == "Others":
    st.markdown(f"### 📁 Others / Auxiliary Account Modality ({current_company})")
    st.info("💡 Miscellaneous accounting logs, external adjustments, and secondary parameters data entries will be integrated here.")

# ==============================================================================
# ১০. গ্লোবাল একটিভ ডায়ালগ কন্ট্রোলার (Global Pop-up Windows Execution Trigger)
# ==============================================================================
# কোনো কর্মচারী বা সেকেন্ড পার্টির আইডি পপআপ ভিউ ট্র্যাকিং ট্রিগারে থাকলে তা রেন্ডার করা হচ্ছে।
if st.session_state.active_emp_id:
    show_employee_details(st.session_state.active_emp_id, st.session_state.current_company)

if st.session_state.active_party_id:
    show_second_party_details(st.session_state.active_party_id)
