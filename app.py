# ==============================================================================
# 1. INITIAL CONFIGURATION & IMPORTS
# ==============================================================================
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import os
import base64
from PIL import Image

# Strict Minimalist Layout Configuration
st.set_page_config(page_title="M/S Jabed Enterprise", layout="wide", initial_sidebar_state="expanded")

# Custom CSS for Professional Minimalist UI (No large fonts, clean lines, compact spacing)
st.markdown("""
    <style>
        html, body, [data-testid="stSidebar"] {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        .block-container {
            padding-top: 1.5rem !important;
            padding-bottom: 1rem !important;
        }
        h1, h2, h3, h4 {
            font-weight: 600 !important;
            margin-top: 0px !important;
            margin-bottom: 8px !important;
        }
        div[data-testid="stExpander"] {
            border: 1px solid #2d2d2d !important;
            border-radius: 4px !important;
            margin-bottom: 5px !important;
        }
        .stButton>button {
            border-radius: 4px !important;
            font-size: 13px !important;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 13px !important;
            font-weight: 500 !important;
        }
    </style>
""", unsafe_allow_html=True)

# ==============================================================================
# 2. SECURITY & ROLE-BASED ACCESS CONTROL
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, login_col, _ = st.columns([1, 1.2, 1])
    with login_col:
        st.markdown("<h3 style='text-align: center;'>SYSTEM AUTHENTICATION</h3>", unsafe_allow_html=True)
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("LOGIN", use_container_width=True):
                if username == "admin" and password == "jabed2026":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "admin"
                    st.session_state.current_action = None
                    st.rerun()
                elif username == "bKash_User" and password == "bkash2026":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "bKash_User"
                    st.session_state.current_company = "bKash"
                    st.session_state.current_action = None
                    st.rerun()
                elif username == "GP_User" and password == "gp2026":
                    st.session_state.logged_in = True
                    st.session_state.user_role = "GP_User"
                    st.session_state.current_company = "GP"
                    st.session_state.current_action = None
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
    st.stop()

# ==============================================================================
# 3. DIRECTORIES & DATABASE INITIALIZATION
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "jabed_enterprise.db")
IMAGE_DIR = os.path.join(BASE_DIR, "Related Image")
PHOTO_DIR = os.path.join(BASE_DIR, "employee_photos")
EMP_NID_DIR = os.path.join(BASE_DIR, "nid_photos")
GUAR_PHOTO_DIR = os.path.join(BASE_DIR, "guarantor_photos")
GUAR_NID_DIR = os.path.join(BASE_DIR, "guarantor_nids")

