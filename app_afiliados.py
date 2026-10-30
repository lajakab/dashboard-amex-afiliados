import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import holidays
import datetime
import calendar

st.set_page_config(page_title="Dashboard Afiliados Amex", page_icon="💳", layout="wide")

# ==========================================
# 1. CARGA DE DATOS Y DIAGNÓSTICO
# ==========================================
@st.cache_data
def cargar_datos():
    return pd.read_parquet("Amex_Afiliados.parquet")

try:
    df = cargar_datos()
except Exception as e:
    st.error(f"Error de sistema al leer el archivo: {e}")
    st.stop()

st.title("📊 Dashboard General - Amex")

# Panel de Diagnóstico para ver las columnas reales
st.info("✅ El archivo Parquet se leyó exitosamente. Revisa esta lista para conocer los nombres exactos de tus columnas:")
st.write(df.columns.tolist())

# ==========================================
# ⚠️ CONFIGURACIÓN DE COLUMNAS 
# ==========================================
# Modifica estas dos variables escribiendo los nombres exactos de la lista superior:
COLUMNA_FECHA = 'creation_date'   # Columna exacta de fecha de venta  
COLUMNA_ESTADO = 'estado'         # Columna exacta para los estados (Lead Efectivo, Rechazada, etc.)

if COLUMNA_FECHA not in df.columns or COLUMNA_ESTADO not in df.columns:
    st.warning(f"🚨 Actualiza los valores de COLUMNA_FECHA y COLUMNA_ESTADO (Líneas 30 y 31 del código) usando los nombres mostrados en el recuadro azul.")
    st.stop()

# Normalizar fecha internamente para evitar errores posteriores
df['Fecha_Normalizada'] = pd.to_datetime(df[COLUMNA_FECHA]).dt.date

# ==========================================
# 2. FILTROS Y LÓGICA DE CALENDARIO
# ==========================================
tab1, tab2 = st.tabs(["📅 General por mes y día", "⚙️ Otras Vistas"])

