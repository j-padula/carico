import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import io

# Configuración de la App
st.set_page_config(page_title="TruckLoad Pro - Multi-Usuario", layout="wide")

# --- SISTEMA DE AUTENTICACIÓN Y BASE DE DATOS MOCK ---
# En una webapp real usaríamos una base de datos. 
# Aquí usamos la memoria de Streamlit para separar las sesiones.
if 'db_usuarios' not in st.session_state:
    st.session_state.db_usuarios = {} # {usuario: {password: x, productos: {}, historial: []}}
if 'usuario_actual' not in st.session_state:
    st.session_state.usuario_actual = None

# --- FUNCIONES DE LÓGICA ---
def calcular_layout(ancho_c, largo_c, items):
    items.sort(key=lambda x: x['w'] * x['h'], reverse=True)
    posiciones, x, y, max_h_fila = [], 0, 0, 0
    for item in items:
        w, h = item['w'], item['h']
        if x + w > ancho_c and x + h <= ancho_c: w, h = h, w
        if x + w <= ancho_c:
            if y + h <= largo_c:
                posiciones.append({'x': x, 'y': y, 'w': w, 'h': h, 'n': item['nombre'], 'c': item['color']})
                x += w
                max_h_fila = max(max_h_fila, h)
        else:
            x = 0
            y += max_h_fila
            max_h_fila = h
            if y + h <= largo_c:
                posiciones.append({'x': x, 'y': y, 'w': w, 'h': h, 'n': item['nombre'], 'c': item['color']})
                x += w
    return posiciones

# --- PANTALLA DE LOGIN / REGISTRO ---
if st.session_state.usuario_actual is None:
    st.title("🔐 Acceso al Sistema de Carga")
    menu = ["Ingresar", "Registrarse"]
    choice = st.sidebar.selectbox("Menú de Acceso", menu)

    if choice == "Registrarse":
        st.subheader("Crear nueva cuenta")
        new_user = st.text_input("Usuario")
        new_pass = st.text_input("Contraseña", type='password')
        if st.button("Crear Usuario"):
            if new_user in st.session_state.db_usuarios:
                st.error("El usuario ya existe.")
            elif new_user == "":
                st.error("El nombre no puede estar vacío.")
            else:
                st.session_state.db_usuarios[new_user] = {'pass': new_pass, 'productos': {}, 'historial': []}
                st.success("Cuenta creada. Ahora podés ingresar.")
    
    else:
        st.subheader("Iniciar Sesión")
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type='password')
        if st.button("Entrar"):
            if user in st.session_state.db_usuarios and st.session_state.db_usuarios[user]['pass'] == password:
                st.session_state.usuario_actual = user
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    st.stop() # Detiene la ejecución aquí si no está logueado

# --- SI LLEGAMOS ACÁ, EL USUARIO ESTÁ LOGUEADO ---
user_data = st.session_state.db_usuarios[st.session_state.usuario_actual]

with st.sidebar:
    st.write(f"👤 Usuario: **{st.session_state.usuario_actual}**")
    if st.button("Cerrar Sesión"):
        st.session_state.usuario_actual = None
        st.rerun()

st.title(f"🚛 Panel de Gestión - {st.session_state.usuario_actual}")

tab1, tab2 = st.tabs(["🚀 Nuevo Plan de Carga", "📜 Mis Historiales"])

