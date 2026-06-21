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
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1]) 
    with col2:
        st.markdown(
            """
            <div style='background-color: #1e1e1e; padding: 30px; border-radius: 10px; border: 1px solid #333; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.5);'>
                <h2 style='text-align: center; color: #10b981; margin-bottom: 5px; font-family: sans-serif;'>M/S JABED ENTERPRISE</h2>
                <p style='text-align: center; color: #a0a0a0; font-size: 14px; margin-bottom: 20px;'>সিস্টেমে প্রবেশ করতে লগইন করুন</p>
            """, unsafe_allow_html=True
        )
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            login_button = st.form_submit_button("লগইন (Login)", use_container_width=True)
            
            if login_button:
                if username == "admin" and password == "jabed2026":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.session_state.current_action = None 
                    st.success("এডমিন হিসেবে লগইন সফল হয়েছে!")
                    import time; time.sleep(0.5); st.rerun()
                elif username == "bKash_User" and password == "bkash2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "bKash_User"
                    st.session_state.current_company = "bKash" 
                    st.session_state.current_action = None 
                    st.success("বিকাশ ইউজার লগইন সফল!")
                    import time; time.sleep(0.5); st.rerun()
                elif username == "GP_User" and password == "gp2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "GP_User"
                    st.session_state.current_company = "GP" 
                    st.session_state.current_action = None 
                    st.success("GP ইউজার লগইন সফল!")
                    import time; time.sleep(0.5); st.rerun()
                else:
                    st.error("ভুল ইউজারনেম অথবা পাসওয়ার্ড! আবার চেষ্টা করুন।")
        st.markdown("</div>", unsafe_allow_html=True)
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
# ৩. ডাটাবেজ এবং অ্যাডভান্সড মাইগ্রেশন লজিক
# ==============================================================================
def init_db():
    for folder in [UPLOAD_DIR, IMAGE_DIR, PHOTO_DIR, EMP_NID_DIR, GUAR_PHOTO_DIR, GUAR_NID_DIR]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            emp_id TEXT PRIMARY KEY, name TEXT NOT NULL, designation TEXT, mobile TEXT, alt_contact TEXT, join_date TEXT,
            basic_salary REAL, variable_salary REAL, total_salary REAL, company TEXT NOT NULL, father_name TEXT,
            father_nid TEXT, mother_name TEXT, emp_nid TEXT, guarantor_name TEXT, guarantor_nid TEXT, guarantor_mobile TEXT
        )
    ''')
    
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
            CREATE TABLE second_parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, party_name TEXT NOT NULL, 
                contact_number TEXT, comments_01 TEXT, comments_02 TEXT, status TEXT DEFAULT 'Active', UNIQUE(company, party_name)
            )
        ''')
    
    default_parties = ["Mother_Wallet", "Hand_Cash", "Petty_Cash", "Bank", "BGP", "Dulal", "Shafayat", "Madina", "Owner", "GAS", "Auto_Rice", "Others", "bKash", "Commission", "Al_Arafa", "Rekit", "DMCBL", "Kabita_Mami", "Ashim_Da", "Al_Amin"]
    for party in default_parties:
        cursor.execute("INSERT OR IGNORE INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) VALUES ('bKash', ?, '', '', '', 'Active')", (party,))
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, company TEXT NOT NULL, second_party TEXT NOT NULL, type TEXT NOT NULL, amount REAL NOT NULL, remarks TEXT
        )
    ''')
    
    cursor.execute("PRAGMA table_info(employees)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    required_cols = {'company': "TEXT DEFAULT 'bKash'", 'father_name': "TEXT", 'father_nid': "TEXT", 'mother_name': "TEXT", 'emp_nid': "TEXT", 'guarantor_name': "TEXT", 'guarantor_nid': "TEXT", 'guarantor_mobile': "TEXT"}
    for col_name, col_type in required_cols.items():
        if col_name not in existing_columns:
            cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type}")
            
    conn.commit(); conn.close()

init_db()

# ==============================================================================
# ৪. গ্লোবাল সেশন স্টেট এবং হেল্পার ফাংশন
# ==============================================================================
for state_key, default_val in [('current_company', 'None'), ('current_action', None), ('active_emp_id', None), ('dialog_edit_mode', False), ('active_party_id', None), ('party_edit_mode', False)]:
    if state_key not in st.session_state:
        st.session_state[state_key] = default_val

def open_edit_mode(): st.session_state.dialog_edit_mode = True
def close_edit_mode(): st.session_state.dialog_edit_mode = False

def render_no_image_frame(title):
    return f"""
    <div style="border: 1px dashed #555; border-radius: 6px; background-color: #1a1a1a; 
                height: 145px; display: flex; flex-direction: column; justify-content: center; 
                align-items: center; color: #888888; text-align: center; margin-bottom: 15px; padding: 5px;">
        <span style="font-size: 24px; margin-bottom: 2px;">🖼️</span>
        <b style="font-size: 12px; color: #aaa;">No Image</b>
        <span style="font-size: 10px; color: #666; margin-top: 2px;">({title})</span>
    </div>
    """

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
            logo_html = f'<img src="data:image/{ext};base64,{encoded}" style="height:45px; vertical-align: middle;">'
            has_logo = True; break
            
    title_text = '<h2 style="color: white; margin: 0; font-family: sans-serif; font-size: 28px; font-weight: bold; letter-spacing: 1px;">M/S JABED ENTERPRISE</h2>'
    header_content = f'<div style="display: flex; justify-content: center; align-items: center; gap: 10px;">{logo_html}{title_text}</div>' if has_logo else title_text
    st.markdown(f"""
        <div style="text-align: center; margin-top: -30px; margin-bottom: 5px;">
            {header_content}
            <p style="color: #888; margin: 4px 0 0 0; font-size: 13px;">394 Anima Plaza, Nagerbazar, Bagerhat Sadar, Bagerhat</p>
        </div>
        <hr style="border: 1px solid #333; margin-top: 15px; margin-bottom: 25px;">
    """, unsafe_allow_html=True)

# ==============================================================================
# 👥 সেকেন্ড পার্টির প্রোফাইল ডিটেইলস ও এডিট ডায়ালগ
# ==============================================================================
@st.dialog("Second Party Details", width="medium")
def show_second_party_details(party_id):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT id, party_name, contact_number, comments_01, comments_02, status FROM second_parties WHERE id = ?", (party_id,))
    party = cursor.fetchone(); conn.close()
    if not party:
        st.error("Second Party not found!"); st.session_state.active_party_id = None; return
    p_id, p_name, p_contact, p_c1, p_c2, p_status = party
    p_status = p_status or "Active"
    
    col_t1, col_t2 = st.columns([6, 2])
    with col_t1:
        if not st.session_state.party_edit_mode:
            if st.button("✏️ Edit", key="sp_edit_toggle_btn"): st.session_state.party_edit_mode = True; st.rerun()
        else:
            if st.button("⬅️ Back to View", key="sp_view_toggle_btn"): st.session_state.party_edit_mode = False; st.rerun()
    with col_t2:
        if st.button("❌ Close", use_container_width=True, key="sp_close_popup_btn"):
            st.session_state.active_party_id = None; st.session_state.party_edit_mode = False; st.rerun()
    st.divider()
    if not st.session_state.party_edit_mode:
        st.markdown(f"#### **Party Name:** {p_name}")
        st.markdown(f"**Contact Number:** {p_contact or '-'}")
        st.markdown(f"**Comments 01:** {p_c1 or '-'}")
        st.markdown(f"**Comments 02:** {p_c2 or '-'}")
        status_color = "#10b981" if p_status == "Active" else "#ef4444"
        st.markdown(f"**Status:** <span style='color:{status_color}; font-weight:bold;'>{p_status}</span>", unsafe_allow_html=True)
    else:
        with st.form("edit_second_party_form_v1"):
            st.markdown("#### 📝 Update Info")
            new_p_name = st.text_input("Party Name *", value=p_name)
            new_p_contact = st.text_input("Contact Number", value=p_contact)
            new_p_c1 = st.text_input("Comments 01", value=p_c1)
            new_p_c2 = st.text_input("Comments 02", value=p_c2)
            new_p_status = st.selectbox("Status", ["Active", "Inactive"], index=0 if p_status == "Active" else 1)
            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                if not new_p_name.strip(): st.error("নাম খালি রাখা যাবে না!")
                else:
                    try:
                        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                        cursor.execute("UPDATE second_parties SET party_name=?, contact_number=?, comments_01=?, comments_02=?, status=? WHERE id=?", 
                                       (new_p_name.strip(), new_p_contact.strip(), new_p_c1.strip(), new_p_c2.strip(), new_p_status, party_id))
                        conn.commit(); conn.close()
                        st.toast("আপডেট সম্পন্ন হয়েছে!", icon="✅")
                        st.session_state.active_party_id = None; st.session_state.party_edit_mode = False
                        import time; time.sleep(0.5); st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("এই নামের পার্টি ইতিমধ্যে বিদ্যমান!")

# ==============================================================================
# 🔍 কর্মচারীর প্রোফাইল ডিটেইলস ডায়ালগ 
# ==============================================================================
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
        st.error("Employee not found!")
        st.session_state.active_emp_id = None
        return
        
    (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary,
     father_name, father_nid, mother_name, emp_nid, guarantor_name, guarantor_nid, guarantor_mobile) = emp
    
    col_t1, col_t2 = st.columns([6, 2])
    with col_t1:
        if not st.session_state.dialog_edit_mode: st.button("✏️ Edit Profile", type="secondary", key="popup_edit_btn", on_click=open_edit_mode)
        else: st.button("⬅️ Back to View", type="secondary", key="popup_back_btn", on_click=close_edit_mode)
    with col_t2:
        if st.button("❌ Close", use_container_width=True, key="popup_close_btn"):
            st.session_state.active_emp_id = None 
            st.session_state.dialog_edit_mode = False
            st.rerun()
    st.divider()
    
    emp_photo_path = os.path.join(PHOTO_DIR, f"{emp_id}_emp.png")
    emp_nid_path = os.path.join(EMP_NID_DIR, f"{emp_id}_nid.png")
    guar_photo_path = os.path.join(GUAR_PHOTO_DIR, f"{emp_id}_guar.png")
    guar_nid_path = os.path.join(GUAR_NID_DIR, f"{emp_id}_guar_nid.png")

    if not st.session_state.dialog_edit_mode:
        col_info, col_img = st.columns([4.5, 2.5])
        with col_info:
            st.markdown(f"#### {name}")
            st.markdown(f"**ID:** `{emp_id}` | **Designation:** `{designation}`")
            st.markdown(f"**Mobile:** {mobile or '-'} | **Alt Contact:** {alt_contact or '-'}")
            st.markdown(f"**Join Date:** {join_date}")
            st.markdown(f"**NID No:** {emp_nid or '-'}")
        with col_img:
            img_c1, img_c2 = st.columns(2)
            with img_c1: 
                if os.path.exists(emp_photo_path): st.image(emp_photo_path, caption="Photo", use_container_width=True)
                else: st.markdown(render_no_image_frame("Photo"), unsafe_allow_html=True)
            with img_c2: 
                if os.path.exists(emp_nid_path): st.image(emp_nid_path, caption="NID", use_container_width=True)
                else: st.markdown(render_no_image_frame("NID"), unsafe_allow_html=True)
                
        st.markdown("<h5 style='color:#10b981; margin-top:10px;'>📂 Family Information</h5>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.markdown(f"**Father's Name:** {father_name or '-'}")
        with c2: st.markdown(f"**Mother's Name:** {mother_name or '-'}"); st.markdown(f"**Father's NID:** {father_nid or '-'}")
        
        st.markdown("<h5 style='color:#10b981; margin-top:10px;'>🛡️ Guarantor Details</h5>", unsafe_allow_html=True)
        g_col1, g_col2 = st.columns([4.5, 2.5])
        with g_col1:
            st.markdown(f"**Name:** {guarantor_name or '-'}")
            st.markdown(f"**NID No:** {guarantor_nid or '-'}")
            st.markdown(f"**Mobile:** {guarantor_mobile or '-'}")
        with g_col2:
            g_img_c1, g_img_c2 = st.columns(2)
            with g_img_c1: 
                if os.path.exists(guar_photo_path): st.image(guar_photo_path, caption="Guar Photo", use_container_width=True)
                else: st.markdown(render_no_image_frame("Guar Photo"), unsafe_allow_html=True)
            with g_img_c2: 
                if os.path.exists(guar_nid_path): st.image(guar_nid_path, caption="Guar NID", use_container_width=True)
                else: st.markdown(render_no_image_frame("Guar NID"), unsafe_allow_html=True)
                
        st.markdown("<br>", unsafe_allow_html=True)
        st.info(f"**Salary Structure:** Basic: {basic_salary:,.1f} ৳ | Variable: {variable_salary:,.1f} ৳ | **Total: {total_salary:,.1f} ৳**")
    else:
        with st.form("edit_employee_form_v10"):
            st.markdown(f"##### 📝 Updating ID: `{emp_id}`")
            e_c1, e_c2 = st.columns(2)
            with e_c1:
                new_name = st.text_input("Name *", value=name)
                new_desig = st.selectbox("Designation", ["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"], index=["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"].index(designation) if designation in ["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"] else 0)
                new_mobile = st.text_input("Mobile", value=mobile)
                new_alt = st.text_input("Alternative Contact", value=alt_contact)
                new_emp_nid = st.text_input("Employee NID Number", value=emp_nid)
                new_emp_img = st.file_uploader("Update Photo", type=["png", "jpg", "jpeg"])
                new_emp_nid_img = st.file_uploader("Update NID Card", type=["png", "jpg", "jpeg"])
                new_g_name = st.text_input("Guarantor Name", value=guarantor_name)
                new_g_nid = st.text_input("Guarantor NID Number", value=guarantor_nid)
                new_g_mob = st.text_input("Guarantor Mobile", value=guarantor_mobile)
            with e_c2:
                try: parsed_date = datetime.strptime(join_date, "%Y-%m-%d").date()
                except: parsed_date = datetime.now().date()
                new_date = st.date_input("Join Date", value=parsed_date)
                new_f_name = st.text_input("Father's Name", value=father_name)
                new_f_nid = st.text_input("Father's NID", value=father_nid)
                new_m_name = st.text_input("Mother's Name", value=mother_name)
                new_basic = st.number_input("Basic Salary", min_value=0.0, value=float(basic_salary))
                new_variable = st.number_input("Variable Salary", min_value=0.0, value=float(variable_salary))
                new_guar_img = st.file_uploader("Update Guarantor Photo", type=["png", "jpg", "jpeg"])
                new_guar_nid_img = st.file_uploader("Update Guarantor NID Card", type=["png", "jpg", "jpeg"])
            
            if st.form_submit_button("💾 Save Profile Changes"):
                if not (new_name or "").strip(): st.error("Name খালি রাখা যাবে না!")
                else:
                    if new_emp_img: Image.open(new_emp_img).save(emp_photo_path)
                    if new_emp_nid_img: Image.open(new_emp_nid_img).save(emp_nid_path)
                    if new_guar_img: Image.open(new_guar_img).save(guar_photo_path)
                    if new_guar_nid_img: Image.open(new_guar_nid_img).save(guar_nid_path)
                    
                    new_total = new_basic + new_variable
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE employees SET name=?, designation=?, mobile=?, alt_contact=?, join_date=?, basic_salary=?, variable_salary=?, total_salary=?,
                            father_name=?, father_nid=?, mother_name=?, emp_nid=?, guarantor_name=?, guarantor_nid=?, guarantor_mobile=?
                        WHERE emp_id=? AND company=?
                    """, (new_name.strip(), new_desig, (new_mobile or "").strip(), (new_alt or "").strip(), str(new_date), new_basic, new_variable, new_total,
                          (new_f_name or "").strip(), (new_f_nid or "").strip(), (new_m_name or "").strip(), (new_emp_nid or "").strip(), (new_g_name or "").strip(), (new_g_nid or "").strip(), (new_g_mob or "").strip(), emp_id, company))
                    conn.commit(); conn.close()
                    st.toast("আপডেট সম্পন্ন হয়েছে!", icon="✅")
                    st.session_state.active_emp_id = None 
                    st.session_state.dialog_edit_mode = False
                    import time; time.sleep(0.5); st.rerun()

# ==============================================================================
# 💈 সাইডবার ন্যাভিগেশন মেনু (Clean & Minimalist)
# ==============================================================================
user_role = st.session_state.get('user_role', None)

if st.sidebar.button("🔒 Logout", use_container_width=True, type="primary"):
    st.session_state.logged_in = False; st.session_state.user_role = None
    st.session_state.current_company = None; st.session_state.current_action = None; st.rerun()

st.sidebar.markdown(f"<p style='text-align:center; font-size:14px; color:#a0a0a0; margin-top:5px;'>Logged in as: <span style='color:#10b981; font-weight:bold;'>{user_role}</span></p>", unsafe_allow_html=True)
st.sidebar.divider()

menu_options_emp = ["Add New Employee", "Add Employee By Upload", "View All Employee"]
menu_options_sp = ["Add New Second Party", "View All Second Parties"]

if user_role in ["admin", "bKash_User"]:
    with st.sidebar.expander("📁 bKash Module", expanded=(st.session_state.get('current_company') == "bKash")):
        # Accounts
        if st.button("💵 Cash Management", key="bk_cash_btn", use_container_width=True):
            st.session_state.current_company = "bKash"; st.session_state.current_action = "Cash Management"; st.rerun()
        if st.button("📉 Expense Management", key="bk_exp_btn", use_container_width=True):
            st.session_state.current_company = "bKash"; st.session_state.current_action = "Expense Management"; st.rerun()
        
        # 2nd Party
        with st.expander("👥 2nd Party Management", expanded=False):
            if st.button("➕ Add New Party", key="bk_add_sp_btn", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Add New Second Party"; st.rerun()
            if st.button("📋 View Parties", key="bk_view_sp_btn", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "View All Second Parties"; st.rerun()
        
        # Employee
        with st.expander("👥 Employee Management", expanded=False):
            if st.button("➕ Add Employee", key="bk_add_emp", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Add New Employee"; st.rerun()
            if st.button("📤 Bulk Import", key="bk_bulk_emp", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Add Employee By Upload"; st.rerun()
            if st.button("📋 View All", key="bk_view_emp", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "View All Employee"; st.rerun()
        
        # Others
        if st.button("📁 Others Account", key="bk_oth_btn", use_container_width=True):
            st.session_state.current_company = "bKash"; st.session_state.current_action = "Others"; st.rerun()

if user_role in ["admin", "GP_User"]:
    with st.sidebar.expander("📁 GP Module", expanded=(st.session_state.get('current_company') == "GP")):
        # Accounts
        if st.button("💵 Cash Management", key="gp_cash_btn", use_container_width=True):
            st.session_state.current_company = "GP"; st.session_state.current_action = "Cash Management"; st.rerun()
        if st.button("📉 Expense Management", key="gp_exp_btn", use_container_width=True):
            st.session_state.current_company = "GP"; st.session_state.current_action = "Expense Management"; st.rerun()
            
        # 2nd Party
        with st.expander("👥 2nd Party Management", expanded=False):
            if st.button("➕ Add New Party", key="gp_add_sp_btn", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Add New Second Party"; st.rerun()
            if st.button("📋 View Parties", key="gp_view_sp_btn", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "View All Second Parties"; st.rerun()
                
        # Employee
        with st.expander("👥 Employee Management", expanded=False):
            if st.button("➕ Add Employee", key="gp_add_emp", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Add New Employee"; st.rerun()
            if st.button("📤 Bulk Import", key="gp_bulk_emp", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Add Employee By Upload"; st.rerun()
            if st.button("📋 View All", key="gp_view_emp", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "View All Employee"; st.rerun()
                
        # Others
        if st.button("📁 Others Account", key="gp_oth_btn", use_container_width=True):
            st.session_state.current_company = "GP"; st.session_state.current_action = "Others"; st.rerun()

if user_role == "admin":
    with st.sidebar.expander("📁 Global Others", expanded=False):
        if st.button("📁 Global Others Account", key="main_oth_btn", use_container_width=True):
            st.session_state.current_company = "Others"; st.session_state.current_action = "Others"; st.rerun()

current_action = st.session_state.get('current_action', None)
current_company = st.session_state.get('current_company', None)

# ==============================================================================
# 🚀 অ্যাকশন এক্সিকিউশন লজিক (Main Body Router)
# ==============================================================================
render_header()

if current_action is None:
    st.markdown("<h3 style='text-align: center; color: #10b981; font-weight: normal;'>ড্যাশবোর্ডে আপনাকে স্বাগতম!</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>কাজ শুরু করতে বাম পাশের মেনু থেকে নির্দিষ্ট মডিউল নির্বাচন করুন।</p>", unsafe_allow_html=True)

elif current_action == "Add New Employee":
    st.markdown(f"#### ➕ Add New Employee ({current_company})")
    design_options = ["DM", "Supervisor", "SE", "ITBS", "Accountant", "Peon", "Other"] if current_company == "GP" else ["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"]
    with st.form(f"employee_form_{current_company.lower()}_v10", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            emp_id = st.text_input("Employee ID *")
            name = st.text_input("Name *")
            designation = st.selectbox("Designation", options=design_options)
            mobile = st.text_input("Mobile")
            alt_contact = st.text_input("Alternative Contact")
            emp_nid = st.text_input("NID Number")
            emp_img = st.file_uploader("Upload Photo", type=["png", "jpg", "jpeg"])
            emp_nid_img = st.file_uploader("Upload NID Image", type=["png", "jpg", "jpeg"])
            g_name = st.text_input("Guarantor Name")
            g_nid = st.text_input("Guarantor NID Number")
            g_mob = st.text_input("Guarantor Mobile")
        with col2:
            join_date = st.date_input("Join Date", datetime.now())
            father_name = st.text_input("Father's Name")
            father_nid = st.text_input("Father's NID")
            mother_name = st.text_input("Mother's Name")
            basic_salary = st.number_input("Basic Salary", min_value=0.0, step=500.0, value=0.0)
            variable_salary = st.number_input("Variable Salary", min_value=0.0, step=500.0, value=0.0)
            g_img = st.file_uploader("Upload Guarantor Photo", type=["png", "jpg", "jpeg"])
            g_nid_img = st.file_uploader("Upload Guarantor NID Image", type=["png", "jpg", "jpeg"])
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("💾 Save Employee", use_container_width=True):
            if not emp_id.strip() or not name.strip(): st.error("Employee ID এবং Name পূরণ করা বাধ্যতামূলক!")
            else:
                conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                cursor.execute("SELECT emp_id FROM employees WHERE emp_id=?", (emp_id.strip(),))
                if cursor.fetchone(): st.error("এই ID দিয়ে ইতিমধ্যে একজন কর্মী নিবন্ধিত আছেন!")
                else:
                    if emp_img: Image.open(emp_img).save(os.path.join(PHOTO_DIR, f"{emp_id.strip()}_emp.png"))
                    if emp_nid_img: Image.open(emp_nid_img).save(os.path.join(EMP_NID_DIR, f"{emp_id.strip()}_nid.png"))
                    if g_img: Image.open(g_img).save(os.path.join(GUAR_PHOTO_DIR, f"{emp_id.strip()}_guar.png"))
                    if g_nid_img: Image.open(g_nid_img).save(os.path.join(GUAR_NID_DIR, f"{emp_id.strip()}_guar_nid.png"))
                    
                    total_sal = basic_salary + variable_salary
                    cursor.execute("""
                        INSERT INTO employees (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary, company, father_name, father_nid, mother_name, emp_nid, guarantor_name, guarantor_nid, guarantor_mobile)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (emp_id.strip(), name.strip(), designation, mobile.strip(), alt_contact.strip(), str(join_date), basic_salary, variable_salary, total_sal, current_company, father_name.strip(), father_nid.strip(), mother_name.strip(), emp_nid.strip(), g_name.strip(), g_nid.strip(), g_mob.strip()))
                    conn.commit(); conn.close()
                    st.success("নতুন কর্মীর ডাটা সফলভাবে সংরক্ষিত হয়েছে!")

elif current_action == "Add Employee By Upload":
    st.markdown(f"#### 📤 Bulk Import Employees ({current_company})")
    uploaded_file = st.file_uploader("Excel ফাইল আপলোড করুন", type=["xlsx"])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.dataframe(df.head(5), use_container_width=True)
            if st.button("💾 Push to Database", type="primary"):
                conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                for _, row in df.iterrows():
                    e_id = str(row.get('emp_id', '')).strip()
                    e_name = str(row.get('name', '')).strip()
                    if e_id and e_name:
                        cursor.execute("""
                            INSERT OR REPLACE INTO employees (emp_id, name, designation, mobile, join_date, basic_salary, variable_salary, total_salary, company)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (e_id, e_name, row.get('designation', 'SR'), str(row.get('mobile', '')), str(datetime.now().date()), float(row.get('basic_salary', 0)), float(row.get('variable_salary', 0)), float(row.get('basic_salary', 0))+float(row.get('variable_salary', 0)), current_company))
                conn.commit(); conn.close(); st.success("বাল্ক আপলোড সম্পন্ন হয়েছে!")
        except Exception as e: st.error(f"ভুল ফাইল ফরম্যাট: {e}")

elif current_action == "View All Employee":
    st.markdown(f"#### 📋 Employee Directory ({current_company})")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT emp_id as 'ID', name as 'Name', designation as 'Designation', mobile as 'Mobile', total_salary as 'Total Salary' FROM employees WHERE company=?", conn, params=(current_company,))
    conn.close()
    if df.empty: st.info("কোনো ডাটা পাওয়া যায়নি।")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)
        # Detailed view using buttons map
        st.markdown("##### View Specific Employee Profile")
        c1, c2 = st.columns([1, 3])
        with c1:
            selected_emp_id = st.selectbox("Select Employee ID", df['ID'].tolist())
            if st.button("👁️ View Profile"):
                st.session_state.active_emp_id = selected_emp_id
                st.rerun()

elif current_action == "Add New Second Party":
    st.markdown(f"#### ➕ Add New 2nd Party ({current_company})")
    with st.form("add_sp_form"):
        party_name = st.text_input("Party Name (English Only) *")
        contact = st.text_input("Contact Number")
        c1 = st.text_input("Comments 01")
        c2 = st.text_input("Comments 02")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("💾 Save Party", use_container_width=True):
            if not party_name.strip(): st.error("নাম দেওয়া বাধ্যতামূলক!")
            else:
                try:
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    cursor.execute("INSERT INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) VALUES (?, ?, ?, ?, ?, 'Active')",
                                   (current_company, party_name.strip(), contact.strip(), c1.strip(), c2.strip()))
                    conn.commit(); conn.close(); st.success(f"'{party_name}' সফলভাবে যুক্ত হয়েছে!")
                except sqlite3.IntegrityError: st.error("এই নামের অ্যাকাউন্টটি ইতিমধ্যে বিদ্যমান!")

elif current_action == "View All Second Parties":
    st.markdown(f"#### 📋 2nd Party List ({current_company})")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, party_name as 'Party Name', contact_number as 'Contact', status as 'Status' FROM second_parties WHERE company=?", conn, params=(current_company,))
    conn.close()
    if df.empty: st.info("কোনো অ্যাকাউন্ট পাওয়া যায়নি।")
    else:
        for _, row in df.iterrows():
            col1, col2, col3 = st.columns([4, 2, 2])
            col1.markdown(f"🔹 **{row['Party Name']}**")
            col2.markdown(f"🟢 Active" if row['Status'] == 'Active' else "🔴 Inactive")
            if col3.button("⚙️ Manage", key=f"m_sp_{row['id']}"):
                st.session_state.active_party_id = row['id']; st.rerun()

elif current_action == "Cash Management":
    st.markdown(f"#### 💵 Cash Management ({current_company})")
    conn = sqlite3.connect(DB_NAME)
    parties = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=? AND status='Active'", (current_company,)).fetchall()]
    conn.close()
    
    tab1, tab2 = st.tabs(["📝 Entry", "📖 Ledger Report"])
    with tab1:
        # Two columns for Cash In and Cash Out (Side by Side)
        col_in, col_out = st.columns(2)
        
        with col_in:
            st.markdown("<h5 style='text-align: center; color: #10b981; padding-bottom: 5px;'>📥 Cash Receive (In)</h5>", unsafe_allow_html=True)
            with st.form("cash_in_form", clear_on_submit=True):
                tx_date_in = st.date_input("Date", datetime.now(), key="d_in")
                tx_party_in = st.selectbox("Second Party", options=[""] + parties, key="p_in")
                tx_amount_in = st.number_input("Amount (৳)", min_value=0.0, step=500.0, key="a_in")
                tx_remarks_in = st.text_input("Remarks", key="r_in")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("💾 Receive Cash", use_container_width=True):
                    if tx_party_in == "" or tx_amount_in <= 0: st.error("সঠিক পার্টি এবং অ্যামাউন্ট দিন!")
                    else:
                        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                        cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash In', ?, ?)",
                                       (str(tx_date_in), current_company, tx_party_in, tx_amount_in, tx_remarks_in))
                        conn.commit(); conn.close(); st.success("ক্যাশ রিসিভ সফলভাবে এন্ট্রি হয়েছে!")

        with col_out:
            st.markdown("<h5 style='text-align: center; color: #ef4444; padding-bottom: 5px;'>📤 Pay Out (Out)</h5>", unsafe_allow_html=True)
            with st.form("cash_out_form", clear_on_submit=True):
                tx_date_out = st.date_input("Date", datetime.now(), key="d_out")
                tx_party_out = st.selectbox("Second Party", options=[""] + parties, key="p_out")
                tx_amount_out = st.number_input("Amount (৳)", min_value=0.0, step=500.0, key="a_out")
                tx_remarks_out = st.text_input("Remarks", key="r_out")
                st.markdown("<br>", unsafe_allow_html=True)
                if st.form_submit_button("💾 Pay Out", use_container_width=True):
                    if tx_party_out == "" or tx_amount_out <= 0: st.error("সঠিক পার্টি এবং অ্যামাউন্ট দিন!")
                    else:
                        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                        cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash Out', ?, ?)",
                                       (str(tx_date_out), current_company, tx_party_out, tx_amount_out, tx_remarks_out))
                        conn.commit(); conn.close(); st.success("পে-আউট সফলভাবে এন্ট্রি হয়েছে!")
                        
    with tab2:
        conn = sqlite3.connect(DB_NAME)
        tx_df = pd.read_sql_query("SELECT date as 'Date', second_party as 'Party', type as 'Type', amount as 'Amount', remarks as 'Remarks' FROM cash_transactions WHERE company=? ORDER BY id DESC", conn, params=(current_company,))
        conn.close()
        if not tx_df.empty:
            total_in = tx_df[tx_df['Type'] == 'Cash In']['Amount'].sum()
            total_out = tx_df[tx_df['Type'] == 'Cash Out']['Amount'].sum()
            st.metric("Closing Balance", f"{total_in - total_out:,.1f} ৳", delta=f"In: {total_in} | Out: {total_out}", delta_color="off")
            st.dataframe(tx_df, use_container_width=True, hide_index=True)

elif current_action == "Expense Management":
    st.markdown(f"#### 📉 Expense Management ({current_company})")
    st.info("💡 এই মডিউলের খরচ স্বয়ংক্রিয়ভাবে 'Petty_Cash' অ্যাকাউন্ট থেকে 'Cash Out' হবে।")

    exp_tab1, exp_tab2 = st.tabs(["📥 Entry & Upload", "📖 Expense Ledger"])

    with exp_tab1:
        st.markdown("##### ⚙️ Configuration & Bulk Upload")
        top_c1, top_c2, top_c3, top_c4 = st.columns([2.5, 2, 4.5, 3])
        
        with top_c1:
            exp_date = st.date_input("Date:", datetime.now().date(), key="expense_master_date")
        with top_c2:
            num_rows = st.number_input("Rows:", min_value=1, max_value=25, value=5, step=1, key="expense_num_rows")
        with top_c3:
            uploaded_exp_file = st.file_uploader("Upload Excel", type=["xlsx"], key="excel_expense_uploader")
        with top_c4:
            st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            exp_buffer = io.BytesIO()
            exp_template_df = pd.DataFrame(columns=["date", "expense_type", "expense_category", "sub_category", "amount", "remarks"])
            exp_template_df.loc[0] = [str(datetime.now().date()), "ROI_Expences", "Electricity_Bill", "Electricity_Bill", 1500.0, "Sample Office Bill"]
            with pd.ExcelWriter(exp_buffer, engine='openpyxl') as writer:
                exp_template_df.to_excel(writer, index=False, sheet_name='Expense_Template')
            st.download_button("📥 Download Template", data=exp_buffer.getvalue(), file_name=f"{current_company}_expense_template.xlsx", use_container_width=True)

        if uploaded_exp_file is not None:
            st.divider()
            try:
                upload_df = pd.read_excel(uploaded_exp_file)
                st.markdown("**Preview (Top 5 rows):**")
                st.dataframe(upload_df.head(5), use_container_width=True, hide_index=True)
                if st.button("💾 Push to Database", use_container_width=True, type="primary"):
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor(); count = 0
                    for _, row in upload_df.iterrows():
                        r_date = str(row.get('date', datetime.now().date())).split(" ")[0]
                        r_type = str(row.get('expense_type', '')).strip()
                        r_cat = str(row.get('expense_category', '')).strip()
                        r_subcat = str(row.get('sub_category', r_cat)).strip() 
                        r_amt = float(row['amount']) if pd.notnull(row['amount']) else 0.0
                        r_rem = str(row.get('remarks', '')).strip() if pd.notnull(row.get('remarks', '')) else ""
                        
                        if r_type not in ['nan', 'None', ''] and r_cat not in ['nan', 'None', ''] and r_amt > 0:
                            formatted_remarks = f"[{r_type} -> {r_cat} -> {r_subcat}] {r_rem}".strip()
                            cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)", 
                                           (r_date, current_company, r_amt, formatted_remarks))
                            count += 1
                    conn.commit(); conn.close()
                    if count > 0: st.success(f"✅ সফলভাবে মোট {count}টি খরচ ইমপোর্ট করা হয়েছে!"); import time; time.sleep(0.5); st.rerun()
                    else: st.error("❌ এক্সেলে কোনো বৈধ ডেটা পাওয়া যায়নি!")
            except Exception as e: st.error(f"এক্সেল প্রসেস করতে সমস্যা হয়েছে: {e}")

        st.divider()
        st.markdown("##### 📝 Manual Entry")
        
        categories_map = {
            "": [""],
            "ROI_Expences": ["", "Electricity_Bill", "Entertainment", "House_Rent", "Internet", "Bike_Maintain", "Repair", "Route_Cost", "Stationary", "Water_Bill", "Printing", "Financial_Expence", "Mobil_Change", "Salary", "bKash_Purpose", "Campaign", "Others"],
            "Expences": ["", "Entertainment", "Repair", "T.A", "Printing", "Campaign", "Cash_Pay", "Others"],
            "Merchant": ["", "Entertainment", "Repair", "T.A", "Printing", "Campaign", "Cash_Pay", "Stationary", "Others"]
        }
        
        h1, h2, h3, h4, h5 = st.columns([2, 2.5, 2.5, 1.5, 3.5])
        h1.markdown("**Type**")
        h2.markdown("**Category**")
        h3.markdown("**Sub Category**")
        h4.markdown("**Amount**")
        h5.markdown("**Remarks**")
        
        expense_rows_data = []
        for i in range(int(num_rows)):
            c1, c2, c3, c4, c5 = st.columns([2, 2.5, 2.5, 1.5, 3.5])
            with c1: 
                exp_type = st.selectbox(f"Type_{i}", ["", "ROI_Expences", "Expences", "Merchant"], key=f"exp_type_{i}", label_visibility="collapsed")
            with c2: 
                exp_cat = st.selectbox(f"Cat_{i}", categories_map.get(exp_type, [""]), key=f"exp_cat_{i}", label_visibility="collapsed")
            with c3: 
                sub_options = [""] if exp_cat == "" else [exp_cat]
                exp_subcat = st.selectbox(f"SubCat_{i}", sub_options, key=f"exp_subcat_{i}", label_visibility="collapsed")
            with c4: 
                amt = st.number_input(f"Amt_{i}", min_value=0.0, step=50.0, value=None, key=f"exp_amt_{i}", label_visibility="collapsed")
            with c5: 
                rem = st.text_input(f"Rem_{i}", value="", key=f"exp_rem_{i}", label_visibility="collapsed", placeholder="Details...")
                
            expense_rows_data.append((exp_type, exp_cat, exp_subcat, amt, rem))
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("💾 Submit All Entries", type="primary", use_container_width=True):
            valid_entries = 0; conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
            for etype, ecat, esubcat, eamt, erem in expense_rows_data:
                if etype != "" and ecat != "" and eamt is not None and eamt > 0:
                    formatted_remarks = f"[{etype} -> {ecat} -> {esubcat}] {erem}".strip()
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)", 
                                   (str(exp_date), current_company, eamt, formatted_remarks))
                    valid_entries += 1
            conn.commit(); conn.close()
            if valid_entries > 0: st.toast(f"🎉 মোট {valid_entries}টি খরচ সংরক্ষিত হয়েছে!"); import time; time.sleep(0.5); st.rerun()
            else: st.error("❌ কমপক্ষে একটি সারিতে সঠিক ইনপুট দিন।")

    with exp_tab2:
        st.markdown("##### 📊 Petty Cash Ledger")
        conn = sqlite3.connect(DB_NAME)
        exp_df = pd.read_sql_query("""
            SELECT date as 'Date', amount as 'Amount', remarks as 'Remarks' 
            FROM cash_transactions WHERE company = ? AND second_party = 'Petty_Cash' AND type = 'Cash Out' ORDER BY date DESC, id DESC
        """, conn, params=(current_company,))
        conn.close()
        if not exp_df.empty:
            st.metric("Total Expenses", f"{exp_df['Amount'].sum():,.1f} ৳")
            st.dataframe(exp_df, use_container_width=True, hide_index=True)
        else: st.info("কোনো খরচের রেকর্ড পাওয়া যায়নি।")

elif current_action == "Others":
    st.markdown(f"#### 📁 Others Account ({current_company})")
    st.info("অন্যান্য হিসাবসমূহের ডেটা এন্ট্রি এখানে থাকবে।")

# ==============================================================================
# ৯. গ্লোবাল একটিভ ডায়ালগ কন্ট্রোলার 
# ==============================================================================
if st.session_state.active_emp_id:
    show_employee_details(st.session_state.active_emp_id, st.session_state.current_company)
    st.session_state.active_emp_id = None

if st.session_state.active_party_id:
    show_second_party_details(st.session_state.active_party_id)
