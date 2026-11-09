import streamlit as st
import pandas as pd
import numpy as np
import holidays
from datetime import date
import calendar

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
ARCHIVO_DATOS = "Amex_Afiliados.parquet"

C_FECHA_VTA = "fecha_vta"
C_ESTADO = "estado"
C_DECISION = "decision"
C_FECHA_DEC = "fecha_decision"
C_ASESOR = "asesor"

TXT_LE = "LEAD EFECTIVO"
TXT_LNC = "LEAD NO CAPTURADO"
TXT_LNC_COND = "LEAD NO CONDICIONES"
TXT_REMED = "REMEDIACIÓN"
# ==========================================

st.set_page_config(page_title="Informe Gerencial Amex", layout="wide")

@st.cache_data
def cargar_datos():
    try:
        df = pd.read_parquet(ARCHIVO_DATOS)
        df.columns = [str(c).strip().lower() for c in df.columns]
        if C_FECHA_VTA in df.columns:
            df[C_FECHA_VTA] = pd.to_datetime(df[C_FECHA_VTA], errors='coerce').dt.date
        if C_FECHA_DEC in df.columns:
            df[C_FECHA_DEC] = pd.to_datetime(df[C_FECHA_DEC], errors='coerce').dt.date
        return df
    except Exception as e:
        st.error(f"❌ Error al leer el archivo Parquet: {e}")
        return pd.DataFrame()

df_raw = cargar_datos()

