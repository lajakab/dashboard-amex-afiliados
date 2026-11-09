import streamlit as st
import pandas as pd
import numpy as np
import holidays
from datetime import date
import calendar

# ==========================================
# ⚙️ CONFIGURACIÓN DE HOJAS Y COLUMNAS
# ==========================================
# Nombre de tu archivo en GitHub
ARCHIVO_DATOS = "Amex_Afiliados.xlsx" 

# 1. HOJA DE VENTAS
HOJA_VENTAS = "Ventas"
C_V_FECHA = "fecha_vta"       # Columna E 
C_V_ESTADO = "estado"         # Columna H 
C_V_DECISION = "decision"     # Columna AT 
C_V_FECHA_DEC = "fecha_decision" 
C_V_ASESOR = "asesor"         

# 2. HOJA DE PLANTA
HOJA_PLANTA = "planta"
C_P_FECHA = "fecha"           # Columna con la fecha del día
C_P_PLANTILLA = "agentes_plantilla" # Columna B
C_P_LOG = "agentes_log"             # Columna C

# 3. HOJA SEG PPTO
HOJA_PPTO = "Seg PPTO"
C_S_FECHA = "fecha"           # Columna AJ
C_S_META_DIA = "meta_dia"     # Columna AK
C_S_META_ASESOR = "meta_asesor" # Columna AL (Meta diaria por asesor)

# 4. HOJA MALLA DÍA
HOJA_MALLA = "Malla Día"
C_M_FECHA = "fecha"           # Columna N
C_M_TIEMPO = "tiempo_real"    # Columna Tiempo Real

# TEXTOS EXACTOS DE LOS ESTADOS
TXT_LE = "LEAD EFECTIVO"
TXT_LNC = "LEAD NO CAPTURADO"
TXT_LNC_COND = "LEAD NO CONDICIONES"
TXT_REMED = "REMEDIACIÓN"
# ==========================================

st.set_page_config(page_title="Informe Gerencial Amex", layout="wide")

# --- 1. CARGA DE DATOS MULTI-HOJA ---
@st.cache_data
def cargar_excel():
    try:
        xls = pd.ExcelFile(ARCHIVO_DATOS)
        df_ventas = pd.read_excel(xls, HOJA_VENTAS)
        df_planta = pd.read_excel(xls, HOJA_PLANTA)
        df_ppto = pd.read_excel(xls, HOJA_PPTO)
        df_malla = pd.read_excel(xls, HOJA_MALLA)
        
        # Asegurar formatos de fecha para poder cruzarlos
        df_ventas[C_V_FECHA] = pd.to_datetime(df_ventas[C_V_FECHA], errors='coerce').dt.date
        df_ventas[C_V_FECHA_DEC] = pd.to_datetime(df_ventas[C_V_FECHA_DEC], errors='coerce').dt.date
        df_planta[C_P_FECHA] = pd.to_datetime(df_planta[C_P_FECHA], errors='coerce').dt.date
        df_ppto[C_S_FECHA] = pd.to_datetime(df_ppto[C_S_FECHA], errors='coerce').dt.date
        df_malla[C_M_FECHA] = pd.to_datetime(df_malla[C_M_FECHA], errors='coerce').dt.date
        
        return df_ventas, df_planta, df_ppto, df_malla
    except Exception as e:
        st.error(f"❌ Error al leer el Excel: {e}")
        return None, None, None, None

df_ventas, df_planta, df_ppto, df_malla = cargar_excel()

