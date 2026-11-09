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

st.set_page_config(page_title="Informe Gerencial Amex", layout="wide")

@st.cache_data
def cargar_datos():
    try:
        df = pd.read_parquet(ARCHIVO_DATOS)
        # Normalizar nombres de columnas a minúsculas
        df.columns = [str(c).strip().lower() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"❌ Error al leer el archivo Parquet: {e}")
        return pd.DataFrame()

df_raw = cargar_datos()

if not df_raw.empty:
    # --- BARRA LATERAL (FILTROS) ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("🔍 Filtros Gerenciales")
    
    # Buscar columna de fecha de venta
    col_fecha = next((c for c in ['fecha_vta', 'fecha', 'fecha_reporte'] if c in df_raw.columns), None)
    
    if col_fecha:
        df_raw[col_fecha] = pd.to_datetime(df_raw[col_fecha], errors='coerce').dt.date
        fechas_validas = df_raw[col_fecha].dropna()
        
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
            
        # Filtro de Asesor si existe
        col_asesor = next((c for c in ['asesor', 'user', 'nombre_asesor'] if c in df_raw.columns), None)
        if col_asesor:
            asesores = ["Todos"] + sorted(df_raw[col_asesor].dropna().astype(str).unique().tolist())
            asesor_sel = st.sidebar.selectbox("Asesor", asesores)
            if asesor_sel != "Todos":
                df_raw = df_raw[df_raw[col_asesor].astype(str) == asesor_sel]
    else:
        st.error("No se encontró ninguna columna de fecha en el archivo Parquet.")
        st.stop()

    # --- CALENDARIO HÁBIL (Lunes a Sábado, sin festivos México) ---
    festivos_mx = holidays.Mexico(years=año_sel)
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    
    fechas_mes = [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]
    df_cal = pd.DataFrame({"Fecha": fechas_mes})
    df_cal['Día_Semana'] = pd.to_datetime(df_cal['Fecha']).dt.dayofweek
    df_cal['Es_Festivo'] = df_cal['Fecha'].apply(lambda x: x in festivos_mx)
    df_cal = df_cal[~((df_cal['Día_Semana'] == 6) | (df_cal['Es_Festivo']))]

    # --- FILTRAR DATOS DEL MES ---
    df_filtro = df_raw[(df_raw[col_fecha].apply(lambda x: getattr(x, 'year', 0)) == año_sel) & 
                       (df_filtro_mes := df_raw[col_fecha].apply(lambda x: getattr(x, 'month', 0)) == mes_sel)].copy()

    col_estado = next((c for c in ['estado', 'status', 'tipificacion'] if c in df_filtro.columns), None)
    col_decision = next((c for c in ['decision', 'dec', 'estado_decision'] if c in df_filtro.columns), None)
    col_fec_dec = next((c for c in ['fecha_decision', 'fec_decision'] if c in df_filtro.columns), None)

    # Agrupación diaria
    if not df_filtro.empty and col_estado:
        agrupado = df_filtro.groupby(col_fecha).apply(lambda x: pd.Series({
            'Tramites': len(x),
            'Lead Efectivo': (x[col_estado].astype(str).str.upper() == 'LEAD EFECTIVO').sum(),
            'Lead No Capturado': (x[col_estado].astype(str).str.upper() == 'LEAD NO CAPTURADO').sum(),
            'Lead No Condiciones': (x[col_estado].astype(str).str.upper() == 'LEAD NO CONDICIONES').sum(),
            'Otros': ((x[col_estado].astype(str).str.upper() == 'REMEDIACIÓN') | 
                      (~x[col_estado].astype(str).str.upper().isin(['LEAD EFECTIVO', 'LEAD NO CAPTURADO', 'LEAD NO CONDICIONES', '']))).sum(),
            
            'EVALUADO': (x[col_decision].astype(str) != '-').sum() if col_decision else 0,
            'NO GESTIONADO': (x[col_decision].astype(str) == '-').sum() if col_decision else 0,
            'Declinado': (x[col_decision].astype(str).str.upper() == 'D').sum() if col_decision else 0,
            'Cancelado': (x[col_decision].astype(str).str.upper() == 'C').sum() if col_decision else 0,
            'Pendiente': (x[col_decision].astype(str).str.upper() == 'P').sum() if col_decision else 0,
            
            'AP MES': ((x[col_decision].astype(str).str.upper() == 'A') & (pd.to_datetime(x[col_fec_dec], errors='coerce').dt.month == mes_sel)).sum() if (col_decision and col_fec_dec) else 0,
            'AP COSECHA': ((x[col_decision].astype(str).str.upper() == 'A') & (pd.to_datetime(x[col_fec_dec], errors='coerce').dt.month != mes_sel)).sum() if (col_decision and col_fec_dec) else 0,
            
            'agentes_log': x['agentes_log'].mean() if 'agentes_log' in x.columns else 1,
            'agentes_plantilla': x['agentes_plantilla'].mean() if 'agentes_plantilla' in x.columns else 1,
            'meta_asesor': x['meta_asesor'].mean() if 'meta_asesor' in x.columns else 0,
            'meta_dia': x['meta_dia'].mean() if 'meta_dia' in x.columns else 0,
            'tiempo_real': x['tiempo_real'].sum() if 'tiempo_real' in x.columns else 1
        })).reset_index()
    else:
        agrupado = pd.DataFrame(columns=[col_fecha, 'Tramites', 'Lead Efectivo'])

    df_final = pd.merge(df_cal, agrupado, left_on="Fecha", right_on=col_fecha, how="left").fillna(0)
    
    dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb"}
    df_final['Día'] = df_final.apply(lambda row: f"{dias_esp[row['Día_Semana']]}-{row['Fecha'].strftime('%d-%b')}".lower(), axis=1)

    # --- CÁLCULO DE FÓRMULAS ---
    df_final['Meta Lead Efectivos Programados'] = df_final.get('meta_asesor', 0) * df_final.get('agentes_plantilla', 0)
    df_final['Meta Lead Efectivos Asistieron'] = df_final.get('meta_asesor', 0) * df_final.get('agentes_log', 0)
    df_final['Diferencia'] = df_final['Meta Lead Efectivos Programados'] - df_final['Meta Lead Efectivos Asistieron']
    
    df_final['% LE'] = np.where(df_final['Tramites'] > 0, df_final['Lead Efectivo'] / df_final['Tramites'], 0)
    df_final['% REM/RECH'] = np.where(df_final['Tramites'] > 0, df_final['Otros'] / df_final['Tramites'], 0)
    df_final['Prom'] = np.where(df_final.get('agentes_log', 0) > 0, df_final['Lead Efectivo'] / df_final.get('agentes_log', 1), 0)
    df_final['% Ausentismo'] = np.where(df_final.get('agentes_plantilla', 0) > 0, (df_final.get('agentes_plantilla', 0) - df_final.get('agentes_log', 0)) / df_final.get('agentes_plantilla', 1), 0)
    df_final['SPH'] = np.where(df_final.get('tiempo_real', 0) > 0, df_final['Lead Efectivo'] / df_final.get('tiempo_real', 1), 0)
    
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
        'agentes_log', 'agentes_plantilla', '% Ausentismo', 'SPH', 
        'AP MES', 'AP COSECHA', 'AP DIA', 'AP Acum', 'Meta Día', 'GAP',
        'EVALUADO', '% EVALUADO', 'NO GESTIONADO', 
        'Declinado', '% Declinado', 'Cancelado', '% Cancelado', 'Pendiente', '% Pendiente'
    ]
    
    df_vista = df_final[[c for c in columnas_vista if c in df_final.columns]].copy()
    df_vista.rename(columns={'agentes_log': 'Agentes Log', 'agentes_plantilla': 'Agentes Plantilla'}, inplace=True)

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

    # Actualizado de applymap a map para compatibilidad con Pandas modernos
    styler = df_vista.style.format({col: '{:.0f}' for col in df_vista.columns if '%' not in col and col != 'Día'})\
                           .format({col: '{:.1%}' for col in df_vista.columns if '%' in col})\
                           .map(semaforo_le, subset=['% LE'] if '% LE' in df_vista.columns else [])\
                           .set_properties(**{'text-align': 'center', 'font-size': '12px'})

    st.dataframe(styler, use_container_width=True, height=600, hide_index=True)
else:
    st.warning("⚠️ No se encontraron datos. Ejecuta tu script local para sincronizar la información.")
