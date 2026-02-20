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

    st.title("🏢 เจาะลึกข้อมูลรายไซต์ (Site Detail)")



    try:

        df_master = load_sheet("Master_Site")

        site_list = df_master['ชื่อไซต์งาน (Process Work)'].dropna().unique().tolist()

        

        # 🌟 1. เพิ่มตัวเลือก "ดูทุกไซต์" ไว้บนสุด

        site_options = ["🌐 ดูแผน PM รวมทุกไซต์ (All Sites)"] + site_list

        selected_site = st.selectbox("🔍 ค้นหาหรือเลือกไซต์งานที่ต้องการดูข้อมูล:", site_options)

        

        st.markdown("---")

        

        # 🌟 2. ถ้ายกเลิกการเลือกไซต์ (ดูภาพรวมทั้งหมด)

        if selected_site == "🌐 ดูแผน PM รวมทุกไซต์ (All Sites)":

            st.subheader("🌐 ภาพรวมตารางแผน PM ทุกไซต์งานประจำปี")

            try:

                df_pm = load_sheet("PM_Plan")

                st.dataframe(df_pm, use_container_width=True, hide_index=True)

                st.info("💡 เลื่อนแถบด้านล่างตารางไปทางขวา เพื่อดูเดือนอื่นๆ ได้เลยครับ")

            except Exception as e:

                st.error(f"ไม่สามารถโหลดข้อมูลแผน PM รวมได้: {e}")

                

        # 🌟 3. ถ้าเลือกเจาะจงไซต์ใดไซต์หนึ่ง (โชว์ PM 4 ครั้งเน้นๆ)

        else:

            st.subheader(f"📍 ข้อมูลสรุปของไซต์: {selected_site}")

            # สลับเอาแผน PM ขึ้นมาเป็นแท็บแรกเลย เพราะสำคัญสุด

            tab1, tab2, tab3 = st.tabs(["🗓️ แผน PM (PM Plan)", "📡 อุปกรณ์ (Assets)", "🚨 ประวัติปัญหา (Issue Log)"])

            

            # --- Tab 1: แผนงานประจำปี (สกัดมาแค่ 4 ครั้ง) ---

            with tab1:

                try:

                    df_pm = load_sheet("PM_Plan")

                    df_pm.columns = [str(c).strip() for c in df_pm.columns]

                    

                    site_col = None

                    for col in df_pm.columns:

                        if "ชื่อไซต์" in str(col) or "Process Work" in str(col):

                            site_col = col

                            break

                            

                    if site_col:

                        site_pm = df_pm[df_pm[site_col] == selected_site]

                        if not site_pm.empty:

                            # 🤖 ระบบสกัดข้อมูล: หาคอลัมน์ที่มีการกรอกแผนไว้

                            pm_schedule = []

                            row_data = site_pm.iloc[0] # ดึงข้อมูลแถวของไซต์นี้มา

                            

                            for col_name, val in row_data.items():

                                val_str = str(val).strip()

                                # เช็คว่าช่องนี้มีข้อมูล และไม่ใช่คอลัมน์ชื่อไซต์/กลุ่มงาน

                                if val_str.lower() != 'nan' and val_str != '' and col_name != site_col and "กลุ่มงาน" not in col_name:

                                    pm_schedule.append({

                                        "ช่วงเวลา (เดือน_สัปดาห์)": col_name, 

                                        "ประเภทงาน (ที่แพลนไว้)": val_str

                                    })

                            

                            if pm_schedule:

                                st.success(f"📌 ไซต์นี้มีกำหนดเข้าทำ PM จำนวน {len(pm_schedule)} ครั้ง ดังนี้ครับ:")

                                st.dataframe(pd.DataFrame(pm_schedule), use_container_width=True, hide_index=True)

                            else:

                                st.info("ยังไม่มีการระบุแผน PM ในตารางสำหรับไซต์นี้ครับ")

                        else:

                            st.warning("ไม่พบชื่อไซต์นี้ในตาราง PM_Plan ครับ")

                    else:

                        st.error("หาคอลัมน์ 'ชื่อไซต์งาน' ในแผ่น PM_Plan ไม่เจอครับ")

                except Exception as e:

                    st.error(f"เกิดข้อผิดพลาดในการโหลดแผน PM: {e}")

                    

            # --- Tab 2: อุปกรณ์ที่ติดตั้ง ---

            with tab2:

                try:

                    df_assets = load_sheet("Asset_Sensor")

                    df_assets.columns = [str(c).strip() for c in df_assets.columns]

                    if not df_assets.empty and 'ชื่อไซต์งาน' in df_assets.columns:

                        site_assets = df_assets[df_assets['ชื่อไซต์งาน'] == selected_site]

                        if not site_assets.empty:

                            st.dataframe(site_assets.drop(columns=['ชื่อไซต์งาน']), use_container_width=True, hide_index=True)

                        else:

                            st.info("ยังไม่มีข้อมูลอุปกรณ์เซ็นเซอร์ติดตั้งสำหรับไซต์นี้ครับ")

                except:

                    st.warning("ระบบกำลังรอตาราง Asset_Sensor")

                    

            # --- Tab 3: ประวัติปัญหา ---

            with tab3:

                try:

                    df_tasks = load_sheet("Task & Workload")

                    df_tasks.columns = [str(c).strip() for c in df_tasks.columns]

                    if not df_tasks.empty and 'ชื่อไซต์งาน' in df_tasks.columns:

                        site_tasks = df_tasks[df_tasks['ชื่อไซต์งาน'] == selected_site]

                        if not site_tasks.empty:

                            show_problems_only = st.checkbox("🔥 โชว์เฉพาะงานที่ 'ติดปัญหา' (Problem)")

                            if show_problems_only:

                                site_tasks = site_tasks[site_tasks['สถานะงาน'] == 'Problem']

                            st.dataframe(site_tasks.drop(columns=['ชื่อไซต์งาน']), use_container_width=True, hide_index=True)

                        else:

                            st.success("🎉 ไซต์นี้ยังไม่เคยมีประวัติปัญหาเลยครับ ยอดเยี่ยมมาก!")

                except:

                    st.warning("ระบบกำลังรอตาราง Task & Workload")



    except Exception as e:

        st.error(f"ระบบขัดข้อง กรุณาตรวจสอบแผ่น Master_Site ใน GSheet: {e}")

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