if not df_raw.empty:
    # --- FILTROS EN BARRA LATERAL ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("🔍 Filtros Gerenciales")
    
    fechas_validas = df_raw[C_FECHA_VTA].dropna() if C_FECHA_VTA in df_raw.columns else pd.Series()
    años_disp = sorted(fechas_validas.apply(lambda x: x.year).unique()) if not fechas_validas.empty else [date.today().year]
    año_sel = st.sidebar.selectbox("Año", años_disp, index=len(años_disp)-1)
    
    meses_disp = sorted(fechas_validas[fechas_validas.apply(lambda x: x.year) == año_sel].apply(lambda x: x.month).unique()) if not fechas_validas.empty else [date.today().month]
    nombres_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    mes_formateado = [nombres_meses[m] for m in meses_disp if m in nombres_meses]
    
    if mes_formateado:
        mes_sel_nombre = st.sidebar.selectbox("Mes", mes_formateado, index=len(mes_formateado)-1)
        mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]
    else:
        mes_sel = date.today().month
        mes_sel_nombre = nombres_meses[mes_sel]

    # Filtro opcional por Asesor
    if C_ASESOR in df_raw.columns:
        asesores = ["Todos"] + sorted(df_raw[C_ASESOR].dropna().astype(str).unique().tolist())
        asesor_sel = st.sidebar.selectbox("Asesor", asesores)
        if asesor_sel != "Todos":
            df_raw = df_raw[df_raw[C_ASESOR].astype(str) == asesor_sel]

    # --- CALENDARIO HÁBIL (Lunes a Sábado, sin festivos México) ---
    festivos_mx = holidays.Mexico(years=año_sel)
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    
    fechas_mes = [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]
    df_cal = pd.DataFrame({"Fecha": fechas_mes})
    df_cal['Día_Semana'] = pd.to_datetime(df_cal['Fecha']).dt.dayofweek
    df_cal['Es_Festivo'] = df_cal['Fecha'].apply(lambda x: x in festivos_mx)
    df_cal = df_cal[~((df_cal['Día_Semana'] == 6) | (df_cal['Es_Festivo']))].copy()

    # --- FILTRAR DATOS DEL MES EN VENTAS ---
    df_filtro = df_raw[(df_raw[C_FECHA_VTA].apply(lambda x: getattr(x, 'year', 0)) == año_sel) & 
                       (df_raw[C_FECHA_VTA].apply(lambda x: getattr(x, 'month', 0)) == mes_sel)].copy() if C_FECHA_VTA in df_raw.columns else pd.DataFrame()

    # Agrupación diaria con tus reglas exactas de conteo
    if not df_filtro.empty:
        agrupado = df_filtro.groupby(C_FECHA_VTA).apply(lambda x: pd.Series({
            'Tramites': len(x),
            'Lead Efectivo': (x[C_ESTADO].astype(str).str.upper() == TXT_LE).sum() if C_ESTADO in x.columns else 0,
            'Lead No Capturado': (x[C_ESTADO].astype(str).str.upper() == TXT_LNC).sum() if C_ESTADO in x.columns else 0,
            'Lead No Condiciones': (x[C_ESTADO].astype(str).str.upper() == TXT_LNC_COND).sum() if C_ESTADO in x.columns else 0,
            'Otros': ((x[C_ESTADO].astype(str).str.upper() == TXT_REMED) | 
                      (~x[C_ESTADO].astype(str).str.upper().isin([TXT_LE, TXT_LNC, TXT_LNC_COND, '']))).sum() if C_ESTADO in x.columns else 0,
            
            'EVALUADO': (x[C_DECISION].astype(str) != '-').sum() if C_DECISION in x.columns else 0,
            'NO GESTIONADO': (x[C_DECISION].astype(str) == '-').sum() if C_DECISION in x.columns else 0,
            'Declinado': (x[C_DECISION].astype(str).str.upper() == 'D').sum() if C_DECISION in x.columns else 0,
            'Cancelado': (x[C_DECISION].astype(str).str.upper() == 'C').sum() if C_DECISION in x.columns else 0,
            'Pendiente': (x[C_DECISION].astype(str).str.upper() == 'P').sum() if C_DECISION in x.columns else 0,
            
            'AP MES': ((x[C_DECISION].astype(str).str.upper() == 'A') & (pd.to_datetime(x[C_FECHA_DEC], errors='coerce').dt.month == mes_sel)).sum() if (C_DECISION in x.columns and C_FECHA_DEC in x.columns) else 0,
            'AP COSECHA': ((x[C_DECISION].astype(str).str.upper() == 'A') & (pd.to_datetime(x[C_FECHA_DEC], errors='coerce').dt.month != mes_sel)).sum() if (C_DECISION in x.columns and C_FECHA_DEC in x.columns) else 0
        })).reset_index()
    else:
        agrupado = pd.DataFrame(columns=['Fecha', 'Tramites', 'Lead Efectivo'])

    # Unir calendario con los datos agrupados
    df_final = pd.merge(df_cal, agrupado, left_on="Fecha", right_on=C_FECHA_VTA, how="left").fillna(0)
    
    dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb"}
    df_final['Día'] = df_final.apply(lambda row: f"{dias_esp[row['Día_Semana']]}-{row['Fecha'].strftime('%d-%b')}".lower(), axis=1)

    # --- CÁLCULO DE MÉTRICAS Y FORMULAS GERENCIALES ---
    # Metas base configuradas por asesor y planta
    meta_asesor_diaria = 279 / 407  # Proporcional estándar
    agentes_planta_fijo = 407
    agentes_log_fijo = 393
    
    df_final['Meta Lead Efectivos Programados'] = meta_asesor_diaria * agentes_planta_fijo
    df_final['Meta Lead Efectivos Asistieron'] = meta_asesor_diaria * agentes_log_fijo
    df_final['Diferencia'] = df_final['Meta Lead Efectivos Programados'] - df_final['Meta Lead Efectivos Asistieron']
    
    df_final['% LE'] = np.where(df_final['Tramites'] > 0, df_final['Lead Efectivo'] / df_final['Tramites'], 0)
    df_final['% REM/RECH'] = np.where(df_final['Tramites'] > 0, df_final['Otros'] / df_final['Tramites'], 0)
    df_final['Prom'] = np.where(agentes_log_fijo > 0, df_final['Lead Efectivo'] / agentes_log_fijo, 0)
    
    df_final['Agentes Log'] = agentes_log_fijo
    df_final['Agentes Plantilla'] = agentes_planta_fijo
    df_final['% Ausentismo'] = np.where(agentes_planta_fijo > 0, (agentes_planta_fijo - agentes_log_fijo) / agentes_planta_fijo, 0)
    
    # SPH (Leads efectivos / Horas reales de malla, asumido 7 hrs base)
    df_final['SPH'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Lead Efectivo'] / 7, 0)
    
    df_final['AP DIA'] = df_final['AP MES'] + df_final['AP COSECHA']
    df_final['AP Acum'] = np.where(df_final['Lead Efectivo'].cumsum() > 0, df_final['AP MES'].cumsum() / df_final['Lead Efectivo'].cumsum(), 0)
    
    df_final['Meta Día'] = 279
    df_final['GAP'] = df_final['Meta Día'].cumsum() - df_final['Lead Efectivo'].cumsum()
    
    df_final['% EVALUADO'] = np.where(df_final['Lead Efectivo'] > 0, df_final['EVALUADO'] / df_final['Lead Efectivo'], 0)
    df_final['% Declinado'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Declinado'] / df_final['Lead Efectivo'], 0)
    df_final['% Cancelado'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Cancelado'] / df_final['Lead Efectivo'], 0)
    df_final['% Pendiente'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Pendiente'] / df_final['Lead Efectivo'], 0)

    # Columnas finales requeridas en la vista
    columnas_vista = [
        'Día', 'Tramites', 'Lead Efectivo', 'Meta Lead Efectivos Programados', 'Meta Lead Efectivos Asistieron', 'Diferencia',
        'Lead No Capturado', 'Lead No Condiciones', 'Otros', '% LE', '% REM/RECH', 'Prom',
        'Agentes Log', 'Agentes Plantilla', '% Ausentismo', 'SPH', 
        'AP MES', 'AP COSECHA', 'AP DIA', 'AP Acum', 'Meta Día', 'GAP',
        'EVALUADO', '% EVALUADO', 'NO GESTIONADO', 
        'Declinado', '% Declinado', 'Cancelado', '% Cancelado', 'Pendiente', '% Pendiente'
    ]
    
    df_vista = df_final[[c for c in columnas_vista if c in df_final.columns]].copy()

    # --- INTERFAZ VISUAL ---
    st.title(f"📊 Informe Gerencial - {mes_sel_nombre} {año_sel}")
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Trámites Totales", f"{int(df_vista['Tramites'].sum()) if 'Tramites' in df_vista else 0}")
    k2.metric("Leads Efectivos", f"{int(df_vista['Lead Efectivo'].sum()) if 'Lead Efectivo' in df_vista else 0}")
    k3.metric("GAP Acumulado", f"{int(df_vista['GAP'].iloc[-1]) if 'GAP' in df_vista and not df_vista.empty else 0}")
    k4.metric("AP Mes (Total)", f"{int(df_vista['AP MES'].sum()) if 'AP MES' in df_vista else 0}")
    
    st.divider()

    def semaforo_le(val):
        if not isinstance(val, float): return ''
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
    st.warning("⚠️ No hay datos para mostrar. Ejecuta tu script local para sincronizar la información.")
