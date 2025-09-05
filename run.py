import subprocess
import os

def run_streamlit():
    #Obtiene la ruta del script de streamllit
    script_path = os.path.join(os.path.dirname(__file__), 'autom_msj.py')
    
    # Ejecuta el comando para iniciar Streamlit
    subprocess.run(['streamlit', 'run', script_path])

if __name__ == "__main__":
    run_streamlit()