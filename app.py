import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import io

st.set_page_config(page_title="TruckLoad Ultra Optimizer", layout="wide")

# --- LÓGICA DE OPTIMIZACIÓN (GUILLOTINE BEST-FIT) ---
def optimizar_carga_total(ancho_c, largo_c, items):
    # Ordenar por área para meter lo más difícil primero
    items.sort(key=lambda x: x['w'] * x['h'], reverse=True)
    
    cargados = []
    sobrantes = []
    # Lista de rectángulos vacíos disponibles
    espacios_libres = [{'x': 0, 'y': 0, 'w': ancho_c, 'h': largo_c}]

    for item in items:
        mejor_espacio_idx = -1
        mejor_orientacion = None # (w, h)
        min_desperdicio = float('inf')

        # Buscar el mejor lugar entre todos los huecos disponibles
        for i, espacio in enumerate(espacios_libres):
            for w_p, h_p in [(item['w'], item['h']), (item['h'], item['w'])]:
                if w_p <= espacio['w'] and h_p <= espacio['h']:
                    desperdicio = (espacio['w'] * espacio['h']) - (w_p * h_p)
                    if desperdicio < min_desperdicio:
                        min_desperdicio = desperdicio
                        mejor_espacio_idx = i
                        mejor_orientacion = (w_p, h_p)

        if mejor_espacio_idx != -1:
            espacio = espacios_libres.pop(mejor_espacio_idx)
            w_final, h_final = mejor_orientacion
            
            # Ubicar bulto
            cargados.append({
                'x': espacio['x'], 'y': espacio['y'],
                'w': w_final, 'h': h_final,
                'n': item['nombre'], 'c': item['color']
            })

            # Dividir el espacio sobrante en dos nuevos rectángulos (Guillotina)
            # Decidimos dividir por el lado que deje el rectángulo más grande útil
            if (espacio['w'] - w_final) > (espacio['h'] - h_final):
                # Dividir verticalmente
                if espacio['w'] - w_final > 0:
                    espacios_libres.append({'x': espacio['x'] + w_final, 'y': espacio['y'], 'w': espacio['w'] - w_final, 'h': h_final})
                if espacio['h'] - h_final > 0:
                    espacios_libres.append({'x': espacio['x'], 'y': espacio['y'] + h_final, 'w': espacio['w'], 'h': espacio['h'] - h_final})
            else:
                # Dividir horizontalmente
                if espacio['h'] - h_final > 0:
                    espacios_libres.append({'x': espacio['x'], 'y': espacio['y'] + h_final, 'w': w_final, 'h': espacio['h'] - h_final})
                if espacio['w'] - w_final > 0:
                    espacios_libres.append({'x': espacio['x'] + w_final, 'y': espacio['y'], 'w': espacio['w'] - w_final, 'h': espacio['h']})
        else:
            sobrantes.append(item)
            
    return cargados, sobrantes

# --- INTERFAZ ---
if 'productos_db' not in st.session_state: st.session_state.productos_db = {}
if 'historial_db' not in st.session_state: st.session_state.historial_db = []

st.title("🚛 TruckLoad Ultra Optimizer")

tab1, tab2 = st.tabs(["🚀 Nuevo Plan", "📜 Historial"])

with tab1:
    col_config, col_main = st.columns([1, 2])
    
    with col_config:
        st.subheader("1. Información del Plan")
        nombre_plan = st.text_input("Nombre del Cliente / Pedido")
        fecha_str = datetime.now().strftime("%d/%m/%Y")
        
        st.divider()
        st.subheader("2. El Vehículo")
        ancho_t = st.number_input("Ancho Camión (cm)", min_value=1, value=240)
        largo_t = st.number_input("Largo Camión (cm)", min_value=1, value=1200)

        st.divider()
        st.subheader("3. Carga")
        with st.expander("Añadir nuevo modelo"):
            with st.form("new_product", clear_on_submit=True):
                n = st.text_input("Nombre")
                a = st.number_input("Ancho (cm)", min_value=1, value=70)
                p = st.number_input("Profundidad (cm)", min_value=1, value=80)
                c = st.color_picker("Color", "#3498db")
                if st.form_submit_button("Guardar"):
                    if n: st.session_state.productos_db[n] = {'w': a, 'h': p, 'c': c}
                    st.rerun()

        lista_final = []
        for nombre, datos in st.session_state.productos_db.items():
            cant = st.number_input(f"Cant. {nombre}", min_value=0, key=f"q_{nombre}")
            for _ in range(cant):
                lista_final.append({'nombre': nombre, 'w': datos['w'], 'h': datos['h'], 'color': datos['c']})

    with col_main:
        if st.button("GENERAR PLAN OPTIMIZADO", type="primary", use_container_width=True):
            if not nombre_plan:
                st.error("❌ ERROR: El nombre del plan es obligatorio.")
            elif not lista_final:
                st.warning("⚠️ No hay productos seleccionados.")
            else:
                cargados, sobrantes = optimizar_carga_total(ancho_t, largo_t, lista_final)
                
                # Gráfico
                fig, ax = plt.subplots(figsize=(10, 8))
                ax.add_patch(patches.Rectangle((0,0), ancho_t, largo_t, color="#f8f9fa", ec="black", lw=2))
                plt.title(f"Plan: {nombre_plan} | Fecha: {fecha_str}", fontsize=14, pad=15)
                
                for b in cargados:
                    ax.add_patch(patches.Rectangle((b['x'], b['y']), b['w'], b['h'], fc=b['c'], ec="white", lw=0.5))
                    ax.text(b['x']+b['w']/2, b['y']+b['h']/2, b['n'], ha='center', va='center', fontsize=6, rotation=90, color="white", weight='bold')

                plt.xlim(-50, ancho_t+50); plt.ylim(-50, largo_t+100); ax.set_aspect('equal'); plt.axis('off')
                st.pyplot(fig)
                
                # Eficiencia
                area_u = sum(b['w']*b['h'] for b in cargados)
                eficiencia = (area_u / (ancho_t * largo_t)) * 100
                st.metric("Aprovechamiento de Piso", f"{eficiencia:.1f}%")

                if sobrantes:
                    st.error(f"⚠️ NO ENTRARON: {len(sobrantes)} bultos.")
                    st.write(pd.DataFrame(sobrantes)['nombre'].value_counts())
                
                # Guardar Historial
                st.session_state.historial_db.append({"Fecha": fecha_str, "Plan": nombre_plan, "Eficiencia": f"{eficiencia:.1f}%"})

with tab2:
    if st.session_state.historial_db:
        st.table(pd.DataFrame(st.session_state.historial_db))
    else:
        st.info("Historial vacío.")
