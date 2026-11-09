import streamlit as st
import pandas as pd
import numpy as np
import holidays
from datetime import date
import calendar

# ==========================================
# ⚙️ CONFIGURACIÓN DE COLUMNAS (EL CEREBRO DEL DASHBOARD)
# ==========================================
# Como el Parquet es una sola tabla plana, aquí le decimos a Python 
# cómo se llaman exactamente tus columnas en el archivo. ¡Ajusta los nombres a la derecha!
ARCHIVO_DATOS = "Amex_Afiliados.parquet"

# NOMBRES DE TUS COLUMNAS EN EL PARQUET
C_FECHA_VTA = "fecha_vta"              # Columna E de Ventas
C_ESTADO = "estado"                    # Columna H de Ventas (LEAD EFECTIVO, etc)
C_DECISION = "estado_decision"         # Columna AT (A, D, C, P, -)
C_FECHA_DECISION = "fecha_decision"    # Fecha en la que se tomó la decisión
C_ASESOR = "asesor"                    # Nombre o ID del asesor
C_TIEMPO_REAL = "tiempo_real"          # Tiempo real de la hoja Malla Día
C_PLANTILLA = "agentes_plantilla"      # Agentes programados
C_LOG = "agentes_log"                  # Agentes que asistieron
C_META_ASESOR = "meta_asesor"          # Meta diaria por asesor (hoja Seg PPTO)
C_META_DIA = "meta_dia"                # Meta total del día (hoja Seg PPTO)

# TEXTOS EXACTOS DE LOS ESTADOS (Respeta mayúsculas)
TXT_LE = "LEAD EFECTIVO"
TXT_LNC = "LEAD NO CAPTURADO"
TXT_LNC_COND = "LEAD NO CONDICIONES"
TXT_REMED = "REMEDIACIÓN"
# ==========================================

st.set_page_config(page_title="Informe Gerencial Amex", layout="wide")

# --- 1. CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_parquet(ARCHIVO_DATOS)
        # Asegurar formatos de fecha
        if C_FECHA_VTA in df.columns:
            df[C_FECHA_VTA] = pd.to_datetime(df[C_FECHA_VTA]).dt.date
        if C_FECHA_DECISION in df.columns:
            df[C_FECHA_DECISION] = pd.to_datetime(df[C_FECHA_DECISION]).dt.date
        return df
    except Exception as e:
        return pd.DataFrame() # Retorna vacío si hay error

df_raw = cargar_datos()

if df_raw.empty:
    st.error(f"No se pudo leer el archivo Parquet o está vacío. Revisa que exista: {ARCHIVO_DATOS}")
