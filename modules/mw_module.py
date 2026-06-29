import streamlit as st
import pandas as pd
import sqlite3
import json
import time
from datetime import datetime, timedelta

DB_NAME = 'jabed_enterprise.db'

# --- ফাঁকা জায়গা (Gap/Padding) কমানোর জন্য কাস্টম CSS ---
def apply_compact_styles():
    st.markdown("""
        <style>
            .block-container {
                padding-top: 0rem !important;
                padding-bottom: 0rem !important;
            }
            h1, h2, h3, h4, h5, h6 {
                margin-top: 1.5rem !important;
                margin-bottom: 0rem !important;
                padding-top: 0px !important;
                padding-bottom: 0px !important;
            }
            hr {
                margin-top: 0.0rem !important;
                margin-bottom: 0.0rem !important;
            }
            [data-testid="stVerticalBlock"] > div {
                gap: 0.0rem !important;
            }
            .stSelectbox, .stTextInput, .stNumberInput {
                margin-bottom: 0px !important;
            }
            [data-testid="stMetric"] {
                padding: 0px 0px !important;
            }
        </style>
    """, unsafe_allow_html=True)

# ✅ গ্লোবাল ডেট ফরম্যাট করার ফাংশন
def format_date_display(date_str):
    """YYYY-MM-DD থেকে DD-MM-YYYY এ কনভার্ট করা"""
    try:
        return datetime.strptime(str(date_str), '%Y-%m-%d').strftime('%d-%m-%Y')
    except:
        return str(date_str)

def format_date_db(date_obj):
    """Date object থেকে YYYY-MM-DD স্ট্রিং এ কনভার্ট করা"""
    if isinstance(date_obj, str):
        return date_obj
    return date_obj.strftime('%Y-%m-%d')

# --- 1. ডাটাবেস টেবিল ইনিশিয়ালাইজেশন (স্মার্ট মাইগ্রেশন সহ) ---
def init_mw_db():
    """✅ সংশোধিত: স্মার্ট মাইগ্রেশন - পুরাতন ডাটা রক্ষা করা হয়"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # টেবিল আছে কিনা চেক করা
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mw_ledger'")
        table_exists = cursor.fetchone()
        
        if not table_exists:
            # টেবিল নেই - নতুন তৈরি করা
            conn.execute('''CREATE TABLE IF NOT EXISTS mw_ledger (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                date TEXT,
                                company TEXT,
                                opening_balance REAL,
                                receive_json TEXT,
                                send_json TEXT,
                                total_receive REAL,
                                total_send REAL,
                                closing_balance REAL,
                                UNIQUE(date, company)
                            )''')
        else:
            # টেবিল আছে - company কলাম আছে কিনা চেক করা
            cursor.execute("PRAGMA table_info(mw_ledger)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'company' not in columns:
                # company কলাম নেই - যোগ করা
                cursor.execute("ALTER TABLE mw_ledger ADD COLUMN company TEXT DEFAULT 'M/S Jabed Enterprise'")
                
                # পুরাতন UNIQUE constraint রিমুভ করতে টেবিল রিক্রিয়েট করতে হবে
                # কিন্তু আগে ডাটা ব্যাকআপ নিই
                cursor.execute("SELECT * FROM mw_ledger")
                old_data = cursor.fetchall()
                
                # পুরাতন টেবিল রিনেম করা
                cursor.execute("ALTER TABLE mw_ledger RENAME TO mw_ledger_old")
                
                # নতুন টেবিল তৈরি করা (সঠিক স্কিমা সহ)
                conn.execute('''CREATE TABLE mw_ledger (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    date TEXT,
                                    company TEXT,
                                    opening_balance REAL,
                                    receive_json TEXT,
                                    send_json TEXT,
                                    total_receive REAL,
                                    total_send REAL,
                                    closing_balance REAL,
                                    UNIQUE(date, company)
                                )''')
                
                # পুরাতন ডাটা ট্রান্সফার করা (company = 'M/S Jabed Enterprise' দিয়ে)
                if old_data:
                    for row in old_data:
                        conn.execute('''
                            INSERT INTO mw_ledger (id, date, company, opening_balance, receive_json, send_json, total_receive, total_send, closing_balance)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (row[0], row[1], 'M/S Jabed Enterprise', row[2], row[3], row[4], row[5], row[6], row[7]))
                
                # পুরাতন টেবিল ডিলিট করা
                conn.execute("DROP TABLE mw_ledger_old")
        
        conn.commit()

# ✅ ব্যাংক লিস্ট নিয়ে আসার ফাংশন (company ফিল্টার সহ)
def get_formatted_bank_list(company):
    """
    bank_module এর সাথে 100% মিল রাখার জন্য সরাসরি bank_accounts টেবিল 
    থেকে account_id ফেচ করা হচ্ছে। (company ফিল্টার সহ)
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            # ✅ company ফিল্টার যোগ করা
            cursor.execute("SELECT account_id FROM bank_accounts WHERE company=?", (company,))
            rows = cursor.fetchall()
            
            banks = []
            for row in rows:
                if row[0]:  # যদি account_id বিদ্যমান থাকে
                    banks.append(row[0])
            return [""] + banks
    except Exception as e:
        return [""]

