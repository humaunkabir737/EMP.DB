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
# লগইন সিস্টেম (সুরক্ষার জন্য রোল-বেসড অ্যাক্সেসসহ)
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
                # ১. এডমিন ইউজার (সব দেখতে পাবেন)
                if username == "admin" and password == "jabed2026":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.session_state.current_action = None 
                    st.success("এডমিন হিসেবে লগইন সফল হয়েছে!")
                    import time
                    time.sleep(0.5)
                    st.rerun()
                
                # ২. বিকাশ ইউজার (শুধু বিকাশ ফোল্ডার দেখতে পাবেন)
                elif username == "bKash_User" and password == "bkash2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "bKash_User"
                    st.session_state.current_company = "bKash" 
                    st.session_state.current_action = None 
                    st.success("বিকাশ ইউজার লগইন সফল!")
                    import time
                    time.sleep(0.5)
                    st.rerun()
                
                # ৩. জিপি ইউজার (শুধু জিপি ফোল্ডার দেখতে পাবেন)
                elif username == "GP_User" and password == "gp2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "GP_User"
                    st.session_state.current_company = "GP" 
                    st.session_state.current_action = None 
                    st.success("GP ইউজার লগইন সফল!")
                    import time
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("ভুল ইউজারনেম অথবা পাসওয়ার্ড! আবার চেষ্টা করুন।")
    st.stop()

# ==============================================================================
# ২. ডাইনামিক পাথ ও ফোল্ডার সেটআপ
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "jabed_enterprise.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploaded_docs")
IMAGE_DIR = os.path.join(BASE_DIR, "Related Image")

PHOTO_DIR = os.path.join(BASE_DIR, "employee_photos")
EMP_NID_DIR = os.path.join(BASE_DIR, "nid_photos")
GUAR_PHOTO_DIR = os.path.join(BASE_DIR, "guarantor_photos")
GUAR_NID_DIR = os.path.join(BASE_DIR, "guarantor_nids")

# ==============================================================================
# ৩. ডাটাবেজ এবং অ্যাডভান্সড মাইগ্রেশন লজিক (Error Resolution)
# ==============================================================================
def init_db():
    for folder in [UPLOAD_DIR, IMAGE_DIR, PHOTO_DIR, EMP_NID_DIR, GUAR_PHOTO_DIR, GUAR_NID_DIR]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # কর্মচারীদের টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            emp_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            designation TEXT,
            mobile TEXT,
            alt_contact TEXT,
            join_date TEXT,
            basic_salary REAL,
            variable_salary REAL,
            total_salary REAL,
            company TEXT NOT NULL,
            father_name TEXT,
            father_nid TEXT,
            mother_name TEXT,
            emp_nid TEXT,
            guarantor_name TEXT,
            guarantor_nid TEXT,
            guarantor_mobile TEXT
        )
    ''')
    
    # 🚨 সেকেন্ড পার্টি টেবিল মাইগ্রেশন কন্ট্রোল (কোম্পানি পৃথকীকরণ ও এরর ফিক্স)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='second_parties'")
    table_exists = cursor.fetchone()
    
    if table_exists:
        cursor.execute("PRAGMA table_info(second_parties)")
        existing_sp_columns = [col[1] for col in cursor.fetchall()]
        
        # যদি 'company' কলামটি না থাকে, তার মানে এটি পুরনো কাঠামোর টেবিল। একে রূপান্তর করতে হবে।
        if 'company' not in existing_sp_columns:
            has_status = 'status' in existing_sp_columns
            
            # ব্যাকআপ নেওয়া ও নতুন টেবিল তৈরি
            cursor.execute("ALTER TABLE second_parties RENAME TO old_second_parties")
            cursor.execute('''
                CREATE TABLE second_parties (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    company TEXT NOT NULL,
                    party_name TEXT NOT NULL, 
                    contact_number TEXT, 
                    comments_01 TEXT, 
                    comments_02 TEXT,
                    status TEXT DEFAULT 'Active',
                    UNIQUE(company, party_name)
                )
            ''')
            
            # পুরনো ডেটাগুলোকে ডিফল্ট 'bKash' হিসেবে নতুন টেবিলে কপি করা
            if has_status:
                cursor.execute('''
                    INSERT INTO second_parties (id, company, party_name, contact_number, comments_01, comments_02, status)
                    SELECT id, 'bKash', party_name, contact_number, comments_01, comments_02, IFNULL(status, 'Active') FROM old_second_parties
                ''')
            else:
                cursor.execute('''
                    INSERT INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status)
                    SELECT 'bKash', party_name, contact_number, comments_01, comments_02, 'Active' FROM old_second_parties
                ''')
            cursor.execute("DROP TABLE old_second_parties")
    else:
        # একদম ফ্রেশ ডাটাবেজ হলে টেবিল তৈরি করার স্ট্রাকচার
        cursor.execute('''
            CREATE TABLE second_parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                company TEXT NOT NULL,
                party_name TEXT NOT NULL, 
                contact_number TEXT, 
                comments_01 TEXT, 
                comments_02 TEXT,
                status TEXT DEFAULT 'Active',
                UNIQUE(company, party_name)
            )
        ''')
    
    # 🎯 ডিফল্ট সেকেন্ড পার্টি ডেটা ইনসার্ট (শুধুমাত্র bKash কোম্পানির জন্য এক্সক্লুসিভ)
    default_parties = ["Mother_Wallet", "Hand_Cash", "Petty_Cash", "Bank", "BGP", "Dulal", "Shafayat", "Madina", "Owner", "GAS", "Auto_Rice", "Others", "bKash", "Commission", "Al_Arafa", "Rekit", "DMCBL", "Kabita_Mami", "Ashim_Da", "Al_Amin"]
    for party in default_parties:
        cursor.execute("""
            INSERT OR IGNORE INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) 
            VALUES ('bKash', ?, '', '', '', 'Active')
        """, (party,))
    
    # ক্যাশ ট্রানজেকশন (ক্যাশ খাতা) টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            company TEXT NOT NULL,
            second_party TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            remarks TEXT
        )
    ''')
    
    # কর্মচারী টেবিলের কলাম মাইগ্রেশন চেক
    cursor.execute("PRAGMA table_info(employees)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    
    required_cols = {
        'company': "TEXT DEFAULT 'bKash'",
        'father_name': "TEXT",
        'father_nid': "TEXT",
        'mother_name': "TEXT",
        'emp_nid': "TEXT",
        'guarantor_name': "TEXT",
        'guarantor_nid': "TEXT",
        'guarantor_mobile': "TEXT"
    }
    
    for col_name, col_type in required_cols.items():
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type}")
            
    conn.commit()
    conn.close()

init_db()

# ==============================================================================
# ৪. গ্লোবাল সেশন স্টেট
# ==============================================================================
if 'current_company' not in st.session_state:
    st.session_state.current_company = "None"

if 'current_action' not in st.session_state:
    st.session_state.current_action = None

if 'active_emp_id' not in st.session_state:
    st.session_state.active_emp_id = None

if 'dialog_edit_mode' not in st.session_state:
    st.session_state.dialog_edit_mode = False

if 'active_party_id' not in st.session_state:
    st.session_state.active_party_id = None

if 'party_edit_mode' not in st.session_state:
    st.session_state.party_edit_mode = False

def open_edit_mode():
    st.session_state.dialog_edit_mode = True

def close_edit_mode():
    st.session_state.dialog_edit_mode = False