else:
    # --- 2. FILTROS LATERALES ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("🔍 Filtros")
    
    # Filtro Año y Mes
    años_disp = sorted(df_raw[C_FECHA_VTA].dropna().apply(lambda x: x.year).unique()) if C_FECHA_VTA in df_raw.columns else [date.today().year]
    año_sel = st.sidebar.selectbox("Año", años_disp, index=len(años_disp)-1)
    
    meses_disp = sorted(df_raw[df_raw[C_FECHA_VTA].apply(lambda x: x.year) == año_sel][C_FECHA_VTA].dropna().apply(lambda x: x.month).unique())
    nombres_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    mes_formateado = [nombres_meses[m] for m in meses_disp]
    mes_sel_nombre = st.sidebar.selectbox("Mes", mes_formateado, index=len(mes_formateado)-1)
    mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]
    
    # Filtro Día y Asesor
    dias_disp = ["Todos"] + sorted(df_raw[(df_raw[C_FECHA_VTA].apply(lambda x: x.year) == año_sel) & (df_raw[C_FECHA_VTA].apply(lambda x: x.month) == mes_sel)][C_FECHA_VTA].dropna().apply(lambda x: x.day).unique().tolist())
    dia_sel = st.sidebar.selectbox("Día Específico", dias_disp)
    
    asesores_disp = ["Todos"] + sorted(df_raw[C_ASESOR].dropna().astype(str).unique().tolist()) if C_ASESOR in df_raw.columns else ["Todos"]
    asesor_sel = st.sidebar.selectbox("Asesor", asesores_disp)

    # --- 3. CALENDARIO LABORAL (SIN DOMINGOS NI FESTIVOS MX) ---
    festivos_mx = holidays.Mexico(years=año_sel)
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    
    # Crear un DataFrame con todos los días del mes
    fechas_mes = [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]
    df_cal = pd.DataFrame({"Fecha": fechas_mes})
    df_cal['Día_Semana'] = pd.to_datetime(df_cal['Fecha']).dt.dayofweek
    df_cal['Es_Festivo'] = df_cal['Fecha'].apply(lambda x: x in festivos_mx)
    
    # Filtrar: Quitar Domingos (6) y Festivos
    df_cal = df_cal[~((df_cal['Día_Semana'] == 6) | (df_cal['Es_Festivo']))]
    
    # --- 4. APLICAR FILTROS A LA BASE DE DATOS ---
    df_filtro = df_raw[(df_raw[C_FECHA_VTA].apply(lambda x: x.year) == año_sel) & (df_raw[C_FECHA_VTA].apply(lambda x: x.month) == mes_sel)].copy()
    if dia_sel != "Todos":
        df_filtro = df_filtro[df_filtro[C_FECHA_VTA].apply(lambda x: x.day) == dia_sel]
    if asesor_sel != "Todos":
        df_filtro = df_filtro[df_filtro[C_ASESOR] == asesor_sel]

    # --- 5. LÓGICA DE AGRUPACIÓN (Los "CONTAR.SI.CONJUNTO" de Python) ---
    # Usamos try-except para que el dashboard no se rompa si falta una columna
    try:
        agrupado = df_filtro.groupby(C_FECHA_VTA).apply(lambda x: pd.Series({
            'Tramites': len(x),
            'Lead Efectivo': (x[C_ESTADO] == TXT_LE).sum(),
            'Lead No Capturado': (x[C_ESTADO] == TXT_LNC).sum(),
            'Lead No Condiciones': (x[C_ESTADO] == TXT_LNC_COND).sum(),
            'Otros': (x[C_ESTADO] == TXT_REMED).sum(), # Aquí puedes sumar otros estados si quieres
            
            # AT: Decisiones
            'EVALUADO': (x[C_DECISION] != "-").sum(),
            'NO GESTIONADO': (x[C_DECISION] == "-").sum(),
            'Declinado': (x[C_DECISION] == "D").sum(),
            'Cancelado': (x[C_DECISION] == "C").sum(),
            'Pendiente': (x[C_DECISION] == "P").sum(),
            
            # AP Mes y Cosecha (Validando la fecha de decisión vs fecha de venta)
            'AP MES': ((x[C_DECISION] == "A") & (pd.to_datetime(x[C_FECHA_DECISION]).dt.month == mes_sel) & (pd.to_datetime(x[C_FECHA_VTA]).dt.month == mes_sel)).sum(),
            'AP COSECHA': ((x[C_DECISION] == "A") & (pd.to_datetime(x[C_FECHA_DECISION]).dt.month == mes_sel) & (pd.to_datetime(x[C_FECHA_VTA]).dt.month != mes_sel)).sum(),
            
            # Datos de otras "hojas" (promedios diarios para no duplicar sumas si hay varias filas por día)
            'Agentes Plantilla': x[C_PLANTILLA].mean() if C_PLANTILLA in x.columns else 0,
            'Agentes Log': x[C_LOG].mean() if C_LOG in x.columns else 0,
            'Meta Día': x[C_META_DIA].mean() if C_META_DIA in x.columns else 0,
            'Tiempo Real': x[C_TIEMPO_REAL].sum() if C_TIEMPO_REAL in x.columns else 0,
            'Meta Asesor': x[C_META_ASESOR].mean() if C_META_ASESOR in x.columns else 0
        })).reset_index()

        # Unir calendario oficial hábil con los datos agrupados
        df_final = pd.merge(df_cal, agrupado, left_on="Fecha", right_on=C_FECHA_VTA, how="left").fillna(0)
        
        # Formatear el nombre del día
        dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb"}
        df_final['Día'] = df_final.apply(lambda row: f"{dias_esp[row['Día_Semana']]}-{row['Fecha'].strftime('%d-%b')}".lower(), axis=1)

        # --- 6. CÁLCULO DE FÓRMULAS COMPLEJAS ---
        # Metas y Diferencias
        df_final['Meta Lead Efectivos Programados'] = df_final['Meta Asesor'] * df_final['Agentes Plantilla']
        df_final['Meta Lead Efectivos Asistieron'] = df_final['Meta Asesor'] * df_final['Agentes Log']
        df_final['Diferencia'] = df_final['Meta Lead Efectivos Programados'] - df_final['Meta Lead Efectivos Asistieron']
        
        # Porcentajes (Usamos np.where para evitar división por cero)
        df_final['% LE'] = np.where(df_final['Tramites'] > 0, df_final['Lead Efectivo'] / df_final['Tramites'], 0)
        df_final['% REM/RECH'] = np.where(df_final['Tramites'] > 0, df_final['Otros'] / df_final['Tramites'], 0)
        
        # Promedios y SPH
        df_final['Prom'] = np.where(df_final['Agentes Log'] > 0, df_final['Lead Efectivo'] / df_final['Agentes Log'], 0)
        df_final['% Ausentismo'] = np.where(df_final['Agentes Plantilla'] > 0, (df_final['Agentes Plantilla'] - df_final['Agentes Log']) / df_final['Agentes Plantilla'], 0)
        df_final['SPH'] = np.where(df_final['Tiempo Real'] > 0, df_final['Lead Efectivo'] / df_final['Tiempo Real'], 0)
        
        # Acumulados y GAPs
        df_final['AP DIA'] = df_final['AP MES'] + df_final['AP COSECHA']
        df_final['AP Acum'] = np.where(df_final['Lead Efectivo'].cumsum() > 0, df_final['AP MES'].cumsum() / df_final['Lead Efectivo'].cumsum(), 0)
        df_final['GAP'] = df_final['Meta Día'].cumsum() - df_final['Lead Efectivo'].cumsum()
        
        # Evaluaciones
        df_final['% EVALUADO'] = np.where(df_final['Lead Efectivo'] > 0, df_final['EVALUADO'] / df_final['Lead Efectivo'], 0)
        df_final['% Declinado'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Declinado'] / df_final['Lead Efectivo'], 0)
        df_final['% Cancelado'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Cancelado'] / df_final['Lead Efectivo'], 0)
        df_final['% Pendiente'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Pendiente'] / df_final['Lead Efectivo'], 0)

        # Ordenar Columnas de Vista
        columnas_finales = [
            'Día', 'Tramites', 'Lead Efectivo', 'Meta Lead Efectivos Programados', 'Meta Lead Efectivos Asistieron', 'Diferencia',
            'Lead No Capturado', 'Lead No Condiciones', 'Otros', '% LE', '% REM/RECH', 'Prom',
            'Agentes Log', 'Agentes Plantilla', '% Ausentismo', 'SPH', 
            'AP MES', 'AP COSECHA', 'AP DIA', 'AP Acum', 'Meta Día', 'GAP',
            'EVALUADO', '% EVALUADO', 'NO GESTIONADO', 
            'Declinado', '% Declinado', 'Cancelado', '% Cancelado', 'Pendiente', '% Pendiente'
        ]
        df_vista = df_final[columnas_finales].copy()

        # --- 7. INTERFAZ GRÁFICA DEL DASHBOARD ---
        st.title(f"📊 Informe Gerencial - {mes_sel_nombre} {año_sel}")
        st.markdown(f"**Días Hábiles del Mes:** {len(df_cal)} días (Excluye domingos y festivos México)")
        
        # KPIs Superiores
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Trámites Totales", f"{int(df_vista['Tramites'].sum())}")
        k2.metric("Leads Efectivos", f"{int(df_vista['Lead Efectivo'].sum())}")
        k3.metric("GAP Acumulado", f"{int(df_vista['GAP'].iloc[-1]) if not df_vista.empty else 0}", "Vs Meta Acumulada")
        k4.metric("AP Mes (Total)", f"{int(df_vista['AP MES'].sum())}")
        
        st.divider()

        # Estilos visuales de Excel a Python
        def estilo_celdas(val):
            if isinstance(val, (int, float)):
                if val < 0: return 'color: red;'
            return ''
            
        def semaforo_porcentajes(val):
            if not isinstance(val, float): return ''
            if val >= 0.90: return 'background-color: #c6e0b4; color: black;' # Verde
            if val >= 0.80: return 'background-color: #ffe699; color: black;' # Amarillo
            if val > 0: return 'background-color: #ffc000; color: black;'    # Naranja
            return ''

        # Formatear la tabla para mostrar
        styler = df_vista.style.format({
            col: '{:.0f}' for col in df_vista.columns if '%' not in col and col != 'Día'
        }).format({
            col: '{:.1%}' for col in df_vista.columns if '%' in col
        }).applymap(estilo_celdas, subset=['GAP', 'Diferencia'])\
          .applymap(semaforo_porcentajes, subset=['% LE'])\
          .set_properties(**{'text-align': 'center', 'font-size': '12px'})
          
        st.dataframe(styler, use_container_width=True, height=600, hide_index=True)

    except KeyError as e:
        st.error(f"❌ Error crítico: Falta una columna en tu archivo Parquet. El sistema buscó la columna: {e}")
        st.info("Revisa la sección 'CONFIGURACIÓN DE COLUMNAS' en el código (líneas 12-21) y asegúrate de escribir los nombres exactos.")
