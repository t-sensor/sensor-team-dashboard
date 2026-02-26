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
import re

def check_password_strength(password):
    """ตรวจสอบว่ารหัสผ่านแข็งแกร่งพอไหม"""
    errors = []
    
    if len(password) < 8:
        errors.append("❌ ความยาวต้องมีอย่างน้อย 8 ตัวอักษร")
    if not re.search(r'[A-Za-z]', password):
        errors.append("❌ ต้องมีตัวอักษรภาษาอังกฤษอย่างน้อย 1 ตัว")
    if not re.search(r'[0-9]', password):
        errors.append("❌ ต้องมีตัวเลขอย่างน้อย 1 ตัว")
    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=/\\]', password):
        errors.append("❌ ต้องมีอักขระพิเศษ เช่น !@#$% อย่างน้อย 1 ตัว")
    
    return errors
def send_line_message(message):
    token = st.secrets["LINE_CHANNEL_TOKEN"]
    group_id = st.secrets["LINE_GROUP_ID"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # 🌟 สำคัญ: รวม @all เข้ากับข้อความหลัก (เคาะบรรทัดใหม่ด้วย \n)
    full_text = f"@all \n{message}"
    
    payload = {
        "to": group_id,
        "messages": [
            {
                "type": "text",
                "text": full_text,
                "mention": { # 👈 นี่คือ "กล่องคุมการแท็ก"
                    "mentions": [
                        {
                            "index": 0,    # 0 คือเริ่มแท็กที่ตัวอักษรที่ 1 (ตัว @)
                            "length": 4,   # 4 คือคลุมคำว่า @all (ห้ามขาดห้ามเกิน)
                            "type": "all"  # บอก LINE ว่า "นี่คือการแท็กทุกคนนะ"
                        }
                    ]
                }
            }
        ]
    }
    try:
        response = requests.post(
            "https://api.line.me/v2/bot/message/push",
            headers=headers,
            data=json.dumps(payload)
        )
        if response.status_code != 200:
            st.error(f"LINE Error: {response.text}")
    except Exception as e:
        st.error(f"ระบบส่ง LINE ขัดข้อง: {e}")
# --- 1. ตั้งค่าหน้าเว็บ ---
# เปลี่ยน page_icon ให้ดึงไฟล์รูปแทนอีโมจิ
st.set_page_config(page_title="Sensor Team System", page_icon="logo.png", layout="wide")

# กุญแจเชื่อมต่อ GSheet
GAS_URL = st.secrets["GAS_URL"]
SHEET_URL = st.secrets["SHEET_URL"]


# 🌟 --- ฟังก์ชันส่วนกลาง --- 🌟
@st.cache_data(ttl=5)
def load_sheet(sheet_name):
    import time
    sheet_id = SHEET_URL.split("/d/")[1].split("/")[0]
    encoded_sheet_name = urllib.parse.quote(sheet_name)
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}&t={int(time.time())}"
    
    return pd.read_csv(
        csv_url, 
        dtype=str,              # บังคับทุก Column เป็น String
        keep_default_na=False,  # 👈 ห้าม Pandas แปลงค่าเป็น NaN เอง
        na_values=['']          # 👈 ถือว่า NaN ก็แค่เซลล์ว่างเท่านั้น
    )
# 📝 ฟังก์ชันบันทึกประวัติเข้า-ออกเว็บ
def log_user_action(username, action):
    try:
        payload = {
            "sheet": "Login_Logs",
            "data": [
                (pd.Timestamp.utcnow() + pd.Timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
                username,
                action
            ]
        }
        requests.post(GAS_URL, data=json.dumps(payload))
    except:
        pass
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
# ✅ แก้เป็นแบบนี้
raw = localS.getItem("auth")
if raw:
    try:
        auth_data = json.loads(raw)
        if auth_data.get("logged_in") == "true":
            st.session_state['logged_in'] = True
            st.session_state['username'] = auth_data.get("username", "")
            st.session_state['role'] = auth_data.get("role", "")
    except:
        pass

# 3. หน้าต่าง Login
# =========================================================
# ⏱️ ระบบตรวจสอบเวลาหมดอายุ (Session Timeout - 30 นาที)
# =========================================================
if st.session_state.get('logged_in'):
    import time
    current_time = time.time()
    # ถ้าพิ่งล็อกอินครั้งแรก ให้ตั้งค่าเวลาเริ่มต้นเป็นปัจจุบัน
    last_active = st.session_state.get('last_active', current_time)
    
    # ถ้าเวลาปัจจุบัน - เวลาล่าสุดที่ขยับ มากกว่า 1800 วินาที (30 นาที)
    if current_time - last_active > 1800:
        # 1. แอบบันทึกประวัติว่าโดนเตะออกเพราะหมดเวลา
        log_user_action(st.session_state.get('username', 'Unknown'), "Auto-Logout (Timeout)")
        
        # 2. ล้างความจำเบราว์เซอร์และ Session
        localS.deleteAll()
        st.session_state['logged_in'] = False
        st.session_state['username'] = ''
        st.session_state['role'] = ''
        
        # 3. แจ้งเตือนแล้วรีเฟรชหน้า
        st.error("⏱️ คุณไม่ได้ใช้งานระบบเกิน 30 นาที ระบบได้ทำการลงชื่อออกอัตโนมัติเพื่อความปลอดภัยครับ")
        time.sleep(3)
        st.rerun()
    else:
        # ถ้ายังไม่ถึง 30 นาที และมีการกดใช้งานเว็บ ให้อัปเดตเวลาล่าสุด
        st.session_state['last_active'] = current_time

if not st.session_state['logged_in']:
    st.markdown("<br><br>", unsafe_allow_html=True) # ดันให้ฟอร์มลงมากลางจออีกนิด
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        
        # 🌟 เทคนิคจัดกึ่งกลาง: สร้างพื้นที่ซ้าย-กลาง-ขวา บีบให้รูปอยู่ตรงกลาง
        img_col1, img_col2, img_col3 = st.columns([1, 1.5, 1])
        with img_col2:
            st.image("logo.png", use_container_width=True)
            
        st.markdown("<h1 style='text-align: center; color: #008080;'>🔐 Sensor Team Login</h1>", unsafe_allow_html=True)
        st.markdown("---")
        st.info("กรุณาเข้าสู่ระบบ หากยังไม่มีรหัส กรุณาลงทะเบียนและรออนุมัติ")
        
        # ... (โค้ดฟอร์ม Login ข้างล่างเหมือนเดิมครับ) ...
        with st.form("login_form"):
            input_user = st.text_input("👤 Username")
            input_pass = st.text_input("🔑 Password", type="password")
            submitted = st.form_submit_button("เข้าสู่ระบบ", type="primary", use_container_width=True)
            
            if submitted:
                if input_user and input_pass:
                  with st.spinner("กำลังตรวจสอบข้อมูล..."):
                        try:
                            df_users = load_sheet("Users_DB")

                            
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
                                        # ✅ แก้เป็นแบบนี้
                                        auth_data = json.dumps({
                                            "logged_in": "true",
                                            "username": input_user.strip(),
                                            "role": role_val
                                        })
                                        localS.setItem("auth", auth_data)
                                        
                                        # อัปเดตสถานะให้เว็บ
                                        st.session_state['logged_in'] = True
                                        st.session_state['username'] = input_user.strip()
                                        st.session_state['role'] = role_val
                                        
                                        # 🌟 แทรกบรรทัดนี้ลงไปตรงนี้ครับ
                                        log_user_action(input_user.strip(), "Login")
                                        
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
# --- 3. สร้างระบบเมนูแถบด้านข้าง (Sidebar) ตามสิทธิ์ ---
# 🌟 ใส่โลโก้ด้านบนสุดของ Sidebar
try:
    st.sidebar.image("logo.png", use_container_width=True) 
except:
    pass # ถ้าหารูปไม่เจอให้ข้ามไปก่อน

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
        "📚 8. คู่มือการใช้งาน (Manuals & Docs)",
        "📅 9. แผนงานล่วงหน้า (Planned Tasks)" # 🌟 เพิ่มบรรทัดนี้ครับ (อย่าลืมใส่ลูกน้ำที่บรรทัดก่อนหน้า)
    ]