# ==============================================================================
# ৫. হেডার ডিজাইন
# ==============================================================================
def render_header():
    logo_html = ""
    has_logo = False
    for ext in ["png", "jpg", "jpeg"]:
        logo_path = os.path.join(IMAGE_DIR, f"logo.{ext}")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            logo_html = f'<img src="data:image/{ext};base64,{encoded}" style="height:55px; vertical-align: middle;">'
            has_logo = True
            break
            
    if has_logo:
        st.markdown(f"""
            <div style="text-align: center; margin-top: -15px; margin-bottom: 2px;">
                <div style="display: flex; justify-content: center; align-items: center; gap: 12px;">
                    {logo_html}
                    <h1 style="color: white; margin: 0; font-family: 'Times New Roman', serif; font-size: 38px; font-weight: bold; letter-spacing: 0.5px;">M/S JABED ENTERPRISE</h1>
                </div>
                <p style="color: #a0a0a0; margin: 6px 0 0 0; font-size: 14.5px; font-family: 'Arial', sans-serif; text-align: center;">394 Anima Plaza, Nagerbazar, Bagerhat Sadar, Bagerhat.</p>
            </div>
            <hr style="border: 1px solid #10b981; margin-top: 15px; margin-bottom: 25px;">
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="text-align: center; margin-top: -15px; margin-bottom: 2px;">
                <h1 style="color: white; margin: 0; font-family: 'Times New Roman', serif; font-size: 38px; font-weight: bold; letter-spacing: 0.5px;">M/S JABED ENTERPRISE</h1>
                <p style="color: #a0a0a0; margin: 6px 0 0 0; font-size: 14.5px; font-family: 'Arial', sans-serif; text-align: center;">394 Anima Plaza, Nagerbazar, Bagerhat Sadar, Bagerhat.</p>
            </div>
            <hr style="border: 1px solid #10b981; margin-top: 15px; margin-bottom: 25px;">
        """, unsafe_allow_html=True)

