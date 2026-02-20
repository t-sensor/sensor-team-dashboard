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
    st.write("ภาพรวมสรุปข้อมูลทั้งหมดของทีม แผนที่ไซต์งาน และระบบแจ้งเตือนอัตโนมัติ")
    st.markdown("---")

    # โหลดข้อมูลจาก 4 ตารางหลักมาเก็บไว้ก่อน
    try:
        df_pm = load_sheet("PM_Plan")
        df_pm.columns = [str(c).strip() for c in df_pm.columns]
    except:
        df_pm = pd.DataFrame()
        
    try:
        df_task = load_sheet("Task & Workload")
        df_task.columns = [str(c).strip() for c in df_task.columns]
    except:
        df_task = pd.DataFrame()

    try:
        df_team = load_sheet("Team_Profile")
        df_team.columns = [str(c).strip() for c in df_team.columns]
    except:
        df_team = pd.DataFrame()
        
    try:
        df_master = load_sheet("Master_Site")
        df_master.columns = [str(c).strip() for c in df_master.columns]
    except:
        df_master = pd.DataFrame()

    # สร้างการ์ดสรุปตัวเลข (KPI Metrics)
    total_sites = len(df_pm['ชื่อไซต์งาน'].dropna().unique()) if not df_pm.empty and 'ชื่อไซต์งาน' in df_pm.columns else 0
    active_tasks = len(df_task[df_task['สถานะงาน'] != 'Complete']) if not df_task.empty and 'สถานะงาน' in df_task.columns else 0
    total_members = len(df_team['ชื่อ'].dropna()) if not df_team.empty and 'ชื่อ' in df_team.columns else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("🏢 จำนวนไซต์งานทั้งหมด", f"{total_sites} ไซต์")
    col2.metric("📋 โปรเจกต์ที่รอดำเนินการ", f"{active_tasks} งาน")
    col3.metric("👥 สมาชิกในทีม", f"{total_members} คน")
    
    st.markdown("<br>", unsafe_allow_html=True)

    # แบ่งหน้าจอเป็น 2 ฝั่ง (ซ้าย: แจ้งเตือนซิม | ขวา: ภาระงาน)
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 🚨 แจ้งเตือนซิม/สัญญา")
        if not df_pm.empty and 'วันที่ซิมหมดอายุ' in df_pm.columns and 'ชื่อไซต์งาน' in df_pm.columns:
            sim_data = df_pm[['ชื่อไซต์งาน', 'วันที่ซิมหมดอายุ']].dropna()
            sim_data = sim_data[sim_data['วันที่ซิมหมดอายุ'].astype(str).str.strip() != "nan"]
            sim_data = sim_data[sim_data['วันที่ซิมหมดอายุ'].astype(str).str.strip() != ""]
            sim_data = sim_data[sim_data['วันที่ซิมหมดอายุ'].astype(str).str.strip() != "-"]
            
            if not sim_data.empty:
                with st.container(height=300): 
                    for _, row in sim_data.iterrows():
                        site = str(row['ชื่อไซต์งาน']).strip()
                        exp = str(row['วันที่ซิมหมดอายุ']).strip()
                        
                        if exp == "หมด" or "หมด" in exp:
                            st.error(f"❌ **{site}**: ซิมหมดอายุแล้ว!")
                        else:
                            st.warning(f"⚠️ **{site}**: หมดอายุ {exp}")
            else:
                st.success("✅ ยอดเยี่ยม! ไม่มีซิมการ์ดที่ใกล้หมดอายุครับ")
        else:
            st.info("รอการซิงค์ข้อมูลซิมการ์ดจากแผ่น PM_Plan...")

    with col_right:
        st.markdown("### 👷‍♂️ สถานะงานค้างรายบุคคล")
        if not df_task.empty and 'ผู้รับผิดชอบหลัก' in df_task.columns and 'สถานะงาน' in df_task.columns:
            active_df = df_task[df_task['สถานะงาน'] != 'Complete']
            if not active_df.empty:
                workload = active_df['ผู้รับผิดชอบหลัก'].value_counts().reset_index()
                workload.columns = ['ชื่อทีมงาน', 'จำนวนโปรเจกต์ที่ค้างอยู่']
                st.dataframe(workload, use_container_width=True, hide_index=True)
            else:
                st.success("🎉 สุดยอดมาก! ตอนนี้ทีมเซ็นเซอร์เคลียร์งานครบ 100% แล้ว")
        else:
            st.info("รอการซิงค์ตารางงานจากแผ่น Task & Workload...")

    st.markdown("---")
    
    # ดึงแผนที่มาโชว์ด้านล่างสุดของหน้าแรก
    st.markdown("### 🗺️ แผนที่พิกัดไซต์งานทั้งหมด")
    if not df_master.empty and 'ละติจูด (Latitude)' in df_master.columns and 'ลองจิจูด (Longitude)' in df_master.columns:
        df_map = df_master.dropna(subset=['ละติจูด (Latitude)', 'ลองจิจูด (Longitude)'])
        if not df_map.empty:
            m = folium.Map(location=[13.736717, 100.523186], zoom_start=6)
            for index, row in df_map.iterrows():
                site_name = str(row.get('ชื่อไซต์งาน (Process Work)', 'ไม่ระบุ'))
                lat = pd.to_numeric(row['ละติจูด (Latitude)'], errors='coerce')
                lon = pd.to_numeric(row['ลองจิจูด (Longitude)'], errors='coerce')
                county = str(row.get('กลุ่มงาน (County)', 'ไม่ระบุ'))
                
                if pd.notna(lat) and pd.notna(lon):
                    popup_text = f"<b>{site_name}</b><br>กลุ่มงาน: {county}"
                    folium.Marker(
                        [lat, lon], popup=popup_text, icon=folium.Icon(color="green", icon="info-sign")
                    ).add_to(m)
            st_folium(m, width=1000, height=500)
        else:
            st.info("ไม่มีข้อมูลพิกัดในตาราง Master_Site")
    else:
        st.info("รอการปรับปรุงข้อมูลแผนที่ครับ")

