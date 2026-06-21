# ==============================================================================
# ১. ইম্পোর্ট এবং পেজ কনফিগারেশন
# ==============================================================================
import streamlit as st       # স্ট্রিমলিট ফ্রেমওয়ার্ক (ওয়েব অ্যাপ তৈরির জন্য)
import sqlite3               # লোকাল ডাটাবেজ ম্যানেজমেন্টের জন্য
import pandas as pd          # ডাটা প্রসেসিং এবং এক্সেল ফাইলের কাজ করার জন্য
from datetime import datetime # তারিখ ও সময় হ্যান্ডেল করার জন্য
import io                    # ফাইল ইনপুট-আউটপুট স্ট্রিম হ্যান্ডেল করতে
import os                    # ফাইল পাথ এবং ডিরেক্টরি চেক/تৈরি করার জন্য
import base64                # লোগো ইমেজকে বাইনারি থেকে টেক্সটে রূপান্তর করতে
from PIL import Image        # ইমেজ ফাইল প্রসেস এবং সেভ করার জন্য

# স্ট্রিমলিট অ্যাপের টাইটেল, লেআউট এবং সাইডবারের ডিফল্ট অবস্থা সেট করা
st.set_page_config(page_title="M/S Jabed Enterprise", layout="wide", initial_sidebar_state="expanded")

# ==============================================================================
# ২. লগইন সিস্টেম (সুরক্ষার জন্য রোল-বেসড অ্যাক্সেসসহ)
# ==============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None

if not st.session_state.logged_in:
    st.title("🔐 M/S Jabed Enterprise - Login System")
    username = st.text_input("ইউজারনেম (Username)")
    password = st.text_input("পাসওয়ার্ড (Password)", type="password")
    
    if st.button("লগইন করুন"):
        if username == "admin" and password == "admin123":
            st.session_state.logged_in = True
            st.session_state.user_role = "Admin"
            st.success("🎉 সফলভাবে অ্যাডমিন হিসেবে লগইন হয়েছে!")
            st.rerun()
        elif username == "manager" and password == "manager123":
            st.session_state.logged_in = True
            st.session_state.user_role = "Manager"
            st.success("🎉 সফলভাবে ম্যানেজার হিসেবে লগইন হয়েছে!")
            st.rerun()
        else:
            st.error("❌ ভুল ইউজারনেম অথবা পাসওয়ার্ড! আবার চেষ্টা করুন।")
    st.stop()

# ==============================================================================
# ৩. ডাটাবেজ ইনিশিয়ালিজেশন ও স্বয়ংক্রিয় কলাম আপগ্রেডেশন (Auto-Migration)
# ==============================================================================
DB_FILE = "emp_management.db"

