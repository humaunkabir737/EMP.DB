import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import io
import time
import re

# --- ডাটাবেস কনফিগারেশন ---
DB_NAME = 'jabed_enterprise.db'

def init_cash_db():
    """ডাটাবেস টেবিল স্ট্রাকচার নিশ্চিত এবং অটো-আপডেট করার ফাংশন"""
    with sqlite3.connect(DB_NAME) as conn:
        # cash_transactions টেবিল তৈরি
        conn.execute('''CREATE TABLE IF NOT EXISTS cash_transactions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            date TEXT,
                            company TEXT,
                            second_party TEXT,
                            type TEXT,
                            amount REAL,
                            remarks TEXT)''')
        
        # --- অটো-মাইগ্রেশন (পুরাতন ডাটাবেজে কলাম না থাকলে তা যোগ করবে) ---
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(cash_transactions)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        
        if existing_columns:
            if 'company' not in existing_columns:
                cursor.execute("ALTER TABLE cash_transactions ADD COLUMN company TEXT DEFAULT 'M/S Jabed Enterprise'")
            if 'second_party' not in existing_columns:
                cursor.execute("ALTER TABLE cash_transactions ADD COLUMN second_party TEXT")
                if 'party_name' in existing_columns:
                    cursor.execute("UPDATE cash_transactions SET second_party = party_name WHERE second_party IS NULL")
            if 'remarks' not in existing_columns:
                cursor.execute("ALTER TABLE cash_transactions ADD COLUMN remarks TEXT")
                if 'account_reference' in existing_columns:
                    cursor.execute("UPDATE cash_transactions SET remarks = account_reference WHERE remarks IS NULL")
            conn.commit()
            
        # bank_accounts টেবিল তৈরি
        conn.execute('''CREATE TABLE IF NOT EXISTS bank_accounts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            bank_name TEXT,
                            account_number TEXT)''')

        # second_parties টেবিল নিশ্চিত করা (পার্টি ট্যাবের জন্য)
        conn.execute('''CREATE TABLE IF NOT EXISTS second_parties (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            company TEXT,
                            party_name TEXT UNIQUE,
                            contact_number TEXT,
                            comments_01 TEXT,
                            comments_02 TEXT,
                            status TEXT DEFAULT 'Active')''')
        
        cursor.execute("PRAGMA table_info(second_parties)")
        existing_party_cols = [row[1] for row in cursor.fetchall()]
        if 'company' not in existing_party_cols: 
            conn.execute("ALTER TABLE second_parties ADD COLUMN company TEXT DEFAULT 'Jabed Enterprise'")
        if 'status' not in existing_party_cols: 
            conn.execute("ALTER TABLE second_parties ADD COLUMN status TEXT DEFAULT 'Active'")
        if 'comments_01' not in existing_party_cols: 
            conn.execute("ALTER TABLE second_parties ADD COLUMN comments_01 TEXT")
        if 'comments_02' not in existing_party_cols: 
            conn.execute("ALTER TABLE second_parties ADD COLUMN comments_02 TEXT")
        conn.commit()

