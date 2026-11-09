import streamlit as st
import pandas as pd
import numpy as np
import holidays
from datetime import date, timedelta
import calendar

# ==========================================
# CONFIGURACIÓN DE COLUMNAS (Ajusta esto según tu parquet)
# ==========================================
ARCHIVO_DATOS = "Amex_Afiliados.parquet"
COL_FECHA = "fecha" # Columna de fecha de venta/gestión
COL_ESTADO = "status" # Columna donde dice 'LEAD EFECTIVO', 'RECHAZADA', etc.
COL_AGENTES = "user" # Columna del ID o Nombre del agente para contar 'Agentes Log'

# Textos exactos de tus tipificaciones en la base de datos
ESTADO_LE = "LEAD EFECTIVO"
ESTADO_LNC = "LEAD NO CAPTURADO"
ESTADO_LNC_COND = "LEAD NO CONDICIONES"
ESTADO_DECLINADO = "DECLINADO"
ESTADO_CANCELADO = "CANCELADO"
ESTADO_APROBADO = "APROBADO" # Ajusta según cómo se llame el Aprobado (AP)
# ==========================================

# Configuración de página amplia para vista gerencial
st.set_page_config(page_title="Dashboard Amex Afiliados", layout="wide", initial_sidebar_state="expanded")

# --- CARGA DE DATOS ---
@st.cache_data
def cargar_datos():
    try:
        df = pd.read_parquet(ARCHIVO_DATOS)
        df[COL_FECHA] = pd.to_datetime(df[COL_FECHA]).dt.date
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo Parquet: {e}")
        return pd.DataFrame()

df_raw = cargar_datos()

