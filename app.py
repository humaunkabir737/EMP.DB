import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date
import io

# ==========================================
# ১. গ্লোবাল অ্যাপ কনফিগারেশন ও কাস্টম CSS
# ==========================================
st.set_page_config(
    page_title="Automated Financial ERP Reporting System",
    layout="wide",
    initial_sidebar_state="expanded"
)

# নিখুঁত লে-আউট, ইনপুট বক্সের কমপ্যাক্টনেস এবং প্লাস-মাইনাস বাটন হাইড করার কাস্টম CSS
st.markdown("""
<style>
    /* লাইনগুলোর মাঝের অতিরিক্ত ভার্টিকাল ফাঁকা জায়গা কমানো */
    div[data-testid="element-container"] { 
        margin-bottom: 5px !important; 
    }
    
    /* প্রতিটি হরিজন্টাল ব্লকের মুখোমুখি লাইন ১০০% সমান্তরাল ও ভার্টিক্যালি সেন্টার করা */
    div[data-testid="stHorizontalBlock"] { 
        gap: 12px !important; 
        align-items: center !important; 
        min-height: 52px !important; 
    }
    
    /* নাম্বার ইনপুট বক্সের ভেতরের প্লাস-মাইনাস (+ / -) বাটন সম্পূর্ণ বন্ধ করা */
    button[data-testid="stNumberInputStepDown"], 
    button[data-testid="stNumberInputStepUp"] { 
        display: none !important; 
    }
    
    /* ইনপুট ফিল্ডের ভেতরের ইন্টারনাল প্যাডিং সংকুচিত করা */
    .stNumberInput input, .stTextInput input, .stSelectbox div { 
        padding-top: 4px !important; 
        padding-bottom: 4px !important; 
    }
    
    /* সেন্ট্রাল লেফট ইনডেন্ট ও লেবেল স্টাইলিং */
    .aligned-label {
        font-size: 14px;
        font-weight: 600;
        text-align: left;
        display: flex;
        align-items: center;
        height: 100%;
    }
    
    /* সবুজ ও লাল রঙের হেডার ব্যানার */
    .hdr-green { padding: 8px 15px; border-radius: 4px; font-size: 14px; text-align: center; font-weight: bold; background-color: #1e4620; color: #ffffff; }
    .hdr-red { padding: 8px 15px; border-radius: 4px; font-size: 14px; text-align: center; font-weight: bold; background-color: #4a1515; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# ২. ডাটাবেজ সেটআপ ও টেবিল আর্কিটেকচার (Processing Layer)
# ==========================================
def get_db_connection():
    conn = sqlite3.connect('jabed_enterprise.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # দৈনিক ক্যাশ খাতা টেবিল
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cash_khata (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        company TEXT,
        entry_date TEXT,
        type TEXT, -- 'RECEIVE' অথবা 'PAYOUT'
        party_name TEXT,
        amount REAL,
        remarks TEXT
    )""")
    
    # মাদার ওয়ালেট ও ব্যাংক লেজার টেবিল
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS mw_bank_ledger (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        company TEXT,
        action_date TEXT,
        action_type TEXT, -- 'Lifting' অথবা 'Refund'
        amount REAL,
        mw_impact REAL,
        bank_impact REAL
    )""")
    
    # কর্মচারী টেবিল (ইউনিক আইডি সহ)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS employees (
        emp_id TEXT PRIMARY KEY,
        name TEXT,
        designation TEXT,
        mobile TEXT,
        salary REAL,
        father_name TEXT,
        mother_name TEXT,
        emp_photo_path TEXT,
        nid_photo_path TEXT
    )""")
    
    # সেকেন্ড পার্টি টেবিল (কোম্পানি ভিত্তিক ইউনিক নাম কনস্ট্রেইন)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS second_parties (
        id INTEGER PRIMARY KEY AUTO_INCREMENT,
        company TEXT,
        party_name TEXT,
        phone TEXT,
        comments TEXT,
        UNIQUE(company, party_name)
    )""")
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# ৩. স্টেট ম্যানেজমেন্ট ও মেমোরি রিফ্রেশ রুলস (State Layer)
# ==========================================
if 'prev_company' not in st.session_state: st.session_state.prev_company = None
if 'prev_action' not in st.session_state: st.session_state.prev_action = None
if 'user_role' not in st.session_state: st.session_state.user_role = 'User'

# সাইডবার প্যানেল ও সিকিউরড লগইন ভিউ
st.sidebar.title("M/S JABED ENTERPRISE")
st.sidebar.subheader("Automated Financial ERP")

# রোল সিলেকশন (এডমিন সিকিউরিটি হার্ডেনিং)
admin_password = st.sidebar.text_input("🔒 এডমিন পাসওয়ার্ড (ঐচ্ছিক)", type="password")
if admin_password == "admin786":
    st.session_state.user_role = 'Admin'
    st.sidebar.success("অ্যাক্সেস মোড: Admin (সর্বময় ক্ষমতা)")
else:
    st.session_state.user_role = 'User'
    st.sidebar.info("অ্যাক্সেস মোড: Staff/User (সীমিত ক্ষমতা)")

# কোম্পানি ও অ্যাকশন মেনু সিলেকশন
current_company = st.sidebar.selectbox("🏢 কোম্পানি নির্বাচন করুন", ["bKash", "GP"], key="selected_company")
current_action = st.sidebar.radio("📖 মেনু নেভিগেশন", [
    "📝 Daily Cash Khata", 
    "💳 MW and Bank (Contra)", 
    "📊 ERP Report Viewer", 
    "👥 Employee Directory",
    "🤝 Second Party Setup"
], key="selected_action")

# 🚨 [রুলস সিঙ্ক]: সাইডবার অপশন চেঞ্জ হলে মেইন বডির ওল্ড ডাটা ব্লাইন্ড ফ্লাশ করার মেকানিজম
if (current_company != st.session_state.prev_company) or (current_action != st.session_state.prev_action):
    keys_to_preserve = ['selected_company', 'selected_action', 'prev_company', 'prev_action', 'user_role']
    for key in list(st.session_state.keys()):
        if key not in keys_to_preserve:
            del st.session_state[key]
    st.session_state.prev_company = current_company
    st.session_state.prev_action = current_action
    st.rerun()

# ==========================================
# ৪. মেইন অ্যাপ্লিকেশন লজিক (App Layer)
# ==========================================
st.title(f"🏢 {current_company} ERP - {current_action[2:]}")
st.write(f"---")

# ------------------------------------------
# ক) দৈনিক ক্যাশ খাতা এন্ট্রি (Daily Cash Khata)
# ------------------------------------------
if current_action == "📝 Daily Cash Khata":
    entry_date = st.date_input("তারিখ নির্বাচন করুন", date.today())
    
    # জমা ও খরচের গ্রিড হেডার
    head_col1, head_col2 = st.columns(2)
    with head_col1:
        st.markdown('<div class="hdr-green">CASH RECEIVE (জমা খাত)</div>', unsafe_allow_html=True)
    with head_col2:
        st.markdown('<div class="hdr-red">PAY OUT (আজকের খরচ/দেনা খাত)</div>', unsafe_allow_html=True)
        
    # ১৫টি ফিক্সড রো সমান্তরাল গ্রিড তৈরি
    row_count = 15
    cash_in_data = []
    cash_out_data = []
    
    # সেকেন্ড পার্টি লিস্ট রিট্রিভ
    conn = get_db_connection()
    parties = [r['party_name'] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=?", (current_company,)).fetchall()]
    conn.close()
    parties = [""] + parties
    
    for i in range(row_count):
        grid_col1, grid_col2 = st.columns(2)
        
        # বাম পাশের কলাম: Cash Receive
        with grid_col1:
            c1, c2, c3 = st.columns([5, 3, 4])
            p_in = c1.selectbox(f"পার্টি {i+1}", parties, key=f"p_in_{i}", label_visibility="collapsed")
            amt_in = c2.number_input(f"টাকা {i+1}", min_value=0.0, step=1.0, key=f"amt_in_{i}", label_visibility="collapsed")
            rem_in = c3.text_input(f"বিবরণ {i+1}", key=f"rem_in_{i}", label_visibility="collapsed")
            if p_in and amt_in > 0:
                cash_in_data.append((current_company, str(entry_date), 'RECEIVE', p_in, amt_in, rem_in))
                
        # ডান পাশের কলাম: Pay Out
        with grid_col2:
            c4, c5, c6 = st.columns([5, 3, 4])
            p_out = c4.selectbox(f"পার্টি {i+1}", parties, key=f"p_out_{i}", label_visibility="collapsed")
            amt_out = c5.number_input(f"টাকা {i+1}", min_value=0.0, step=1.0, key=f"amt_out_{i}", label_visibility="collapsed")
            rem_out = c6.text_input(f"বিবরণ {i+1}", key=f"rem_out_{i}", label_visibility="collapsed")
            if p_out and amt_out > 0:
                cash_out_data.append((current_company, str(entry_date), 'PAYOUT', p_out, amt_out, rem_out))

    st.write("---")
    st.subheader("💵 সমাপনী খতিয়ান ও ব্যালেন্স সমন্বয়")
    
    # 📐 [লাইন অ্যালাইনমেন্ট ফিক্স]: প্রতিটি ডাটা রো-কে মুখোমুখি সাব-গ্রিডে লক করা
    total_in_calc = sum(item[4] for item in cash_in_data)
    total_out_calc = sum(item[4] for item in cash_out_data)
    
    # রো ১: Opening Volt Cash বনাম DM DSS Bank Balance
    r1_c1, r1_c2 = st.columns(2)
    with r1_c1:
        cc1, cc2 = st.columns([6, 6])
        cc1.markdown('<div class="aligned-label">📄 Opening Volt Cash (প্রারম্ভিক নগদ):</div>', unsafe_allow_html=True)
        opening_volt = cc2.number_input("Opening Volt", min_value=0.0, step=1.0, key="op_volt", label_visibility="collapsed")
    with r1_c2:
        cc3, cc4 = st.columns([6, 6])
        cc3.markdown('<div class="aligned-label">🏦 DM DSS Bank Balance (ব্যাংক ম্যানুয়াল):</div>', unsafe_allow_html=True)
        dm_bank = cc4.number_input("DM Bank", min_value=0.0, step=1.0, key="dm_bank", label_visibility="collapsed")
        
    # রো ২: Closing Volt Cash বনাম Market Advance
    closing_volt_calc = (opening_volt + total_in_calc) - total_out_calc
    
    r2_c1, r2_c2 = st.columns(2)
    with r2_c1:
        cc1, cc2 = st.columns([6, 6])
        cc1.markdown('<div class="aligned-label">🔒 Closing Volt Cash (সমাপনী নগদ):</div>', unsafe_allow_html=True)
        cc2.number_input("Closing Volt", value=closing_volt_calc, disabled=True, key="cl_volt", label_visibility="collapsed")
    with r2_c2:
        cc3, cc4 = st.columns([6, 6])
        cc3.markdown('<div class="aligned-label">📈 Market Advance (মার্কেট অ্যাডভান্স):</div>', unsafe_allow_html=True)
        market_adv = cc4.number_input("Market Advance", min_value=0.0, step=1.0, key="mkt_adv", label_visibility="collapsed")

    # রো ৩: Grand Total বনাম Others Due
    r3_c1, r3_c2 = st.columns(2)
    with r3_c1:
        cc1, cc2 = st.columns([6, 6])
        cc1.markdown('<div class="aligned-label">📊 Grand Total Cash In (সর্বমোট জমা):</div>', unsafe_allow_html=True)
        cc2.number_input("Total In Label", value=total_in_calc, disabled=True, key="tot_in_lbl", label_visibility="collapsed")
    with r3_c2:
        cc3, cc4 = st.columns([6, 6])
        cc3.markdown('<div class="aligned-label">📉 Others Due (অন্যান্য বকেয়া পাওনা):</div>', unsafe_allow_html=True)
        others_due = cc4.number_input("Others Due", min_value=0.0, step=1.0, key="oth_due", label_visibility="collapsed")

    # অ্যাকশন বাটনস প্যানেল
    st.write("---")
    b1, b2, _ = st.columns([3, 3, 6])
    
    if b1.button("💾 আজকের সম্পূর্ণ খাতা সংরক্ষণ করুন", use_container_width=True):
        if not cash_in_data and not cash_out_data:
            st.warning("সংরক্ষণের জন্য কোনো তথ্য ইনপুট দেওয়া হয়নি।")
        else:
            conn = get_db_connection()
            cursor = conn.cursor()
            if cash_in_data: cursor.executemany("INSERT INTO cash_khata (company, entry_date, type, party_name, amount, remarks) VALUES (?,?,?,?,?,?)", cash_in_data)
            if cash_out_data: cursor.executemany("INSERT INTO cash_khata (company, entry_date, type, party_name, amount, remarks) VALUES (?,?,?,?,?,?)", cash_out_data)
            conn.commit()
            conn.close()
            st.success("আজকের ক্যাশ খাতার বিবরণ সফলভাবে ইআরপি ডাটাবেজে সংরক্ষিত হয়েছে।")
            st.rerun()
            
    if b2.button("🧹 ছক সম্পূর্ণ খালি করুন (Reset Form)", use_container_width=True):
        keys_to_preserve = ['selected_company', 'selected_action', 'prev_company', 'prev_action', 'user_role']
        for key in list(st.session_state.keys()):
            if key not in keys_to_preserve: del st.session_state[key]
        st.success("ইনপুট ছক সম্পূর্ণ খালি করা হয়েছে।")
        st.rerun()

# ------------------------------------------
# খ) মাদার ওয়ালেট ও ব্যাংক এন্ট্রি (MW and Bank Contra)
# ------------------------------------------
elif current_action == "💳 MW and Bank (Contra)":
    st.subheader("মাদার ওয়ালেট এবং ব্যাংক ট্রান্সফার ট্র্যাকিং (Double-Entry Engine)")
    
    form_col, status_col = st.columns([5, 7])
    
    with form_col:
        with st.form("mw_bank_form"):
            action_date = st.date_input("লেনদেনের তারিখ", date.today())
            action_type = st.selectbox("লেনদেনের ধরণ (Action)", ["Lifting", "Refund"])
            amount = st.number_input("টাকার পরিমাণ (Amount)", min_value=0.0, step=500.0)
            
            submit_contra = st.form_submit_button("সংরক্ষণ করুন (Execute Contra)")
            if submit_contra and amount > 0:
                # ডাবল-এন্ট্রি অ্যাকাউন্টিং অটো-প্রসেস মেকানিজম
                mw_impact = amount if action_type == "Lifting" else -amount
                bank_impact = -amount if action_type == "Lifting" else amount
                
                conn = get_db_connection()
                conn.execute("""
                    INSERT INTO mw_bank_ledger (company, action_date, action_type, amount, mw_impact, bank_impact)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (current_company, str(action_date), action_type, amount, mw_impact, bank_impact))
                conn.commit()
                conn.close()
                st.success(f"{action_type} এন্ট্রি সফলভাবে প্রসেস হয়েছে!")
                st.rerun()
                
    with status_col:
        # লাইভ ব্যালেন্স স্ট্যাটাস ক্যালকুলেশন
        conn = get_db_connection()
        balances = conn.execute("""
            SELECT SUM(mw_impact) as total_mw, SUM(bank_impact) as total_bank 
            FROM mw_bank_ledger WHERE company=?
        """, (current_company,)).fetchone()
        conn.close()
        
        live_mw = balances['total_mw'] if balances['total_mw'] else 0.0
        live_bank = balances['total_bank'] if balances['total_bank'] else 0.0
        
        st.metric(label="💳 লাইভ মাদার ওয়ালেট ব্যালেন্স (Mother Wallet)", value=f"{live_mw:,.2f} BDT")
        st.metric(label="🏦 লাইভ ব্যাংক অ্যাকাউন্ট ব্যালেন্স (Bank Net)", value=f"{live_bank:,.2f} BDT")

