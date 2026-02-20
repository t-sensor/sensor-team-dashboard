import streamlit as st
from streamlit_local_storage import LocalStorage # 🌟 แก้ตรงนี้ครับ (เพิ่ม streamlit_ นำหน้า)
import requests
import json
import pandas as pd
import folium
from streamlit_folium import st_folium
import urllib.parse
import plotly.express as px
import time

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Sensor Team System", page_icon="⚙️", layout="wide")

# กุญแจเชื่อมต่อ GSheet
GAS_URL = st.secrets["GAS_URL"]
SHEET_URL = st.secrets["SHEET_URL"]


# 🌟 --- ฟังก์ชันส่วนกลาง --- 🌟
# 🌟 --- ฟังก์ชันส่วนกลาง --- 🌟
@st.cache_data(ttl=5) # 🚀 ลดเวลาให้เหลือ 5 วินาที
def load_sheet(sheet_name):
    import time
    sheet_id = SHEET_URL.split("/d/")[1].split("/")[0]
    encoded_sheet_name = urllib.parse.quote(sheet_name)
    
    # 🚀 ทะลวง Cache Google ด้วยการแนบเวลาปัจจุบัน (&t=...) ต่อท้ายลิงก์
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}&t={int(time.time())}"
    
    return pd.read_csv(csv_url)

# =========================================================
# 🔐 ระบบตรวจสอบการ Login (จำรหัสด้วย Local Storage)
# =========================================================
# เรียกใช้ระบบความจำของเบราว์เซอร์
localS = LocalStorage()

# 1. ตั้งค่าเริ่มต้นให้ Session
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''
    st.session_state['role'] = ''

# 2. เช็คว่าเบราว์เซอร์เคยจำรหัสผ่านไว้ไหม (ถ้าเคย ให้ข้ามหน้า Login ไปเลย!)
if localS.getItem("logged_in") == "true":
    st.session_state['logged_in'] = True
    st.session_state['username'] = localS.getItem("username")
    st.session_state['role'] = localS.getItem("role")