def init_db():
    """ডাটাবেজ কানেক্ট করা, টেবিল তৈরি করা এবং কলাম মিসিং থাকলে তা অটো অ্যাড করা"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # ১. কর্মচারীদের মূল তথ্য টেবিল (বাগ ফিক্সড: সিনট্যাক্স ঠিক করা হয়েছে)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            emp_id TEXT PRIMARY KEY,
            name TEXT,
            designation TEXT,
            mobile TEXT,
            company TEXT,
            basic_salary REAL DEFAULT 0.0,
            variable_salary REAL DEFAULT 0.0,
            total_salary REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Active'
        )
    ''')
    
    # ২. ডেইলি ক্যাশ বুক (টাকা জমা-খরচের খাতা) টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_cash_book (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            company TEXT,
            op_vault REAL DEFAULT 0.0,
            op_bank REAL DEFAULT 0.0,
            op_advance REAL DEFAULT 0.0,
            op_due REAL DEFAULT 0.0,
            cl_vault REAL DEFAULT 0.0,
            cl_bank REAL DEFAULT 0.0,
            cl_advance REAL DEFAULT 0.0,
            cl_due REAL DEFAULT 0.0,
            total_opening REAL DEFAULT 0.0,
            total_closing REAL DEFAULT 0.0,
            daily_receive REAL DEFAULT 0.0,
            daily_expense REAL DEFAULT 0.0,
            grand_total_receive REAL DEFAULT 0.0,
            grand_total_expense REAL DEFAULT 0.0,
            final_net_balance REAL DEFAULT 0.0,
            status TEXT DEFAULT 'Pending'
        )
    ''')

    # ৩. বিвиди বা ফুটকর খরচ ট্র্যাকিং টেবিল
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS general_expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            company TEXT,
            expense_type TEXT,
            description TEXT,
            amount REAL DEFAULT 0.0
        )
    ''')
    conn.commit()

    # 🛠️ স্বয়ংক্রিয় স্ট্রাকচার রিফেয়ারিং লজিক (কলাম মাইগ্রেশন)
    required_cols = {
        'basic_salary': "REAL DEFAULT 0.0",
        'variable_salary': "REAL DEFAULT 0.0",
        'total_salary': "REAL DEFAULT 0.0",
        'status': "TEXT DEFAULT 'Active'"
    }
    
    cursor.execute("PRAGMA table_info(employees)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    
    for col_name, col_type in required_cols.items():
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE employees ADD COLUMN {col_name} {col_type};")
                conn.commit()
            except Exception:
                pass
                
    conn.close()

init_db()

def get_db_connection():
    """ডাটাবেজের সাথে সচল কানেকশন রিটার্ন করা"""
    return sqlite3.connect(DB_FILE)

# ==============================================================================
# ৪. গ্লোবাল সেশন স্টেট এবং নেভিগেশন ভেরিয়েবল কন্ট্রোল
# ==============================================================================
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Dashboard"
if 'current_company' not in st.session_state:
    st.session_state.current_company = "M/S Jabed Enterprise"
if 'active_emp_id' not in st.session_state:
    st.session_state.active_emp_id = None
if 'active_party_id' not in st.session_state:
    st.session_state.active_party_id = None

# ==============================================================================
# ৫. কাস্টম গ্লোবাল CSS ডিজাইন স্পেসিং এবং রিল্যাক্সড ক্যাশ বুক লেআউট
# ==============================================================================
st.markdown("""
<style>
    /* ১. গ্লোবাল ইনপুট বক্সের প্যাডিং সামান্য কমিয়ে স্লিম কিন্তু সুন্দর লুক দেওয়া */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        padding-top: 4px !important;
        padding-bottom: 4px !important;
        height: 32px !important;
    }
    
    /* ২. গ্লোবাল ব্লগ স্পেসিং ডিফল্ট ১৬px থেকে কমিয়ে ১০px করা (যাতে খুব ঠাসাঠাসি না লাগে) */
    div[data-testid="stVerticalBlock"] {
        gap: 0.6rem !important; 
    }
    
    /* ৩. ক্যাশ বুক রো স্পেসিং কন্ট্রোল (মিশে যাওয়া রোধ করতে comfortable gap নির্ধারণ) */
    div[data-testid="stHorizontalBlock"] {
        margin-top: 2px !important;
        margin-bottom: 2px !important;
        padding-top: 1px !important;
        padding-bottom: 1px !important;
    }

    /* ৪. ক্যাশ বুকের ইনপুট এবং টেক্সট লাইনের উচ্চতা ৩২px এ লক করা যাতে মিশে না যায় */
    .meta-label-vertical, .meta-value-vertical, 
    .summary-label-vertical, .summary-value-vertical {
        min-height: 32px !important;
        height: 32px !important;
        display: flex;
        align-items: center;
        margin: 0 !important;
        padding: 0 !important;
        font-size: 14px !important;
    }
    .meta-value-vertical, .summary-value-vertical {
        justify-content: flex-end;
    }

    /* ৫. হেডার স্টাইলিং */
    .hdr-green {
        background-color: #0d5c3a; color: #00ffaa; padding: 6px; 
        font-weight: bold; text-align: center; border-radius: 4px; margin-bottom: 4px;
    }
    .hdr-red {
        background-color: #631c1c; color: #ff5555; padding: 6px; 
        font-weight: bold; text-align: center; border-radius: 4px; margin-bottom: 4px;
    }
    .folder-lbl {
        font-weight: bold; color: #e0e0e0; font-size: 14px; margin-top: 4px;
    }
    .meta-hr {
        margin-top: 4px !important; margin-bottom: 4px !important; border: 0.5px solid #444 !important;
    }