# ==============================================================================
# 🔍 সেকেন্ড পার্টির প্রোফাইল ডিটেইলস ও এডিট ডায়ালগ
# ==============================================================================
@st.dialog("Second Party Details", width="medium")
def show_second_party_details(party_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, party_name, contact_number, comments_01, comments_02, status FROM second_parties WHERE id = ?", (party_id,))
    party = cursor.fetchone()
    conn.close()
    
    if not party:
        st.error("Second Party not found!")
        st.session_state.active_party_id = None
        return
        
    p_id, p_name, p_contact, p_c1, p_c2, p_status = party
    if p_status is None:
        p_status = "Active"
        
    col_t1, col_t2 = st.columns([6, 2])
    with col_t1:
        if not st.session_state.party_edit_mode:
            if st.button("✏️ Edit", key="sp_edit_toggle_btn"):
                st.session_state.party_edit_mode = True
                st.rerun()
        else:
            if st.button("⬅️ Back to View", key="sp_view_toggle_btn"):
                st.session_state.party_edit_mode = False
                st.rerun()
    with col_t2:
        if st.button("❌ Close", use_container_width=True, key="sp_close_popup_btn"):
            st.session_state.active_party_id = None
            st.session_state.party_edit_mode = False
            st.rerun()
            
    st.markdown("---")
    
    if not st.session_state.party_edit_mode:
        # Read Only মোড
        st.markdown(f"### **Second Party Name:** {p_name}")
        st.markdown(f"**Contact Number:** {p_contact if p_contact else '-'}")
        st.markdown(f"**Comments 01:** {p_c1 if p_c1 else '-'}")
        st.markdown(f"**Comments 02:** {p_c2 if p_c2 else '-'}")
        
        status_color = "#10b981" if p_status == "Active" else "#ef4444"
        st.markdown(f"**Status:** <span style='color:{status_color}; font-weight:bold; font-size:16px;'>{p_status}</span>", unsafe_allow_html=True)
    else:
        # Edit মোড ফর্ম
        with st.form("edit_second_party_form_v1"):
            st.markdown("#### 📝 Update Second Party Info")
            new_p_name = st.text_input("Second Party Name *", value=p_name)
            new_p_contact = st.text_input("Contact Number", value=p_contact)
            new_p_c1 = st.text_input("Comments 01", value=p_c1)
            new_p_c2 = st.text_input("Comments 02", value=p_c2)
            new_p_status = st.selectbox("Status", ["Active", "Inactive"], index=0 if p_status == "Active" else 1)
            
            save_sp = st.form_submit_button("💾 Save Changes", use_container_width=True)
            if save_sp:
                if not new_p_name.strip():
                    st.error("Second Party Name খালি রাখা যাবে না!")
                else:
                    try:
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE second_parties 
                            SET party_name=?, contact_number=?, comments_01=?, comments_02=?, status=?
                            WHERE id=?
                        """, (new_p_name.strip(), new_p_contact.strip(), new_p_c1.strip(), new_p_c2.strip(), new_p_status, party_id))
                        conn.commit()
                        conn.close()
                        
                        st.toast("সেকেন্ড পার্টির তথ্য সফলভাবে আপডেট করা হয়েছে!", icon="✅")
                        st.session_state.active_party_id = None
                        st.session_state.party_edit_mode = False
                        import time
                        time.sleep(0.5)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("এই কোম্পানির আন্ডারে এই নামের আরেকটি সেকেন্ড পার্টি ইতিমধ্যে ডাটাবেজে বিদ্যমান!")

# ==============================================================================
# ৬. কর্মচারীর প্রোফাইল ডিটেইলস ডায়ালগ
# ==============================================================================
@st.dialog("Employee Profile Details", width="large")
def show_employee_details(emp_id, company):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary,
               father_name, father_nid, mother_name, emp_nid, guarantor_name, guarantor_nid, guarantor_mobile 
        FROM employees WHERE emp_id = ? AND company = ?
    """, (emp_id, company))
    emp = cursor.fetchone()
    conn.close()
    
    if not emp:
        st.error("Employee not found!")
        st.session_state.active_emp_id = None
        return
        
    (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary,
     father_name, father_nid, mother_name, emp_nid, guarantor_name, guarantor_nid, guarantor_mobile) = emp
    
    col_t1, col_t2 = st.columns([6, 2])
    with col_t1:
        if not st.session_state.dialog_edit_mode:
            st.button("✏️ Edit Profile", type="secondary", key="popup_edit_btn", on_click=open_edit_mode)
        else:
            st.button("⬅️ Back to View Mode", type="secondary", key="popup_back_btn", on_click=close_edit_mode)
    with col_t2:
        if st.button("❌ Close Window", use_container_width=True, key="popup_close_btn"):
            st.session_state.active_emp_id = None
            st.session_state.dialog_edit_mode = False
            st.rerun()
            
    st.markdown("---")
    
    img_folders = [PHOTO_DIR, EMP_NID_DIR, GUAR_PHOTO_DIR, GUAR_NID_DIR]
    emp_photo_path = os.path.join(PHOTO_DIR, f"{emp_id}_emp.png")
    emp_nid_path = os.path.join(EMP_NID_DIR, f"{emp_id}_nid.png")
    guar_photo_path = os.path.join(GUAR_PHOTO_DIR, f"{emp_id}_guar.png")
    guar_nid_path = os.path.join(GUAR_NID_DIR, f"{emp_id}_guar_nid.png")

    if not st.session_state.dialog_edit_mode:
        col_info, col_img = st.columns([4.5, 2.5])
        with col_info:
            st.markdown(f"### **Name:** {name}")
            st.markdown(f"**Employee ID:** `{emp_id}` | **Designation:** `{designation}`")
            st.markdown(f"**Mobile:** {mobile if mobile else '-'} | **Alternative Contact:** {alt_contact if alt_contact else '-'}")
            st.markdown(f"**Joining Date:** {join_date}")
            st.markdown(f"**Employee NID No:** {emp_nid if emp_nid else '-'}")
        
        with col_img:
            img_c1, img_c2 = st.columns(2)
            with img_c1:
                if os.path.exists(emp_photo_path):
                    st.image(emp_photo_path, caption="Emp Photo", use_container_width=True)
                else:
                    st.caption("[ No Photo ]")
            with img_c2:
                if os.path.exists(emp_nid_path):
                    st.image(emp_nid_path, caption="Emp NID Card", use_container_width=True)
                else:
                    st.caption("[ No NID Card ]")

        st.markdown("<h4 style='color:#1f852c; margin-top:10px;'>📂 Family Information</h4>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Father's Name:** {father_name if father_name else '-'}")
        with c2:
            st.markdown(f"**Mother's Name:** {mother_name if mother_name else '-'}")
            st.markdown(f"**Father's NID:** {father_nid if father_nid else '-'}")

        st.markdown("<h4 style='color:#1f852c; margin-top:10px;'>🛡️ Guarantor Details & Documents</h4>", unsafe_allow_html=True)
        g_col1, g_col2 = st.columns([4.5, 2.5])
        with g_col1:
            st.markdown(f"**Guarantor Name:** {guarantor_name if guarantor_name else '-'}")
            st.markdown(f"**Guarantor NID No:** {guarantor_nid if guarantor_nid else '-'}")
            st.markdown(f"**Guarantor Mobile:** {guarantor_mobile if guarantor_mobile else '-'}")
        with g_col2:
            g_img_c1, g_img_c2 = st.columns(2)
            with g_img_c1:
                if os.path.exists(guar_photo_path):
                    st.image(guar_photo_path, caption="Guar Photo", use_container_width=True)
                else:
                    st.caption("[ No Photo ]")
            with g_img_c2:
                if os.path.exists(guar_nid_path):
                    st.image(guar_nid_path, caption="Guar NID Card", use_container_width=True)
                else:
                    st.caption("[ No NID Card ]")

        st.markdown("<br>", unsafe_allow_html=True)
        st.success(f"**Salary Structure:** Basic: {basic_salary:,.1f} ৳ | Variable: {variable_salary:,.1f} ৳ | **Total Salary: {total_salary:,.1f} ৳**")

    else:
        if st.session_state.get('confirm_exit_prompt'):
            st.info("ℹ️ You haven't changed anything. Do you want to exit edit mode?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ OK", key="confirm_exit_ok", use_container_width=True):
                    st.session_state.active_emp_id = None
                    st.session_state.dialog_edit_mode = False
                    st.session_state.confirm_exit_prompt = False
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", key="confirm_exit_cancel", use_container_width=True):
                    st.session_state.confirm_exit_prompt = False
                    st.rerun()
            st.stop()
            
        with st.form("edit_employee_form_v10", clear_on_submit=False):
            st.markdown(f"#### 📝 Updating Profile for ID: `{emp_id}`")
            
            e_c1, e_c2 = st.columns(2)
            with e_c1:
                new_name = st.text_input("Name *", value=name)
                new_desig = st.selectbox("Designation", ["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"], index=["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"].index(designation) if designation in ["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"] else 0)
                new_mobile = st.text_input("Mobile", value=mobile)
                new_alt = st.text_input("Alternative Contact", value=alt_contact)
                new_emp_nid = st.text_input("Employee NID Number", value=emp_nid)
                
                st.markdown("##### 📸 Employee Documents Update")
                new_emp_img = st.file_uploader("Update Employee Photo", type=["png", "jpg", "jpeg"], key="edit_emp_img")
                new_emp_nid_img = st.file_uploader("Update Employee NID Card Image", type=["png", "jpg", "jpeg"], key="edit_emp_nid_img")
                
                st.markdown("##### 🛡️ Guarantor Details")
                new_g_name = st.text_input("Guarantor Name", value=guarantor_name)
                new_g_nid = st.text_input("Guarantor NID Number", value=guarantor_nid)
                new_g_mob = st.text_input("Guarantor Mobile", value=guarantor_mobile)
                
            with e_c2:
                try:
                    parsed_date = datetime.strptime(join_date, "%Y-%m-%d").date()
                except Exception:
                    parsed_date = datetime.now().date()
                new_date = st.date_input("Join Date", value=parsed_date)
                
                new_f_name = st.text_input("Father's Name", value=father_name)
                new_f_nid = st.text_input("Father's NID", value=father_nid)
                new_m_name = st.text_input("Mother's Name", value=mother_name)
                
                new_basic = st.number_input("Basic Salary", min_value=0.0, value=float(basic_salary))
                new_variable = st.number_input("Variable Salary", min_value=0.0, value=float(variable_salary))
                
                st.markdown("##### 📸 Guarantor Documents Update")
                new_guar_img = st.file_uploader("Update Guarantor Photo", type=["png", "jpg", "jpeg"], key="edit_guar_img")
                new_guar_nid_img = st.file_uploader("Update Guarantor NID Card Image", type=["png", "jpg", "jpeg"], key="edit_guar_nid_img")

            save_btn = st.form_submit_button("💾 Save All Profile Changes")
            if save_btn:
                import time
                c_new_name = (new_name or "").strip()
                c_new_mobile = (new_mobile or "").strip()
                c_new_alt = (new_alt or "").strip()
                c_new_f_name = (new_f_name or "").strip()
                c_new_f_nid = (new_f_nid or "").strip()
                c_new_m_name = (new_m_name or "").strip()
                c_new_emp_nid = (new_emp_nid or "").strip()
                c_new_g_name = (new_g_name or "").strip()
                c_new_g_nid = (new_g_nid or "").strip()
                c_new_g_mob = (new_g_mob or "").strip()
                
                safe_join_date = join_date if join_date else ""
                
                has_changed = (
                    c_new_name != name or
                    new_desig != designation or
                    c_new_mobile != mobile or
                    c_new_alt != alt_contact or
                    str(new_date) != str(safe_join_date) or
                    c_new_f_name != father_name or
                    c_new_f_nid != father_nid or
                    c_new_m_name != mother_name or
                    c_new_emp_nid != emp_nid or
                    c_new_g_name != guarantor_name or
                    c_new_g_nid != guarantor_nid or
                    c_new_g_mob != guarantor_mobile or
                    float(new_basic) != float(basic_salary) or
                    float(new_variable) != float(variable_salary) or
                    new_emp_img is not None or        
                    new_emp_nid_img is not None or
                    new_guar_img is not None or
                    new_guar_nid_img is not None
                )
                
                if not has_changed:
                    st.session_state.confirm_exit_prompt = True
                    st.rerun()
                elif not c_new_name:
                    st.error("Name খালি রাখা যাবে না!")
                else:
                    if new_emp_img:
                        Image.open(new_emp_img).save(emp_photo_path)
                    if new_emp_nid_img:
                        Image.open(new_emp_nid_img).save(emp_nid_path)
                    if new_guar_img:
                        Image.open(new_guar_img).save(guar_photo_path)
                    if new_guar_nid_img:
                        Image.open(new_guar_nid_img).save(guar_nid_path)
                        
                    new_total = new_basic + new_variable
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        UPDATE employees 
                        SET name=?, designation=?, mobile=?, alt_contact=?, join_date=?, basic_salary=?, variable_salary=?, total_salary=?,
                            father_name=?, father_nid=?, mother_name=?, emp_nid=?, guarantor_name=?, guarantor_nid=?, guarantor_mobile=?
                        WHERE emp_id=? AND company=?
                    """, (
                        c_new_name, new_desig, c_new_mobile, c_new_alt, str(new_date), new_basic, new_variable, new_total,
                        c_new_f_name, c_new_f_nid, c_new_m_name, c_new_emp_nid, c_new_g_name, c_new_g_nid, c_new_g_mob,
                        emp_id, company
                    ))
                    conn.commit()
                    conn.close()
                    
                    st.toast("कर्मীর সম্পূর্ণ তথ্য এবং ডকুমেন্ট সফলভাবে আপডেট করা হয়েছে!", icon="✅")
                    time.sleep(1.2)
                    st.session_state.active_emp_id = None
                    st.session_state.dialog_edit_mode = False
                    st.rerun()

# ==============================================================================
# ৭. সাইডবার ন্যাভিগেশন মেনু (রোল অনুযায়ী ফিল্টারিং)
# ==============================================================================
st.sidebar.markdown("## Main Menu")
user_role = st.session_state.get('user_role', None)

st.sidebar.markdown(f"### স্বাগতম, <span style='color:#10b981;'>{user_role}</span> 👋", unsafe_allow_html=True)

if st.sidebar.button("🔒 লগআউট (Logout)", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.current_company = None
    st.session_state.current_action = None
    st.rerun()

st.sidebar.markdown("<hr style='margin: 10px 0px; border-color: #444;'>", unsafe_allow_html=True)
menu_options_emp = ["Add New Employee", "Add Employee By Upload", "View All Employee"]

# ------------------------------------------------------------------------------
# ১. 📁 bKash মেইন ফোল্ডার
# ------------------------------------------------------------------------------
if user_role in ["admin", "bKash_User"]:
    with st.sidebar.expander("📁 bKash", expanded=(st.session_state.get('current_company') == "bKash")):
        
        with st.expander("📁 Employee Management", expanded=False):
            bk_default = menu_options_emp.index(st.session_state.current_action) if (st.session_state.get('current_company') == "bKash" and st.session_state.get('current_action') in menu_options_emp) else None
            def bk_emp_cb():
                st.session_state.current_company = "bKash"
                st.session_state.current_action = st.session_state.bk_emp_radio
            st.radio("bKash Emp Options", options=menu_options_emp, index=bk_default, key="bk_emp_radio", on_change=bk_emp_cb, label_visibility="collapsed")
            
        with st.expander("💰 Sales Management", expanded=False):
            st.caption("Sales features coming soon...")
            
        with st.expander("📊 Account Management", expanded=False):
            if st.button("💵 Cash Management", key="bk_cash_btn", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "Cash Management"
                st.rerun()
            if st.button("📉 Expense Management", key="bk_exp_btn", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "Expense Management"
                st.rerun()
                
            with st.expander("👥 Second Party Management", expanded=False):
                if st.button("➕ Add New Second Party", key="bk_add_sp_btn", use_container_width=True):
                    st.session_state.current_company = "bKash"
                    st.session_state.current_action = "Add New Second Party"
                    st.rerun()
                if st.button("📋 View All Second Parties", key="bk_view_sp_btn", use_container_width=True):
                    st.session_state.current_company = "bKash"
                    st.session_state.current_action = "View All Second Parties"
                    st.rerun()
                
        with st.expander("📁 Others", expanded=False):
            if st.button("📁 Others Account", key="bk_oth_btn", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "Others"
                st.rerun()

# ------------------------------------------------------------------------------
# ২. 📁 GP মেইন ফোল্ডার
# ------------------------------------------------------------------------------
if user_role in ["admin", "GP_User"]:
    with st.sidebar.expander("📁 GP", expanded=(st.session_state.get('current_company') == "GP")):
        
        with st.expander("📁 Employee Management", expanded=False):
            gp_default = menu_options_emp.index(st.session_state.current_action) if (st.session_state.get('current_company') == "GP" and st.session_state.get('current_action') in menu_options_emp) else None
            def gp_emp_cb():
                st.session_state.current_company = "GP"
                st.session_state.current_action = st.session_state.gp_emp_radio
            st.radio("GP Emp Options", options=menu_options_emp, index=gp_default, key="gp_emp_radio", on_change=gp_emp_cb, label_visibility="collapsed")
            
        with st.expander("💰 Sales Management", expanded=False):
            st.caption("Sales features coming soon...")
            
        with st.expander("📊 Account Management", expanded=False):
            if st.button("💵 Cash Management", key="gp_cash_btn", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "Cash Management"
                st.rerun()
            if st.button("📉 Expense Management", key="gp_exp_btn", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "Expense Management"
                st.rerun()
                
            with st.expander("👥 Second Party Management", expanded=False):
                if st.button("➕ Add New Second Party", key="gp_add_sp_btn", use_container_width=True):
                    st.session_state.current_company = "GP"
                    st.session_state.current_action = "Add New Second Party"
                    st.rerun()
                if st.button("📋 View All Second Parties", key="gp_view_sp_btn", use_container_width=True):
                    st.session_state.current_company = "GP"
                    st.session_state.current_action = "View All Second Parties"
                    st.rerun()
                
        with st.expander("📁 Others", expanded=False):
            if st.button("📁 Others Account", key="gp_oth_btn", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "Others"
                st.rerun()

if user_role == "admin":
    with st.sidebar.expander("📁 Others", expanded=False):
        if st.button("📁 Others Account", key="main_oth_btn", use_container_width=True):
            st.session_state.current_company = "Others"
            st.session_state.current_action = "Others"
            st.rerun()

st.sidebar.markdown("---")
current_action = st.session_state.get('current_action', None)
current_company = st.session_state.get('current_company', None)

# ==============================================================================
# ৮. অ্যাকশন এক্সিকিউশন লজিক (Main Body Router)
# ==============================================================================
if current_action is None:
    st.markdown("<h2 style='text-align: center; font-family: \"Times New Roman\", serif; font-weight: bold;'>M/S JABED ENTERPRISE</h2>", unsafe_allow_html=True)
    st.markdown("<h4 style='text-align: center; color: #a0a0a0;'>ড্যাশবোর্ড সিস্টেমে আপনাকে স্বাগতম!</h4>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 কাজ শুরু করতে বাম পাশের সাইডবার মেনু থেকে কোম্পানির নির্দিষ্ট ফোল্ডার এক্সপ্যান্ড করে কাঙ্ক্ষিত অপশনটি সিলেক্ট করুন।")

# --- Employee Management Actions ---
elif current_action == "Add New Employee":
    st.markdown(f"### 👥 Add New Employee ({current_company})")
    if current_company == "GP":
        design_options = ["DM", "Supervisor", "SE", "ITBS", "Accountant", "Peon", "Other"]
        select_key = "gp_designation_select"
    else:
        design_options = ["GM", "D&M", "F&A", "DCO", "DSS", "DSO", "Security Gurd", "Peon", "Cleaner", "Other"]
        select_key = "bkash_designation_select"
    
    with st.form(f"employee_form_{current_company.lower()}_v10", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 🔑 Basic & Contact Info")
            emp_id = st.text_input("Employee ID *", key=f"emp_id_{current_company}")
            name = st.text_input("Name *", key=f"name_{current_company}")
            designation = st.selectbox("Designation", options=design_options, key=select_key)
            mobile = st.text_input("Mobile")
            alt_contact = st.text_input("Alternative Contact")
            emp_nid = st.text_input("Employee NID Number")
            
            st.markdown("##### 📸 Employee Photo & NID Attachment")
            emp_img = st.file_uploader("Upload Employee Photo", type=["png", "jpg", "jpeg"])
            emp_nid_img = st.file_uploader("Upload Employee NID Card Image", type=["png", "jpg", "jpeg"])
            
            st.markdown("##### 🛡️ Guarantor Information")
            g_name = st.text_input("Guarantor Name")
            g_nid = st.text_input("Guarantor NID Number")
            g_mob = st.text_input("Guarantor Mobile")
            
        with col2:
            st.markdown("##### 📂 Family & Salary Details")
            join_date = st.date_input("Join Date", datetime.now())
            father_name = st.text_input("Father's Name")
            father_nid = st.text_input("Father's NID")
            mother_name = st.text_input("Mother's Name")
            
            basic_salary = st.number_input("Basic Salary", min_value=0.0, step=500.0, value=0.0)
            variable_salary = st.number_input("Variable Salary", min_value=0.0, step=500.0, value=0.0)
            
            st.markdown("##### 📸 Guarantor Photo & NID Attachment")
            guar_img = st.file_uploader("Upload Guarantor Photo", type=["png", "jpg", "jpeg"])
            guar_nid_img = st.file_uploader("Upload Guarantor NID Card Image", type=["png", "jpg", "jpeg"])
            
        submit_btn = st.form_submit_button(f"Save {current_company} Employee Profile")
        if submit_btn:
            if not emp_id or not name:
                st.error("Employee ID এবং Name অবশ্যই দিতে হবে!")
            else:
                try:
                    total_salary = basic_salary + variable_salary
                    if emp_img:
                        Image.open(emp_img).save(os.path.join(PHOTO_DIR, f"{emp_id.strip()}_emp.png"))
                    if emp_nid_img:
                        Image.open(emp_nid_img).save(os.path.join(EMP_NID_DIR, f"{emp_id.strip()}_nid.png"))
                    if guar_img:
                        Image.open(guar_img).save(os.path.join(GUAR_PHOTO_DIR, f"{emp_id.strip()}_guar.png"))
                    if guar_nid_img:
                        Image.open(guar_nid_img).save(os.path.join(GUAR_NID_DIR, f"{emp_id.strip()}_guar_nid.png"))
                        
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO employees (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary, company, father_name, father_nid, mother_name, emp_nid, guarantor_name, guarantor_nid, guarantor_mobile)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (emp_id.strip(), name.strip(), designation, mobile.strip(), alt_contact.strip(), str(join_date), basic_salary, variable_salary, total_salary, current_company, father_name.strip(), father_nid.strip(), mother_name.strip(), emp_nid.strip(), g_name.strip(), g_nid.strip(), g_mob.strip()))
                    conn.commit()
                    conn.close()
                    st.success(f"সফলভাবে {current_company}-তে কর্মী {name} এর প্রোফাইল ও ডকুমেন্টস ডাটাবেজে যুক্ত হয়েছে!")
                except sqlite3.IntegrityError:
                    st.error(f"Error: এই Employee ID ({emp_id}) ইতিমধ্যে ডাটাবেজে রয়েছে!")

elif current_action == "Add Employee By Upload":
    st.markdown(f"### 📊 Excel Bulk Upload ({current_company})")
    buffer = io.BytesIO()
    demo_df = pd.DataFrame(columns=["emp_id", "name", "designation", "mobile", "alt_contact", "join_date", "basic_salary", "variable_salary", "father_name", "father_nid", "mother_name", "emp_nid", "guarantor_name", "guarantor_nid", "guarantor_mobile"])
    demo_df.loc[0] = ["EMP-001", "Sample Name", "SR", "017XXXXXXXX", "019XXXXXXXX", "2026-01-01", 15000, 2000, "Father Name", "123456789", "Mother Name", "987654321", "G Name", "456123", "018XXXX"]
    
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        demo_df.to_excel(writer, index=False, sheet_name='Template')
    
    st.download_button("📥 Download Full Excel Template", data=buffer.getvalue(), file_name=f"{current_company}_comprehensive_template.xlsx")
    st.markdown("---")
    
    uploaded_file = st.file_uploader("XLSX বা XLS ফাইল আপলোড করুন", type=["xlsx", "xls"])
    if uploaded_file is not None:
        try:
            df = pd.read_excel(uploaded_file)
            required_cols = ["emp_id", "name", "designation", "basic_salary", "variable_salary"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                st.error(f"এক্সেলে প্রয়োজনীয় প্রধান কলাম অনুপস্থিত: {', '.join(missing_cols)}")
            else:
                st.markdown("#### 🔍 Uploaded File Preview (প্রথম ৫টি সারি):")
                st.dataframe(df.head(5), use_container_width=True, hide_index=True)
                
                st.warning("⚠️ ফাইলটি চূড়ান্তভাবে সেভ করার জন্য নিচের বাটনে ক্লিক করুন।")
                confirm_upload = st.button(f"💾 Confirm & Save to {current_company} Database", type="primary")
                
                if confirm_upload:
                    conn = sqlite3.connect(DB_NAME)
                    success_count, error_count = 0, 0
                    for _, row in df.iterrows():
                        try:
                            cursor = conn.cursor()
                            b_sal = float(row.get('basic_salary', 0)) if pd.notnull(row.get('basic_salary')) else 0.0
                            v_sal = float(row.get('variable_salary', 0)) if pd.notnull(row.get('variable_salary')) else 0.0
                            t_sal = b_sal + v_sal
                            
                            cursor.execute("""
                                INSERT INTO employees (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary, company, father_name, father_nid, mother_name, emp_nid, guarantor_name, guarantor_nid, guarantor_mobile)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                str(row['emp_id']), str(row['name']), str(row.get('designation', 'Other')),
                                str(row.get('mobile', '')), str(row.get('alt_contact', '')),
                                str(row.get('join_date', datetime.now().date())), b_sal, v_sal, t_sal, current_company,
                                str(row.get('father_name', '')), str(row.get('father_nid', '')),
                                str(row.get('mother_name', '')), str(row.get('emp_nid', '')),
                                str(row.get('guarantor_name', '')), str(row.get('guarantor_nid', '')), str(row.get('guarantor_mobile', ''))
                            ))
                            success_count += 1
                        except sqlite3.IntegrityError:
                            error_count += 1
                    
                    conn.commit()
                    conn.close()
                    st.success(f"সফলভাবে {success_count} জন কর্মীর ডাটা {current_company}-তে ইমপোর্ট হয়েছে!")
                    if error_count > 0:
                        st.warning(f"{error_count} টি আইডি ডাটাবেজে আগে থেকেই থাকায় স্কিপ করা হয়েছে।")
        except Exception as e:
            st.error(f"ফাইল প্রসেস করতে সমস্যা হয়েছে: {e}")

