import streamlit as st
import pandas as pd
import numpy as np
import holidays
from datetime import date
import calendar

# ==========================================
# CONFIGURACIÓN 
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
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("🔍 Filtros")
    
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

    festivos_mx = holidays.Mexico(years=año_sel)
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    
    fechas_mes = [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]
    df_cal = pd.DataFrame({"Fecha": fechas_mes})
    df_cal['Día_Semana'] = pd.to_datetime(df_cal['Fecha']).dt.dayofweek
    df_cal['Es_Festivo'] = df_cal['Fecha'].apply(lambda x: x in festivos_mx)
    df_cal = df_cal[~((df_cal['Día_Semana'] == 6) | (df_cal['Es_Festivo']))]

    df_filtro = df_raw[(df_raw[C_FECHA_VTA].apply(lambda x: getattr(x, 'year', 0)) == año_sel) & 
                          (df_raw[C_FECHA_VTA].apply(lambda x: getattr(x, 'month', 0)) == mes_sel)].copy() if C_FECHA_VTA in df_raw.columns else pd.DataFrame()

    if not df_filtro.empty:
        agrupado = df_filtro.groupby(C_FECHA_VTA).apply(lambda x: pd.Series({
            'Tramites': len(x),
            'Lead Efectivo': (x[C_ESTADO] == TXT_LE).sum() if C_ESTADO in x.columns else 0,
            'Lead No Capturado': (x[C_ESTADO] == TXT_LNC).sum() if C_ESTADO in x.columns else 0,
            'Lead No Condiciones': (x[C_ESTADO] == TXT_LNC_COND).sum() if C_ESTADO in x.columns else 0,
            'Otros': (x[C_ESTADO] == TXT_REMED).sum() if C_ESTADO in x.columns else 0,
            'EVALUADO': (x[C_DECISION] != "-").sum() if C_DECISION in x.columns else 0,
            'NO GESTIONADO': (x[C_DECISION] == "-").sum() if C_DECISION in x.columns else 0,
            'Declinado': (x[C_DECISION] == "D").sum() if C_DECISION in x.columns else 0,
            'Cancelado': (x[C_DECISION] == "C").sum() if C_DECISION in x.columns else 0,
            'Pendiente': (x[C_DECISION] == "P").sum() if C_DECISION in x.columns else 0,
            'AP MES': ((x[C_DECISION] == "A") & (pd.to_datetime(x[C_FECHA_DEC], errors='coerce').dt.month == mes_sel)).sum() if (C_DECISION in x.columns and C_FECHA_DEC in x.columns) else 0,
            'AP COSECHA': ((x[C_DECISION] == "A") & (pd.to_datetime(x[C_FECHA_DEC], errors='coerce').dt.month != mes_sel)).sum() if (C_DECISION in x.columns and C_FECHA_DEC in x.columns) else 0
        })).reset_index()
    else:
        agrupado = pd.DataFrame(columns=['Fecha', 'Tramites', 'Lead Efectivo'])

    df_final = pd.merge(df_cal, agrupado, left_on="Fecha", right_on=C_FECHA_VTA, how="left").fillna(0)
    
    dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb"}
    df_final['Día'] = df_final.apply(lambda row: f"{dias_esp[row['Día_Semana']]}-{row['Fecha'].strftime('%d-%b')}".lower(), axis=1)

    df_final['% LE'] = np.where(df_final['Tramites'] > 0, df_final['Lead Efectivo'] / df_final['Tramites'], 0)
    df_final['% REM/RECH'] = np.where(df_final['Tramites'] > 0, df_final['Otros'] / df_final['Tramites'], 0)
    df_final['AP DIA'] = df_final['AP MES'] + df_final['AP COSECHA']
    df_final['AP Acum'] = np.where(df_final['Lead Efectivo'].cumsum() > 0, df_final['AP MES'].cumsum() / df_final['Lead Efectivo'].cumsum(), 0)

    columnas_vista = [
        'Día', 'Tramites', 'Lead Efectivo', 'Lead No Capturado', 'Lead No Condiciones', 'Otros', 
        '% LE', '% REM/RECH', 'AP MES', 'AP COSECHA', 'AP DIA', 'AP Acum',
        'EVALUADO', 'NO GESTIONADO', 'Declinado', 'Cancelado', 'Pendiente'
    ]
    df_vista = df_final[[c for c in columnas_vista if c in df_final.columns]].copy()

    st.title(f"📊 Informe Gerencial - {mes_sel_nombre} {año_sel}")
    
    k1, k2, k3 = st.columns(3)
    k1.metric("Trámites Totales", f"{int(df_vista['Tramites'].sum()) if 'Tramites' in df_vista else 0}")
    k2.metric("Leads Efectivos", f"{int(df_vista['Lead Efectivo'].sum()) if 'Lead Efectivo' in df_vista else 0}")
    k3.metric("AP Mes (Total)", f"{int(df_vista['AP MES'].sum()) if 'AP MES' in df_vista else 0}")
    
    st.divider()
    st.dataframe(df_vista, use_container_width=True, height=500, hide_index=True)
else:
    st.warning("⚠️ No hay datos para mostrar. Asegúrate de ejecutar tu script local para subir el archivo parquet optimizado.")