if not df_raw.empty:
    # --- FILTROS LATERALES ---
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("Filtros Gerenciales")
    
    # Extraer años y meses disponibles
    años_disp = sorted(df_raw[COL_FECHA].apply(lambda x: x.year).unique())
    año_sel = st.sidebar.selectbox("Seleccione el Año", años_disp, index=len(años_disp)-1)
    
    meses_disp = sorted(df_raw[df_raw[COL_FECHA].apply(lambda x: x.year) == año_sel][COL_FECHA].apply(lambda x: x.month).unique())
    nombres_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    mes_formateado = [nombres_meses[m] for m in meses_disp]
    
    mes_sel_nombre = st.sidebar.selectbox("Seleccione el Mes", mes_formateado, index=len(mes_formateado)-1)
    mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]

    # Meta diaria estática (puedes volverlo dinámico luego)
    meta_diaria = st.sidebar.number_input("Meta Diaria (Tramites)", min_value=0, value=279)

    # --- LÓGICA DE CALENDARIO Y DÍAS HÁBILES (Sin Domingos, Sin Festivos MX) ---
    festivos_mx = holidays.Mexico(years=año_sel)
    
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    fechas_mes = [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]
    
    df_calendario = pd.DataFrame({"Fecha": fechas_mes})
    df_calendario['Día_Semana'] = pd.to_datetime(df_calendario['Fecha']).dt.dayofweek
    df_calendario['Festivo'] = df_calendario['Fecha'].apply(lambda x: x in festivos_mx)
    
    # Es hábil si NO es domingo (6) y NO es festivo
    df_calendario['Es_Habil'] = ~((df_calendario['Día_Semana'] == 6) | (df_calendario['Festivo']))
    dias_habiles_totales = df_calendario['Es_Habil'].sum()
    
    # --- PROCESAMIENTO DE DATOS ---
    df_mes = df_raw[(df_raw[COL_FECHA].apply(lambda x: x.year) == año_sel) & (df_raw[COL_FECHA].apply(lambda x: x.month) == mes_sel)]
    
    # Agrupación diaria simulando los CONTAR.SI.CONJUNTO
    agrupado = df_mes.groupby(COL_FECHA).apply(lambda x: pd.Series({
        'Tramites': len(x),
        'Lead Efectivo': (x[COL_ESTADO] == ESTADO_LE).sum(),
        'Lead No Capturado': (x[COL_ESTADO] == ESTADO_LNC).sum(),
        'Lead No Condiciones': (x[COL_ESTADO] == ESTADO_LNC_COND).sum(),
        'Declinado': (x[COL_ESTADO] == ESTADO_DECLINADO).sum(),
        'Cancelado': (x[COL_ESTADO] == ESTADO_CANCELADO).sum(),
        'AP': (x[COL_ESTADO] == ESTADO_APROBADO).sum(),
        'Agentes Log': x[COL_AGENTES].nunique() # Cuenta agentes únicos en el día
    })).reset_index()
    
    # Unir calendario con datos
    df_final = pd.merge(df_calendario, agrupado, left_on="Fecha", right_on=COL_FECHA, how="left").fillna(0)
    
    # Nombre del día en español (ej. lun-02-nov)
    dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb", 6:"dom"}
    df_final['Día'] = df_final.apply(lambda row: f"{dias_esp[row['Día_Semana']]}-{row['Fecha'].strftime('%d-%b')}", axis=1)
    
    # --- CÁLCULO DE COLUMNAS FORMULADAS ---
    df_final['Otros'] = df_final['Tramites'] - (df_final['Lead Efectivo'] + df_final['Lead No Capturado'] + df_final['Lead No Condiciones'])
    df_final['% LE'] = np.where(df_final['Tramites'] > 0, df_final['Lead Efectivo'] / df_final['Tramites'], 0)
    
    # Asumiendo % REM/RECH como Otros / Tramites (Ajustar según necesidad)
    df_final['% REM/RECH'] = np.where(df_final['Tramites'] > 0, df_final['Otros'] / df_final['Tramites'], 0)
    df_final['Prom'] = np.where(df_final['Agentes Log'] > 0, df_final['Tramites'] / df_final['Agentes Log'], 0)
    
    # Simulación de Agentes Plantilla y Ausentismo (puedes conectarlo a otra BD luego)
    df_final['Agentes Plantilla'] = df_final['Agentes Log'] + np.random.randint(0, 3, size=len(df_final)) # Placeholder
    df_final['% Ausentismo'] = np.where(df_final['Agentes Plantilla'] > 0, (df_final['Agentes Plantilla'] - df_final['Agentes Log']) / df_final['Agentes Plantilla'], 0)
    
    df_final['Meta Día'] = np.where(df_final['Es_Habil'], meta_diaria, 0)
    df_final['GAP'] = df_final['Tramites'] - df_final['Meta Día']
    
    df_final['% Declinado'] = np.where(df_final['Tramites'] > 0, df_final['Declinado'] / df_final['Tramites'], 0)
    df_final['% Cancelado'] = np.where(df_final['Tramites'] > 0, df_final['Cancelado'] / df_final['Tramites'], 0)

    # Ordenar columnas para la vista gerencial
    cols_vista = [
        'Día', 'Tramites', 'Lead Efectivo', 'Lead No Capturado', 'Lead No Condiciones', 'Otros', 
        '% LE', '% REM/RECH', 'Prom', 'Agentes Log', 'Agentes Plantilla', '% Ausentismo', 
        'AP', 'Meta Día', 'GAP', 'Declinado', '% Declinado', 'Cancelado', '% Cancelado'
    ]
    df_vista = df_final[cols_vista].copy()

    # --- INTERFAZ DEL DASHBOARD ---
    st.title("📊 Informe Gerencial - Amex Afiliados")
    
    # Pestañas
    tab_gerencial, tab_detalles = st.tabs(["📑 Resumen Mensual", "🔍 Base de Datos"])
    
    with tab_gerencial:
        # Tarjetas Superiores (KPIs)
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        total_tramites = df_vista['Tramites'].sum()
        total_le = df_vista['Lead Efectivo'].sum()
        gap_total = df_vista['GAP'].sum()
        
        kpi1.metric("Días Hábiles Mes", f"{dias_habiles_totales} días")
        kpi2.metric("Trámites Totales", f"{int(total_tramites)}")
        kpi3.metric("Leads Efectivos", f"{int(total_le)}", f"{(total_le/total_tramites)*100 if total_tramites else 0:.1f}% LE")
        kpi4.metric("GAP Acumulado", f"{int(gap_total)}", "Por debajo de meta" if gap_total < 0 else "Por encima de meta", delta_color="normal")

        st.markdown("---")
        
        # Estilos Condicionales para la Tabla (El toque "Bonito y Gerencial")
        def color_gap(val):
            color = '#ffcccc' if val < 0 else '#ccffcc'
            return f'background-color: {color}'
            
        def color_porcentaje(val):
            if val >= 0.90: return 'background-color: #c6e0b4' # Verde
            elif val >= 0.80: return 'background-color: #ffe699' # Amarillo
            elif val > 0: return 'background-color: #ffc000' # Naranja
            return ''

        # Aplicar estilos con Pandas Styler
        styler = df_vista.style.format({
            'Tramites': '{:.0f}', 'Lead Efectivo': '{:.0f}', 'Lead No Capturado': '{:.0f}',
            'Lead No Condiciones': '{:.0f}', 'Otros': '{:.0f}', 'Agentes Log': '{:.0f}', 
            'Agentes Plantilla': '{:.0f}', 'AP': '{:.0f}', 'Meta Día': '{:.0f}', 'GAP': '{:.0f}',
            'Declinado': '{:.0f}', 'Cancelado': '{:.0f}',
            '% LE': '{:.1%}', '% REM/RECH': '{:.1%}', 'Prom': '{:.1f}', 
            '% Ausentismo': '{:.1%}', '% Declinado': '{:.1%}', '% Cancelado': '{:.1%}'
        })\
        .applymap(color_gap, subset=['GAP'])\
        .applymap(color_porcentaje, subset=['% LE'])\
        .background_gradient(cmap='Blues', subset=['Tramites'])\
        .set_properties(**{'text-align': 'center', 'font-size': '13px'})
        
        # Mostrar tabla expandida
        st.dataframe(styler, use_container_width=True, height=600, hide_index=True)

    with tab_detalles:
        st.subheader("Datos crudos del mes")
        st.dataframe(df_mes, use_container_width=True)

else:
    st.warning("No se encontraron datos en el archivo Parquet. Verifique la ruta o el archivo.")