elif current_action == "View All Employee":
    st.markdown(f"### 📋 All Employees Database ({current_company})")
    search_query = st.text_input("🔍 Search Employee by Name / ID / Mobile:")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        query = "SELECT emp_id, name, designation, mobile, total_salary, emp_nid FROM employees WHERE company = ?"
        df = pd.read_sql_query(query, conn, params=(current_company,))
        conn.close()
        
        if not df.empty:
            if search_query:
                q = search_query.lower()
                df = df[df['name'].str.lower().str.contains(q) | df['emp_id'].str.lower().str.contains(q) | df['mobile'].str.contains(q)]
            
            st.markdown("<style>.grid-header { font-weight: bold; padding: 6px; background-color: #262730; border-radius: 4px; }</style>", unsafe_allow_html=True)
            
            h_col0, h_col1, h_col2, h_col3, h_col4, h_col5 = st.columns([0.6, 1.3, 2.2, 1.2, 1.6, 1.6])
            h_col0.markdown("<div class='grid-header'>View</div>", unsafe_allow_html=True)
            h_col1.markdown("<div class='grid-header'>Employee ID</div>", unsafe_allow_html=True)
            h_col2.markdown("<div class='grid-header'>Name</div>", unsafe_allow_html=True)
            h_col3.markdown("<div class='grid-header'>Designation</div>", unsafe_allow_html=True)
            h_col4.markdown("<div class='grid-header'>Mobile</div>", unsafe_allow_html=True)
            h_col5.markdown("<div class='grid-header'>Total Salary</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin: 4px 0px 10px 0px; border-color: #444;'>", unsafe_allow_html=True)
            
            for idx, row in df.iterrows():
                r_col0, r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns([0.6, 1.3, 2.2, 1.2, 1.6, 1.6])
                if r_col0.button("👁️", key=f"btn_{row['emp_id']}_{idx}"):
                    st.session_state.active_emp_id = row['emp_id']
                    st.session_state.dialog_edit_mode = False
                    st.rerun()
                
                r_col1.write(f"`{row['emp_id']}`")
                r_col2.write(row['name'])
                r_col3.write(row['designation'] if row['designation'] else "-")
                r_col4.write(row['mobile'] if row['mobile'] else "-")
                r_col5.write(f"**{row['total_salary']:,.1f} ৳**")
                st.markdown("<hr style='margin: 2px 0px; border-color: #222;'>", unsafe_allow_html=True)
        else:
            st.info(f"বর্তমানে {current_company} ডেটাবেজে কোনো কর্মীর তথ্য সংরক্ষিত নেই।")
    except Exception as e:
        st.error(f"ডাটা লোড করার সময় সমস্যা হয়েছে: {e}")