else:
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

# 🌟 โชว์สถานะคนออนไลน์ (เห็นเฉพาะ Admin)
if CURRENT_ROLE == 'admin':
    st.sidebar.markdown("**📡 สถานะทีมงาน (Online)**")
    try:
        df_logs = load_sheet("Login_Logs")
        if not df_logs.empty:
            df_logs.columns = [str(c).strip() for c in df_logs.columns]
            last_status = df_logs.drop_duplicates(subset=['Username'], keep='last')
            online_users = last_status[last_status['Action'] == 'Login']
            
            if not online_users.empty:
                for _, r in online_users.iterrows():
                    time_only = str(r['Timestamp']).split(' ')[1][:5]
                    st.sidebar.caption(f"🟢 **{r['Username']}** (เข้าเมื่อ {time_only})")
            else:
                st.sidebar.caption("⚪ ไม่มีผู้ใช้ออนไลน์")
    except:
        st.sidebar.caption("รอโหลดข้อมูล...")

st.sidebar.markdown("<br>", unsafe_allow_html=True)

# 🌟 ปุ่ม Logout (กดแล้วบันทึกประวัติและเตะออก)
if st.sidebar.button("🚪 ออกจากระบบ", type="primary", use_container_width=True):
    # บันทึกประวัติ
    log_user_action(st.session_state['username'], "Logout")
    
    # ล้างความจำเบราว์เซอร์
    localS.deleteAll()
    
    # เคลียร์ Session
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''
    st.session_state['role'] = ''
    
    # รีเฟรชเว็บ
    time.sleep(1)
    st.rerun()

# --- 4. โครงสร้างแต่ละเมนู (โค้ด Dashboard ของเดิมจะต่อจากตรงนี้ลงไป) ---
# --- ส่วนที่ 1: Dashboard อัจฉริยะ (เมนู 1) ---
if menu == "🏠 1. ภาพรวมและสถิติ (Dashboard)":
    st.title("📊 Team Sensor Command Center")
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
        if not df_task.empty and 'ชื่อไซต์งาน' in df_task.columns and 'ชื่องาน / รายละเอียด' in df_task.columns:
            df_task_latest = df_task.drop_duplicates(subset=['ชื่อไซต์งาน', 'ชื่องาน / รายละเอียด'], keep='last')
            active_tasks = len(df_task_latest[df_task_latest['สถานะงาน'] != 'Complete'])
        else:
            active_tasks = 0
        
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
        
