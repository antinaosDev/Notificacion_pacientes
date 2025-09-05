import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import json
import os
import time
import threading

# Check if we're in a cloud environment
try:
    import pywhatkit
    WHATSAPP_AVAILABLE = True
except ImportError:
    WHATSAPP_AVAILABLE = False
    st.warning("⚠️ WhatsApp functionality not available in cloud environment. Messages will be logged only.")

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
.message-preview {
    background-color: #f8f9fa;
    border: 1px solid #dee2e6;
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
    font-family: monospace;
    white-space: pre-wrap;
}
.success-message {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    padding: 10px;
    border-radius: 5px;
    margin: 5px 0;
}
.error-message {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
    padding: 10px;
    border-radius: 5px;
    margin: 5px 0;
}
</style>
""", unsafe_allow_html=True)

# Función cargar datos
@st.cache_data
def load_data(file):
    if file is not None:
        try:
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
        except Exception as e:
            st.error(f"Error al cargar el archivo: {str(e)}")
            return pd.DataFrame()
    return pd.DataFrame()

# Guardar logs
def save_log(log_entry):
    log_file = "notification_log.json"
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file,"r", encoding='utf-8') as f:
                logs = json.load(f)
        except:
            logs = []
    logs.append(log_entry)
    try:
        with open(log_file,"w", encoding='utf-8') as f:
            json.dump(logs, f, indent=2, default=str, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error al guardar log: {str(e)}")

# Enviar WhatsApp (modificado para cloud)
def send_whatsapp(phone, message):
    if not WHATSAPP_AVAILABLE:
        # Simular envío en ambiente cloud
        return True, "Mensaje simulado (ambiente cloud)"
    
    try:
        if not str(phone).startswith("+"):
            phone = "+56" + str(phone)
        pywhatkit.sendwhatmsg_instantly(phone, message, tab_close=True, wait_time=10)
        return True, "Mensaje enviado por WhatsApp"
    except Exception as e:
        return False, f"Error WhatsApp: {str(e)}"

# Mensajes
def create_reminder_message(row):
    fecha_cita = row['FECHA_ATENCION'].strftime("%d/%m/%Y") if pd.notnull(row['FECHA_ATENCION']) else "sin fecha"
    return f"""🏥 CESFAM Cholchol - Recordatorio de Cita 🏥

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

*Este es un mensaje automático, por favor no responder directamente.*"""

def create_change_message(row):
    nueva_fecha = row['NUEVA_FECHA'].strftime("%d/%m/%Y") if pd.notnull(row['NUEVA_FECHA']) else "sin fecha"
    profesional = row['PROFESIONAL_REASIGNADO'] if pd.notnull(row['PROFESIONAL_REASIGNADO']) else "No asignado"
    return f"""🏥 CESFAM Cholchol - Cambio de Cita 🏥

Hola {row['NOMBRE_PACIENTE']},

Su cita ha sido reprogramada:

📅 Nueva Fecha: {nueva_fecha}
👨‍⚕️ Profesional: {profesional}
📋 Motivo: {row['MOTIVO_CONSULTA']}