def init_db():
    for folder in [IMAGE_DIR, PHOTO_DIR, EMP_NID_DIR, GUAR_PHOTO_DIR, GUAR_NID_DIR]:
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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL, company TEXT NOT NULL, second_party TEXT NOT NULL, type TEXT NOT NULL, amount REAL NOT NULL, remarks TEXT
        )
    ''')
    
    # Pre-seeded 20 entities under strict English policy
    default_parties = ["Mother_Wallet", "Hand_Cash", "Petty_Cash", "Bank", "BGP", "Dulal", "Shafayat", "Madina", "Owner", "GAS", "Auto_Rice", "Others", "bKash", "Commission", "Al_Arafa", "Rekit", "DMCBL", "Kabita_Mami", "Ashim_Da", "Al_Amin"]
    for company_node in ['bKash', 'GP']:
        for party in default_parties:
            cursor.execute("INSERT OR IGNORE INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) VALUES (?, ?, '', '', '', 'Active')", (company_node, party))
            
    conn.commit()
    conn.close()

init_db()

# ==============================================================================
# 4. STATE MANAGEMENT & DATA HELPERS
# ==============================================================================
for state_key, default_val in [('current_company', 'None'), ('current_action', None), ('active_emp_id', None), ('dialog_edit_mode', False), ('active_party_id', None), ('party_edit_mode', False)]:
    if state_key not in st.session_state:
        st.session_state[state_key] = default_val

def get_opening_vault_cash(company, target_date_str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT SUM(CASE WHEN type='Cash In' THEN amount ELSE 0 END) - SUM(CASE WHEN type='Cash Out' THEN amount ELSE 0 END)
        FROM cash_transactions WHERE company=? AND date < ?
    """, (company, target_date_str))
    res = cursor.fetchone()[0]
    conn.close()
    return float(res) if res else 0.0

# ==============================================================================
# 5. HEADER COMPONENT (MINIMALIST)
# ==============================================================================
def render_header():
    logo_html = ""
    for ext in ["png", "jpg", "jpeg"]:
        logo_path = os.path.join(IMAGE_DIR, f"logo.{ext}")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            logo_html = f'<img src="data:image/{ext};base64,{encoded}" style="height:38px; vertical-align: middle; margin-right:10px;">'
            break
    
    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: space-between; padding-bottom: 8px; border-bottom: 1px solid #2d2d2d; margin-bottom: 15px;">
            <div style="display: flex; align-items: center;">
                {logo_html}
                <div>
                    <span style="font-size: 20px; font-weight: 600; letter-spacing: 0.5px; color: #ffffff;">M/S JABED ENTERPRISE</span>
                    <span style="font-size: 11px; color: #888888; margin-left: 15px;">394 Anima Plaza, Nagerbazar, Bagerhat</span>
                </div>
            </div>
            <div style="font-size: 12px; color: #888888;">System Date: {datetime.now().strftime('%Y-%m-%d')}</div>
        </div>
    """, unsafe_allow_html=True)

# ==============================================================================
# 6. SIDEBAR MENU NAVIGATION (RULE 1: STRICTLY COLLAPSED BY DEFAULT)
# ==============================================================================
st.sidebar.markdown("<div style='padding: 5px 0px;'><b style='font-size:14px; color:#10b981;'>ERP DASHBOARD</b></div>", unsafe_allow_html=True)
user_role = st.session_state.user_role
st.sidebar.markdown(f"<small style='color:#888888;'>Active User: {user_role}</small>", unsafe_allow_html=True)

if st.sidebar.button("LOGOUT", use_container_width=True):
    st.session_state.logged_in = False
    st.session_state.user_role = None
    st.session_state.current_company = None
    st.session_state.current_action = None
    st.rerun()

st.sidebar.markdown("<hr style='margin: 8px 0px; border-color: #2d2d2d;'>", unsafe_allow_html=True)
menu_emp_opts = ["Add New Employee", "Add Employee By Upload", "View All Employee"]

# Company Folders: expanded=False ensures strict default collapsed architecture
if user_role in ["admin", "bKash_User"]:
    with st.sidebar.expander("📁 bKash Folder", expanded=False):
        with st.expander("Employees", expanded=False):
            for opt in menu_emp_opts:
                if st.button(opt, key=f"bk_emp_{opt}", use_container_width=True):
                    st.session_state.current_company = "bKash"
                    st.session_state.current_action = opt
                    st.rerun()
        with st.expander("Accounts", expanded=False):
            if st.button("Cash Management", key="bk_cash_m", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Cash Management"; st.rerun()
            if st.button("Expense Management", key="bk_exp_m", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Expense Management"; st.rerun()
            if st.button("Add Second Party", key="bk_add_sp", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "Add New Second Party"; st.rerun()
            if st.button("View Second Parties", key="bk_view_sp", use_container_width=True):
                st.session_state.current_company = "bKash"; st.session_state.current_action = "View All Second Parties"; st.rerun()

if user_role in ["admin", "GP_User"]:
    with st.sidebar.expander("📁 GP Folder", expanded=False):
        with st.expander("Employees", expanded=False):
            for opt in menu_emp_opts:
                if st.button(opt, key=f"gp_emp_{opt}", use_container_width=True):
                    st.session_state.current_company = "GP"
                    st.session_state.current_action = opt
                    st.rerun()
        with st.expander("Accounts", expanded=False):
            if st.button("Cash Management", key="gp_cash_m", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Cash Management"; st.rerun()
            if st.button("Expense Management", key="gp_exp_m", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Expense Management"; st.rerun()
            if st.button("Add Second Party", key="gp_add_sp", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "Add New Second Party"; st.rerun()
            if st.button("View Second Parties", key="gp_view_sp", use_container_width=True):
                st.session_state.current_company = "GP"; st.session_state.current_action = "View All Second Parties"; st.rerun()

# ==============================================================================
# 7. ROUTER & CONTROLLER MAIN WORKSPACE
# ==============================================================================
render_header()
current_action = st.session_state.current_action
current_company = st.session_state.current_company

if current_action is None:
    st.info("Select a core module from the collapsed sidebar options to initialize.")

# ------------------------------------------------------------------------------
# CORE MODULE: CASH MANAGEMENT (RULE 2: SEPARATED TABS & SIDE-BY-SIDE GRID)
# ------------------------------------------------------------------------------
elif current_action == "Cash Management":
    st.markdown(f"🔬 **Cash Ledger Engine ({current_company})**")
    
    conn = sqlite3.connect(DB_NAME)
    parties = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=? AND status='Active'", (current_company,)).fetchall()]
    conn.close()

    # Rule 2 Implementation: Segment into isolated workflows via native Tabs
    tab_manual, tab_excel, tab_report = st.tabs(["⚡ Manual Double-Entry Grid", "📤 Excel Bulk Import Pushes", "📖 View Statement Registry"])
    
    with tab_manual:
        # Date & Vault Controls
        c_top1, c_top2 = st.columns([2, 2])
        tx_date = c_top1.date_input("Transaction Date Control:", datetime.now().date(), key="cash_master_date")
        calculated_opening_vault = get_opening_vault_cash(current_company, str(tx_date))
        c_top2.markdown(f"<div style='padding-top:28px; font-size:13px; color:#a0a0a0;'>System Calculated Opening Vault: <b>{calculated_opening_vault:,.2f} USD/BDT</b></div>", unsafe_allow_html=True)
        
        st.markdown("<hr style='margin:10px 0px; border-color:#2d2d2d;'>", unsafe_allow_html=True)
        
        # Rule 2: Cash Receive & Pay-out strictly side-by-side
        col_receive, col_payout = st.columns(2)
        
        with col_receive:
            st.markdown("<div style='background-color:#112211; padding:6px; border-radius:3px; font-size:12px; font-weight:600; text-align:center; color:#10b981; margin-bottom:10px;'>CASH RECEIVE ENTRY</div>", unsafe_allow_html=True)
            rcv_inputs = []
            grid_h1, grid_h2, grid_h3 = st.columns([3.5, 2.5, 4])
            grid_h1.markdown("<small style='color:#888;'>Second Party Account</small>", unsafe_allow_html=True)
            grid_h2.markdown("<small style='color:#88;'>Amount</small>", unsafe_allow_html=True)
            grid_h3.markdown("<small style='color:#88;'>Remarks / Memo</small>", unsafe_allow_html=True)
            
            for i in range(10):
                r_c1, r_c2, r_c3 = st.columns([3.5, 2.5, 4])
                p_name = r_c1.selectbox(f"R_P_{i}", options=[""] + parties, key=f"rcv_p_{i}", label_visibility="collapsed")
                p_amt = r_c2.number_input(f"R_A_{i}", min_value=0.0, step=500.0, value=None, key=f"rcv_a_{i}", label_visibility="collapsed")
                p_rem = r_c3.text_input(f"R_R_{i}", placeholder="-", key=f"rcv_r_{i}", label_visibility="collapsed")
                rcv_inputs.append((p_name, p_amt, p_rem))
                
            grid_rcv_sum = sum([item[1] for item in rcv_inputs if item[1] is not None])
            grand_total_receive = calculated_opening_vault + grid_rcv_sum
            st.markdown(f"<div style='text-align:right; font-size:13px; color:#10b981;'>Side Total: {grand_total_receive:,.2f}</div>", unsafe_allow_html=True)

        with col_payout:
            st.markdown("<div style='background-color:#221111; padding:6px; border-radius:3px; font-size:12px; font-weight:600; text-align:center; color:#f87171; margin-bottom:10px;'>CASH PAY-OUT ENTRY</div>", unsafe_allow_html=True)
            
            # Dynamic variables matching system schema
            v_c1, v_c2 = st.columns([6, 4])
            v_c1.markdown("<small style='color:#888;'>Variable Ledger System State</small>", unsafe_allow_html=True)
            dm_dss = v_c2.number_input("DM Bank", min_value=0.0, value=0.0, step=1000.0, key="v_dm_dss", label_visibility="collapsed")
            
            pay_inputs = []
            grid_p1, grid_p2, grid_p3 = st.columns([3.5, 2.5, 4])
            grid_p1.markdown("<small style='color:#88;'>Second Party Account</small>", unsafe_allow_html=True)
            grid_p2.markdown("<small style='color:#88;'>Amount</small>", unsafe_allow_html=True)
            grid_p3.markdown("<small style='color:#88;'>Remarks / Memo</small>", unsafe_allow_html=True)
            
            for i in range(10):
                p_c1, p_c2, p_c3 = st.columns([3.5, 2.5, 4])
                po_party = p_c1.selectbox(f"P_P_{i}", options=[""] + parties, key=f"pay_p_{i}", label_visibility="collapsed")
                po_amt = p_c2.number_input(f"P_A_{i}", min_value=0.0, step=500.0, value=None, key=f"pay_a_{i}", label_visibility="collapsed")
                po_rem = p_c3.text_input(f"P_R_{i}", placeholder="-", key=f"pay_r_{i}", label_visibility="collapsed")
                pay_inputs.append((po_party, po_amt, po_rem))
                
            grid_pay_sum = sum([item[1] for item in pay_inputs if item[1] is not None])
            grand_total_payout = dm_dss + grid_pay_sum
            st.markdown(f"<div style='text-align:right; font-size:13px; color:#f87171;'>Side Total: {grand_total_payout:,.2f}</div>", unsafe_allow_html=True)

        st.markdown("<hr style='margin:10px 0px; border-color:#2d2d2d;'>", unsafe_allow_html=True)
        
        # Trial Balance Execution
        if round(grand_total_receive, 2) == round(grand_total_payout, 2):
            if st.button("EXECUTE LOCK & TRANSACTION WORKFLOW", type="primary", use_container_width=True):
                conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                if dm_dss > 0:
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Bank', 'Cash Out', ?, 'Auto Entry')", (str(tx_date), current_company, dm_dss))
                for rp, ra, rr in rcv_inputs:
                    if rp and ra and ra > 0:
                        cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash In', ?, ?)", (str(tx_date), current_company, rp, ra, rr.strip()))
                for pp, pa, pr in pay_inputs:
                    if pp and pa and pa > 0:
                        cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, 'Cash Out', ?, ?)", (str(tx_date), current_company, pp, pa, pr.strip()))
                conn.commit(); conn.close()
                st.success("Journals successfully committed.")
                st.rerun()
        else:
            st.markdown(f"<div style='color:#ef4444; font-size:12px;'>Equation mismatch error. Offset variance: {abs(grand_total_receive - grand_total_payout):,.2f}. Write-lock active.</div>", unsafe_allow_html=True)

    with tab_excel:
        st.markdown("<small style='color:#888;'>Drop file to run automated ledger import engine.</small>", unsafe_allow_html=True)
        up_cash = st.file_uploader("Upload Configuration File (*.xlsx)", type=["xlsx"], key="xl_cash")
        if up_cash:
            try:
                df = pd.read_excel(up_cash)
                st.dataframe(df.head(3), use_container_width=True)
                if st.button("PROCESS COGNITIVE SHEET IMPORT", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    for _, r in df.iterrows():
                        cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, ?, ?, ?, ?)",
                                       (str(r['date']).split(" ")[0], current_company, str(r['second_party']), str(r['type']), float(r['amount']), str(r['remarks'])))
                    conn.commit(); conn.close()
                    st.success("Bulk commit execution finalized.")
            except Exception as e:
                st.error(f"Execution terminated: {e}")

    with tab_report:
        conn = sqlite3.connect(DB_NAME)
        ledger_df = pd.read_sql_query("SELECT date, second_party, type, amount, remarks FROM cash_transactions WHERE company=? ORDER BY date DESC, id DESC", conn, params=(current_company,))
        conn.close()
        st.dataframe(ledger_df, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# CORE MODULE: EXPENSE MANAGEMENT (RULE 3: MINIMALIST GRID & BLANK STATE)
# ------------------------------------------------------------------------------
elif current_action == "Expense Management":
    st.markdown(f"🔬 **Operating Expense Node ({current_company})**")
    
    e_tab1, e_tab2 = st.tabs(["Manual Provisioning", "Bulk Import Schema"])
    
    with e_tab1:
        cfg1, cfg2 = st.columns([3, 1.5])
        ex_date = cfg1.date_input("Provision Date:", datetime.now().date())
        ex_rows = cfg2.number_input("Grid Capacity Allocation:", min_value=1, max_value=20, value=5)
        
        categories_map = {
            "": [""],
            "ROI_Expences": ["", "Electricity_Bill", "Entertainment", "House_Rent", "Internet", "Bike_Maintain", "Repair", "Route_Cost", "Stationary", "Water_Bill", "Printing", "Financial_Expence", "Mobil_Change", "Salary", "bKash_Purpose", "Campaign", "Others"],
            "Expences": ["", "Entertainment", "Repair", "T.A", "Printing", "Campaign", "Cash_Pay", "Others"],
            "Merchant": ["", "Entertainment", "Repair", "T.A", "Printing", "Campaign", "Cash_Pay", "Stationary", "Others"]
        }
        
        st.markdown("<hr style='margin:10px 0px; border-color:#2d2d2d;'>", unsafe_allow_html=True)
        
        h1, h2, h3, h4 = st.columns([3, 3, 2, 4])
        h1.markdown("<small style='color:#888;'>Expense Type</small>", unsafe_allow_html=True)
        h2.markdown("<small style='color:#888;'>Expense Category</small>", unsafe_allow_html=True)
        h3.markdown("<small style='color:#888;'>Amount</small>", unsafe_allow_html=True)
        h4.markdown("<small style='color:#888;'>Remarks</small>", unsafe_allow_html=True)
        
        exp_entries = []
        for i in range(int(ex_rows)):
            c1, c2, c3, c4 = st.columns([3, 3, 2, 4])
            # Rule 3 Layout Alignment & Blank default setup
            e_type = c1.selectbox(f"ET_{i}", ["", "ROI_Expences", "Expences", "Merchant"], index=0, key=f"ext_{i}", label_visibility="collapsed")
            e_cat = c2.selectbox(f"EC_{i}", categories_map.get(e_type, [""]), index=0, key=f"exc_{i}", label_visibility="collapsed")
            e_amt = c3.number_input(f"EA_{i}", min_value=0.0, step=100.0, value=None, key=f"exa_{i}", label_visibility="collapsed")
            e_rem = c4.text_input(f"ER_{i}", value="", placeholder="Memo string...", key=f"exr_{i}", label_visibility="collapsed")
            exp_entries.append((e_type, e_cat, e_amt, e_rem))
            
        if st.button("COMMIT ALL OPERATIONAL EXPENSES", type="primary", use_container_width=True):
            conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
            for et, ec, ea, er in exp_entries:
                if et and ec and ea and ea > 0:
                    memo_str = f"[{et} -> {ec}] {er}".strip()
                    cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)",
                                   (str(ex_date), current_company, ea, memo_str))
            conn.commit(); conn.close()
            st.success("Operational metrics updated.")
            st.rerun()

    with e_tab2:
        up_exp = st.file_uploader("Upload Configuration File (*.xlsx)", type=["xlsx"], key="xl_exp")
        if up_exp:
            try:
                df = pd.read_excel(up_exp)
                st.dataframe(df.head(3), use_container_width=True)
                if st.button("PROCESS OPERATIONAL IMPORT RUN", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    for _, r in df.iterrows():
                        memo_str = f"[{r['expense_type']} -> {r['expense_category']}] {r.get('remarks','')}".strip()
                        cursor.execute("INSERT INTO cash_transactions (date, company, second_party, type, amount, remarks) VALUES (?, ?, 'Petty_Cash', 'Cash Out', ?, ?)",
                                       (str(r['date']).split(" ")[0], current_company, float(r['amount']), memo_str))
                    conn.commit(); conn.close()
                    st.success("Operation committed."); st.rerun()
            except Exception as e: st.error(str(e))

# ------------------------------------------------------------------------------
# EMPLOYEES: ADD PROFILE MODULE
# ------------------------------------------------------------------------------
elif current_action == "Add New Employee":
    st.markdown(f"🔬 **Human Resources Onboarding ({current_company})**")
    design_options = ["DM", "Supervisor", "SE", "ITBS", "Accountant", "Peon", "Other"] if current_company == "GP" else ["GM", "D&M", "F&A", "DCO", "DSS", "SR", "Other"]
    
    with st.form("emp_reg_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            emp_id = st.text_input("Employee ID *")
            name = st.text_input("Full Legal Name *")
            designation = st.selectbox("System Designation Tag", options=design_options)
            mobile = st.text_input("Primary Contact")
            alt_contact = st.text_input("Secondary Contact")
            emp_nid = st.text_input("National ID Reference")
            emp_img = st.file_uploader("Biometric Profile Photo Image", type=["png", "jpg", "jpeg"])
        with col2:
            join_date = st.date_input("Corporate Activation Date", datetime.now())
            basic_salary = st.number_input("Fixed Contract Component (Basic)", min_value=0.0, value=0.0)
            variable_salary = st.number_input("Variable KPI Component", min_value=0.0, value=0.0)
            
        if st.form_submit_button("PERSIST REGISTRATION ARCHIVE"):
            if not emp_id.strip() or not name.strip():
                st.error("Missing mandatory alphanumeric keys.")
            else:
                conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                cursor.execute("SELECT emp_id FROM employees WHERE emp_id=?", (emp_id.strip(),))
                if cursor.fetchone():
                    st.error("Key collision: Employee ID already structural in database.")
                else:
                    if emp_img:
                        Image.open(emp_img).save(os.path.join(PHOTO_DIR, f"{emp_id.strip()}_emp.png"))
                    t_sal = basic_salary + variable_salary
                    cursor.execute("""
                        INSERT INTO employees (emp_id, name, designation, mobile, alt_contact, join_date, basic_salary, variable_salary, total_salary, company)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (emp_id.strip(), name.strip(), designation, mobile.strip(), alt_contact.strip(), str(join_date), basic_salary, variable_salary, t_sal, current_company))
                    conn.commit(); conn.close()
                    st.success("HR Document generated.")

# ------------------------------------------------------------------------------
# EMPLOYEES: BULK UPLOAD MODULE
# ------------------------------------------------------------------------------
elif current_action == "Add Employee By Upload":
    st.markdown(f"🔬 **HR Batch Ingestion Process ({current_company})**")
    uploaded_file = st.file_uploader("Ingest Master Data Frame (*.xlsx)", type=["xlsx"])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            st.dataframe(df.head(5), use_container_width=True)
            if st.button("RUN RAW RECORD INSERTION ENGINE"):
                conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                for _, row in df.iterrows():
                    e_id = str(row.get('emp_id', '')).strip()
                    e_name = str(row.get('name', '')).strip()
                    if e_id and e_name:
                        bs = float(row.get('basic_salary', 0))
                        vs = float(row.get('variable_salary', 0))
                        cursor.execute("""
                            INSERT OR REPLACE INTO employees (emp_id, name, designation, mobile, join_date, basic_salary, variable_salary, total_salary, company)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (e_id, e_name, row.get('designation', 'SR'), str(row.get('mobile', '')), str(datetime.now().date()), bs, vs, bs+vs, current_company))
                conn.commit(); conn.close()
                st.success("Batch database operation concluded.")
        except Exception as e: st.error(f"Ingestion error: {e}")

# ------------------------------------------------------------------------------
# EMPLOYEES: DIRECTORY VIEW
# ------------------------------------------------------------------------------
elif current_action == "View All Employee":
    st.markdown(f"🔬 **Master HR Directory Registry ({current_company})**")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT emp_id as 'ID', name as 'Legal Name', designation as 'Designation', mobile as 'Contact No' FROM employees WHERE company=?", conn, params=(current_company,))
    conn.close()
    if df.empty:
        st.info("No query matches found in registry.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

# ------------------------------------------------------------------------------
# SECOND PARTY: PROVISION NEW ENTRY
# ------------------------------------------------------------------------------
elif current_action == "Add New Second Party":
    st.markdown(f"🔬 **Provision External Ledger Target ({current_company})**")
    with st.form("add_sp_form"):
        party_name = st.text_input("Unique Entity Name (English System String Keys Only) *")
        contact = st.text_input("Telemetry / Contact Reference")
        if st.form_submit_button("PERSIST ENTRY IN SYSTEM SCHEMA"):
            if not party_name.strip(): st.error("Key allocation error: String cannot be Null.")
            elif any(char >= '\u0980' and char <= '\u09ff' for char in party_name): st.error("Naming Policy Violation: Strict English constraint enforced.")
            else:
                try:
                    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
                    cursor.execute("INSERT INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status) VALUES (?, ?, ?, '', '', 'Active')",
                                   (current_company, party_name.strip(), contact.strip()))
                    conn.commit(); conn.close()
                    st.success("Entity integrated.")
                except sqlite3.IntegrityError: st.error("Unique constraint key violation. Entity exists.")

# ------------------------------------------------------------------------------
# SECOND PARTY: MATRIX VIEW
# ------------------------------------------------------------------------------
elif current_action == "View All Second Parties":
    st.markdown(f"🔬 **Counterparty Identity Index ({current_company})**")
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT id, party_name as 'Entity Key Identifier', contact_number as 'Routing Communication', status as 'Structural Status' FROM second_parties WHERE company=?", conn, params=(current_company,))
    conn.close()
    st.dataframe(df, use_container_width=True, hide_index=True)
