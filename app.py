import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
from datetime import datetime
import io

# Configuración de página
st.set_page_config(page_title="TruckLoad Master Pro", layout="wide")

# --- MOTOR DE OPTIMIZACIÓN DE ALTA DENSIDAD ---
def optimizar_carga_maxima(ancho_c, largo_c, items):
    # Ordenar de mayor a menor área para colocar primero lo más difícil
    items.sort(key=lambda x: x['w'] * x['h'], reverse=True)
    
    cargados = []
    sobrantes = []
    # Lista de rectángulos vacíos (empezamos con el camión completo)
    espacios_libres = [{'x': 0, 'y': 0, 'w': ancho_c, 'h': largo_c}]

    for item in items:
        mejor_idx = -1
        mejor_orientacion = None
        min_sobrante_area = float('inf')

        # Buscar en TODOS los huecos disponibles el "Mejor Ajuste de Área"
        for i, espacio in enumerate(espacios_libres):
            for w_p, h_p in [(item['w'], item['h']), (item['h'], item['w'])]:
                if w_p <= espacio['w'] and h_p <= espacio['h']:
                    sobrante_area = (espacio['w'] * espacio['h']) - (w_p * h_p)
                    # Priorizamos el hueco donde entre más "justo"
                    if sobrante_area < min_sobrante_area:
                        min_sobrante_area = sobrante_area
                        mejor_idx = i
                        mejor_orientacion = (w_p, h_p)

        if mejor_idx != -1:
            espacio = espacios_libres.pop(mejor_idx)
            w_f, h_f = mejor_orientacion
            
            cargados.append({
                'x': espacio['x'], 'y': espacio['y'],
                'w': w_f, 'h': h_f,
                'n': item['nombre'], 'c': item['color']
            })

            # Partición de espacio (Guillotina Inteligente)
            # Dividimos el espacio sobrante de forma que maximice el área de los nuevos huecos
            if (espacio['w'] - w_f) > (espacio['h'] - h_f):
                # Dividir a la derecha primero
                if espacio['w'] - w_f > 0:
                    espacios_libres.append({'x': espacio['x'] + w_f, 'y': espacio['y'], 'w': espacio['w'] - w_f, 'h': espacio['h']})
                if espacio['h'] - h_f > 0:
                    espacios_libres.append({'x': espacio['x'], 'y': espacio['y'] + h_f, 'w': w_f, 'h': espacio['h'] - h_f})
            else:
                # Dividir arriba primero
                if espacio['h'] - h_f > 0:
                    espacios_libres.append({'x': espacio['x'], 'y': espacio['y'] + h_f, 'w': espacio['w'], 'h': espacio['h'] - h_f})
                if espacio['w'] - w_f > 0:
                    espacios_libres.append({'x': espacio['x'] + w_f, 'y': espacio['y'], 'w': espacio['w'] - w_f, 'h': h_f})
            
            # Re-ordenar espacios para priorizar los que están más cerca del fondo (y más bajo)
            espacios_libres.sort(key=lambda e: (e['y'], e['x']))
        else:
            sobrantes.append(item)
            
    return cargados, sobrantes

# --- INTERFAZ MULTI-USUARIO (SIMPLIFICADA) ---
if 'usuarios' not in st.session_state: st.session_state.usuarios = {}
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.title("🔐 Acceso al Sistema")
    u = st.text_input("Usuario")
    p = st.text_input("Contraseña", type="password")
    col1, col2 = st.columns(2)
    if col1.button("Ingresar"):
        if u in st.session_state.usuarios and st.session_state.usuarios[u]['p'] == p:
            st.session_state.user = u
            st.rerun()
        else: st.error("Error de acceso")
    if col2.button("Registrarse"):
        if u and p:
            st.session_state.usuarios[u] = {'p': p, 'prod': {}, 'hist': []}
            st.success("Registrado. Iniciá sesión.")
    st.stop()

# --- APP PRINCIPAL ---
u_data = st.session_state.usuarios[st.session_state.user]
st.sidebar.title(f"Bienvenido, {st.session_state.user}")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

st.title("🚛 TruckLoad Master Pro")

t1, t2 = st.tabs(["🚀 Generar Carga", "📜 Historial"])

with t1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Datos del Plan")
        nombre_plan = st.text_input("Nombre del Cliente (OBLIGATORIO)")
        fecha_plan = datetime.now().strftime("%d/%m/%Y")
        
        anch_c = st.number_input("Ancho Camión (cm)", min_value=1, value=240)
        larg_c = st.number_input("Largo Camión (cm)", min_value=1, value=1200)

        st.divider()
        with st.expander("Gestionar Inventario"):
            with st.form("new"):
                n = st.text_input("Nombre Modelo")
                a = st.number_input("Ancho (cm)", min_value=1, value=60)
                pr = st.number_input("Profundidad (cm)", min_value=1, value=60)
                cl = st.color_picker("Color", "#3498db")
                if st.form_submit_button("Añadir") and n:
                    u_data['prod'][n] = {'w': a, 'h': pr, 'c': cl}
                    st.rerun()
            if st.button("Limpiar Todo el Inventario"):
                u_data['prod'] = {}
                st.rerun()

        carga_final = []
        for n, d in u_data['prod'].items():
            cant = st.number_input(f"Cant. {n}", min_value=0, key=f"q_{n}")
            for _ in range(cant): carga_final.append({'nombre': n, 'w': d['w'], 'h': d['h'], 'color': d['c']})

    with c2:
        if st.button("CALCULAR CARGA ÓPTIMA", type="primary", use_container_width=True):
            if not nombre_plan:
                st.error("⚠️ Debes asignar un NOMBRE al plan.")
            elif not carga_final:
                st.warning("⚠️ Selecciona productos para cargar.")
            else:
                cargados, sobrantes = optimizar_carga_maxima(anch_c, larg_c, carga_final)
                
                fig, ax = plt.subplots(figsize=(10, 8))
                ax.add_patch(patches.Rectangle((0,0), anch_c, larg_c, color="#f0f2f6", ec="black", lw=2))
                plt.title(f"PLAN: {nombre_plan.upper()}\nFECHA: {fecha_plan}", fontsize=14, fontweight='bold', pad=20)
                
                for b in cargados:
                    ax.add_patch(patches.Rectangle((b['x'], b['y']), b['w'], b['h'], fc=b['c'], ec="white", lw=0.5))
                    ax.text(b['x']+b['w']/2, b['y']+b['h']/2, b['n'], ha='center', va='center', fontsize=5, rotation=90, color="white", weight='bold')

                plt.xlim(-50, anch_c+50); plt.ylim(-50, larg_c+100); ax.set_aspect('equal'); plt.axis('off')
                st.pyplot(fig)
                
                area_u = sum(b['w']*b['h'] for b in cargados)
                eficiencia = (area_u / (anch_c * larg_c)) * 100
                st.metric("Aprovechamiento de Piso", f"{eficiencia:.1f}%")
                
                if sobrantes:
                    st.error(f"❌ No entraron {len(sobrantes)} bultos.")
                    st.write(pd.DataFrame(sobrantes)['nombre'].value_counts())
                
                u_data['hist'].append({"Fecha": fecha_plan, "Cliente": nombre_plan, "Bultos": len(cargados), "Ef": f"{eficiencia:.1f}%"})

with t2:
    if u_data['hist']: st.table(pd.DataFrame(u_data['hist']))
    else: st.info("Historial vacío")