elif menu == "🏢 2. เจาะลึกรายไซต์ (Site Detail)":
    st.title("🏢 เจาะลึกข้อมูลรายไซต์ (Site Detail)")

    try:
        df_master = load_sheet("Master_Site")
        site_list = df_master['ชื่อไซต์งาน (Process Work)'].dropna().unique().tolist()
        
        site_options = ["🌐 ดูแผน PM รวมทุกไซต์ (All Sites)"] + site_list
        selected_site = st.selectbox("🔍 ค้นหาหรือเลือกไซต์งานที่ต้องการดูข้อมูล:", site_options)
        
        st.markdown("---")
        
        if selected_site == "🌐 ดูแผน PM รวมทุกไซต์ (All Sites)":
            st.subheader("🌐 ภาพรวมตารางแผน PM ทุกไซต์งานประจำปี")
            try:
                df_pm = load_sheet("PM_Plan")
                st.dataframe(df_pm, use_container_width=True, hide_index=True)
                st.info("💡 เลื่อนแถบด้านล่างตารางไปทางขวา เพื่อดูเดือนอื่นๆ ได้เลยครับ")
            except Exception as e:
                st.error(f"ไม่สามารถโหลดข้อมูลแผน PM รวมได้: {e}")
                
        else:
            st.subheader(f"📍 ข้อมูลสรุปของไซต์: {selected_site}")
            tab1, tab2, tab3 = st.tabs(["🗓️ แผน PM (PM Plan)", "📡 อุปกรณ์ (Assets)", "🚨 ประวัติปัญหา (Issue Log)"])
            
            with tab1:
                try:
                    df_pm = load_sheet("PM_Plan")
                    df_pm.columns = [str(c).strip() for c in df_pm.columns]
                    
                    if 'ชื่อไซต์งาน' in df_pm.columns:
                        site_pm = df_pm[df_pm['ชื่อไซต์งาน'] == selected_site]
                        if not site_pm.empty:
                            
                            if 'วันที่ซิมหมดอายุ' in site_pm.columns:
                                sim_dates = site_pm['วันที่ซิมหมดอายุ'].dropna().astype(str).str.strip()
                                sim_dates = sim_dates[(sim_dates != "nan") & (sim_dates != "")]
                                if not sim_dates.empty:
                                    unique_sim_dates = sim_dates.unique()
                                    st.markdown("### 📶 ⚠️ แจ้งเตือนสถานะซิมการ์ด")
                                    for date in unique_sim_dates:
                                        st.error(f"🚨 **ระวัง!** ซิมการ์ดของไซต์นี้ หมดอายุในวันที่: **{date}**")
                            
                            st.success(f"📌 กำหนดการเข้าทำ PM ของไซต์: {selected_site}")
                            
                            pm_data = []
                            row = site_pm.iloc[0] 
                            pm_columns = ['PM ใหญ่', 'PM ย่อย ครั้งที่ 1', 'PM ย่อย ครั้งที่ 2', 'PM ย่อย ครั้งที่ 3']
                            
                            for col in pm_columns:
                                if col in site_pm.columns:
                                    val = str(row[col]).strip()
                                    if val and val.lower() != 'nan' and val != '-':
                                        pm_data.append({"รอบการทำงาน": col, "กำหนดการ (เดือนและสัปดาห์)": val})
                            
                            if pm_data:
                                st.dataframe(pd.DataFrame(pm_data), use_container_width=True, hide_index=True)
                            else:
                                st.info("ยังไม่ได้ระบุเดือนที่เข้าทำ PM สำหรับไซต์นี้ครับ")
                                
                        else:
                            st.info("ยังไม่มีข้อมูลแผน PM สำหรับไซต์นี้ครับ")
                    else:
                        st.warning("รอการปรับปรุงหัวคอลัมน์ 'ชื่อไซต์งาน' ในแผ่น PM_Plan ครับ")
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาดในการโหลดแผน PM: {e}")
                    
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
    st.title("📱 กระดานงานส่วนตัว")
    
    CURRENT_USER = "Heart"
    st.info(f"👤 สวัสดีครับคุณ **{CURRENT_USER}** นี่คืองานที่อยู่ในความรับผิดชอบของคุณครับ")

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
        else:
            st.info("ตารางใน GSheet ยังว่างเปล่าครับ")
            
    except Exception as e:
        st.error(f"ระบบขัดข้อง: {e}")
    
    team_members = ["Heart", "Phubeth", "Mink", "Film", "Folk", "Chan"]
    st.markdown("### ➕ ฟอร์มแจ้งงานด่วน / อัปเดตงาน")
    with st.form("task_form"):
        col1, col2 = st.columns(2)
        with col1:
            site_name = st.text_input("ชื่อไซต์งาน", placeholder="เช่น CPN อยุธยา")
            task_detail = st.text_input("ชื่อง
