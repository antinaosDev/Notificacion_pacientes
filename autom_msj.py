import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pywhatkit
import io
import json
import os
import time
import threading

# Configuración de página
st.set_page_config(
    page_title="Sistema de Notificaciones Médicas",
    page_icon="🏥",
    layout="wide"
)

# CSS
st.markdown("""
<style>
.header {background: linear-gradient(135deg, #1E88E5 0%, #43A047 100%);
padding: 2rem; border-radius: 10px; margin-bottom: 2rem; color: white; text-align: center;}
.logo-container {display: flex; justify-content: center; align-items: center; gap: 1rem; margin-bottom: 1rem;}
.logo {font-size: 3rem; font-weight: bold;}
.stButton>button {background-color: #1E88E5; color: white; border: none; border-radius: 5px; padding: 0.5rem 1rem;}
.stButton>button:hover {background-color: #0D47A1;}
</style>
""", unsafe_allow_html=True)

# Función cargar datos
@st.cache_data
def load_data(file):
    if file is not None:
        df = pd.read_excel(file, dtype={'TELEFONO': str})
        required_columns = ['RUT','NOMBRE_PACIENTE','TELEFONO','FECHA_ATENCION',
                            'MOTIVO_CONSULTA','PROFESIONAL','¿NOTIFICADO?',
                            '¿CAMBIO DE HORA?','NUEVA_FECHA','PROFESIONAL_REASIGNADO']
        for col in required_columns:
            if col not in df.columns:
                df[col] = None
        for col in ['FECHA_NOTIFICACION','HORA_NOTIFICACION','METODO_NOTIFICACION']:
            if col not in df.columns:
                df[col] = None
        df['FECHA_ATENCION'] = pd.to_datetime(df['FECHA_ATENCION'], errors='coerce')
        df['NUEVA_FECHA'] = pd.to_datetime(df['NUEVA_FECHA'], errors='coerce')
        return df
    return pd.DataFrame()

# Guardar logs
def save_log(log_entry):
    log_file = "notification_log.json"
    logs = []
    if os.path.exists(log_file):
        with open(log_file,"r") as f:
            logs = json.load(f)
    logs.append(log_entry)
    with open(log_file,"w") as f:
        json.dump(logs,f,indent=2,default=str)

# Enviar WhatsApp
def send_whatsapp(phone, message):
    try:
        if not str(phone).startswith("+"):
            phone = "+56" + str(phone)
        pywhatkit.sendwhatmsg_instantly(phone,message,tab_close=True,wait_time=10)
        return True, "Mensaje enviado por WhatsApp"
    except Exception as e:
        return False, f"Error WhatsApp: {str(e)}"

# Mensajes
def create_reminder_message(row):
    fecha_cita = row['FECHA_ATENCION'].strftime("%d/%m/%Y") if pd.notnull(row['FECHA_ATENCION']) else "sin fecha"
    return f"""
🏥 CESFAM Cholchol - Recordatorio de Cita 🏥

Hola {row['NOMBRE_PACIENTE']},

Le recordamos que tiene programada una cita médica:

📅 Fecha: {fecha_cita}
👨‍⚕️ Profesional: {row['PROFESIONAL']}
📋 Motivo: {row['MOTIVO_CONSULTA']}

📍 Lugar: Centro de Salud Familiar CESFAM Cholchol
Calle Anibal Pinto 552, Cholchol

📋 Recomendaciones:
- Llegar 15 minutos antes de su hora de cita
- Traer su cédula de identidad y carnet de salud
- Si no puede asistir, notificar con anticipación

Para confirmar, reagendar o consultar:
📧 Email: cholcholsome@gmail.com

*Este es un mensaje automático, por favor no responder directamente.*
"""

def create_change_message(row):
    nueva_fecha = row['NUEVA_FECHA'].strftime("%d/%m/%Y")
    profesional = row['PROFESIONAL_REASIGNADO']
    return f"""
🏥 CESFAM Cholchol - Cambio de Cita 🏥

Hola {row['NOMBRE_PACIENTE']},

Su cita ha sido reprogramada:

📅 Nueva Fecha: {nueva_fecha}
👨‍⚕️ Profesional: {profesional}
📋 Motivo: {row['MOTIVO_CONSULTA']}

*Mensaje automático*
"""

