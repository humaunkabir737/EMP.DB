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

st.markdown("""
<style>
    div[data-testid="column"] { padding: 8px; }
    .block-container { padding-top: 1.5rem; }
    .sidebar-menu-btn { width: 100%; margin-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# লগইন সিস্টেম
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
        with st.form("login_form"):
            username = st.text_input("ইউজারনেম (Username)")
            password = st.text_input("পাসওয়ার্ড (Password)", type="password")
            if st.form_submit_button("লগইন করুন", use_container_width=True):
                if username == "admin" and password == "jabed2026":
                    st.session_state.logged_in = True; st.session_state.user_role = "admin"; st.session_state.current_action = None 
                    st.success("লগইন সফল হয়েছে!"); import time; time.sleep(0.5); st.rerun()
                elif username == "bKash_User" and password == "bkash2026": 
                    st.session_state.logged_in = True; st.session_state.user_role = "bKash_User"; st.session_state.current_company = "bKash"; st.session_state.current_action = None 
                    st.success("লগইন সফল!"); import time; time.sleep(0.5); st.rerun()
                elif username == "GP_User" and password == "gp2026": 
                    st.session_state.logged_in = True; st.session_state.user_role = "GP_User"; st.session_state.current_company = "GP"; st.session_state.current_action = None 
                    st.success("লগইন সফল!"); import time; time.sleep(0.5); st.rerun()
                else: st.error("ভুল ইউজারনেম অথবা পাসওয়ার্ড!")
    st.stop()

# ==============================================================================
# ২. ডাইনামিক পাথ ও ফোল্ডার
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
# ৩. ডাটাবেজ মাইগ্রেশন ও সীডিং
# ==============================================================================
def init_db():
    for folder in [UPLOAD_DIR, IMAGE_DIR, PHOTO_DIR, EMP_NID_DIR, GUAR_PHOTO_DIR, GUAR_NID_DIR]:
        if not os.path.exists(folder): os.makedirs(folder)

    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
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
    
    # নতুন লজিকের জন্য প্রয়োজনীয় ডিফল্ট অ্যাকাউন্টিং হেডসমূহ যুক্ত করা হলো
    default_parties = ["Hand_Cash", "Petty_Cash", "DM_DSS_Bank", "Market_Advance", "Others_Due", "Bank", "BGP", "Dulal", "Shafayat", "Madina", "Owner", "GAS", "Auto_Rice", "Others", "bKash", "Commission", "Al_Arafa", "Rekit", "DMCBL", "Kabita_Mami", "Ashim_Da", "Al_Amin"]
    for party in default_parties:
        cursor.execute("INSERT OR IGNORE INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) VALUES ('bKash', ?, '', '', '', 'Active')", (party,))
        cursor.execute("INSERT OR IGNORE INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) VALUES ('GP', ?, '', '', '', 'Active')", (party,))
        
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, company TEXT NOT NULL, second_party TEXT NOT NULL, type TEXT NOT NULL, amount REAL NOT NULL, remarks TEXT
        )
    ''')
    
    cursor.execute("PRAGMA table_info(employees)")
    existing_columns = [col[1] for col in cursor.fetchall()]
    required_cols = {'company': "TEXT DEFAULT 'bKash'", 'father_name': "TEXT", 'father_nid': "TEXT", 'mother_name': "TEXT", 'emp_nid': "TEXT", 'guarantor_name': "TEXT", 'guarantor_nid': "TEXT", 'guarantor_mobile': "TEXT"}
    for col_name, col_type in required_cols.items():
        if col_name not in existing_columns: cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type}")
            
    conn.commit(); conn.close()

init_db()

# ==============================================================================
# ৪. গ্লোবাল সেশন স্টেট ও হেল্পার ফাংশন
# ==============================================================================
for state_key, default_val in [('current_company', 'None'), ('current_action', None), ('active_emp_id', None), ('dialog_edit_mode', False), ('active_party_id', None), ('party_edit_mode', False)]:
    if state_key not in st.session_state: st.session_state[state_key] = default_val

def open_edit_mode(): st.session_state.dialog_edit_mode = True
def close_edit_mode(): st.session_state.dialog_edit_mode = False

# নির্দিষ্ট তারিখের আগের যেকোনো অ্যাকাউন্টের ব্যালেন্স বের করার ডায়নামিক ফাংশন
def get_ledger_opening_balance(company, target_date_str, party_name):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(CASE WHEN type='Cash In' THEN amount ELSE 0 END) - SUM(CASE WHEN type='Cash Out' THEN amount ELSE 0 END)
        FROM cash_transactions WHERE company=? AND second_party=? AND date < ?
    """, (company, party_name, target_date_str))
    result = cursor.fetchone()[0]
    conn.close()
    return float(result) if result else 0.0

