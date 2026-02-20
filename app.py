import streamlit as st
import requests
import json
import pandas as pd
import folium
from streamlit_folium import st_folium
import urllib.parse 
import plotly.express as px

# --- 1. ตั้งค่าหน้าเว็บ ---
st.set_page_config(page_title="Sensor Team Dashboard", page_icon="⚙️", layout="wide")

# --- 2. ดึงกุญแจลับจากตู้เซฟ ---
GAS_URL = st.secrets["GAS_URL"]
SHEET_URL = st.secrets["SHEET_URL"]

# 🌟 --- ฟังก์ชันส่วนกลาง --- 🌟
@st.cache_data(ttl=60)
def load_sheet(sheet_name):
    sheet_id = SHEET_URL.split("/d/")[1].split("/")[0]
    encoded_sheet_name = urllib.parse.quote(sheet_name)
    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}"
    return pd.read_csv(csv_url)

# --- 3. สร้างระบบเมนูแถบด้านข้าง (Sidebar) ---
st.sidebar.title("🛠️ Sensor Team Menu")
menu = st.sidebar.radio("เลือกเมนูการใช้งาน:", [
    "🏠 1. ภาพรวมและสถิติ (Dashboard)",
    "🏢 2. เจาะลึกรายไซต์ (Site Detail)",
    "📱 3. กระดานงานส่วนตัว (My Workload)",
    "📊 4. ภาพรวมงานของทีม (Team Manager)",
    "🧰 5. ระบบเบิก-คืนอุปกรณ์ (Tools)",
    "👥 6. ข้อมูลทีม (Team Profile)",
    "🧠 7. ศูนย์การเรียนรู้ (Learning & Quiz)",
    "📚 8. คู่มือการใช้งาน (Manuals & Docs)"
])

st.sidebar.markdown("---")
st.sidebar.info("👨‍💻 เข้าสู่ระบบโดย: **Heart**")

# --- 4. โครงสร้างแต่ละเมนู ---

if menu == "🏠 1. ภาพรวมและสถิติ (Dashboard)":
    st.title("📊 ศูนย์บัญชาการทีม Sensor (Command Center)")
    st.write("ภาพรวมสรุปข้อมูลทั้งหมดของทีม และระบบแจ้งเตือนอัตโนมัติ")
    st.markdown("---")

    try:
        # โหลดข้อมูลพื้นฐาน
        df_pm = load_sheet("PM_Plan")
        df_task = load_sheet("Task & Workload")
        df_team = load_sheet("Team_Profile")
        df_master = load_sheet("Master_Site")
        
        # จัดการหัวคอลัมน์ให้คลีน
        for df in [df_pm, df_task, df_team, df_master]:
            if not df.empty: df.columns = [str(c).strip() for c in df.columns]

        # สรุปตัวเลข KPI
        total_sites = len(df_pm['ชื่อไซต์งาน'].dropna().unique()) if 'ชื่อไซต์งาน' in df_pm.columns else 0
        active_tasks = len(df_task[df_task['สถานะงาน'] != 'Complete']) if 'สถานะงาน' in df_task.columns else 0
        total_members = len(df_team['ชื่อ'].dropna()) if 'ชื่อ' in df_team.columns else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("🏢 ไซต์งานทั้งหมด", f"{total_sites} ไซต์")
        c2.metric("📋 งานที่กำลังทำ", f"{active_tasks} งาน")
        c3.metric("👥 สมาชิกทีม", f"{total_members} คน")

        st.markdown("<br>", unsafe_allow_html=True)
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 🚨 แจ้งเตือนซิม/สัญญา")
            if 'วันที่ซิมหมดอายุ' in df_pm.columns:
                sim_alert = df_pm[['ชื่อไซต์งาน', 'วันที่ซิมหมดอายุ']].dropna()
                sim_alert = sim_alert[sim_alert['วันที่ซิมหมดอายุ'].astype(str).str.strip() != ""]
                if not sim_alert.empty:
                    with st.container(height=300):
                        for _, r in sim_alert.iterrows():
                            exp = str(r['วันที่ซิมหมดอายุ']).strip()
                            if "หมด" in exp: st.error(f"❌ **{r['ชื่อไซต์งาน']}**: ซิมหมดอายุ!")
                            else: st.warning(f"⚠️ **{r['ชื่อไซต์งาน']}**: หมดอายุ {exp}")
            else: st.info("ยังไม่มีข้อมูลซิมการ์ด")

        with col_r:
            st.markdown("### 👷‍♂️ ภาระงานรายบุคคล")
            if 'ผู้รับผิดชอบหลัก' in df_task.columns:
                workload = df_task[df_task['สถานะงาน'] != 'Complete']['ผู้รับผิดชอบหลัก'].value_counts().reset_index()
                workload.columns = ['ชื่อ', 'งานค้าง']
                st.dataframe(workload, use_container_width=True, hide_index=True)

        st.markdown("### 🗺️ พิกัดไซต์งาน")
        if 'ละติจูด (Latitude)' in df_master.columns:
            m = folium.Map(location=[13.73, 100.52], zoom_start=6)
            for _, r in df_master.dropna(subset=['ละติจูด (Latitude)', 'ลองจิจูด (Longitude)']).iterrows():
                folium.Marker([r['ละติจูด (Latitude)'], r['ลองจิจูด (Longitude)']], popup=r['ชื่อไซต์งาน (Process Work)']).add_to(m)
            st_folium(m, width=1000, height=400)
    except: st.warning("กำลังรอข้อมูลจาก Google Sheets...")