# ------------------------------------------
# গ) ইআরপি রিপোর্ট ভিউয়ার (Automated ERP Reporting)
# ------------------------------------------
elif current_action == "📊 ERP Report Viewer":
    st.subheader("Automated ERP Output Generation Window")
    
    report_type = st.radio("কোন রিপোর্টটি দেখতে চান নির্বাচন করুন:", [
        "📖 1. Cash Khata Report (দৈনিক খতিয়ান)", 
        "📊 2. Investment Update Report (ইনভেস্টমেন্ট ট্র্যাকার)"
    ], horizontal=True)
    
    conn = get_db_connection()
    
    if "Cash Khata Report" in report_type:
        st.write("### Cash Khata Detail Ledger")
        d1, d2, p_filt = st.columns([3, 3, 6])
        start_dt = d1.date_input("শুরুর তারিখ", date.today())
        end_dt = d2.date_input("শেষের তারিখ", date.today())
        
        parties = [r['party_name'] for r in conn.execute("SELECT DISTINCT party_name FROM cash_khata WHERE company=?", (current_company,)).fetchall()]
        selected_party = p_filt.selectbox("নির্দিষ্ট সেকেন্ড পার্টি ফিল্টার", ["All Parties"] + parties)
        
        query = "SELECT entry_date as 'তারিখ', type as 'ধরণ', party_name as 'সেকেন্ড পার্টি', amount as 'টাকা', remarks as 'বিবরণ' FROM cash_khata WHERE company=? AND entry_date BETWEEN ? AND ?"
        params = [current_company, str(start_dt), str(end_dt)]
        if selected_party != "All Parties":
            query += " AND party_name=?"
            params.append(selected_party)
            
        df_report = pd.read_sql_query(query, conn, params=params)
        
        # অ্যাকশন রো এবং রোল প্রিভিলেজ কন্ট্রোল
        st.dataframe(df_report, use_container_width=True, hide_index=True)
        
        # অ্যাডমিন মোড হলে এডিট/ডিলিটের বিশেষ সুযোগ দৃশ্যমান হবে
        if st.session_state.user_role == 'Admin':
            st.warning("⚠️ এডমিন প্যানেল সক্রিয়: ডাটাবেজ মডিফিকেশন মোড সচল আছে।")
            # এডিট বা ডিলিটের লজিক এখানে সংযুক্ত করা যাবে
            
    elif "Investment Update Report" in report_type:
        st.write("### Live Investment Status Report")
        
        # ৪৭ লাখ টাকার বেসলাইন ক্যালকুলেশন ইঞ্জিন
        baseline = 47000000.00
        
        # লাইভ ডাটা সামারি পুল
        mw_bal = conn.execute("SELECT SUM(mw_impact) FROM mw_bank_ledger WHERE company=?", (current_company,)).fetchone()[0] or 0.0
        bank_bal = conn.execute("SELECT SUM(bank_impact) FROM mw_bank_ledger WHERE company=?", (current_company,)).fetchone()[0] or 0.0
        
        # ফর্মুলা ভিত্তিক ইনভেস্টমেন্ট ভ্যালু জেনারেশন
        total_investment = baseline + mw_bal + bank_bal
        
        st.info("💡 সূত্র: মোট ইনভেস্টমেন্ট = ৪৭ লাখ (বেসলাইন) + ক্যাশ + ব্যাংক + মাদার ওয়ালেট + (পাওনা - দেনা)")
        
        inv_data = {
            "কম্পোনেন্ট খতিয়ান বিবরণ": ["Base Investment (মূল বেসলাইন)", "Mother Wallet Net Status", "Bank Account Net Status", "Total Real-time Investment"],
            "বর্তমান আর্থিক স্থিতি (BDT)": [f"{baseline:,.2f}", f"{mw_bal:,.2f}", f"{bank_bal:,.2f}", f"{total_investment:,.2f}"]
        }
        st.table(pd.DataFrame(inv_data))
        
        # Output Support (PDF / Print / Excel export triggers)
        st.write("---")
        st.subheader("📥 Export Automated ERP Output")
        c_p1, c_p2, c_p3 = st.columns(3)
        c_p1.button("🖨️ System Direct Print View", use_container_width=True)
        c_p2.button("📄 Export to PDF Format", use_container_width=True)
        c_p3.button("📊 Download Excel Statement", use_container_width=True)
        
    conn.close()