def render_no_image_frame(title):
    return f"""
    <div style="border: 2px dashed #444444; border-radius: 8px; background-color: #1e1e1e; height: 145px; display: flex; flex-direction: column; justify-content: center; align-items: center; color: #888888; margin-bottom: 15px;">
        <span style="font-size: 26px; margin-bottom: 2px;">🖼️</span><b style="font-size: 13px; color: #cccccc;">No Image</b><span style="font-size: 11px; color: #666666;">({title})</span>
    </div>
    """

def render_header():
    logo_html = ""
    for ext in ["png", "jpg", "jpeg"]:
        logo_path = os.path.join(IMAGE_DIR, f"logo.{ext}")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f: encoded = base64.b64encode(f.read()).decode()
            logo_html = f'<img src="data:image/{ext};base64,{encoded}" style="height:55px; vertical-align: middle;">'; break
    title_text = '<h1 style="color: white; margin: 0; font-family:\'Times New Roman\', serif; font-size: 38px; font-weight: bold;">M/S JABED ENTERPRISE</h1>'
    header_content = f'<div style="display: flex; justify-content: center; align-items: center; gap: 12px;">{logo_html}{title_text}</div>' if logo_html else title_text
    st.markdown(f"""
        <div style="text-align: center; margin-top: -15px; margin-bottom: 2px;">{header_content}<p style="color: #a0a0a0; margin: 6px 0 0 0; font-size: 14.5px;">394 Anima Plaza, Nagerbazar, Bagerhat Sadar, Bagerhat.</p></div>
        <hr style="border: 1px solid #10b981; margin-top: 15px; margin-bottom: 25px;">
    """, unsafe_allow_html=True)

# ==============================================================================
# 💈 সাইডবার ন্যাভিগেশন (ফোল্ডার বাগ ফিক্সড)
# ==============================================================================
st.sidebar.markdown("## Main Menu")
user_role = st.session_state.get('user_role', None)
st.sidebar.markdown(f"### স্বাগতম, <span style='color:#10b981;'>{user_role}</span> 👋", unsafe_allow_html=True)

if st.sidebar.button("🔒 লগআউট (Logout)", use_container_width=True):
    st.session_state.logged_in = False; st.session_state.user_role = None; st.session_state.current_company = None; st.session_state.current_action = None; st.rerun()

st.sidebar.markdown("<hr style='margin: 10px 0px; border-color: #444;'>", unsafe_allow_html=True)
menu_options_emp = ["Add New Employee", "Add Employee By Upload", "View All Employee"]