elif menu == "🏢 2. เจาะลึกรายไซต์ (Site Detail)":
    st.title("🏢 ข้อมูลรายไซต์")
    try:
        df_master = load_sheet("Master_Site")
        site_list = df_master['ชื่อไซต์งาน (Process Work)'].dropna().unique().tolist()
        selected_site = st.selectbox("🔍 เลือกไซต์งาน:", site_list)
        
        tab1, tab2, tab3 = st.tabs(["🗓️ แผน PM", "📡 อุปกรณ์", "🚨 ประวัติปัญหา"])
        
        with tab1:
            df_pm = load_sheet("PM_Plan")
            df_pm.columns = [str(c).strip() for c in df_pm.columns]
            site_pm = df_pm[df_pm['ชื่อไซต์งาน'] == selected_site]
            if not site_pm.empty:
                row = site_pm.iloc[0]
                pm_cols = ['PM ใหญ่', 'PM ย่อย ครั้งที่ 1', 'PM ย่อย ครั้งที่ 2', 'PM ย่อย ครั้งที่ 3']
                pm_data = [{"รอบ": c, "กำหนดการ": str(row[c])} for c in pm_cols if c in site_pm.columns and str(row[c]).strip() != "nan"]
                st.table(pd.DataFrame(pm_data))
        
        with tab2:
            df_assets = load_sheet("Asset_Sensor")
            df_assets.columns = [str(c).strip() for c in df_assets.columns]
            st.dataframe(df_assets[df_assets['ชื่อไซต์งาน'] == selected_site], use_container_width=True, hide_index=True)
            
        with tab3:
            df_tasks = load_sheet("Task & Workload")
            df_tasks.columns = [str(c).strip() for c in df_tasks.columns]
            st.dataframe(df_tasks[df_tasks['ชื่อไซต์งาน'] == selected_site], use_container_width=True, hide_index=True)
    except: st.error("ไม่พบข้อมูล")