def get_banks():
    """ব্যাংক মডিউল থেকে ব্যাংক অ্যাকাউন্ট সমূহের নাম 'Bank Name_Last 4 Digit' ফরম্যাটে আনা"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            banks = conn.execute("SELECT bank_name, account_number FROM bank_accounts").fetchall()
            if not banks:
                return ["TXT_4012", "DBBL_9876", "Standard_5541"]
            return [f"{b[0]}_{str(b[1])[-4:]}" for b in banks]
    except Exception:
        return ["IFIC_4012"]

def preview_and_validate_excel(uploaded_file, current_company):
    """
    এক্সেল/CSV ফাইল প্রিভিউ এবং ৪টি লেভেলে ভ্যালিডেশন করার ফাংশন।
    """
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
            
        # সব ডেটা টেক্সট হিসেবে ট্রিম (strip) করে নেওয়া
        df = df.astype(str).apply(lambda x: x.str.strip())
        
        # 1. কলাম নাম ভ্যালিডেশন
        expected_cols = ['Party_Name', 'Contact_Number', 'Comments_01', 'Comments_02']
        if len(df.columns) != len(expected_cols) or not all(col in df.columns for col in expected_cols):
            st.error(f"❌ Wrong column format! Your file must have exactly 4 columns: {', '.join(expected_cols)}")
            return None, True

        # ডাটাবেজ থেকে বিদ্যমান পার্টিগুলোর নাম তুলে আনা (ডুপ্লিকেট চেক করার জন্য)
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT LOWER(party_name) FROM second_parties WHERE company = ?", (current_company,))
            existing_parties = {row[0] for row in cursor.fetchall()}

        validated_rows = []
        has_error = False

        for index, row in df.iterrows():
            row_num = index + 1
            party_name = row['Party_Name']
            contact_number = row['Contact_Number']
            comments_1 = row['Comments_01'] if row['Comments_01'] != 'nan' else ''
            comments_2 = row['Comments_02'] if row['Comments_02'] != 'nan' else ''
            
            status = "✅ Ready"
            error_msg = ""

            # 2. খালি নাম চেক
            if not party_name or party_name == 'nan':
                status = "❌ Error"
                error_msg += "Party name cannot be empty. "
                has_error = True
                
            # 3. ফোন নম্বর ভ্যালিডেশন (শুধু সংখ্যা কি না)
            if contact_number and contact_number != 'nan':
                clean_num = contact_number
                if clean_num.endswith('.0'): clean_num = clean_num[:-2]
                if any(c.isalpha() for c in clean_num):
                    status = "❌ Error"
                    error_msg += "Phone number contains letters. Only numbers allowed. "
                    has_error = True
                contact_number = clean_num
            else:
                contact_number = ""

            # 4. ডুপ্লিকেট পার্টি নাম চেক (একই কোম্পানির অধীনে)
            if party_name and party_name != 'nan' and party_name.lower() in existing_parties:
                status = "⚠️ Duplicate"
                error_msg += f"Account with name '{party_name}' already exists. "

            validated_rows.append({
                "SL": row_num,
                "Party_Name": party_name,
                "Contact_Number": contact_number,
                "Comments_01": comments_1,
                "Comments_02": comments_2,
                "Status": status,
                "Remarks": error_msg if error_msg else "Data is correct"
            })

        preview_df = pd.DataFrame(validated_rows)
        return preview_df, has_error

    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None, True

# --- Dialog: Party Delete & Bulk Delete Popup ---
@st.dialog("🚨 Delete Confirmation (Action Required)")
def show_party_popup(message, action_type=None, row_id=None):
    """Safe confirmation popup for single and bulk party deletion"""
    st.markdown(f"<div style='color: #d32f2f; font-weight: bold;'>{message}</div>", unsafe_allow_html=True)
    st.write("Are you sure you want to perform this action?")
    
    c1, c2 = st.columns(2)
    current_company = st.session_state.get('current_company', 'M/S Jabed Enterprise')
    
    if action_type == "delete_party":
        if c1.button("💥 Yes, Delete", use_container_width=True, key="pop_confirm_single_btn"):
            try:
                with sqlite3.connect(DB_NAME) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT party_name FROM second_parties WHERE id=?", (row_id,))
                    p_name = cursor.fetchone()[0]
                    
                    cursor.execute("DELETE FROM second_parties WHERE id=?", (row_id,))
                    conn.commit()
                st.toast(f"🗑️ '{p_name}' deleted successfully!", icon="✅")
                time.sleep(0.8)
                st.session_state.party_preview = None
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error deleting data: {e}")
        if c2.button("❌ Cancel", use_container_width=True, key="pop_cancel_single_btn"):
            st.rerun()
            
    elif action_type == "bulk_delete_party":
        if c1.button("💥 Yes, Delete All", use_container_width=True, key="pop_confirm_bulk_btn"):
            try:
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("DELETE FROM second_parties WHERE company=?", (current_company,))
                    conn.commit()
                st.toast("♻️ All second parties deleted successfully!", icon="🗑️")
                time.sleep(0.8)
                st.session_state.party_preview = None
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error in bulk delete: {e}")
        if c2.button("❌ Cancel", use_container_width=True, key="pop_cancel_bulk_btn"):
            st.rerun()

# --- Dialog: Edit Second Party ---
@st.dialog("⚙️ Edit Second Party Account")
def show_edit_party_dialog(party_id):
    """Dialog to update a specific second party's information"""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM second_parties WHERE id=?", (party_id,))
        party_row = cursor.fetchone()
        
    if party_row:
        with st.form("edit_party_form", clear_on_submit=False):
            st.markdown(f"**📝 Editing:** {party_row['party_name']}")
            
            new_name = st.text_input("Second Party Name (English Only) *", value=party_row['party_name'])
            up_contact = st.text_input("Contact Number", value=str(party_row['contact_number']) if party_row['contact_number'] else "")
            up_c1 = st.text_input("Comments 01", value=str(party_row['comments_01']) if party_row['comments_01'] != 'nan' else "")
            up_c2 = st.text_input("Comments 02", value=str(party_row['comments_02']) if party_row['comments_02'] != 'nan' else "")
            
            current_status = party_row['status']
            status_options = ["Active", "Inactive"]
            status_index = status_options.index(current_status) if current_status in status_options else 0
            up_status = st.selectbox("Account Status", status_options, index=status_index)
            
            st.markdown("<br>", unsafe_allow_html=True)
            ec1, ec2 = st.columns(2)
            
            if ec1.form_submit_button("💾 Update Information", use_container_width=True):
                if not new_name.strip():
                    st.error("Name is required!")
                elif up_contact.strip() and any(c.isalpha() for c in up_contact):
                    st.error("❌ Contact number contains letters!")
                else:
                    try:
                        clean_num = up_contact.strip()
                        if clean_num.endswith('.0'): clean_num = clean_num[:-2]
                        if clean_num == 'nan': clean_num = ""
                        
                        with sqlite3.connect(DB_NAME) as conn:
                            conn.execute("""
                                UPDATE second_parties 
                                SET party_name=?, contact_number=?, comments_01=?, comments_02=?, status=? 
                                WHERE id=?
                            """, (new_name.strip(), clean_num, up_c1.strip(), up_c2.strip(), up_status, party_id))
                            conn.commit()
                            
                        st.toast("🎉 Information updated successfully!", icon="✅")
                        time.sleep(0.8)
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("⚠️ An account with this name already exists!")
                    except Exception as e:
                        st.error(f"Error updating: {e}")
                        
            if ec2.form_submit_button("Cancel", use_container_width=True):
                st.rerun()