# বকশ (bKash) ফোল্ডার এবং মেনু
if user_role in ["admin", "bKash_User"]:
    with st.sidebar.expander("📁 bKash", expanded=(st.session_state.get('current_company') == "bKash")):
        st.markdown("<p style='color:#10b981; margin-bottom:2px;'><b>📁 Employee Management</b></p>", unsafe_allow_html=True)
        bk_default = menu_options_emp.index(st.session_state.current_action) if (st.session_state.get('current_company') == "bKash" and st.session_state.get('current_action') in menu_options_emp) else None
        def bk_emp_cb(): st.session_state.current_company = "bKash"; st.session_state.current_action = st.session_state.bk_emp_radio
        st.radio("bKash Emp", options=menu_options_emp, index=bk_default, key="bk_emp_radio", on_change=bk_emp_cb, label_visibility="collapsed")
        
        st.markdown("<hr style='margin:8px 0px; border-color:#333;'><p style='color:#10b981; margin-bottom:2px;'><b>📊 Account Management</b></p>", unsafe_allow_html=True)
        if st.button("📝 Cash Khata Maintenance", key="bk_ck_btn", use_container_width=True): st.session_state.current_company = "bKash"; st.session_state.current_action = "Cash Khata Maintenance"; st.rerun()
        if st.button("📊 Cash Report View", key="bk_cr_btn", use_container_width=True): st.session_state.current_company = "bKash"; st.session_state.current_action = "Report View"; st.rerun()
        if st.button("📉 Expense Management", key="bk_exp_btn", use_container_width=True): st.session_state.current_company = "bKash"; st.session_state.current_action = "Expense Management"; st.rerun()
        
        st.markdown("<hr style='margin:8px 0px; border-color:#333;'><p style='color:#10b981; margin-bottom:2px;'><b>👥 Second Party Details</b></p>", unsafe_allow_html=True)
        if st.button("➕ Add New Second Party", key="bk_add_sp_btn", use_container_width=True): st.session_state.current_company = "bKash"; st.session_state.current_action = "Add New Second Party"; st.rerun()
        if st.button("📋 View All Second Parties", key="bk_view_sp_btn", use_container_width=True): st.session_state.current_company = "bKash"; st.session_state.current_action = "View All Second Parties"; st.rerun()

# গ্রামীণফোন (GP) ফোল্ডার এবং মেনু
if user_role in ["admin", "GP_User"]:
    with st.sidebar.expander("📁 GP", expanded=(st.session_state.get('current_company') == "GP")):
        st.markdown("<p style='color:#10b981; margin-bottom:2px;'><b>📁 Employee Management</b></p>", unsafe_allow_html=True)
        gp_default = menu_options_emp.index(st.session_state.current_action) if (st.session_state.get('current_company') == "GP" and st.session_state.get('current_action') in menu_options_emp) else None
        def gp_emp_cb(): st.session_state.current_company = "GP"; st.session_state.current_action = st.session_state.gp_emp_radio
        st.radio("GP Emp", options=menu_options_emp, index=gp_default, key="gp_emp_radio", on_change=gp_emp_cb, label_visibility="collapsed")
        
        st.markdown("<hr style='margin:8px 0px; border-color:#333;'><p style='color:#10b981; margin-bottom:2px;'><b>📊 Account Management</b></p>", unsafe_allow_html=True)
        if st.button("📝 Cash Khata Maintenance ", key="gp_ck_btn", use_container_width=True): st.session_state.current_company = "GP"; st.session_state.current_action = "Cash Khata Maintenance"; st.rerun()
        if st.button("📊 Cash Report View ", key="gp_cr_btn", use_container_width=True): st.session_state.current_company = "GP"; st.session_state.current_action = "Report View"; st.rerun()
        if st.button("📉 Expense Management ", key="gp_exp_btn", use_container_width=True): st.session_state.current_company = "GP"; st.session_state.current_action = "Expense Management"; st.rerun()
        
        st.markdown("<hr style='margin:8px 0px; border-color:#333;'><p style='color:#10b981; margin-bottom:2px;'><b>👥 Second Party Details</b></p>", unsafe_allow_html=True)
        if st.button("➕ Add New Second Party ", key="gp_add_sp_btn", use_container_width=True): st.session_state.current_company = "GP"; st.session_state.current_action = "Add New Second Party"; st.rerun()
        if st.button("📋 View All Second Parties ", key="gp_view_sp_btn", use_container_width=True): st.session_state.current_company = "GP"; st.session_state.current_action = "View All Second Parties"; st.rerun()

current_action = st.session_state.get('current_action', None)
current_company = st.session_state.get('current_company', None)

# ==============================================================================
# 🚀 মেইন রাউটার লজিক শুরু
# ==============================================================================
render_header()

if current_action is None:
    st.markdown("<h3 style='text-align: center; color: #10b981;'>ড্যাশবোর্ডে আপনাকে স্বাগতম!</h3>", unsafe_allow_html=True)
    st.info("💡 কাজ শুরু করতে বাম পাশের সাইডবার মেনু থেকে কোম্পানির নির্দিষ্ট ফোল্ডার এক্সপ্যান্ড করে কাঙ্ক্ষিত অপশনটি সিলেক্ট করুন।")

