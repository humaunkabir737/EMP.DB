# ==============================================================================
# ১. ইম্পোর্ট এবং পেজ কনফিগারেশন
# ==============================================================================
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS second_parties (
            id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT NOT NULL, party_name TEXT NOT NULL, 
            contact_number TEXT, comments_01 TEXT, comments_02 TEXT, status TEXT DEFAULT 'Active', UNIQUE(company, party_name)
        )
    ''')
    
    default_parties = ["Mother_Wallet", "Hand_Cash", "Petty_Cash", "Bank", "BGP", "Dulal", "Shafayat", "Madina", "Owner", "GAS", "Auto_Rice", "Others", "bKash", "Commission", "Al_Arafa", "Rekit", "DMCBL", "Kabita_Mami", "Ashim_Da", "Al_Amin"]
    for party in default_parties:
        cursor.execute("INSERT OR IGNORE INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) VALUES ('bKash', ?, '', '', '', 'Active')", (party,))
        cursor.execute("INSERT OR IGNORE INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) VALUES ('GP', ?, '', '', '', 'Active')", (party,))
        
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, company TEXT NOT NULL, second_party TEXT NOT NULL, type TEXT NOT NULL, amount REAL NOT NULL, remarks TEXT
        )
    ''')
    
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

# রিয়েল-টাইম পূর্ববর্তী দিন পর্যন্ত মোট ক্লোজিং ব্যালেন্স তথা ওপেনিং ভল্ট ক্যাশ ক্যালকুলেটর
def get_opening_vault_cash(company, target_date_str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN type='Cash In' THEN amount ELSE 0 END) - 
            SUM(CASE WHEN type='Cash Out' THEN amount ELSE 0 END)
        FROM cash_transactions 
        WHERE company=? AND date < ?
    """, (company, target_date_str))
    result = cursor.fetchone()[0]
    conn.close()
    return float(result) if result else 0.0

# নো-ইমেজ ফ্রেম জেনারেটর
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
                elif any(char >= '\u0980' and char <= '\u09ff' for char in new_p_name): st.error("Error: Second Party Name অবশ্যই ইংরেজিতে হতে হবে (No Bengali Allowed)!")
                else:
                    try:
                        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                        cursor.execute("UPDATE second_parties SET party_name=?, contact_number=?, comments_01=?, comments_02=?, status=? WHERE id=?", 
                                       (new_p_name.strip(), new_p_contact.strip(), new_p_c1.strip(), new_p_c2.strip(), new_p_status, party_id))
                        conn.commit(); conn.close()
                        st.toast("সেকেন্ড পার্টির তথ্য সফলভাবে আপডেট করা হয়েছে!", icon="✅")
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
                    st.toast("कर्मীর তথ্য সফলভাবে আপডেট করা হয়েছে!", icon="✅")
                    st.session_state.active_emp_id = None 
                    st.session_state.dialog_edit_mode = False
                    import time; time.sleep(0.5); st.rerun()

# ==============================================================================
# 💈 সাইডবার ন্যাভিগেশন মেনু
# ==============================================================================
st.sidebar.markdown("## Main Menu")
user_role = st.session_state.get('user_role', None)
st.sidebar.markdown(f"### স্বাগতম, <span style='color:#10b981;'>{user_role}</span> 👋", unsafe_allow_html=True)

if st.sidebar.button("🔒 লগআউট (Logout)", use_container_width=True):
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

current_action = st.session_state.get('current_action', None)
current_company = st.session_state.get('current_company', None)

# ==============================================================================
# 🚀 অ্যাকশন এক্সিকিউশন লজিক (Main Body Router)
# ==============================================================================
render_header()

if current_action is None:
    st.markdown("<h3 style='text-align: center; color: #10b981;'>ড্যাশবোর্ড সিস্টেমে আপনাকে স্বাগতম!</h3>", unsafe_allow_html=True)
    st.info("💡 কাজ শুরু করতে বাম পাশের সাইডবার মেনু থেকে কোম্পানির নির্দিষ্ট ফোল্ডার এক্সপ্যান্ড করে কাঙ্ক্ষিত অপশনটি সিলেক্ট করুন।")

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
                    st.success("🎉 নতুন কর্মীর প্রোফাইল সফলভাবে ডাটাবেজে সংরক্ষিত হয়েছে!")

elif current_action == "Add Employee By Upload":
    st.markdown(f"### 📤 Bulk Import Employees ({current_company})")
    uploaded_file = st.file_uploader("এক্সেল ফাইল আপলোড করুন", type=["xlsx"])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.dataframe(df.head(5), use_container_width=True)
            if st.button("💾 ডাটাবেজে পুশ করুন"):
                conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                for _, row in df.iterrows():
                    e_id = str(row.get('emp_id', '')).strip()
                    e_name = str(row.get('name', '')).strip()
                    if e_id and e_name:
                        cursor.execute("""
                            INSERT OR REPLACE INTO employees (emp_id, name, designation, mobile, join_date, basic_salary, variable_salary, total_salary, company)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (e_id, e_name, row.get('designation', 'SR'), str(row.get('mobile', '')), str(datetime.now().date()), float(row.get('basic_salary', 0)), float(row.get('variable_salary', 0)), float(row.get('basic_salary', 0))+float(row.get('variable_salary', 0)), current_company))
                conn.commit(); conn.close(); st.success("সাফল্যের সাথে বাল্ক আপলোড সম্পন্ন হয়েছে!")
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
            elif any(char >= '\u0980' and char <= '\u09ff' for char in party_name): st.error("Error: Second Party Name অবশ্যই ইংরেজিতে হতে হবে (No Bengali Allowed)!")
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

