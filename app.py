import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import io

# Configuración de la App
st.set_page_config(page_title="Carga Inteligente de Heladeras", layout="wide")

# --- PERSISTENCIA SIMPLE ---
if 'productos' not in st.session_state:
    st.session_state.productos = {}
if 'historial' not in st.session_state:
    st.session_state.historial = []

# --- LÓGICA DE ACOMODO ---
def calcular_layout(ancho_c, largo_c, items):
    # Ordenar por tamaño para optimizar
    items.sort(key=lambda x: x['w'] * x['h'], reverse=True)
    posiciones = []
    x, y, max_h_fila = 0, 0, 0
    
    for item in items:
        w, h = item['w'], item['h']
        # Rotación automática si entra mejor
        if x + w > ancho_c and x + h <= ancho_c:
            w, h = h, w
        
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

# --- INTERFAZ ---
st.title("🚛 Sistema de Gestión de Carga Pro")

pestana1, pestana2 = st.tabs(["Nueva Carga", "Historial"])

with pestana1:
    col_izq, col_der = st.columns([1, 2])
    
    with col_izq:
        st.subheader("1. Datos del Transporte")
        ancho_camion = st.number_input("Ancho útil (cm)", value=240)
        largo_camion = st.number_input("Largo útil (cm)", value=1200)
        
        st.divider()
        st.subheader("2. Inventario de Productos")
        with st.expander("Registrar Nuevo Producto"):
            nom = st.text_input("Nombre (ej: Heladera Gafa)")
            an = st.number_input("Ancho (cm)", 70)
            pr = st.number_input("Profundo (cm)", 80)
            cl = st.color_picker("Color", "#3498db")
            if st.button("Guardar en Memoria"):
                st.session_state.productos[nom] = {'w': an, 'h': pr, 'color': cl}

        carga_total = []
        for nombre, d in st.session_state.productos.items():
            cant = st.number_input(f"Cantidad de {nombre}", 0, key=nombre)
            for _ in range(cant):
                carga_total.append({'nombre': nombre, 'w': d['w'], 'h': d['h'], 'color': d['color']})

    with col_der:
        st.subheader("3. Plan de Carga Visual")
        if st.button("GENERAR PLAN", type="primary"):
            resultado = calcular_layout(ancho_camion, largo_camion, carga_total)
            
            # Dibujo
            fig, ax = plt.subplots(figsize=(10, 5))
            ax.add_patch(patches.Rectangle((0,0), ancho_camion, largo_camion, color="#eeeeee", ec="#000"))
            for p in resultado:
                ax.add_patch(patches.Rectangle((p['x'], p['y']), p['w'], p['h'], fc=p['c'], ec="white"))
                ax.text(p['x']+p['w']/2, p['y']+p['h']/2, p['n'], ha='center', va='center', fontsize=7, rotation=90)
            
            plt.xlim(-50, ancho_camion+50); plt.ylim(-50, largo_camion+50)
            ax.set_aspect('equal'); plt.axis('off')
            st.pyplot(fig)
            
            # Guardar en historial
            if resultado:
                st.session_state.historial.append({
                    "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Bultos": len(resultado),
                    "Estado": "Calculado"
                })

with pestana2:
    st.subheader("Registros Anteriores")
    if st.session_state.historial:
        st.table(st.session_state.historial)
    else:
        st.info("No hay cargas registradas aún.")