# ==========================================
        # 📶 ระบบแจ้งเตือนวันหมดอายุซิม (SIM Expiration)
        # ==========================================
        st.markdown("### 📶 ข้อมูลการเชื่อมต่อ (SIM & Network)")
        
        with st.expander("🔻 กดเพื่อดูตารางวันหมดอายุซิมเร้าเตอร์ (SIM Expiration)", expanded=False):
            if 'วันที่ซิมหมดอายุ' in df_pm.columns:
                df_sim = df_pm[['ชื่อไซต์งาน', 'วันที่ซิมหมดอายุ']].copy()
                
                # 🌟 บังคับแปลงทุกอย่างเป็นตัวอักษร ป้องกัน Error จาก Pandas
                df_sim['วันที่ซิมหมดอายุ'] = df_sim['วันที่ซิมหมดอายุ'].fillna("").astype(str)
                
                if not df_sim.empty:
                    import re
                    today = pd.Timestamp.today().normalize()
                    
                    def get_sortable_date(date_str):
                        # 🌟 ล้างช่องว่าง และอักขระล่องหนทิ้งให้หมด
                        date_str = str(date_str).replace('\u200b', '').replace('\n', '').strip().lower()
                        
                        if not date_str or date_str in ['nan', '-', 'none', '', 'ไม่มี']:
                            return pd.Timestamp('2099-12-31') 
                        
                        # 🌟 ถ้ามีคำว่า "หมด" หรือ "expire" ดันขึ้นบนสุดทันที!
                        if "หมด" in date_str or "expire" in date_str:
                            return pd.Timestamp('1999-01-01') 
                            
                        try:
                            match_full = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', date_str)
                            if match_full:
                                d, m, y = int(match_full.group(1)), int(match_full.group(2)), int(match_full.group(3))
                                if y > 2400: y -= 543
                                return pd.Timestamp(year=y, month=m, day=d)
                                
                            match_short = re.search(r'(\d{1,2})[-/](\d{2}|\d{4})', date_str)
                            if match_short:
                                m, y = int(match_short.group(1)), int(match_short.group(2))
                                if y < 100: y += 2000 
                                elif y > 2400: y -= 543 
                                next_month = m + 1 if m < 12 else 1
                                next_year = y if m < 12 else y + 1
                                return pd.Timestamp(year=next_year, month=next_month, day=1) - pd.Timedelta(days=1)
                                
                            parsed = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                            if pd.notna(parsed): return parsed
                            
                            # ถ้าเป็นคำแปลกๆ อื่นๆ (เช่น รอต่อสัญญา) ก็ดันขึ้นบนเหมือนกัน
                            return pd.Timestamp('1999-01-02') 
                        except:
                            return pd.Timestamp('1999-01-02')

                    df_sim['Parsed_Date'] = df_sim['วันที่ซิมหมดอายุ'].apply(get_sortable_date)
                    
                    df_sim = df_sim[df_sim['Parsed_Date'] != pd.Timestamp('2099-12-31')]
                    
                    if not df_sim.empty:
                        def assign_status(d):
                            if d.year == 1999 or d < today:
                                return "🔴 ซิมหมดอายุแล้ว"
                            elif (d - today).days <= 60:
                                return "🟡 ใกล้หมดอายุ"
                            else:
                                return "🟢 ใช้งานได้ปกติ"

                        df_sim['สถานะการใช้งาน'] = df_sim['Parsed_Date'].apply(assign_status)
                        df_sim = df_sim.sort_values(by=['Parsed_Date', 'ชื่อไซต์งาน'])

                        df_display = df_sim[['ชื่อไซต์งาน', 'วันที่ซิมหมดอายุ', 'สถานะการใช้งาน']].copy()

                        def highlight_sim(val):
                            if '🔴' in str(val): return 'color: #FF4B4B; font-weight: bold;'
                            elif '🟡' in str(val): return 'color: #FFC107; font-weight: bold;'
                            elif '🟢' in str(val): return 'color: #00E676;'
                            return 'color: #A6B0C3;'

                        styled_sim = df_display.style.applymap(highlight_sim, subset=['สถานะการใช้งาน']).set_properties(**{
                            'background-color': '#1A1C23',  
                            'color': '#E2E8F0',             
                            'border-color': '#282B36',
                            'text-align': 'center'
                        })
                        
                        dynamic_height = int(len(df_display) * 35.5) + 42
                        col_space1, col_table, col_space3 = st.columns([1, 3, 1])
                        with col_table:
                            st.dataframe(styled_sim, use_container_width=True, hide_index=True, height=dynamic_height)
                            
                    else:
                        st.info("✨ ยังไม่มีข้อมูลไซต์งานที่ต้องแจ้งเตือนซิมครับ")
                else:
                    st.info("✨ ยังไม่มีข้อมูลไซต์งานในระบบครับ")
            else:
                st.warning("⚠️ ไม่พบคอลัมน์ 'วันที่ซิมหมดอายุ' ในตาราง PM_Plan ครับ")
        
        st.markdown("<br>", unsafe_allow_html=True) # เว้นบรรทัดให้สวยงามก่อนขึ้นแผนที่
# 🗺️ แผนที่
        st.markdown("### 🗺️ แผนที่พิกัดไซต์งาน (สีหมุดตามสถานะ PM)")
        if not df_master.empty and 'ละติจูด (Latitude)' in df_master.columns:
            
            # 🌟 จุดที่แก้ไข: เติม tiles='CartoDB dark_matter' เข้าไปเพื่อเปลี่ยนเป็นธีมดำ
            m = folium.Map(location=[13.73, 100.52], zoom_start=6, tiles='CartoDB dark_matter')
            
            for _, r in df_master.dropna(subset=['ละติจูด (Latitude)', 'ลองจิจูด (Longitude)']).iterrows():
                s_name = str(r['ชื่อไซต์งาน (Process Work)']).strip()
                dot_color = site_colors.get(s_name, "gray")
                folium.Marker([r['ละติจูด (Latitude)'], r['ลองจิจูด (Longitude)']], 
                              popup=s_name, icon=folium.Icon(color=dot_color)).add_to(m)
            
            st_folium(m, height=600, use_container_width=True)
            
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
        

#หน้า3 ---------------------------------------------------------------------------------------------
elif menu == "📱 3. กระดานงานส่วนตัว (My Workload)":
    st.title("📱 กระดานงานส่วนตัว")
    
    # 1. ระบุตัวตน
    CURRENT_USER = st.session_state.get('username', 'ไม่ระบุตัวตน')
    st.info(f"👤 สวัสดีครับคุณ **{CURRENT_USER}** นี่คืองานที่อยู่ในความรับผิดชอบของคุณครับ")

    # โหลดข้อมูลงาน
    try:
        df_tasks = load_sheet("Task & Workload")
        if not df_tasks.empty:
            df_tasks.columns = [str(c).strip() for c in df_tasks.columns]
    except:
        df_tasks = pd.DataFrame()