if df_ventas is not None:
    # --- 2. FILTROS LATERALES ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("🔍 Filtros")
    
    fechas_validas = df_ventas[C_V_FECHA].dropna()
    años_disp = sorted(fechas_validas.apply(lambda x: x.year).unique()) if not fechas_validas.empty else [date.today().year]
    año_sel = st.sidebar.selectbox("Año", años_disp, index=len(años_disp)-1)
    
    meses_disp = sorted(fechas_validas[fechas_validas.apply(lambda x: x.year) == año_sel].apply(lambda x: x.month).unique())
    nombres_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    mes_formateado = [nombres_meses[m] for m in meses_disp]
    mes_sel_nombre = st.sidebar.selectbox("Mes", mes_formateado, index=len(mes_formateado)-1)
    mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]

    # --- 3. CALENDARIO HÁBIL ---
    festivos_mx = holidays.Mexico(years=año_sel)
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    
    fechas_mes = [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]
    df_cal = pd.DataFrame({"Fecha": fechas_mes})
    df_cal['Día_Semana'] = pd.to_datetime(df_cal['Fecha']).dt.dayofweek
    df_cal['Es_Festivo'] = df_cal['Fecha'].apply(lambda x: x in festivos_mx)
    df_cal = df_cal[~((df_cal['Día_Semana'] == 6) | (df_cal['Es_Festivo']))] # Sin domingos ni festivos

    # --- 4. PREPARAR HOJAS AUXILIARES ---
    # Agrupamos por día para cruzar fácilmente con el calendario
    try:
        planta_agg = df_planta.groupby(C_P_FECHA).agg({C_P_PLANTILLA: 'sum', C_P_LOG: 'sum'}).reset_index()
        ppto_agg = df_ppto.groupby(C_S_FECHA).agg({C_S_META_DIA: 'sum', C_S_META_ASESOR: 'mean'}).reset_index()
        malla_agg = df_malla.groupby(C_M_FECHA).agg({C_M_TIEMPO: 'sum'}).reset_index()
    except KeyError as e:
        st.error(f"❌ Falta una columna en las hojas secundarias (planta, Seg PPTO o Malla Día). Columna no encontrada: {e}")
        st.stop()

    # --- 5. AGRUPACIÓN DE VENTAS ---
    df_filtro = df_ventas[(df_ventas[C_V_FECHA].apply(lambda x: getattr(x, 'year', 0)) == año_sel) & 
                          (df_ventas[C_V_FECHA].apply(lambda x: getattr(x, 'month', 0)) == mes_sel)]
    
    try:
        ventas_agg = df_filtro.groupby(C_V_FECHA).apply(lambda x: pd.Series({
            'Tramites': len(x),
            'Lead Efectivo': (x[C_V_ESTADO] == TXT_LE).sum(),
            'Lead No Capturado': (x[C_V_ESTADO] == TXT_LNC).sum(),
            'Lead No Condiciones': (x[C_V_ESTADO] == TXT_LNC_COND).sum(),
            'Otros': (x[C_V_ESTADO] == TXT_REMED).sum(),
            'EVALUADO': (x[C_V_DECISION] != "-").sum(),
            'NO GESTIONADO': (x[C_V_DECISION] == "-").sum(),
            'Declinado': (x[C_V_DECISION] == "D").sum(),
            'Cancelado': (x[C_V_DECISION] == "C").sum(),
            'Pendiente': (x[C_V_DECISION] == "P").sum(),
            'AP MES': ((x[C_V_DECISION] == "A") & (pd.to_datetime(x[C_V_FECHA_DEC]).dt.month == mes_sel)).sum(),
            'AP COSECHA': ((x[C_V_DECISION] == "A") & (pd.to_datetime(x[C_V_FECHA_DEC]).dt.month != mes_sel)).sum()
        })).reset_index()
    except KeyError as e:
        st.error(f"❌ Falta una columna en la hoja 'Ventas'. No se encontró: {e}")
        st.stop()

    # --- 6. UNIFICAR TODA LA INFORMACIÓN (El MEGA CRUCE) ---
    df_final = pd.merge(df_cal, ventas_agg, left_on="Fecha", right_on=C_V_FECHA, how="left")
    df_final = pd.merge(df_final, planta_agg, left_on="Fecha", right_on=C_P_FECHA, how="left")
    df_final = pd.merge(df_final, ppto_agg, left_on="Fecha", right_on=C_S_FECHA, how="left")
    df_final = pd.merge(df_final, malla_agg, left_on="Fecha", right_on=C_M_FECHA, how="left").fillna(0)

    # Nombres de días en español
    dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb"}
    df_final['Día'] = df_final.apply(lambda row: f"{dias_esp[row['Día_Semana']]}-{row['Fecha'].strftime('%d-%b')}".lower(), axis=1)

    # --- 7. CÁLCULO DE FÓRMULAS ---
    df_final['Meta Lead Efectivos Programados'] = df_final[C_S_META_ASESOR] * df_final[C_P_PLANTILLA]
    df_final['Meta Lead Efectivos Asistieron'] = df_final[C_S_META_ASESOR] * df_final[C_P_LOG]
    df_final['Diferencia'] = df_final['Meta Lead Efectivos Programados'] - df_final['Meta Lead Efectivos Asistieron']
    
    df_final['% LE'] = np.where(df_final['Tramites'] > 0, df_final['Lead Efectivo'] / df_final['Tramites'], 0)
    df_final['% REM/RECH'] = np.where(df_final['Tramites'] > 0, df_final['Otros'] / df_final['Tramites'], 0)
    df_final['Prom'] = np.where(df_final[C_P_LOG] > 0, df_final['Lead Efectivo'] / df_final[C_P_LOG], 0)
    df_final['% Ausentismo'] = np.where(df_final[C_P_PLANTILLA] > 0, (df_final[C_P_PLANTILLA] - df_final[C_P_LOG]) / df_final[C_P_PLANTILLA], 0)
    df_final['SPH'] = np.where(df_final[C_M_TIEMPO] > 0, df_final['Lead Efectivo'] / df_final[C_M_TIEMPO], 0)
    
    df_final['AP DIA'] = df_final['AP MES'] + df_final['AP COSECHA']
    df_final['AP Acum'] = np.where(df_final['Lead Efectivo'].cumsum() > 0, df_final['AP MES'].cumsum() / df_final['Lead Efectivo'].cumsum(), 0)
    df_final['GAP'] = df_final[C_S_META_DIA].cumsum() - df_final['Lead Efectivo'].cumsum()
    
    df_final['% EVALUADO'] = np.where(df_final['Lead Efectivo'] > 0, df_final['EVALUADO'] / df_final['Lead Efectivo'], 0)
    df_final['% Declinado'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Declinado'] / df_final['Lead Efectivo'], 0)
    df_final['% Cancelado'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Cancelado'] / df_final['Lead Efectivo'], 0)
    df_final['% Pendiente'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Pendiente'] / df_final['Lead Efectivo'], 0)

    # Renombrar columnas finales para que queden exactas como las pides
    df_final.rename(columns={
        C_P_LOG: 'Agentes Log', 
        C_P_PLANTILLA: 'Agentes Plantilla',
        C_S_META_DIA: 'Meta Día'
    }, inplace=True)

    columnas_vista = [
        'Día', 'Tramites', 'Lead Efectivo', 'Meta Lead Efectivos Programados', 'Meta Lead Efectivos Asistieron', 'Diferencia',
        'Lead No Capturado', 'Lead No Condiciones', 'Otros', '% LE', '% REM/RECH', 'Prom',
        'Agentes Log', 'Agentes Plantilla', '% Ausentismo', 'SPH', 
        'AP MES', 'AP COSECHA', 'AP DIA', 'AP Acum', 'Meta Día', 'GAP',
        'EVALUADO', '% EVALUADO', 'NO GESTIONADO', 
        'Declinado', '% Declinado', 'Cancelado', '% Cancelado', 'Pendiente', '% Pendiente'
    ]
    df_vista = df_final[columnas_vista].copy()

    # --- 8. INTERFAZ GRÁFICA ---
    st.title(f"📊 Informe Gerencial - {mes_sel_nombre} {año_sel}")
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Trámites Totales", f"{int(df_vista['Tramites'].sum())}")
    k2.metric("Leads Efectivos", f"{int(df_vista['Lead Efectivo'].sum())}")
    k3.metric("GAP Acumulado", f"{int(df_vista['GAP'].iloc[-1]) if not df_vista.empty else 0}")
    k4.metric("AP Mes (Total)", f"{int(df_vista['AP MES'].sum())}")
    
    st.divider()

    def estilo_celdas(val):
        if isinstance(val, (int, float)) and val < 0: return 'color: red;'
        return ''
        
    def semaforo(val):
        if not isinstance(val, float): return ''
        if val >= 0.90: return 'background-color: #c6e0b4; color: black;'
        if val >= 0.80: return 'background-color: #ffe699; color: black;'
        if val > 0: return 'background-color: #ffc000; color: black;'
        return ''

    styler = df_vista.style.format({col: '{:.0f}' for col in df_vista.columns if '%' not in col and col != 'Día'})\
                           .format({col: '{:.1%}' for col in df_vista.columns if '%' in col})\
                           .applymap(estilo_celdas, subset=['GAP', 'Diferencia'])\
                           .applymap(semaforo, subset=['% LE'])\
                           .set_properties(**{'text-align': 'center', 'font-size': '12px'})
      
    st.dataframe(styler, use_container_width=True, height=600, hide_index=True)
else:
    st.warning("Cargando la aplicación... Si esto persiste, verifica que el archivo 'Amex_Afiliados.xlsx' esté en tu repositorio.")