# Cabecera
st.markdown("""
<div class="header">
<div class="logo-container">
<div class="logo">🏥</div>
<div>
<h1>Sistema de Notificaciones Médicas</h1>
<p>Análisis y gestión de citas médicas</p>
</div>
<div class="logo">📊</div>
</div>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    mode = st.radio("Modo de ejecución:",("Automático","Manual"))
    if mode=="Manual":
        manual_btn = st.button("🚀 Ejecutar Notificaciones (Manual)")
    show_logs = st.button("📋 Ver Registros")

# Carga Excel
st.header("📂 Carga de Datos")
uploaded_file = st.file_uploader("Subir archivo Excel con citas médicas", type=["xlsx","xls"])
df = load_data(uploaded_file)

# Función principal
def process_notifications(df):
    success_count = 0
    error_count = 0
    today = datetime.now().date()
    target_date = today + timedelta(days=2)

    # 1️⃣ Recordatorios de citas nuevas (no notificadas)
    to_notify = df[(df['¿NOTIFICADO?'] != True) & 
                   (df['FECHA_ATENCION'].dt.date >= today) &
                   (df['FECHA_ATENCION'].dt.date <= target_date)]
    
    for idx,row in to_notify.iterrows():
        message = create_reminder_message(row)
        phone = row['TELEFONO']
        success,result = send_whatsapp(phone,message)
        if success:
            df.at[idx,'¿NOTIFICADO?'] = True
            df.at[idx,'FECHA_NOTIFICACION'] = datetime.now().date()
            df.at[idx,'HORA_NOTIFICACION'] = datetime.now().strftime("%H:%M:%S")
            df.at[idx,'METODO_NOTIFICACION'] = "WhatsApp"
            success_count += 1
        else:
            error_count += 1
        log_entry = {"timestamp":datetime.now(),"patient":row['NOMBRE_PACIENTE'],
                     "phone":phone,"type":"Recordatorio","method":"WhatsApp",
                     "message":message,"status":"Enviado" if success else "Error"}
        if not success:
            log_entry["error"] = result
        save_log(log_entry)
        time.sleep(1)

    # 2️⃣ Mensajes de reprogramación
    changed_appointments = df[(df['¿CAMBIO DE HORA?'] == True) &
                              df['NUEVA_FECHA'].notnull() &
                              df['PROFESIONAL_REASIGNADO'].notnull() &
                              (df['FECHA_ATENCION'].dt.date >= today) &
                              (df['FECHA_ATENCION'].dt.date <= target_date)]
    
    for idx,row in changed_appointments.iterrows():
        message = create_change_message(row)
        phone = row['TELEFONO']
        success,result = send_whatsapp(phone,message)
        if success:
            df.at[idx,'FECHA_NOTIFICACION'] = datetime.now().date()
            df.at[idx,'HORA_NOTIFICACION'] = datetime.now().strftime("%H:%M:%S")
            df.at[idx,'METODO_NOTIFICACION'] = "WhatsApp"
            df.at[idx,'¿CAMBIO DE HORA?'] = False
            success_count += 1
        else:
            error_count += 1
        log_entry = {"timestamp":datetime.now(),"patient":row['NOMBRE_PACIENTE'],
                     "phone":phone,"type":"Cambio de Cita","method":"WhatsApp",
                     "message":message,"status":"Enviado" if success else "Error"}
        if not success:
            log_entry["error"] = result
        save_log(log_entry)
        time.sleep(1)

    st.success(f"📊 Resultados: ✅ {success_count} / ❌ {error_count}")
    st.session_state.df = df

# Ejecutar automático al cargar Excel
if uploaded_file and mode=="Automático":
    if 'auto_sent' not in st.session_state:
        st.session_state.auto_sent = True
        threading.Thread(target=lambda: process_notifications(df)).start()

# Ejecutar manual
if mode=="Manual" and manual_btn:
    process_notifications(df)

# Mostrar tabla y descargar
if not df.empty:
    st.header("📋 Vista Previa de Citas")
    st.dataframe(df,use_container_width=True)

    if show_logs or 'show_logs' in st.session_state:
        st.header("📋 Registro de Notificaciones")
        log_file = "notification_log.json"
        if os.path.exists(log_file):
            with open(log_file,"r") as f:
                logs = json.load(f)
            if logs:
                st.dataframe(pd.DataFrame(logs),use_container_width=True)

    # Descargar Excel actualizado
    if 'df' in st.session_state:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            st.session_state.df.to_excel(writer,index=False)
        st.download_button("💾 Descargar Datos Actualizados",data=output.getvalue(),
                           file_name="citas_actualizadas.xlsx",mime="application/vnd.ms-excel")
else:
    st.info("👆 Por favor, sube un archivo Excel para comenzar")

from PIL import Image

@st.cache_resource
def load_logo(path):
    return Image.open(path)
# Pie de página
st.markdown("---")
st.markdown('<div style="text-align:center;color:#666;"><p>Desarrollado para análisis y gestión de datos médicos</p></div>',unsafe_allow_html=True)
with st.container():
        col1, col2, col3, col4 = st.columns([3,1,5,1])
        with col2:
            logo = load_logo("logo_alain.png")
            st.image(logo, width=150)
        with col3:
            st.markdown("""
                <div style='text-align: left; color: #888888; font-size: 20px; padding-bottom: 20px;'>
                    💼 Aplicación desarrollada por <strong>Alain Antinao Sepúlveda</strong> <br>
                    📧 Contacto: <a href="mailto:alain.antinao.s@gmail.com" style="color: #4A90E2;">alain.antinao.s@gmail.com</a> <br>
                    🌐 Más información en: <a href="https://alain-antinao-s.notion.site/Alain-C-sar-Antinao-Sep-lveda-1d20a081d9a980ca9d43e283a278053e" target="_blank" style="color: #4A90E2;">Mi página personal</a>
                </div>
            """, unsafe_allow_html=True)