# 2. --- ส่วนแสดงตารางงานของตัวเอง (Active Tasks) ---
    my_active_tasks = pd.DataFrame() 
    
    if not df_tasks.empty and 'ผู้รับผิดชอบหลัก' in df_tasks.columns:
        df_tasks['ผู้รับผิดชอบหลัก'] = df_tasks['ผู้รับผิดชอบหลัก'].fillna("")
        df_tasks['ผู้ช่วย'] = df_tasks['ผู้ช่วย'].fillna("")
        df_tasks['สถานะงาน'] = df_tasks['สถานะงาน'].fillna("")

        # 🌟 ความอัจฉริยะที่เพิ่มขึ้น: รวบงานที่ซ้ำกัน (ไซต์และชื่องานเหมือนกัน) โดยยึด "สถานะล่าสุด" (บรรทัดล่างสุด)
        df_latest_tasks = df_tasks.drop_duplicates(
            subset=['ชื่อไซต์งาน', 'ชื่องาน / รายละเอียด'], 
            keep='last'
        )

        # กรองเฉพาะงานของฉัน (จากรายการที่อัปเดตล่าสุดแล้ว)
        my_all_tasks = df_latest_tasks[
            (df_latest_tasks['ผู้รับผิดชอบหลัก'] == CURRENT_USER) | 
            (df_latest_tasks['ผู้ช่วย'].str.contains(CURRENT_USER, na=False))
        ]

        # แยกเฉพาะงานที่ยัง "ไม่เสร็จ" เพื่อเอาไปส่งให้ Dropdown อัปเดตงาน
        my_active_tasks = my_all_tasks[my_all_tasks['สถานะงาน'] != "Complete"]

        if not my_all_tasks.empty:
            st.markdown("### 📋 รายการงานของคุณ (อัปเดตล่าสุด)")
            display_cols = ['วันที่เข้าทำ (Scheduled Date)', 'ชื่อไซต์งาน', 'ชื่องาน / รายละเอียด', 'ประเภทงาน', 'สถานะงาน', 'ผู้ช่วย', 'ปัญหา/หมายเหตุ']
            available_cols = [col for col in display_cols if col in df_tasks.columns]
            
            def highlight_status(val):
                color = 'red' if 'Problem' in val else ('green' if 'Complete' in val else 'orange')
                return f'color: {color}'
            
            # โชว์ตารางงานทั้งหมดของฉัน (ที่รวบประวัติซ้ำๆ ออกไปแล้ว)
            st.dataframe(my_all_tasks[available_cols].style.applymap(highlight_status, subset=['สถานะงาน']), use_container_width=True, hide_index=True)
        else:
            st.success("🎉 ตอนนี้คุณไม่มีงานค้างเลยครับ พักผ่อนได้!")
    else:
        st.info("กำลังโหลดข้อมูล หรือตารางยังว่างอยู่ครับ...")

    st.markdown("---")

    # =========================================================
    # ⚡ ส่วนที่ 1: อัปเดตสถานะงานเดิม (ไม่ต้องกรอกใหม่)
    # =========================================================
    st.markdown("### ⚡ อัปเดตงานที่ค้างอยู่ (Quick Update)")
    
    if not my_active_tasks.empty:
        task_options = my_active_tasks.apply(
            lambda x: f"[{x['ชื่อไซต์งาน']}] {x['ชื่องาน / รายละเอียด']} (เริ่ม: {x['วันที่เข้าทำ (Scheduled Date)']})", axis=1
        ).tolist()
        
        selected_task_str = st.selectbox("เลือกงานที่ต้องการอัปเดต:", ["-- กรุณาเลือกงาน --"] + task_options)
        
        if selected_task_str != "-- กรุณาเลือกงาน --":
            task_index = task_options.index(selected_task_str)
            original_task = my_active_tasks.iloc[task_index]
            
            with st.container(border=True):
                st.info(f"📌 กำลังอัปเดตงาน: **{original_task['ชื่องาน / รายละเอียด']}** ณ **{original_task['ชื่อไซต์งาน']}**")
                
                col_u1, col_u2 = st.columns(2)
                with col_u1:
                    update_action = st.radio("สถานะล่าสุด:", ["✅ งานเสร็จเรียบร้อย (Complete)", "⚠️ ติดปัญหา / ยังไม่เสร็จ (Problem/In Progress)"])
                
                with col_u2:
                    # 🌟 แก้ไข: บังคับให้ปุ่ม Toggle แจ้งเตือน LINE ปิดไว้เสมอ (value=False)
                    notify_line_update = st.toggle("🔕 ส่ง LINE แจ้งเตือนทีม (กดเปิดเมื่องานสำคัญ)", value=False, key="toggle_update")
                
                if "Problem" in update_action:
                    update_note = st.text_area("ระบุปัญหาหรือความคืบหน้า:", placeholder="เช่น อะไหล่ไม่พอ, ฝนตกทำงานไม่ได้...")
                    new_status = "Problem"
                else:
                    update_note = "ดำเนินงานเสร็จสิ้นเรียบร้อย"
                    new_status = "Complete"
                
                if st.button("บันทึกการอัปเดต", type="primary", use_container_width=True):
                    payload = {
                        "sheet": "Task & Workload",
                        "data": [
                            (pd.Timestamp.utcnow() + pd.Timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
                            original_task['ชื่อไซต์งาน'], 
                            original_task['ชื่องาน / รายละเอียด'], 
                            original_task['ประเภทงาน'], 
                            original_task['วันที่เข้าทำ (Scheduled Date)'], 
                            (pd.Timestamp.utcnow() + pd.Timedelta(hours=7)).strftime("%d/%m/%Y"), 
                            new_status, 
                            CURRENT_USER, 
                            original_task['ผู้ช่วย'],
                            update_note 
                        ]
                    }
                    
                    with st.spinner("กำลังบันทึกสถานะ..."):
                        try:
                            requests.post(GAS_URL, data=json.dumps(payload))
                            
                            if notify_line_update:
                                msg_icon = "✅" if new_status == "Complete" else "⚠️"
                                line_msg = (
                                    f"{msg_icon} อัปเดตสถานะงาน!\n"
                                    f"━━━━━━━━━━━━━\n"
                                    f"👷 โดย: {CURRENT_USER}\n"
                                    f"🏢 ไซต์: {original_task['ชื่อไซต์งาน']}\n"
                                    f"📋 งาน: {original_task['ชื่องาน / รายละเอียด']}\n"
                                    f"📌 สถานะ: {new_status}\n"
                                    f"💬 ปัญหา/หมายเหตุ: {update_note}"
                                )
                                send_line_message(line_msg)
                            
                            st.success("อัปเดตสถานะเรียบร้อย!")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาด: {e}")

    else:
        st.info("เยี่ยมมาก! คุณไม่มีงานค้างที่ต้องอัปเดตครับ")

    st.markdown("---")

    # =========================================================
    # ➕ ส่วนที่ 2: ฟอร์มแจ้งงานใหม่ (New Task)
    # =========================================================
    st.markdown("### ➕ เปิดใบงานใหม่ (Create New Task)")
    
    team_members = ["Heart", "Phubeth", "Mink", "Film", "Folk", "Chan"]
    try:
        df_master_m3 = load_sheet("Master_Site")
        site_list_m3 = sorted(df_master_m3['ชื่อไซต์งาน (Process Work)'].dropna().unique().tolist())
    except:
        site_list_m3 = []
    
    site_options_m3 = site_list_m3 + ["➕ อื่นๆ (ระบุเอง)"]

    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            selected_site_m3 = st.selectbox("สถานที่ / ไซต์งาน", site_options_m3)
            if selected_site_m3 == "➕ อื่นๆ (ระบุเอง)":
                final_site_name = st.text_input("ระบุชื่อไซต์งานใหม่:", placeholder="พิมพ์ชื่อไซต์ที่นี่...")
            else:
                final_site_name = selected_site_m3
                
            task_detail = st.text_input("รายละเอียดงาน", placeholder="เช่น เข้าไปเปลี่ยนซิมเร้าเตอร์")
            task_type = st.selectbox("ประเภทงาน", ["งานด่วน", "งานตามแพลน", "งานโปรเจกต์"])
        
        with c2:
            start_date = st.date_input("วันที่เข้าทำ")
            end_date = st.date_input("กำหนดเสร็จ")
            status = st.selectbox("สถานะเริ่มต้น", ["Planning", "In progress"])
            
            try:
                def_idx = team_members.index(CURRENT_USER)
            except:
                def_idx = 0
            assignee = st.selectbox("ผู้รับผิดชอบหลัก", team_members, index=def_idx)
            assistants = st.multiselect("ผู้ช่วย (ถ้ามี)", team_members)

        st.markdown("---")
        col_btn, col_toggle = st.columns([2, 1])
        with col_toggle:
            # 🌟 แก้ไข: บังคับให้ปุ่ม Toggle แจ้งเตือน LINE ปิดไว้เสมอ (value=False)
            notify_line_new = st.toggle("🔕 ส่ง LINE แจ้งเตือนทีม (กดเปิดเมื่องานสำคัญ)", value=False, key="toggle_new")
        
        with col_btn:
            submitted_new = st.button("สร้างงานใหม่", type="primary", use_container_width=True)
        
        if submitted_new:
            if final_site_name and task_detail:
                assistants_str = ", ".join(assistants)
                payload = {
                    "sheet": "Task & Workload",
                    "data": [
                        (pd.Timestamp.utcnow() + pd.Timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
                        final_site_name, task_detail, task_type, 
                        start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y"), 
                        status, assignee, assistants_str,
                        "-" 
                    ]
                }
                with st.spinner("กำลังบันทึกข้อมูล..."):
                    try:
                        res = requests.post(GAS_URL, data=json.dumps(payload))
                        
                        if notify_line_new: 
                            if res.json().get("status") == "success":
                                helper_text = assistants_str if assistants_str else "-"
                                line_msg = (
                                    f"🔔 เปิดใบงานใหม่!\n"
                                    f"━━━━━━━━━━━━━\n"
                                    f"👤 แจ้งโดย: {CURRENT_USER}\n"
                                    f"🏢 ไซต์: {final_site_name}\n"
                                    f"📋 งาน: {task_detail}\n"
                                    f"🏷️ ประเภท: {task_type}\n"
                                    f"📅 เริ่ม: {start_date.strftime('%d/%m/%Y')}\n"
                                    f"👷 รับผิดชอบ: {assignee}\n"       # 👈 เติม \n ให้แล้วครับ
                                    f"🤝 ผู้ช่วย: {helper_text}"         # 👈 เปลี่ยนมาใช้ helper_text ที่จัดรูปแบบแล้ว
                                )
                                send_line_message(line_msg)
                        
                        st.success(f"บันทึกงาน '{task_detail}' เรียบร้อย!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"ระบบขัดข้อง: {e}")
            else:
                st.warning("⚠️ กรุณาระบุ 'ชื่อไซต์' และ 'รายละเอียดงาน'")
#หน้าที่4 ---------------------------------------------------------------------------------------------
elif menu == "📊 4. ภาพรวมงานของทีม (Team Manager)":
    st.title("📊 ภาพรวมงานของทีม (Team Workload)")
    st.write("ศูนย์บัญชาการสำหรับดูภาระงานของทุกคนในทีม เพื่อประกอบการตัดสินใจจ่ายงาน")
    
    try:
        df_tasks = load_sheet("Task & Workload")
        
        if not df_tasks.empty:
            df_tasks.columns = [str(c).strip() for c in df_tasks.columns]
            
            # 🌟 ความอัจฉริยะที่เพิ่มเข้ามา: รวบงานที่ซ้ำกัน ให้เหลือเฉพาะ "สถานะล่าสุด" (บรรทัดล่างสุด) แบบเดียวกับเมนู 3
            if 'ชื่อไซต์งาน' in df_tasks.columns and 'ชื่องาน / รายละเอียด' in df_tasks.columns:
                df_latest_tasks = df_tasks.drop_duplicates(
                    subset=['ชื่อไซต์งาน', 'ชื่องาน / รายละเอียด'], 
                    keep='last'
                )
            else:
                df_latest_tasks = df_tasks.copy()
            
# --- 📈 ส่วนที่ 1: กราฟสรุปภาระงาน (Workload) ---
            st.markdown("### 📈 ภาระงานรายบุคคล (Active Tasks)")
            
            # ดึงเฉพาะงานที่ยังไม่เสร็จ
            active_tasks = df_latest_tasks[df_latest_tasks['สถานะงาน'] != 'Complete']
            
            records_main = []
            records_asst = []
            
            for _, row in active_tasks.iterrows():
                # 1. แยกชื่อผู้รับผิดชอบหลัก
                main_p = str(row.get('ผู้รับผิดชอบหลัก', '')).strip()
                if main_p and main_p.lower() != 'nan' and main_p != '-':
                    records_main.append({'ชื่อทีมงาน': main_p})
                
                # 2. แยกชื่อผู้ช่วย
                asst_str = str(row.get('ผู้ช่วย', '')).strip()
                if asst_str and asst_str.lower() != 'nan' and asst_str != '-':
                    assistants = [a.strip() for a in asst_str.split(',') if a.strip()]
                    for a in assistants:
                        if a != main_p: # ป้องกันชื่อซ้ำในงานเดียวกัน
                            records_asst.append({'ชื่อทีมงาน': a})

            # ==========================================
            # 🌟 กราฟชุดที่ 1: ผู้รับผิดชอบหลัก (เต็มจอ)
            # ==========================================
            st.markdown("#### 📌 1. ผู้รับผิดชอบหลัก (Main Assignee)")
            if records_main:
                df_main = pd.DataFrame(records_main)
                wl_main = df_main.groupby('ชื่อทีมงาน').size().reset_index(name='จำนวนงาน (ชิ้น)')
                wl_main = wl_main.sort_values(by='จำนวนงาน (ชิ้น)', ascending=False)
                
                fig1 = px.bar(
                    wl_main, x='ชื่อทีมงาน', y='จำนวนงาน (ชิ้น)', text='จำนวนงาน (ชิ้น)',
                    color_discrete_sequence=['#008080'] # โทนเขียว-ฟ้า
                )
                fig1.update_traces(textposition='outside')
                fig1.update_layout(yaxis=dict(dtick=1))
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("ไม่มีงานค้างในส่วนของผู้รับผิดชอบหลักครับ")

            st.markdown("<br>", unsafe_allow_html=True) # เว้นระยะห่างระหว่างกราฟนิดนึง

            # ==========================================
            # 🌟 กราฟชุดที่ 2: ผู้ช่วยสนับสนุน (เต็มจอ)
            # ==========================================
            st.markdown("#### 🤝 2. ผู้ช่วยสนับสนุน (Assistant)")
            if records_asst:
                df_asst = pd.DataFrame(records_asst)
                wl_asst = df_asst.groupby('ชื่อทีมงาน').size().reset_index(name='จำนวนงาน (ชิ้น)')
                wl_asst = wl_asst.sort_values(by='จำนวนงาน (ชิ้น)', ascending=False)
                
                fig2 = px.bar(
                    wl_asst, x='ชื่อทีมงาน', y='จำนวนงาน (ชิ้น)', text='จำนวนงาน (ชิ้น)',
                    color_discrete_sequence=['#FF9F36'] # โทนส้ม
                )
                fig2.update_traces(textposition='outside')
                fig2.update_layout(yaxis=dict(dtick=1))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("ไม่มีงานค้างในส่วนของผู้ช่วยครับ")
            
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
            
            # 🌟 ทำการกรองข้อมูลตามที่ผู้ใช้เลือก (จากฐานข้อมูลล่าสุด df_latest_tasks)
            filtered_df = df_latest_tasks.copy()
            if filter_status:
                filtered_df = filtered_df[filtered_df['สถานะงาน'].isin(filter_status)]
                
            if filter_person != "ดูทุกคน":
                filtered_df = filtered_df[
                    (filtered_df['ผู้รับผิดชอบหลัก'] == filter_person) | 
                    (filtered_df['ผู้ช่วย'].str.contains(filter_person, na=False))
                ]
            
            # 🌟 จัดเรียงคอลัมน์ให้สวยงามและอ่านง่าย (เพิ่มปัญหา/หมายเหตุ เข้ามาด้วย)
            display_cols = ['วันที่เข้าทำ (Scheduled Date)', 'ชื่อไซต์งาน', 'ชื่องาน / รายละเอียด', 'ประเภทงาน', 'สถานะงาน', 'ผู้รับผิดชอบหลัก', 'ผู้ช่วย', 'ปัญหา/หมายเหตุ']
            available_cols = [col for col in display_cols if col in filtered_df.columns]
            
            # 🌟 ใส่สีให้สถานะงานเหมือนเมนู 3
            def highlight_status_m4(val):
                color = 'red' if 'Problem' in str(val) else ('green' if 'Complete' in str(val) else 'orange')
                return f'color: {color}'
            
            # แสดงตารางผลลัพธ์
            st.dataframe(filtered_df[available_cols].style.applymap(highlight_status_m4, subset=['สถานะงาน']), use_container_width=True, hide_index=True)
            
        else:
            st.info("ยังไม่มีข้อมูลงานในระบบครับ")
            
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการโหลดตารางงาน: {e}")
#หน้าที่5 ----------------------------------------------------------------------------------------
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
        df_equip = load_sheet("Master_Equipment")
        if 'Equipment' in df_equip.columns and 'Volume' in df_equip.columns:
            for _, row in df_equip.iterrows():
                tool_name = str(row['Equipment']).strip()
                volume = pd.to_numeric(row['Volume'], errors='coerce')
                if pd.notna(volume) and tool_name != "nan":
                    total_stock[tool_name] = int(volume)
                    borrowed_stock[tool_name] = 0
                    
        df_tools = load_sheet("Team_Tools")
        if not df_tools.empty:
            df_tools.columns = [str(c).strip() for c in df_tools.columns]
            has_qty_col = 'จำนวน' in df_tools.columns
            
            for _, row in df_tools.iterrows():
                hist_tool = str(row.iloc[2]).strip()
                hist_status = str(row.iloc[4]).strip()
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
            if remaining < 0: remaining = 0 
            
            display_text = f"{tool} (เหลือ {remaining}/{total})"
            tool_options_display.append(display_text)
            real_tool_names[display_text] = tool

    # --- ส่วนที่ 1: ฟอร์มเบิก/คืน ---
    st.markdown("### 📝 ฟอร์มทำรายการ")
    
    # 🌟 อัปเกรดเป็น st.container เพื่อให้โต้ตอบได้ทันที (Interactive)
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col2:
            status = st.radio("📌 สถานะการทำรายการ", ["🔴 ยืมอุปกรณ์ (Borrow)", "🟢 คืนอุปกรณ์ (Return)"], horizontal=True)
            site_used = st.selectbox("📍 นำไปใช้ที่ไซต์งาน", ["ส่วนกลาง / ออฟฟิศ"] + site_list)
            
        with col1:
            # 🌟 ทำให้ฉลาดขึ้น: ตั้งค่าเริ่มต้นเป็นชื่อคนที่ล็อกอินอยู่
            try:
                def_idx = team_members.index(CURRENT_USER)
            except:
                def_idx = 0
            borrower = st.selectbox("👤 ชื่อผู้เบิก/คืน", team_members, index=def_idx)
            
            # 🌟 เพิ่มกล่องติ๊กถูก "เลือกทั้งหมด"
            select_all = st.checkbox("☑️ เลือกอุปกรณ์ทั้งหมด (Select All)")
            
            if select_all:
                # ถ้ากดติ๊ก ให้ยัดทุกอย่างลงไปในช่องเลือกอัตโนมัติ
                selected_displays = st.multiselect("🔧 เลือกอุปกรณ์ (กดกากบาท ❌ เพื่อเอาบางชิ้นออกได้)", tool_options_display, default=tool_options_display)
            else:
                selected_displays = st.multiselect("🔧 เลือกอุปกรณ์ (กดเลือกได้หลายชิ้น)", tool_options_display)
        
        # 📦 สร้างช่องกรอกจำนวน โผล่ขึ้นมาตามของที่กดเลือกแบบ Real-time
        quantities = {}
        if selected_displays:
            st.markdown("---")
            st.markdown("**📦 ระบุจำนวนที่ต้องการทำรายการ:**")
            col_q1, col_q2 = st.columns(2)
            for i, display in enumerate(selected_displays):
                tool = real_tool_names[display]
                # สลับฝั่งซ้ายขวาให้ดูสวยงาม
                with col_q1 if i % 2 == 0 else col_q2:
                    quantities[tool] = st.number_input(f"จำนวน: {tool}", min_value=1, step=1, key=f"qty_{tool}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        # เปลี่ยนปุ่ม Submit ธรรมดา
        submitted = st.button("บันทึกข้อมูลเข้าคลัง", type="primary", use_container_width=True)
        
        if submitted:
            if selected_displays:
                with st.spinner("กำลังบันทึกข้อมูลเข้าทีละรายการ..."):
                    success_count = 0
                    for display in selected_displays:
                        tool = real_tool_names[display]
                        qty = quantities[tool]
                        
                        payload = {
                            "sheet": "Team_Tools",
                            "data": [
                                (pd.Timestamp.utcnow() + pd.Timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
                                borrower, tool, site_used, 
                                status.replace("🔴 ", "").replace("🟢 ", ""),
                                qty
                            ]
                        }
                        try:
                            requests.post(GAS_URL, data=json.dumps(payload))
                            success_count += 1
                        except:
                            pass
                            
                    if success_count == len(selected_displays):
                        st.success(f"✅ บันทึก '{status}' จำนวน {success_count} รายการ เรียบร้อยแล้ว!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun() # รีเฟรชหน้าเพื่ออัปเดตยอดคงเหลือ
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
            # แสดงจากล่างขึ้นบน (ล่าสุดอยู่บนสุด)
            st.dataframe(df_tools.iloc[::-1], use_container_width=True, hide_index=True)
    except:
        st.info("ยังไม่มีประวัติการเบิกใช้อุปกรณ์ในระบบครับ")
#หน้าที่6 --------------------------------------------------------------------------------
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
#หน้าที่9 --------------------------------------------------------------------------------
#หน้าที่9 --------------------------------------------------------------------------------
elif menu == "📅 9. แผนงานล่วงหน้า (Planned Tasks)":
    st.title("📅 แผนงานล่วงหน้า (Upcoming Projects & Plans)")
    st.write("ตารางบันทึกคิวงาน โปรเจกต์ติดตั้ง หรือแผนงานที่ทราบล่วงหน้า เพื่อเตรียมความพร้อมของทีม")

    # 1. โหลดข้อมูลไซต์และทีมงาน
    try:
        df_master = load_sheet("Master_Site")
        site_list = sorted(df_master['ชื่อไซต์งาน (Process Work)'].dropna().unique().tolist())
    except:
        site_list = []
    
    site_options = site_list + ["➕ อื่นๆ (ระบุเอง)"]
    team_members = ["ยังไม่ระบุตัวตน", "Heart", "Phubeth", "Mink", "Film", "Folk", "Chan"]
    # ตัด "ยังไม่ระบุตัวตน" ออกจากรายชื่อผู้ช่วย
    helper_members = [m for m in team_members if m != "ยังไม่ระบุตัวตน"]

    # 2. ฟอร์มเพิ่มแผนงานใหม่ (ซ่อนไว้ใน Expander เพื่อความสะอาดตา)
    with st.expander("➕ กดเพื่อเพิ่มแผนงานล่วงหน้า (Add New Plan)", expanded=False):
        with st.form("add_plan_form"):
            c1, c2 = st.columns(2)
            with c1:
                selected_site = st.selectbox("สถานที่ / ไซต์งาน", site_options)
                custom_site = st.text_input("ชื่อไซต์งาน (กรณีเลือกอื่นๆ):")
                task_detail = st.text_input("รายละเอียดโปรเจกต์ / แผนงาน:", placeholder="เช่น งานติดตั้งระบบใหม่ที่ Michelin หรือเช็คระบบ Rojana Power Plant...")
            with c2:
                target_date = st.date_input("กำหนดการโดยประมาณ (Target Date)")
                assignee = st.selectbox("ผู้รับผิดชอบโครงการ (ถ้าทราบ)", team_members)
                
                # 🌟 เพิ่มช่องเลือกผู้ช่วยแบบกดได้หลายคน
                assistants = st.multiselect("ผู้ช่วย (ถ้ามี)", helper_members)
                
                status = st.selectbox("สถานะแผนงาน", ["🟡 รอคอนเฟิร์ม (Tentative)", "🟢 ยืนยันแล้ว (Confirmed)", "🔵 โอนไปเป็นใบงานจริงแล้ว (Moved)"])
            
            remark = st.text_input("หมายเหตุ / สิ่งที่ต้องเตรียม:", placeholder="เช่น รอของเข้า, เตรียมสั่งอุปกรณ์ติดตั้ง, ขอกำลังเสริม...")
            
            submitted = st.form_submit_button("💾 บันทึกแผนงานล่วงหน้า", type="primary", use_container_width=True)
            
            if submitted:
                final_site = custom_site if selected_site == "➕ อื่นๆ (ระบุเอง)" else selected_site
                if final_site and task_detail:
                    
                    # 🌟 จัดรูปแบบรายชื่อผู้ช่วยให้พร้อมส่งเข้า GSheet
                    assistants_str = ", ".join(assistants) if assistants else "-"
                    
                    payload = {
                        "sheet": "Planned_Tasks",
                        "data": [
                            (pd.Timestamp.utcnow() + pd.Timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
                            final_site,
                            task_detail,
                            target_date.strftime("%d/%m/%Y"),
                            assignee,
                            assistants_str, # 👈 เพิ่มตัวแปรผู้ช่วยตรงนี้ (ตรงกับคอลัมน์ F)
                            status,
                            remark
                        ]
                    }
                    with st.spinner("กำลังบันทึกแผนงานล่วงหน้า..."):
                        try:
                            requests.post(GAS_URL, data=json.dumps(payload))
                            st.success(f"บันทึกแผนงาน '{task_detail}' ลงระบบเรียบร้อย!")
                            st.cache_data.clear()
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"เกิดข้อผิดพลาด: {e}")
                else:
                    st.warning("⚠️ กรุณาระบุชื่อไซต์และรายละเอียดงานให้ครบถ้วนครับ")

    st.markdown("---")

    # 3. ตารางแสดงแผนงานล่วงหน้า
    st.markdown("### 📋 ตารางติดตามแผนงานโปรเจกต์")
    try:
        df_plan = load_sheet("Planned_Tasks")
        if not df_plan.empty:
            df_plan.columns = [str(c).strip() for c in df_plan.columns]
            
            # ตัวกรองข้อมูลให้ดูง่ายขึ้น
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filter_status = st.multiselect("🔍 กรองสถานะ:", 
                                               ["🟡 รอคอนเฟิร์ม (Tentative)", "🟢 ยืนยันแล้ว (Confirmed)", "🔵 โอนไปเป็นใบงานจริงแล้ว (Moved)"], 
                                               default=["🟡 รอคอนเฟิร์ม (Tentative)", "🟢 ยืนยันแล้ว (Confirmed)"]) # ค่าเริ่มต้นจะไม่โชว์งานที่โอนไปทำจริงแล้ว
            
            # กรองตาราง
            if filter_status and 'สถานะ' in df_plan.columns:
                df_plan = df_plan[df_plan['สถานะ'].isin(filter_status)]
            
            # ใส่สีให้สถานะเพื่อความสวยงาม
            def highlight_plan_status(val):
                if 'รอคอนเฟิร์ม' in str(val): return 'color: #FF9F36' # สีส้ม
                elif 'ยืนยันแล้ว' in str(val): return 'color: #008080' # สีเขียว
                elif 'โอนไปเป็นใบงาน' in str(val): return 'color: gray' # สีเทา
                return ''
            
            # แสดงตาราง
            st.dataframe(df_plan.style.applymap(highlight_plan_status, subset=['สถานะ']), use_container_width=True, hide_index=True)
            
        else:
            st.info("ยังไม่มีข้อมูลแผนงานล่วงหน้าในระบบครับ (เริ่มกดเพิ่มแผนงานด้านบนได้เลย)")
    except Exception as e:
        st.warning(f"ระบบกำลังรอการสร้างแผ่น 'Planned_Tasks' ใน Google Sheets ครับ")
else:
    st.title(menu)
    st.write(f"กำลังพัฒนาฟีเจอร์สำหรับเมนูนี้ครับ...")