</style>
""", unsafe_allow_html=True)

def render_header():
    """কোম্পানির নাম এবং ঠিকানার মাঝের গ্যাপ কমিয়ে দৃষ্টিনন্দন হেডার প্রদর্শন"""
    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 0px; padding-bottom: 0px;">
            <h1 style="margin: 0; color: #00ffaa; font-size: 28px;">{st.session_state.current_company}</h1>
            <p style="color: #a0a0a0; margin: 2px 0 0 0; font-size: 14px;">হিসাব ব্যবস্থাপনা ও ডায়েরি সিস্টেম</p>
        </div>
        <hr style="margin-top: 6px; margin-bottom: 12px; border: 0.5px solid #333;">
    """, unsafe_allow_html=True)

# ==============================================================================
# ৬. সাইডবার নেভিগেশন এবং কন্ট্রোল প্যানেল
# ==============================================================================
with st.sidebar:
    st.markdown("### 🏢 কোম্পানি সিলেক্ট করুন")
    company_options = ["M/S Jabed Enterprise", "M/S Al-Modina Enterprise", "M/S J.E Auto Bricks"]
    selected_comp = st.selectbox("চলতি কোম্পানি:", company_options, index=company_options.index(st.session_state.current_company))
    if selected_comp != st.session_state.current_company:
        st.session_state.current_company = selected_comp
        st.rerun()
        
    st.markdown("---")
    st.markdown("### 🧭 মেনু নেভিগেশন")
    
    if st.button("📊 ড্যাশবোর্ড ওভারভিউ", use_container_width=True):
        st.session_state.current_page = "Dashboard"
    if st.button("👥 कर्मचारी বা স্টাফ ম্যানেজমেন্ট", use_container_width=True):
        st.session_state.current_page = "Employee Management"
    if st.button("📖 দৈনিক জমা-খরচের খাতা", use_container_width=True):
        st.session_state.current_page = "Daily Cash Book"
    if st.button("📁 বিবিধ বা অন্যান্য অ্যাকাউন্ট", use_container_width=True):
        st.session_state.current_page = "Others"
        
    st.markdown("---")
    st.write(f"👤 রোল: **{st.session_state.user_role}**")
    if st.button("🚪 লগআউট করুন", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = None
        st.rerun()

# কারেন্ট পেজ ভ্যারিয়েবল সেট করা
current_page = st.session_state.current_page
current_company = st.session_state.current_company

# ==============================================================================
# 📊 ড্যাশবোর্ড ওভারভিউ মডিউল
# ==============================================================================
if current_page == "Dashboard":
    render_header()
    st.subheader("📊 ড্যাশবোর্ড ওভারভিউ")
    
    conn = get_db_connection()
    total_emp = pd.read_sql_query("SELECT COUNT(*) FROM employees WHERE company=? AND status='Active'", conn, params=(current_company,)).iloc[0,0]
    total_exp = pd.read_sql_query("SELECT SUM(amount) FROM general_expenses WHERE company=?", conn, params=(current_company,)).iloc[0,0] or 0.0
    conn.close()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("👥 একটিভ স্টাফ সংখ্যা", f"{total_emp} জন")
    m2.metric("📉 মোট বিবিধ খরচ", f"{total_exp:,.2f} ৳")
    m3.metric("🏢 বর্তমান সিলেক্টেড ফার্ম", current_company.split(" ")[1])

# ==============================================================================
# 👥 কর্মচারী বা স্টাফ ম্যানেজমেন্ট মডিউল
# ==============================================================================
elif current_page == "Employee Management":
    render_header()
    st.subheader("👥 কর্মচারী বা স্টাফ ম্যানেজমেন্ট")
    
    emp_action = st.tabs(["👥 কর্মচারীদের তালিকা", "➕ নতুন কর্মচারী যোগ", "📤 এক্সেল বাল্ক আপলোড"])
    
    # ট্যাব ১: স্টাফ তালিকা দর্শন
    with emp_action[0]:
        conn = get_db_connection()
        try:
            df = pd.read_sql_query(
                "SELECT emp_id as 'ID', name as 'নাম', designation as 'পদবী', mobile as 'মোবাইল', total_salary as 'মোট বেতন (৳)' FROM employees WHERE company=? AND status='Active'", 
                conn, params=(current_company,)
            )
            if not df.empty:
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("বর্তমানে কোনো স্টাফের তথ্য পাওয়া যায়নি।")
        except Exception as e:
            st.error(f"🔴 ডাটাবেজ ট্র্যাকিং এরর: {e}")
        finally:
            conn.close()
            
    # ট্যাব ২: একজন নতুন কর্মী ম্যানুয়াল যোগ
    with emp_action[1]:
        with st.form("add_emp_form", clear_on_submit=True):
            e_id = st.text_input("স্টাফ আইডি (ID) *")
            e_name = st.text_input("স্টাফের নাম (Name) *")
            e_des = st.text_input("পদবী (Designation)")
            e_mob = st.text_input("মোবাইল নম্বর")
            b_sal = st.number_input("মূল বেতন (Basic Salary)", min_value=0.0, step=500.0)
            v_sal = st.number_input("ভেরিয়েবল বেতন (Variable Salary)", min_value=0.0, step=500.0)
            
            if st.form_submit_button("💾 কর্মচারী তথ্য সংরক্ষণ করুন"):
                if e_id and e_name:
                    t_sal = b_sal + v_sal  # টোটাল স্যালারি হিসাব নির্ধারণ
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO employees (emp_id, name, designation, mobile, company, basic_salary, variable_salary, total_salary, status) VALUES (?,?,?,?,?,?,?,?,'Active')",
                            (e_id, e_name, e_des, e_mob, current_company, b_sal, v_sal, t_sal)
                        )
                        conn.commit()
                        st.success(f"🎉 {e_name} সফলভাবে ডাটাবেজে যুক্ত হয়েছেন!")
                    except sqlite3.IntegrityError:
                        st.error("❌ এই স্টাফ আইডিটি ইতিমধ্যে ডাটাবেজে বিদ্যমান!")
                    finally:
                        conn.close()
                else:
                    st.warning("⚠️ দয়া করে আইডি এবং নাম ফিল্ড দুটি অবশ্যই পূরণ করুন।")
                    
    # ট্যাব ৩: এক্সেল ডাটা বাল্ক ইম্পোর্ট ফিক্স
    with emp_action[2]:
        st.markdown("### 📤 এক্সেল ফাইল থেকে বাল্ক আপলোড")
        uploaded_file = st.file_uploader("এক্সেল (.xlsx) ফাইল সিলেক্ট করুন", type=["xlsx"])
        if uploaded_file is not None:
            try:
                excel_df = pd.read_excel(uploaded_file)
                st.write("📋 ফাইলের ভেতরের তথ্য বা প্রিভিউ:")
                st.dataframe(excel_df.head(), use_container_width=True)
                
                if st.button("🚀 ডাটাবেজে ইম্পোর্ট সম্পন্ন করুন"):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    success_count = 0
                    
                    for index, row in excel_df.iterrows():
                        # এক্সেল রো থেকে ডাটা প্রসেস এবং কলাম সেফগার্ড লজিক
                        e_id = str(row.get('ID', '')).strip()
                        e_name = str(row.get('নাম', '')).strip()
                        e_des = str(row.get('পদবী', ''))
                        e_mob = str(row.get('মোবাইল', ''))
                        b_sal = float(row.get('মূল বেতন', 0.0))
                        v_sal = float(row.get('ভেরিয়েবল বেতন', 0.0))
                        t_sal = b_sal + v_sal
                        
                        if e_id and e_name and e_id != "nan" and e_name != "nan":
                            try:
                                cursor.execute(
                                    "INSERT OR REPLACE INTO employees (emp_id, name, designation, mobile, company, basic_salary, variable_salary, total_salary, status) VALUES (?,?,?,?,?,?,?,?,'Active')",
                                    (e_id, e_name, e_des, e_mob, current_company, b_sal, v_sal, t_sal)
                                )
                                success_count += 1
                            except Exception:
                                pass
                    conn.commit()
                    conn.close()
                    st.success(f"🎉 সফলভাবে এক্সেল থেকে {success_count} জন স্টাফের ডাটা ইনসার্ট হয়েছে!")
            except Exception as e:
                st.error(f"❌ এক্সেল ফাইলটি পড়তে সমস্যা হয়েছে: {e}")