# --- 👥 Second Party Management (কোম্পানি ভিত্তিক স্বতন্ত্র লজিক) ---
elif current_action == "Add New Second Party":
    st.markdown(f"### 👥 Add New Second Party ({current_company})")
    st.markdown(f"বর্তমানে আপনি **{current_company}**-এর অধীনে নতুন একজন সেকেন্ড পার্টি যুক্ত করছেন।")
    
    with st.form("add_second_party_form", clear_on_submit=True):
        p_name = st.text_input("সেকেন্ড পার্টির নাম (Second Party Name) *")
        p_contact = st.text_input("যোগাযোগের নম্বর (Contact Number / Mobile)")
        p_comment1 = st.text_input("মন্তব্য ০১ (Comments 01)")
        p_comment2 = st.text_input("মন্তব্য ০২ (Comments 02)")
        
        submit_sp = st.form_submit_button("💾 সেকেন্ড পার্টি সংরক্ষণ করুন", use_container_width=True)
        if submit_sp:
            if not p_name.strip():
                st.error("সেকেন্ড পার্টির নাম অবশ্যই দিতে হবে!")
            else:
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    # 🎯 কারেন্ট সিলেক্টেড কোম্পানির প্যারামিটার পাস হচ্ছে
                    cursor.execute("""
                        INSERT INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status)
                        VALUES (?, ?, ?, ?, ?, 'Active')
                    """, (current_company, p_name.strip(), p_contact.strip(), p_comment1.strip(), p_comment2.strip()))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 সফলভাবে '{p_name.strip()}' সেকেন্ড পার্টিটি {current_company} তালিকায় সংরক্ষিত হয়েছে!")
                except sqlite3.IntegrityError:
                    st.error(f"⚠️ দুঃখিত! {current_company}-তে '{p_name.strip()}' নামে ইতিমধ্যে একটি সেকেন্ড পার্টি তৈরি করা আছে।")