# ✅ পূর্ববর্তী তারিখের ক্লোজিং ব্যালেন্স খোঁজার ফাংশন (company সহ)
def get_previous_closing(target_date, company):
    """✅ সংশোধিত: company ফিল্টার যোগ করা হয়েছে"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # ✅ company ফিল্টার যোগ করা
        cursor.execute("""
            SELECT closing_balance FROM mw_ledger 
            WHERE company=? AND date < ? 
            ORDER BY date DESC LIMIT 1
        """, (company, target_date))
        row = cursor.fetchone()
        return row[0] if row else 0.0

# --- 3. মূল ইউজার ইন্টারফেস ফাংশন ---
def show_mw_management():
    apply_compact_styles()
    
    # 🎯 সেশন থেকে কারেন্ট কোম্পানি ফেচ করা
    current_company = st.session_state.get('current_company', 'M/S Jabed Enterprise')
    
    # মূল দুটি ট্যাব তৈরি 
    tab_ledger, tab_report = st.tabs(["📝 Daily Ledger Entry", "📊 Ledger Reports & Analytics"])
    
    # ==========================================
    # TAB 1: DAILY LEDGER ENTRY
    # ==========================================
    with tab_ledger:
        st.markdown(f"### 💰 Mother Wallet (MW) Daily Ledger - {current_company}")
        init_mw_db()
        st.markdown("---")

        col_top_left, col_top_right = st.columns([7, 3])
        with col_top_left:
            st.markdown("<p style='font-weight:bold; margin-top:5px;'>📅 Date: </p>", unsafe_allow_html=True)
        with col_top_right:
            # 🎯 ক্যালেন্ডার ইনপুট থেকে সরাসরি স্ট্যান্ডার্ড 'YYYY-MM-DD' ফরম্যাটে তারিখ নেওয়া হচ্ছে
            selected_date = format_date_db(st.date_input("Date", datetime.now().date(), format="DD-MM-YYYY", label_visibility="collapsed", key="master_sheet_date"))

        # ✅ ডাটাবেজে এই তারিখ এবং কোম্পানির এন্ট্রি আছে কিনা চেক করা
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            # ✅ company ফিল্টার যোগ করা
            cursor.execute("SELECT opening_balance, receive_json, send_json FROM mw_ledger WHERE company=? AND date = ?", (current_company, selected_date))
            existing_record = cursor.fetchone()

        is_update_mode = existing_record is not None

        # ডিফল্ট ব্ল্যাংক টেমপ্লেট
        default_receive = pd.DataFrame([
            {"Type": "DSO Return", "Amount": 0.0, "Account/Details": ""},
            {"Type": "Commission Receive", "Amount": 0.0, "Account/Details": ""}
        ])
        default_send = pd.DataFrame([
            {"Type": "Send to DSO", "Amount": 0.0, "Account/Details": ""}
        ])

        # মোড অনুযায়ী ডাটা সেটআপ করা
        if is_update_mode:
            opening_balance = existing_record[0]
            try: receive_init = pd.read_json(existing_record[1], orient='records')
            except: receive_init = default_receive
            try: send_init = pd.read_json(existing_record[2], orient='records')
            except: send_init = default_send
        else:
            # ✅ company পাস করা হচ্ছে get_previous_closing এ
            opening_balance = get_previous_closing(selected_date, current_company)
            receive_init = default_receive
            send_init = default_send

        if opening_balance == 0.0 and not is_update_mode:
            with st.expander("⚙️ Initial Setup", expanded=True):
                opening_balance = st.number_input("Set Initial Opening Balance (৳)", min_value=0.0, value=0.0, step=500.0)

        # 🎯 বর্তমান কোম্পানির ওপর ভিত্তি করে ব্যাংক লিস্ট ফিল্টার করা (company সহ)
        bank_list_options = get_formatted_bank_list(current_company)

        num_rows_recv_key = f"num_rows_recv_{selected_date}"
        if num_rows_recv_key not in st.session_state:
            st.session_state[num_rows_recv_key] = len(receive_init)

        num_rows_send_key = f"num_rows_send_{selected_date}"
        if num_rows_send_key not in st.session_state:
            st.session_state[num_rows_send_key] = len(send_init)

        # Initialize Recieve Data into Session State
        for i in range(st.session_state[num_rows_recv_key]):
            if f"init_recv_{selected_date}_{i}" not in st.session_state:
                st.session_state[f"init_recv_{selected_date}_{i}"] = True
                if i < len(receive_init):
                    st.session_state[f"recv_type_{selected_date}_{i}"] = receive_init.iloc[i]["Type"]
                    st.session_state[f"recv_amt_{selected_date}_{i}"] = float(receive_init.iloc[i]["Amount"])
                    st.session_state[f"recv_det_{selected_date}_{i}"] = str(receive_init.iloc[i]["Account/Details"])
                else:
                    st.session_state[f"recv_type_{selected_date}_{i}"] = "Others"
                    st.session_state[f"recv_amt_{selected_date}_{i}"] = 0.0
                    st.session_state[f"recv_det_{selected_date}_{i}"] = ""

        # Initialize Send Data into Session State
        for i in range(st.session_state[num_rows_send_key]):
            if f"init_send_{selected_date}_{i}" not in st.session_state:
                st.session_state[f"init_send_{selected_date}_{i}"] = True
                if i < len(send_init):
                    st.session_state[f"send_type_{selected_date}_{i}"] = send_init.iloc[i]["Type"]
                    st.session_state[f"send_amt_{selected_date}_{i}"] = float(send_init.iloc[i]["Amount"])
                    st.session_state[f"send_det_{selected_date}_{i}"] = str(send_init.iloc[i]["Account/Details"])
                else:
                    st.session_state[f"send_type_{selected_date}_{i}"] = "Others"
                    st.session_state[f"send_amt_{selected_date}_{i}"] = 0.0
                    st.session_state[f"send_det_{selected_date}_{i}"] = ""

        metric_container = st.container()

        st.markdown("<br>", unsafe_allow_html=True)
        c_tables1, c_tables2 = st.columns(2)

        # --- Receive Section ---
        with c_tables1:
            st.markdown("#### 📥 Receive Section")
            h1, h2, h3 = st.columns([3, 2, 4])
            h1.markdown("**Type**")
            h2.markdown("**Amount (৳)**")
            h3.markdown("**Account/Details**")
            
            receive_data = []
            recv_options = ["DSO Return", "Commission Receive", "Lifting", "Others"]
            
            for i in range(st.session_state[num_rows_recv_key]):
                r1, r2, r3 = st.columns([3, 2, 4])
                with r1:
                    saved_type = st.session_state[f"recv_type_{selected_date}_{i}"]
                    def_idx = recv_options.index(saved_type) if saved_type in recv_options else 3
                    t_val = st.selectbox(f"r_t_{i}", recv_options, index=def_idx, label_visibility="collapsed", key=f"r_tw_{selected_date}_{i}")
                    st.session_state[f"recv_type_{selected_date}_{i}"] = t_val
                with r2:
                    saved_amt = st.session_state[f"recv_amt_{selected_date}_{i}"]
                    a_val = st.number_input(f"r_a_{i}", min_value=0.0, format="%.2f", value=float(saved_amt), label_visibility="collapsed", key=f"r_aw_{selected_date}_{i}")
                    st.session_state[f"recv_amt_{selected_date}_{i}"] = a_val
                with r3:
                    if t_val == "Lifting":
                        saved_val = st.session_state.get(f"recv_det_{selected_date}_{i}", "")
                        def_idx = bank_list_options.index(saved_val) if saved_val in bank_list_options else 0
                        d_val = st.selectbox(f"r_d_bank_{i}", bank_list_options, index=def_idx, label_visibility="collapsed", key=f"r_db_w_{selected_date}_{i}")
                        st.session_state[f"recv_det_{selected_date}_{i}"] = d_val
                    else:
                        curr_val = st.session_state.get(f"recv_det_{selected_date}_{i}", "")
                        if curr_val in bank_list_options and curr_val != "":
                            curr_val = ""
                            st.session_state[f"recv_det_{selected_date}_{i}"] = ""
                        d_val = st.text_input(f"r_d_txt_{i}", value=curr_val, label_visibility="collapsed", placeholder="Enter details...", key=f"r_dt_w_{selected_date}_{i}")
                        st.session_state[f"recv_det_{selected_date}_{i}"] = d_val
                        
                receive_data.append({"Type": t_val, "Amount": a_val, "Account/Details": d_val})
                
            if st.button("➕ Add Receive Row", key=f"add_recv_{selected_date}", use_container_width=True):
                st.session_state[num_rows_recv_key] += 1
                st.rerun()
                
            receive_df = pd.DataFrame(receive_data)
            total_receive = pd.to_numeric(receive_df["Amount"]).sum()

        # --- Send Section ---
        with c_tables2:
            st.markdown("#### 📤 Send Section")
            h1, h2, h3 = st.columns([3, 2, 4])
            h1.markdown("**Type**")
            h2.markdown("**Amount (৳)**")
            h3.markdown("**Account/Details**")
            
            send_data = []
            send_options = ["Send to DSO", "Refund", "SA Transfer", "B.Payment", "Others"]
            
            for i in range(st.session_state[num_rows_send_key]):
                r1, r2, r3 = st.columns([3, 2, 4])
                with r1:
                    saved_type = st.session_state[f"send_type_{selected_date}_{i}"]
                    def_idx = send_options.index(saved_type) if saved_type in send_options else 4
                    t_val = st.selectbox(f"s_t_{i}", send_options, index=def_idx, label_visibility="collapsed", key=f"s_tw_{selected_date}_{i}")
                    st.session_state[f"send_type_{selected_date}_{i}"] = t_val
                with r2:
                    saved_amt = st.session_state[f"send_amt_{selected_date}_{i}"]
                    a_val = st.number_input(f"s_a_{i}", min_value=0.0, format="%.2f", value=float(saved_amt), label_visibility="collapsed", key=f"s_aw_{selected_date}_{i}")
                    st.session_state[f"send_amt_{selected_date}_{i}"] = a_val
                with r3:
                    if t_val == "Refund":
                        saved_val = st.session_state.get(f"send_det_{selected_date}_{i}", "")
                        def_idx = bank_list_options.index(saved_val) if saved_val in bank_list_options else 0
                        d_val = st.selectbox(f"s_d_bank_{i}", bank_list_options, index=def_idx, label_visibility="collapsed", key=f"s_db_w_{selected_date}_{i}")
                        st.session_state[f"send_det_{selected_date}_{i}"] = d_val
                    else:
                        curr_val = st.session_state.get(f"send_det_{selected_date}_{i}", "")
                        if curr_val in bank_list_options and curr_val != "":
                            curr_val = ""
                            st.session_state[f"send_det_{selected_date}_{i}"] = ""
                        d_val = st.text_input(f"s_d_txt_{i}", value=curr_val, label_visibility="collapsed", placeholder="Enter details...", key=f"s_dt_w_{selected_date}_{i}")
                        st.session_state[f"send_det_{selected_date}_{i}"] = d_val
                        
                send_data.append({"Type": t_val, "Amount": a_val, "Account/Details": d_val})
                
            if st.button("➕ Add Send Row", key=f"add_send_{selected_date}", use_container_width=True):
                st.session_state[num_rows_send_key] += 1
                st.rerun()
                
            send_df = pd.DataFrame(send_data)
            total_send = pd.to_numeric(send_df["Amount"]).sum()

        closing_balance = opening_balance + total_receive - total_send

        with metric_container:
            m_col1, m_col2, m_col3, m_col4 = st.columns(4)
            m_col1.metric("Opening Balance", f"{opening_balance:,.2f} ৳")
            m_col2.metric("Total Receive", f"{total_receive:,.2f} ৳", delta=f"+{total_receive:,.2f}" if total_receive > 0 else None)
            m_col3.metric("Total Send", f"{total_send:,.2f} ৳", delta=f"-{total_send:,.2f}" if total_send > 0 else None, delta_color="inverse")
            m_col4.metric("Closing Balance", f"{closing_balance:,.2f} ৳")

        st.markdown("<br>", unsafe_allow_html=True)
        
        button_label = "🔄 Update Ledger Data" if is_update_mode else "💾 Save Today's Ledger"
        button_type = "secondary" if is_update_mode else "primary"
        
        if st.button(button_label, type=button_type, use_container_width=True, key="save_ledger_btn_mw"):
            receive_json_str = receive_df.to_json(orient='records')
            send_json_str = send_df.to_json(orient='records')
            
            with sqlite3.connect(DB_NAME) as conn:
                # ✅ company ফিল্টার যোগ করা হয়েছে
                
                # পুরাতন সিঙ্ক হওয়া ডেটা মুছে ফেলা (কোম্পানি অনুযায়ী)
                conn.execute("""
                    DELETE FROM bank_transactions 
                    WHERE date=? AND company=? AND source_module='MW Module'
                """, (selected_date, current_company))
                
                # 1. Receive Section থেকে "Lifting" চেক করে ব্যাংকে WITHDRAW সিঙ্ক করা
                for row in receive_data:
                    tx_type = row["Type"]
                    amount = row["Amount"]
                    account_details = row["Account/Details"]
                    
                    if tx_type == "Lifting" and account_details in bank_list_options and account_details != "":
                        if amount > 0:
                            conn.execute("""
                                INSERT INTO bank_transactions 
                                (date, company, bank_info, type, amount, source_module, trx_sub_type) 
                                VALUES (?, ?, ?, 'WITHDRAW', ?, 'MW Module', 'Lifting')
                            """, (selected_date, current_company, account_details, amount))
                            
                # 2. Send Section থেকে "Refund" চেক করে ব্যাংকে DEPOSIT সিঙ্ক করা
                for row in send_data:
                    tx_type = row["Type"]
                    amount = row["Amount"]
                    account_details = row["Account/Details"]
                    
                    if tx_type == "Refund" and account_details in bank_list_options and account_details != "":
                        if amount > 0:
                            conn.execute("""
                                INSERT INTO bank_transactions 
                                (date, company, bank_info, type, amount, source_module, trx_sub_type) 
                                VALUES (?, ?, ?, 'DEPOSIT', ?, 'MW Module', 'Refund')
                            """, (selected_date, current_company, account_details, amount))
                
                # ✅ company ফিল্টার যোগ করা হয়েছে
                if is_update_mode:
                    conn.execute("""
                        UPDATE mw_ledger 
                        SET opening_balance=?, receive_json=?, send_json=?, total_receive=?, total_send=?, closing_balance=?
                        WHERE date=? AND company=?
                    """, (opening_balance, receive_json_str, send_json_str, total_receive, total_send, closing_balance, selected_date, current_company))
                    f_date = format_date_display(selected_date)
                    st.toast(f"✅ {f_date} তারিখের লেজার সফলভাবে আপডেট হয়েছে!", icon="🔄")
                else:
                    # ✅ company কলাম যোগ করা হয়েছে INSERT এ
                    conn.execute("""
                        INSERT INTO mw_ledger (date, company, opening_balance, receive_json, send_json, total_receive, total_send, closing_balance) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (selected_date, current_company, opening_balance, receive_json_str, send_json_str, total_receive, total_send, closing_balance))
                    f_date = format_date_display(selected_date)
                    st.toast(f"🎉 {f_date} তারিখের লেজার সফলভাবে সেভ হয়েছে!", icon="💾")
                
                conn.commit()
            
            for key in list(st.session_state.keys()):
                if selected_date in key:
                    del st.session_state[key]
            
            time.sleep(0.6)
            st.rerun()

        # --- হিস্ট্রি লগ ---
        st.markdown("---")
        st.markdown("### 📜 Ledger History Logs")
        
        with sqlite3.connect(DB_NAME) as conn:
            try:
                # ✅ company ফিল্টার যোগ করা হয়েছে
                history_df = pd.read_sql("""
                    SELECT date AS "Date", 
                           opening_balance AS "Opening Balance", 
                           total_receive AS "Total Receive", 
                           total_send AS "Total Send", 
                           closing_balance AS "Closing Balance" 
                    FROM mw_ledger 
                    WHERE company=?
                    ORDER BY date DESC
                """, conn, params=(current_company,))
            except:
                history_df = pd.DataFrame()

        if not history_df.empty:
            # ✅ ডেট ফরম্যাটিং গ্লোবাল ফাংশন ব্যবহার করা
            history_df["Date"] = pd.to_datetime(history_df["Date"]).dt.strftime('%d-%m-%Y')
            st.dataframe(
                history_df.style.format({
                    "Opening Balance": "{:,.2f} ৳",
                    "Total Receive": "{:,.2f} ৳",
                    "Total Send": "{:,.2f} ৳",
                    "Closing Balance": "{:,.2f} ৳"
                }),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("ডাটাবেজে পূর্বে সাবমিট করা কোনো লেজার হিস্ট্রি পাওয়া যায়নি।")

    # ==========================================
    # TAB 2: LEDGER REPORTS & ANALYTICS
    # ==========================================
    with tab_report:
        st.markdown("### 📊 Mother Wallet (MW) Advanced Report Panel")
        st.markdown("---")
        
        with sqlite3.connect(DB_NAME) as conn:
            try:
                # ✅ company ফিল্টার যোগ করা হয়েছে
                raw_report_df = pd.read_sql("SELECT * FROM mw_ledger WHERE company=? ORDER BY date DESC", conn, params=(current_company,))
            except:
                raw_report_df = pd.DataFrame()
                
        if raw_report_df.empty:
            st.warning("📊 রিপোর্ট জেনারেট করার জন্য ডাটাবেজে কোনো লেজার ডেটা পাওয়া যায়নি।")
        else:
            f_col1, f_col2 = st.columns([2, 4])
            
            with f_col1:
                filter_type = st.radio(
                    "📅 Select Report Range Type",
                    ["Daily Report", "Monthly Summary", "Custom Date Range"],
                    index=0,
                    key="report_range_type_radio_mw"
                )
            
            start_dt, end_dt = None, None
            with f_col2:
                if filter_type == "Daily Report":
                    rep_date = st.date_input("Select Report Date", datetime.now().date(), format="DD-MM-YYYY", key="rep_date_picker_mw")
                    start_dt = end_dt = format_date_db(rep_date)
                    
                elif filter_type == "Monthly Summary":
                    all_dates = pd.to_datetime(raw_report_df['date'])
                    months_available = all_dates.dt.strftime('%B %Y').unique()
                    selected_month_str = st.selectbox("Select Month", months_available, key="rep_month_picker_mw")
                    
                    parsed_month = datetime.strptime(selected_month_str, "%B %Y")
                    start_dt = parsed_month.replace(day=1).strftime("%Y-%m-%d")
                    next_month = (parsed_month.replace(day=28) + timedelta(days=4))
                    end_dt = (next_month - timedelta(days=next_month.day)).strftime("%Y-%m-%d")
                    
                elif filter_type == "Custom Date Range":
                    d_range = st.date_input("Select Date Range", [datetime.now().date() - timedelta(days=7), datetime.now().date()], format="DD-MM-YYYY", key="rep_range_picker_mw")
                    if isinstance(d_range, list) or isinstance(d_range, tuple):
                        if len(d_range) == 2:
                            start_dt, end_dt = format_date_db(d_range[0]), format_date_db(d_range[1])
                        else:
                            start_dt = end_dt = format_date_db(d_range[0])
            
            filtered_master = raw_report_df[(raw_report_df['date'] >= start_dt) & (raw_report_df['date'] <= end_dt)].copy()
            
            if filtered_master.empty:
                f_start = format_date_display(start_dt)
                f_end = format_date_display(end_dt)
                st.info(f"নির্বাচিত রেঞ্জে ({f_start} থেকে {f_end}) কোনো ডেটা পাওয়া যায়নি।")
            else:
                sub_tab_summary, sub_tab_breakdown = st.tabs(["📉 Period Summary Matrix", "🔍 Sector Breakdown Details"])
                
                with sub_tab_summary:
                    st.markdown("#### 📌 Financial Overview")
                    tot_rec_p = filtered_master['total_receive'].sum()
                    tot_snd_p = filtered_master['total_send'].sum()
                    
                    sorted_asc = filtered_master.sort_values('date')
                    open_bal_p = sorted_asc.iloc[0]['opening_balance']
                    close_bal_p = sorted_asc.iloc[-1]['closing_balance']
                    
                    m_p1, m_p2, m_p3, m_p4 = st.columns(4)
                    m_p1.metric("Period Start Opening", f"{open_bal_p:,.2f} ৳")
                    m_p2.metric("Total Receive (Period)", f"{tot_rec_p:,.2f} ৳")
                    m_p3.metric("Total Send (Period)", f"{tot_snd_p:,.2f} ৳")
                    m_p4.metric("Period End Closing", f"{close_bal_p:,.2f} ৳")
                    
                    st.markdown("<br>##### 📅 Day-to-Day Ledger Log", unsafe_allow_html=True)
                    view_df = filtered_master[['date', 'opening_balance', 'total_receive', 'total_send', 'closing_balance']].copy()
                    view_df.columns = ["Date", "Opening Balance", "Total Receive", "Total Send", "Closing Balance"]
                    
                    # ✅ গ্লোবাল ডেট ফরম্যাট ফাংশন ব্যবহার করা
                    view_df["Date"] = view_df["Date"].apply(format_date_display)
                    st.dataframe(
                        view_df.style.format({
                            "Opening Balance": "{:,.2f} ৳",
                            "Total Receive": "{:,.2f} ৳",
                            "Total Send": "{:,.2f} ৳",
                            "Closing Balance": "{:,.2f} ৳"
                        }),
                        use_container_width=True,
                        hide_index=True
                    )
                
                with sub_tab_breakdown:
                    all_recv_rows = []
                    all_send_rows = []
                    
                    for _, row in filtered_master.iterrows():
                        dt = row['date']
                        try:
                            r_list = json.loads(row['receive_json'])
                            for item in r_list:
                                item['Date'] = dt
                                all_recv_rows.append(item)
                        except: pass
                        
                        try:
                            s_list = json.loads(row['send_json'])
                            for item in s_list:
                                item['Date'] = dt
                                all_send_rows.append(item)
                        except: pass
                        
                    df_recv_breakdown = pd.DataFrame(all_recv_rows) if all_recv_rows else pd.DataFrame(columns=["Date", "Type", "Amount", "Account/Details"])
                    df_send_breakdown = pd.DataFrame(all_send_rows) if all_send_rows else pd.DataFrame(columns=["Date", "Type", "Amount", "Account/Details"])
                    
                    b_col1, b_col2 = st.columns(2)
                    
                    with b_col1:
                        st.markdown("##### 📥 Itemized Receives")
                        if not df_recv_breakdown.empty:
                            df_recv_breakdown = df_recv_breakdown[["Date", "Type", "Amount", "Account/Details"]]
                            sum_recv = df_recv_breakdown.groupby("Type")["Amount"].sum().reset_index()
                            sum_recv.columns = ["Receive Sector", "Total Amount"]
                            st.dataframe(sum_recv.style.format({"Total Amount": "{:,.2f} ৳"}), use_container_width=True, hide_index=True)
                            
                            with st.expander("🔍 View Transaction Details"):
                                # ✅ গ্লোবাল ডেট ফরম্যাট ফাংশন ব্যবহার করা
                                df_recv_breakdown["Date"] = df_recv_breakdown["Date"].apply(format_date_display)
                                st.dataframe(df_recv_breakdown.style.format({"Amount": "{:,.2f} ৳"}), use_container_width=True, hide_index=True)
                        else:
                            st.info("কোনো রিসিভ রেকর্ড নেই।")
                            
                    with b_col2:
                        st.markdown("##### 📤 Itemized Sends")
                        if not df_send_breakdown.empty:
                            df_send_breakdown = df_send_breakdown[["Date", "Type", "Amount", "Account/Details"]]
                            sum_send = df_send_breakdown.groupby("Type")["Amount"].sum().reset_index()
                            sum_send.columns = ["Send Sector", "Total Amount"]
                            st.dataframe(sum_send.style.format({"Total Amount": "{:,.2f} ৳"}), use_container_width=True, hide_index=True)
                            
                            with st.expander("🔍 View Transaction Details"):
                                # ✅ গ্লোবাল ডেট ফরম্যাট ফাংশন ব্যবহার করা
                                df_send_breakdown["Date"] = df_send_breakdown["Date"].apply(format_date_display)
                                st.dataframe(df_send_breakdown.style.format({"Amount": "{:,.2f} ৳"}), use_container_width=True, hide_index=True)
                        else:
                            st.info("কোনো সেন্ড রেকর্ড নেই।")
