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
                    st.session_state.current_action = None # 👈 নিরাপদে রিফ্রেশ করার জন্য এখানেও যোগ করা হলো
                    st.success("এডমিন হিসেবে লগইন সফল হয়েছে!")
                    import time
                    time.sleep(0.5)
                    st.rerun()
                
                # ২. বিকাশ ইউজার (শুধু বিকাশ ফোল্ডার দেখতে পাবেন)
                elif username == "bKash_User" and password == "bkash2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "bKash_User"
                    st.session_state.current_company = "bKash" 
                    st.session_state.current_action = None # 👈 🔴 এই নতুন লাইনটি যোগ করা হলো
                    st.success("বিকাশ ইউজার লগইন সফল!")
                    import time
                    time.sleep(0.5)
                    st.rerun()
                
                # ৩. জিপি ইউজার (শুধু জিপি ফোল্ডার দেখতে পাবেন)
                elif username == "GP_User" and password == "gp2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "GP_User"
                    st.session_state.current_company = "GP" 
                    st.session_state.current_action = None # 👈 🔴 এই নতুন লাইনটি যোগ করা হলো
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
# ৩. ডাটাবেজ এবং কলাম মাইগ্রেশন লজিক
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
    
    # সেকেন্ড পার্টি টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS second_parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            party_name TEXT UNIQUE NOT NULL, 
            contact_number TEXT, 
            comments_01 TEXT, 
            comments_02 TEXT
        )
    ''')
    
    # ডিফল্ট সেকেন্ড পার্টি ডেটা ইনসার্ট
    default_parties = ["Mother_Wallet", "Hand_Cash", "Petty_Cash", "Bank", "BGP", "Dulal", "Shafayat", "Madina", "Owner", "GAS", "Auto_Rice", "Others", "bKash", "Commission", "Al_Arafa", "Rekit", "DMCBL", "Kabita_Mami", "Ashim_Da", "Al_Amin"]
    for party in default_parties:
        cursor.execute("INSERT OR IGNORE INTO second_parties (party_name, contact_number, comments_01, comments_02) VALUES (?, '', '', '')", (party,))
    
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
# ৭. সাইডবার ন্যাভিগেশন মেনু (রোল অনুযায়ী কঠোর ফিল্টারিং)
# ==============================================================================
st.sidebar.markdown("## Main Menu")
user_role = st.session_state.get('user_role', None)

# লগইন করা ইউজারের নাম ডাইনামিক্যালি দেখাবে
st.sidebar.markdown(f"### স্বাগতম, <span style='color:#10b981;'>{user_role}</span> 👋", unsafe_allow_html=True)

# লগআউট বাটন (সব ইউজারই দেখতে পাবে)
if st.sidebar.button("🔒 লগআউট (Logout)", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.current_company = None
    st.session_state.current_action = None
    st.rerun()

st.sidebar.markdown("<hr style='margin: 10px 0px; border-color: #444;'>", unsafe_allow_html=True)
menu_options_emp = ["Add New Employee", "Add Employee By Upload", "View All Employee"]

# ------------------------------------------------------------------------------
# ১. 📁 bKash মেইন ফোল্ডার (শুধু admin এবং bKas_User দেখতে পাবে)
# ------------------------------------------------------------------------------
if user_role in ["admin", "bKas_User", "bKash_User"]:
    with st.sidebar.expander("📁 bKash", expanded=(st.session_state.get('current_company') == "bKash")):
        
        # সাব-ফোল্ডার: Employee Management
        with st.expander("📁 Employee Management", expanded=False):
            bk_default = menu_options_emp.index(st.session_state.current_action) if (st.session_state.get('current_company') == "bKash" and st.session_state.get('current_action') in menu_options_emp) else None
            def bk_emp_cb():
                st.session_state.current_company = "bKash"
                st.session_state.current_action = st.session_state.bk_emp_radio
            st.radio("bKash Emp Options", options=menu_options_emp, index=bk_default, key="bk_emp_radio", on_change=bk_emp_cb, label_visibility="collapsed")
            
        # সাব-ফোল্ডার: Sales Management
        with st.expander("💰 Sales Management", expanded=False):
            st.caption("Sales features coming soon...")
            
        # সাব-ফোল্ডার: Accounts Management
        with st.expander("📊 Account Management", expanded=False):
            if st.button("💵 Cash Management", key="bk_cash_btn", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "Cash Management"
                st.rerun()
            if st.button("📉 Expense Management", key="bk_exp_btn", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "Expense Management"
                st.rerun()
                
            # 👥 নেস্টেড সাব-ফোল্ডার: Second Party Management
            with st.expander("👥 Second Party Management", expanded=False):
                if st.button("➕ Add New Second Party", key="bk_add_sp_btn", use_container_width=True):
                    st.session_state.current_company = "bKash"
                    st.session_state.current_action = "Add New Second Party"
                    st.rerun()
                if st.button("📋 View All Second Parties", key="bk_view_sp_btn", use_container_width=True):
                    st.session_state.current_company = "bKash"
                    st.session_state.current_action = "View All Second Parties"
                    st.rerun()
                
        # সাব-ফোল্ডার: Others
        with st.expander("📁 Others", expanded=False):
            if st.button("📁 Others Account", key="bk_oth_btn", use_container_width=True):
                st.session_state.current_company = "bKash"
                st.session_state.current_action = "Others"
                st.rerun()

# ------------------------------------------------------------------------------
# ২. 📁 GP মেইন ফোল্ডার (শুধু admin এবং GP_User দেখতে পাবে)
# ------------------------------------------------------------------------------
if user_role in ["admin", "GP_User"]:
    with st.sidebar.expander("📁 GP", expanded=(st.session_state.get('current_company') == "GP")):
        
        # সাব-ফোল্ডার: Employee Management
        with st.expander("📁 Employee Management", expanded=False):
            gp_default = menu_options_emp.index(st.session_state.current_action) if (st.session_state.get('current_company') == "GP" and st.session_state.get('current_action') in menu_options_emp) else None
            def gp_emp_cb():
                st.session_state.current_company = "GP"
                st.session_state.current_action = st.session_state.gp_emp_radio
            st.radio("GP Emp Options", options=menu_options_emp, index=gp_default, key="gp_emp_radio", on_change=gp_emp_cb, label_visibility="collapsed")
            
        # সাব-ফোল্ডার: Sales Management
        with st.expander("💰 Sales Management", expanded=False):
            st.caption("Sales features coming soon...")
            
        # সাব-ফোল্ডার: Accounts Management
        with st.expander("📊 Account Management", expanded=False):
            if st.button("💵 Cash Management", key="gp_cash_btn", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "Cash Management"
                st.rerun()
            if st.button("📉 Expense Management", key="gp_exp_btn", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "Expense Management"
                st.rerun()
                
            # 👥 নেস্টেড সাব-ফোল্ডার: Second Party Management
            with st.expander("👥 Second Party Management", expanded=False):
                if st.button("➕ Add New Second Party", key="gp_add_sp_btn", use_container_width=True):
                    st.session_state.current_company = "GP"
                    st.session_state.current_action = "Add New Second Party"
                    st.rerun()
                if st.button("📋 View All Second Parties", key="gp_view_sp_btn", use_container_width=True):
                    st.session_state.current_company = "GP"
                    st.session_state.current_action = "View All Second Parties"
                    st.rerun()
                
        # সাব-ফোল্ডার: Others
        with st.expander("📁 Others", expanded=False):
            if st.button("📁 Others Account", key="gp_oth_btn", use_container_width=True):
                st.session_state.current_company = "GP"
                st.session_state.current_action = "Others"
                st.rerun()

# ------------------------------------------------------------------------------
# ৩. 📁 Others মেইন ফোল্ডার (🚨 শুধু admin দেখতে পাবে)
# ------------------------------------------------------------------------------
if user_role == "admin":
    with st.sidebar.expander("📁 Others", expanded=False):
        if st.button("📁 Others Account", key="main_oth_btn", use_container_width=True):
            st.session_state.current_company = "Others"
            st.session_state.current_action = "Others"
            st.rerun()

# ------------------------------------------------------------------------------
# ৪. ⚙️ পাসওয়ার্ড রিসেট প্যানেল (🚨 শুধু admin দেখতে পাবে)
# ------------------------------------------------------------------------------
if user_role == "admin":
    with st.sidebar.expander("⚙️ পাসওয়ার্ড রিসেট প্যানেল (Admin)", expanded=False):
        # 💡 আপনার পাসওয়ার্ড রিসেট প্যানেলের ভেতরের কোডটুকু এখানে থাকবে
        st.write("Password reset features here...")

st.sidebar.markdown("---")
current_action = st.session_state.get('current_action', None)
# ==============================================================================
# ৮. অ্যাকশন এক্সিকিউশন লজিক (Main Body Router)
# ==============================================================================
if current_action is None:
    user_role = st.session_state.get('user_role', None)
current_company = st.session_state.get('current_company', None)

# 🚨 রোল-বেসড নিরাপত্তা লক (Direct Session State Check - কোনো NameError আসবে না)
if st.session_state.get('current_company') == "bKash" and st.session_state.get('user_role') not in ["admin", "bKas_User", "bKash_User"]:
    st.error("❌ এই সেকশনটি দেখার অনুমতি আপনার নেই!")
    st.stop()

if st.session_state.get('current_company') == "GP" and st.session_state.get('user_role') not in ["admin", "GP_User"]:
    st.error("❌ এই সেকশনটি দেখার অনুমতি আপনার নেই!")
    st.stop()
# 👆 [পেস্ট করা শেষ]

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
    
    form_key = f"employee_form_{current_company.lower()}_v10"
    
    with st.form(form_key, clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 🔑 Basic & Contact Info")
            emp_id = st.text_input("Employee ID (e.g., EMP-101) *", key=f"emp_id_{current_company}")
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
    search_query = st.text_input("🔍 Search Employee by Name / ID / Mobile / NID:")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        query = "SELECT emp_id, name, designation, mobile, total_salary, emp_nid FROM employees WHERE company = ?"
        df = pd.read_sql_query(query, conn, params=(current_company,))
        conn.close()
        
        if not df.empty:
            if search_query:
                q = search_query.lower()
                df = df[df['name'].str.lower().str.contains(q) | df['emp_id'].str.lower().str.contains(q) | df['mobile'].str.contains(q) | df['emp_nid'].str.contains(q)]
            
            st.markdown("""
                <style>
                .grid-header { font-weight: bold; padding: 6px; background-color: #262730; border-radius: 4px; text-align: left; }
                </style>
            """, unsafe_allow_html=True)
            
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
                
            st.markdown(f"<br>**সর্বমোট স্টাফ সংখ্যা ({current_company}):** `{len(df)} জন`", unsafe_allow_html=True)
        else:
            st.info(f"বর্তমানে {current_company} ডেটাবেজে কোনো কর্মীর তথ্য সংরক্ষিত নেই।")
    except Exception as e:
        st.error(f"ডাটা লোড করার সময় সমস্যা হয়েছে: {e}")

# --- 👥 Second Party Management (New Features Execution Logic) ---
elif current_action == "Add New Second Party":
    st.markdown(f"### 👥 Add New Second Party ({current_company})")
    st.markdown("নতুন কোনো এজেন্ট, ডিলার বা অ্যাকাউন্টস লেজারের জন্য সেকেন্ড পার্টি নাম এখানে যুক্ত করুন।")
    
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
                    cursor.execute("""
                        INSERT INTO second_parties (party_name, contact_number, comments_01, comments_02)
                        VALUES (?, ?, ?, ?)
                    """, (p_name.strip(), p_contact.strip(), p_comment1.strip(), p_comment2.strip()))
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 সফলভাবে '{p_name.strip()}' সেকেন্ড পার্টি হিসেবে ডাটাবেজে সংরক্ষিত হয়েছে!")
                except sqlite3.IntegrityError:
                    st.error(f"⚠️ দুঃখিত! '{p_name.strip()}' নামে ইতিমধ্যে একটি সেকেন্ড পার্টি তৈরি করা আছে।")

elif current_action == "View All Second Parties":
    st.markdown(f"### 📋 All Second Parties List ({current_company})")
    search_sp = st.text_input("🔍 সেকেন্ড পার্টি খুঁজুন (Search by Name or Contact):")
    
    try:
        conn = sqlite3.connect(DB_NAME)
        sp_df = pd.read_sql_query("SELECT id as 'ID', party_name as 'সেকেন্ড পার্টির নাম', contact_number as 'কন্টাক্ট নম্বর', comments_01 as 'মন্তব্য ০১', comments_02 as 'মন্তব্য ০২' FROM second_parties ORDER BY id DESC", conn)
        conn.close()
        
        if not sp_df.empty:
            if search_sp:
                q = search_sp.lower()
                sp_df = sp_df[sp_df['সেকেন্ড পার্টির নাম'].str.lower().str.contains(q) | sp_df['কন্টাক্ট নম্বর'].str.contains(q)]
                
            st.dataframe(sp_df, use_container_width=True, hide_index=True)
            st.markdown(f"**মোট রেজিস্টার্ড সেকেন্ড পার্টি সংখ্যা:** `{len(sp_df)} টি`")
        else:
            st.info("বর্তমানে ডাটাবেজে কোনো সেকেন্ড পার্টির তথ্য নেই।")
    except Exception as e:
        st.error(f"ডাটা লোড করতে সমস্যা হয়েছে: {e}")

# --- Accounts Management Actions ---
elif current_action == "Cash Management":
    st.markdown(f"### 💵 Cash Management ({current_company})")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT party_name FROM second_parties")
    parties_list = [r[0] for r in cursor.fetchall()]
    conn.close()
    
    t1, t2, t3 = st.tabs(["📝 Manual Entry", "📤 Bulk Upload (Excel)", "📖 Cash Khata (Ledger)"])
    
    with t1:
        st.markdown("#### 📝 দৈনিক ক্যাশ লেনদেন এন্ট্রি করুন")
        with st.form("manual_cash_form", clear_on_submit=True):
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                cash_date = st.date_input("তারিখ (Date)", datetime.now().date())
                cash_type = st.selectbox("লেনদেনের ধরন (Type)", ["Cash In", "Cash Out"])
                cash_party = st.selectbox("সেকেন্ড পার্টি (Second Party)", parties_list)
            with f_col2:
                cash_amount = st.number_input("পরিমাণ (Amount ৳)", min_value=0.0, step=500.0)
                cash_remarks = st.text_area("মন্তব্য (Remarks)")
                
            save_cash = st.form_submit_button("💾 লেনদেন সংরক্ষণ করুন", use_container_width=True)
            if save_cash:
                if cash_amount <= 0:
                    st.error("পরিমাণ অবশ্যই ০ টাকার বেশি হতে হবে!")
                else:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (str(cash_date), current_company, cash_party, cash_type, cash_amount, cash_remarks))
                    conn.commit()
                    conn.close()
                    st.toast(f"✅ ৳{cash_amount:,.1f} এর লেনদেনটি সফলভাবে সেভ হয়েছে!", icon="💵")
                    import time
                    time.sleep(0.5)
                    st.rerun()
                    
    with t2:
        st.markdown("#### 📤 এক্সেল ফাইল আপলোডের মাধ্যমে বাল্ক এন্ট্রি")
        
        cash_buffer = io.BytesIO()
        cash_template_df = pd.DataFrame(columns=["date", "second_party", "type", "amount", "remarks"])
        cash_template_df.loc[0] = [str(datetime.now().date()), "Hand_Cash", "Cash In", 15000.0, "Sample Entry Remarks"]
        cash_template_df.loc[1] = [str(datetime.now().date()), "Bank", "Cash Out", 5000.0, "Office Expense Cash Out"]
        
        with pd.ExcelWriter(cash_buffer, engine='openpyxl') as writer:
            cash_template_df.to_excel(writer, index=False, sheet_name='Cash_Template')
            
        st.download_button("📥 Download Cash Khata Excel Template", data=cash_buffer.getvalue(), file_name="cash_khata_template.xlsx")
        st.markdown("---")
        
        uploaded_cash_file = st.file_uploader("ক্যাশ এক্সেল ফাইল (.xlsx) এখানে আপলোড দিন", type=["xlsx"])
        if uploaded_cash_file is not None:
            try:
                upload_df = pd.read_excel(uploaded_cash_file)
                req_cash_cols = ["date", "second_party", "type", "amount"]
                missing_cash_cols = [c for c in req_cash_cols if c not in upload_df.columns]
                
                if missing_cash_cols:
                    st.error(f"এক্সেলে প্রয়োজনীয় কলাম অনুপস্থিত: {', '.join(missing_cash_cols)}")
                else:
                    st.markdown("##### 🔍 আপলোড করা ফাইলের ডাটা প্রিভিউ:")
                    st.dataframe(upload_df.head(10), use_container_width=True)
                    
                    if st.button("💾 Confirm & Upload Cash Data to Database", type="primary", use_container_width=True):
                        conn = sqlite3.connect(DB_NAME)
                        cursor = conn.cursor()
                        success_tx = 0
                        
                        for _, row in upload_df.iterrows():
                            r_date = str(row['date'])
                            r_party = str(row['second_party'])
                            r_type = str(row['type']).strip() if str(row['type']).strip() in ["Cash In", "Cash Out"] else "Cash In"
                            r_amount = float(row['amount']) if pd.notnull(row['amount']) else 0.0
                            r_remarks = str(row.get('remarks', '')) if pd.notnull(row.get('remarks')) else ''
                            
                            if r_amount > 0:
                                cursor.execute("""
                                    INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (r_date, current_company, r_party, r_type, r_amount, r_remarks))
                                success_tx += 1
                                
                        conn.commit()
                        conn.close()
                        st.success(f"✅ সফলভাবে মোট {success_tx} টি ক্যাশ লেনদেন ডাটাবেজে ইমপোর্ট হয়েছে!")
                        import time
                        time.sleep(1)
                        st.rerun()
            except Exception as e:
                st.error(f"ফাইলটি প্রসেস করতে ত্রুটি হয়েছে: {e}")
                
    with t3:
        st.markdown("#### 📖 Cash Khata (Daily Report & Ledger View)")
        
        conn = sqlite3.connect(DB_NAME)
        tx_query = "SELECT date as 'তারিখ', second_party as 'সেকেন্ড পার্টি', type as 'ধরনের লেনদেন', amount as 'পরিমাণ (৳)', remarks as 'মন্তব্য' FROM cash_transactions WHERE company = ? ORDER BY date DESC, id DESC"
        tx_df = pd.read_sql_query(tx_query, conn, params=(current_company,))
        conn.close()
        
        if not tx_df.empty:
            total_in = tx_df[tx_df['ধরনের লেনদেন'] == 'Cash In']['পরিমাণ (৳)'].sum()
            total_out = tx_df[tx_df['ধরনের লেনদেন'] == 'Cash Out']['পরিমাণ (৳)'].sum()
            closing_balance = total_in - total_out
            
            m1, m2, m3 = st.columns(3)
            m1.metric("মোট ক্যাশ ইন (Total Cash In)", f"{total_in:,.1f} ৳")
            m2.metric("মোট ক্যাশ আউট (Total Cash Out)", f"{total_out:,.1f} ৳")
            m3.metric("ক্লোজিং ব্যালেন্স (Closing Balance)", f"{closing_balance:,.1f} ৳")
            
            st.markdown("---")
            search_p = st.text_input("🔍 সেকেন্ড পার্টি ফিল্টার করুন (Search by Second Party Name):")
            if search_p:
                tx_df = tx_df[tx_df['সেকেন্ড পার্টি'].str.lower().str.contains(search_p.lower())]
                
            st.dataframe(tx_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"বর্তমানে {current_company}-এর আন্ডারে কোনো ক্যাশ লেনদেনের রেকর্ড ডাটাবেজে নেই।")

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
