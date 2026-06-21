        # ==============================================================================
        # 🟩 এজেন্ডা ১: ইনপুট বক্সের ভেতরের স্পেস সর্বনিম্নকরণ ও রো সিঙ্ক (আপডেট করা)
        # ==============================================================================
        st.markdown("""
        <style>
        /* ১. ইনপুট বক্সের ভেতরের টেক্সটের ওপর-নিচের স্পেস (Padding) সর্বনিম্ন করা */
        .stNumberInput input {
            padding-top: 2px !important;
            padding-bottom: 2px !important;
            height: 30px !important; /* বক্সের উচ্চতা ৪২px থেকে কমিয়ে ৩০px করা হলো */
            line-height: 1 !important;
            font-size: 14px !important;
        }
        
        /* ২. স্ট্রিমলিটের ডিফল্ট বেস-ইনপুট কন্টেইনারের হাইট লক করা */
        .stNumberInput div[data-baseweb="base-input"] {
            height: 30px !important;
            min-height: 30px !important;
        }

        /* ৩. বাম ও ডান পাশের প্রতিটি রো-এর উচ্চতা ইনপুট বক্সের সাথে মিলিয়ে ৩০px করা */
        .meta-label-vertical, .meta-value-vertical, 
        .summary-label-vertical, .summary-value-vertical {
            min-height: 30px; /* নতুন স্লিম বক্সের সাথে পারফেক্ট সিঙ্ক */
            display: flex;
            align-items: center; /* ভার্টিক্যালি একদম মাঝখানে থাকবে */
            margin: 0 !important;
            padding: 0 !important;
        }
        .meta-value-vertical, .summary-value-vertical {
            justify-content: flex-end;
        }
        
        /* ৪. অনুভূমিক রেখার মার্জিন কিছুটা কমিয়ে আনা */
        .meta-hr {
            margin-top: 10px !important;
            margin-bottom: 10px !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # ─── [ধাপ ১] প্রধান হেডার অংশ ───
        main_col1, main_col2 = st.columns(2)
        with main_col1:
            st.markdown("""
                <div class="hdr-green" style="margin-bottom: 0px !important; padding-bottom: 0px !important;">🛸 CASH RECEIVE (জমা)</div>
                <div class="folder-lbl" style="margin-top: 2px !important; padding-top: 0px !important;">📁 Opening Cash:</div>
            """, unsafe_allow_html=True)
            
        with main_col2:
            st.markdown("""
                <div class="hdr-red" style="margin-bottom: 0px !important; padding-bottom: 0px !important;">🛸 PAY OUT</div>
                <div class="folder-lbl" style="margin-top: 2px !important; padding-top: 0px !important;">📁 Closing Balances:</div>
            """, unsafe_allow_html=True)

        # ─── [ধাপ ২] রো ১: Vault Cash এলাইনমেন্ট লক ───
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            l_r1_c1, l_r1_c2 = st.columns([7, 5])
            l_r1_c1.markdown('<div class="meta-label-vertical">Opening Vault Cash:</div>', unsafe_allow_html=True)
            l_r1_c2.markdown(f'<div class="meta-value-vertical">{op_vault_val:,.2f} ৳</div>', unsafe_allow_html=True)
        with row1_col2:
            r_r1_c1, r_r1_c2 = st.columns([7, 5])
            r_r1_c1.markdown('<div class="meta-label-vertical">Vault Cash:</div>', unsafe_allow_html=True)
            placeholder_vault_cash_text = r_r1_c2.empty()

        # ─── [ধাপ ৩] রো ২: DM & DSS Bank এলাইনমেন্ট লক ───
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            l_r2_c1, l_r2_c2 = st.columns([7, 5])
            l_r2_c1.markdown('<div class="meta-label-vertical">DM & DSS Bank:</div>', unsafe_allow_html=True)
            l_r2_c2.markdown(f'<div class="meta-value-vertical">{op_bank_val:,.2f} ৳</div>', unsafe_allow_html=True)
        with row2_col2:
            r_r2_c1, r_r2_c2 = st.columns([7, 5])
            r_r2_c1.markdown('<div class="meta-label-vertical">DM & DSS Bank:</div>', unsafe_allow_html=True)
            m_bank = r_r2_c2.number_input("", min_value=0.0, step=1.0, key="m_inp_bank", label_visibility="collapsed")

        # ─── [ধাপ ৪] রো ৩: Market Advance এলাইনমেন্ট লক ───
        row3_col1, row3_col2 = st.columns(2)
        with row3_col1:
            l_r3_c1, l_r3_c2 = st.columns([7, 5])
            l_r3_c1.markdown('<div class="meta-label-vertical">Market Advance:</div>', unsafe_allow_html=True)
            l_r3_c2.markdown(f'<div class="meta-value-vertical">{op_adv_val:,.2f} ৳</div>', unsafe_allow_html=True)
        with row3_col2:
            r_r3_c1, r_r3_c2 = st.columns([7, 5])
            r_r3_c1.markdown('<div class="meta-label-vertical">Market Advance:</div>', unsafe_allow_html=True)
            m_advance = r_r3_c2.number_input("", min_value=0.0, step=1.0, key="m_inp_advance", label_visibility="collapsed")

        # ─── [ধাপ ৫] রো ৪: Others Due এলাইনমেন্ট লক ───
        row4_col1, row4_col2 = st.columns(2)
        with row4_col1:
            l_r4_c1, l_r4_c2 = st.columns([7, 5])
            l_r4_c1.markdown('<div class="meta-label-vertical">Others Due:</div>', unsafe_allow_html=True)
            l_r4_c2.markdown(f'<div class="meta-value-vertical">{op_due_val:,.2f} ৳</div>', unsafe_allow_html=True)
        with row4_col2:
            r_r4_c1, r_r4_c2 = st.columns([7, 5])
            r_r4_c1.markdown('<div class="meta-label-vertical">Others Due:</div>', unsafe_allow_html=True)
            m_due = r_r4_c2.number_input("", min_value=0.0, step=1.0, key="m_inp_due", label_visibility="collapsed")

        # ─── [ধাপ ৬] অনুভূমিক রেখা অংশ ───
        hr_col1, hr_col2 = st.columns(2)
        with hr_col1:
            st.markdown('<hr class="meta-hr">', unsafe_allow_html=True)
        with hr_col2:
            st.markdown('<hr class="meta-hr">', unsafe_allow_html=True)

        # ─── [ধাপ ৭] রো ৫: Total Opening & Closing Cash ───
        row5_col1, row5_col2 = st.columns(2)
        with row5_col1:
            l_r5_c1, l_r5_c2 = st.columns([7, 5])
            l_r5_c1.markdown('<div class="summary-label-vertical" style="color:#00ffaa; font-weight:bold;">Total Opening Cash:</div>', unsafe_allow_html=True)
            l_r5_c2.markdown(f'<div class="summary-value-vertical" style="color:#00ffaa; font-weight:bold;">{total_opening_calc:,.2f} ৳</div>', unsafe_allow_html=True)
        with row5_col2:
            r_r5_c1, r_r5_c2 = st.columns([7, 5])
            r_r5_c1.markdown('<div class="summary-label-vertical" style="color:#ff5555; font-weight:bold;">Total Closing Cash:</div>', unsafe_allow_html=True)
            placeholder_total_closing_text = r_r5_c2.empty()

        # ─── [ধাপ ৮] রো ৬: লাইভ গ্র্যান্ড টোটাল প্লেসহোল্ডার স্লট ───
        row6_col1, row6_col2 = st.columns(2)
        with row6_col1:
            placeholder_left_summary = st.empty()
        with row6_col2:
            placeholder_right_summary = st.empty()