elif menu == "📱 3. กระดานงานส่วนตัว (My Workload)":
    st.title("📱 งานของฉัน")
    CURRENT_USER = "Heart"
    try:
        df_tasks = load_sheet("Task & Workload")
        df_tasks.columns = [str(c).strip() for c in df_tasks.columns]
        my_tasks = df_tasks[(df_tasks['ผู้รับผิดชอบหลัก'] == CURRENT_USER) | (df_tasks['ผู้ช่วย'].str.contains(CURRENT_USER, na=False))]
        st.dataframe(my_tasks, use_container_width=True, hide_index=True)
    except: st.info("ไม่มีงานค้าง")

    st.markdown("### ➕ อัปเดตงาน")
    with st.form("task_form"):
        site = st.text_input("ชื่อไซต์งาน")
        task = st.text_input("รายละเอียดงาน")
        status = st.selectbox("สถานะ", ["Planning", "In progress", "Problem", "Complete"])
        if st.form_submit_button("บันทึก"):
            payload = {"sheet": "Task & Workload", "data": [pd.Timestamp.now().strftime("%Y-%m-%d"), site, task, "งานด่วน", "-", "-", status, CURRENT_USER, ""]}
            requests.post(GAS_URL, data=json.dumps(payload))
            st.success("บันทึกแล้ว!")

elif menu == "📊 4. ภาพรวมงานของทีม (Team Manager)":
    st.title("📊 ภาระงานทีม")
    df_tasks = load_sheet("Task & Workload")
    df_tasks.columns = [str(c).strip() for c in df_tasks.columns]
    active = df_tasks[df_tasks['สถานะงาน'] != 'Complete']
    fig = px.bar(active['ผู้รับผิดชอบหลัก'].value_counts().reset_index(), x='ผู้รับผิดชอบหลัก', y='count', title="งานค้างรายบุคคล")
    st.plotly_chart(fig, use_container_width=True)

elif menu == "🧰 5. ระบบเบิก-คืนอุปกรณ์ (Tools)":
    st.title("🧰 เบิก-คืนอุปกรณ์")
    st.info("ใช้สำหรับบันทึกการเบิกอุปกรณ์จากคลังส่วนกลาง")
    # ... (ส่วนนี้ใช้ตามโครงสร้างเดิมของคุณ Heart ใน GSheet ได้เลยครับ) ...

elif menu == "👥 6. ข้อมูลทีม (Team Profile)":
    st.title("👥 ประวัติทีมงาน")
    df_team = load_sheet("Team_Profile")
    df_team.columns = [str(c).strip() for c in df_team.columns]
    cols = st.columns(2)
    for i, r in df_team.iterrows():
        with cols[i % 2]:
            st.info(f"### {r.get('อีโมจิ', '👤')} {r['ชื่อ']}")
            st.write(f"**ตำแหน่ง:** {r['ตำแหน่ง']}")
            st.write(f"**ใบเซอร์:** {r.get('ใบเซอร์', '-')}")

elif menu == "🧠 7. ศูนย์การเรียนรู้ (Learning & Quiz)":
    st.title("🧠 คลังความรู้")
    t1, t2, t3 = st.tabs(["📚 ความรู้", "📝 ควิซ", "🧮 เครื่องคิดเลข"])
    with t1:
        df_learn = load_sheet("Learning_Content")
        for _, r in df_learn.iterrows():
            with st.expander(f"📖 {r['ชื่อหัวข้อ']}"):
                st.info(f"**สูตร:** {r['สูตรการคำนวณ']}")
                st.write(r['ข้อมูลการคำนวณ'])
                st.success(f"**ตัวอย่าง:** {r['ตัวอย่างการคำนวณ']}")
    with t3:
        df_calc = load_sheet("Calc_Tools")
        st.write("เลือกสูตรจาก GSheet เพื่อคำนวณ")
        # (โค้ดคำนวณ Dynamic ที่เราทำไว้จะรันตรงนี้)

elif menu == "📚 8. คู่มือการใช้งาน (Manuals & Docs)":
    st.title("📚 โฟลเดอร์คู่มือ")
    df_docs = load_sheet("Manual_Docs")
    for _, r in df_docs.iterrows():
        st.markdown(f"### 📂 {r['หมวดหมู่']}")
        st.write(r['รายละเอียด'])
        st.markdown(f"[🔗 เปิดโฟลเดอร์]({r['ลิงก์โฟลเดอร์']})")
        st.divider()