# ==============================================================================
# লজিক: 💵 Cash Management (bKash/GP-এর জন্য অ্যাডভান্সড ডাবল-এন্ট্রি ও এক্সেল আপলোড)
# ==============================================================================
elif current_action == "Cash Management":
    st.markdown(f"### 💵 Advanced Cash Khata Management ({current_company})")
    
    conn = sqlite3.connect(DB_NAME)
    parties = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=? AND status='Active'", (current_company,)).fetchall()]
    conn.close()

    tab1, tab2 = st.tabs(["📝 ডাবল-এন্ট্রি লেনদেন গ্রিড ও এক্সেল আপলোড", "📖 ক্যাশ খাতার খতিয়ান ও খেরোখাতা"])
    
    with tab1:
        # ----------------------------------------------------------------------
        # অংশ ১: Upload by Excel অপশন সংযোজন
        # ----------------------------------------------------------------------
        st.markdown("##### 📤 Upload Cash Khata via Excel (Bulk Import)")
        up_col1, up_col2 = st.columns([3, 1])
        with up_col1:
            uploaded_cash_excel = st.file_uploader("ক্যাশ খাতার এক্সেল ফাইলটি ড্রপ করুন:", type=["xlsx"], key="excel_cash_uploader")
        with up_col2:
            st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            cash_template_buffer = io.BytesIO()
            cash_temp_df = pd.DataFrame(columns=["date", "second_party", "type", "amount", "remarks"])
            cash_temp_df.loc[0] = [str(datetime.now().date()), "Mother_Wallet", "Cash In", 50000.0, "Bank Transfer In"]
            cash_temp_df.loc[1] = [str(datetime.now().date()), "Hand_Cash", "Cash Out", 12000.0, "Daily Market Payout"]
            with pd.ExcelWriter(cash_template_buffer, engine='openpyxl') as writer:
                cash_temp_df.to_excel(writer, index=False, sheet_name='Cash_Template')
            st.download_button("📥 ডাউনলোড ক্যাশ টেমপ্লেট", data=cash_template_buffer.getvalue(), file_name=f"{current_company}_cash_template.xlsx", use_container_width=True)

        if uploaded_cash_excel is not None:
            try:
                xl_df = pd.read_excel(uploaded_cash_excel)
                st.markdown("👀 **এক্সেল ফাইলের প্রিভিউ:**")
                st.dataframe(xl_df.head(5), use_container_width=True, hide_index=True)
                if st.button("💾 এক্সেল ডাটা সরাসরি পুশ করুন", key="push_excel_cash_btn"):
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    success_count = 0
                    for _, row in xl_df.iterrows():
                        c_date = str(row.get('date', datetime.now().date())).split(" ")[0]
                        c_party = str(row.get('second_party', '')).strip()
                        c_type = str(row.get('type', '')).strip()
                        c_amount = float(row['amount']) if pd.notnull(row['amount']) else 0.0
                        c_remarks = str(row.get('remarks', '')).strip() if pd.notnull(row.get('remarks', '')) else ""
                        
                        if c_party and c_type in ["Cash In", "Cash Out"] and c_amount > 0:
                            cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, ?, ?, ?)",
                                           (c_date, current_company, c_party, c_type, c_amount, c_remarks))
                            success_count += 1
                    conn.commit(); conn.close()
                    if success_count > 0:
                        st.success(f"✅ এক্সেল থেকে সফলভাবে {success_count}টি লেনদেন ডাটাবেজে অন্তর্ভুক্ত করা হয়েছে!"); import time; time.sleep(0.5); st.rerun()
                    else:
                        st.error("❌ ফাইলে কোনো ভ্যালিড লেনদেন খুঁজে পাওয়া যায়নি!")
            except Exception as e:
                st.error(f"এক্সেল প্রসেসিং এরর: {e}")

        st.markdown("<hr style='border: 0.5px solid #333;'>", unsafe_allow_html=True)
        
        # ----------------------------------------------------------------------
        # অংশ ২: ডাইনামিক পাশাপাশি ডাবল টেবিল (3.jpg সংযুক্ত ফরম্যাট অনুযায়ী)
        # ----------------------------------------------------------------------
        st.markdown("##### 📝 ম্যানুয়াল সাইড-বাই-সাইড ডাবল-এন্ট্রি সিস্টেম")
        
        # উপরে ডেট পরিবর্তনের মাস্টার কন্ট্রোল
        tx_master_date = st.date_input("📆 হিসাবের তারিখ পরিবর্তন করুন (Date Master):", datetime.now().date(), key="cash_master_entry_date")
        target_date_str = str(tx_master_date)
        
        # রিয়েল-টাইম পূর্ববর্তী দিনগুলোর ক্লোজিং থেকে ওপেনিং ভল্ট ক্যাশ ক্যালকুলেট
        calculated_opening_vault = get_opening_vault_cash(current_company, target_date_str)
        
        # পাশাপাশি মূল দুই কলাম (জমা ও খরচ)
        receive_side_col, payout_side_col = st.columns(2)
        
        # --- BAM COLUMN: CASH RECEIVE (জমা) ---
        with receive_side_col:
            st.markdown("<h4 style='background-color:#064e3b; padding:8px; border-radius:5px; text-align:center; color:#10b981;'>📥 CASH RECEIVE (জমা টেবিল)</h4>", unsafe_allow_html=True)
            
            # ইমেজ 3.jpg এর অনুরূপ ওপেনিং ব্লক লেআউট
            st.markdown("**📂 Opening Cash Structure**")
            box_r1, box_r2 = st.columns([2, 1])
            box_r1.info("🔑 Opening Vault Cash (অটোমেটিক)")
            op_vault_val = box_r2.number_input("Vault Amt", value=calculated_opening_vault, disabled=True, label_visibility="collapsed", key="op_vault_display_val")
            
            # ৪টি রো-এর ডেটা অ্যারে ডিক্লেয়ারেশন
            rcv_inputs = []
            
            st.markdown("<hr style='margin:5px 0px; border-color:#222;'>", unsafe_allow_html=True)
            st.markdown("**➕ নতুন নগদ জমা এন্ট্রি গ্রিড**")
            
            # হেডার গাইড
            h_rc1, h_rc2, h_rc3 = st.columns([3, 2, 3])
            h_rc1.markdown("<small><b>সেকেন্ড পার্টি নাম</b></small>", unsafe_allow_html=True)
            h_rc2.markdown("<small><b>Amount ৳</b></small>", unsafe_allow_html=True)
            h_rc3.markdown("<small><b>Remarks (বিবরণ)</b></small>", unsafe_allow_html=True)
            
            # ১০টি ডাইনামিক এন্ট্রি রো জেনারেশন
            for idx in range(10):
                r_c1, r_c2, r_c3 = st.columns([3, 2, 3])
                with r_c1:
                    p_name = st.selectbox(f"R_Party_{idx}", options=[""] + parties, key=f"rcv_party_{idx}", label_visibility="collapsed")
                with r_c2:
                    p_amt = st.number_input(f"R_Amt_{idx}", min_value=0.0, step=500.0, value=None, key=f"rcv_amt_{idx}", label_visibility="collapsed")
                with r_c3:
                    p_rem = st.text_input(f"R_Rem_{idx}", placeholder="বিবরণ...", key=f"rcv_rem_{idx}", label_visibility="collapsed")
                rcv_inputs.append((p_name, p_amt, p_rem))
                
            # সর্বমোট জমা সাইডের যোগফল হিসাব (ওপেনিং ভল্ট + গ্রিডের নতুন এন্ট্রি)
            grid_rcv_total = sum([item[1] for item in rcv_inputs if item[1] is not None])
            grand_total_receive = op_vault_val + grid_rcv_total
            st.markdown(f"<h5 style='text-align:right; color:#10b981;'>Total Receive Side: {grand_total_receive:,.1f} ৳</h5>", unsafe_allow_html=True)

        # --- DAN COLUMN: PAY OUT (খরচ/প্রদান) ---
        with payout_side_col:
            st.markdown("<h4 style='background-color:#7f1d1d; padding:8px; border-radius:5px; text-align:center; color:#f87171;'>📤 PAY OUT (খরচ টেবিল)</h4>", unsafe_allow_html=True)
            
            # ইমেজ 3.jpg এর অনুরূপ এডিটেবল ওপেনিং লেআউট
            st.markdown("**📂 Variable Ledger Status**")
            
            pay_box_lbl1, pay_box_val1 = st.columns([2, 1])
            pay_box_lbl1.markdown("<div style='padding-top:5px;'>🏦 DM & DSS Bank</div>", unsafe_allow_html=True)
            dm_dss_val = pay_box_val1.number_input("DM Bank", min_value=0.0, value=0.0, step=1000.0, label_visibility="collapsed", key="v_dm_dss")
            
            pay_box_lbl2, pay_box_val2 = st.columns([2, 1])
            pay_box_lbl2.markdown("<div style='padding-top:5px;'>🛒 Market Advance</div>", unsafe_allow_html=True)
            market_adv_val = pay_box_val2.number_input("Mkt Adv", min_value=0.0, value=0.0, step=1000.0, label_visibility="collapsed", key="v_mkt_adv")
            
            pay_box_lbl3, pay_box_val3 = st.columns([2, 1])
            pay_box_lbl3.markdown("<div style='padding-top:5px;'>⚠️ Others Due</div>", unsafe_allow_html=True)
            others_due_val = pay_box_val3.number_input("Oth Due", min_value=0.0, value=0.0, step=1000.0, label_visibility="collapsed", key="v_oth_due")
            
            # ৩টি ওপেনিং প্রদান উপাদানের যোগফল
            sub_total_payout_opening = dm_dss_val + market_adv_val + others_due_val
            
            st.markdown("<hr style='margin:5px 0px; border-color:#222;'>", unsafe_allow_html=True)
            st.markdown("**➖ নতুন নগদ পে-আউট এন্ট্রি গ্রিড**")
            
            # হেডার গাইড
            h_pc1, h_pc2, h_pc3 = st.columns([3, 2, 3])
            h_pc1.markdown("<small><b>সেকেন্ড পার্টি নাম</b></small>", unsafe_allow_html=True)
            h_pc2.markdown("<small><b>Amount ৳</b></small>", unsafe_allow_html=True)
            h_pc3.markdown("<small><b>Remarks (বিবরণ)</b></small>", unsafe_allow_html=True)
            
            pay_inputs = []
            # ১০টি ডাইনামিক পে-আউট এন্ট্রি রো জেনারেশন
            for idx in range(10):
                p_c1, p_c2, p_c3 = st.columns([3, 2, 3])
                with p_c1:
                    po_party = st.selectbox(f"P_Party_{idx}", options=[""] + parties, key=f"pay_party_{idx}", label_visibility="collapsed")
                with p_c2:
                    po_amt = st.number_input(f"P_Amt_{idx}", min_value=0.0, step=500.0, value=None, key=f"pay_amt_{idx}", label_visibility="collapsed")
                with p_c3:
                    po_rem = st.text_input(f"P_Rem_{idx}", placeholder="বিবরণ...", key=f"pay_rem_{idx}", label_visibility="collapsed")
                pay_inputs.append((po_party, po_amt, po_rem))
                
            # সর্বমোট পে-আউট সাইডের যোগফল হিসাব
            grid_pay_total = sum([item[1] for item in pay_inputs if item[1] is not None])
            grand_total_payout = sub_total_payout_opening + grid_pay_total
            st.markdown(f"<h5 style='text-align:right; color:#f87171;'>Total Payout Side: {grand_total_payout:,.1f} ৳</h5>", unsafe_allow_html=True)

        # ----------------------------------------------------------------------
        # অংশ ৩: ম্যাচিং ভ্যালিডেশন ও গ্লোবাল সেভ মেকানিজম
        # ----------------------------------------------------------------------
        st.markdown("---")
        
        # ডিসপ্লে ব্যালেন্সার প্যানেল
        bal_c1, bal_c2, bal_c3 = st.columns([3, 3, 4])
        bal_c1.metric("মোট রিসিভ সাইড (Total Receive)", f"{grand_total_receive:,.1f} ৳")
        bal_c2.metric("মোট পে-আউট সাইড (Total PayOut)", f"{grand_total_payout:,.1f} ৳")
        
        mismatch_delta = abs(grand_total_receive - grand_total_payout)
        
        if round(grand_total_receive, 2) == round(grand_total_payout, 2):
            bal_c3.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
            bal_c3.success("⚖️ হিসাবের উভয় পাস সম্পূর্ণ মিলে গেছে! ডেটা সেভ করার জন্য প্রস্তুত।")
            
            # মাস্টার সেভ বাটন
            if st.button("💾 সমীকরণ চূড়ান্ত করুন এবং ক্যাশ খাতা সেভ করুন", type="primary", use_container_width=True, key="master_cash_save_btn"):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                try:
                    pushed_records = 0
                    
                    # ক) ম্যানুয়াল ওপেনিং হেডার ৩টি আইটেম
                    if dm_dss_val > 0:
                        cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Bank', 'Cash Out', ?, '[Opening Header] DM & DSS Bank Entry')", (target_date_str, current_company, dm_dss_val))
                    if market_adv_val > 0:
                        cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Others', 'Cash Out', ?, '[Opening Header] Market Advance Entry')", (target_date_str, current_company, market_adv_val))
                    if others_due_val > 0:
                        cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Others', 'Cash Out', ?, '[Opening Header] Others Due Entry')", (target_date_str, current_company, others_due_val))
                    
                    # খ) রিসিভ গ্রিড থেকে ডাটাবেজে এন্ট্রি
                    for r_party, r_amt, r_rem in rcv_inputs:
                        if r_party != "" and r_amt is not None and r_amt > 0:
                            cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash In', ?, ?)",
                                           (target_date_str, current_company, r_party, r_amt, r_rem.strip()))
                            pushed_records += 1
                            
                    # গ) পে-আউট গ্রিড থেকে ডাটাবেজে এন্ট্রি
                    for p_party, p_amt, p_rem in pay_inputs:
                        if p_party != "" and p_amt is not None and p_amt > 0:
                            cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash Out', ?, ?)",
                                           (target_date_str, current_company, p_party, p_amt, p_rem.strip()))
                            pushed_records += 1
                            
                    conn.commit()
                    st.balloons()
                    st.success(f"🎉 চমৎকার! সমীকরণ মিলেছে এবং খাতার সর্বমোট {pushed_records + 3}টি রেকর্ড সফলভাবে ডাটাবেজে লক করা হয়েছে।")
                    import time; time.sleep(0.8); st.rerun()
                except Exception as ex:
                    st.error(f"ডাটাবেজ সেভ ট্রানজেকশন এরর: {ex}")
                finally:
                    conn.close()
        else:
            bal_c3.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
            bal_c3.error(f"❌ হিসাব মেলেনি! দুই সাইডের মাঝে **{mismatch_delta:,.1f} ৳** এর ব্যবধান রয়েছে। ডেটা সেভ লক করা হয়েছে।")
            st.button("💾 সমীকরণ চূড়ান্ত করুন এবং ক্যাশ খাতা সেভ করুন", type="primary", use_container_width=True, disabled=True, key="master_cash_save_disabled")

    with tab2:
        st.markdown("##### 📖 ক্যাশ খাতার সাধারণ জাবেদা ও রিয়েল-টাইম খতিয়ান বিবরণী")
        conn = sqlite3.connect(DB_NAME)
        ledger_df = pd.read_sql_query("""
            SELECT date as 'তারিখ', second_party as 'খাত/সেকেন্ড পার্টি', type as 'লেনদেনের ধরণ', amount as 'টাকার পরিমাণ (৳)', remarks as 'বিবরণ'
            FROM cash_transactions WHERE company=? ORDER BY date DESC, id DESC
        """, conn, params=(current_company,))
        conn.close()
        
        if not ledger_df.empty:
            total_inflow = ledger_df[ledger_df['লেনদেনের ধরণ'] == 'Cash In']['টাকার পরিমাণ (৳)'].sum()
            total_outflow = ledger_df[ledger_df['লেনদেনের ধরণ'] == 'Cash Out']['টাকার পরিমাণ (৳)'].sum()
            
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("সর্বমোট নগদ ইন (Total Inflow)", f"{total_inflow:,.1f} ৳")
            c_m2.metric("সর্বমোট নগদ আউট (Total Outflow)", f"{total_outflow:,.1f} ৳")
            c_m3.metric("নিট ক্যাশ অন হ্যান্ড (Current Vault Cash)", f"{total_inflow - total_outflow:,.1f} ৳", delta=f"{total_inflow - total_outflow:,.1f} ৳ Reserves")
            
            st.dataframe(ledger_df, use_container_width=True, hide_index=True)
        else:
            st.info("ক্যাশ খাতায় এখনো কোনো লেনদেনের রেকর্ড এন্ট্রি করা হয়নি।")

