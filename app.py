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

# CSS দিয়ে ৩ নং ছবির মতো টেবিল বা বর্ডার গ্রিড স্টাইল নিশ্চিত করা
st.markdown("""
<style>
    div[data-testid="column"] {
        padding: 10px;
    }
    .block-container {
        padding-top: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

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
# ৪. গ্লোবাল সেশন স্টেট এবং হেল্পার ফাংশน
# ==============================================================================
for state_key, default_val in [('current_company', 'None'), ('current_action', None), ('active_emp_id', None), ('dialog_edit_mode', False), ('active_party_id', None), ('party_edit_mode', False)]:
    if state_key not in st.session_state:
        st.session_state[state_key] = default_val

def open_edit_mode(): st.session_state.dialog_edit_mode = True
def close_edit_mode(): st.session_state.dialog_edit_mode = False

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
        st.session_state.active_emp_id = None; return
        
    (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary,
     father_name, father_nid, mother_name, emp_nid, guarantor_name, guarantor_nid, guarantor_mobile) = emp
    
    col_t1, col_t2 = st.columns([6, 2])
    with col_t1:
        if not st.session_state.dialog_edit_mode: st.button("✏️ Edit Profile", type="secondary", key="popup_edit_btn", on_click=open_edit_mode)
        else: st.button("⬅️ Back to View Mode", type="secondary", key="popup_back_btn", on_click=close_edit_mode)
    with col_t2:
        if st.button("❌ Close Window", use_container_width=True, key="popup_close_btn"):
            st.session_state.active_emp_id = None; st.session_state.dialog_edit_mode = False; st.rerun()
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
                new_g_name = st.text_input("Guarantor Name", value=g_name)
                new_g_nid = st.text_input("Guarantor NID Number", value=g_nid)
                new_g_mob = st.text_input("Guarantor Mobile", value=g_mob)
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
                    st.toast("কর্মীর তথ্য সফলভাবে আপডেট করা হয়েছে!", icon="✅")
                    st.session_state.active_emp_id = None; st.session_state.dialog_edit_mode = False
                    import time; time.sleep(0.5); st.rerun()

# ==============================================================================
# 💈 সাইডবার ন্যাভিগেশন মেনু (নতুন সাব-মেনু আর্কিটেকচার সম্বলিত)
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
            st.sidebar.radio("bKash Emp Options", options=menu_options_emp, index=bk_default, key="bk_emp_radio", on_change=bk_emp_cb, label_visibility="collapsed")
        
        with st.expander("📊 Account Management (bKash)", expanded=True):
            st.markdown("<b style='color:#10b981; font-size:12px;'>💵 Cash Management</b>", unsafe_allow_html=True)
            if st.button("📝 Cash Khata Maintenance", key="bk_ck_m_btn", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Cash Khata Maintenance"; st.rerun()
            if st.button("📊 Report View", key="bk_rv_btn", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Report View"; st.rerun()
            
            st.markdown("<hr style='margin:4px 0px; border-color:#333;'>", unsafe_allow_html=True)
            if st.button("📉 Expense Management", key="bk_exp_btn", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Expense Management"; st.rerun()
            
            with st.expander("👥 Second Party Details", expanded=False):
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
            st.sidebar.radio("GP Emp Options", options=menu_options_emp, index=gp_default, key="gp_emp_radio", on_change=gp_emp_cb, label_visibility="collapsed")
        
        with st.expander("📊 Account Management (GP)", expanded=True):
            st.markdown("<b style='color:#10b981; font-size:12px;'>💵 Cash Management</b>", unsafe_allow_html=True)
            if st.button("📝 Cash Khata Maintenance ", key="gp_ck_m_btn", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Cash Khata Maintenance"; st.rerun()
            if st.button("📊 Report View ", key="gp_rv_btn", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Report View"; st.rerun()
            
            st.markdown("<hr style='margin:4px 0px; border-color:#333;'>", unsafe_allow_html=True)
            if st.button("📉 Expense Management ", key="gp_exp_btn", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Expense Management"; st.rerun()
            
            with st.expander("👥 Second Party Details ", expanded=False):
                if st.button("➕ Add New Second Party ", key="gp_add_sp_btn", use_container_width=True):
                    st.session_state.current_company = "GP"; st.session_state.current_action = "Add New Second Party"; st.rerun()
                if st.button("📋 View All Second Parties ", key="gp_view_sp_btn", use_container_width=True):
                    st.session_state.current_company = "GP"; st.session_state.current_action = "View All Second Parties"; st.rerun()
        
        with st.expander("📁 Others ", expanded=False):
            if st.button("📁 Others Account ", key="gp_oth_btn", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Others"; st.rerun()

current_action = st.session_state.get('current_action', None)
current_company = st.session_state.get('current_company', None)

# ==============================================================================
# 🚀 মেইন রাউটার লজিক
# ==============================================================================
render_header()

if current_action is None:
    st.markdown("<h3 style='text-align: center; color: #10b981;'>ড্যাশবোর্ডে আপনাকে স্বাগতম!</h3>", unsafe_allow_html=True)
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
                st.session_state.active_emp_id = row['ID']; st.rerun()

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

# ==============================================================================
# Option 1: 📝 Cash Khata Maintenance (৩ নং ছবির হুবহু ডাবল-টেবিল গ্রিড লেআউট)
# ==============================================================================
elif current_action == "Cash Khata Maintenance":
    st.markdown(f"### 📝 Cash Khata Maintenance ({current_company})")
    
    conn = sqlite3.connect(DB_NAME)
    parties = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=? AND status='Active'", (current_company,)).fetchall()]
    conn.close()

    # ১. Excel Bulk Upload অপশন
    with st.expander("📤 Excel ফাইল ড্রপ করে একসাথে সব ডেটা ইনপুট করুন (Bulk Upload)", expanded=False):
        up_col1, up_col2 = st.columns([3, 1])
        with up_col1:
            uploaded_cash_excel = st.file_uploader("ক্যাশ খাতার এক্সেল ফাইলটি এখানে ড্রপ করুন:", type=["xlsx"])
        with up_col2:
            st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            cash_template_buffer = io.BytesIO()
            cash_temp_df = pd.DataFrame(columns=["date", "second_party", "type", "amount", "remarks"])
            cash_temp_df.loc[0] = [str(datetime.now().date()), "Mother_Wallet", "Cash In", 50000.0, "Bank Transfer In"]
            cash_temp_df.loc[1] = [str(datetime.now().date()), "Hand_Cash", "Cash Out", 12000.0, "Daily Market Payout"]
            with pd.ExcelWriter(cash_template_buffer, engine='openpyxl') as writer:
                cash_temp_df.to_excel(writer, index=False, sheet_name='Template')
            st.download_button("📥 ডাউনলোড টেমপ্লেট", data=cash_template_buffer.getvalue(), file_name=f"{current_company}_cash_template.xlsx", use_container_width=True)

        if uploaded_cash_excel is not None:
            try:
                xl_df = pd.read_excel(uploaded_cash_excel)
                st.dataframe(xl_df.head(5), use_container_width=True, hide_index=True)
                if st.button("💾 এক্সেল ডাটা সেভ করুন"):
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    success_count = 0
                    for _, row in xl_df.iterrows():
                        c_date = str(row.get('date', datetime.now().date())).split(" ")[0]
                        c_party = str(row.get('second_party', '')).strip()
                        c_type = str(row.get('type', '')).strip()
                        c_amount = float(row['amount']) if pd.notnull(row['amount']) else 0.0
                        c_remarks = str(row.get('remarks', '')).strip() if pd.notnull(row.get('remarks', '')) else ""
                        if c_party and c_type in ["Cash In", "Cash Out"] and c_amount > 0:
                            cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, ?, ?, ?)", (c_date, current_company, c_party, c_type, c_amount, c_remarks))
                            success_count += 1
                    conn.commit(); conn.close()
                    st.success(f"✅ এক্সেল থেকে সফলভাবে {success_count}টি লেনদেন সেভ করা হয়েছে!"); import time; time.sleep(0.5); st.rerun()
            except Exception as e: st.error(f"এক্সেল প্রসেসিং এরর: {e}")

    # ২. ৩ নং ছবির হুবহু ডাবল-টেবিল গ্রিড লেআউট (Side-by-Side Tables)
    st.markdown("#### ⚖️ ডেইলি ক্যাশ খাতা গ্রিড এন্ট্রি")
    tx_master_date = st.date_input("📆 তারিখ (Date Selection):", datetime.now().date())
    target_date_str = str(tx_master_date)
    calculated_opening_vault = get_opening_vault_cash(current_company, target_date_str)

    # মূল দুই কলামের ডিজাইন ছক
    receive_side_col, payout_side_col = st.columns(2)
    
    # 📥 Cash Receive (জমা) টেবিল (বামে)
    with receive_side_col:
        st.markdown("<h4 style='background-color:#064e3b; padding:10px; border-radius:5px; text-align:center; color:#10b981; margin-bottom:0px; border: 1px solid #10b981;'>📥 CASH RECEIVE (জমা)</h4>", unsafe_allow_html=True)
        
        # ওপেনিং ক্যাশ ঘর
        st.markdown("<div style='background-color:#141414; padding:10px; border:1px solid #333;'><b>📂 Opening Cash:</b></div>", unsafe_allow_html=True)
        op_box_c1, op_box_c2 = st.columns([3, 2])
        op_box_c1.markdown("<p style='margin-top:8px;'>Opening Vault Cash (অটোমেটিক)</p>", unsafe_allow_html=True)
        op_vault_val = op_box_c2.number_input("Vault Amt", value=calculated_opening_vault, disabled=True, label_visibility="collapsed", key="v_op_vault")
        
        st.markdown("<div style='background-color:#141414; padding:5px; border:1px solid #333;'><b>➕ নগদ জমার এন্ট্রি ছক:</b></div>", unsafe_allow_html=True)
        
        # টেবিল হেডার রো
        th_c1, th_c2, th_c3 = st.columns([3, 2, 3])
        th_c1.markdown("<b style='font-size:13px;'>সেকেন্ড পার্টি নাম (Dropdown)</b>", unsafe_allow_html=True)
        th_c2.markdown("<b style='font-size:13px;'>Amount ৳</b>", unsafe_allow_html=True)
        th_c3.markdown("<b style='font-size:13px;'>Remarks (মন্তব্য)</b>", unsafe_allow_html=True)
        
        rcv_inputs = []
        for idx in range(10):
            r_c1, r_c2, r_c3 = st.columns([3, 2, 3])
            with r_c1: rp = st.selectbox(f"R_Party_{idx}", options=[""] + parties, key=f"r_p_{idx}", label_visibility="collapsed")
            with r_c2: ra = st.number_input(f"R_Amt_{idx}", min_value=0.0, step=500.0, value=None, key=f"r_a_{idx}", label_visibility="collapsed")
            with r_c3: rr = st.text_input(f"R_Rem_{idx}", placeholder="-", key=f"r_r_{idx}", label_visibility="collapsed")
            rcv_inputs.append((rp, ra, rr))
            
        grid_rcv_total = sum([item[1] for item in rcv_inputs if item[1] is not None])
        grand_total_receive = op_vault_val + grid_rcv_total
        st.markdown(f"<h4 style='text-align:right; color:#10b981; margin-top:10px;'>Total Receive Side: {grand_total_receive:,.1f} ৳</h4>", unsafe_allow_html=True)

    # 📤 Pay Out (খরচ) টেবিল (ডানে)
    with payout_side_col:
        st.markdown("<h4 style='background-color:#7f1d1d; padding:10px; border-radius:5px; text-align:center; color:#f87171; margin-bottom:0px; border: 1px solid #7f1d1d;'>📤 PAY OUT (খরচ/প্রদান)</h4>", unsafe_allow_html=True)
        
        st.markdown("<div style='background-color:#141414; padding:10px; border:1px solid #333;'><b>📂 Variable Ledger Manual Input:</b></div>", unsafe_allow_html=True)
        
        # ৩ নং ছবির ম্যানুয়াল ৩টি ফিল্ড
        p_lbl1, p_val1 = st.columns([3, 2])
        p_lbl1.markdown("<p style='margin-top:8px;'>🏦 DM & DSS Bank</p>", unsafe_allow_html=True)
        dm_dss_val = p_val1.number_input("DM Bank", min_value=0.0, value=0.0, step=1000.0, label_visibility="collapsed", key="v_dm")
        
        p_lbl2, p_val2 = st.columns([3, 2])
        p_lbl2.markdown("<p style='margin-top:8px;'>🛒 Market Advance</p>", unsafe_allow_html=True)
        market_adv_val = p_val2.number_input("Mkt Adv", min_value=0.0, value=0.0, step=1000.0, label_visibility="collapsed", key="v_ma")
        
        p_lbl3, p_val3 = st.columns([3, 2])
        p_lbl3.markdown("<p style='margin-top:8px;'>⚠️ Others Due</p>", unsafe_allow_html=True)
        others_due_val = p_val3.number_input("Oth Due", min_value=0.0, value=0.0, step=1000.0, label_visibility="collapsed", key="v_od")
        
        sub_total_payout_opening = dm_dss_val + market_adv_val + others_due_val
        
        st.markdown("<div style='background-color:#141414; padding:5px; border:1px solid #333;'><b>➖ নগদ খরচের এন্ট্রি ছক:</b></div>", unsafe_allow_html=True)
        
        # টেবিল হেডার রো
        ph_c1, ph_c2, ph_c3 = st.columns([3, 2, 3])
        ph_c1.markdown("<b style='font-size:13px;'>সেকেন্ড পার্টি নাম (Dropdown)</b>", unsafe_allow_html=True)
        ph_c2.markdown("<b style='font-size:13px;'>Amount ৳</b>", unsafe_allow_html=True)
        ph_c3.markdown("<b style='font-size:13px;'>Remarks (মন্তব্য)</b>", unsafe_allow_html=True)
        
        pay_inputs = []
        for idx in range(10):
            p_c1, p_c2, p_c3 = st.columns([3, 2, 3])
            with p_c1: pp = st.selectbox(f"P_Party_{idx}", options=[""] + parties, key=f"p_p_{idx}", label_visibility="collapsed")
            with p_c2: pa = st.number_input(f"P_Amt_{idx}", min_value=0.0, step=500.0, value=None, key=f"p_a_{idx}", label_visibility="collapsed")
            with p_c3: pr = st.text_input(f"P_Rem_{idx}", placeholder="-", key=f"p_r_{idx}", label_visibility="collapsed")
            pay_inputs.append((pp, pa, pr))
            
        grid_pay_total = sum([item[1] for item in pay_inputs if item[1] is not None])
        grand_total_payout = sub_total_payout_opening + grid_pay_total
        st.markdown(f"<h4 style='text-align:right; color:#f87171; margin-top:10px;'>Total Payout Side: {grand_total_payout:,.1f} ৳</h4>", unsafe_allow_html=True)

    st.markdown("---")
    
    # ব্যালেন্স চেকিং এবং কঠোর সেভ লজিক
    mismatch_delta = abs(grand_total_receive - grand_total_payout)
    if round(grand_total_receive, 2) == round(grand_total_payout, 2):
        st.success("⚖️ দুই পাশের হিসাব মিলে গেছে! আপনি এখন ডাটাবেজে সাবমিট করতে পারেন।")
        if st.button("💾 সমীকরণ নিশ্চিত করুন এবং ক্যাশ খাতা সেভ করুন", type="primary", use_container_width=True):
            conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
            try:
                if dm_dss_val > 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Bank', 'Cash Out', ?, '[Opening Header] DM & DSS Bank Entry')", (target_date_str, current_company, dm_dss_val))
                if market_adv_val > 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Others', 'Cash Out', ?, '[Opening Header] Market Advance Entry')", (target_date_str, current_company, market_adv_val))
                if others_due_val > 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Others', 'Cash Out', ?, '[Opening Header] Others Due Entry')", (target_date_str, current_company, others_due_val))
                
                for rp, ra, rr in rcv_inputs:
                    if rp and ra and ra > 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash In', ?, ?)", (target_date_str, current_company, rp, ra, rr.strip()))
                for pp, pa, pr in pay_inputs:
                    if pp and pa and pa > 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash Out', ?, ?)", (target_date_str, current_company, pp, pa, pr.strip()))
                conn.commit(); st.balloons(); st.success("🎉 চমৎকার! খাতার আজকের দিনের হিসাব সফলভাবে লক করা হয়েছে।")
                import time; time.sleep(0.5); st.rerun()
            except Exception as ex: st.error(f"Error: {ex}")
            finally: conn.close()
    else:
        st.error(f"❌ হিসাব মেলেনি! দুই সাইডের মাঝে {mismatch_delta:,.1f} ৳ অমিল রয়েছে। সমীকরণ না মিললে ডেটা সেভ করা যাবে না।")
        st.button("💾 সমীকরণ নিশ্চিত করুন এবং ক্যাশ খাতা সেভ করুন", type="primary", use_container_width=True, disabled=True)

# ==============================================================================
# Option 2: 📊 Report View (ডেইলি, মাসিক এবং সেকেন্ড পার্টি-ভিত্তিক অ্যাডভান্সড রিপোর্ট)
# ==============================================================================
elif current_action == "Report View":
    st.markdown(f"### 📊 Report View ({current_company})")
    
    rep_tab1, rep_tab2, rep_tab3 = st.tabs(["📆 Daily Report", "📅 Monthly Report", "👥 Second Party-wise Report"])
    
    conn = sqlite3.connect(DB_NAME)
    
    # ১. Daily Report
    with rep_tab1:
        st.markdown("##### 📆 দৈনিক লেনদেন রিপোর্ট")
        rep_date = st.date_input("তারিখ নির্বাচন করুন:", datetime.now().date(), key="rep_daily_date")
        daily_df = pd.read_sql_query("""
            SELECT date as 'তারিখ', second_party as 'সেকেন্ড পার্টি', type as 'ধরণ', amount as 'টাকার পরিমাণ (৳)', remarks as 'বিবরণ'
            FROM cash_transactions WHERE company=? AND date=? ORDER BY id DESC
        """, conn, params=(current_company, str(rep_date)))
        if daily_df.empty: st.info("এই তারিখে কোনো লেনদেনের রেকর্ড পাওয়া যায়নি।")
        else:
            t_in = daily_df[daily_df['ধরণ'] == 'Cash In']['টাকার পরিমাণ (৳)'].sum()
            t_out = daily_df[daily_df['ধরণ'] == 'Cash Out']['টাকার পরিমাণ (৳)'].sum()
            rc1, rc2, rc3 = st.columns(3)
            rc1.metric("মোট জমা (Cash In)", f"{t_in:,.1f} ৳")
            rc2.metric("মোট খরচ (Cash Out)", f"{t_out:,.1f} ৳")
            rc3.metric("ব্যালেন্স", f"{t_in - t_out:,.1f} ৳")
            st.dataframe(daily_df, use_container_width=True, hide_index=True)

    # ২. Monthly Report
    with rep_tab2:
        st.markdown("##### 📅 মাসিক পুঞ্জীভূত রিপোর্ট")
        months_list = [f"{i:02d}" for i in range(1, 13)]
        selected_month = st.selectbox("মাস সিলেক্ট করুন:", months_list, index=int(datetime.now().strftime("%m"))-1)
        selected_year = st.selectbox("বছর সিলেক্ট করুন:", ["2025", "2026", "2027"], index=1)
        
        month_str = f"{selected_year}-{selected_month}-%"
        monthly_df = pd.read_sql_query("""
            SELECT date as 'তারিখ', second_party as 'সেকেন্ড পার্টি', type as 'ধরণ', amount as 'টাকার পরিমাণ (৳)', remarks as 'বিবরণ'
            FROM cash_transactions WHERE company=? AND date LIKE ? ORDER BY date ASC, id DESC
        """, conn, params=(current_company, month_str))
        if monthly_df.empty: st.info("এই মাসে কোনো লেনদেনের রেকর্ড পাওয়া যায়নি।")
        else:
            tm_in = monthly_df[monthly_df['ধরণ'] == 'Cash In']['টাকার পরিমাণ (৳)'].sum()
            tm_out = monthly_df[monthly_df['ধরণ'] == 'Cash Out']['টাকার পরিমাণ (৳)'].sum()
            rm1, rm2, rm3 = st.columns(3)
            rm1.metric("এই মাসের মোট ইন", f"{tm_in:,.1f} ৳")
            rm2.metric("এই মাসের মোট আউট", f"{tm_out:,.1f} ৳")
            rm3.metric("মাসিক নেট সঞ্চয়", f"{tm_in - tm_out:,.1f} ৳")
            st.dataframe(monthly_df, use_container_width=True, hide_index=True)

    # ৩. Second Party-wise Report
    with rep_tab3:
        st.markdown("##### 👥 সেকেন্ড পার্টি-ভিত্তিক নির্দিষ্ট খতিয়ান")
        active_parties = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=?", (current_company,)).fetchall()]
        selected_party = st.selectbox("সেকেন্ড পার্টি ফিল্টার করুন:", active_parties)
        
        party_df = pd.read_sql_query("""
            SELECT date as 'তারিখ', type as 'ধরণ', amount as 'টাকার পরিমাণ (৳)', remarks as 'বিবরণ'
            FROM cash_transactions WHERE company=? AND second_party=? ORDER BY date ASC, id DESC
        """, conn, params=(current_company, selected_party))
        if party_df.empty: st.info(f"'{selected_party}' এর কোনো ট্রানজেকশন হিস্ট্রি পাওয়া যায়নি।")
        else:
            tp_in = party_df[party_df['ধরণ'] == 'Cash In']['টাকার পরিমাণ (৳)'].sum()
            tp_out = party_df[party_df['ধরণ'] == 'Cash Out']['টাকার পরিমাণ (৳)'].sum()
            rp1, rp2, rp3 = st.columns(3)
            rp1.metric("মোট গৃহীত ক্যাশ (In)", f"{tp_in:,.1f} ৳")
            rp2.metric("মোট প্রদত্ত ক্যাশ (Out)", f"{tp_out:,.1f} ৳")
            rp3.metric("ব্যালেন্স লিজেন্ড", f"{tp_in - tp_out:,.1f} ৳")
            st.dataframe(party_df, use_container_width=True, hide_index=True)
            
    conn.close()

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
        with top_c1: exp_date = st.date_input("📆 খরচের তারিখ (Date):", datetime.now().date(), key="expense_master_date")
        with top_c2: num_rows = st.number_input("সারির সংখ্যা (Rows):", min_value=1, max_value=25, value=10, step=1, key="expense_num_rows")
        with top_c3: uploaded_exp_file = st.file_uploader("📤 এক্সেল ফাইল ড্রপ করুন (Bulk Import)", type=["xlsx"], key="excel_expense_uploader")
        with top_c4:
            st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            exp_buffer = io.BytesIO()
            exp_template_df = pd.DataFrame(columns=["date", "expense_type", "expense_category", "sub_category", "amount", "remarks"])
            exp_template_df.loc[0] = [str(datetime.now().date()), "ROI_Expences", "Electricity_Bill", "Electricity_Bill", 1500.0, "Sample Office Bill"]
            with pd.ExcelWriter(exp_buffer, engine='openpyxl') as writer: exp_template_df.to_excel(writer, index=False, sheet_name='Template')
            st.download_button("📥 ডাউনলোড টেমপ্লেট ", data=exp_buffer.getvalue(), file_name=f"{current_company}_expense_template.xlsx", use_container_width=True)

        if uploaded_exp_file is not None:
            try:
                upload_df = pd.read_excel(uploaded_exp_file)
                if st.button("💾 ডাটাবেজে এক্সেল খরচ পুশ করুন"):
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor(); count = 0
                    for _, row in upload_df.iterrows():
                        r_date = str(row.get('date', datetime.now().date())).split(" ")[0]
                        r_type = str(row.get('expense_type', '')).strip()
                        r_cat = str(row.get('expense_category', '')).strip()
                        r_subcat = str(row.get('sub_category', r_cat)).strip() 
                        r_amt = float(row['amount']) if pd.notnull(row['amount']) else 0.0
                        r_rem = str(row.get('remarks', '')) if pd.notnull(row.get('remarks', '')) else ""
                        if r_type and r_cat and r_amt > 0:
                            cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)", (r_date, current_company, r_amt, f"[{r_type} -> {r_cat}] {r_rem}"))
                            count += 1
                    conn.commit(); conn.close(); st.success(f"✅ সফলভাবে মোট {count}টি খরচ ইমপোর্ট করা হয়েছে!"); import time; time.sleep(0.5); st.rerun()
            except Exception as e: st.error(f"এরর: {e}")

        st.markdown("---")
        st.markdown("##### 📝 ম্যানুয়াল মাল্টি-row এন্ট্রি")
        categories_map = {
            "": [""],
            "ROI_Expences": ["", "Electricity_Bill", "Entertainment", "House_Rent", "Internet", "Bike_Maintain", "Repair", "Route_Cost", "Stationary", "Water_Bill", "Printing", "Financial_Expence", "Mobil_Change", "Salary", "bKash_Purpose", "Campaign", "Others"],
            "Expences": ["", "Entertainment", "Repair", "T.A", "Printing", "Campaign", "Cash_Pay", "Others"],
            "Merchant": ["", "Entertainment", "Repair", "T.A", "Printing", "Campaign", "Cash_Pay", "Stationary", "Others"]
        }
        
        h1, h2, h3, h4, h5 = st.columns([2, 2.5, 2.5, 1.5, 3.5])
        h1.markdown("**Expense Type**"); h2.markdown("**Expense Category**"); h3.markdown("**Sub Category**"); h4.markdown("**Amount ৳**"); h5.markdown("**Remarks**")
        
        expense_rows_data = []
        for i in range(int(num_rows)):
            c1, c2, c3, c4, c5 = st.columns([2, 2.5, 2.5, 1.5, 3.5])
            with c1: etype = st.selectbox(f"Type_{i}", ["", "ROI_Expences", "Expences", "Merchant"], key=f"e_t_{i}", label_visibility="collapsed")
            with c2: ecat = st.selectbox(f"Cat_{i}", categories_map.get(etype, [""]), key=f"e_c_{i}", label_visibility="collapsed")
            with c3: esub = st.selectbox(f"SubCat_{i}", [""] if ecat == "" else [ecat], key=f"e_s_{i}", label_visibility="collapsed")
            with c4: eamt = st.number_input(f"Amt_{i}", min_value=0.0, step=50.0, value=None, key=f"e_a_{i}", label_visibility="collapsed")
            with c5: erem = st.text_input(f"Rem_{i}", key=f"e_r_{i}", label_visibility="collapsed", placeholder="বিস্তারিত...")
            expense_rows_data.append((etype, ecat, esub, eamt, erem))
            
        if st.button("💾 সকল খরচ একসাথে সাবমিট করুন", type="primary", use_container_width=True):
            valid_entries = 0; conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
            for et, ec, es, ea, er in expense_rows_data:
                if et and ec and ea and ea > 0:
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)", (str(exp_date), current_company, ea, f"[{et} -> {ec}] {er}"))
                    valid_entries += 1
            conn.commit(); conn.close()
            if valid_entries > 0: st.success(f"🎉 মোট {valid_entries}টি খরচ সেভ করা হয়েছে!"); import time; time.sleep(0.5); st.rerun()

    with exp_tab2:
        conn = sqlite3.connect(DB_NAME)
        exp_df = pd.read_sql_query("SELECT date as 'তারিখ', amount as 'খরচের পরিমাণ (৳)', remarks as 'বিস্তারিত বিবরণ' FROM cash_transactions WHERE company = ? AND second_party = 'Petty_Cash' AND type = 'Cash Out' ORDER BY date DESC", conn, params=(current_company,))
        conn.close()
        if not exp_df.empty:
            st.metric("💰 সর্বমোট খরচ", f"{exp_df['খরচের পরিমাণ (৳)'].sum():,.1f} ৳")
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
