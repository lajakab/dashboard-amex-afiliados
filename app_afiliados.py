import streamlit as st
import pandas as pd
import numpy as np
import holidays
from datetime import date
import calendar

ARCHIVO_DATOS = "Amex_Afiliados.parquet"

st.set_page_config(page_title="Informe Gerencial Amex", layout="wide")

@st.cache_data
def cargar_datos():
    try:
        df = pd.read_parquet(ARCHIVO_DATOS)
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"❌ Error al leer el archivo Parquet: {e}")
        return pd.DataFrame()

df_raw = cargar_datos()

if not df_raw.empty:
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("🔍 Filtros Gerenciales")
    
    # Detectar dinámicamente la columna de fecha
    col_fecha = next((c for c in ['fecha', 'fecha_vta', 'fecha_reporte', 'index'] if c in df_raw.columns), df_raw.columns[0])

    if col_fecha in df_raw.columns:
        df_raw[col_fecha] = pd.to_datetime(df_raw[col_fecha], errors='coerce')
        fechas_validas = df_raw[col_fecha].dropna()
        
        años_disp = sorted(fechas_validas.dt.year.unique()) if not fechas_validas.empty else [date.today().year]
        año_sel = st.sidebar.selectbox("Año", años_disp, index=len(años_disp)-1)
        
        meses_disp = sorted(fechas_validas[fechas_validas.dt.year == año_sel].dt.month.unique()) if not fechas_validas.empty else [date.today().month]
        nombres_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
        mes_formateado = [nombres_meses[m] for m in meses_disp if m in nombres_meses]
        
        mes_sel_nombre = st.sidebar.selectbox("Mes", mes_formateado, index=len(mes_formateado)-1) if mes_formateado else "Noviembre"
        mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]
    else:
        año_sel, mes_sel, mes_sel_nombre = 2026, 11, "Noviembre"

    # Filtrar mes y año de manera segura
    df_mes = df_raw[(df_raw[col_fecha].dt.year == año_sel) & 
                    (df_raw[col_fecha].dt.month == mes_sel)].copy()

    # Formatear la columna Día (ej. lun-02-nov)
    dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb"}
    df_mes['Día_Semana'] = df_mes[col_fecha].dt.dayofweek
    df_mes['Día'] = df_mes.apply(lambda row: f"{dias_esp.get(row['Día_Semana'], 'lun')}-{row[col_fecha].strftime('%d-%b')}".lower(), axis=1)

    # --- CÁLCULO DE FÓRMULAS ---
    df_mes['Meta Lead Efectivos Programados'] = df_mes.get('meta_asesor', 0) * df_mes.get('agentes_plantilla', 0)
    df_mes['Meta Lead Efectivos Asistieron'] = df_mes.get('meta_asesor', 0) * df_mes.get('agentes_log', 0)
    df_mes['Diferencia'] = df_mes['Meta Lead Efectivos Programados'] - df_mes['Meta Lead Efectivos Asistieron']
    
    df_mes['% LE'] = np.where(df_mes.get('tramites', 0) > 0, df_mes.get('lead_efectivo', 0) / df_mes['tramites'], 0)
    df_mes['% REM/RECH'] = np.where(df_mes.get('tramites', 0) > 0, df_mes.get('otros', 0) / df_mes['tramites'], 0)
    df_mes['Prom'] = np.where(df_mes.get('agentes_log', 0) > 0, df_mes.get('lead_efectivo', 0) / df_mes['agentes_log'], 0)
    df_mes['% Ausentismo'] = np.where(df_mes.get('agentes_plantilla', 0) > 0, (df_mes['agentes_plantilla'] - df_mes.get('agentes_log', 0)) / df_mes['agentes_plantilla'], 0)
    df_mes['SPH'] = np.where(df_mes.get('tiempo_real', 0) > 0, df_mes.get('lead_efectivo', 0) / df_mes['tiempo_real'], 0)
    
    df_mes['AP DIA'] = df_mes.get('ap_mes', 0) + df_mes.get('ap_cosecha', 0)
    df_mes['AP Acum'] = np.where(df_mes.get('lead_efectivo', 0).cumsum() > 0, df_mes.get('ap_mes', 0).cumsum() / df_mes['lead_efectivo'].cumsum(), 0)
    df_mes['Meta Día'] = 279 
    df_mes['GAP'] = df_mes['Meta Día'].cumsum() - df_mes.get('lead_efectivo', 0).cumsum()
    
    df_mes['% EVALUADO'] = np.where(df_mes.get('lead_efectivo', 0) > 0, df_mes.get('evaluado', 0) / df_mes['lead_efectivo'], 0)
    df_mes['% Declinado'] = np.where(df_mes.get('lead_efectivo', 0) > 0, df_mes.get('declinado', 0) / df_mes['lead_efectivo'], 0)
    df_mes['% Cancelado'] = np.where(df_mes.get('lead_efectivo', 0) > 0, df_mes.get('cancelado', 0) / df_mes['lead_efectivo'], 0)
    df_mes['% Pendiente'] = np.where(df_mes.get('lead_efectivo', 0) > 0, df_mes.get('pendiente', 0) / df_mes['lead_efectivo'], 0)

    renombres = {
        'tramites': 'Tramites', 'lead_efectivo': 'Lead Efectivo', 
        'lead_no_capturado': 'Lead No Capturado', 'lead_no_condiciones': 'Lead No Condiciones',
        'otros': 'Otros', 'agentes_log': 'Agentes Log', 'agentes_plantilla': 'Agentes Plantilla',
        'ap_mes': 'AP MES', 'ap_cosecha': 'AP COSECHA', 'evaluado': 'EVALUADO',
        'no_gestionado': 'NO GESTIONADO', 'declinado': 'Declinado', 
        'cancelado': 'Cancelado', 'pendiente': 'Pendiente'
    }
    df_mes.rename(columns=renombres, inplace=True)

    columnas_vista = [
        'Día', 'Tramites', 'Lead Efectivo', 'Meta Lead Efectivos Programados', 'Meta Lead Efectivos Asistieron', 'Diferencia',
        'Lead No Capturado', 'Lead No Condiciones', 'Otros', '% LE', '% REM/RECH', 'Prom',
        'Agentes Log', 'Agentes Plantilla', '% Ausentismo', 'SPH', 
        'AP MES', 'AP COSECHA', 'AP DIA', 'AP Acum', 'Meta Día', 'GAP',
        'EVALUADO', '% EVALUADO', 'NO GESTIONADO', 
        'Declinado', '% Declinado', 'Cancelado', '% Cancelado', 'Pendiente', '% Pendiente'
    ]
    
    df_vista = df_mes[[c for c in columnas_vista if c in df_mes.columns]].copy()

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
    st.warning("⚠️ No se encontraron datos. Ejecuta tu script local para sincronizar la información.")