elif current_action == "View All Second Parties":
    st.markdown(f"### 📋 All Second Parties List ({current_company})")
    search_sp = st.text_input(f"🔍 {current_company} সেকেন্ড পার্টি খুঁজুন (Search by Name or Contact):")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        # 🎯 শুধুমাত্র নির্দিষ্ট কোম্পানির ডেটা ফিল্টার এবং সর্টিং (Active সর্বদা উপরে)
        query = """
            SELECT id, party_name, contact_number, comments_01, comments_02, status 
            FROM second_parties 
            WHERE company = ?
            ORDER BY CASE WHEN status = 'Active' THEN 0 ELSE 1 END, party_name ASC
        """
        sp_df = pd.read_sql_query(query, conn, params=(current_company,))
        conn.close()
        
        if not sp_df.empty:
            if search_sp:
                q = search_sp.lower()
                sp_df = sp_df[sp_df['party_name'].str.lower().str.contains(q) | sp_df['contact_number'].str.contains(q)]
                
            st.markdown("<style>.sp-grid-header { font-weight: bold; padding: 6px; background-color: #262730; border-radius: 4px; }</style>", unsafe_allow_html=True)
            
            h_col0, h_col1, h_col2, h_col3 = st.columns([0.8, 2.8, 2.4, 1.2])
            h_col0.markdown("<div class='sp-grid-header'>Action</div>", unsafe_allow_html=True)
            h_col1.markdown("<div class='sp-grid-header'>Second Party Name</div>", unsafe_allow_html=True)
            h_col2.markdown("<div class='sp-grid-header'>Contact Number</div>", unsafe_allow_html=True)
            h_col3.markdown("<div class='sp-grid-header'>Status</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin: 4px 0px 10px 0px; border-color: #444;'>", unsafe_allow_html=True)
            
            for idx, row in sp_df.iterrows():
                r_col0, r_col1, r_col2, r_col3 = st.columns([0.8, 2.8, 2.4, 1.2])
                
                if r_col0.button("👁️ View", key=f"sp_view_btn_{row['id']}_{idx}", use_container_width=True):
                    st.session_state.active_party_id = row['id']
                    st.session_state.party_edit_mode = False
                    st.rerun()
                    
                r_col1.write(row['party_name'])
                r_col2.write(row['contact_number'] if row['contact_number'] else "-")
                
                status_str = row['status'] if row['status'] else "Active"
                if status_str == "Active":
                    r_col3.markdown("<span style='color:#10b981; font-weight:bold;'>Active</span>", unsafe_allow_html=True)
                else:
                    r_col3.markdown("<span style='color:#ef4444; font-weight:bold;'>Inactive</span>", unsafe_allow_html=True)
                    
                st.markdown("<hr style='margin: 2px 0px; border-color: #222;'>", unsafe_allow_html=True)
                
            st.markdown(f"<br>**{current_company} এর মোট রেজিস্টার্ড সেকেন্ড পার্টি সংখ্যা:** `{len(sp_df)} টি`")
        else:
            st.info(f"বর্তমানে {current_company} তালিকায় কোনো সেকেন্ড পার্টির তথ্য নেই।")
    except Exception as e:
        st.error(f"ডাটা লোড করতে সমস্যা হয়েছে: {e}")

