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
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                if username == "admin" and password == "jabed2026":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.session_state.current_action = None 
                    st.success("Welcome Admin!")
                    import time; time.sleep(0.5); st.rerun()
                elif username == "bKash_User" and password == "bkash2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "bKash_User"
                    st.session_state.current_company = "bKash" 
                    st.session_state.current_action = None 
                    st.success("Welcome bKash!")
                    import time; time.sleep(0.5); st.rerun()
                elif username == "GP_User" and password == "gp2026": 
                    st.session_state.logged_in = True
                    st.session_state.user_role = "GP_User"
                    st.session_state.current_company = "GP" 
                    st.session_state.current_action = None 
                    st.success("Welcome GP!")
                    import time; time.sleep(0.5); st.rerun()
                else:
                    st.error("Wrong Username & Password, Please Try Again")
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
for state_key, default_val in [('current_company', None), ('current_action', None), ('active_emp_id', None), ('dialog_edit_mode', False), ('active_party_id', None), ('party_edit_mode', False)]:
    if state_key not in st.session_state:
        st.session_state[state_key] = default_val

def open_edit_mode(): st.session_state.dialog_edit_mode = True
def close_edit_mode(): st.session_state.dialog_edit_mode = False

# সুনির্দিষ্ট সমাপনী ক্যাশ হিস্ট্রি কুয়েরি হেল্পার
def get_historical_closing_balances(company, target_date_str):
    conn = sqlite3.connect(DB_NAME)
    # টার্গেট তারিখের পূর্বের সর্বশেষ তারিখ খুঁজে বের করা যেখানে সমাপনী ডেটা রয়েছে
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
    return f"""
    <div style="border: 2px dashed #444444; border-radius: 8px; background-color: #1e1e1e; 
                height: 145px; display: flex; flex-direction: column; justify-content: center; 
                align-items: center; color: #888888; text-align: center; margin-bottom: 15px; padding: 5px;">
        <span style="font-size: 26px; margin-bottom: 2px;">🖼️</span>
        <b style="font-size: 13px; color: #cccccc;">No Image</b>
        <span style="font-size: 11px; color: #666666; margin-top: 2px;">({title})</span>
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
    st.markdown("---")
    if not st.session_state.party_edit_mode:
        st.markdown(f"### **Second Party Name:** {p_name}")
        st.markdown(f"**Contact Number:** {p_contact or '-'}")
        st.markdown(f"**Comments 01:** {p_c1 or '-'}")
        st.markdown(f"**Comments 02:** {p_c2 or '-'}")
        status_color = "#10b981" if p_status == "Active" else "#ef4444"
        st.markdown(f"**Status:** <span style='color:{status_color}; font-weight:bold; font-size:16px;'>{p_status}</span>", unsafe_allow_html=True)
    else:
        with st.form("edit_second_party_form_v1"):
            st.markdown("#### 📝 Update Second Party Info")
            new_p_name = st.text_input("Second Party Name *", value=p_name)
            new_p_contact = st.text_input("Contact Number", value=p_contact)
            new_p_c1 = st.text_input("Comments 01", value=p_c1)
            new_p_c2 = st.text_input("Comments 02", value=p_c2)
            new_p_status = st.selectbox("Status", ["Active", "Inactive"], index=0 if p_status == "Active" else 1)
            if st.form_submit_button("💾 Save Changes", use_container_width=True):
                if not new_p_name.strip(): st.error("Second Party Name খালি রাখা যাবে না!")
                else:
                    try:
                        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                        cursor.execute("UPDATE second_parties SET party_name=?, contact_number=?, comments_01=?, comments_02=?, status=? WHERE id=?", 
                                       (new_p_name.strip(), new_p_contact.strip(), new_p_c1.strip(), new_p_c2.strip(), new_p_status, party_id))
                        conn.commit(); conn.close()
                        st.toast("Successfully Added Second Party!", icon="✅")
                        st.session_state.active_party_id = None; st.session_state.party_edit_mode = False
                        import time; time.sleep(0.5); st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("এই কোম্পানির আন্ডারে এই নামের আরেকটি সেকেন্ড পার্টি ইতিমধ্যে ডাটাবেজে বিদ্যমান!")

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
        else: st.button("⬅️ Back to View Mode", type="secondary", key="popup_back_btn", on_click=close_edit_mode)
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
            st.markdown(f"**Mobile:** {mobile or '-'} | **Alternative Contact:** {alt_contact or '-'}")
            st.markdown(f"**Joining Date:** {join_date}")
            st.markdown(f"**Employee NID No:** {emp_nid or '-'}")
        with col_img:
            img_c1, img_c2 = st.columns(2)
            with img_c1: 
                if os.path.exists(emp_photo_path): st.image(emp_photo_path, caption="Emp Photo", use_container_width=True)
                else: st.markdown(render_no_image_frame("Emp Photo"), unsafe_allow_html=True)
            with img_c2: 
                if os.path.exists(emp_nid_path): st.image(emp_nid_path, caption="Emp NID Card", use_container_width=True)
                else: st.markdown(render_no_image_frame("Emp NID"), unsafe_allow_html=True)
                
        st.markdown("<h4 style='color:#10b981; margin-top:10px;'>📂 Family Information</h4>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1: st.markdown(f"**Father's Name:** {father_name or '-'}")
        with c2: st.markdown(f"**Mother's Name:** {mother_name or '-'}"); st.markdown(f"**Father's NID:** {father_nid or '-'}")
        
        st.markdown("<h4 style='color:#10b981; margin-top:10px;'>🛡️ Guarantor Details & Documents</h4>", unsafe_allow_html=True)
        g_col1, g_col2 = st.columns([4.5, 2.5])
        with g_col1:
            st.markdown(f"**Guarantor Name:** {guarantor_name or '-'}")
            st.markdown(f"**Guarantor NID No:** {guarantor_nid or '-'}")
            st.markdown(f"**Guarantor Mobile:** {guarantor_mobile or '-'}")
        with g_col2:
            g_img_c1, g_img_c2 = st.columns(2)
            with g_img_c1: 
                if os.path.exists(guar_photo_path): st.image(guar_photo_path, caption="Guar Photo", use_container_width=True)
                else: st.markdown(render_no_image_frame("Guar Photo"), unsafe_allow_html=True)
            with g_img_c2: 
                if os.path.exists(guar_nid_path): st.image(guar_nid_path, caption="Guar NID Card", use_container_width=True)
                else: st.markdown(render_no_image_frame("Guar NID"), unsafe_allow_html=True)
                
        st.markdown("<br>", unsafe_allow_html=True)
        st.success(f"**Salary Structure:** Basic: {basic_salary:,.1f} ৳ | Variable: {variable_salary:,.1f} ৳ | **Total Salary: {total_salary:,.1f} ৳**")
    else:
        with st.form("edit_employee_form_v10"):
            st.markdown(f"#### 📝 Updating Profile for ID: `{emp_id}`")
            e_c1, e_c2 = st.columns(2)
            with e_c1:
                new_name = st.text_input("Name *", value=name)
                new_desig = st.selectbox("Designation", ["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"], index=["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"].index(designation) if designation in ["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"] else 0)
                new_mobile = st.text_input("Mobile", value=mobile)
                new_alt = st.text_input("Alternative Contact", value=alt_contact)
                new_emp_nid = st.text_input("Employee NID Number", value=emp_nid)
                new_emp_img = st.file_uploader("Update Employee Photo", type=["png", "jpg", "jpeg"])
                new_emp_nid_img = st.file_uploader("Update Employee NID Card Image", type=["png", "jpg", "jpeg"])
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
                new_guar_nid_img = st.file_uploader("Update Guarantor NID Card Image", type=["png", "jpg", "jpeg"])
            
            if st.form_submit_button("💾 Save All Profile Changes"):
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
                    st.toast("Succesfuly Updated!", icon="✅")
                    st.session_state.active_emp_id = None 
                    st.session_state.dialog_edit_mode = False
                    import time; time.sleep(0.5); st.rerun()

# ==============================================================================
# 💈 সাইডবার ন্যাভিগেশন মেনু
# ==============================================================================
st.sidebar.markdown("## Main Menu")
user_role = st.session_state.get('user_role', None)
st.sidebar.markdown(f"### স্বাগতম, <span style='color:#10b981;'>{user_role}</span> 👋", unsafe_allow_html=True)

if st.sidebar.button("🔒 Logout", use_container_width=True):
    st.session_state.logged_in = False; st.session_state.user_role = None
    st.session_state.current_company = None; st.session_state.current_action = None; st.rerun()

st.sidebar.markdown("<hr style='margin: 10px 0px; border-color: #444;'>", unsafe_allow_html=True)
menu_options_emp = ["Add New Employee", "Add Employee By Upload", "View All Employee"]

if user_role in ["admin", "bKash_User"]:
    with st.sidebar.expander("📁 bKash", expanded=(st.session_state.get('current_company') == "bKash")):
        with st.expander("📁 Employee Management", expanded=False):
            bk_default = menu_options_emp.index(st.session_state.current_action) if (st.session_state.get('current_company') == "bKash" and st.session_state.get('current_action') in menu_options_emp) else None
            def bk_emp_cb(): st.session_state.current_company = "bKash"; st.session_state.current_action = st.session_state.bk_emp_radio
            st.radio("bKash Emp Options", options=menu_options_emp, index=bk_default, key="bk_emp_radio", on_change=bk_emp_cb, label_visibility="collapsed")
        with st.expander("📊 Account Management", expanded=False):
            if st.button("💵 Cash Management", key="bk_cash_btn", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Cash Management"; st.rerun()
            if st.button("📉 Expense Management", key="bk_exp_btn", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Expense Management"; st.rerun()
            with st.expander("👥 Second Party Management", expanded=False):
                if st.button("➕ Add New Second Party", key="bk_add_sp_btn", use_container_width=True):
                    st.session_state.current_company = "bKash"; st.session_state.current_action = "Add New Second Party"; st.rerun()
                if st.button("📋 View All Second Parties", key="bk_view_sp_btn", use_container_width=True):
                    st.session_state.current_company = "bKash"; st.session_state.current_action = "View All Second Parties"; st.rerun()
        with st.expander("📁 Others", expanded=False):
            if st.button("📁 Others Account", key="bk_oth_btn", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Others"; st.rerun()

if user_role in ["admin", "GP_User"]:
    with st.sidebar.expander("📁 GP", expanded=(st.session_state.get('current_company') == "GP")):
        with st.expander("📁 Employee Management", expanded=False):
            gp_default = menu_options_emp.index(st.session_state.current_action) if (st.session_state.get('current_company') == "GP" and st.session_state.get('current_action') in menu_options_emp) else None
            def gp_emp_cb(): st.session_state.current_company = "GP"; st.session_state.current_action = st.session_state.gp_emp_radio
            st.radio("GP Emp Options", options=menu_options_emp, index=gp_default, key="gp_emp_radio", on_change=gp_emp_cb, label_visibility="collapsed")
        with st.expander("📊 Account Management", expanded=False):
            if st.button("💵 Cash Management", key="gp_cash_btn", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Cash Management"; st.rerun()
            if st.button("📉 Expense Management", key="gp_exp_btn", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Expense Management"; st.rerun()
            with st.expander("👥 Second Party Management", expanded=False):
                if st.button("➕ Add New Second Party", key="gp_add_sp_btn", use_container_width=True):
                    st.session_state.current_company = "GP"; st.session_state.current_action = "Add New Second Party"; st.rerun()
                if st.button("📋 View All Second Parties", key="gp_view_sp_btn", use_container_width=True):
                    st.session_state.current_company = "GP"; st.session_state.current_action = "View All Second Parties"; st.rerun()
        with st.expander("📁 Others", expanded=False):
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
    st.markdown("<h3 style='text-align: center; color: #10b981;'>Welcome to M/S Jabed Enterprise!</h3>", unsafe_allow_html=True)
    st.info("💡 Please Select A Menu From Sidebar")

elif current_action == "Add New Employee":
    st.markdown(f"### 👥 Add New Employee ({current_company})")
    design_options = ["DM", "Supervisor", "SE", "ITBS", "Accountant", "Peon", "Other"] if current_company == "GP" else ["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"]
    with st.form(f"employee_form_{current_company.lower()}_v10", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            emp_id = st.text_input("Employee ID *")
            name = st.text_input("Name *")
            designation = st.selectbox("Designation", options=design_options)
            mobile = st.text_input("Mobile")
            alt_contact = st.text_input("Alternative Contact")
            emp_nid = st.text_input("Employee NID Number")
            emp_img = st.file_uploader("Upload Employee Photo", type=["png", "jpg", "jpeg"])
            emp_nid_img = st.file_uploader("Upload Employee NID Card Image", type=["png", "jpg", "jpeg"])
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
            g_nid_img = st.file_uploader("Upload Guarantor NID Card Image", type=["png", "jpg", "jpeg"])
        
        if st.form_submit_button("💾 Save Employee Profile"):
            if not emp_id.strip() or not name.strip(): st.error("Employee ID এবং Name অবশ্যই পূরণ করতে হবে!")
            else:
                conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                cursor.execute("SELECT emp_id FROM employees WHERE emp_id=?", (emp_id.strip(),))
                if cursor.fetchone(): st.error("এই Employee ID দিয়ে ইতিমধ্যে একজন কর্মী নিবন্ধিত আছেন!")
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
                    st.success("🎉 Succesfully Added New Employee Data!")

elif current_action == "Add Employee By Upload":
    st.markdown(f"### 📤 Bulk Import Employees ({current_company})")
    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.dataframe(df.head(5), use_container_width=True)
            if st.button("💾 Save"):
                conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                for _, row in df.iterrows():
                    e_id = str(row.get('emp_id', '')).strip()
                    e_name = str(row.get('name', '')).strip()
                    if e_id and e_name:
                        # ডাটাবেজে আইডিটি আগে থেকে আছে কিনা তা চেক করা হচ্ছে
  cursor.execute("SELECT 1 FROM employees WHERE emp_id = ?", (e_id,))
  if cursor.fetchone():
      # আইডি থাকলে ফ্যামিলি ডাটা ও ছবি অক্ষত রেখে শুধু বেসিক কলামগুলো আপডেট হবে
      cursor.execute("""
          UPDATE employees 
          SET name=?, designation=?, mobile=?, basic_salary=?, variable_salary=?, total_salary=?, company=?
          WHERE emp_id=?
      """, (e_name, e_des, e_mob, b_sal, v_sal, t_sal, current_company, e_id))
  else:
      # আইডি একদম নতুন হলে নতুন রো ইনসার্ট হবে
      cursor.execute("""
          INSERT INTO employees (emp_id, name, designation, mobile, basic_salary, variable_salary, total_salary, company)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      """, (e_id, e_name, e_des, e_mob, b_sal, v_sal, t_sal, current_company))
                conn.commit(); conn.close(); st.success("🎉 Bulk Employee Data Successfully Uploaded & Updated Without Any Data Loss!")
        except Exception as e: st.error(f"ভুল ফাইল ফরম্যাট: {e}")

elif current_action == "View All Employee":
    st.markdown(f"### 📋 Employee Directory ({current_company})")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT emp_id as 'ID', name as 'নাম', designation as 'পদবী', mobile as 'মোবাইল', total_salary as 'মোট বেতন (৳)' FROM employees WHERE company=?", conn, params=(current_company,))
    conn.close()
    if df.empty: st.info("কোনো ডাটা পাওয়া যায়নি।")
    else:
        for idx, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
            c1.markdown(f"`{row['ID']}`")
            c2.markdown(f"**{row['নাম']}** ({row['পদবী']})")
            c3.markdown(f"📞 {row['মোবাইল'] or '-'}")
            if c4.button("👁️ View Profile", key=f"v_emp_{row['ID']}"):
                st.session_state.active_emp_id = row['ID']
                st.rerun()

elif current_action == "Add New Second Party":
    st.markdown(f"### 👥 Add New Second Party Account ({current_company})")
    with st.form("add_sp_form"):
        party_name = st.text_input("Second Party Name (English Only) *")
        contact = st.text_input("Contact Number")
        c1 = st.text_input("Comments 01")
        c2 = st.text_input("Comments 02")
        if st.form_submit_button("💾 Save Second Party"):
            if not party_name.strip(): st.error("নাম দেওয়া বাধ্যতামূলক!")
            else:
                try:
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    cursor.execute("INSERT INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) VALUES (?, ?, ?, ?, ?, 'Active')",
                                   (current_company, party_name.strip(), contact.strip(), c1.strip(), c2.strip()))
                    conn.commit(); conn.close(); st.success(f"'{party_name}' সফলভাবে যুক্ত হয়েছে!")
                except sqlite3.IntegrityError: st.error("এই নামের অ্যাকাউন্টটি ইতিমধ্যে বিদ্যমান!")

elif current_action == "View All Second Parties":
    st.markdown(f"### 📋 Second Party List ({current_company})")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, party_name as 'অ্যাকাউন্টের নাম', contact_number as 'যোগাযোগ', status as 'স্ট্যাটাস' FROM second_parties WHERE company=?", conn, params=(current_company,))
    conn.close()
    if df.empty: st.info("কোনো অ্যাকাউন্ট পাওয়া যায়নি।")
    else:
        for _, row in df.iterrows():
            col1, col2, col3 = st.columns([4, 2, 2])
            col1.markdown(f"🔹 **{row['অ্যাকাউন্টের নাম']}**")
            col2.markdown(f"🟢 Active" if row['স্ট্যাটাস'] == 'Active' else "🔴 Inactive")
            if col3.button("⚙️ Manage", key=f"m_sp_{row['id']}"):
                st.session_state.active_party_id = row['id']; st.rerun()

elif current_action == "Cash Management":
    st.markdown(f"### 💵 Cash Management ({current_company})")
    
    # ১ নং ছবির সাথে ১০০% চেহারা ও নিখুঁত এলাইনমেন্ট মিলানোর জন্য কাস্টম CSS
    st.markdown("""
        <style>
        /* নাম্বার ইনপুটের + এবং - বাটন সম্পূর্ণ হাইড করার সিএসএস */
        button[data-testid="stNumberInputStepDown"], 
        button[data-testid="stNumberInputStepUp"] {
            display: none !important;
        }
        div[data-testid="stNumberInput"] input {
            padding-right: 10px !important;
        }
        /* ইনপুট বক্সগুলোর মাঝখানের অতিরিক্ত ফাঁকা জায়গা (Padding) কমানো */
        div[data-testid="element-container"] {
            margin-bottom: 5px !important;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 12px !important;
        }
        /* হেডার ও ফোল্ডার টেক্সট স্টাইল */
        .hdr-green {
            background-color: #0d533f; color: white; padding: 8px 15px;
            border-radius: 4px; font-weight: bold; font-size: 14px; text-align: center;
        }
        .hdr-red {
            background-color: #7a1c1c; color: white; padding: 8px 15px;
            border-radius: 4px; font-weight: bold; font-size: 14px; text-align: center;
        }
        .folder-lbl {
            color: #f39c12; font-weight: bold; font-size: 14px; margin-top: 10px; margin-bottom: 10px;
        }
        /* ডানে-বামে নিখুঁত এলাইনমেন্টের জন্য রো গ্রিড */
        .meta-label-vertical {
            line-height: 38px; font-size: 14px; color: #aaaaaa;
        }
        .meta-value-vertical {
            line-height: 38px; font-size: 14px; font-weight: bold; text-align: right; color: #ffffff;
        }
        .summary-label-vertical {
            line-height: 32px; font-size: 14px; color: #ffffff;
        }
        .summary-value-vertical {
            line-height: 32px; font-size: 14px; font-weight: bold; text-align: right; color: #ffffff;
        }
        .summary-grand-value {
            line-height: 32px; font-size: 15px; font-weight: bold; text-align: right; color: #00ffaa;
        }
        .meta-hr {
            border: 0; border-top: 1px solid #333333; margin: 8px 0 !important;
        }
        .table-column-title {
            color: #888888; font-size: 13px; font-weight: bold; margin-top: 15px; margin-bottom: 5px;
        }
        </style>
    """, unsafe_allow_html=True)

    # ডাইনামিক রো সংখ্যা ট্র্যাকিং সেশন স্টেট (ডিফল্ট ১৫ দিয়ে শুরু হবে, এক্সেলে বেশি থাকলে অটো বাড়বে)
    if "num_rows_in" not in st.session_state: st.session_state.num_rows_in = 15
    if "num_rows_out" not in st.session_state: st.session_state.num_rows_out = 15

    # ক্যাশ ম্যানেজমেন্ট ট্যাব বিভাজন
    tab1, tab2 = st.tabs(["📝 Daily Cash Khata", "📖 View Cash Khata Report"])

    # ----------------------------------------------------------------------
    # 📝 ট্যাব ১: দৈনিক খাতা এন্ট্রি প্যানেল (এক্সেল আপলোড এবং এডিটেবল ভিউ)
    # ----------------------------------------------------------------------
    with tab1:
        # টপ বার: তারিখ সিলেকশন
        col_top_left, col_top_right = st.columns([7, 3])
        with col_top_left:
            st.markdown("<p style='font-weight:bold; margin-top:8px;'>📅 Date: </p>", unsafe_allow_html=True)
        with col_top_right:
            tx_date = st.date_input("Date", datetime.now().date(), label_visibility="collapsed", key="master_sheet_date")
        
        date_str = str(tx_date)

        # ডাটাবেজ থেকে একটিভ সেকেন্ড পার্টি লিস্ট নিয়ে আসা
        conn = sqlite3.connect(DB_NAME)
        parties = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=? AND status='Active' ORDER BY party_name ASC", (current_company,)).fetchall()]
        conn.close()

        # 📥 এক্সেল ফাইল আপলোড সাব-সেকশন (নতুন সংযোজন)
        with st.expander("📥 Excel Upload"):
            up_col1, up_col2 = st.columns([6, 4])
            with up_col1:
                excel_file = st.file_uploader("Selecy Excel File (.xlsx)", type=["xlsx"], key="cash_excel_uploader")
            with up_col2:
                # আপনার ১ নং প্রশ্নের সমাধান: তারিখ ফিল্টারিং চয়েস পারমিশন
                accept_all_dates = st.radio("📅 তারিখ ফিল্টারিং পারমিশন (Your Choice):", 
                                            ["শুধু ড্যাশবোর্ডের তারিখের ডাটা ফিল্টার করে নিন", "যেকোনো তারিখের সব ডাটা একসাথে গ্রহণ করুন"], 
                                            key="excel_date_choice")
            
            # ছক সম্পূর্ণ ক্লিয়ার করার জন্য অতিরিক্ত রিসেট বাটন
            if st.button("🧹 ছক সম্পূর্ণ খালি করুন (Reset Form)", key="reset_cash_form_btn"):
                st.session_state.num_rows_in = 15
                st.session_state.num_rows_out = 15
                for i in range(200): # সম্ভাব্য সব ঘর রিসেট
                    st.session_state[f"c_p_in_{i}"] = ""; st.session_state[f"c_a_in_{i}"] = 0.0; st.session_state[f"c_r_in_{i}"] = ""
                    st.session_state[f"c_p_out_{i}"] = ""; st.session_state[f"c_a_out_{i}"] = 0.0; st.session_state[f"c_r_out_{i}"] = ""
                st.rerun()

            if excel_file is not None:
                if st.button("📊 এক্সেল ডাটা ইনপুট ছকে লোড করুন", type="secondary", use_container_width=True):
                    try:
                        df = pd.read_excel(excel_file)
                        if len(df.columns) < 5:
                            st.error("এক্সেল ফাইলে অবশ্যই ৫টি কলাম (Date, Type, Second Party, Amount, Detail) থাকতে হবে।")
                        else:
                            # কলাম পজিশন ফিক্সড করা (A, B, C, D, E)
                            df.columns = ['Date', 'Type', 'Party', 'Amount', 'Detail']
                            
                            # এক্সেল ডেট ফরম্যাট ঠিক করা
                            try: df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                            except: df['Date'] = df['Date'].astype(str).str.strip()
                            
                            # আপনার চয়েস অনুযায়ী তারিখ ফিল্টার করা
                            if "শুধু ড্যাশবোর্ডের তারিখের ডাটা" in accept_all_dates:
                                df = df[df['Date'] == date_str]
                            
                            # টাইপ অনুযায়ী RECEIVE এবং PAY OUT আলাদা করা
                            df_in = df[df['Type'].astype(str).str.upper().str.strip() == 'RECEIVE']
                            df_out = df[df['Type'].astype(str).str.upper().str.strip() == 'PAY OUT']
                            
                            # আপনার ২ নং প্রশ্নের সমাধান (অপশন খ): ডাটা অনুযায়ী ডাইনামিক রো নির্ধারণ
                            st.session_state.num_rows_in = max(15, len(df_in))
                            st.session_state.num_rows_out = max(15, len(df_out))
                            
                            # সেশন স্টেটে জমার ডাটা পুশ করা
                            for idx, row in enumerate(df_in.to_dict(orient='records')):
                                p_name = str(row['Party']).strip()
                                st.session_state[f"c_p_in_{idx}"] = p_name if p_name in parties else ""
                                st.session_state[f"c_a_in_{idx}"] = float(row['Amount']) if pd.notnull(row['Amount']) else 0.0
                                st.session_state[f"c_r_in_{idx}"] = str(row['Detail']) if pd.notnull(row['Detail']) and str(row['Detail']) != 'nan' else ""
                            
                            # সেশন স্টেটে খরচের ডাটা পুশ করা
                            for idx, row in enumerate(df_out.to_dict(orient='records')):
                                p_name = str(row['Party']).strip()
                                st.session_state[f"c_p_out_{idx}"] = p_name if p_name in parties else ""
                                st.session_state[f"c_a_out_{idx}"] = float(row['Amount']) if pd.notnull(row['Amount']) else 0.0
                                st.session_state[f"c_r_out_{idx}"] = str(row['Detail']) if pd.notnull(row['Detail']) and str(row['Detail']) != 'nan' else ""
                                
                            st.success(f"🎉 এক্সেল থেকে ডাটা সফলভাবে ইনপুট ছকে লোড হয়েছে! (জমা: {len(df_in)}টি, খরচ: {len(df_out)}টি)। আপনি চাইলে এখনই এগুলো এডিট করতে পারেন।")
                            import time; time.sleep(0.6); st.rerun()
                    except Exception as e:
                        st.error(f"এক্সেল ফাইল পড়তে সমস্যা হয়েছে: {e}")

        # ডাটাবেজ থেকে অটোমেটিক পূর্বের দিনের শেষ সমাপনী ব্যালেন্স ট্র্যাক করা (আজকের ওপেনিং)
        conn = sqlite3.connect(DB_NAME)
        prev_date_row = conn.execute("SELECT DISTINCT date FROM cash_transactions WHERE company=? AND date < ? AND type='System Balance' ORDER BY date DESC LIMIT 1", (current_company, date_str)).fetchone()
        
        op_vault_val, op_bank_val, op_adv_val, op_due_val = 0.0, 0.0, 0.0, 0.0
        if prev_date_row:
            prev_date = prev_date_row[0]
            bal_rows = conn.execute("SELECT second_party, amount FROM cash_transactions WHERE company=? AND date=? AND type='System Balance'", (current_company, prev_date)).fetchall()
            for sp, amt in bal_rows:
                if sp == '__SYS_VAULT__': op_vault_val = amt
                elif sp == '__SYS_BANK__': op_bank_val = amt
                elif sp == '__SYS_ADVANCE__': op_adv_val = amt
                elif sp == '__SYS_DUE__': op_due_val = amt
        conn.close()
        
        total_opening_calc = op_vault_val + op_bank_val + op_adv_val + op_due_val

        # মূল সামারি লে-আউট
        main_col1, main_col2 = st.columns(2)

        # 🟢 বাম কলাম: CASH RECEIVE (জমা)
        with main_col1:
            st.markdown('<div class="hdr-green">🛸 CASH RECEIVE (জমা)</div>', unsafe_allow_html=True)
            st.markdown('<div class="folder-lbl">📁 Opening Cash (অটোমেটিক পূর্বের ব্যালেন্স):</div>', unsafe_allow_html=True)
            
            l_r1_c1, l_r1_c2 = st.columns([7, 5])
            l_r1_c1.markdown('<div class="meta-label-vertical">Opening Vault Cash:</div>', unsafe_allow_html=True)
            l_r1_c2.markdown(f'<div class="meta-value-vertical">{op_vault_val:,.2f} ৳</div>', unsafe_allow_html=True)
            
            l_r2_c1, l_r2_c2 = st.columns([7, 5])
            l_r2_c1.markdown('<div class="meta-label-vertical">DM & DSS Bank:</div>', unsafe_allow_html=True)
            l_r2_c2.markdown(f'<div class="meta-value-vertical">{op_bank_val:,.2f} ৳</div>', unsafe_allow_html=True)
            
            l_r3_c1, l_r3_c2 = st.columns([7, 5])
            l_r3_c1.markdown('<div class="meta-label-vertical">Market Advance:</div>', unsafe_allow_html=True)
            l_r3_c2.markdown(f'<div class="meta-value-vertical">{op_adv_val:,.2f} ৳</div>', unsafe_allow_html=True)
            
            l_r4_c1, l_r4_c2 = st.columns([7, 5])
            l_r4_c1.markdown('<div class="meta-label-vertical">Others Due:</div>', unsafe_allow_html=True)
            l_r4_c2.markdown(f'<div class="meta-value-vertical">{op_due_val:,.2f} ৳</div>', unsafe_allow_html=True)
            
            st.markdown('<hr class="meta-hr">', unsafe_allow_html=True)
            
            l_r5_c1, l_r5_c2 = st.columns([7, 5])
            l_r5_c1.markdown('<div class="summary-label-vertical" style="color:#00ffaa; font-weight:bold;">Total Opening Cash:</div>', unsafe_allow_html=True)
            l_r5_c2.markdown(f'<div class="summary-value-vertical" style="color:#00ffaa; font-weight:bold;">{total_opening_calc:,.2f} ৳</div>', unsafe_allow_html=True)
            
            placeholder_left_summary = st.empty()

        # 🔴 ডান কলাম: PAY OUT (খরচ/প্রদান)
        with main_col2:
            st.markdown('<div class="hdr-red">🛸 PAY OUT (খরচ/প্রদান)</div>', unsafe_allow_html=True)
            st.markdown('<div class="folder-lbl">📁 Closing Balances (ম্যানুয়াল এন্ট্রি):</div>', unsafe_allow_html=True)
            
            r_r1_c1, r_r1_c2 = st.columns([7, 5])
            r_r1_c1.markdown('<div class="meta-label-vertical">Vault Cash:</div>', unsafe_allow_html=True)
            placeholder_vault_cash_text = r_r1_c2.empty()
            
            r_r2_c1, r_r2_c2 = st.columns([7, 5])
            r_r2_c1.markdown('<div class="meta-label-vertical">DM & DSS Bank:</div>', unsafe_allow_html=True)
            m_bank = r_r2_c2.number_input("DM Bank Input", min_value=0.0, step=1.0, key="m_inp_bank")
            
            r_r3_c1, r_r3_c2 = st.columns([7, 5])
            r_r3_c1.markdown('<div class="meta-label-vertical">Market Advance:</div>', unsafe_allow_html=True)
            m_advance = r_r3_c2.number_input("Market Adv Input", min_value=0.0, step=1.0, key="m_inp_advance")
            
            r_r4_c1, r_r4_c2 = st.columns([7, 5])
            r_r4_c1.markdown('<div class="meta-label-vertical">Others Due:</div>', unsafe_allow_html=True)
            m_due = r_r4_c2.number_input("Others Due Input", min_value=0.0, step=1.0, key="m_inp_due")
            
            st.markdown('<hr class="meta-hr">', unsafe_allow_html=True)
            
            r_r5_c1, r_r5_c2 = st.columns([7, 5])
            r_r5_c1.markdown('<div class="summary-label-vertical" style="color:#ff5555; font-weight:bold;">Total Closing Cash:</div>', unsafe_allow_html=True)
            placeholder_total_closing_text = r_r5_c2.empty()
            
            placeholder_right_summary = st.empty()

        # 📊 ডাটা এন্ট্রি গ্রিড প্যানেল (ডাইনামিক রো বাটন কন্ট্রোলড)
        st.markdown("<br>", unsafe_allow_html=True)
        grid_col1, grid_col2 = st.columns(2)
        
        # বাম পাশের ডাইনামিক রো (CASH RECEIVE)
        with grid_col1:
            st.markdown('<p style="color:#00ffaa; font-weight:bold; margin-bottom:0;">➕ আজকের জমা তালিকা (CASH RECEIVE):</p>', unsafe_allow_html=True)
            h_l1, h_l2, h_l3 = st.columns([5, 3, 4])
            h_l1.markdown('<div class="table-column-title">সেকেন্ড পার্টি নাম</div>', unsafe_allow_html=True)
            h_l2.markdown('<div class="table-column-title">Amount ৳</div>', unsafe_allow_html=True)
            h_l3.markdown('<div class="table-column-title">Remarks (বিবরণ)</div>', unsafe_allow_html=True)
            
            inputs_in = []
            for i in range(st.session_state.num_rows_in):
                r_l1, r_l2, r_l3 = st.columns([5, 3, 4])
                with r_l1: p = st.selectbox(f"p_in_{i}", [""] + parties, label_visibility="collapsed", key=f"c_p_in_{i}")
                with r_l2: a = st.number_input(f"a_in_{i}", min_value=0.0, step=1.0, label_visibility="collapsed", key=f"c_a_in_{i}")
                with r_l3: rem = st.text_input(f"r_in_{i}", label_visibility="collapsed", placeholder="-", key=f"c_r_in_{i}")
                if p and a > 0: inputs_in.append((p, a, rem))
            
            if st.button("➕ আরও ১টি জমার রো বাড়ান", key="add_row_in_btn"):
                st.session_state.num_rows_in += 1; st.rerun()

        # ডান পাশের ডাইনামিক রো (PAY OUT)
        with grid_col2:
            st.markdown('<p style="color:#ff5555; font-weight:bold; margin-bottom:0;">➖ আজকের খরচ তালিকা (PAY OUT):</p>', unsafe_allow_html=True)
            h_r1, h_r2, h_r3 = st.columns([5, 3, 4])
            h_r1.markdown('<div class="table-column-title">সেকেন্ড পার্টি নাম</div>', unsafe_allow_html=True)
            h_r2.markdown('<div class="table-column-title">Amount ৳</div>', unsafe_allow_html=True)
            h_r3.markdown('<div class="table-column-title">Remarks (বিবরণ)</div>', unsafe_allow_html=True)
            
            inputs_out = []
            for i in range(st.session_state.num_rows_out):
                r_r1, r_r2, r_r3 = st.columns([5, 3, 4])
                with r_r1: p = st.selectbox(f"p_out_{i}", [""] + parties, label_visibility="collapsed", key=f"c_p_out_{i}")
                with r_r2: a = st.number_input(f"a_out_{i}", min_value=0.0, step=1.0, label_visibility="collapsed", key=f"c_a_out_{i}")
                with r_r3: rem = st.text_input(f"r_out_{i}", label_visibility="collapsed", placeholder="-", key=f"c_r_out_{i}")
                if p and a > 0: inputs_out.append((p, a, rem))
            
            if st.button("➕ আরও ১টি খরচের রো বাড়ান", key="add_row_out_btn"):
                st.session_state.num_rows_out += 1; st.rerun()

        # 🧮 রিয়েল-টাইম লাইভ ম্যাথমেটিক্যাল ক্যালকুলেশন এবং এলাইনমেন্ট লক
        total_today_receive = sum(x[1] for x in inputs_in)
        grand_total_receive = total_opening_calc + total_today_receive
        total_today_payout = sum(x[1] for x in inputs_out)
        
        cl_vault = grand_total_receive - total_today_payout - (m_bank + m_advance + m_due)
        total_closing_calc = cl_vault + m_bank + m_advance + m_due
        grand_total_payout = total_today_payout + total_closing_calc 

        placeholder_vault_cash_text.markdown(f'<div class="meta-value-vertical">{cl_vault:,.2f} ৳</div>', unsafe_allow_html=True)
        placeholder_total_closing_text.markdown(f'<div class="summary-value-vertical" style="color:#ff5555; font-weight:bold;">{total_closing_calc:,.2f} ৳</div>', unsafe_allow_html=True)

        # জমার দিকের এবং খরচের দিকের বটম লাইনগুলো সমান্তরাল লক করা
        placeholder_left_summary.markdown(f"""
            <div style="margin-top:10px;">
                <div class="summary-label-vertical" style="display:inline-block; width:55%;">Today's Receive (আজকের জমা):</div>
                <div class="summary-value-vertical" style="display:inline-block; width:43%;">{total_today_receive:,.2f} ৳</div>
                <hr class="meta-hr">
                <div class="summary-label-vertical" style="display:inline-block; width:55%; font-weight:bold;">Grand Total:</div>
                <div class="summary-grand-value" style="display:inline-block; width:43%;">{grand_total_receive:,.2f} ৳</div>
            </div>
        """, unsafe_allow_html=True)

        placeholder_right_summary.markdown(f"""
            <div style="margin-top:10px;">
                <div class="summary-label-vertical" style="display:inline-block; width:55%;">Today's Pay Out (আজকের খরচ):</div>
                <div class="summary-value-vertical" style="display:inline-block; width:43%;">{total_today_payout:,.2f} ৳</div>
                <hr class="meta-hr">
                <div class="summary-label-vertical" style="display:inline-block; width:55%; font-weight:bold;">Grand Total:</div>
                <div class="summary-grand-value" style="display:inline-block; width:43%; color:#ff5555;">{grand_total_payout:,.2f} ৳</div>
            </div>
        """, unsafe_allow_html=True)

        # 🔒 গলোবাল ডাটাবেজ সেভ বাটন
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔒 এই তারিখের সম্পূর্ণ খাতা একসাথে ডাটাবেজে সংরক্ষণ করুন", type="primary", use_container_width=True, key="save_cash_master_btn"):
            conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
            try:
                cursor.execute("DELETE FROM cash_transactions WHERE company=? AND date=?", (current_company, date_str))
                for p, a, rem in inputs_in:
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash In', ?, ?)", (date_str, current_company, p, a, rem))
                for p, a, rem in inputs_out:
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash Out', ?, ?)", (date_str, current_company, p, a, rem))
                
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_VAULT__', 'System Balance', ?, 'Closing Vault')", (date_str, current_company, cl_vault))
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_BANK__', 'System Balance', ?, 'Closing Bank')", (date_str, current_company, m_bank))
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_ADVANCE__', 'System Balance', ?, 'Closing Advance')", (date_str, current_company, m_advance))
                cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, '__SYS_DUE__', 'System Balance', ?, 'Closing Due')", (date_str, current_company, m_due))
                
                conn.commit()
                st.toast(f"🎉 {date_str} তারিখের সম্পূর্ণ খাতা ডাটাবেজে সফলভাবে সংরক্ষিত হয়েছে!", icon="✅")
                import time; time.sleep(0.4); st.rerun()
            except Exception as e: st.error(f"ডাটা সেভ করতে সমস্যা হয়েছে: {e}")
            finally: conn.close()

    # ----------------------------------------------------------------------
    # 📖 ট্যাব ২: ক্যাশ রিপোর্ট ও খতিয়ান প্যানেল
    # ----------------------------------------------------------------------
    with tab2:
        st.markdown("##### 📊 ক্যাশ লেনদেনের ডাইনামিক খতিয়ান ও ফিল্টার রিপোর্ট")
        f_col1, f_col2, f_col3, f_col4 = st.columns([2.5, 2.5, 4, 3])
        with f_col1: start_d = st.date_input("শুরুর তারিখ (Start Date)", datetime.now().date().replace(day=1), key="cash_rep_start")
        with f_col2: end_d = st.date_input("শেষের তারিখ (End Date)", datetime.now().date(), key="cash_rep_end")
        with f_col3:
            conn = sqlite3.connect(DB_NAME)
            db_parties = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=? ORDER BY party_name ASC", (current_company,)).fetchall()]
            conn.close()
            sel_party = st.selectbox("🎯 নির্দিষ্ট সেকেন্ড পার্টি সিলেক্ট করুন", options=["সব খাতা একসাথে (All Parties)"] + db_parties, key="cash_rep_party")
        with f_col4: sel_type = st.selectbox("💸 লেনদেনের ধরণ", options=["সব লেনদেন (In & Out)", "শুধু জমা (Cash In)", "শুধু খরচ (Cash Out)"], key="cash_rep_type")
            
        query = """
            SELECT date as 'তারিখ', second_party as 'সেকেন্ড পার্টি', type as 'ধরণ', amount as 'অ্যামাউন্ট (৳)', remarks as 'বিস্তারিত বিবরণ' 
            FROM cash_transactions 
            WHERE company=? AND type IN ('Cash In', 'Cash Out') AND date BETWEEN ? AND ?
        """
        params = [current_company, str(start_d), str(end_d)]
        if sel_party != "সব খাতা একসাথে (All Parties)": query += " AND second_party=?"; params.append(sel_party)
        if sel_type == "শুধু জমা (Cash In)": query += " AND type='Cash In'"
        elif sel_type == "শুধু খরচ (Cash Out)": query += " AND type='Cash Out'"
        query += " ORDER BY date DESC, id DESC"
        
        conn = sqlite3.connect(DB_NAME); report_df = pd.read_sql_query(query, conn, params=params); conn.close()
        
        if not report_df.empty:
            t_in = report_df[report_df['ধরণ'] == 'Cash In']['অ্যামাউন্ট (৳)'].sum()
            t_out = report_df[report_df['ধরণ'] == 'Cash Out']['অ্যামাউন্ট (৳)'].sum()
            net_bal = t_in - t_out
            
            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("🟢 সর্বমোট জমা (Total Received)", f"{t_in:,.2f} ৳")
            m2.metric("🔴 সর্বমোট খরচ (Total Payout)", f"{t_out:,.2f} ৳")
            m3.metric("⚖️ নিট লেনদেন ব্যালেন্স (Net Balance)", f"{net_bal:,.2f} ৳", delta=f"{net_bal:,.2f} ৳")
            
            st.markdown("---")
            st.dataframe(report_df, use_container_width=True, hide_index=True)
            
            # পার্টি ভিত্তিক সারসংক্ষেপ
            summary_query = """
                SELECT second_party as 'সেকেন্ড পার্টি',
                       SUM(CASE WHEN type='Cash In' THEN amount ELSE 0 END) as 'মোট জমা (৳)',
                       SUM(CASE WHEN type='Cash Out' THEN amount ELSE 0 END) as 'মোট খরচ (৳)'
                FROM cash_transactions 
                WHERE company=? AND type IN ('Cash In', 'Cash Out') AND date BETWEEN ? AND ?
            """
            sum_params = [current_company, str(start_d), str(end_d)]
            if sel_party != "সব খাতা একসাথে (All Parties)": summary_query += " AND second_party=?"; sum_params.append(sel_party)
            summary_query += " GROUP BY second_party ORDER BY second_party ASC"
            
            conn = sqlite3.connect(DB_NAME); sum_df = pd.read_sql_query(summary_query, conn, params=sum_params); conn.close()
            sum_df['পার্থক্য / নিট ক্যাশ প্রভাব (৳)'] = sum_df['মোট জমা (৳)'] - sum_df['মোট খরচ (৳)']
            st.markdown("<br>📊 **পার্টি-ভিত্তিক পুঞ্জীভূত সারসংক্ষেপ:**", unsafe_allow_html=True)
            st.dataframe(sum_df, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ নির্বাচিত ফিল্টারে কোনো লেনদেনের রেকর্ড পাওয়া যায়নি।")
# ==============================================================================
# লজিক: Expense Management মডিউল 
# ==============================================================================
elif current_action == "Expense Management":
    st.markdown(f"### 📉 Expense Management Module ({current_company})")
    st.markdown("💡 এই মডিউলের সমস্ত খরচ স্বয়ংক্রিয়ভাবে ক্যাশ খাতার **'Petty_Cash'** অ্যাকাউন্ট থেকে মাইনাস (Cash Out) হবে।")

    exp_tab1, exp_tab2 = st.tabs(["📥 খরচ এন্ট্রি ও এক্সেল আপলোড", "📖 খরচের খতিয়ান ও রিপোর্ট"])

    with exp_tab1:
        st.markdown("##### ⚙️ কনফিগারেশন এবং এক্সেল বাল্ক আপলোড")
        top_c1, top_c2, top_c3, top_c4 = st.columns([2.5, 2, 4.5, 3])
        
        with top_c1:
            exp_date = st.date_input("📆 খরচের তারিখ (Date):", datetime.now().date(), key="expense_master_date")
        with top_c2:
            num_rows = st.number_input("সারির সংখ্যা (Rows):", min_value=1, max_value=25, value=10, step=1, key="expense_num_rows")
        with top_c3:
            uploaded_exp_file = st.file_uploader("📤 এক্সেল ফাইল ড্রপ করুন (Bulk Import)", type=["xlsx"], key="excel_expense_uploader")
        with top_c4:
            st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            exp_buffer = io.BytesIO()
            exp_template_df = pd.DataFrame(columns=["date", "expense_type", "expense_category", "sub_category", "amount", "remarks"])
            exp_template_df.loc[0] = [str(datetime.now().date()), "ROI_Expences", "Electricity_Bill", "Electricity_Bill", 1500.0, "Sample Office Bill"]
            exp_template_df.loc[1] = [str(datetime.now().date()), "Expences", "Entertainment", "Entertainment", 350.0, "Guest Tea & Snacks"]
            with pd.ExcelWriter(exp_buffer, engine='openpyxl') as writer:
                exp_template_df.to_excel(writer, index=False, sheet_name='Expense_Template')
            st.download_button("📥 ডাউনলোড টেমপ্লেট", data=exp_buffer.getvalue(), file_name=f"{current_company}_expense_template.xlsx", use_container_width=True)

        if uploaded_exp_file is not None:
            st.markdown("---")
            try:
                upload_df = pd.read_excel(uploaded_exp_file)
                st.markdown("👀 **আপলোড করা ফাইলের প্রিভিউ (প্রথম ৫টি রো):**")
                st.dataframe(upload_df.head(5), use_container_width=True, hide_index=True)
                if st.button("💾 ডাটাবেজে এক্সেল খরচ পুশ করুন", use_container_width=True):
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
                    if count > 0: st.success(f"✅ সফলভাবে মোট {count}টি খরচ এক্সেল থেকে ইমপোর্ট করা হয়েছে!"); import time; time.sleep(0.5); st.rerun()
                    else: st.error("❌ এক্সেলে কোনো বৈধ ডেটা পাওয়া যায়নি!")
            except Exception as e: st.error(f"এক্সেল প্রসেস করতে সমস্যা হয়েছে: {e}")

        st.markdown("---")
        st.markdown("##### 📝 ম্যানুয়াল মাল্টি-রো এন্ট্রি (নতুন Sub Category কলাম সহ)")
        
        categories_map = {
            "": [""],
            "ROI_Expences": ["", "Electricity_Bill", "Entertainment", "House_Rent", "Internet", "Bike_Maintain", "Repair", "Route_Cost", "Stationary", "Water_Bill", "Printing", "Financial_Expence", "Mobil_Change", "Salary", "bKash_Purpose", "Campaign", "Others"],
            "Expences": ["", "Entertainment", "Repair", "T.A", "Printing", "Campaign", "Cash_Pay", "Others"],
            "Merchant": ["", "Entertainment", "Repair", "T.A", "Printing", "Campaign", "Cash_Pay", "Stationary", "Others"]
        }
        
        h1, h2, h3, h4, h5 = st.columns([2, 2.5, 2.5, 1.5, 3.5])
        h1.markdown("**Expense Type**")
        h2.markdown("**খাত (Expense Category)**")
        h3.markdown("**Sub Category**")
        h4.markdown("**পরিমাণ (Amount ৳)**")
        h5.markdown("**বিবরণ (Remarks)**")
        
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
                rem = st.text_input(f"Rem_{i}", value="", key=f"exp_rem_{i}", label_visibility="collapsed", placeholder="বিস্তারিত...")
                
            expense_rows_data.append((exp_type, exp_cat, exp_subcat, amt, rem))
            
        st.markdown("---")
        if st.button("💾 সকল ম্যানুয়াল খরচ একসাথে সাবমিট করুন", type="primary", use_container_width=True):
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
        st.markdown("##### 📊 আপনার কোম্পানির খরচ সমূহের তালিকা (Petty Cash Ledger)")
        conn = sqlite3.connect(DB_NAME)
        exp_df = pd.read_sql_query("""
            SELECT date as 'তারিখ', amount as 'খরচের পরিমাণ (৳)', remarks as 'বিস্তারিত বিবরণ' 
            FROM cash_transactions WHERE company = ? AND second_party = 'Petty_Cash' AND type = 'Cash Out' ORDER BY date DESC, id DESC
        """, conn, params=(current_company,))
        conn.close()
        if not exp_df.empty:
            st.metric("💰 সর্বমোট খরচ (Total Expenses)", f"{exp_df['খরচের পরিমাণ (৳)'].sum():,.1f} ৳")
            st.dataframe(exp_df, use_container_width=True, hide_index=True)
        else: st.info("বর্তমানে কোনো খরচের রেকর্ড পাওয়া যায়নি।")

elif current_action == "Others":
    st.markdown(f"### 📁 Others Account ({current_company})")
    st.info("💡 অন্যান্য ফুটকর বা বিবিধ হিসাবসমূহের ডেটা এন্ট্রি এখানে থাকবে।")

# ==============================================================================
# ৯. গ্লোবাল একটিভ ডায়ালগ কন্ট্রোলার 
# ==============================================================================
if st.session_state.active_emp_id:
    show_employee_details(st.session_state.active_emp_id, st.session_state.current_company)
    st.session_state.active_emp_id = None

if st.session_state.active_party_id:
    show_second_party_details(st.session_state.active_party_id)
