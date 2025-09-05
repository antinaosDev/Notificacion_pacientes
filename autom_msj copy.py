import pandas as pd import numpy as np from datetime import datetime, timedelta import pywhatkit import clicksend_client from clicksend_client import SmsMessage from clicksend_client.rest import ApiException import io import os import json import time import threading # Configuración de la página st.set_page_config( page_title="Sistema de Notificaciones Médicas", page_icon="🏥", layout="wide" ) # Estilos CSS personalizados st.markdown(""" <style> :root { --primary-color: #1E88E5; --secondary-color: #43A047; --background-color: #F5F5F5; --text-color: #333333; } .header {background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%); padding: 2rem; border-radius: 10px; margin-bottom: 2rem; color: white; text-align: center;} .logo-container {display: flex; justify-content: center; align-items: center; gap: 1rem; margin-bottom: 1rem;} .logo {font-size: 3rem; font-weight: bold;} .stButton>button {background-color: var(--primary-color); color: white; border: none; border-radius: 5px; padding: 0.5rem 1rem;} .stButton>button:hover {background-color: #0D47A1;} </style> """, unsafe_allow_html=True) # Función para cargar datos desde archivo @st.cache_data def load_data(file): if file is not None: df = pd.read_excel(file, dtype={'TELEFONO': str}) required_columns = [ 'RUT', 'NOMBRE_PACIENTE', 'TELEFONO', 'FECHA_ATENCION', 'MOTIVO_CONSULTA', 'PROFESIONAL', '¿NOTIFICADO?', '¿CAMBIO DE HORA?', 'NUEVA_FECHA', 'PROFESIONAL_REASIGNADO' ] for col in required_columns: if col not in df.columns: df[col] = None if 'FECHA_NOTIFICACION' not in df.columns: df['FECHA_NOTIFICACION'] = None if 'METODO_NOTIFICACION' not in df.columns: df['METODO_NOTIFICACION'] = None # Convertir fechas a datetime df['FECHA_ATENCION'] = pd.to_datetime(df['FECHA_ATENCION'], errors='coerce') df['NUEVA_FECHA'] = pd.to_datetime(df['NUEVA_FECHA'], errors='coerce') return df return pd.DataFrame() # Función para guardar logs def save_log(log_data): log_file = "notification_log.json" if os.path.exists(log_file): with open(log_file, "r") as f: logs = json.load(f) else: logs = [] logs.append(log_data) with open(log_file, "w") as f: json.dump(logs, f, indent=2, default=str) # Funciones de envío def send_whatsapp(phone, message): try: phone = str(phone) if not phone.startswith("+"): phone = "+56" + phone pywhatkit.sendwhatmsg_instantly(phone, message, tab_close=True, wait_time=10) return True, "Mensaje enviado por WhatsApp" except Exception as e: return False, f"Error WhatsApp: {str(e)}" def send_sms(phone, message, username, api_key): try: if not username or not api_key: return False, "❌ Credenciales SMS no configuradas" phone = str(phone).strip() # Normalizar número (si no tiene +, agregamos) if not phone.startswith("+"): if phone.startswith("56"): phone = "+" + phone else: phone = "+56" + phone # Configuración ClickSend configuration = clicksend_client.Configuration() configuration.username = username configuration.password = api_key api_instance = clicksend_client.SMSApi(clicksend_client.ApiClient(configuration)) sms_message = SmsMessage(source="StreamlitApp", body=message, to=phone) sms_messages = clicksend_client.SmsMessageCollection(messages=[sms_message]) response = api_instance.sms_send_post(sms_messages) # Devolver detalle de la respuesta return True, f"✅ SMS enviado: {response}" except ApiException as e: return False, f"❌ Error API SMS: {e.body}" except Exception as e: return False, f"⚠️ Error inesperado SMS: {str(e)}" # Funciones de mensajes def create_reminder_message(row): fecha_cita = row['FECHA_ATENCION'].strftime('%d/%m/%Y') if pd.notnull(row['FECHA_ATENCION']) else "sin fecha" return f""" 🏥 CESFAM Cholchol - Recordatorio de Cita 🏥 Hola {row['NOMBRE_PACIENTE']}, Le recordamos que tiene programada una cita médica: 📅 Fecha: {fecha_cita} 👨‍⚕️ Profesional: {row['PROFESIONAL']} 📋 Motivo: {row['MOTIVO_CONSULTA']} 📍 Lugar: Centro de Salud Familiar CESFAM Cholchol Calle Anibal Pinto 552, Cholchol 📋 Recomendaciones: - Llegar 15 minutos antes de su hora de cita - Traer su cédula de identidad y carnet de salud - Si no puede asistir, notificar con anticipación Para confirmar, reagendar o consultar: 📧 Email: cholcholsome@gmail.com *Este es un mensaje automático, por favor no responder.* Atentamente, Equipo de Salud CESFAM Cholchol """ def create_change_message(row): nueva_fecha = row['NUEVA_FECHA'].strftime('%d/%m/%Y') if pd.notnull(row['NUEVA_FECHA']) else "sin fecha" profesional = row['PROFESIONAL_REASIGNADO'] if pd.notnull(row['PROFESIONAL_REASIGNADO']) else row['PROFESIONAL'] return f""" Hola {row['NOMBRE_PACIENTE']}, Le informamos que su cita médica ha sido reprogramada. 📅 NUEVA FECHA: {nueva_fecha} 👨‍⚕️ PROFESIONAL: {profesional} 🏥 CENTRO MÉDICO: CESFAM Cholchol 📍 DIRECCIÓN: Calle Anibal Pinto 552, Cholchol **Importante:** - Llegue 15 minutos antes de su hora de cita - Traer su cédula de identidad y carnet de salud - En caso de no poder asistir, favor avisar con anticipación Para consultas o reagendamientos: 📧 Email: cholcholsome@gmail.com *Este es un mensaje automático, por favor no responder.* Atentamente, Equipo de Salud CESFAM Cholchol """ # Cabecera st.markdown(""" <div class="header"> <div class="logo-container"> <div class="logo">🏥</div> <div> <h1>Sistema de Notificaciones Médicas</h1> <p>Análisis y gestión de citas médicas</p> </div> <div class="logo">📊</div> </div> </div> """, unsafe_allow_html=True) # Inicializar variables SMS sms_username = "" sms_api_key = "" # Sidebar with st.sidebar: st.header("⚙️ Configuración") st.subheader("Canales de Notificación") enable_whatsapp = st.checkbox("WhatsApp", value=True) enable_sms = st.checkbox("SMS", value=False) if enable_sms: sms_username = st.text_input("Usuario ClickSend", value="") sms_api_key = st.text_input("API Key ClickSend", type="password", value="") st.subheader("Modo de Ejecución") execution_mode = st.radio("Seleccionar modo:", ("Automático", "Manual")) if execution_mode == "Automático": run_notifications = True else: run_notifications = st.button("🚀 Ejecutar Notificaciones") show_logs = st.button("📋 Ver Registros") # Carga de archivo st.header("📂 Carga de Datos") uploaded_file = st.file_uploader("Subir archivo Excel con citas médicas", type=["xlsx", "xls"]) df = load_data(uploaded_file) def process_notifications(df, enable_whatsapp, enable_sms, sms_username, sms_api_key): whatsapp_count = 0 sms_count = 0 success_count = 0 error_count = 0 today = datetime.now().date() tomorrow = today + timedelta(days=1) reminder_appointments = df[(df['FECHA_ATENCION'].dt.date == tomorrow) & (df['¿NOTIFICADO?'] != True)] change_appointments = df[(df['¿CAMBIO DE HORA?'] == True) & (df['FECHA_NOTIFICACION'].isnull())] for idx, row in pd.concat([reminder_appointments, change_appointments]).iterrows(): if idx in reminder_appointments.index: message = create_reminder_message(row) tipo = "Recordatorio" else: message = create_change_message(row) tipo = "Cambio de Hora" phone = row['TELEFONO'] success = False method = "" if enable_whatsapp: success, result = send_whatsapp(phone, message) method = "WhatsApp" if success: whatsapp_count += 1 if enable_sms and (not success or not enable_whatsapp): success, result = send_sms(phone, message, sms_username, sms_api_key) method = "SMS" if success: sms_count += 1 if success: success_count += 1 df.at[idx, '¿NOTIFICADO?'] = True df.at[idx, 'FECHA_NOTIFICACION'] = datetime.now() df.at[idx, 'METODO_NOTIFICACION'] = method status = "Enviado" else: error_count += 1 status = "Error" log_entry = { "timestamp": datetime.now(), "patient": row['NOMBRE_PACIENTE'], "phone": phone, "type": tipo, "method": method, "message": message, "status": status } if status == "Error": log_entry["error"] = result save_log(log_entry) time.sleep(1) # evitar bloqueo st.success(f"📊 Resultados:\n- ✅ Exitosos: {success_count}\n- ❌ Errores: {error_count}\n- 📱 WhatsApp: {whatsapp_count}\n- 📨 SMS: {sms_count}") st.session_state.df = df if not df.empty: st.header("📋 Vista Previa de Citas") st.dataframe(df, width='stretch') st.header("📅 Dashboard de Citas Próximas") next_week = datetime.now().date() + timedelta(days=7) upcoming_appointments = df[(df['FECHA_ATENCION'].dt.date >= datetime.now().date()) & (df['FECHA_ATENCION'].dt.date <= next_week)] col1, col2, col3 = st.columns(3) with col1: st.metric("Total Citas", len(df)) with col2: st.metric("Citas Próximas (7 días)", len(upcoming_appointments)) with col3: st.metric("Pendientes de Notificar", len(df[df['¿NOTIFICADO?'] != True])) if run_notifications: threading.Thread(target=process_notifications, args=(df, enable_whatsapp, enable_sms, sms_username, sms_api_key)).start() # Mostrar registros if show_logs or 'show_logs' in st.session_state: st.session_state.show_logs = True st.header("📋 Registro de Notificaciones") log_file = "notification_log.json" if os.path.exists(log_file): with open(log_file, "r") as f: logs = json.load(f) if logs: st.dataframe(pd.DataFrame(logs), width='stretch') # Descargar datos actualizados if 'df' in st.session_state: output = io.BytesIO() with pd.ExcelWriter(output, engine='xlsxwriter') as writer: st.session_state.df.to_excel(writer, index=False) st.download_button(label="💾 Descargar Datos Actualizados", data=output.getvalue(), file_name="citas_actualizadas.xlsx", mime="application/vnd.ms-excel") else: st.info("👆 Por favor, sube un archivo Excel para comenzar") # Pie de página st.markdown("---") st.markdown(""" <div style="text-align: center; color: #666;"> <p>Desarrollado con ❤️ para el análisis y gestión de datos médicos</p> <p>© 2023 Sistema de Notificaciones Médicas</p> </div> """, unsafe_allow_html=True)


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