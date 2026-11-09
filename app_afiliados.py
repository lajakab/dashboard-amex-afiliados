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

st.set_page_config(page_title="Informe Gerencial Amex", layout="wide")

@st.cache_data
def cargar_datos():
    try:
        df = pd.read_parquet(ARCHIVO_DATOS)
        df['fecha_vta'] = pd.to_datetime(df['fecha_vta'], errors='coerce')
        if 'fecha_decision' in df.columns:
            df['fecha_decision'] = pd.to_datetime(df['fecha_decision'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"❌ Error al leer el archivo Parquet: {e}")
        return pd.DataFrame()

df_raw = cargar_datos()

if not df_raw.empty:
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("🔍 Filtros")
    
    fechas_validas = df_raw['fecha_vta'].dropna()
    años_disp = sorted(fechas_validas.dt.year.unique()) if not fechas_validas.empty else [date.today().year]
    año_sel = st.sidebar.selectbox("Año", años_disp, index=len(años_disp)-1)
    
    meses_disp = sorted(fechas_validas[fechas_validas.dt.year == año_sel].dt.month.unique()) if not fechas_validas.empty else [date.today().month]
    nombres_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    mes_formateado = [nombres_meses[m] for m in meses_disp if m in nombres_meses]
    
    if mes_formateado:
        mes_sel_nombre = st.sidebar.selectbox("Mes", mes_formateado, index=len(mes_formateado)-1)
        mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]
    else:
        mes_sel = date.today().month
        mes_sel_nombre = nombres_meses[mes_sel]

    # --- CALENDARIO VERTICAL (Lunes a Sábado, sin festivos MX) ---
    festivos_mx = holidays.Mexico(years=año_sel)
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    
    fechas_mes = [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]
    df_cal = pd.DataFrame({"Fecha": fechas_mes})
    df_cal['Día_Semana'] = pd.to_datetime(df_cal['Fecha']).dt.dayofweek
    df_cal['Es_Festivo'] = df_cal['Fecha'].apply(lambda x: x in festivos_mx)
    df_cal = df_cal[~((df_cal['Día_Semana'] == 6) | (df_cal['Es_Festivo']))].copy()

    # --- FILTRAR DATOS Y AGRUPAR ---
    df_filtro = df_raw[(df_raw['fecha_vta'].dt.year == año_sel) & (df_raw['fecha_vta'].dt.month == mes_sel)].copy()

    if not df_filtro.empty:
        # Cruce exacto según instrucciones
        agrupado = df_filtro.groupby(df_filtro['fecha_vta'].dt.date).apply(lambda x: pd.Series({
            'Tramites': len(x),
            'Lead Efectivo': (x['estado'] == 'LEAD EFECTIVO').sum(),
            'Lead No Capturado': (x['estado'] == 'LEAD NO CAPTURADO').sum(),
            'Lead No Condiciones': (x['estado'] == 'LEAD NO CONDICIONES').sum(),
            'Otros': (~x['estado'].isin(['LEAD EFECTIVO', 'LEAD NO CAPTURADO', 'LEAD NO CONDICIONES'])).sum(), # Remedio + Otros
            
            'EVALUADO': (x['decision'] != '-').sum(),
            'NO GESTIONADO': (x['decision'] == '-').sum(),
            'Declinado': (x['decision'] == 'D').sum(),
            'Cancelado': (x['decision'] == 'C').sum(),
            'Pendiente': (x['decision'] == 'P').sum(),
            
            'AP MES': ((x['decision'] == 'A') & (x['fecha_decision'].dt.month == mes_sel)).sum(),
            'AP COSECHA': ((x['decision'] == 'A') & (x['fecha_decision'].dt.month != mes_sel)).sum(),
            
            # Variables de las otras hojas (tomamos el máximo porque son fijas por día gracias al merge local)
            'Agentes Log': x['agentes_log'].max() if 'agentes_log' in x.columns else 0,
            'Agentes Plantilla': x['agentes_plantilla'].max() if 'agentes_plantilla' in x.columns else 0,
            'meta_dia': x['meta_dia'].max() if 'meta_dia' in x.columns else 0,
            'meta_asesor': x['meta_asesor'].max() if 'meta_asesor' in x.columns else 0,
            'tiempo_real': x['tiempo_real'].max() if 'tiempo_real' in x.columns else 0
        })).reset_index().rename(columns={'fecha_vta': 'Fecha'})
    else:
        agrupado = pd.DataFrame(columns=['Fecha', 'Tramites', 'Lead Efectivo'])

    # --- UNIR CON EL CALENDARIO ---
    df_final = pd.merge(df_cal, agrupado, on="Fecha", how="left").fillna(0)
    
    dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb"}
    df_final['Día'] = df_final.apply(lambda row: f"{dias_esp[row['Día_Semana']]}-{row['Fecha'].strftime('%d-%b')}".lower(), axis=1)

    # --- FORMULAS MATEMÁTICAS APLICADAS (Exactas a tu solicitud) ---
    df_final['Meta Lead Efectivos Programados'] = df_final['meta_asesor'] * df_final['Agentes Plantilla']
    df_final['Meta Lead Efectivos Asistieron'] = df_final['meta_asesor'] * df_final['Agentes Log']
    df_final['Diferencia'] = df_final['Meta Lead Efectivos Programados'] - df_final['Meta Lead Efectivos Asistieron']
    
    df_final['% LE'] = np.where(df_final['Tramites'] > 0, df_final['Lead Efectivo'] / df_final['Tramites'], 0)
    df_final['% REM/RECH'] = np.where(df_final['Tramites'] > 0, df_final['Otros'] / df_final['Tramites'], 0)
    
    df_final['Prom'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Agentes Log'] / df_final['Lead Efectivo'], 0)
    df_final['% Ausentismo'] = np.where(df_final['Agentes Plantilla'] > 0, df_final['Agentes Log'] / df_final['Agentes Plantilla'], 0)
    df_final['SPH'] = np.where(df_final.get('tiempo_real', 0) > 0, df_final['Lead Efectivo'] / df_final['tiempo_real'], 0)
    
    df_final['AP DIA'] = df_final['AP MES'] + df_final['AP COSECHA']
    df_final['AP Acum'] = np.where(df_final['Lead Efectivo'].cumsum() > 0, df_final['AP MES'].cumsum() / df_final['Lead Efectivo'].cumsum(), 0)
    
    df_final['Meta Día'] = df_final.get('meta_dia', 0)
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