# 3. หน้าต่าง Login
if not st.session_state['logged_in']:
    st.markdown("<h1 style='text-align: center; color: #008080;'>🔐 Sensor Team Login</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.info("กรุณาเข้าสู่ระบบ หากยังไม่มีรหัส กรุณาลงทะเบียนและรออนุมัติ")
        with st.form("login_form"):
            input_user = st.text_input("👤 Username")
            input_pass = st.text_input("🔑 Password", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)
            
            if submitted:
                if input_user and input_pass:
                  with st.spinner("กำลังตรวจสอบข้อมูล..."):
                        try:
                            df_users = load_sheet("Users_DB")
                            
                            # 👇 แทรกบรรทัดนี้ลงไปตรงนี้เลยครับ (ระหว่าง load_sheet กับ df_users.columns)
                            st.write("👀 แอบดูข้อมูลที่ดึงมาได้:", df_users)
                            
                            df_users.columns = [str(c).replace('\n', '').strip() for c in df_users.columns]
                            
                            if 'Username' in df_users.columns and 'Password' in df_users.columns:
                                df_users['Username'] = df_users['Username'].astype(str).str.strip()
                                df_users['Password'] = df_users['Password'].astype(str).str.strip()
                                
                                user_record = df_users[(df_users['Username'] == input_user.strip()) & (df_users['Password'] == input_pass.strip())]
                                
                                if not user_record.empty:
                                    status = str(user_record.iloc[0].get('Status', '')).strip()
                                    if status.lower() == 'approved':
                                        # 🌟 ล็อกอินผ่าน -> สั่งให้เบราว์เซอร์จำข้อมูลไว้เลย
                                        role_val = str(user_record.iloc[0].get('Role', 'user')).strip()
                                        localS.setItem("logged_in", "true")
                                        localS.setItem("username", input_user.strip())
                                        localS.setItem("role", role_val)
                                        
                                        # อัปเดตสถานะให้เว็บ
                                        st.session_state['logged_in'] = True
                                        st.session_state['username'] = input_user.strip()
                                        st.session_state['role'] = role_val
                                        
                                        st.success("เข้าสู่ระบบสำเร็จ! กรุณารอสักครู่...")
                                        time.sleep(1)
                                        st.rerun() 
                                    else:
                                        st.error("⚠️ บัญชีของคุณอยู่ระหว่างรอผู้ดูแลระบบอนุมัติครับ")
                                else:
                                    st.error("❌ Username หรือ Password ไม่ถูกต้อง")
                            else:
                                st.error("ไม่พบคอลัมน์ 'Username' หรือ 'Password' ใน Google Sheets")
                        except Exception as e:
                            st.warning(f"รอการเชื่อมต่อฐานข้อมูล Users_DB ({e})")
                else:
                    st.warning("กรุณากรอกข้อมูลให้ครบถ้วน")
        
        st.markdown("<br><center>ยังไม่มีบัญชีผู้ใช้งาน? <a href='https://docs.google.com/forms/d/e/1FAIpQLSeqVZReF49TvuHi7aIr__TMM0_7x4771PF7cg_VXpO1lyQjHw/viewform' target='_blank'>คลิกที่นี่เพื่อลงทะเบียน</a></center>", unsafe_allow_html=True)
    
    st.stop()
# =========================================================
# 🎉 2. ส่วนแสดงเมนูเมื่อ Login ผ่าน (Role-based Access)
# =========================================================
CURRENT_USER = st.session_state['username']
CURRENT_ROLE = st.session_state['role'].lower()

# --- 3. สร้างระบบเมนูแถบด้านข้าง (Sidebar) ตามสิทธิ์ ---
st.sidebar.title("🛠️ Sensor Team Menu")

# เช็คสิทธิ์ (Admin กับ Member เห็นทุกอย่าง / User เห็นแค่บางเมนู)
if CURRENT_ROLE in ['admin', 'member']:
    menu_options = [
        "🏠 1. ภาพรวมและสถิติ (Dashboard)",
        "🏢 2. เจาะลึกรายไซต์ (Site Detail)",
        "📱 3. กระดานงานส่วนตัว (My Workload)",
        "📊 4. ภาพรวมงานของทีม (Team Manager)",
        "🧰 5. ระบบเบิก-คืนอุปกรณ์ (Tools)",
        "👥 6. ข้อมูลทีม (Team Profile)",
        "🧠 7. ศูนย์การเรียนรู้ (Learning & Quiz)",
        "📚 8. คู่มือการใช้งาน (Manuals & Docs)"
    ]
else:
    # สิทธิ์ระดับ user (ลูกค้า/ภายนอก) ดูได้แค่หน้าเหล่านี้ (ปรับแก้ได้ตามต้องการครับ)
    menu_options = [
        "🏠 1. ภาพรวมและสถิติ (Dashboard)",
        "🏢 2. เจาะลึกรายไซต์ (Site Detail)",
        "📚 8. คู่มือการใช้งาน (Manuals & Docs)"
    ]

menu = st.sidebar.radio("เลือกเมนูการใช้งาน:", menu_options)

st.sidebar.markdown("---")
# โชว์ป้ายชื่อและตำแหน่งสุดเท่
role_color = "🟢" if CURRENT_ROLE == 'admin' else ("🔵" if CURRENT_ROLE == 'member' else "⚪")
st.sidebar.info(f"👨‍💻 เข้าสู่ระบบโดย: **{CURRENT_USER}**\n\n{role_color} ระดับสิทธิ์: {CURRENT_ROLE.upper()}")

# ปุ่ม Logout
# ปุ่ม Logout
if st.sidebar.button("🚪 ออกจากระบบ", use_container_width=True):
    # ล้างความจำในเบราว์เซอร์
    localS.deleteAll()
    
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''
    st.session_state['role'] = ''
    time.sleep(1)
    st.rerun()

# --- 4. โครงสร้างแต่ละเมนู (โค้ด Dashboard ที่เหลือของคุณ Heart จะต่อจากตรงนี้ลงไปเหมือนเดิมครับ) ---
# --- ส่วนที่ 1: Dashboard อัจฉริยะ (เมนู 1) ---
if menu == "🏠 1. ภาพรวมและสถิติ (Dashboard)":
    st.title("📊 ศูนย์บัญชาการทีม Sensor (Command Center)")
    st.write("ภาพรวมสรุปข้อมูล แผนที่ และสถานะ PM อัจฉริยะแบบ Real-time")
    st.markdown("---")

    try:
        # 1. โหลดข้อมูลพื้นฐาน
        df_pm = load_sheet("PM_Plan")
        df_task = load_sheet("Task & Workload")
        df_master = load_sheet("Master_Site")
        
        for df in [df_pm, df_task, df_master]:
            if not df.empty: df.columns = [str(c).strip() for c in df.columns]

        # 📅 ระบบเวลา Real-time
        import datetime
        now = datetime.datetime.now()
        cur_m = now.month
        thai_months = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]
        cur_m_name = thai_months[cur_m - 1]

        # 2. สรุปตัวเลข KPI
        # นับจำนวนไซต์จาก Master_Site เพื่อความแม่นยำ
        total_sites_count = len(df_master['ชื่อไซต์งาน (Process Work)'].dropna().unique()) if 'ชื่อไซต์งาน (Process Work)' in df_master.columns else 0
        active_tasks = len(df_task[df_task['สถานะงาน'] != 'Complete']) if 'สถานะงาน' in df_task.columns else 0
        
        c1, c2, c3 = st.columns(3)
        c1.metric("🏢 จำนวนไซต์งานทั้งหมด", f"{total_sites_count} ไซต์")
        c2.metric("📋 งานที่กำลังทำ", f"{active_tasks} งาน")
        c3.metric("📅 เดือนปัจจุบัน", cur_m_name)

        # 🔍 ปุ่ม Filter Real-time
        st.markdown("### 🔍 เลือกดูสถานะตามกำหนดการ PM")
        filter_choice = st.radio("คัดกรองไซต์งาน:", 
                                 ["แสดงทั้งหมด", "🔴 ผ่านมาแล้ว (เลยกำหนด)", "🟠 เดือนนี้ (ต้องเข้าทำ)", "🟡 เดือนหน้า (เตรียมตัว)", "🟢 PM เรียบร้อยแล้ว / ยังไม่ถึงรอบ"], 
                                 horizontal=True)

        # 🧠 Logic วิเคราะห์สีและสถานะ
        pm_status_list = []
        site_colors = {}
        pm_cols = ['PM ใหญ่', 'PM ย่อย ครั้งที่ 1', 'PM ย่อย ครั้งที่ 2', 'PM ย่อย ครั้งที่ 3']

        for _, row in df_pm.iterrows():
            site_name = str(row['ชื่อไซต์งาน']).strip()
            pm_done = str(row.get('สถานะ PM', '')).strip()
            
            if "PM แล้ว" in pm_done:
                final_status, m_color, due_date = "🟢 PM เรียบร้อยแล้ว / ยังไม่ถึงรอบ", "green", "Completed"
            else:
                # 🛠️ จุดที่แก้ไข: เปลี่ยนจาก row[col] เป็น row[c] เพื่อแก้ Error
                site_dates = [str(row[c]).strip() for c in pm_cols if c in row and str(row[c]).strip() not in ["nan", "-", ""]]
                final_status, m_color, due_date = "🟢 PM เรียบร้อยแล้ว / ยังไม่ถึงรอบ", "green", "-"
                p_score = 4 
                
                for d_str in site_dates:
                    m_part = d_str.split(' ')[0]
                    if m_part in thai_months:
                        m_idx = thai_months.index(m_part) + 1
                        if m_idx < cur_m: 
                            if p_score > 1: final_status, m_color, due_date, p_score = "🔴 ผ่านมาแล้ว (เลยกำหนด)", "red", d_str, 1
                        elif m_idx == cur_m: 
                            if p_score > 2: final_status, m_color, due_date, p_score = "🟠 เดือนนี้ (ต้องเข้าทำ)", "orange", d_str, 2
                        elif m_idx == cur_m + 1 or (cur_m == 12 and m_idx == 1): 
                            if p_score > 3: final_status, m_color, due_date, p_score = "🟡 เดือนหน้า (เตรียมตัว)", "beige", d_str, 3

            site_colors[site_name] = m_color
            pm_status_list.append({"ชื่อไซต์งาน": site_name, "สถานะ": final_status, "กำหนดการ": due_date})

        df_status = pd.DataFrame(pm_status_list)
        
        # 🌟 เพิ่มส่วนแสดงรายชื่อไซต์งานทั้งหมดที่มี
        with st.expander(f"📂 รายชื่อไซต์งานทั้งหมด ({total_sites_count} ไซต์)"):
            if not df_master.empty:
                st.dataframe(df_master[[ 'ชื่อไซต์งาน (Process Work)']],  hide_index=True)
            else:
                st.info("ไม่มีข้อมูลใน Master_Site")

        # ตารางสถานะที่กรองแล้ว
        if filter_choice != "แสดงทั้งหมด":
            df_status = df_status[df_status['สถานะ'] == filter_choice]
        
        st.markdown("### 🗓️ ตารางติดตามสถานะ PM")
        st.dataframe(df_status.sort_values(by="สถานะ"), use_container_width=True, hide_index=True)

        # 🗺️ แผนที่
        st.markdown("### 🗺️ แผนที่พิกัดไซต์งาน (สีหมุดตามสถานะ PM)")
        if not df_master.empty and 'ละติจูด (Latitude)' in df_master.columns:
            m = folium.Map(location=[13.73, 100.52], zoom_start=6)
            for _, r in df_master.dropna(subset=['ละติจูด (Latitude)', 'ลองจิจูด (Longitude)']).iterrows():
                s_name = str(r['ชื่อไซต์งาน (Process Work)']).strip()
                dot_color = site_colors.get(s_name, "gray")
                folium.Marker([r['ละติจูด (Latitude)'], r['ลองจิจูด (Longitude)']], 
                              popup=s_name, icon=folium.Icon(color=dot_color)).add_to(m)
            st_folium(m, width=1000, height=400)
            
    except Exception as e: 
        st.warning(f"ระบบกำลังโหลดข้อมูล... ({e})")