with tab1:
    st.subheader("Filtros de Tiempo")
    
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        years_disp = [2024, 2025, 2026, 2027]
        year_sel = st.selectbox("Seleccione el Año", years_disp, index=years_disp.index(2026) if 2026 in years_disp else 0)
    with col_f2:
        meses_dict = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 
                      7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        mes_sel_nombre = st.selectbox("Seleccione el Mes", list(meses_dict.values()), index=9)
        mes_sel_num = [k for k, v in meses_dict.items() if v == mes_sel_nombre][0]

    festivos_mx = holidays.Mexico(years=year_sel)
    num_dias_mes = calendar.monthrange(year_sel, mes_sel_num)[1]
    
    dias_habiles_lista = []
    for d in range(1, num_dias_mes + 1):
        fecha_act = datetime.date(year_sel, mes_sel_num, d)
        if fecha_act.weekday() != 6 and fecha_act not in festivos_mx:
            dias_habiles_lista.append(fecha_act)
            
    dias_habiles_totales = len(dias_habiles_lista)
    
    hoy = datetime.date.today()
    dias_transcurridos = [d for d in dias_habiles_lista if d <= hoy]
    total_transcurridos = len(dias_transcurridos) if hoy.month == mes_sel_num and hoy.year == year_sel else (dias_habiles_totales if hoy > datetime.date(year_sel, mes_sel_num, num_dias_mes) else 0)

    c1, c2, c3 = st.columns(3)
    c1.metric("Días Hábiles del Mes", dias_habiles_totales)
    c2.metric("Días Transcurridos", total_transcurridos)
    
    st.divider()

    # ==========================================
    # 3. TABLA Y MÉTRICAS
    # ==========================================
    df_mes = df[(pd.to_datetime(df['Fecha_Normalizada']).dt.year == year_sel) & (pd.to_datetime(df['Fecha_Normalizada']).dt.month == mes_sel_num)]
    
    if not df_mes.empty:
        resumen_diario = df_mes.groupby('Fecha_Normalizada').apply(lambda x: pd.Series({
            'Tramites': len(x),
            'Lead Efectivo': (x[COLUMNA_ESTADO] == 'LEAD EFECTIVO').sum(),
            'Lead No Capturado': (x[COLUMNA_ESTADO] == 'LEAD NO CAPTURADO').sum(),
            'Lead No Condiciones': (x[COLUMNA_ESTADO] == 'LEAD NO CONDICIONES').sum(),
            'Otros': (x[COLUMNA_ESTADO] == 'RECHAZADA').sum() + (x[COLUMNA_ESTADO] == 'REMEDIACIÓN').sum(),
            'AP': (x[COLUMNA_ESTADO] == 'A').sum(),
            'Declinado': (x[COLUMNA_ESTADO] == 'D').sum(),
            'Cancelado': (x[COLUMNA_ESTADO] == 'C').sum(),
            'Pendiente': (x[COLUMNA_ESTADO] == 'p').sum()
        })).reset_index()
    else:
        resumen_diario = pd.DataFrame(columns=['Fecha_Normalizada', 'Tramites', 'Lead Efectivo', 'Lead No Capturado', 
                                               'Lead No Condiciones', 'Otros', 'AP', 'Declinado', 'Cancelado', 'Pendiente'])

    fechas_del_mes = pd.DataFrame({'Fecha_Normalizada': [datetime.date(year_sel, mes_sel_num, d) for d in range(1, num_dias_mes + 1)]})
    resumen_diario = pd.merge(fechas_del_mes, resumen_diario, on='Fecha_Normalizada', how='left').fillna(0)
    
    dias_es = {0: 'lun', 1: 'mar', 2: 'mié', 3: 'jue', 4: 'vie', 5: 'sáb', 6: 'dom'}
    meses_ab = {10: 'oct', 11: 'nov', 12: 'dic', 1:'ene', 2:'feb', 3:'mar', 4:'abr', 5:'may', 6:'jun', 7:'jul', 8:'ago', 9:'sep'}
    resumen_diario['Día'] = resumen_diario['Fecha_Normalizada'].apply(lambda x: f"{dias_es[x.weekday()]}-{x.day:02d}-{meses_ab[x.month]}")

    resumen_diario['% LE'] = (resumen_diario['Lead Efectivo'] / resumen_diario['Tramites']).fillna(0)
    resumen_diario['% REM/RECH'] = (resumen_diario['Otros'] / resumen_diario['Tramites']).fillna(0)
    
    resumen_diario['Agentes Log'] = 60 
    resumen_diario['Agentes Plantilla'] = 61
    resumen_diario['Prom'] = (resumen_diario['Lead Efectivo'] / resumen_diario['Agentes Log']).fillna(0)
    resumen_diario['% Ausentimo'] = (resumen_diario['Agentes Plantilla'] / resumen_diario['Agentes Log'] - 1).fillna(0)
    resumen_diario['SPH'] = 0.70 
    
    resumen_diario['AP DIA'] = (resumen_diario['AP'] / resumen_diario['Lead Efectivo']).fillna(0)
    resumen_diario['AP Acum'] = resumen_diario['AP DIA'] 
    
    resumen_diario['Meta Día'] = 300 
    resumen_diario['Lead_Efectivo_Acum'] = resumen_diario['Lead Efectivo'].cumsum()
    resumen_diario['Meta_Acum'] = resumen_diario['Meta Día'].cumsum()
    
    resumen_diario['GAP'] = resumen_diario.apply(lambda x: 0 if x['Lead Efectivo'] == 0 else x['Lead_Efectivo_Acum'] - x['Meta_Acum'], axis=1)
    
    resumen_diario['% EVALUADO'] = 0.20 
    resumen_diario['NO GESTIONADO'] = 0 
    
    resumen_diario['% Declinado'] = (resumen_diario['Declinado'] / resumen_diario['Lead Efectivo']).fillna(0)
    resumen_diario['% Cancelado'] = (resumen_diario['Cancelado'] / resumen_diario['Lead Efectivo']).fillna(0)
    resumen_diario['% Pendiente'] = (resumen_diario['Pendiente'] / resumen_diario['Lead Efectivo']).fillna(0)

    columnas_finales = [
        'Fecha_Normalizada', 'Día', 'Tramites', 'Lead Efectivo', 'Lead No Capturado', 'Lead No Condiciones', 'Otros', 
        '% LE', '% REM/RECH', 'Prom', 'Agentes Log', 'Agentes Plantilla', '% Ausentimo', 'SPH', 
        'AP', 'AP DIA', 'AP Acum', 'Meta Día', 'GAP', '% EVALUADO', 'NO GESTIONADO', 
        'Declinado', '% Declinado', 'Cancelado', '% Cancelado', 'Pendiente', '% Pendiente'
    ]
    
    df_tabla = resumen_diario[columnas_finales].copy()
    st.subheader("📋 Resumen Diario Operativo")
    
    styler = df_tabla.style.format({
        '% LE': '{:.0%}', '% REM/RECH': '{:.0%}', 'Prom': '{:.1f}', '% Ausentimo': '{:.0%}',
        'SPH': '{:.2f}', 'AP DIA': '{:.1%}', 'AP Acum': '{:.1%}', '% EVALUADO': '{:.0%}',
        '% Declinado': '{:.1%}', '% Cancelado': '{:.1%}', '% Pendiente': '{:.1%}'
    })
    styler = styler.set_properties(subset=['Tramites', 'Lead Efectivo'], **{'background-color': '#e2efda', 'color': 'black'})
    
    st.dataframe(styler, use_container_width=True, hide_index=True)
    st.divider()

    # ==========================================
    # 4. GRÁFICA
    # ==========================================
    st.subheader("📉 Seguimiento LE Real Vs Pto Diario")
    
    df_grafica = resumen_diario[resumen_diario['Tramites'] > 0]
    
    if not df_grafica.empty:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_grafica['Día'], y=df_grafica['Meta Día'], name='LEADS EFECTIVOS PTTO', marker_color='#ed7d31', text=df_grafica['Meta Día'], textposition='auto'))
        fig.add_trace(go.Bar(x=df_grafica['Día'], y=df_grafica['Lead Efectivo'], name='LEADS EFECTIVOS REAL', marker_color='#203864', text=df_grafica['Lead Efectivo'], textposition='auto'))
        fig.add_trace(go.Bar(x=df_grafica['Día'], y=df_grafica['GAP'], name='DIFERENCIA NETA ACUMULADA', marker_color='#385723', text=df_grafica['GAP'], textposition='auto'))

        fig.update_layout(barmode='group', height=500, legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="left", x=0), margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos suficientes para mostrar la gráfica en este mes.")