*Mensaje automático*"""

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

# Status del sistema
if not WHATSAPP_AVAILABLE:
    st.warning("🚨 **MODO DEMO**: La aplicación está ejecutándose en modo demostración. Los mensajes no se enviarán realmente, pero se registrarán en los logs.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    mode = st.radio("Modo de ejecución:", ("Manual", "Automático"))
    
    st.header("📊 Estado del Sistema")
    if WHATSAPP_AVAILABLE:
        st.success("✅ WhatsApp disponible")
    else:
        st.warning("⚠️ Modo demo activo")
    
    show_logs = st.button("📋 Ver Registros")
    
    if st.button("🗑️ Limpiar Logs"):
        if os.path.exists("notification_log.json"):
            os.remove("notification_log.json")
            st.success("Logs eliminados")

# Carga Excel
st.header("📂 Carga de Datos")
uploaded_file = st.file_uploader("Subir archivo Excel con citas médicas", type=["xlsx","xls"])

if uploaded_file:
    df = load_data(uploaded_file)
    
    if not df.empty:
        st.success(f"✅ Archivo cargado: {len(df)} registros encontrados")
        
        # Mostrar estadísticas básicas
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Citas", len(df))
        with col2:
            notificados = len(df[df['¿NOTIFICADO?'] == True])
            st.metric("Ya Notificados", notificados)
        with col3:
            pendientes = len(df[df['¿NOTIFICADO?'] != True])
            st.metric("Pendientes", pendientes)
        with col4:
            cambios = len(df[df['¿CAMBIO DE HORA?'] == True])
            st.metric("Con Cambios", cambios)

# Función principal mejorada
def process_notifications(df):
    if df.empty:
        st.error("No hay datos para procesar")
        return
    
    success_count = 0
    error_count = 0
    today = datetime.now().date()
    target_date = today + timedelta(days=2)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 1️⃣ Recordatorios de citas nuevas (no notificadas)
    to_notify = df[(df['¿NOTIFICADO?'] != True) & 
                   (df['FECHA_ATENCION'].dt.date >= today) &
                   (df['FECHA_ATENCION'].dt.date <= target_date)]
    
    # 2️⃣ Mensajes de reprogramación
    changed_appointments = df[(df['¿CAMBIO DE HORA?'] == True) &
                              df['NUEVA_FECHA'].notnull() &
                              df['PROFESIONAL_REASIGNADO'].notnull() &
                              (df['FECHA_ATENCION'].dt.date >= today) &
                              (df['FECHA_ATENCION'].dt.date <= target_date)]
    
    total_to_process = len(to_notify) + len(changed_appointments)
    
    if total_to_process == 0:
        st.info("📋 No hay citas que requieran notificación en este momento")
        return
    
    st.info(f"📤 Procesando {total_to_process} notificaciones...")
    processed = 0
    
    # Procesar recordatorios
    for idx, row in to_notify.iterrows():
        status_text.text(f"Enviando recordatorio a {row['NOMBRE_PACIENTE']}...")
        message = create_reminder_message(row)
        phone = row['TELEFONO']
        
        # Mostrar preview del mensaje
        with st.expander(f"📱 Mensaje para {row['NOMBRE_PACIENTE']}", expanded=False):
            st.markdown(f'<div class="message-preview">{message}</div>', unsafe_allow_html=True)
        
        success, result = send_whatsapp(phone, message)
        
        if success:
            df.at[idx, '¿NOTIFICADO?'] = True
            df.at[idx, 'FECHA_NOTIFICACION'] = datetime.now().date()
            df.at[idx, 'HORA_NOTIFICACION'] = datetime.now().strftime("%H:%M:%S")
            df.at[idx, 'METODO_NOTIFICACION'] = "WhatsApp" if WHATSAPP_AVAILABLE else "Demo"
            success_count += 1
            st.markdown(f'<div class="success-message">✅ Enviado a {row["NOMBRE_PACIENTE"]}</div>', unsafe_allow_html=True)
        else:
            error_count += 1
            st.markdown(f'<div class="error-message">❌ Error enviando a {row["NOMBRE_PACIENTE"]}: {result}</div>', unsafe_allow_html=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "patient": row['NOMBRE_PACIENTE'],
            "phone": phone,
            "type": "Recordatorio",
            "method": "WhatsApp" if WHATSAPP_AVAILABLE else "Demo",
            "message": message,
            "status": "Enviado" if success else "Error"
        }
        if not success:
            log_entry["error"] = result
        save_log(log_entry)
        
        processed += 1
        progress_bar.progress(processed / total_to_process)
        time.sleep(0.5)  # Pausa reducida para demo
    
    # Procesar cambios de cita
    for idx, row in changed_appointments.iterrows():
        status_text.text(f"Enviando cambio de cita a {row['NOMBRE_PACIENTE']}...")
        message = create_change_message(row)
        phone = row['TELEFONO']
        
        # Mostrar preview del mensaje
        with st.expander(f"📱 Cambio de cita para {row['NOMBRE_PACIENTE']}", expanded=False):
            st.markdown(f'<div class="message-preview">{message}</div>', unsafe_allow_html=True)
        
        success, result = send_whatsapp(phone, message)
        
        if success:
            df.at[idx, 'FECHA_NOTIFICACION'] = datetime.now().date()
            df.at[idx, 'HORA_NOTIFICACION'] = datetime.now().strftime("%H:%M:%S")
            df.at[idx, 'METODO_NOTIFICACION'] = "WhatsApp" if WHATSAPP_AVAILABLE else "Demo"
            df.at[idx, '¿CAMBIO DE HORA?'] = False
            success_count += 1
            st.markdown(f'<div class="success-message">✅ Cambio enviado a {row["NOMBRE_PACIENTE"]}</div>', unsafe_allow_html=True)
        else:
            error_count += 1
            st.markdown(f'<div class="error-message">❌ Error enviando cambio a {row["NOMBRE_PACIENTE"]}: {result}</div>', unsafe_allow_html=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "patient": row['NOMBRE_PACIENTE'],
            "phone": phone,
            "type": "Cambio de Cita",
            "method": "WhatsApp" if WHATSAPP_AVAILABLE else "Demo",
            "message": message,
            "status": "Enviado" if success else "Error"
        }
        if not success:
            log_entry["error"] = result
        save_log(log_entry)
        
        processed += 1
        progress_bar.progress(processed / total_to_process)
        time.sleep(0.5)
    
    progress_bar.progress(1.0)
    status_text.text("✅ Proceso completado")
    
    st.success(f"📊 **Resultados del proceso:**\n- ✅ Exitosos: {success_count}\n- ❌ Errores: {error_count}")
    st.session_state.df = df

# Ejecutar manual
if uploaded_file and not df.empty:
    if mode == "Manual":
        if st.button("🚀 Ejecutar Notificaciones", type="primary"):
            process_notifications(df)
    
    elif mode == "Automático":
        if 'auto_executed' not in st.session_state:
            st.info("🔄 Modo automático activado. Ejecutando notificaciones...")
            st.session_state.auto_executed = True
            process_notifications(df)

# Mostrar tabla y funciones adicionales
if uploaded_file and not df.empty:
    st.header("📋 Vista Previa de Citas")
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        filter_notificado = st.selectbox("Filtrar por estado:", ["Todos", "Notificados", "Pendientes"])
    with col2:
        filter_cambio = st.selectbox("Filtrar por cambios:", ["Todos", "Con cambios", "Sin cambios"])
    
    # Aplicar filtros
    filtered_df = df.copy()
    if filter_notificado == "Notificados":
        filtered_df = filtered_df[filtered_df['¿NOTIFICADO?'] == True]
    elif filter_notificado == "Pendientes":
        filtered_df = filtered_df[filtered_df['¿NOTIFICADO?'] != True]
    
    if filter_cambio == "Con cambios":
        filtered_df = filtered_df[filtered_df['¿CAMBIO DE HORA?'] == True]
    elif filter_cambio == "Sin cambios":
        filtered_df = filtered_df[filtered_df['¿CAMBIO DE HORA?'] != True]
    
    st.dataframe(filtered_df, use_container_width=True)

    # Mostrar logs si se solicitó
    if show_logs:
        st.header("📋 Registro de Notificaciones")
        log_file = "notification_log.json"
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding='utf-8') as f:
                    logs = json.load(f)
                if logs:
                    logs_df = pd.DataFrame(logs)
                    st.dataframe(logs_df, use_container_width=True)
                else:
                    st.info("No hay registros de notificaciones aún")
            except Exception as e:
                st.error(f"Error al cargar logs: {str(e)}")
        else:
            st.info("No hay archivo de logs disponible")

    # Descargar Excel actualizado
    if 'df' in st.session_state:
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                st.session_state.df.to_excel(writer, index=False, sheet_name='Citas_Actualizadas')
            
            st.download_button(
                "💾 Descargar Datos Actualizados",
                data=output.getvalue(),
                file_name=f"citas_actualizadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.ms-excel"
            )
        except Exception as e:
            st.error(f"Error al generar archivo de descarga: {str(e)}")
else:
    st.info("👆 Por favor, sube un archivo Excel para comenzar")

# Pie de página
st.markdown("---")
st.markdown('<div style="text-align:center;color:#666;"><p>Desarrollado para análisis y gestión de datos médicos</p></div>', unsafe_allow_html=True)

# Información del desarrollador
with st.container():
    col1, col2, col3, col4 = st.columns([3,1,5,1])
    with col3:
        st.markdown("""
            <div style='text-align: left; color: #888888; font-size: 18px; padding-bottom: 20px;'>
                💼 Aplicación desarrollada por <strong>Alain Antinao Sepúlveda</strong> <br>
                📧 Contacto: <a href="mailto:alain.antinao.s@gmail.com" style="color: #4A90E2;">alain.antinao.s@gmail.com</a> <br>
                🌐 Más información en: <a href="https://alain-antinao-s.notion.site/Alain-C-sar-Antinao-Sep-lveda-1d20a081d9a980ca9d43e283a278053e" target="_blank" style="color: #4A90E2;">Mi página personal</a>
            </div>
        """, unsafe_allow_html=True)