# ==============================================================================
# 📝 Cash Khata Maintenance (অটো-ওপেনিং ও ডাইনামিক ক্লোজিং ব্যালেন্সিং লজিক)
# ==============================================================================
elif current_action == "Cash Khata Maintenance":
    st.markdown(f"### 📝 Cash Khata Maintenance ({current_company})")
    conn = sqlite3.connect(DB_NAME)
    parties = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=? AND status='Active'", (current_company,)).fetchall()]
    conn.close()

    # ১. Excel Bulk Upload (ঐচ্ছিক)
    with st.expander("📤 Excel ফাইল ড্রপ করে একসাথে সব ডেটা ইনপুট করুন (Bulk Upload)", expanded=False):
        up_col1, up_col2 = st.columns([3, 1])
        with up_col1: uploaded_cash_excel = st.file_uploader("ক্যাশ খাতার এক্সেল ফাইলটি এখানে ড্রপ করুন:", type=["xlsx"])
        with up_col2:
            st.markdown("<div style='padding-top: 24px;'></div>", unsafe_allow_html=True)
            cash_template_buffer = io.BytesIO()
            cash_temp_df = pd.DataFrame(columns=["date", "second_party", "type", "amount", "remarks"])
            cash_temp_df.loc[0] = [str(datetime.now().date()), "Bank", "Cash In", 50000.0, "Bank Transfer In"]
            with pd.ExcelWriter(cash_template_buffer, engine='openpyxl') as writer: cash_temp_df.to_excel(writer, index=False, sheet_name='Template')
            st.download_button("📥 ডাউনলোড টেমপ্লেট", data=cash_template_buffer.getvalue(), file_name=f"{current_company}_cash_template.xlsx", use_container_width=True)

        if uploaded_cash_excel is not None:
            try:
                xl_df = pd.read_excel(uploaded_cash_excel)
                st.dataframe(xl_df.head(5), use_container_width=True, hide_index=True)
                if st.button("💾 এক্সেল ডাটা সেভ করুন"):
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor(); success_count = 0
                    for _, row in xl_df.iterrows():
                        c_date = str(row.get('date', datetime.now().date())).split(" ")[0]
                        c_party, c_type, c_amount = str(row.get('second_party', '')).strip(), str(row.get('type', '')).strip(), float(row['amount']) if pd.notnull(row['amount']) else 0.0
                        if c_party and c_type in ["Cash In", "Cash Out"] and c_amount > 0:
                            cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, ?, ?, ?)", (c_date, current_company, c_party, c_type, c_amount, str(row.get('remarks', ''))))
                            success_count += 1
                    conn.commit(); conn.close()
                    st.success(f"✅ এক্সেল থেকে {success_count}টি লেনদেন সেভ করা হয়েছে!"); import time; time.sleep(0.5); st.rerun()
            except Exception as e: st.error(f"এক্সেল প্রসেসিং এরর: {e}")

    # ২. আপনার চাহিদামত পিওর ডাবল-এন্ট্রি গ্রিড (Receive vs Payout)
    st.markdown("#### ⚖️ ডেইলি ক্যাশ খাতা গ্রিড এন্ট্রি")
    tx_master_date = st.date_input("📆 হিসাবের তারিখ (Date Selection):", datetime.now().date())
    target_date_str = str(tx_master_date)
    
    # ডাটাবেজ থেকে নির্দিষ্ট তারিখের অটোমেটিক ওপেনিং ব্যালেন্সগুলো টেনে আনা
    op_vault = get_ledger_opening_balance(current_company, target_date_str, 'Hand_Cash')
    op_dm = get_ledger_opening_balance(current_company, target_date_str, 'DM_DSS_Bank')
    op_ma = get_ledger_opening_balance(current_company, target_date_str, 'Market_Advance')
    op_od = get_ledger_opening_balance(current_company, target_date_str, 'Others_Due')
    
    # টোটাল ওপেনিং ব্যালেন্স (Cash Receive এর উপরের অংশ)
    total_opening_cash = op_vault + op_dm + op_ma + op_od

    receive_side_col, payout_side_col = st.columns(2)
    
    # -------------------------------------------------------------------------
    # 📥 বাম কলাম: CASH RECEIVE (জমা)
    # -------------------------------------------------------------------------
    with receive_side_col:
        st.markdown("<h4 style='background-color:#064e3b; padding:8px; border-radius:5px; text-align:center; color:#10b981; border: 1px solid #10b981;'>📥 CASH RECEIVE (জমা)</h4>", unsafe_allow_html=True)
        
        st.markdown("<div style='background-color:#141414; padding:10px; border:1px solid #333;'><b>📂 Opening Cash (অটোমেটিক পূর্বের ব্যালেন্স):</b></div>", unsafe_allow_html=True)
        # অটোমেটিক ফিল্ডসমূহ (রিড অনলি)
        c1, c2 = st.columns([3, 2]); c1.write("Opening Vault Cash:"); c2.write(f"**{op_vault:,.1f} ৳**")
        c1, c2 = st.columns([3, 2]); c1.write("DM & DSS Bank:"); c2.write(f"**{op_dm:,.1f} ৳**")
        c1, c2 = st.columns([3, 2]); c1.write("Market Advance:"); c2.write(f"**{op_ma:,.1f} ৳**")
        c1, c2 = st.columns([3, 2]); c1.write("Others Due:"); c2.write(f"**{op_od:,.1f} ৳**")
        st.markdown(f"<div style='text-align:right; color:#10b981; font-weight:bold; border-top:1px solid #333; padding-top:5px;'>Total Opening Cash: {total_opening_cash:,.1f} ৳</div>", unsafe_allow_html=True)
        
        st.markdown("<br><div style='background-color:#141414; padding:5px; border:1px solid #333;'><b>➕ Today's Receive (আজকের জমা):</b></div>", unsafe_allow_html=True)
        
        th_c1, th_c2, th_c3 = st.columns([3, 2, 3])
        th_c1.markdown("<b style='font-size:13px;'>সেকেন্ড পার্টি নাম</b>", unsafe_allow_html=True)
        th_c2.markdown("<b style='font-size:13px;'>Amount ৳</b>", unsafe_allow_html=True)
        th_c3.markdown("<b style='font-size:13px;'>Remarks (বিবরণ)</b>", unsafe_allow_html=True)
        
        rcv_inputs = []
        for idx in range(10):
            r_c1, r_c2, r_c3 = st.columns([3, 2, 3])
            with r_c1: rp = st.selectbox(f"R_Party_{idx}", options=[""] + parties, key=f"r_p_{idx}", label_visibility="collapsed")
            with r_c2: ra = st.number_input(f"R_Amt_{idx}", min_value=0.0, step=500.0, value=None, key=f"r_a_{idx}", label_visibility="collapsed")
            with r_c3: rr = st.text_input(f"R_Rem_{idx}", placeholder="-", key=f"r_r_{idx}", label_visibility="collapsed")
            rcv_inputs.append((rp, ra, rr))
            
        today_total_receive = sum([item[1] for item in rcv_inputs if item[1] is not None])
        st.markdown(f"<div style='text-align:right; font-weight:bold;'>Total Today's Receive: {today_total_receive:,.1f} ৳</div>", unsafe_allow_html=True)
        
        grand_total_receive = total_opening_cash + today_total_receive
        st.markdown(f"<h4 style='text-align:right; color:#10b981; margin-top:10px; border-top:2px solid #10b981; padding-top:5px;'>Total Receive Side: {grand_total_receive:,.1f} ৳</h4>", unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 📤 ডান কলাম: PAY OUT (খরচ)
    # -------------------------------------------------------------------------
    with payout_side_col:
        st.markdown("<h4 style='background-color:#7f1d1d; padding:8px; border-radius:5px; text-align:center; color:#f87171; border: 1px solid #7f1d1d;'>📤 PAY OUT (খরচ/প্রদান)</h4>", unsafe_allow_html=True)
        
        st.markdown("<div style='background-color:#141414; padding:10px; border:1px solid #333;'><b>📂 Closing Balances:</b></div>", unsafe_allow_html=True)
        
        st.caption("নিচের ঘরগুলোতে দিনশেষের স্থিতি ম্যানুয়ালি বসান:")
        p_lbl1, p_val1 = st.columns([3, 2]); p_lbl1.markdown("<p style='margin-top:8px;'>DM & DSS Bank:</p>", unsafe_allow_html=True)
        cl_dm = p_val1.number_input("DM Bank", min_value=0.0, value=0.0, step=1000.0, label_visibility="collapsed", key="cl_dm")
        
        p_lbl2, p_val2 = st.columns([3, 2]); p_lbl2.markdown("<p style='margin-top:8px;'>Market Advance:</p>", unsafe_allow_html=True)
        cl_ma = p_val2.number_input("Mkt Adv", min_value=0.0, value=0.0, step=1000.0, label_visibility="collapsed", key="cl_ma")
        
        p_lbl3, p_val3 = st.columns([3, 2]); p_lbl3.markdown("<p style='margin-top:8px;'>Others Due:</p>", unsafe_allow_html=True)
        cl_od = p_val3.number_input("Oth Due", min_value=0.0, value=0.0, step=1000.0, label_visibility="collapsed", key="cl_od")
        
        st.markdown("<br><div style='background-color:#141414; padding:5px; border:1px solid #333;'><b>➖ Today's Pay Out (আজকের খরচ):</b></div>", unsafe_allow_html=True)
        
        ph_c1, ph_c2, ph_c3 = st.columns([3, 2, 3])
        ph_c1.markdown("<b style='font-size:13px;'>সেকেন্ড পার্টি নাম</b>", unsafe_allow_html=True)
        ph_c2.markdown("<b style='font-size:13px;'>Amount ৳</b>", unsafe_allow_html=True)
        ph_c3.markdown("<b style='font-size:13px;'>Remarks (বিবরণ)</b>", unsafe_allow_html=True)
        
        pay_inputs = []
        for idx in range(10):
            p_c1, p_c2, p_c3 = st.columns([3, 2, 3])
            with p_c1: pp = st.selectbox(f"P_Party_{idx}", options=[""] + parties, key=f"p_p_{idx}", label_visibility="collapsed")
            with p_c2: pa = st.number_input(f"P_Amt_{idx}", min_value=0.0, step=500.0, value=None, key=f"p_a_{idx}", label_visibility="collapsed")
            with p_c3: pr = st.text_input(f"P_Rem_{idx}", placeholder="-", key=f"p_r_{idx}", label_visibility="collapsed")
            pay_inputs.append((pp, pa, pr))
            
        today_total_payout = sum([item[1] for item in pay_inputs if item[1] is not None])
        st.markdown(f"<div style='text-align:right; font-weight:bold;'>Total Today's Pay Out: {today_total_payout:,.1f} ৳</div>", unsafe_allow_html=True)
        
        # আপনার দেওয়া সূত্র অনুযায়ী অটোমেটিক Closing Cash ক্যালকুলেশন
        cl_vault = grand_total_receive - (today_total_payout + cl_dm + cl_ma + cl_od)
        
        st.markdown("<div style='background-color:#1a202c; padding:8px; border:1px dashed #f87171; margin-top:10px;'>", unsafe_allow_html=True)
        pc1, pc2 = st.columns([3, 2])
        pc1.markdown("<b style='color:#f87171;'>Closing Vault Cash (Auto):</b>", unsafe_allow_html=True)
        pc2.markdown(f"<b style='color:#f87171; font-size:16px;'>{cl_vault:,.1f} ৳</b>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        grand_total_payout = cl_vault + cl_dm + cl_ma + cl_od + today_total_payout
        st.markdown(f"<h4 style='text-align:right; color:#f87171; margin-top:10px; border-top:2px solid #f87171; padding-top:5px;'>Total Pay Out Side: {grand_total_payout:,.1f} ৳</h4>", unsafe_allow_html=True)

    st.markdown("---")
    
    # সেভ লজিক ও ডাবল-এন্ট্রি ইনটেগ্রিটি মেইনটেনেন্স
    if cl_vault < 0:
        st.error("❌ ফিজিক্যাল ভল্ট ক্যাশ কখনো ঋণাত্মক (Negative) হতে পারে না! আপনার রিসিভ বা পে-আউট এন্ট্রিতে কোনো ভুল আছে।")
        st.button("💾 ক্যাশ খাতা সেভ করুন", type="primary", use_container_width=True, disabled=True)
    else:
        st.success(f"⚖️ সমীকরণ মিলেছে! আজকের ক্লোজিং ভল্ট ক্যাশ: **{cl_vault:,.1f} ৳**। আপনি এখন ডাটাবেজে সাবমিট করতে পারেন।")
        if st.button("💾 সমীকরণ নিশ্চিত করুন এবং ক্যাশ খাতা সেভ করুন", type="primary", use_container_width=True):
            conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
            try:
                # ১. গ্রিডের ডাটা সেভ
                for rp, ra, rr in rcv_inputs:
                    if rp and ra and ra > 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash In', ?, ?)", (target_date_str, current_company, rp, ra, rr.strip()))
                for pp, pa, pr in pay_inputs:
                    if pp and pa and pa > 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash Out', ?, ?)", (target_date_str, current_company, pp, pa, pr.strip()))
                
                # ২. ম্যানুয়াল ক্লোজিং ভ্যালুগুলোকে ডাটাবেজ ডেল্টা হিসেবে সেভ করা (যাতে আগামীকালের ওপেনিং ঠিক থাকে)
                delta_dm = cl_dm - op_dm
                if delta_dm > 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'DM_DSS_Bank', 'Cash Out', ?, 'Net Ledger Adjustment')", (target_date_str, current_company, delta_dm))
                elif delta_dm < 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'DM_DSS_Bank', 'Cash In', ?, 'Net Ledger Adjustment')", (target_date_str, current_company, abs(delta_dm)))
                
                delta_ma = cl_ma - op_ma
                if delta_ma > 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Market_Advance', 'Cash Out', ?, 'Net Ledger Adjustment')", (target_date_str, current_company, delta_ma))
                elif delta_ma < 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Market_Advance', 'Cash In', ?, 'Net Ledger Adjustment')", (target_date_str, current_company, abs(delta_ma)))
                
                delta_od = cl_od - op_od
                if delta_od > 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Others_Due', 'Cash Out', ?, 'Net Ledger Adjustment')", (target_date_str, current_company, delta_od))
                elif delta_od < 0: cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Others_Due', 'Cash In', ?, 'Net Ledger Adjustment')", (target_date_str, current_company, abs(delta_od)))
                
                conn.commit(); st.balloons(); st.success("🎉 চমৎকার! খাতার আজকের দিনের হিসাব সফলভাবে ডাটাবেজে লক করা হয়েছে।")
                import time; time.sleep(0.8); st.rerun()
            except Exception as ex: st.error(f"Error: {ex}")
            finally: conn.close()