# --- Main Module Function ---
def show_cash_management():
    init_cash_db()
    
    current_company = st.session_state.get('current_company', 'M/S Jabed Enterprise')
    st.markdown(f"### 💵 Cash Management ({current_company})")

    # Custom CSS Injection
    st.markdown("""
        <style>
        button[data-testid="stNumberInputStepDown"], 
        button[data-testid="stNumberInputStepUp"] {
            display: none !important;
        }
        div[data-testid="stNumberInput"] input {
            padding-right: 10px !important;
        }
        div[data-testid="element-container"] {
            margin-bottom: 2.5px !important;
        }
        div[data-testid="stHorizontalBlock"] {
            gap: 10px !important;
        }
        .hdr-green {
            background-color: #0d533f; color: white; padding: 6px 15px;
            font-weight: bold; font-size: 14px; text-align: center;
        }
        .hdr-red {
            background-color: #7a1c1c; color: white; padding: 8px 15px;
            font-weight: bold; font-size: 14px; text-align: center;
        }
        .folder-lbl {
            color: #f39c12; font-weight: bold; font-size: 14px; margin-top: 10px; margin-bottom: 10px;
        }
        .meta-label-vertical { line-height: 38px; font-size: 14px; color: #aaaaaa; }
        .meta-value-vertical { line-height: 38px; font-size: 14px; font-weight: bold; text-align: right; color: #ffffff; }
        .summary-label-vertical { line-height: 32px; font-size: 14px; color: #ffffff; }
        .summary-value-vertical { line-height: 32px; font-size: 14px; font-weight: bold; text-align: right; color: #ffffff; }
        .summary-grand-value { line-height: 32px; font-size: 15px; font-weight: bold; text-align: right; color: #00ffaa; }
        .meta-hr { border: 0; border-top: 1px solid #333333; margin: 8px 0 !important; }
        .table-column-title { color: #888888; font-size: 13px; font-weight: bold; margin-top: 15px; margin-bottom: 5px; }
        .party-header { font-weight: bold; color: #888888; font-size: 14px; border-bottom: 1px solid #333333; padding-bottom: 4px; margin-bottom: 6px; }
        .party-row { line-height: 38px; font-size: 14px; color: #ffffff; }
        </style>
    """, unsafe_allow_html=True)

    if "num_rows_in" not in st.session_state: st.session_state.num_rows_in = 5
    if "num_rows_out" not in st.session_state: st.session_state.num_rows_out = 5
    if 'party_preview' not in st.session_state: st.session_state.party_preview = None
    if 'party_uploader_key' not in st.session_state: st.session_state.party_uploader_key = 100

    # 3 Tab Division
    tab1, tab2, tab3 = st.tabs(["📝 Daily Cash Khata", "📖 View Cash Khata Report", "👥 Party Management"])

    # ======================================================================
    # TAB 1: Daily Cash Entry Panel
    # ======================================================================
    with tab1:
        col_top_left, col_top_right = st.columns([7, 3])
        with col_top_left:
            st.markdown("<p style='font-weight:bold; margin-top:8px;'>📅 Date: </p>", unsafe_allow_html=True)
        with col_top_right:
            tx_date = st.date_input("Date", datetime.now().date(), format="DD-MM-YYYY", label_visibility="collapsed", key="master_sheet_date")
    
        date_str = tx_date.strftime('%Y-%m-%d')

        conn = sqlite3.connect(DB_NAME)
        db_parties = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=? AND status='Active' ORDER BY party_name ASC", (current_company,)).fetchall()]
        conn.close()
        
        parties = ["Bank", "Petty_Cash"] + db_parties

        with st.expander("📥 Excel Upload"):
            up_col1, up_col2 = st.columns([6, 4])
            with up_col1:
                excel_file = st.file_uploader("Select Excel File (.xlsx)", type=["xlsx"], key="cash_excel_uploader")
            with up_col2:
                accept_all_dates = st.radio("📅 Date Filtering Permission (Your Choice):", 
                                            ["Filter only dashboard date data", "Accept any date data together"], 
                                            key="excel_date_choice")
            
            if st.button("🧹 Clear Form (Reset Form)", key="reset_cash_form_btn"):
                st.session_state.num_rows_in = 5
                st.session_state.num_rows_out = 5
                for i in range(200):
                    st.session_state[f"c_p_in_{i}"] = ""
                    st.session_state[f"c_a_in_{i}"] = 0.0
                    st.session_state[f"c_r_in_{i}"] = ""
                    st.session_state[f"c_p_out_{i}"] = ""
                    st.session_state[f"c_a_out_{i}"] = 0.0
                    st.session_state[f"c_r_out_{i}"] = ""
                st.rerun()

            if excel_file is not None:
                if st.button("📊 Load Excel Data to Entry Form", type="secondary", use_container_width=True):
                    try:
                        df = pd.read_excel(excel_file)
                        if len(df.columns) < 5:
                            st.error("Excel file must have at least 5 columns.")
                        else:
                            df.columns = ['Date', 'Type', 'Party', 'Amount', 'Detail']
                            try: 
                                df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')
                            except: 
                                df['Date'] = df['Date'].astype(str).str.strip()
    
                            if "Filter only dashboard date data" in accept_all_dates:
                                df = df[df['Date'] == date_str]
                            
                            df_in = df[df['Type'].astype(str).str.upper().str.strip() == 'RECEIVE']
                            df_out = df[df['Type'].astype(str).str.upper().str.strip() == 'PAY OUT']
                            
                            st.session_state.num_rows_in = max(5, len(df_in))
                            st.session_state.num_rows_out = max(5, len(df_out))
     
                            for idx, row in enumerate(df_in.to_dict(orient='records')):
                                p_name = str(row['Party']).strip()
                                st.session_state[f"c_p_in_{idx}"] = p_name if p_name in parties else ""
                                st.session_state[f"c_a_in_{idx}"] = float(row['Amount']) if pd.notnull(row['Amount']) else 0.0
                                st.session_state[f"c_r_in_{idx}"] = str(row['Detail']) if pd.notnull(row['Detail']) and str(row['Detail']) != 'nan' else ""
                            
                            for idx, row in enumerate(df_out.to_dict(orient='records')):
                                p_name = str(row['Party']).strip()
                                st.session_state[f"c_p_out_{idx}"] = p_name if p_name in parties else ""
                                st.session_state[f"c_a_out_{idx}"] = float(row['Amount']) if pd.notnull(row['Amount']) else 0.0
                                st.session_state[f"c_r_out_{idx}"] = str(row['Detail']) if pd.notnull(row['Detail']) and str(row['Detail']) != 'nan' else ""
      
                            st.success(f"🎉 Excel data loaded! (Received: {len(df_in)}, Paid: {len(df_out)})")
                            time.sleep(0.6); st.rerun()
                    except Exception as e:
                        st.error(f"Error reading Excel file: {e}")

        # Previous day balance tracking logic
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

        # Grid Layout Header
        main_col1, main_col2 = st.columns(2)
        with main_col1:
            st.markdown('<div class="hdr-green">🛸 CASH RECEIVE</div>', unsafe_allow_html=True)
            st.markdown('<div class="folder-lbl">📁 Opening Cash:</div>', unsafe_allow_html=True)
        with main_col2:
            st.markdown('<div class="hdr-red">🛸 PAY OUT</div>', unsafe_allow_html=True)
            st.markdown('<div class="folder-lbl">📁 Closing Balances:</div>', unsafe_allow_html=True)

        # === Row 1: Vault Cash ===
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            sub_c1, sub_c2 = st.columns([7, 5])
            sub_c1.markdown('<div class="meta-label-vertical">Opening Vault Cash:</div>', unsafe_allow_html=True)
            sub_c2.markdown(f'<div class="meta-value-vertical">{op_vault_val:,.2f} ৳</div>', unsafe_allow_html=True)
        with row1_col2:
            sub_c1, sub_c2 = st.columns([7, 5])
            sub_c1.markdown('<div class="meta-label-vertical">Vault Cash:</div>', unsafe_allow_html=True)
            placeholder_vault_cash_text = sub_c2.empty()

        # === Row 2: DM & DSS Bank ===
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            sub_c1, sub_c2 = st.columns([7, 5])
            sub_c1.markdown('<div class="meta-label-vertical">DM & DSS Bank:</div>', unsafe_allow_html=True)
            sub_c2.markdown(f'<div class="meta-value-vertical">{op_bank_val:,.2f} ৳</div>', unsafe_allow_html=True)
        with row2_col2:
            sub_c1, sub_c2 = st.columns([7, 5])
            sub_c1.markdown('<div class="meta-label-vertical">DM & DSS Bank:</div>', unsafe_allow_html=True)
            m_bank = sub_c2.number_input("", min_value=0.0, step=1.0, key="m_inp_bank", label_visibility="collapsed")

        # === Row 3: Market Advance ===
        row3_col1, row3_col2 = st.columns(2)
        with row3_col1:
            sub_c1, sub_c2 = st.columns([7, 5])
            sub_c1.markdown('<div class="meta-label-vertical">Market Advance:</div>', unsafe_allow_html=True)
            sub_c2.markdown(f'<div class="meta-value-vertical">{op_adv_val:,.2f} ৳</div>', unsafe_allow_html=True)
        with row3_col2:
            sub_c1, sub_c2 = st.columns([7, 5])
            sub_c1.markdown('<div class="meta-label-vertical">Market Advance:</div>', unsafe_allow_html=True)
            m_advance = sub_c2.number_input("", min_value=0.0, step=1.0, key="m_inp_advance", label_visibility="collapsed")

        # === Row 4: Others Due ===
        row4_col1, row4_col2 = st.columns(2)
        with row4_col1:
            sub_c1, sub_c2 = st.columns([7, 5])
            sub_c1.markdown('<div class="meta-label-vertical">Others Due:</div>', unsafe_allow_html=True)
            sub_c2.markdown(f'<div class="meta-value-vertical">{op_due_val:,.2f} ৳</div>', unsafe_allow_html=True)
        with row4_col2:
            sub_c1, sub_c2 = st.columns([7, 5])
            sub_c1.markdown('<div class="meta-label-vertical">Others Due:</div>', unsafe_allow_html=True)
            m_due = sub_c2.number_input("", min_value=0.0, step=1.0, key="m_inp_due", label_visibility="collapsed")

        hr_col1, hr_col2 = st.columns(2)
        with hr_col1: st.markdown('<hr class="meta-hr">', unsafe_allow_html=True)
        with hr_col2: st.markdown('<hr class="meta-hr">', unsafe_allow_html=True)

        # === Row 5: Totals ===
        row5_col1, row5_col2 = st.columns(2)
        with row5_col1:
            sub_c1, sub_c2 = st.columns([7, 5])
            sub_c1.markdown('<div class="summary-label-vertical" style="color:#00ffaa; font-weight:bold;">Total Opening Cash:</div>', unsafe_allow_html=True)
            sub_c2.markdown(f'<div class="summary-value-vertical" style="color:#00ffaa; font-weight:bold;">{total_opening_calc:,.2f} ৳</div>', unsafe_allow_html=True)
        with row5_col2:
            sub_c1, sub_c2 = st.columns([7, 5])
            sub_c1.markdown('<div class="summary-label-vertical" style="color:#ff5555; font-weight:bold;">Total Closing Cash:</div>', unsafe_allow_html=True)
            placeholder_total_closing_text = sub_c2.empty()
            
        # Row 6: Live Summary
        row6_col1, row6_col2 = st.columns(2)
        with row6_col1: placeholder_left_summary = st.empty()
        with row6_col2: placeholder_right_summary = st.empty()

        st.markdown("<br>", unsafe_allow_html=True)
        grid_col1, grid_col2 = st.columns(2)
        
        # CASH RECEIVE Table Loop
        with grid_col1:
            st.markdown('<p style="color:#00ffaa; font-weight:bold; margin-bottom:0;">➕ Today Received List (CASH RECEIVE):</p>', unsafe_allow_html=True)
            
            h_l1, h_l2, h_l3 = st.columns([3.5, 3, 5.5])
            h_l1.markdown('<div class="table-column-title">Second Party Name</div>', unsafe_allow_html=True)
            h_l2.markdown('<div class="table-column-title">Amount ৳</div>', unsafe_allow_html=True)
            h_l3.markdown('<div class="table-column-title">Remarks/Account</div>', unsafe_allow_html=True)
            
            inputs_in = []
            for i in range(st.session_state.num_rows_in):
                r_l1, r_l2, r_l3 = st.columns([3.5, 3, 5.5])
                with r_l1: 
                    p = st.selectbox(f"p_in_{i}", [""] + parties, label_visibility="collapsed", key=f"c_p_in_f_{i}")
                with r_l2: 
                    a = st.number_input(f"a_in_{i}", min_value=0.0, step=1.0, label_visibility="collapsed", key=f"c_a_in_f_{i}")
                with r_l3: 
                    if p == "Bank":
                        bank_options = [""] + get_banks()
                        saved_val = st.session_state.get(f"c_r_in_f_{i}", "")
                        default_idx = bank_options.index(saved_val) if saved_val in bank_options else 0
                        rem = st.selectbox(f"r_in_bank_{i}", bank_options, index=default_idx, label_visibility="collapsed", key=f"c_r_in_bwidget_f_{i}")
                        st.session_state[f"c_r_in_f_{i}"] = rem
                    else:
                        if st.session_state.get(f"c_r_in_f_{i}", "") in get_banks():
                            st.session_state[f"c_r_in_f_{i}"] = ""
                        rem = st.text_input(f"r_in_{i}", label_visibility="collapsed", placeholder="Enter remarks...", key=f"c_r_in_f_{i}")
                        
                if p and a > 0: 
                    inputs_in.append((p, a, rem))
            
            st.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Add Another Receive Row", key="add_row_in_btn", use_container_width=True):
                st.session_state.num_rows_in += 1
                st.rerun()

        # PAY OUT Table Loop
        with grid_col2:
            st.markdown('<p style="color:#ff5555; font-weight:bold; margin-bottom:0;">➕ Today Expense List (PAY OUT):</p>', unsafe_allow_html=True)
            
            h_r1, h_r2, h_r3 = st.columns([3.5, 3, 5.5])
            h_r1.markdown('<div class="table-column-title">Second Party Name</div>', unsafe_allow_html=True)
            h_r2.markdown('<div class="table-column-title">Amount ৳</div>', unsafe_allow_html=True)
            h_r3.markdown('<div class="table-column-title">Remarks/Account</div>', unsafe_allow_html=True)
            
            inputs_out = []
            for i in range(st.session_state.num_rows_out):
                r_r1, r_r2, r_r3 = st.columns([3.5, 3, 5.5])
                with r_r1: 
                    p = st.selectbox(f"p_out_{i}", [""] + parties, label_visibility="collapsed", key=f"c_p_out_f_{i}")
                with r_r2: 
                    a = st.number_input(f"a_out_{i}", min_value=0.0, step=1.0, label_visibility="collapsed", key=f"c_a_out_f_{i}")
                with r_r3: 
                    if p == "Bank":
                        bank_options = [""] + get_banks()
                        saved_val = st.session_state.get(f"c_r_out_f_{i}", "")
                        default_idx = bank_options.index(saved_val) if saved_val in bank_options else 0
                        rem = st.selectbox(f"r_out_bank_{i}", bank_options, index=default_idx, label_visibility="collapsed", key=f"c_r_out_bwidget_f_{i}")
                        st.session_state[f"c_r_out_f_{i}"] = rem
                    else:
                        if st.session_state.get(f"c_r_out_f_{i}", "") in get_banks():
                            st.session_state[f"c_r_out_f_{i}"] = ""
                        rem = st.text_input(f"r_out_{i}", label_visibility="collapsed", placeholder="Enter remarks...", key=f"c_r_out_f_{i}")
                        
                if p and a > 0: 
                    inputs_out.append((p, a, rem))
            
            st.markdown("<div style='padding-top: 5px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Add Another Pay Out Row", key="add_row_out_btn", use_container_width=True):
                st.session_state.num_rows_out += 1
                st.rerun()

        # Live Calculation Processing
        total_today_receive = sum(x[1] for x in inputs_in)
        grand_total_receive = total_opening_calc + total_today_receive
        total_today_payout = sum(x[1] for x in inputs_out)
        
        cl_vault = grand_total_receive - total_today_payout - (m_bank + m_advance + m_due)
        total_closing_calc = cl_vault + m_bank + m_advance + m_due
        grand_total_payout = total_today_payout + total_closing_calc 

        placeholder_vault_cash_text.markdown(f'<div class="meta-value-vertical">{cl_vault:,.2f} ৳</div>', unsafe_allow_html=True)
        placeholder_total_closing_text.markdown(f'<div class="summary-value-vertical" style="color:#ff5555; font-weight:bold;">{total_closing_calc:,.2f} ৳</div>', unsafe_allow_html=True)

        placeholder_left_summary.markdown(f"""
            <div style="margin-top:10px;">
                <div class="summary-label-vertical" style="display:inline-block; width:55%;">Today's Receive:</div>
                <div class="summary-value-vertical" style="display:inline-block; width:43%;">{total_today_receive:,.2f} ৳</div>
                <hr class="meta-hr">
                <div class="summary-label-vertical" style="display:inline-block; width:55%; font-weight:bold;">Grand Total:</div>
                <div class="summary-grand-value" style="display:inline-block; width:43%;">{grand_total_receive:,.2f} ৳</div>
            </div>
        """, unsafe_allow_html=True)

        placeholder_right_summary.markdown(f"""
            <div style="margin-top:10px;">
                <div class="summary-label-vertical" style="display:inline-block; width:55%;">Today's Pay Out:</div>
                <div class="summary-value-vertical" style="display:inline-block; width:43%;">{total_today_payout:,.2f} ৳</div>
                <hr class="meta-hr">
                <div class="summary-label-vertical" style="display:inline-block; width:55%; font-weight:bold;">Grand Total:</div>
                <div class="summary-grand-value" style="display:inline-block; width:43%; color:#ff5555;">{grand_total_payout:,.2f} ৳</div>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔒 Save Complete Khata for This Date to Database", type="primary", use_container_width=True, key="save_cash_master_btn"):
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
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
                st.toast(f"🎉 Complete khata for {date_str} saved to database!", icon="✅")
                time.sleep(0.4); st.rerun()
            except Exception as e: 
                st.error(f"Error saving data: {e}")
            finally: 
                conn.close()

    # ======================================================================
    # TAB 2: Cash Report View Panel
    # ======================================================================
    with tab2:
        st.markdown("##### 📊 Dynamic Cash Transaction Ledger & Filter Report")
        f_col1, f_col2, f_col3, f_col4 = st.columns([2.5, 2.5, 4, 3])
    
        with f_col1: 
            start_d = st.date_input("Start Date", datetime.now().date().replace(day=1), format="DD-MM-YYYY", key="cash_rep_start")
        with f_col2: 
            end_d = st.date_input("End Date", datetime.now().date(), format="DD-MM-YYYY", key="cash_rep_end")
        with f_col3:
            conn = sqlite3.connect(DB_NAME)
            db_parties_report = [r[0] for r in conn.execute("SELECT party_name FROM second_parties WHERE company=? ORDER BY party_name ASC", (current_company,)).fetchall()]
            conn.close()
            all_report_parties = ["Bank", "Petty_Cash"] + db_parties_report
            sel_party = st.selectbox("Select Specific Second Party", options=["All Parties Together"] + all_report_parties, key="cash_rep_party")
        with f_col4: 
            sel_type = st.selectbox("Transaction Type", options=["All Transactions (In & Out)", "Only Received (Cash In)", "Only Expense (Cash Out)"], key="cash_rep_type")
            
        query = """
            SELECT date as 'Date', second_party as 'Second Party', type as 'Type', amount as 'Amount (৳)', remarks as 'Details' 
            FROM cash_transactions 
            WHERE company=? AND type IN ('Cash In', 'Cash Out') AND date BETWEEN ? AND ?
        """
        params = [current_company, start_d.strftime('%Y-%m-%d'), end_d.strftime('%Y-%m-%d')]
        if sel_party != "All Parties Together": 
            query += " AND second_party=?"
            params.append(sel_party)
        if sel_type == "Only Received (Cash In)": 
            query += " AND type='Cash In'"
        elif sel_type == "Only Expense (Cash Out)": 
            query += " AND type='Cash Out'"
        query += " ORDER BY date DESC, id DESC"
        
        conn = sqlite3.connect(DB_NAME)
        report_df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if not report_df.empty:
            t_in = report_df[report_df['Type'] == 'Cash In']['Amount (৳)'].sum()
            t_out = report_df[report_df['Type'] == 'Cash Out']['Amount (৳)'].sum()
            net_bal = t_in - t_out
            
            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("🟢 Total Received", f"{t_in:,.2f} ৳")
            m2.metric("🔴 Total Expense", f"{t_out:,.2f} ৳")
            m3.metric("⚖️ Net Balance", f"{net_bal:,.2f} ৳", delta=f"{net_bal:,.2f} ৳")
            
            st.markdown("---")
            
            try:
                report_df['Date'] = pd.to_datetime(report_df['Date']).dt.strftime('%d-%m-%Y')
            except Exception:
                pass
                
            st.dataframe(report_df, use_container_width=True, hide_index=True)
            
            summary_query = """
                SELECT second_party as 'Second Party',
                       SUM(CASE WHEN type='Cash In' THEN amount ELSE 0 END) as 'Total Received (৳)',
                       SUM(CASE WHEN type='Cash Out' THEN amount ELSE 0 END) as 'Total Expense (৳)'
                FROM cash_transactions 
                WHERE company=? AND type IN ('Cash In', 'Cash Out') AND date BETWEEN ? AND ?
            """
            sum_params = [current_company, start_d.strftime('%Y-%m-%d'), end_d.strftime('%Y-%m-%d')]
            if sel_party != "All Parties Together": 
                summary_query += " AND second_party=?"
                sum_params.append(sel_party)
            summary_query += " GROUP BY second_party ORDER BY second_party ASC"
            
            conn = sqlite3.connect(DB_NAME)
            sum_df = pd.read_sql_query(summary_query, conn, params=sum_params)
            conn.close()
      
            sum_df['Net Impact (৳)'] = sum_df['Total Received (৳)'] - sum_df['Total Expense (৳)']
            st.markdown("<br>📊 **Party-wise Aggregated Summary:**", unsafe_allow_html=True)
            st.dataframe(sum_df, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ No transactions found for selected filter.")

    # ======================================================================
    # TAB 3: Second Party Management Panel
    # ======================================================================
    with tab3:
        st.markdown("##### 👥 Second Party Management Panel")
        
        # --- 1. Manual Entry Section ---
        with st.expander("➕ Add New Party (Manually add new account)"):
            with st.form("add_sp_form", clear_on_submit=True):
                party_name = st.text_input("Second Party Name (English Only) *")
                contact = st.text_input("Contact Number")
                c1 = st.text_input("Comments 01")
                c2 = st.text_input("Comments 02")
                
                if st.form_submit_button("💾 Save Second Party"):
                    if not party_name.strip():
                        st.error("Name is required!")
                    elif contact.strip() and any(c.isalpha() for c in contact):
                        st.error("❌ Contact number contains letters! Only numbers allowed.")
                    else:
                        try:
                            clean_num = contact.strip()
                            if clean_num.endswith('.0'): clean_num = clean_num[:-2]
                            
                            with sqlite3.connect(DB_NAME) as conn:
                                conn.execute("""INSERT INTO second_parties 
                                             (company, party_name, contact_number, comments_01, comments_02, status) 
                                             VALUES (?, ?, ?, ?, ?, 'Active')""",
                                             (current_company, party_name.strip(), clean_num, c1.strip(), c2.strip()))
                            st.toast(f"🎉 '{party_name}' added successfully!", icon="✅")
                            time.sleep(1)
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Account with this name already exists!")
                        except Exception as e:
                            st.error(f"Error saving data: {e}")

        st.markdown("---")

        # --- 2. Excel Bulk Upload & Download ---
        p_col1, p_col2 = st.columns([1, 1])
        with p_col1:
            st.markdown("**1. Download Sample File:**")
            st.markdown("<div style='padding-top: 12px;'></div>", unsafe_allow_html=True)
            sample_df = pd.DataFrame({
                'Party_Name': ['Siddique_Enterprise', 'Rahman_Traders'], 
                'Contact_Number': ['01711000000', '01911000000'], 
                'Comments_01': ['ROI Party', 'Merchant Party'],
                'Comments_02': ['Dhaka', 'Khulna']
            })
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer: sample_df.to_excel(writer, index=False)
            st.download_button("📥 Download Sample (.xlsx)", buffer.getvalue(), "sample_second_parties.xlsx", key="party_sample_dl_btn")
            
        with p_col2:
            st.markdown("**2. Excel File Upload (Bulk Upload):**")
            uploaded_file = st.file_uploader("Upload Excel", type=["xlsx", "csv"], label_visibility="collapsed", key=f"party_uploader_{st.session_state.party_uploader_key}")
            
            if uploaded_file is not None:
                # Preview & Live Validation Run
                preview_df, has_error = preview_and_validate_excel(uploaded_file, current_company)
                if preview_df is not None:
                    st.session_state.party_preview = preview_df
                    st.session_state.party_has_error = has_error

        # --- 3. Excel Save & Validation Interface Logic ---
        if st.session_state.party_preview is not None:
            df = st.session_state.party_preview
            has_error = st.session_state.get('party_has_error', False)
            
            total_rows = len(df)
            error_count = len(df[df['Status'] == "❌ Error"])
            dup_count = len(df[df['Status'] == "⚠️ Duplicate"])
            ready_count = len(df[df['Status'] == "✅ Ready"])
            
            st.markdown("---")
            st.write("### 📋 Upload Preview & Live Status Check:")
            
            # Status Column Coloring Style
            def style_status(val):
                if "❌" in val: return 'background-color: #ffcccc; color: black; font-weight: bold;'
                if "⚠️" in val: return 'background-color: #fff0b3; color: black; font-weight: bold;'
                return 'background-color: #d1e7dd; color: black; font-weight: bold;'
                
            styled_df = df.style.applymap(style_status, subset=['Status'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

            sc1, sc2, sc3 = st.columns(3)
            
            # Safety Lock Control
            if has_error:
                st.error(f"🛑 File has {error_count} critical errors. Fix red marked rows and re-upload.")
                sc1.button("💾 Save Locked (Fix errors)", disabled=True, key="save_disabled_unique_btn", use_container_width=True)
                sc2.button("🔄 Replace Locked", disabled=True, key="save_disabled_replace_btn", use_container_width=True)
            else:
                if dup_count > 0:
                    st.warning(f"⚠️ File has {dup_count} duplicate accounts found.")
                else:
                    st.success(f"🎉 All file data perfect! {ready_count} accounts ready to add.")

                # Button 1: Save Only Unique Data
                if sc1.button("✅ Save Only Unique Data (Skip Duplicates)", use_container_width=True, key="save_unique_party_btn"):
                    inserted_count, skipped_count = 0, 0
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        for _, row in df.iterrows():
                            if row['Status'] == "✅ Ready":
                                try:
                                    cursor.execute("""
                                        INSERT INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status)
                                        VALUES (?, ?, ?, ?, ?, 'Active')
                                    """, (current_company, row['Party_Name'], row['Contact_Number'], row['Comments_01'], row['Comments_02']))
                                    inserted_count += 1
                                except sqlite3.IntegrityError:
                                    skipped_count += 1
                        conn.commit()
                    
                    if inserted_count > 0: st.toast(f"💾 {inserted_count} accounts saved successfully!", icon="✅")
                    if skipped_count > 0: st.toast(f"⚠️ {skipped_count} duplicates skipped.", icon="ℹ️")
                    
                    st.session_state.party_preview = None
                    st.session_state.party_uploader_key += 1
                    time.sleep(1); st.rerun()
                        
                # Button 2: Delete & Fresh Replace
                if sc2.button("🔄 Delete All & Replace with New Data", use_container_width=True, key="replace_all_party_btn"):
                    inserted_count = 0
                    with sqlite3.connect(DB_NAME) as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM second_parties WHERE company=?", (current_company,))
                        for _, row in df.iterrows():
                            if row['Status'] in ["✅ Ready", "⚠️ Duplicate"]:
                                try:
                                    cursor.execute("""
                                        INSERT OR REPLACE INTO second_parties (company, party_name, contact_number, comments_01, comments_02, status)
                                        VALUES (?, ?, ?, ?, ?, 'Active')
                                    """, (current_company, row['Party_Name'], row['Contact_Number'], row['Comments_01'], row['Comments_02']))
                                    inserted_count += 1
                                except Exception:
                                    pass
                        conn.commit()
                        
                    st.toast(f"♻️ {inserted_count} records replaced successfully!", icon="🔄")
                    st.session_state.party_preview = None
                    st.session_state.party_uploader_key += 1
                    time.sleep(1); st.rerun()
            
            # Button 3: Cancel Preview
            if sc3.button("❌ Cancel Preview", use_container_width=True, key="cancel_party_preview_btn"):
                st.session_state.party_preview = None
                st.session_state.party_uploader_key += 1
                st.rerun()

        st.markdown("---")

        # --- 4. Saved Second Parties List & Excel Export ---
        with sqlite3.connect(DB_NAME) as conn:
            try:
                query = "SELECT id, party_name, contact_number, comments_01, comments_02, status FROM second_parties WHERE company=?"
                p_data = pd.read_sql(query, conn, params=(current_company,))
            except:
                p_data = pd.DataFrame()

        l_col1, l_col2 = st.columns([2, 1])
        with l_col1:
            st.write("### 📋 Second Party List")
        with l_col2:
            if not p_data.empty:
                export_df = p_data.copy()
                export_df = export_df.rename(columns={'party_name': 'Party_Name', 'contact_number': 'Contact_Number', 'comments_01': 'Comments_01', 'comments_02': 'Comments_02', 'status': 'Status'})
                export_df = export_df[['Party_Name', 'Contact_Number', 'Comments_01', 'Comments_02', 'Status']]
                
                ex_buffer = io.BytesIO()
                with pd.ExcelWriter(ex_buffer, engine='xlsxwriter') as writer: export_df.to_excel(writer, index=False)
                
                st.download_button(
                    label="📥 Download Excel (Export)",
                    data=ex_buffer.getvalue(),
                    file_name=f"{current_company.replace(' ', '_')}_parties.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="party_main_export_btn"
                )

        if not p_data.empty:
            h1, h2, h3, h4 = st.columns([4, 2, 2, 2])
            h1.markdown("<div class='party-header'>Account Name</div>", unsafe_allow_html=True)
            h2.markdown("<div class='party-header'>Contact Number</div>", unsafe_allow_html=True)
            h3.markdown("<div class='party-header'>Status</div>", unsafe_allow_html=True)
            h4.markdown("<div class='party-header'>Action</div>", unsafe_allow_html=True)
            
            for _, row in p_data.iterrows():
                p_id = row['id']
                p_name = str(row['party_name'])
                p_contact = str(row['contact_number']) if row['contact_number'] else "-"
                p_status = str(row['status'])
                
                cols = st.columns([4, 2, 2, 2])
                cols[0].markdown(f"<div class='party-row'>🔹 **{p_name}**</div>", unsafe_allow_html=True)
                cols[1].markdown(f"<div class='party-row'>{p_contact}</div>", unsafe_allow_html=True)
                
                status_html = "🟢 Active" if p_status == 'Active' else "🔴 Inactive"
                cols[2].markdown(f"<div class='party-row'>{status_html}</div>", unsafe_allow_html=True)
                
                ac1, ac2 = cols[3].columns(2)
                if ac1.button("⚙️", key=f"m_sp_{p_id}", help="Manage/Edit"):
                    show_edit_party_dialog(p_id)
                    
                if ac2.button("❌", key=f"d_sp_{p_id}", help="Delete"):
                    show_party_popup(f"Are you sure you want to permanently delete second party **'{p_name}'**?", action_type="delete_party", row_id=p_id)
        else:
            st.info("No second parties found for this company.")

        # --- 5. Bulk Delete Button Triple-Confirmation Logic ---
        if not p_data.empty:
            st.divider()
            if st.button("⚠️ Delete All Second Parties (Bulk Delete)", key="bulk_delete_parties_main_btn", use_container_width=True):
                show_party_popup(
                    "⚠️ **WARNING!** You want to permanently delete ALL second parties for this company? This cannot be undone.", 
                    action_type="bulk_delete_party"
                )

if __name__ == "__main__":
    st.set_page_config(page_title="Cash Management DB", layout="wide")
    show_cash_management()
