import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
from datetime import datetime
import io

# Configuración
st.set_page_config(page_title="TruckLoad Optimizer Ultra", layout="wide")

# --- LÓGICA DE OPTIMIZACIÓN AVANZADA ---
def optimizar_espacio_maximo(ancho_c, largo_c, lista_pedidos):
    # Ordenar por área (más grandes primero)
    lista_pedidos.sort(key=lambda x: x['w'] * x['h'], reverse=True)
    
    cargados = []
    no_cargados = []
    # Lista de espacios vacíos (empezamos con el camión completo)
    espacios_libres = [{'x': 0, 'y': 0, 'w': ancho_c, 'h': largo_c}]

    for item in lista_pedidos:
        colocado = False
        # Intentar en cada espacio libre disponible
        for i, espacio in enumerate(espacios_libres):
            w, h = item['w'], item['h']
            
            # Probar orientación normal y rotada
            for ancho, largo in [(w, h), (h, w)]:
                if ancho <= espacio['w'] and largo <= espacio['h']:
                    # ¡Cabe! Lo posicionamos
                    nuevo_bulto = {
                        'x': espacio['x'], 'y': espacio['y'],
                        'w': ancho, 'h': largo,
                        'n': item['nombre'], 'c': item['color']
                    }
                    cargados.append(nuevo_bulto)
                    
                    # Dividir el espacio restante en dos nuevos espacios libres (Guillotine Split)
                    # Espacio a la derecha
                    if espacio['w'] - ancho > 0:
                        espacios_libres.append({
                            'x': espacio['x'] + ancho, 'y': espacio['y'],
                            'w': espacio['w'] - ancho, 'h': largo
                        })
                    # Espacio arriba
                    if espacio['h'] - largo > 0:
                        espacios_libres.append({
                            'x': espacio['x'], 'y': espacio['y'] + largo,
                            'w': espacio['w'], 'h': espacio['h'] - largo
                        })
                    
                    espacios_libres.pop(i)
                    colocado = True
                    break
            if colocado: break
        
        if not colocado:
            no_cargados.append(item)
            
    return cargados, no_cargados

# --- INTERFAZ ---
if 'productos' not in st.session_state: st.session_state.productos = {}

st.title("🚀 Optimizador de Carga Máxima")

col_cfg, col_vis = st.columns([1, 2])

with col_cfg:
    nombre_plan = st.text_input("📦 Nombre del Plan / Cliente (Obligatorio)")
    ancho_t = st.number_input("Ancho Camión (cm)", min_value=1, value=240)
    largo_t = st.number_input("Largo Camión (cm)", min_value=1, value=1200)
    
    st.divider()
    with st.expander("Añadir Modelos de Heladeras"):
        with st.form("nuevo_p"):
            n = st.text_input("Nombre Modelo")
            a = st.number_input("Ancho (cm)", min_value=1, value=70)
            p = st.number_input("Profundidad (cm)", min_value=1, value=80)
            c = st.color_picker("Color", "#3498db")
            if st.form_submit_button("Registrar") and n:
                st.session_state.productos[n] = {'w': a, 'h': p, 'color': c}
                st.rerun()

    carga_solicitada = []
    if st.session_state.productos:
        st.write("**Cantidades a cargar:**")
        for n, d in st.session_state.productos.items():
            cant = st.number_input(f"{n} ({d['w']}x{d['h']})", min_value=0, key=f"q_{n}")
            for _ in range(cant):
                carga_solicitada.append({'nombre': n, 'w': d['w'], 'h': d['h'], 'color': d['color']})

with col_vis:
    if st.button("CALCULAR APROVECHAMIENTO MÁXIMO", type="primary", use_container_width=True):
        if not nombre_plan:
            st.error("⚠️ Error: El Plan debe tener un nombre.")
        elif not carga_solicitada:
            st.warning("⚠️ No hay bultos seleccionados.")
        else:
            cargados, sobrantes = optimizar_espacio_maximo(ancho_t, largo_t, carga_solicitada)
            
            # Gráfico
            fig, ax = plt.subplots(figsize=(10, 8))
            ax.add_patch(patches.Rectangle((0,0), ancho_t, largo_t, color="#f1f3f6", ec="black", lw=2))
            plt.title(f"CLIENTE: {nombre_plan} | {datetime.now().strftime('%d/%m/%Y')}", fontsize=12)
            
            for b in cargados:
                ax.add_patch(patches.Rectangle((b['x'], b['y']), b['w'], b['h'], fc=b['c'], ec="white", lw=0.5))
                ax.text(b['x']+b['w']/2, b['y']+b['h']/2, b['n'], ha='center', va='center', fontsize=5, rotation=90, color="white")

            plt.xlim(-50, ancho_t+50); plt.ylim(-50, largo_t+100); ax.set_aspect('equal'); plt.axis('off')
            st.pyplot(fig)
            
            # Reporte de Eficiencia
            area_utilizada = sum(b['w']*b['h'] for b in cargados)
            eficiencia = (area_utilizada / (ancho_t * largo_t)) * 100
            
            c1, c2 = st.columns(2)
            c1.metric("Espacio Utilizado", f"{eficiencia:.1f}%")
            c2.metric("Bultos Cargados", len(cargados))
            
            if sobrantes:
                st.error(f"❌ ATENCIÓN: {len(sobrantes)} bultos quedaron fuera por falta de espacio.")
                df_sobra = pd.DataFrame(sobrantes)['nombre'].value_counts()
                st.write("Detalle de lo que NO entró:")
                st.dataframe(df_sobra)
            else:
                st.success("✅ ¡Perfecto! Toda la mercadería entró en el camión.")