# --- ส่วนที่ 2: เพิ่มปุ่มกด PM แล้ว (เมนู 2) ---
# --- ส่วนที่ 2: เจาะลึกรายไซต์ (เมนู 2) ---
elif menu == "🏢 2. เจาะลึกรายไซต์ (Site Detail)":
    st.title("🏢 เจาะลึกข้อมูลรายไซต์ (Site Detail)")

    try:
        # โหลดข้อมูล Master Site เพื่อดึงรายชื่อไซต์
        df_master = load_sheet("Master_Site")
        site_list = df_master['ชื่อไซต์งาน (Process Work)'].dropna().unique().tolist()
        
        # ตรวจสอบการนำทางมาจากหน้า Dashboard (ถ้ามี)
        default_index = 0
        if 'selected_site_from_dashboard' in st.session_state:
            requested_site = st.session_state.selected_site_from_dashboard
            if requested_site in site_list:
                default_index = site_list.index(requested_site) + 1
            del st.session_state.selected_site_from_dashboard

        site_options = ["🌐 ดูแผน PM รวมทุกไซต์ (All Sites)"] + site_list
        selected_site = st.selectbox("🔍 ค้นหาหรือเลือกไซต์งานที่ต้องการดูข้อมูล:", site_options, index=default_index)
        
        st.markdown("---")
        
        if selected_site == "🌐 ดูแผน PM รวมทุกไซต์ (All Sites)":
            st.subheader("🌐 ภาพรวมตารางแผน PM ทุกไซต์งานประจำปี")
            try:
                df_pm_all = load_sheet("PM_Plan")
                st.dataframe(df_pm_all, use_container_width=True, hide_index=True)
                st.info("💡 เลื่อนแถบด้านล่างตารางไปทางขวา เพื่อดูเดือนอื่นๆ ได้เลยครับ")
            except Exception as e:
                st.error(f"ไม่สามารถโหลดข้อมูลแผน PM รวมได้: {e}")
                
        else:
            st.subheader(f"📍 ข้อมูลสรุปของไซต์: {selected_site}")
            tab1, tab2, tab3 = st.tabs(["🗓️ แผน PM (PM Plan)", "📡 อุปกรณ์ (Assets)", "🚨 ประวัติปัญหา (Issue Log)"])
            
            # --- Tab 1: แผน PM (PM ใหญ่ + PM ย่อย 1-3) ---
            with tab1:
                try:
                    df_pm = load_sheet("PM_Plan")
                    df_pm.columns = [str(c).strip() for c in df_pm.columns]
                    site_pm = df_pm[df_pm['ชื่อไซต์งาน'] == selected_site]
                    
                    if not site_pm.empty:
                        row_data = site_pm.iloc[0]
                        pm_done_status = str(row_data.get('สถานะ PM', '')).strip()
                        
                        # กรองเอาเฉพาะรอบการ PM 4 ครั้งตามเงื่อนไข
                        pm_cols = ['PM ใหญ่', 'PM ย่อย ครั้งที่ 1', 'PM ย่อย ครั้งที่ 2', 'PM ย่อย ครั้งที่ 3']
                        pm_schedule = []
                        for col in pm_cols:
                            if col in site_pm.columns:
                                val = str(row_data[col]).strip()
                                if val and val.lower() != 'nan' and val != '-':
                                    pm_schedule.append({"รอบการทำงาน": col, "กำหนดการ": val})
                        
                        st.success(f"📌 กำหนดการ PM ของ {selected_site}")
                        if pm_schedule:
                            st.table(pd.DataFrame(pm_schedule))
                        
                        # แยกบรรทัดที่ 5: วันที่ซิมหมดอายุ
                        if 'วันที่ซิมหมดอายุ' in site_pm.columns:
                            sim_date = str(row_data['วันที่ซิมหมดอายุ']).strip()
                            if sim_date and sim_date.lower() != 'nan' and sim_date != '-':
                                st.warning(f"📶 **วันที่ซิมหมดอายุ:** {sim_date}")

                        st.markdown("---")
                        
                        # ระบบปุ่มบันทึกสถานะ PM
                        if pm_done_status == "PM แล้ว":
                            st.info("✅ ไซต์นี้บันทึกว่าทำ PM เสร็จเรียบร้อยแล้ว")
                            if st.button(f"↩️ ยกเลิกสถานะ PM ของ {selected_site}", type="secondary"):
                                payload = {"action": "update_pm_status", "sheet": "PM_Plan", "siteName": selected_site, "status": ""}
                                res = requests.post(GAS_URL, data=json.dumps(payload))
                                st.cache_data.clear()
                                st.rerun()
                        else:
                            if st.button(f"✅ บันทึกว่า {selected_site} ทำ PM รอบนี้เสร็จแล้ว", type="primary"):
                                payload = {"action": "update_pm_status", "sheet": "PM_Plan", "siteName": selected_site, "status": "PM แล้ว"}
                                requests.post(GAS_URL, data=json.dumps(payload))
                                st.cache_data.clear()
                                st.rerun()
                    else:
                        st.info("ไม่พบข้อมูลแผนงานของไซต์นี้ใน PM_Plan")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในหน้า PM Plan: {e}")
                    
            # --- Tab 2: อุปกรณ์ที่ติดตั้ง (Assets) ---
            with tab2:
                try:
                    df_assets = load_sheet("Asset_Sensor")
                    df_assets.columns = [str(c).strip() for c in df_assets.columns]
                    # ค้นหาคอลัมน์ไซต์งานแบบยืดหยุ่น
                    site_col_assets = next((c for c in df_assets.columns if "ไซต์" in c or "Site" in c), None)
                    
                    if site_col_assets:
                        site_assets = df_assets[df_assets[site_col_assets] == selected_site]
                        if not site_assets.empty:
                            st.dataframe(site_assets.drop(columns=[site_col_assets]), use_container_width=True, hide_index=True)
                        else:
                            st.info(f"ไม่พบข้อมูลอุปกรณ์ของไซต์ {selected_site} ในแผ่น Asset_Sensor")
                    else:
                        st.warning("⚠️ ตาราง Asset_Sensor ไม่มีคอลัมน์ 'ชื่อไซต์งาน'")
                except Exception as e:
                    st.warning(f"ยังไม่สามารถดึงข้อมูลจากแผ่น Asset_Sensor ได้: {e}")
                    
            # --- Tab 3: ประวัติปัญหา (Issue Log) ---
            with tab3:
                has_log = False
                # 1. ดึง "หมายเหตุ" จาก PM_Plan มาแสดงก่อน
                try:
                    df_note = load_sheet("PM_Plan")
                    df_note.columns = [str(c).strip() for c in df_note.columns]
                    site_row = df_note[df_note['ชื่อไซต์งาน'] == selected_site]
                    if not site_row.empty and 'หมายเหตุ' in df_note.columns:
                        note = str(site_row.iloc[0]['หมายเหตุ']).strip()
                        if note and note.lower() != 'nan' and note != '-':
                            st.info(f"📝 **หมายเหตุจากแผนงาน:**\n\n{note}")
                            st.markdown("---")
                            has_log = True
                except: pass

                # 2. ดึงประวัติจาก Task & Workload
                try:
                    df_tasks = load_sheet("Task & Workload")
                    df_tasks.columns = [str(c).strip() for c in df_tasks.columns]
                    site_tasks = df_tasks[df_tasks['ชื่อไซต์งาน'] == selected_site]
                    if not site_tasks.empty:
                        st.markdown("🔍 **ประวัติการทำงานและปัญหา:**")
                        st.dataframe(site_tasks.drop(columns=['ชื่อไซต์งาน']), use_container_width=True, hide_index=True)
                        has_log = True
                except: pass

                # 3. ถ้าไม่มีทั้งคู่ค่อยโชว์ 🎉
                if not has_log:
                    st.success("🎉 ยังไม่เคยพบปัญหาร้ายแรงในไซต์นี้")

    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดที่เมนู 2: {e}")
        
