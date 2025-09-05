import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import io
import json
import os
import time
import threading
import requests
from urllib.parse import quote
import base64

# Configuración de página
st.set_page_config(
    page_title="Sistema de Notificaciones Médicas",
    page_icon="🏥",
    layout="wide"
)

# Detect environment and available messaging methods
def detect_environment():
    """Detect the current environment and available messaging capabilities"""
    env_info = {
        'is_cloud': any([
            'STREAMLIT_SERVER_PORT' in os.environ,
            'STREAMLIT_BROWSER_GATHER_USAGE_STATS' in os.environ,
            os.environ.get('DISPLAY') == '',
            'DISPLAY' not in os.environ
        ]),
        'selenium_available': False,
        'api_available': False
    }
    
    # Check for Selenium
    if not env_info['is_cloud']:
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            env_info['selenium_available'] = True
        except ImportError:
            pass
    
    # API methods are always available
    env_info['api_available'] = True
    
    return env_info

# Initialize environment
ENV_INFO = detect_environment()

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
    max-height: 200px;
    overflow-y: auto;
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
.method-card {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
    background-color: #f9f9f9;
}
.method-available {
    border-left: 4px solid #28a745;
}
.method-unavailable {
    border-left: 4px solid #dc3545;
}
</style>
""", unsafe_allow_html=True)

# WhatsApp Selenium Class
class WhatsAppSelenium:
    def __init__(self):
        self.driver = None
        self.is_logged_in = False
    
    def setup_driver(self):
        """Setup Chrome driver for WhatsApp Web"""
        if ENV_INFO['is_cloud']:
            return False, "Selenium no disponible en entorno cloud"
        
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            options = Options()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            
            # Optional: run in headless mode (uncomment next line)
            # options.add_argument('--headless')
            
            self.driver = webdriver.Chrome(options=options)
            return True, "Driver configurado exitosamente"
        except Exception as e:
            return False, f"Error configurando driver: {str(e)}"
    
    def login_whatsapp(self):
        """Navigate to WhatsApp Web and wait for QR scan"""
        if not self.driver:
            return False, "Driver no inicializado"
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            self.driver.get("https://web.whatsapp.com")
            
            # Wait for QR code or main interface
            wait = WebDriverWait(self.driver, 60)
            
            # Check if already logged in or need to scan QR
            try:
                # Wait for either QR code or chat list
                wait.until(
                    lambda driver: driver.find_element(By.CSS_SELECTOR, '[data-testid="qr-code"]') or 
                                 driver.find_element(By.CSS_SELECTOR, '[data-testid="chat-list"]')
                )
                
                # Check if we're in the main interface
                if self.driver.find_elements(By.CSS_SELECTOR, '[data-testid="chat-list"]'):
                    self.is_logged_in = True
                    return True, "Ya conectado a WhatsApp Web"
                else:
                    return False, "Necesita escanear código QR en WhatsApp Web"
                    
            except Exception as e:
                return False, f"Error esperando login: {str(e)}"
                
        except Exception as e:
            return False, f"Error accediendo a WhatsApp Web: {str(e)}"
    
    def send_message(self, phone, message):
        """Send message via WhatsApp Web"""
        if not self.driver or not self.is_logged_in:
            return False, "WhatsApp Web no está conectado"
        
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            
            # Format phone number
            if not phone.startswith("+"):
                phone = "+56" + str(phone)
            
            # Navigate to chat
            url = f"https://web.whatsapp.com/send?phone={phone.replace('+', '')}"
            self.driver.get(url)
            
            wait = WebDriverWait(self.driver, 30)
            
            # Wait for message input box
            message_box = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="message-composer"] [contenteditable="true"]'))
            )
            
            # Clear and send message
            message_box.clear()
            message_box.send_keys(message)
            
            # Find and click send button
            send_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-testid="send"]'))
            )
            send_button.click()
            
            time.sleep(2)  # Wait for message to send
            return True, "Mensaje enviado via Selenium"
            
        except Exception as e:
            return False, f"Error enviando mensaje: {str(e)}"
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_logged_in = False

# WhatsApp API alternatives (for cloud environments)
class WhatsAppAPI:
    @staticmethod
    def send_via_api_link(phone, message):
        """Generate WhatsApp API link for manual sending"""
        if not phone.startswith("+"):
            phone = "+56" + str(phone)
        
        encoded_message = quote(message)
        phone_clean = phone.replace("+", "")
        
        whatsapp_url = f"https://api.whatsapp.com/send?phone={phone_clean}&text={encoded_message}"
        
        return True, f"Link generado: {whatsapp_url}"
    
    @staticmethod
    def send_via_webhook(phone, message, webhook_url=None):
        """Send via external webhook service (placeholder for custom implementation)"""
        if not webhook_url:
            return False, "Webhook URL no configurada"
        
        try:
            payload = {
                "phone": phone,
                "message": message,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code == 200:
                return True, "Mensaje enviado via webhook"
            else:
                return False, f"Error webhook: {response.status_code}"
        except Exception as e:
            return False, f"Error webhook: {str(e)}"

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

# Main sending function with multiple methods
def send_whatsapp_message(phone, message, method="auto"):
    """Send WhatsApp message using available method"""
    
    if method == "selenium" and ENV_INFO['selenium_available']:
        if 'whatsapp_selenium' not in st.session_state:
            st.session_state.whatsapp_selenium = WhatsAppSelenium()
        
        selenium_client = st.session_state.whatsapp_selenium
        if not selenium_client.driver:
            success, msg = selenium_client.setup_driver()
            if not success:
                return False, msg
            success, msg = selenium_client.login_whatsapp()
            if not success:
                return False, msg
        
        return selenium_client.send_message(phone, message)
    
    elif method == "api_link":
        return WhatsAppAPI.send_via_api_link(phone, message)
    
    elif method == "webhook":
        webhook_url = st.session_state.get('webhook_url', None)
        return WhatsAppAPI.send_via_webhook(phone, message, webhook_url)
    
    else:
        # Auto mode - use best available method
        if ENV_INFO['selenium_available'] and not ENV_INFO['is_cloud']:
            return send_whatsapp_message(phone, message, "selenium")
        else:
            return send_whatsapp_message(phone, message, "api_link")

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

# Environment Status
st.header("🔧 Estado del Sistema")
col1, col2, col3 = st.columns(3)

with col1:
    if ENV_INFO['is_cloud']:
        st.markdown('<div class="method-card method-unavailable">🌐 <strong>Entorno:</strong> Cloud/Servidor<br>📱 <strong>WhatsApp:</strong> Via API Links</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="method-card method-available">💻 <strong>Entorno:</strong> Local<br>📱 <strong>WhatsApp:</strong> Selenium disponible</div>', unsafe_allow_html=True)

with col2:
    if ENV_INFO['selenium_available']:
        st.markdown('<div class="method-card method-available">🤖 <strong>Selenium:</strong> Disponible<br>🔗 <strong>Método:</strong> WhatsApp Web directo</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="method-card method-unavailable">🤖 <strong>Selenium:</strong> No disponible<br>🔗 <strong>Método:</strong> Links de API</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="method-card method-available">🔗 <strong>API Links:</strong> Siempre disponible<br>📤 <strong>Método:</strong> Enlaces manuales</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # Method selection
    if ENV_INFO['selenium_available'] and not ENV_INFO['is_cloud']:
        send_method = st.selectbox(
            "Método de envío:",
            ["auto", "selenium", "api_link"],
            format_func=lambda x: {
                "auto": "🔄 Automático (mejor disponible)",
                "selenium": "🤖 Selenium (WhatsApp Web)",
                "api_link": "🔗 API Links (manual)"
            }[x]
        )
    else:
        send_method = "api_link"
        st.info("🔗 Método: API Links (único disponible)")
    
    # Webhook configuration (optional)
    if st.checkbox("Configurar Webhook personalizado"):
        webhook_url = st.text_input("URL del Webhook:", placeholder="https://tu-webhook.com/whatsapp")
        if webhook_url:
            st.session_state.webhook_url = webhook_url
            send_method = "webhook"
    
    mode = st.radio("Modo de ejecución:", ("Manual", "Automático"))
    
    # Selenium controls
    if ENV_INFO['selenium_available'] and send_method in ["auto", "selenium"]:
        st.header("🤖 Control de Selenium")
        if st.button("🔄 Reiniciar WhatsApp Web"):
            if 'whatsapp_selenium' in st.session_state:
                st.session_state.whatsapp_selenium.close()
                del st.session_state.whatsapp_selenium
            st.success("Selenium reiniciado")
        
        if st.button("❌ Cerrar navegador"):
            if 'whatsapp_selenium' in st.session_state:
                st.session_state.whatsapp_selenium.close()
                del st.session_state.whatsapp_selenium
                st.success("Navegador cerrado")
    
    st.header("📊 Registro")
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

# Función principal
def process_notifications(df, method="auto"):
    if df.empty:
        st.error("No hay datos para procesar")
        return
    
    success_count = 0
    error_count = 0
    links_generated = []
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
    
    st.info(f"📤 Procesando {total_to_process} notificaciones usando método: **{method}**")
    processed = 0
    
    # Procesar recordatorios
    for idx, row in to_notify.iterrows():
        status_text.text(f"Enviando recordatorio a {row['NOMBRE_PACIENTE']}...")
        message = create_reminder_message(row)
        phone = row['TELEFONO']
        
        # Mostrar preview del mensaje
        with st.expander(f"📱 Mensaje para {row['NOMBRE_PACIENTE']}", expanded=False):
            st.markdown(f'<div class="message-preview">{message}</div>', unsafe_allow_html=True)
        
        success, result = send_whatsapp_message(phone, message, method)
        
        if success:
            df.at[idx, '¿NOTIFICADO?'] = True
            df.at[idx, 'FECHA_NOTIFICACION'] = datetime.now().date()
            df.at[idx, 'HORA_NOTIFICACION'] = datetime.now().strftime("%H:%M:%S")
            df.at[idx, 'METODO_NOTIFICACION'] = method
            success_count += 1
            st.markdown(f'<div class="success-message">✅ {row["NOMBRE_PACIENTE"]}: {result}</div>', unsafe_allow_html=True)
            
            if "Link generado:" in result:
                links_generated.append({
                    'patient': row['NOMBRE_PACIENTE'],
                    'phone': phone,
                    'link': result.replace("Link generado: ", "")
                })
        else:
            error_count += 1
            st.markdown(f'<div class="error-message">❌ Error enviando a {row["NOMBRE_PACIENTE"]}: {result}</div>', unsafe_allow_html=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "patient": row['NOMBRE_PACIENTE'],
            "phone": phone,
            "type": "Recordatorio",
            "method": method,
            "message": message,
            "status": "Enviado" if success else "Error",
            "result": result
        }
        save_log(log_entry)
        
        processed += 1
        progress_bar.progress(processed / total_to_process)
        time.sleep(0.5)
    
    # Procesar cambios de cita
    for idx, row in changed_appointments.iterrows():
        status_text.text(f"Enviando cambio de cita a {row['NOMBRE_PACIENTE']}...")
        message = create_change_message(row)
        phone = row['TELEFONO']
        
        with st.expander(f"📱 Cambio de cita para {row['NOMBRE_PACIENTE']}", expanded=False):
            st.markdown(f'<div class="message-preview">{message}</div>', unsafe_allow_html=True)
        
        success, result = send_whatsapp_message(phone, message, method)
        
        if success:
            df.at[idx, 'FECHA_NOTIFICACION'] = datetime.now().date()
            df.at[idx, 'HORA_NOTIFICACION'] = datetime.now().strftime("%H:%M:%S")
            df.at[idx, 'METODO_NOTIFICACION'] = method
            df.at[idx, '¿CAMBIO DE HORA?'] = False
            success_count += 1
            st.markdown(f'<div class="success-message">✅ {row["NOMBRE_PACIENTE"]}: {result}</div>', unsafe_allow_html=True)
            
            if "Link generado:" in result:
                links_generated.append({
                    'patient': row['NOMBRE_PACIENTE'],
                    'phone': phone,
                    'link': result.replace("Link generado: ", "")
                })
        else:
            error_count += 1
            st.markdown(f'<div class="error-message">❌ Error enviando cambio a {row["NOMBRE_PACIENTE"]}: {result}</div>', unsafe_allow_html=True)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "patient": row['NOMBRE_PACIENTE'],
            "phone": phone,
            "type": "Cambio de Cita",
            "method": method,
            "message": message,
            "status": "Enviado" if success else "Error",
            "result": result
        }
        save_log(log_entry)
        
        processed += 1
        progress_bar.progress(processed / total_to_process)
        time.sleep(0.5)
    
    progress_bar.progress(1.0)
    status_text.text("✅ Proceso completado")
    
    st.success(f"📊 **Resultados del proceso:**\n- ✅ Exitosos: {success_count}\n- ❌ Errores: {error_count}")
    
    # Show generated links if any
    if links_generated:
        st.header("🔗 Enlaces de WhatsApp Generados")
        st.info("Haga clic en los enlaces para abrir WhatsApp con el mensaje pre-cargado:")
        
        for link_info in links_generated:
            st.markdown(f"**{link_info['patient']}** ({link_info['phone']}): [Abrir WhatsApp]({link_info['link']})")
    
    st.session_state.df = df

# Ejecutar notificaciones
if uploaded_file and not df.empty:
    if mode == "Manual":
        if st.button("🚀 Ejecutar Notificaciones", type="primary"):
            process_notifications(df, send_method)
    
    elif mode == "Automático":
        if 'auto_executed' not in st.session_state:
            st.info("🔄 Modo automático activado. Ejecutando notificaciones...")
            st.session_state.auto_executed = True
            process_notifications(df, send_method)

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
st.markdown('<div style="text-align:center;color:#666;"><p>Sistema de Notificaciones Médicas - Desarrollado para análisis y gestión de datos médicos</p></div>', unsafe_allow_html=True)

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

# Cleanup on app close
import atexit

def cleanup():
    """Clean up selenium driver on app close"""
    if 'whatsapp_selenium' in st.session_state:
        st.session_state.whatsapp_selenium.close()

atexit.register(cleanup)