# ==============================================================================
# লজিক: Expense Management মডিউল (STRICT ARCHITECTURE)
# ==============================================================================
elif current_action == "Expense Management":
    st.markdown(f"### 📉 Expense Management Module ({current_company})")
    st.markdown("💡 এই মডিউলের সমস্ত খরচ স্বয়ংক্রিয়ভাবে ক্যাশ খাতার **'Petty_Cash'** অ্যাকাউন্ট থেকে মাইনাস (Cash Out) হবে।")

    exp_tab1, exp_tab2 = st.tabs(["📥 খরচ এন্ট্রি ও এক্সেল আপলোড", "📖 খরচের খতিয়ান ও রিপোর্ট"])

    with exp_tab1:
        # ----------------------------------------------------------------------
        # আর্কিটেকচার রুল ৪: কনফিগারেশন বার একই সমান্তরাল লাইনে স্থাপন (Single Parallel Line)
        # ----------------------------------------------------------------------
        st.markdown("##### ⚙️ কনফিগারেশন এবং এক্সেল বাল্ক আপলোড")
        top_c1, top_c2, top_c3, top_c4 = st.columns([2, 1.5, 3.5, 3])
        
        with top_c1:
            exp_date = st.date_input("📆 খরচের তারিখ (Date):", datetime.now().date(), key="expense_master_date")
        with top_c2:
            num_rows = st.number_input("সারির সংখ্যা (Rows):", min_value=1, max_value=25, value=10, step=1, key="expense_num_rows")
        with top_c3:
            uploaded_exp_file = st.file_uploader("📤 এক্সেল ফাইল ড্রপ করুন (Bulk Import)", type=["xlsx"], key="excel_expense_uploader")
        with top_c4:
            st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            exp_buffer = io.BytesIO()
            exp_template_df = pd.DataFrame(columns=["date", "expense_type", "expense_category", "amount", "remarks"])
            exp_template_df.loc[0] = [str(datetime.now().date()), "ROI_Expences", "Electricity_Bill", 1500.0, "Office Bill"]
            exp_template_df.loc[1] = [str(datetime.now().date()), "Expences", "Entertainment", 350.0, "Guest Tea & Snacks"]
            with pd.ExcelWriter(exp_buffer, engine='openpyxl') as writer:
                exp_template_df.to_excel(writer, index=False, sheet_name='Expense_Template')
            st.download_button("📥 ডাউনলোড টেমপ্লেট", data=exp_buffer.getvalue(), file_name=f"{current_company}_expense_template.xlsx", use_container_width=True)

        if uploaded_exp_file is not None:
            st.markdown("---")
            try:
                upload_df = pd.read_excel(uploaded_exp_file)
                st.markdown("👀 **আপলোড করা ভাগের প্রিভিউ (প্রথম ৫টি রো):**")
                st.dataframe(upload_df.head(5), use_container_width=True, hide_index=True)
                if st.button("💾 ডাটাবেজে এক্সেল খরচ পুশ করুন", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor(); count = 0
                    for _, row in upload_df.iterrows():
                        r_date = str(row.get('date', datetime.now().date())).split(" ")[0]
                        r_type = str(row.get('expense_type', '')).strip()
                        r_cat = str(row.get('expense_category', '')).strip()
                        r_amt = float(row['amount']) if pd.notnull(row['amount']) else 0.0
                        r_rem = str(row.get('remarks', '')).strip() if pd.notnull(row.get('remarks', '')) else ""
                        
                        if r_type not in ['nan', 'None', ''] and r_cat not in ['nan', 'None', ''] and r_amt > 0:
                            formatted_remarks = f"[{r_type} -> {r_cat}] {r_rem}".strip()
                            cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)", 
                                           (r_date, current_company, r_amt, formatted_remarks))
                            count += 1
                    conn.commit(); conn.close()
                    if count > 0: st.success(f"✅ সফলভাবে মোট {count}টি খরচ এক্সেল থেকে ইমপোর্ট করা হয়েছে!"); import time; time.sleep(0.5); st.rerun()
                    else: st.error("❌ এক্সেলে কোনো বৈধ ডেটা পাওয়া যায়নি!")
            except Exception as e: st.error(f"এক্সেল প্রসেস করতে সমস্যা হয়েছে: {e}")

        st.markdown("---")
        st.markdown("##### 📝 ম্যানুয়াল মাল্টি-রো এন্ট্রি")
        
        # ডাইনামিক ক্যাটাগরি ম্যাপিং
        categories_map = {
            "": [""],
            "ROI_Expences": ["", "Electricity_Bill", "Entertainment", "House_Rent", "Internet", "Bike_Maintain", "Repair", "Route_Cost", "Stationary", "Water_Bill", "Printing", "Financial_Expence", "Mobil_Change", "Salary", "bKash_Purpose", "Campaign", "Others"],
            "Expences": ["", "Entertainment", "Repair", "T.A", "Printing", "Campaign", "Cash_Pay", "Others"],
            "Merchant": ["", "Entertainment", "Repair", "T.A", "Printing", "Campaign", "Cash_Pay", "Stationary", "Others"]
        }
        
        # ----------------------------------------------------------------------
        # আর্কিটেকচার রুল ৪: FULL WIDTH-এ ৪টি নিখুঁত কলাম (Type, Category, Amount, Remarks)
        # ----------------------------------------------------------------------
        h1, h2, h3, h4 = st.columns([3, 3, 2, 4])
        h1.markdown("**Expense Type**")
        h2.markdown("**খাত (Expense Category)**")
        h3.markdown("**পরিমাণ (Amount ৳)**")
        h4.markdown("**বিবরণ (Remarks)**")
        
        expense_rows_data = []
        for i in range(int(num_rows)):
            c1, c2, c3, c4 = st.columns([3, 3, 2, 4])
            with c1: 
                # আর্কিটেকচার রুল ৪: সম্পূর্ণ ব্ল্যাঙ্ক স্টেট থেকে ড্রপডাউন শুরু করা
                exp_type = st.selectbox(f"Type_{i}", ["", "ROI_Expences", "Expences", "Merchant"], index=0, key=f"exp_type_{i}", label_visibility="collapsed")
            with c2: 
                # ডাইনামিক ফিল্টারিং ম্যাপিং
                exp_cat = st.selectbox(f"Cat_{i}", categories_map.get(exp_type, [""]), index=0, key=f"exp_cat_{i}", label_visibility="collapsed")
            with c3: 
                # আর্কিটেকচার রুল ৪: ভ্যালু ডিফল্ট None সেট করা থাকবে
                amt = st.number_input(f"Amt_{i}", min_value=0.0, step=50.0, value=None, key=f"exp_amt_{i}", label_visibility="collapsed")
            with c4: 
                rem = st.text_input(f"Rem_{i}", value="", key=f"exp_rem_{i}", label_visibility="collapsed", placeholder="বিস্তারিত বিবরণ লিখুন...")
                
            expense_rows_data.append((exp_type, exp_cat, amt, rem))
            
        st.markdown("---")
        if st.button("💾 সকল ম্যানুয়াল খরচ একসাথে সাবমিট করুন", type="primary", use_container_width=True):
            valid_entries = 0; conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
            for etype, ecat, eamt, erem in expense_rows_data:
                if etype != "" and ecat != "" and eamt is not None and eamt > 0:
                    formatted_remarks = f"[{etype} -> {ecat}] {erem}".strip()
                    # আর্কিটেকচার রুল ৪: খরচসমূহ স্বয়ংক্রিয়ভাবে second_party='Petty_Cash' এবং type='Cash Out' হিসেবে পুশ হবে
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)", 
                                   (str(exp_date), current_company, eamt, formatted_remarks))
                    valid_entries += 1
            conn.commit(); conn.close()
            if valid_entries > 0: st.toast(f"🎉 মোট {valid_entries}টি খরচ সংরক্ষিত হয়েছে!"); import time; time.sleep(0.5); st.rerun()
            else: st.error("❌ কমপক্ষে একটি সারিতে সঠিক ইনপুট দিন।")

    with exp_tab2:
        st.markdown("##### 📊 আপনার কোম্পানির খরচ সমүүহের তালিকা (Petty Cash Ledger)")
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