with tab1:
    col_in, col_viz = st.columns([1, 2])
    
    with col_in:
        st.subheader("1. Identificación del Plan")
        # --- REQUISITO: NOMBRE DEL PLAN ---
        nombre_plan = st.text_input("Nombre del Cliente / Pedido (Obligatorio)", placeholder="Ej: Pedido Juan Pérez")
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        st.info(f"Fecha de hoy: {fecha_actual}")

        st.divider()
        st.subheader("2. Medidas del Camión")
        ancho_c = st.number_input("Ancho Camión (cm)", min_value=1, value=240)
        largo_c = st.number_input("Largo Camión (cm)", min_value=1, value=1200)
        
        st.divider()
        st.subheader("3. Mis Productos")
        with st.form("nuevo_p", clear_on_submit=True):
            nom_p = st.text_input("Nombre del Producto")
            # --- REQUISITO: SIN LÍMITE DE 70/80 ---
            an_p = st.number_input("Ancho (cm)", min_value=1, value=10)
            pr_p = st.number_input("Profundidad (cm)", min_value=1, value=10)
            cl_p = st.color_picker("Color", "#3498db")
            if st.form_submit_button("Guardar Producto") and nom_p:
                user_data['productos'][nom_p] = {'w': an_p, 'h': pr_p, 'color': cl_p}
                st.rerun()

        carga = []
        if user_data['productos']:
            st.write("**Seleccionar cantidades:**")
            for n, d in user_data['productos'].items():
                cant = st.number_input(f"{n} ({d['w']}x{d['h']})", min_value=0, key=f"c_{n}")
                for _ in range(cant): carga.append({'nombre': n, 'w': d['w'], 'h': d['h'], 'color': d['color']})
        else:
            st.warning("No tenés productos guardados todavía.")

    with col_viz:
        st.subheader("4. Resultado y Gráfico")
        if st.button("GENERAR PLAN DE CARGA", type="primary", use_container_width=True):
            # --- REQUISITO: VALIDAR NOMBRE ---
            if not nombre_plan:
                st.error("⚠️ ERROR: Debes ingresar un NOMBRE para el plan antes de continuar.")
            elif not carga:
                st.warning("⚠️ Seleccioná al menos un producto.")
            else:
                res = calcular_layout(ancho_c, largo_c, carga)
                
                # --- GRÁFICO CON NOMBRE Y FECHA ---
                fig, ax = plt.subplots(figsize=(10, 8))
                ax.add_patch(patches.Rectangle((0,0), ancho_c, largo_c, color="#f1f3f6", ec="#2c3e50", lw=2))
                
                # Título de la imagen
                plt.title(f"Plan: {nombre_plan}\nFecha: {fecha_actual}", fontsize=14, pad=20)
                
                for p in res:
                    ax.add_patch(patches.Rectangle((p['x'], p['y']), p['w'], p['h'], fc=p['c'], ec="white", lw=0.5))
                    ax.text(p['x']+p['w']/2, p['y']+p['h']/2, p['n'], ha='center', va='center', fontsize=6, rotation=90, color="white", weight='bold')
                
                plt.xlim(-50, ancho_c+50); plt.ylim(-50, largo_c+100); ax.set_aspect('equal'); plt.axis('off')
                st.pyplot(fig)
                
                # Guardar en Historial del Usuario
                user_data['historial'].append({
                    "Fecha": fecha_actual,
                    "Plan": nombre_plan,
                    "Bultos": len(res)
                })
                
                # Generar PDF
                pdf = FPDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 16)
                pdf.cell(190, 10, f"Plan: {nombre_plan}", 1, 1, 'C')
                pdf.set_font("Arial", '', 12); pdf.cell(190, 10, f"Fecha: {fecha_actual}", 0, 1, 'C')
                with io.BytesIO() as tmp:
                    fig.savefig(tmp, format='png', bbox_inches='tight'); tmp.seek(0)
                    with open("temp_p.png", "wb") as f: f.write(tmp.read())
                    pdf.image("temp_p.png", x=10, y=40, w=180)
                
                st.download_button(f"📥 Descargar PDF {nombre_plan}", pdf.output(dest='S').encode('latin-1'), f"{nombre_plan}.pdf")

with tab2:
    st.subheader(f"Historial de {st.session_state.usuario_actual}")
    if user_data['historial']:
        st.table(pd.DataFrame(user_data['historial']))
    else:
        st.info("No tenés planes guardados.")