# ==============================================================================
# 📖 দৈনিক জমা-খরচের খাতা মডিউল (রিল্যাক্সড ডিজাইন স্পেসেড)
# ==============================================================================
elif current_page == "Daily Cash Book":
    render_header()
    st.subheader("📖 দৈনিক জমা-খরচের ক্যাশ বুক")
    
    # ডামি ডাটাবেজ মান লোড লজিক (বাস্তব ক্ষেত্রে ডাটাবেজ থেকে কুয়েরি হবে)
    op_vault_val, op_bank_val, op_adv_val, op_due_val = 25000.0, 145000.0, 35000.0, 12000.0
    total_opening_calc = op_vault_val + op_bank_val + op_adv_val + op_due_val

    # ─── [ধাপ ১] প্রধান হেডার অংশ (মার্জিন অ্যাডজাস্টেড) ───
    main_col1, main_col2 = st.columns(2)
    with main_col1:
        st.markdown("""
            <div class="hdr-green" style="margin-bottom: 0px !important;">🛸 CASH RECEIVE (জমা)</div>
            <div class="folder-lbl" style="margin-top: 4px !important; margin-bottom: 2px !important;">📁 Opening Cash (অটোমেটিক পূর্বের ব্যালেন্স):</div>
        """, unsafe_allow_html=True)
    with main_col2:
        st.markdown("""
            <div class="hdr-red" style="margin-bottom: 0px !important;">🛸 PAY OUT (খরচ/প্রদান)</div>
            <div class="folder-lbl" style="margin-top: 4px !important; margin-bottom: 2px !important;">📁 Closing Balances (ম্যানুয়াল এন্ট্রি):</div>
        """, unsafe_allow_html=True)

    # ─── [ধাপ ২] রো ১: Vault Cash এলাইনমেন্ট (Comfortable Spacing) ───
    row1_col1, row1_col2 = st.columns(2)
    with row1_col1:
        l_r1_c1, l_r1_c2 = st.columns([7, 5])
        l_r1_c1.markdown('<div class="meta-label-vertical">Opening Vault Cash:</div>', unsafe_allow_html=True)
        l_r1_c2.markdown(f'<div class="meta-value-vertical">{op_vault_val:,.2f} ৳</div>', unsafe_allow_html=True)
    with row1_col2:
        r_r1_c1, r_r1_c2 = st.columns([7, 5])
        r_r1_c1.markdown('<div class="meta-label-vertical">Vault Cash:</div>', unsafe_allow_html=True)
        placeholder_vault_cash_text = r_r1_c2.empty()

    # ─── [ধাপ ৩] রো ২: DM & DSS Bank এলাইনমেন্ট ───
    row2_col1, row2_col2 = st.columns(2)
    with row2_col1:
        l_r2_c1, l_r2_c2 = st.columns([7, 5])
        l_r2_c1.markdown('<div class="meta-label-vertical">DM & DSS Bank:</div>', unsafe_allow_html=True)
        l_r2_c2.markdown(f'<div class="meta-value-vertical">{op_bank_val:,.2f} ৳</div>', unsafe_allow_html=True)
    with row2_col2:
        r_r2_c1, r_r2_c2 = st.columns([7, 5])
        r_r2_c1.markdown('<div class="meta-label-vertical">DM & DSS Bank:</div>', unsafe_allow_html=True)
        m_bank = r_r2_c2.number_input("", min_value=0.0, step=1.0, key="m_inp_bank", label_visibility="collapsed")

    # ─── [ধাপ ৪] রো ৩: Market Advance এলাইনমেন্ট ───
    row3_col1, row3_col2 = st.columns(2)
    with row3_col1:
        l_r3_c1, l_r3_c2 = st.columns([7, 5])
        l_r3_c1.markdown('<div class="meta-label-vertical">Market Advance:</div>', unsafe_allow_html=True)
        l_r3_c2.markdown(f'<div class="meta-value-vertical">{op_adv_val:,.2f} ৳</div>', unsafe_allow_html=True)
    with row3_col2:
        r_r3_c1, r_r3_c2 = st.columns([7, 5])
        r_r3_c1.markdown('<div class="meta-label-vertical">Market Advance:</div>', unsafe_allow_html=True)
        m_advance = r_r3_c2.number_input("", min_value=0.0, step=1.0, key="m_inp_advance", label_visibility="collapsed")

    # ─── [ধাপ ৫] রো ৪: Others Due এলাইনমেন্ট ───
    row4_col1, row4_col2 = st.columns(2)
    with row4_col1:
        l_r4_c1, l_r4_c2 = st.columns([7, 5])
        l_r4_c1.markdown('<div class="meta-label-vertical">Others Due:</div>', unsafe_allow_html=True)
        l_r4_c2.markdown(f'<div class="meta-value-vertical">{op_due_val:,.2f} ৳</div>', unsafe_allow_html=True)
    with row4_col2:
        r_r4_c1, r_r4_c2 = st.columns([7, 5])
        r_r4_c1.markdown('<div class="meta-label-vertical">Others Due:</div>', unsafe_allow_html=True)
        m_due = r_r4_c2.number_input("", min_value=0.0, step=1.0, key="m_inp_due", label_visibility="collapsed")

    # ─── [ধাপ ৬] অনুভূমিক ডিভাইডার রেখা ───
    hr_col1, hr_col2 = st.columns(2)
    with hr_col1: st.markdown('<hr class="meta-hr">', unsafe_allow_html=True)
    with hr_col2: st.markdown('<hr class="meta-hr">', unsafe_allow_html=True)

    # ─── [ধাপ ৭] রো ৫: Total Opening & Closing ───
    row5_col1, row5_col2 = st.columns(2)
    with row5_col1:
        l_r5_c1, l_r5_c2 = st.columns([7, 5])
        l_r5_c1.markdown('<div class="summary-label-vertical" style="color:#00ffaa; font-weight:bold;">Total Opening Cash:</div>', unsafe_allow_html=True)
        l_r5_c2.markdown(f'<div class="summary-value-vertical" style="color:#00ffaa; font-weight:bold;">{total_opening_calc:,.2f} ৳</div>', unsafe_allow_html=True)
    with row5_col2:
        r_r5_c1, r_r5_c2 = st.columns([7, 5])
        r_r5_c1.markdown('<div class="summary-label-vertical" style="color:#ff5555; font-weight:bold;">Total Closing Cash:</div>', unsafe_allow_html=True)
        placeholder_total_closing_text = r_r5_c2.empty()

    # ─── [ধাপ ৮] লাইভ গ্র্যান্ড সামারি কন্টেইনার হোল্ডার ───
    row6_col1, row6_col2 = st.columns(2)
    with row6_col1: placeholder_left_summary = st.empty()
    with row6_col2: placeholder_right_summary = st.empty()

    # প্লেসহোল্ডার ডেটা রেন্ডারিং
    placeholder_vault_cash_text.markdown('<div class="meta-value-vertical">0.00 ৳</div>', unsafe_allow_html=True)
    placeholder_total_closing_text.markdown('<div class="summary-value-vertical" style="color:#ff5555; font-weight:bold;">0.00 ৳</div>', unsafe_allow_html=True)