#หน้า3 
#หน้า3 
elif menu == "📱 3. กระดานงานส่วนตัว (My Workload)":
    st.title("📱 กระดานงานส่วนตัว")
    
    # 1. กำหนดชื่อผู้ใช้งานปัจจุบัน (ดึงจากระบบ Login)
    # 🌟 อัปเดตให้ใช้ชื่อจาก Session ที่ล็อกอินเข้ามาแทนแบบ Fix ค่าเดิม
    CURRENT_USER = st.session_state.get('username', 'ไม่ระบุตัวตน')
    st.info(f"👤 สวัสดีครับคุณ **{CURRENT_USER}** นี่คืองานที่อยู่ในความรับผิดชอบของคุณครับ")

    # 2. --- ส่วนแสดงตารางงานของตัวเอง (คงของเดิมไว้ 100%) ---
    try:
        df_tasks = load_sheet("Task & Workload")
        
        if not df_tasks.empty:
            df_tasks.columns = [str(c).strip() for c in df_tasks.columns]
            
            if 'ผู้รับผิดชอบหลัก' in df_tasks.columns and 'ผู้ช่วย' in df_tasks.columns:
                df_tasks['ผู้รับผิดชอบหลัก'] = df_tasks['ผู้รับผิดชอบหลัก'].fillna("")
                df_tasks['ผู้ช่วย'] = df_tasks['ผู้ช่วย'].fillna("")
                
                my_tasks = df_tasks[
                    (df_tasks['ผู้รับผิดชอบหลัก'] == CURRENT_USER) | 
                    (df_tasks['ผู้ช่วย'].str.contains(CURRENT_USER, na=False))
                ]
                
                if not my_tasks.empty:
                    st.markdown("### 📋 รายการงานของคุณ")
                    display_cols = ['วันที่เข้าทำ (Scheduled Date)', 'ชื่อไซต์งาน', 'ชื่องาน / รายละเอียด', 'ประเภทงาน', 'สถานะงาน', 'ผู้ช่วย']
                    available_cols = [col for col in display_cols if col in df_tasks.columns]
                    st.dataframe(my_tasks[available_cols], use_container_width=True, hide_index=True)
                else:
                    st.success("🎉 ตอนนี้คุณไม่มีงานค้างเลยครับ พักผ่อนได้!")
            else:
                st.error("⚠️ หาหัวคอลัมน์ 'ผู้รับผิดชอบหลัก' หรือ 'ผู้ช่วย' ไม่เจอครับ")
                st.write("ชื่อคอลัมน์ที่ระบบอ่านได้จาก GSheet คือ:", df_tasks.columns.tolist())
        else:
            st.info("ตารางใน GSheet ยังว่างเปล่าครับ")
            
    except Exception as e:
        st.error(f"ระบบขัดข้อง: {e}")
    
    # 3. --- ส่วนฟอร์มกรอกงานด่วน (อัปเกรด Dropdown & อื่นๆ) ---
    st.markdown("### ➕ ฟอร์มแจ้งงานด่วน / อัปเดตงาน")
    
    # ดึงรายชื่อทีม
    team_members = ["Heart", "Phubeth", "Mink", "Film", "Folk", "Chan"]
    
    # 🌟 ดึงรายชื่อไซต์งานทั้งหมดมาทำ Dropdown
    try:
        df_master_m3 = load_sheet("Master_Site")
        site_list_m3 = df_master_m3['ชื่อไซต์งาน (Process Work)'].dropna().unique().tolist()
    except:
        site_list_m3 = []
        
    # เติมตัวเลือก "อื่นๆ" ไว้ล่างสุด
    site_options_m3 = site_list_m3 + ["➕ อื่นๆ (ระบุเอง)"]

    # 🌟 ใช้ st.container แทน st.form เพื่อให้โชว์ช่องพิมพ์ "อื่นๆ" ได้แบบ Real-time
    with st.container(border=True):
        col1, col2 = st.columns(2)
        
        with col1:
            # Dropdown เลือกไซต์งาน
            selected_site_m3 = st.selectbox("ชื่อไซต์งาน", site_options_m3)
            
            # ถ้าเลือกอื่นๆ ให้มีช่องพิมพ์โผล่มา
            if selected_site_m3 == "➕ อื่นๆ (ระบุเอง)":
                final_site_name = st.text_input("ระบุชื่อไซต์งานใหม่:", placeholder="พิมพ์ชื่อไซต์ที่นี่...")
            else:
                final_site_name = selected_site_m3
                
            task_detail = st.text_input("ชื่องาน / รายละเอียด", placeholder="เช่น เข้าไปเปลี่ยนซิมเร้าเตอร์")
            task_type = st.selectbox("ประเภทงาน", ["งานด่วน", "งานตามแพลน", "งานโปรเจกต์"])
            status = st.selectbox("สถานะงาน", ["Planning", "In progress", "Problem", "Complete"])
            
        with col2:
            start_date = st.date_input("วันที่เข้าทำ (Scheduled Date)")
            end_date = st.date_input("กำหนดเสร็จ (Deadline)")
            
            # 🌟 ให้ Default ผู้รับผิดชอบ เป็นชื่อคนที่ล็อกอินอยู่เลย (เพื่อความรวดเร็ว)
            default_assignee_idx = team_members.index(CURRENT_USER) if CURRENT_USER in team_members else 0
            assignee = st.selectbox("ผู้รับผิดชอบหลัก", team_members, index=default_assignee_idx)
            
            assistants = st.multiselect("ผู้ช่วย (ถ้ามี)", team_members)
            
        st.markdown("<br>", unsafe_allow_html=True)
        # เปลี่ยนเป็น st.button ธรรมดา (เพราะไม่ได้ใช้ st.form แล้ว)
        submitted = st.button("บันทึกข้อมูลลงตาราง", type="primary", use_container_width=True)
        
        if submitted:
            if final_site_name and task_detail:
                assistants_str = ", ".join(assistants)
                payload = {
                    "sheet": "Task & Workload",
                    "data": [
                        (pd.Timestamp.utcnow() + pd.Timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
                        final_site_name, task_detail, task_type, 
                        start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"), 
                        status, assignee, assistants_str
                    ]
                }
                with st.spinner("กำลังส่งข้อมูลเข้าตาราง..."):
                    try:
                        response = requests.post(GAS_URL, data=json.dumps(payload))
                        if response.json().get("status") == "success":
                            st.success(f"บันทึกงาน '{task_detail}' ที่ '{final_site_name}' สำเร็จ! 🎉")
                            st.cache_data.clear() # เคลียร์แคชเพื่อให้ตารางอัปเดตงานใหม่ทันที
                            st.rerun() # รีเฟรชหน้าเว็บทันที
                    except Exception as e:
                        st.error(f"ระบบขัดข้อง: {e}")
            else:
                st.warning("⚠️ กรุณากรอก 'ชื่อไซต์งาน' และ 'รายละเอียดงาน' ให้ครบถ้วนครับ")
elif menu == "📊 4. ภาพรวมงานของทีม (Team Manager)":
    st.title("📊 ภาพรวมงานของทีม (Team Workload)")
    st.write("ศูนย์บัญชาการสำหรับดูภาระงานของทุกคนในทีม เพื่อประกอบการตัดสินใจจ่ายงาน")
    
    try:
        df_tasks = load_sheet("Task & Workload")
        
        if not df_tasks.empty:
            df_tasks.columns = [str(c).strip() for c in df_tasks.columns]
            
            # --- 📈 ส่วนที่ 1: กราฟสรุปภาระงาน (Workload) ---
            st.markdown("### 📈 ภาระงานรายบุคคล (เฉพาะงานหลักที่รับผิดชอบ)")
            
            if 'ผู้รับผิดชอบหลัก' in df_tasks.columns:
                # กรองเอางานที่เสร็จแล้วออกไปก่อน (เพื่อดูเฉพาะงานที่กำลังทำหรือติดปัญหา)
                active_tasks = df_tasks[df_tasks['สถานะงาน'] != 'Complete']
                
                # นับจำนวนงานของแต่ละคน
                workload_count = active_tasks['ผู้รับผิดชอบหลัก'].value_counts().reset_index()
                workload_count.columns = ['ชื่อทีมงาน', 'จำนวนงาน (ชิ้น)']
                
                # วาดกราฟแท่งด้วย Plotly
                fig = px.bar(
                    workload_count, 
                    x='ชื่อทีมงาน', 
                    y='จำนวนงาน (ชิ้น)', 
                    text='จำนวนงาน (ชิ้น)',
                    color='ชื่อทีมงาน',
                    title="จำนวนงานที่ค้างอยู่ของแต่ละคน (Active Tasks)"
                )
                fig.update_traces(textposition='outside') # ให้ตัวเลขอยู่บนแท่งกราฟ
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            # --- 📋 ส่วนที่ 2: ตารางรวมงานทั้งหมด (พร้อมระบบ Filter) ---
            st.markdown("### 📋 ตารางติดตามงานของทีม (Team Task Tracker)")
            
            # สร้างตัวกรองข้อมูล (Filter)
            col1, col2 = st.columns(2)
            with col1:
                filter_status = st.multiselect(
                    "📌 กรองตามสถานะ:", 
                    ["Planning", "In progress", "Problem", "Complete"], 
                    default=["Planning", "In progress", "Problem"] # ค่าเริ่มต้นไม่โชว์งาน Complete
                )
            with col2:
                filter_person = st.selectbox(
                    "👤 ดูเฉพาะงานของ:", 
                    ["ดูทุกคน"] + ["Heart", "Phubeth", "Mink", "Film", "Folk", "Chan"]
                )
            
            # ทำการกรองข้อมูลตามที่ผู้ใช้เลือก
            filtered_df = df_tasks.copy()
            if filter_status:
                filtered_df = filtered_df[filtered_df['สถานะงาน'].isin(filter_status)]
                
            if filter_person != "ดูทุกคน":
                filtered_df = filtered_df[
                    (filtered_df['ผู้รับผิดชอบหลัก'] == filter_person) | 
                    (filtered_df['ผู้ช่วย'].str.contains(filter_person, na=False))
                ]
            
            # แสดงตารางผลลัพธ์
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            
        else:
            st.info("ยังไม่มีข้อมูลงานในระบบครับ")
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดตารางงาน: {e}")
elif menu == "🧰 5. ระบบเบิก-คืนอุปกรณ์ (Tools)":
    st.title("🧰 ระบบเบิก-คืนอุปกรณ์ส่วนกลาง")
    st.write("บันทึกประวัติ พร้อมระบบนับสต๊อกและคำนวณของคงเหลืออัตโนมัติ")
    
    # 1. ดึงข้อมูลรายชื่อไซต์และทีมงาน
    try:
        df_master = load_sheet("Master_Site")
        site_list = df_master['ชื่อไซต์งาน (Process Work)'].dropna().tolist()
    except:
        site_list = ["ไม่ระบุ / โชว์รูม"]
    team_members = ["Heart", "Phubeth", "Mink", "Film", "Folk", "Chan"]
    
    # 2. 🧮 ระบบคำนวณสต๊อกคงเหลือ (Inventory Engine)
    total_stock = {}     # เก็บของทั้งหมดที่มี
    borrowed_stock = {}  # เก็บของที่ถูกยืมไปแล้ว
    
    try:
        # โหลดคลังหลัก (Master_Equipment)
        df_equip = load_sheet("Master_Equipment")
        if 'Equipment' in df_equip.columns and 'Volume' in df_equip.columns:
            for _, row in df_equip.iterrows():
                tool_name = str(row['Equipment']).strip()
                volume = pd.to_numeric(row['Volume'], errors='coerce')
                if pd.notna(volume) and tool_name != "nan":
                    total_stock[tool_name] = int(volume)
                    borrowed_stock[tool_name] = 0 # ตั้งค่าเริ่มต้นของถูกยืมเป็น 0
                    
        # โหลดประวัติการยืม (Team_Tools) เพื่อหาของที่หายไปจากคลัง
        df_tools = load_sheet("Team_Tools")
        if not df_tools.empty:
            df_tools.columns = [str(c).strip() for c in df_tools.columns]
            # ตรวจสอบว่ามีคอลัมน์ใหม่ไหม (ถ้ายังไม่มี ให้ตีความว่าบรรทัดนั้นยืม 1 ชิ้น)
            has_qty_col = 'จำนวน' in df_tools.columns
            
            for _, row in df_tools.iterrows():
                # อิงตามคอลัมน์: 1=ผู้เบิก, 2=อุปกรณ์, 3=ไซต์, 4=สถานะ
                hist_tool = str(row.iloc[2]).strip()
                hist_status = str(row.iloc[4]).strip()
                
                # ดึงจำนวน (ถ้าไม่มีคอลัมน์ให้ใส่ 1)
                qty = float(row['จำนวน']) if has_qty_col and pd.notna(row.get('จำนวน')) else 1.0
                
                if hist_tool in borrowed_stock:
                    if "ยืม" in hist_status or "Borrow" in hist_status:
                        borrowed_stock[hist_tool] += qty
                    elif "คืน" in hist_status or "Return" in hist_status:
                        borrowed_stock[hist_tool] -= qty
                        
    except Exception as e:
        st.warning(f"ระบบกำลังรอข้อมูลคลังสินค้า: {e}")

    # 3. เตรียมตัวเลือก Dropdown พร้อมแสดงยอดคงเหลือ
    tool_options_display = []
    real_tool_names = {}
    
    for tool, total in total_stock.items():
        if total > 0:
            remaining = int(total - borrowed_stock[tool])
            if remaining < 0: remaining = 0 # ป้องกันติดลบ
            
            display_text = f"{tool} (เหลือ {remaining}/{total})"
            tool_options_display.append(display_text)
            real_tool_names[display_text] = tool

    # --- ส่วนที่ 1: ฟอร์มเบิก/คืน ---
    st.markdown("### 📝 ฟอร์มทำรายการ")
    with st.form("tools_form"):
        col1, col2 = st.columns(2)
        with col2:
            status = st.radio("📌 สถานะการทำรายการ", ["🔴 ยืมอุปกรณ์ (Borrow)", "🟢 คืนอุปกรณ์ (Return)"], horizontal=True)
            site_used = st.selectbox("📍 นำไปใช้ที่ไซต์งาน", ["ส่วนกลาง / ออฟฟิศ"] + site_list)
            
        with col1:
            borrower = st.selectbox("👤 ชื่อผู้เบิก/คืน", team_members)
            selected_displays = st.multiselect("🔧 เลือกอุปกรณ์ (กดเลือกได้หลายชิ้น)", tool_options_display)
        
        # 📦 สร้างช่องกรอกจำนวน โผล่ขึ้นมาตามของที่กดเลือก!
        quantities = {}
        if selected_displays:
            st.markdown("**📦 ระบุจำนวนที่ต้องการทำรายการ:**")
            col_q1, col_q2 = st.columns(2)
            for i, display in enumerate(selected_displays):
                tool = real_tool_names[display]
                # สลับฝั่งซ้ายขวาให้ดูสวยงาม
                with col_q1 if i % 2 == 0 else col_q2:
                    quantities[tool] = st.number_input(f"จำนวน: {tool}", min_value=1, step=1, key=f"qty_{tool}")
            
        submitted = st.form_submit_button("บันทึกข้อมูลเข้าคลัง", type="primary")
        
        if submitted:
            if selected_displays:
                with st.spinner("กำลังบันทึกข้อมูลเข้าทีละรายการ..."):
                    success_count = 0
                    # ทำการวนลูปยิงข้อมูลเข้า GSheet ทีละอุปกรณ์ (เพื่อให้คอมพิวเตอร์นับเลขได้ง่าย)
                    for display in selected_displays:
                        tool = real_tool_names[display]
                        qty = quantities[tool]
                        
                        payload = {
                            "sheet": "Team_Tools",
                            "data": [
                                (pd.Timestamp.utcnow() + pd.Timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
                                borrower, tool, site_used, 
                                status.replace("🔴 ", "").replace("🟢 ", ""),
                                qty # คอลัมน์ F: จำนวน
                            ]
                        }
                        try:
                            requests.post(GAS_URL, data=json.dumps(payload))
                            success_count += 1
                        except:
                            pass
                            
                    if success_count == len(selected_displays):
                        st.success(f"✅ บันทึก '{status}' จำนวน {success_count} รายการ เรียบร้อยแล้ว! (รีเฟรชเพื่อดูยอดคงเหลืออัปเดต)")
                    else:
                        st.warning("บันทึกได้บางรายการ กรุณาตรวจสอบ GSheet")
            else:
                st.warning("⚠️ กรุณาเลือกอุปกรณ์ที่ต้องการทำรายการก่อนครับ")
    
    st.markdown("---")
    
    # --- ส่วนที่ 2: ตารางประวัติการเบิก-คืน ---
    st.markdown("### 📋 ประวัติการยืม-คืนล่าสุด")
    try:
        df_tools = load_sheet("Team_Tools")
        if not df_tools.empty:
            df_tools.columns = [str(c).strip() for c in df_tools.columns]
            st.dataframe(df_tools, use_container_width=True, hide_index=True)
    except:
        st.info("ยังไม่มีประวัติการเบิกใช้อุปกรณ์ในระบบครับ")
elif menu == "👥 6. ข้อมูลทีม (Team Profile)":
    st.title("👥 ข้อมูลและศักยภาพทีม (Team Profile)")
    st.write("ทำเนียบสมาชิกทีม Sensor เพื่อดูความรับผิดชอบ ความเชี่ยวชาญ และใบรับรองของแต่ละบุคคล")
    
    try:
        df_team = load_sheet("Team_Profile")
        df_team.columns = [str(c).strip() for c in df_team.columns]
        
        if not df_team.empty and 'ชื่อ' in df_team.columns:
            st.markdown("---")
            col1, col2 = st.columns(2)
            
            try:
                df_tasks = load_sheet("Task & Workload")
                df_tasks.columns = [str(c).strip() for c in df_tasks.columns]
            except:
                df_tasks = pd.DataFrame()
            
            for i, row in df_team.iterrows():
                name = str(row.get('ชื่อ', 'ไม่ระบุ')).strip()
                role = str(row.get('ตำแหน่ง', '-'))
                skill = str(row.get('ความเชี่ยวชาญ', '-'))
                tel = str(row.get('เบอร์ติดต่อ', '-'))
                # 🌟 เปลี่ยนมารับค่าจากคอลัมน์ 'ใบเซอร์' แทน
                cert = str(row.get('ใบเซอร์', '-'))
                
                if name and name.lower() != 'nan':
                    with col1 if i % 2 == 0 else col2:
                        st.info(f"### 👨‍🔧 คุณ {name}") # ใส่ไอคอนช่างเป็นค่าเริ่มต้นแทน
                        st.markdown(f"**ตำแหน่ง:** {role}")
                        st.markdown(f"**ความเชี่ยวชาญ:** {skill}")
                        st.markdown(f"**ใบรับรอง (Certificate):** {cert}") # โชว์ใบเซอร์ตรงนี้
                        st.markdown(f"**เบอร์ติดต่อ:** {tel}")
                        
                        if not df_tasks.empty and 'ผู้รับผิดชอบหลัก' in df_tasks.columns and 'สถานะงาน' in df_tasks.columns:
                            active_tasks = df_tasks[(df_tasks['ผู้รับผิดชอบหลัก'] == name) & (df_tasks['สถานะงาน'] != 'Complete')]
                            task_count = len(active_tasks)
                            
                            if task_count > 0:
                                st.error(f"📌 **สถานะ:** มีงานค้างอยู่ {task_count} โปรเจกต์")
                            else:
                                st.success("✨ **สถานะ:** ตอนนี้เคลียร์งานครบ 100% แล้ว!")
                                
                        st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ แผ่น 'Team_Profile' ยังไม่มีข้อมูล หรือยังไม่มีคอลัมน์ที่ชื่อว่า 'ชื่อ' ครับ")
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลด Team_Profile: {e}")
elif menu == "🧠 7. ศูนย์การเรียนรู้ (Learning & Quiz)":
    st.title("🧠 ศูนย์การเรียนรู้ และเครื่องมือคำนวณ")
    st.write("คลังความรู้ แบบทดสอบ และเครื่องมือคำนวณที่อัปเดตจาก Google Sheets โดยตรง")
    
    # สร้าง 3 แท็บ
    tab1, tab2, tab3 = st.tabs(["📚 คลังความรู้ (Knowledge)", "📝 แบบทดสอบ (Quiz)", "🧮 เครื่องมือคำนวณอัจฉริยะ"])
    
# --- Tab 1: คลังความรู้ (ดึงจาก Learning_Content) ---
    with tab1:
        st.markdown("### 📚 คลังความรู้และคู่มือสูตรคำนวณ")
        try:
            df_learning = load_sheet("Learning_Content")
            df_learning.columns = [str(c).strip() for c in df_learning.columns]
            
            if not df_learning.empty and 'ชื่อหัวข้อ' in df_learning.columns:
                for index, row in df_learning.iterrows():
                    category = str(row.get('หมวดหมู่', 'ทั่วไป'))
                    topic = str(row.get('ชื่อหัวข้อ', ''))
                    
                    # 🌟 เปลี่ยนมาใช้ \n\n แทนการใช้ <br> เพื่อให้กล่องของ Streamlit แสดงผลได้สวยงาม
                    formula = str(row.get('สูตรการคำนวณ', ''))
                    info = str(row.get('ข้อมูลการคำนวณ', '')).replace('\n', '\n\n')
                    example = str(row.get('ตัวอย่างการคำนวณ', '')).replace('\n', '\n\n')
                    
                    if topic and topic.lower() != 'nan':
                        with st.expander(f"📖 [{category}] {topic}"):
                            
                            # กล่องไฮไลท์สูตรคำนวณ (สีฟ้า)
                            if formula and formula.lower() != 'nan' and formula != '-':
                                st.info(f"**💡 สูตรการคำนวณ:**\n\n### {formula}")
                                
                            # ส่วนอธิบายข้อมูล 
                            if info and info.lower() != 'nan' and info != '-':
                                st.markdown(f"**📝 ข้อมูลและคำอธิบาย:**\n\n{info}")
                                
                            # กล่องไฮไลท์ตัวอย่าง (สีเขียว)
                            if example and example.lower() != 'nan' and example != '-':
                                st.success(f"**🔢 ตัวอย่างการคำนวณ:**\n\n{example}", icon="✅")
            else:
                st.info("ยังไม่มีข้อมูล หรือรอการเปลี่ยนหัวคอลัมน์เป็น 'ชื่อหัวข้อ' ในแผ่น Learning_Content ครับ")
        except Exception as e:
            st.error(f"ไม่สามารถโหลด Learning_Content ได้: {e}")
    # --- Tab 2: แบบทดสอบ (ดึงจาก Quiz_Data) ---
    with tab2:
        try:
            df_quiz = load_sheet("Quiz_Data")
            df_quiz.columns = [str(c).strip() for c in df_quiz.columns]
            
            if not df_quiz.empty and 'คำถาม' in df_quiz.columns:
                st.markdown("### 📝 ทดสอบความรู้ประจำสัปดาห์")
                
                for i, row in df_quiz.iterrows():
                    question = str(row.get('คำถาม', ''))
                    if question and question.lower() != 'nan':
                        st.markdown(f"**ข้อที่ {i+1}: {question}**")
                        
                        # รวบรวมตัวเลือก A B C D
                        options = []
                        for col in ['ตัวเลือก A', 'ตัวเลือก B', 'ตัวเลือก C', 'ตัวเลือก D']:
                            if col in df_quiz.columns:
                                opt = str(row.get(col, ''))
                                if opt and opt.lower() != 'nan':
                                    options.append(opt)
                        
                        if options:
                            ans = st.radio(f"เลือกคำตอบข้อ {i+1}:", options, key=f"quiz_{i}", index=None)
                            correct_ans = str(row.get('เฉลย', '')).strip()
                            explain = str(row.get('คำอธิบาย (ถ้าตอบผิด)', ''))
                            
                            if st.button(f"ส่งคำตอบข้อ {i+1}", key=f"btn_{i}"):
                                if ans:
                                    # เช็คคำตอบว่าตรงกับเฉลยหรือไม่
                                    if ans in correct_ans or correct_ans in ans:
                                        st.success("✅ ถูกต้องครับ! เยี่ยมมาก")
                                        if explain and explain.lower() != 'nan':
                                            st.info(f"💡 **อธิบายเพิ่มเติม:** {explain}")
                                    else:
                                        st.error(f"❌ ผิดครับ! (เฉลยคือ: {correct_ans})")
                                        if explain and explain.lower() != 'nan':
                                            st.info(f"💡 **ทำไมถึงผิด?:** {explain}")
                                else:
                                    st.warning("กรุณาเลือกคำตอบก่อนกดส่งครับ")
                        st.markdown("---")
            else:
                st.info("ยังไม่มีข้อสอบในแผ่น Quiz_Data ครับ")
        except Exception as e:
            st.error(f"ไม่สามารถโหลด Quiz_Data ได้: {e}")

    # --- Tab 3: เครื่องมือคำนวณ (ดึงจากแผ่น Calc_Tools) ---
    with tab3:
        st.markdown("### 🧮 เครื่องมือคำนวณอัจฉริยะ (ไม่จำกัดจำนวนตัวแปร)")
        st.write("ระบบจะสร้างช่องกรอกข้อมูลและคำนวณอัตโนมัติ ตามสูตรที่คุณตั้งไว้ใน Google Sheets")
        
        try:
            df_calc = load_sheet("Calc_Tools")
            df_calc.columns = [str(c).strip() for c in df_calc.columns]
            
            if not df_calc.empty and 'ชื่อสูตร' in df_calc.columns:
                formula_list = df_calc['ชื่อสูตร'].dropna().tolist()
                formula_list = [f for f in formula_list if str(f).lower() != 'nan']
                
                if formula_list:
                    selected_form = st.selectbox("📌 เลือกสูตรที่ต้องการคำนวณ:", formula_list)
                    f_data = df_calc[df_calc['ชื่อสูตร'] == selected_form].iloc[0]
                    
                    # 🌟 ใช้ชื่อคอลัมน์ 'ชื่อตัวแปร' ตามตาราง GSheet ของคุณ Heart
                    var_str = str(f_data.get('ชื่อตัวแปร', ''))
                    equation = str(f_data.get('สมการ', ''))
                    unit = str(f_data.get('หน่วยผลลัพธ์', ''))
                    desc = str(f_data.get('คำอธิบาย', ''))
                    
                    if desc and desc.lower() != 'nan':
                        st.info(f"💡 **หลักการคำนวณ:** {desc}")
                        
                    # แยกตัวแปรด้วยลูกน้ำ
                    if var_str and var_str.lower() != 'nan':
                        variables = [v.strip() for v in var_str.split(',') if v.strip()]
                    else:
                        variables = []
                        
                    # สร้างกล่องรับค่าแบบอัตโนมัติ
                    input_values = {}
                    if variables:
                        cols = st.columns(2)
                        for i, var in enumerate(variables):
                            with cols[i % 2]:
                                input_values[var] = st.number_input(f"🔢 ค่าของ {var}", value=0.0, step=0.1, key=f"var_{var}")
                                
                        if st.button("🧮 คำนวณผลลัพธ์", type="primary"):
                            if equation and equation.lower() != 'nan':
                                try:
                                    eq_safe = equation.replace("x", "*").replace("X", "*")
                                    result = eval(eq_safe, {"__builtins__": None}, input_values) 
                                    st.markdown(f"<h3 style='text-align: center; color: #008080; padding: 20px; border: 2px dashed #008080; border-radius: 10px;'>ผลลัพธ์ = {result:,.2f} {unit}</h3>", unsafe_allow_html=True)
                                except Exception as e:
                                    st.error(f"❌ สมการใน GSheet อาจพิมพ์ผิด หรือชื่อตัวแปรในสมการไม่ตรงกับที่ตั้งไว้ (Error: {e})")
                            else:
                                st.warning("⚠️ ยังไม่ได้กำหนดสมการใน GSheet ครับ")
                    else:
                        st.warning("⚠️ ยังไม่ได้กำหนดชื่อตัวแปรใน GSheet ครับ")
                else:
                    st.info("ยังไม่มีรายชื่อสูตรครับ")
            else:
                st.warning("⚠️ โปรดตรวจสอบว่าแผ่น 'Calc_Tools' มีคอลัมน์ชื่อ 'ชื่อสูตร', 'ชื่อตัวแปร' และ 'สมการ' ครบถ้วนครับ")
        except Exception as e:
            st.warning("ระบบกำลังรอตาราง Calc_Tools จาก Google Sheets ครับ...")
elif menu == "📚 8. คู่มือการใช้งาน (Manuals & Docs)":
    st.title("📚 คู่มือการใช้งานและเอกสาร (Manuals & Docs)")
    st.write("ศูนย์รวมโฟลเดอร์คู่มือการติดตั้ง Wiring Diagram และเอกสารมาตรฐานของทีม Sensor")
    st.markdown("---")

    try:
        df_docs = load_sheet("Manual_Docs")
        df_docs.columns = [str(c).strip() for c in df_docs.columns]

        if not df_docs.empty and 'หมวดหมู่' in df_docs.columns:
            for _, row in df_docs.iterrows():
                cat_name = str(row.get('หมวดหมู่', ''))
                desc = str(row.get('รายละเอียด', '-'))
                
                # 🌟 จุดที่อัปเกรด 1: ใช้ .strip() เพื่อลบช่องว่าง (Spacebar) ที่อาจเผลอกดตอนวางลิงก์
                link = str(row.get('ลิงก์โฟลเดอร์', row.get('ลิงก์เอกสาร', ''))).strip() 

                if cat_name and cat_name.lower() != 'nan':
                    with st.container():
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"### 📂 {cat_name}")
                            if desc and desc.lower() != 'nan' and desc != '-':
                                st.write(f"ℹ️ {desc}")
                        with col2:
                            st.markdown("<br>", unsafe_allow_html=True) 
                            
                            # 🌟 จุดที่อัปเกรด 2: แค่มีตัวอักษรเกิน 5 ตัว ก็ถือว่าเป็นลิงก์แล้ว
                            if link and link.lower() != 'nan' and len(link) > 5:
                                
                                # 🌟 จุดที่อัปเกรด 3: ถ้าลิงก์ที่วางมาไม่มี http:// ระบบจะเติมให้อัตโนมัติ!
                                if not link.startswith('http'):
                                    link = 'https://' + link
                                    
                                st.markdown(f"<a href='{link}' target='_blank'><button style='width:100%; padding:10px; background-color:#008080; color:white; border:none; border-radius:5px; cursor:pointer; font-weight:bold; font-size:16px;'>🔗 เปิดโฟลเดอร์</button></a>", unsafe_allow_html=True)
                            else:
                                st.write("*(ยังไม่มีลิงก์โฟลเดอร์)*")
                        st.divider()
        else:
            st.info("💡 กรุณาสร้างแผ่น 'Manual_Docs' ใน GSheet และใส่คอลัมน์ 'หมวดหมู่', 'รายละเอียด', 'ลิงก์โฟลเดอร์'")
            
    except Exception as e:
        st.warning(f"ระบบกำลังรอการเชื่อมต่อกับแผ่น 'Manual_Docs' ใน Google Sheets ครับ")
else:
    st.title(menu)
    st.write(f"กำลังพัฒนาฟีเจอร์สำหรับเมนูนี้ครับ...")