# --- Accounts Management Actions ---
elif current_action == "Cash Management":
    st.markdown(f"### 📊 Unified Daily Master Report & Cash Khata ({current_company})")
    
    # ১. ডাটাবেজ টেবিল স্ট্রাকচার তৈরি (মাস্টার রিপোর্টের জন্য)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_master_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            company TEXT NOT NULL,
            total_investment REAL,
            master_sim REAL,
            bank_cash REAL,
            accounts_receivable REAL,
            accounts_payable REAL,
            opening_vault REAL,
            opening_bank REAL,
            opening_advance REAL,
            opening_due REAL,
            dso_return REAL,
            bank_receive REAL,
            bgp_receive REAL,
            others_receive REAL,
            closing_vault REAL,
            closing_bank REAL,
            closing_advance REAL,
            closing_due REAL,
            dso_payment REAL,
            bank_deposit REAL,
            bgp_payment REAL,
            expenses REAL,
            others_payment REAL,
            grand_total_asset REAL,
            total_cash_in REAL,
            total_cash_out REAL,
            UNIQUE(date, company)
        )
    ''')
    conn.commit()
    conn.close()

    # ২. সেশন স্টেট ইনিশিয়ালাইজেশন (ডাটা হোল্ড এবং অন-স্পট কারেকশনের জন্য)
    master_fields = [
        "total_investment", "master_sim", "bank_cash", "accounts_receivable", "accounts_payable",
        "opening_vault", "opening_bank", "opening_advance", "opening_due",
        "dso_return", "bank_receive", "bgp_receive", "others_receive",
        "closing_vault", "closing_bank", "closing_advance", "closing_due",
        "dso_payment", "bank_deposit", "bgp_payment", "expenses", "others_payment"
    ]
    for field in master_fields:
        if field not in st.session_state:
            st.session_state[field] = 0.0

    if "report_date" not in st.session_state:
        st.session_state["report_date"] = datetime.now().date()

    # দুটি কাজের জন্য ট্যাব ইন্টারফেস (১. মেইন ড্যাশবোর্ড, ২. হিস্টোরি/লেজার)
    tab_dashboard, tab_ledger = st.tabs(["📝 Unified Master Dashboard", "📖 View Saved Reports & Ledger"])

    with tab_dashboard:
        # --------------------------------------------------------------------------
        # পদ্ধতি ২: এক্সেল ফাইল আপলোড এবং ডাইনামিক ফিল্ড পপুলেশন লজিক
        # --------------------------------------------------------------------------
        st.markdown("#### 📤 পদ্ধতি ২: এক্সেল ফাইল থেকে ডাটা ইমপোর্ট করুন (ঐচ্ছিক)")
        uploaded_master_excel = st.file_uploader(
            "আপনার ডেইলি এক্সেল মাস্টার রিপোর্টটি (.xlsx) এখানে আপলোড করুন", 
            type=["xlsx"], 
            key="master_excel_file_uploader"
        )
        
        if uploaded_master_excel is not None:
            file_identifier = f"{uploaded_master_excel.name}_{uploaded_master_excel.size}"
            # ডাবল প্রসেসিং ও লুপ আটকানোর জন্য ট্র্যাকিং মেকানিজম
            if st.session_state.get("last_processed_excel_report") != file_identifier:
                try:
                    excel_df = pd.read_excel(uploaded_master_excel, header=None)
                    excel_df = excel_df.astype(str)
                    
                    # এক্সেল থেকে কি-ওয়ার্ড সার্চ করে স্বয়ংক্রিয় সংখ্যা বের করার সাব-ফাংশন
                    def extract_value_by_keyword(df, keyword_list):
                        for r in range(df.shape[0]):
                            for c in range(df.shape[1]):
                                cell_txt = df.iloc[r, c].strip().lower()
                                if any(kw in cell_txt for kw in keyword_list):
                                    for offset in [1, 2]: # পাশের অথবা নিচের ঘর চেক করা
                                        if c + offset < df.shape[1]:
                                            val = df.iloc[r, c + offset].replace(',', '').strip()
                                            try: return float(val) if val else 0.0
                                            except ValueError: pass
                                        if r + offset < df.shape[0]:
                                            val = df.iloc[r + offset, c].replace(',', '').strip()
                                            try: return float(val) if val else 0.0
                                            except ValueError: pass
                        return 0.0

                    # আপনার এক্সেল ফাইলের লেখার সাথে মিলিয়ে কি-ওয়ার্ড ম্যাপিং রুলস
                    mapping_rules = {
                        "total_investment": ["total investment", "ইনভেস্টমেন্ট", "বিনিয়োগ"],
                        "master_sim": ["master sim", "মাস্টার সিম"],
                        "bank_cash": ["bank cash", "ব্যাংক ক্যাশ", "ব্যাংক ব্যালেন্স"],
                        "accounts_receivable": ["accounts receivable", "মার্কেট পাওনা", "receivable"],
                        "accounts_payable": ["accounts payable", "মার্কেট দেনা", "payable"],
                        "opening_vault": ["opening vault", "ওপেনিং ভল্ট"],
                        "opening_bank": ["opening bank", "ওপেনিং ব্যাংক"],
                        "opening_advance": ["opening market advance", "ওপেনিং অ্যাডভান্স"],
                        "opening_due": ["opening others due", "ওপেনিং বিবিধ পাওনা"],
                        "dso_return": ["dso return", "ডিএসও রিটার্ন"],
                        "bank_receive": ["bank receive", "ব্যাংক রিসিভ"],
                        "bgp_receive": ["bgp receive", "বিজিপি রিসিভ"],
                        "others_receive": ["others receive", "অন্যান্য প্রাপ্তি"],
                        "closing_vault": ["closing vault", "ক্লোজিং ভল্ট"],
                        "closing_bank": ["closing bank", "ক্লোজিং ব্যাংক"],
                        "closing_advance": ["closing market advance", "ক্লোজিং অ্যাডভান্স"],
                        "closing_due": ["closing others due", "ক্লোজিং বিবিধ"],
                        "dso_payment": ["dso payment", "ডিএসও পেমেন্ট"],
                        "bank_deposit": ["bank deposit", "ব্যাংক ডিপোজিট"],
                        "bgp_payment": ["bgp payment", "বিজিপি পেমেন্ট"],
                        "expenses": ["expenses", "দৈনন্দিন খরচ", "খরচ"],
                        "others_payment": ["others payment", "অন্যান্য পেমেন্ট"]
                    }

                    # ডাটা এক্সট্রাক্ট করে সেশন স্টেটে রাইট করা
                    for field_key, keywords in mapping_rules.items():
                        st.session_state[field_key] = extract_value_by_keyword(excel_df, keywords)
                        
                    st.session_state["last_processed_excel_report"] = file_identifier
                    st.success("✅ এক্সেল থেকে ডাটা সফলভাবে রিড করা হয়েছে! নিচের ড্যাশবোর্ডে ভ্যালুগুলো সাজানো হয়েছে।")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ এক্সেল ফাইল রিড করতে সমস্যা হয়েছে: {e}")

        st.markdown("---")
        st.markdown("#### 📝 পদ্ধতি ১: ম্যানুয়াল এন্ট্রি ও কারেকশন ড্যাশবোর্ড")
        
        # তারিখ সিলেক্টর
        st.session_state["report_date"] = st.date_input("রিপোর্টের তারিখ (Date)", st.session_state["report_date"])

        # --------------------------------------------------------------------------
        # ড্যাশবোর্ড লেআউট: ৩টি গ্রাফিক্যাল কলামে বিভক্ত
        # --------------------------------------------------------------------------
        col_asset, col_cash_in, col_cash_out = st.columns(3)

        # কলাম ১: ইনভেস্টমেন্ট এবং অ্যাসেট বিবরণী
        with col_asset:
            st.markdown("<h4 style='color: #3b82f6;'>🏛️ Investment & Asset Detail</h4>", unsafe_allow_html=True)
            st.session_state["total_investment"] = st.number_input("Total Investment (৳)", min_value=0.0, key="total_investment_input", value=st.session_state["total_investment"], step=1000.0)
            st.markdown("---")
            st.session_state["master_sim"] = st.number_input("Master SIM Bal (৳)", min_value=0.0, key="master_sim_input", value=st.session_state["master_sim"], step=500.0)
            st.session_state["bank_cash"] = st.number_input("Asset Bank Cash (৳)", min_value=0.0, key="bank_cash_input", value=st.session_state["bank_cash"], step=500.0)
            st.session_state["accounts_receivable"] = st.number_input("Accounts Receivable (A/R) (৳)", min_value=0.0, key="ar_input", value=st.session_state["accounts_receivable"], step=500.0)
            st.session_state["accounts_payable"] = st.number_input("Accounts Payable (A/P) (৳)", min_value=0.0, key="ap_input", value=st.session_state["accounts_payable"], step=500.0)

        # কলাম ২: ক্যাশ খাতা - ওপেনিং এবং প্রাপ্তি (Cash In)
        with col_cash_in:
            st.markdown("<h4 style='color: #10b981;'>💰 Cash Khata: Opening & IN</h4>", unsafe_allow_html=True)
            st.caption("🟢 Opening Balance Components")
            st.session_state["opening_vault"] = st.number_input("Opening Vault Cash (৳)", min_value=0.0, key="op_vault_input", value=st.session_state["opening_vault"], step=500.0)
            st.session_state["opening_bank"] = st.number_input("Opening DM/DSS Bank (৳)", min_value=0.0, key="op_bank_input", value=st.session_state["opening_bank"], step=500.0)
            st.session_state["opening_advance"] = st.number_input("Opening Market Advance (৳)", min_value=0.0, key="op_adv_input", value=st.session_state["opening_advance"], step=500.0)
            st.session_state["opening_due"] = st.number_input("Opening Others Due (৳)", min_value=0.0, key="op_due_input", value=st.session_state["opening_due"], step=500.0)
            
            st.caption("📥 Today's Receives (Cash In)")
            st.session_state["dso_return"] = st.number_input("DSO Return (৳)", min_value=0.0, key="dso_ret_input", value=st.session_state["dso_return"], step=500.0)
            st.session_state["bank_receive"] = st.number_input("Bank Receive (৳)", min_value=0.0, key="bank_rec_input", value=st.session_state["bank_receive"], step=500.0)
            st.session_state["bgp_receive"] = st.number_input("BGP Receive (৳)", min_value=0.0, key="bgp_rec_input", value=st.session_state["bgp_receive"], step=500.0)
            st.session_state["others_receive"] = st.number_input("Others Receive (৳)", min_value=0.0, key="oth_rec_input", value=st.session_state["others_receive"], step=500.0)

        # কলাম ৩: ক্যাশ খাতা - ক্লোজিং এবং পেমেন্ট (Cash Out)
        with col_cash_out:
            st.markdown("<h4 style='color: #ef4444;'>💸 Cash Khata: Closing & OUT</h4>", unsafe_allow_html=True)
            st.caption("🔴 Closing Balance Components")
            st.session_state["closing_vault"] = st.number_input("Closing Vault Cash (৳)", min_value=0.0, key="cl_vault_input", value=st.session_state["closing_vault"], step=500.0)
            st.session_state["closing_bank"] = st.number_input("Closing DM/DSS Bank (৳)", min_value=0.0, key="cl_bank_input", value=st.session_state["closing_bank"], step=500.0)
            st.session_state["closing_advance"] = st.number_input("Closing Market Advance (৳)", min_value=0.0, key="cl_adv_input", value=st.session_state["closing_advance"], step=500.0)
            st.session_state["closing_due"] = st.number_input("Closing Others Due (৳)", min_value=0.0, key="cl_due_input", value=st.session_state["closing_due"], step=500.0)
            
            st.caption("📤 Today's Payments (Cash Out)")
            st.session_state["dso_payment"] = st.number_input("DSO Payment (৳)", min_value=0.0, key="dso_pay_input", value=st.session_state["dso_payment"], step=500.0)
            st.session_state["bank_deposit"] = st.number_input("Bank Deposit (৳)", min_value=0.0, key="bank_dep_input", value=st.session_state["bank_deposit"], step=500.0)
            st.session_state["bgp_payment"] = st.number_input("BGP Payment (৳)", min_value=0.0, key="bgp_pay_input", value=st.session_state["bgp_payment"], step=500.0)
            st.session_state["expenses"] = st.number_input("Daily Expenses (৳)", min_value=0.0, key="expenses_input", value=st.session_state["expenses"], step=100.0)
            st.session_state["others_payment"] = st.number_input("Others Payment (৳)", min_value=0.0, key="oth_pay_input", value=st.session_state["others_payment"], step=500.0)

        # --------------------------------------------------------------------------
        # রিয়েল-টাইম লাইভ ভ্যালিডেশন এবং গাণিতিক হিসাব ইঞ্জিন
        # --------------------------------------------------------------------------
        opening_hand_cash = (st.session_state["opening_vault"] + st.session_state["opening_bank"] + 
                             st.session_state["opening_advance"] + st.session_state["opening_due"])
        
        closing_hand_cash = (st.session_state["closing_vault"] + st.session_state["closing_bank"] + 
                             st.session_state["closing_advance"] + st.session_state["closing_due"])

        total_cash_in = (opening_hand_cash + st.session_state["dso_return"] + st.session_state["bank_receive"] + 
                         st.session_state["bgp_receive"] + st.session_state["others_receive"])
        
        total_cash_out = (closing_hand_cash + st.session_state["dso_payment"] + st.session_state["bank_deposit"] + 
                          st.session_state["bgp_payment"] + st.session_state["expenses"] + st.session_state["others_payment"])

        grand_total_asset = (st.session_state["master_sim"] + closing_hand_cash + st.session_state["bank_cash"] + 
                             st.session_state["accounts_receivable"] - st.session_state["accounts_payable"])

        cash_diff = round(total_cash_in - total_cash_out, 2)
        asset_diff = round(st.session_state["total_investment"] - grand_total_asset, 2)

        st.markdown("<br><hr>", unsafe_allow_html=True)
        st.markdown("#### 🔍 লাইভ হিসাব রেকনসিলিয়েশন স্ট্যাটাস")

        # গুরুত্বপূর্ণ মেট্রিক স্কোরকার্ডসমূহ
        m_col1, m_col2, m_col3 = st.columns(3)
        m_col1.metric("আজকের ওপেনিং ক্যাশ (Opening)", f"{opening_hand_cash:,.1f} ৳")
        m_col2.metric("আজকের ক্লোজিং ক্যাশ (Closing)", f"{closing_hand_cash:,.1f} ৳")
        m_col3.metric("মোট অ্যাসেট ভ্যালু (Total Asset)", f"{grand_total_asset:,.1f} ৳")

        # হিসাব ম্যাচিং কন্ডিশনস
        is_cash_matched = (abs(cash_diff) < 0.1)
        is_asset_matched = (abs(asset_diff) < 0.1)
        status_ok = True
        
        if is_cash_matched:
            st.success(f"✅ ক্যাশ খাতা মিলেছে! (Total Cash In: {total_cash_in:,.1f} ৳ == Total Cash Out: {total_cash_out:,.1f} ৳)")
        else:
            status_ok = False
            st.error(f"❌ ক্যাশ খাতা মিলেনি! অমিল: {cash_diff:,.1f} ৳ (In: {total_cash_in:,.1f} | Out: {total_cash_out:,.1f})")

        if is_asset_matched:
            st.success(f"✅ ইনভেস্টমেন্ট ও অ্যাসেট মিলেছে! (Total Investment: {st.session_state['total_investment']:,.1f} ৳ == Asset Value: {grand_total_asset:,.1f} ৳)")
        else:
            status_ok = False
            st.error(f"❌ ইনভেস্টমেন্ট ও অ্যাসেট মিলেনি! অমিল: {asset_diff:,.1f} ৳ (Investment: {st.session_state['total_investment']:,.1f} | Asset: {grand_total_asset:,.1f})")

        # --------------------------------------------------------------------------
        # ডাইনামিক সেভ বাটন অ্যাক্টিভেশন কন্ট্রোলার
        # --------------------------------------------------------------------------
        st.markdown("<br>", unsafe_allow_html=True)
        if status_ok:
            st.balloons()
            save_master_report = st.button("💾 Save Daily Master Report", type="primary", use_container_width=True, key="active_save_report_btn")
            if save_master_report:
                try:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO daily_master_reports (
                            date, company, total_investment, master_sim, bank_cash, accounts_receivable, accounts_payable,
                            opening_vault, opening_bank, opening_advance, opening_due, dso_return, bank_receive, bgp_receive, others_receive,
                            closing_vault, closing_bank, closing_advance, closing_due, dso_payment, bank_deposit, bgp_payment, expenses, others_payment,
                            grand_total_asset, total_cash_in, total_cash_out
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(st.session_state["report_date"]), current_company, st.session_state["total_investment"],
                        st.session_state["master_sim"], st.session_state["bank_cash"], st.session_state["accounts_receivable"], st.session_state["accounts_payable"],
                        st.session_state["opening_vault"], st.session_state["opening_bank"], st.session_state["opening_advance"], st.session_state["opening_due"],
                        st.session_state["dso_return"], st.session_state["bank_receive"], st.session_state["bgp_receive"], st.session_state["others_receive"],
                        st.session_state["closing_vault"], st.session_state["closing_bank"], st.session_state["closing_advance"], st.session_state["closing_due"],
                        st.session_state["dso_payment"], st.session_state["bank_deposit"], st.session_state["bgp_payment"], st.session_state["expenses"], st.session_state["others_payment"],
                        grand_total_asset, total_cash_in, total_cash_out
                    ))
                    conn.commit()
                    conn.close()
                    st.toast("🎉 আজকের ডেইলি মাস্টার রিপোর্টটি সফলভাবে সংরক্ষিত হয়েছে!", icon="🚀")
                    
                    # সেভ করার পর ফর্ম ক্লিয়ার করা
                    for field in master_fields:
                        st.session_state[field] = 0.0
                    if "last_processed_excel_report" in st.session_state:
                        del st.session_state["last_processed_excel_report"]
                    import time
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"ডাটাবেজে রিপোর্ট সেভ করতে ত্রুটি হয়েছে: {e}")
        else:
            st.button("💾 Save Daily Master Report (হিসাব না মিললে বাটন লক থাকবে)", type="secondary", disabled=True, use_container_width=True, key="disabled_save_report_btn")

    with tab_ledger:
        st.markdown("#### 📖 সংরক্ষিত দৈনিক রিপোর্টসমূহের তালিকা ও লেজার ভিউ")
        try:
            conn = sqlite3.connect(DB_NAME)
            history_query = """
                SELECT date as 'তারিখ', total_investment as 'ইনভেস্টমেন্ট (৳)', grand_total_asset as 'মোট সম্পদ (৳)', 
                       total_cash_in as 'ক্যাশ ইন (৳)', total_cash_out as 'ক্যাশ আউট (৳)' 
                FROM daily_master_reports 
                WHERE company = ? 
                ORDER BY date DESC
            """
            history_df = pd.read_sql_query(history_query, conn, params=(current_company,))
            conn.close()
            
            if not history_df.empty:
                st.dataframe(history_df, use_container_width=True, hide_index=True)
            else:
                st.info(f"বর্তমানে {current_company}-এর আন্ডারে কোনো সংরক্ষিত মাস্টার রিপোর্টের রেকর্ড নেই।")
        except Exception as e:
            st.error(f"ইতিহাস লোড করতে ত্রুটি হয়েছে: {e}")

elif current_action == "Expense Management":
    st.markdown(f"### 📉 Expense Management ({current_company})")
    st.info("💡 দৈনন্দিন খরচের (Expense Management) মডিউলটি একইভাবে ক্যাশ খাতার লজিক অনুসরণ করে ডেভলপ করা যাবে।")

elif current_action == "Others":
    st.markdown(f"### 📁 Others Account ({current_company})")
    st.info("💡 অন্যান্য ফুটকর বা বিবিধ হিসাবসমূহের ডেটা এন্ট্রি এখানে থাকবে।")

# ==============================================================================
# ৯. গ্লোবাল একটিভ ডায়ালগ কন্ট্রোলার 
# ==============================================================================
if st.session_state.active_emp_id:
    show_employee_details(st.session_state.active_emp_id, st.session_state.current_company)

if st.session_state.active_party_id:
    show_second_party_details(st.session_state.active_party_id)