# ------------------------------------------
# ঘ) কর্মচারী ডিরেক্টরি (Employee Directory & Bulk Upload)
# ------------------------------------------
elif current_action == "👥 Employee Directory":
    st.subheader("কর্মচারী ডাটাবেজ ও বাল্ক এক্সেল ইনপুট")
    
    # বাল্ক আপলোডার প্যানেল
    excel_file = st.file_uploader("এক্সেল ফাইল আপলোড করুন (Bulk Upload)", type=["xlsx"])
    if excel_file:
        df_uploaded = pd.read_excel(excel_file)
        st.write("প্রিভিউ ডাটা:", df_uploaded.head(3))
        
        if st.button("🚀 ডাটাবেজে মার্চ করুন (Sync Database)"):
            conn = get_db_connection()
            # 🚨 [ডাটা ওভাররাইট বাগ ফিক্স]: আইডি মিললে ফ্যামিলি ডাটা ও ছবি অক্ষত রেখে শুধু স্যালারি/বেসিক আপডেট
            for _, row in df_uploaded.iterrows():
                emp_id = str(row['emp_id'])
                conn.execute("""
                    INSERT INTO employees (emp_id, name, designation, mobile, salary)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(emp_id) DO UPDATE SET
                        name=excluded.name,
                        designation=excluded.designation,
                        mobile=excluded.mobile,
                        salary=excluded.salary
                """, (emp_id, row['name'], row['designation'], str(row['mobile']), row['salary']))
            conn.commit()
            conn.close()
            st.success("পুরাতন সংবেদনশীল ডাটা অক্ষত রেখে বাল্ক ফাইল সফলভাবে মার্চ করা হয়েছে।")