# ==============================================================================
# 📊 Report View (ডেইলি, মাসিক এবং সেকেন্ড পার্টি-ভিত্তিক অ্যাডভান্সড রিপোর্ট)
# ==============================================================================
elif current_action == "Report View":
    st.markdown(f"### 📊 Report View ({current_company})")
    rep_tab1, rep_tab2, rep_tab3 = st.tabs(["📆 Daily Report", "📅 Monthly Report", "👥 Second Party-wise Report"])
    conn = sqlite3.connect(DB_NAME)
    
    with rep_tab1:
        st.markdown("##### 📆 দৈনিক লেনদেন রিপোর্ট")
        rep_date = st.date_input("তারিখ নির্বাচন করুন:", datetime.now().date(), key="rep_daily_date")
        daily_df = pd.read_sql_query("SELECT date as 'তারিখ', second_party as 'সেকেন্ড পার্টি', type as 'ধরণ', amount as 'টাকার পরিমাণ (৳)', remarks as 'বিবরণ' FROM cash_transactions WHERE company=? AND date=? ORDER BY id DESC", conn, params=(current_company, str(rep_date)))
        if daily_df.empty: st.info("এই তারিখে কোনো রেকর্ড নেই।")
        else:
            st.dataframe(daily_df, use_container_width=True, hide_index=True)

    with rep_tab2:
        st.markdown("##### 📅 মাসিক পুঞ্জীভূত রিপোর্ট")
        months_list = [f"{i:02d}" for i in range(1, 13)]
        selected_month = st.selectbox("মাস সিলেক্ট করুন:", months_list, index=int(datetime.now().strftime("%m"))-1)
        selected_year = st.selectbox("বছর সিলেক্ট করুন:", ["2025", "2026", "2027"], index=1)
        month_str = f"{selected_year}-{selected_month}-%"
        monthly_df = pd.read_sql_query("SELECT date as 'তারিখ', second_party as 'সেকেন্ড পার্টি', type as 'ধরণ', amount as 'টাকার পরিমাণ (৳)', remarks as 'বিবরণ' FROM cash_transactions WHERE company=? AND date LIKE ? ORDER BY date ASC, id DESC", conn, params=(current_company, month_str))
        if monthly_df.empty: st.info("এই মাসে কোনো রেকর্ড নেই।")
        else:
            t_in, t_out = monthly_df[monthly_df['ধরণ'] == 'Cash In']['টাকার পরিমাণ (৳)'].sum(), monthly_df[monthly_df['ধরণ'] == 'Cash Out']['টাকার পরিমাণ (৳)'].sum()
            m1, m2, m3 = st.columns(3); m1.metric("মোট ইন", f"{t_in:,.1f} ৳"); m2.metric("মোট আউট", f"{t_out:,.1f} ৳"); m3.metric("নেট ফ্লো", f"{t_in - t_out:,.1f} ৳")
            st.dataframe(monthly_df, use_container_width=True, hide_index=True)

    with rep_tab3:
        st.markdown("##### 👥 সেকেন্ড পার্টি-ভিত্তিক নির্দিষ্ট খতিয়ান")
        active_parties = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=?", (current_company,)).fetchall()]
        selected_party = st.selectbox("সেকেন্ড পার্টি ফিল্টার করুন:", active_parties)
        party_df = pd.read_sql_query("SELECT date as 'তারিখ', type as 'ধরণ', amount as 'টাকার পরিমাণ (৳)', remarks as 'বিবরণ' FROM cash_transactions WHERE company=? AND second_party=? ORDER BY date ASC, id DESC", conn, params=(current_company, selected_party))
        if party_df.empty: st.info(f"'{selected_party}' এর কোনো ট্রানজেকশন নেই।")
        else:
            p_in, p_out = party_df[party_df['ধরণ'] == 'Cash In']['টাকার পরিমাণ (৳)'].sum(), party_df[party_df['ধরণ'] == 'Cash Out']['টাকার পরিমাণ (৳)'].sum()
            r1, r2, r3 = st.columns(3); r1.metric("মোট গৃহীত (In)", f"{p_in:,.1f} ৳"); r2.metric("মোট প্রদত্ত (Out)", f"{p_out:,.1f} ৳"); r3.metric("বর্তমান ব্যালেন্স", f"{p_in - p_out:,.1f} ৳")
            st.dataframe(party_df, use_container_width=True, hide_index=True)
            
    conn.close()

# ==============================================================================
# 📉 Expense Management Module
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
                        r_type, r_cat = str(row.get('expense_type', '')).strip(), str(row.get('expense_category', '')).strip()
                        r_subcat = str(row.get('sub_category', r_cat)).strip() 
                        r_amt = float(row['amount']) if pd.notnull(row['amount']) else 0.0
                        if r_type and r_cat and r_amt > 0:
                            cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)", (r_date, current_company, r_amt, f"[{r_type} -> {r_cat} -> {r_subcat}] {str(row.get('remarks', ''))}"))
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
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)", (str(exp_date), current_company, ea, f"[{et} -> {ec} -> {es}] {er}"))
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

# ==============================================================================
# ৯. গ্লোবাল একটিভ ডায়ালগ কন্ট্রোলার 
# ==============================================================================
if st.session_state.active_emp_id:
    show_employee_details(st.session_state.active_emp_id, st.session_state.current_company)
    st.session_state.active_emp_id = None

if st.session_state.active_party_id:
    show_second_party_details(st.session_state.active_party_id)
