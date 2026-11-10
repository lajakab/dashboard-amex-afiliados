import streamlit as st
import pandas as pd
import numpy as np
import holidays
from datetime import date
import calendar

st.set_page_config(page_title="Informe Gerencial Amex", layout="wide")

@st.cache_data
def cargar_pestanas():
    # Simulamos la lectura de "hojas" llamando a los archivos independientes
    try:
        df_v = pd.read_parquet("ventas.parquet") if "ventas.parquet" else pd.DataFrame()
    except: df_v = pd.DataFrame()
    
    try:
        df_p = pd.read_parquet("planta.parquet") if "planta.parquet" else pd.DataFrame()
    except: df_p = pd.DataFrame()
    
    try:
        df_ppto = pd.read_parquet("seg_ppto.parquet") if "seg_ppto.parquet" else pd.DataFrame()
    except: df_ppto = pd.DataFrame()
    
    try:
        df_m = pd.read_parquet("malla_día.parquet") if "malla_día.parquet" else pd.DataFrame()
    except: df_m = pd.DataFrame()

    return df_v, df_p, df_ppto, df_m

df_ventas, df_planta, df_ppto, df_malla = cargar_pestanas()

if not df_ventas.empty and len(df_ventas.columns) > 45:
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("🔍 Filtros")
    
    # 1. PREPARACIÓN VENTAS (Vienen como texto, las pasamos a Fecha/Número según coordenada)
    # E(4)=Fecha, H(7)=Estado, AT(45)=Decision
    df_ventas['F_VTA'] = pd.to_datetime(df_ventas.iloc[:, 4], errors='coerce').dt.normalize()
    df_ventas['ESTADO'] = df_ventas.iloc[:, 7].astype(str).str.strip().str.upper()
    df_ventas['DECISION'] = df_ventas.iloc[:, 45].astype(str).str.strip().str.upper()
    
    # Búsqueda dinámica de la fecha de decisión
    col_fdec_idx = next((i for i, c in enumerate(df_ventas.columns) if 'fec' in str(c).lower() and 'dec' in str(c).lower()), None)
    df_ventas['F_DEC'] = pd.to_datetime(df_ventas.iloc[:, col_fdec_idx], errors='coerce').dt.normalize() if col_fdec_idx is not None else pd.NaT

    # Filtros laterales
    fechas_validas = df_ventas['F_VTA'].dropna()
    años_disp = sorted(fechas_validas.dt.year.unique()) if not fechas_validas.empty else [date.today().year]
    año_sel = st.sidebar.selectbox("Año", años_disp, index=len(años_disp)-1)
    
    meses_disp = sorted(fechas_validas[fechas_validas.dt.year == año_sel].dt.month.unique()) if not fechas_validas.empty else [date.today().month]
    nombres_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    mes_formateado = [nombres_meses[m] for m in meses_disp if m in nombres_meses]
    mes_sel_nombre = st.sidebar.selectbox("Mes", mes_formateado, index=len(mes_formateado)-1) if mes_formateado else "Noviembre"
    mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]

    # --- CALENDARIO VERTICAL ---
    festivos_mx = holidays.Mexico(years=año_sel)
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    df_cal = pd.DataFrame({"Fecha": [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]})
    df_cal['Fecha'] = pd.to_datetime(df_cal['Fecha'])
    df_cal['Día_Semana'] = df_cal['Fecha'].dt.dayofweek
    df_cal['Es_Festivo'] = df_cal['Fecha'].apply(lambda x: x in festivos_mx)
    df_cal = df_cal[~((df_cal['Día_Semana'] == 6) | (df_cal['Es_Festivo']))].copy()

    # --- PREPARACIÓN HOJAS AUXILIARES ---
    # PLANTA: A(0)=Fecha, B(1)=Plantilla, C(2)=Log
    if not df_planta.empty and len(df_planta.columns) > 2:
        df_planta['Fecha'] = pd.to_datetime(df_planta.iloc[:, 0], errors='coerce').dt.normalize()
        df_planta['Agentes Plantilla'] = pd.to_numeric(df_planta.iloc[:, 1], errors='coerce').fillna(0)
        df_planta['Agentes Log'] = pd.to_numeric(df_planta.iloc[:, 2], errors='coerce').fillna(0)
        df_p_agg = df_planta.groupby('Fecha').agg({'Agentes Plantilla': 'max', 'Agentes Log': 'max'}).reset_index()
        df_cal = pd.merge(df_cal, df_p_agg, on='Fecha', how='left')

    # SEG PPTO: AJ(35)=Fecha, AK(36)=Meta Día, AL(37)=Meta Asesor
    if not df_ppto.empty and len(df_ppto.columns) > 37:
        df_ppto['Fecha'] = pd.to_datetime(df_ppto.iloc[:, 35], errors='coerce').dt.normalize()
        df_ppto['Meta Día'] = pd.to_numeric(df_ppto.iloc[:, 36], errors='coerce').fillna(0)
        df_ppto['Meta Asesor'] = pd.to_numeric(df_ppto.iloc[:, 37], errors='coerce').fillna(0)
        df_ppto_agg = df_ppto.groupby('Fecha').agg({'Meta Día': 'max', 'Meta Asesor': 'max'}).reset_index()
        df_cal = pd.merge(df_cal, df_ppto_agg, on='Fecha', how='left')

    # MALLA DÍA: N(13)=Fecha, Tiempo real
    if not df_malla.empty and len(df_malla.columns) > 13:
        df_malla['Fecha'] = pd.to_datetime(df_malla.iloc[:, 13], errors='coerce').dt.normalize()
        col_tr_idx = next((i for i, c in enumerate(df_malla.columns) if 'tiempo' in str(c).lower()), -1)
        if col_tr_idx != -1:
            df_malla['Tiempo Real'] = pd.to_numeric(df_malla.iloc[:, col_tr_idx], errors='coerce').fillna(0)
            df_m_agg = df_malla.groupby('Fecha').agg({'Tiempo Real': 'sum'}).reset_index()
            df_cal = pd.merge(df_cal, df_m_agg, on='Fecha', how='left')

    # Prevenir KeyError rellenando vacíos
    for col in ['Agentes Plantilla', 'Agentes Log', 'Meta Día', 'Meta Asesor', 'Tiempo Real']:
        if col not in df_cal.columns: df_cal[col] = 0
    df_cal = df_cal.fillna(0)

    # --- AGRUPACIÓN DE VENTAS ---
    df_filtro = df_ventas[(df_ventas['F_VTA'].dt.year == año_sel) & (df_ventas['F_VTA'].dt.month == mes_sel)]
    agrupado = df_filtro.groupby('F_VTA').apply(lambda x: pd.Series({
        'Tramites': len(x),
        'Lead Efectivo': (x['ESTADO'] == 'LEAD EFECTIVO').sum(),
        'Lead No Capturado': (x['ESTADO'] == 'LEAD NO CAPTURADO').sum(),
        'Lead No Condiciones': (x['ESTADO'] == 'LEAD NO CONDICIONES').sum(),
        'Otros': (~x['ESTADO'].isin(['LEAD EFECTIVO', 'LEAD NO CAPTURADO', 'LEAD NO CONDICIONES', '', 'NAN'])).sum(),
        'EVALUADO': (x['DECISION'] != '-').sum(),
        'NO GESTIONADO': (x['DECISION'] == '-').sum(),
        'Declinado': (x['DECISION'] == 'D').sum(),
        'Cancelado': (x['DECISION'] == 'C').sum(),
        'Pendiente': (x['DECISION'] == 'P').sum(),
        'AP MES': ((x['DECISION'] == 'A') & (x['F_DEC'].dt.month == mes_sel)).sum(),
        'AP COSECHA': ((x['DECISION'] == 'A') & (x['F_DEC'].dt.month != mes_sel)).sum()
    })).reset_index().rename(columns={'F_VTA': 'Fecha'})

    # --- CRUCE FINAL Y CÁLCULOS ---
    df_final = pd.merge(df_cal, agrupado, on="Fecha", how="left").fillna(0)
    dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb"}
    df_final['Día'] = df_final.apply(lambda row: f"{dias_esp[row['Fecha'].dayofweek]}-{row['Fecha'].strftime('%d-%b')}".lower(), axis=1)

    # Cálculos Gerenciales Exactos
    df_final['Meta Lead Efectivos Programados'] = df_final['Meta Asesor'] * df_final['Agentes Plantilla']
    df_final['Meta Lead Efectivos Asistieron'] = df_final['Meta Asesor'] * df_final['Agentes Log']
    df_final['Diferencia'] = df_final['Meta Lead Efectivos Programados'] - df_final['Meta Lead Efectivos Asistieron']
    
    df_final['% LE'] = np.where(df_final['Tramites'] > 0, df_final['Lead Efectivo'] / df_final['Tramites'], 0)
    df_final['% REM/RECH'] = np.where(df_final['Tramites'] > 0, df_final['Otros'] / df_final['Tramites'], 0)
    df_final['Prom'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Agentes Log'] / df_final['Lead Efectivo'], 0)
    df_final['% Ausentismo'] = np.where(df_final['Agentes Plantilla'] > 0, (df_final['Agentes Plantilla'] - df_final['Agentes Log']) / df_final['Agentes Plantilla'], 0)
    df_final['SPH'] = np.where(df_final['Tiempo Real'] > 0, df_final['Lead Efectivo'] / df_final['Tiempo Real'], 0)
    df_final['AP DIA'] = df_final['AP MES'] + df_final['AP COSECHA']
    df_final['AP Acum'] = np.where(df_final['Lead Efectivo'].cumsum() > 0, df_final['AP MES'].cumsum() / df_final['Lead Efectivo'].cumsum(), 0)
    df_final['GAP'] = df_final['Meta Día'].cumsum() - df_final['Lead Efectivo'].cumsum()
    df_final['% EVALUADO'] = np.where(df_final['Lead Efectivo'] > 0, df_final['EVALUADO'] / df_final['Lead Efectivo'], 0)
    df_final['% Declinado'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Declinado'] / df_final['Lead Efectivo'], 0)
    df_final['% Cancelado'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Cancelado'] / df_final['Lead Efectivo'], 0)
    df_final['% Pendiente'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Pendiente'] / df_final['Lead Efectivo'], 0)

    columnas_vista = [
        'Día', 'Tramites', 'Lead Efectivo', 'Meta Lead Efectivos Programados', 'Meta Lead Efectivos Asistieron', 'Diferencia',
        'Lead No Capturado', 'Lead No Condiciones', 'Otros', '% LE', '% REM/RECH', 'Prom',
        'Agentes Log', 'Agentes Plantilla', '% Ausentismo', 'SPH', 
        'AP MES', 'AP COSECHA', 'AP DIA', 'AP Acum', 'Meta Día', 'GAP',
        'EVALUADO', '% EVALUADO', 'NO GESTIONADO', 
        'Declinado', '% Declinado', 'Cancelado', '% Cancelado', 'Pendiente', '% Pendiente'
    ]
    df_vista = df_final[[c for c in columnas_vista if c in df_final.columns]].copy()

    st.title(f"📊 Informe Gerencial - {mes_sel_nombre} {año_sel}")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Trámites Totales", f"{int(df_vista['Tramites'].sum())}")
    k2.metric("Leads Efectivos", f"{int(df_vista['Lead Efectivo'].sum())}")
    k3.metric("GAP Acumulado", f"{int(df_vista['GAP'].iloc[-1]) if not df_vista.empty else 0}")
    k4.metric("AP Mes (Total)", f"{int(df_vista['AP MES'].sum())}")
    
    st.divider()

    def semaforo_le(val):
        if not isinstance(val, (float, int)): return ''
        if val >= 0.90: return 'background-color: #c6e0b4; color: black;'
        if val >= 0.80: return 'background-color: #ffe699; color: black;'
        if val > 0: return 'background-color: #ffc000; color: black;'
        return ''

    styler = df_vista.style.format({col: '{:.0f}' for col in df_vista.columns if '%' not in col and col != 'Día'})\
                           .format({col: '{:.1%}' for col in df_vista.columns if '%' in col})\
                           .map(semaforo_le, subset=['% LE'] if '% LE' in df_vista.columns else [])\
                           .set_properties(**{'text-align': 'center', 'font-size': '12px'})
    st.dataframe(styler, use_container_width=True, height=600, hide_index=True)
else:
    st.warning("⚠️ No se encontró la hoja de Ventas o le faltan columnas. Ejecuta el script local.")