# ==============================================================================
# 📁 বিবিধ বা অন্যান্য অ্যাকাউন্ট ম্যানেজমেন্ট মডিউল
# ==============================================================================
elif current_page == "Others":
    render_header()
    st.subheader(f"📁 Others Account Management ({current_company})")
    
    with st.form("others_exp_form", clear_on_submit=True):
        st.markdown("##### 📉 সাধারণ বা বিবিধ খরচ এন্ট্রি")
        exp_type = st.selectbox("খরচের খাত:", ["অফিস খরচ", "পরিবহন বিল", "আপ্যায়ন", "অন্যান্য"])
        exp_desc = st.text_area("খরচের বিস্তারিত বিবরণ")
        exp_amount = st.number_input("টাকার পরিমাণ (৳)", min_value=0.0, step=10.0)
        
        if st.form_submit_button("📥 খরচ নথিভুক্ত করুন"):
            if exp_amount > 0:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO general_expenses (date, company, expense_type, description, amount) VALUES (?,?,?,?,?)",
                    (datetime.now().strftime("%Y-%m-%d"), current_company, exp_type, exp_desc, exp_amount)
                )
                conn.commit()
                conn.close()
                st.success("🎉 খরচের তথ্যটি ডাটাবেজে সফলভাবে সেভ হয়েছে!")
            else:
                st.warning("⚠️ টাকার পরিমাণ শূন্য থেকে বেশি হতে হবে।")