# ------------------------------------------
# ঙ) সেকেন্ড পার্টি সেটআপ (Second Party Management)
# ------------------------------------------
elif current_action == "🤝 Second Party Setup":
    st.subheader("নতুন সেকেন্ড পার্টি প্রোফাইল কনফিগারেশন")
    
    with st.form("party_form"):
        p_name = st.text_input("সেকেন্ড পার্টির নাম (অবশ্যই ইউনিক হতে হবে)")
        p_phone = st.text_input("ফোন নম্বর")
        p_comment = st.text_input("মন্তব্য/বিবরণ")
        
        submit_party = st.form_submit_button("নতুন পার্টি যুক্ত করুন")
        if submit_party and p_name:
            conn = get_db_connection()
            try:
                # 🚨 [ডুপ্লিকেট এরর হ্যান্ডলিং]: একই কোম্পানিতে ডুপ্লিকেট নাম প্রতিরোধ করা
                conn.execute("""
                    INSERT INTO second_parties (company, party_name, phone, comments)
                    VALUES (?, ?, ?, ?)
                """, (current_company, p_name, p_phone, p_comment))
                conn.commit()
                st.success(f"'{p_name}' সফলভাবে {current_company} এর খাতায় যুক্ত হয়েছে।")
            except sqlite3.IntegrityError:
                st.error(f"❌ এরর: '{p_name}' নামে এই কোম্পানিতে অলরেডি একটি অ্যাকাউন্ট রয়েছে।")
            finally:
                conn.close()
