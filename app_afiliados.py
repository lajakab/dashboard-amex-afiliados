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
        if 'fecha_vta' in df.columns:
            df['fecha_vta'] = pd.to_datetime(df['fecha_vta'], errors='coerce')
        if 'fecha_decision' in df.columns:
            df['fecha_decision'] = pd.to_datetime(df['fecha_decision'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"❌ Error al leer Parquet: {e}")
        return pd.DataFrame()

df_raw = cargar_datos()

if not df_raw.empty and 'fecha_vta' in df_raw.columns:
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("🔍 Filtros")
    
    fechas_validas = df_raw['fecha_vta'].dropna()
    años_disp = sorted(fechas_validas.dt.year.unique()) if not fechas_validas.empty else [date.today().year]
    año_sel = st.sidebar.selectbox("Año", años_disp, index=len(años_disp)-1)
    
    meses_disp = sorted(fechas_validas[fechas_validas.dt.year == año_sel].dt.month.unique()) if not fechas_validas.empty else [date.today().month]
    nombres_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    mes_formateado = [nombres_meses[m] for m in meses_disp if m in nombres_meses]
    mes_sel_nombre = st.sidebar.selectbox("Mes", mes_formateado, index=len(mes_formateado)-1) if mes_formateado else "Noviembre"
    mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]

    if 'asesor' in df_raw.columns:
        asesores = ["Todos"] + sorted(df_raw['asesor'].dropna().astype(str).unique().tolist())
        asesor_sel = st.sidebar.selectbox("Asesor", asesores)
        if asesor_sel != "Todos":
            df_raw = df_raw[df_raw['asesor'] == asesor_sel]

    # CALENDARIO HÁBIL
    festivos_mx = holidays.Mexico(years=año_sel)
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    fechas_mes = [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]
    df_cal = pd.DataFrame({"Fecha": fechas_mes})
    df_cal['Fecha'] = pd.to_datetime(df_cal['Fecha'])
    df_cal['Día_Semana'] = df_cal['Fecha'].dt.dayofweek
    df_cal['Es_Festivo'] = df_cal['Fecha'].apply(lambda x: x in festivos_mx)
    df_cal = df_cal[~((df_cal['Día_Semana'] == 6) | (df_cal['Es_Festivo']))].copy()

    # FILTRAR MES
    df_filtro = df_raw[(df_raw['fecha_vta'].dt.year == año_sel) & (df_raw['fecha_vta'].dt.month == mes_sel)].copy()

    if not df_filtro.empty:
        agrupado = df_filtro.groupby(df_filtro['fecha_vta'].dt.normalize()).apply(lambda x: pd.Series({
            'Tramites': len(x),
            'Lead Efectivo': (x.get('estado', pd.Series(dtype=str)) == 'LEAD EFECTIVO').sum(),
            'Lead No Capturado': (x.get('estado', pd.Series(dtype=str)) == 'LEAD NO CAPTURADO').sum(),
            'Lead No Condiciones': (x.get('estado', pd.Series(dtype=str)) == 'LEAD NO CONDICIONES').sum(),
            'Otros': ((x.get('estado', pd.Series(dtype=str)) == 'REMEDIACIÓN') | 
                      (~x.get('estado', pd.Series(dtype=str)).isin(['LEAD EFECTIVO', 'LEAD NO CAPTURADO', 'LEAD NO CONDICIONES', '']))).sum(),
            
            'EVALUADO': (x.get('decision', pd.Series(dtype=str)) != '-').sum(),
            'NO GESTIONADO': (x.get('decision', pd.Series(dtype=str)) == '-').sum(),
            'Declinado': (x.get('decision', pd.Series(dtype=str)) == 'D').sum(),
            'Cancelado': (x.get('decision', pd.Series(dtype=str)) == 'C').sum(),
            'Pendiente': (x.get('decision', pd.Series(dtype=str)) == 'P').sum(),
            
            'AP MES': ((x.get('decision', pd.Series(dtype=str)) == 'A') & (pd.to_datetime(x.get('fecha_decision', pd.Series(dtype=str)), errors='coerce').dt.month == mes_sel)).sum(),
            'AP COSECHA': ((x.get('decision', pd.Series(dtype=str)) == 'A') & (pd.to_datetime(x.get('fecha_decision', pd.Series(dtype=str)), errors='coerce').dt.month != mes_sel)).sum(),
            
            'Agentes Plantilla': x.get('agentes_plantilla', pd.Series([0])).max(),
            'Agentes Log': x.get('agentes_log', pd.Series([0])).max(),
            'Meta Día': x.get('meta_dia', pd.Series([0])).max(),
            'Meta Asesor': x.get('meta_asesor', pd.Series([0])).max(),
            'Tiempo Real': x.get('tiempo_real', pd.Series([0])).max()
        })).reset_index().rename(columns={'fecha_vta': 'Fecha'})
    else:
        agrupado = pd.DataFrame(columns=['Fecha', 'Tramites', 'Lead Efectivo'])

    # UNIR Y CALCULAR
    df_final = pd.merge(df_cal, agrupado, on="Fecha", how="left").fillna(0)
    dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb"}
    df_final['Día'] = df_final.apply(lambda row: f"{dias_esp[row['Día_Semana']]}-{row['Fecha'].strftime('%d-%b')}".lower(), axis=1)

    df_final['Meta Lead Efectivos Programados'] = df_final.get('Meta Asesor', 0) * df_final.get('Agentes Plantilla', 0)
    df_final['Meta Lead Efectivos Asistieron'] = df_final.get('Meta Asesor', 0) * df_final.get('Agentes Log', 0)
    df_final['Diferencia'] = df_final['Meta Lead Efectivos Programados'] - df_final['Meta Lead Efectivos Asistieron']
    
    df_final['% LE'] = np.where(df_final.get('Tramites', 0) > 0, df_final.get('Lead Efectivo', 0) / df_final.get('Tramites', 1), 0)
    df_final['% REM/RECH'] = np.where(df_final.get('Tramites', 0) > 0, df_final.get('Otros', 0) / df_final.get('Tramites', 1), 0)
    df_final['Prom'] = np.where(df_final.get('Lead Efectivo', 0) > 0, df_final.get('Agentes Log', 0) / df_final.get('Lead Efectivo', 1), 0)
    df_final['% Ausentismo'] = np.where(df_final.get('Agentes Plantilla', 0) > 0, df_final.get('Agentes Log', 0) / df_final.get('Agentes Plantilla', 1), 0)
    df_final['SPH'] = np.where(df_final.get('Tiempo Real', 0) > 0, df_final.get('Lead Efectivo', 0) / df_final.get('Tiempo Real', 1), 0)
    
    df_final['AP DIA'] = df_final.get('AP MES', 0) + df_final.get('AP COSECHA', 0)
    df_final['AP Acum'] = np.where(df_final.get('Lead Efectivo', pd.Series([0])).cumsum() > 0, df_final.get('AP MES', pd.Series([0])).cumsum() / df_final.get('Lead Efectivo', pd.Series([1])).cumsum(), 0)
    df_final['GAP'] = df_final.get('Meta Día', pd.Series([0])).cumsum() - df_final.get('Lead Efectivo', pd.Series([0])).cumsum()
    
    df_final['% EVALUADO'] = np.where(df_final.get('Lead Efectivo', 0) > 0, df_final.get('EVALUADO', 0) / df_final.get('Lead Efectivo', 1), 0)
    df_final['% Declinado'] = np.where(df_final.get('Lead Efectivo', 0) > 0, df_final.get('Declinado', 0) / df_final.get('Lead Efectivo', 1), 0)
    df_final['% Cancelado'] = np.where(df_final.get('Lead Efectivo', 0) > 0, df_final.get('Cancelado', 0) / df_final.get('Lead Efectivo', 1), 0)
    df_final['% Pendiente'] = np.where(df_final.get('Lead Efectivo', 0) > 0, df_final.get('Pendiente', 0) / df_final.get('Lead Efectivo', 1), 0)

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
    k1.metric("Trámites Totales", f"{int(df_vista.get('Tramites', pd.Series([0])).sum())}")
    k2.metric("Leads Efectivos", f"{int(df_vista.get('Lead Efectivo', pd.Series([0])).sum())}")
    k3.metric("GAP Acumulado", f"{int(df_vista.get('GAP', pd.Series([0])).iloc[-1]) if not df_vista.empty else 0}")
    k4.metric("AP Mes (Total)", f"{int(df_vista.get('AP MES', pd.Series([0])).sum())}")
    
    st.divider()

    def semaforo_le(val):
        if not isinstance(val, (float, int)): return ''
        if val >= 0.90: return 'background-color: #c6e0b4; color: black;'
        if val >= 0.80: return 'background-color: #ffe699; color: black;'
        if val > 0: return 'background-color: #ffc000; color: black;'
        return ''

    # Aseguramos el formato visual para que no salgan decimal
