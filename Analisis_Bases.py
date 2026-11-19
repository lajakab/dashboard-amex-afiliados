import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import re
import os

# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
st.set_page_config(
    page_title="Análisis Operativo de Estados Leads, Perfiles y Bases",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-title { font-size: 26px; font-weight: 800; color: #0f172a; margin-bottom: 5px; }
    .sub-title { font-size: 14px; color: #64748b; margin-bottom: 20px; }
    .header-section { color: #1e3a8a; font-size: 18px; font-weight: 700; border-bottom: 2px solid #cbd5e1; padding-bottom: 6px; margin-top: 15px; margin-bottom: 15px; }
    .kpi-card { background-color: #ffffff; border-radius: 8px; padding: 12px 15px; border-left: 4px solid #2563eb; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 10px; }
    .kpi-title { font-size: 11px; color: #64748b; font-weight: 700; text-transform: uppercase; }
    .kpi-val { font-size: 18px; font-weight: 700; color: #0f172a; }
</style>
""", unsafe_allow_html=True)

meses_es = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

# 2. CARGA Y PROCESAMIENTO DE DATOS
@st.cache_data(ttl=300)
def load_data():
    file_paths = [
        "ventas.parquet", 
        "tb_afiliado_report_leads_amex.parquet", 
        "Amex_Afiliados.parquet",
        "DISTRIBUCION AMEX.xlsx"
    ]
    
    df = None
    loaded_file = None
    
    for path in file_paths:
        if os.path.exists(path):
            try:
                if path.endswith('.parquet'):
                    df = pd.read_parquet(path)
                elif path.endswith('.xlsx'):
                    df = pd.read_excel(path)
                loaded_file = path
                break
            except Exception:
                continue
                
    if df is None:
        return pd.DataFrame(), "Archivo no encontrado"

    df.columns = df.columns.str.strip()

    def get_col(candidates, default_name):
        for c in candidates:
            if c in df.columns:
                return c
        return default_name

    # Mapeo de columnas según requerimientos de ventas
    col_c_val = get_col(['estatus_val', 'LEAD EFECTIVO', 'C'], 'estatus_val')
    col_e_vta = get_col(['fecha_vta', 'Fecha Vta', 'FECHA_VTA', 'E'], 'fecha_vta')
    col_h_status = get_col(['status_vta', 'Status Vta', 'H'], 'status_vta')
    col_ad_list = get_col(['List_ID', 'list_id', 'LIST_ID', 'AD'], 'List_ID')
    col_am_pixel = get_col(['url_pixel', 'URI_PIXEL', 'pixel', 'AM'], 'url_pixel')
    col_at_decision = get_col(['status_evaluacion', 'AT Decisión', 'AT', 'status', 'status_evaluación'], 'status_evaluacion')
    col_ce_contacto = get_col(['Contacto Final Banco', 'contacto_final_banco', 'CE'], 'Contacto Final Banco')
    col_cc_edad = get_col(['edad2', 'Edad2', 'Edad', 'CC'], 'edad2')
    col_bz_score = get_col(['Score', 'score', 'BZ'], 'Score')
    col_by_servidor = get_col(['Servidor', 'servidor', 'BY'], 'Servidor')
    col_aw_producto = get_col(['Tipo de Producto', 'tipo_de_producto', 'AW'], 'Tipo de Producto')
    col_s_tarjeta = get_col(['Tarjeta', 'tarjeta', 'S'], 'Tarjeta')

    # Estandarización estricta de Fechas (Col E) a objetos datetime.date para evitar error de comparación
    if col_e_vta in df.columns:
        df['fecha_vta_dt'] = pd.to_datetime(df[col_e_vta], errors='coerce')
        df['fecha_vta_clean'] = df['fecha_vta_dt'].dt.date
    else:
        df['fecha_vta_dt'] = pd.to_datetime('today')
        df['fecha_vta_clean'] = datetime.now().date()

    df['Año_Mes'] = df['fecha_vta_dt'].dt.month.map(meses_es) + " " + df['fecha_vta_dt'].dt.year.astype(str)

    # 1. Cálculo de Thank You Píxel (Extracción desde Col AM url_pixel)
    if col_am_pixel in df.columns:
        extracted = df[col_am_pixel].astype(str).str.extract(r'thank-you/([^?&]+)', expand=False)
        df['Thank_You_Pixel'] = extracted.fillna('Sin Thank You').str.replace('-', ' ').str.title()
    else:
        df['Thank_You_Pixel'] = 'Sin Thank You'

    # Estandarización de Variables Operativas
    df['Lead_Efectivo_ColC'] = df[col_c_val].fillna('NO').astype(str).str.strip().str.upper() if col_c_val in df.columns else 'LEAD EFECTIVO'
    df['Status_Vta_ColH'] = df[col_h_status].fillna('OTRO').astype(str).str.strip().str.upper() if col_h_status in df.columns else 'LEAD EFECTIVO'
    df['Contacto_CE_Clean'] = df[col_ce_contacto].fillna('Sin Gestión Banco').astype(str).str.strip().str.title() if col_ce_contacto in df.columns else 'Sin Gestión Banco'
    df['List_ID_Clean'] = df[col_ad_list].fillna('Sin List ID').astype(str).str.strip() if col_ad_list in df.columns else 'Sin List ID'
    df['Edad2_Clean'] = df[col_cc_edad].fillna('Sin Edad').astype(str).str.strip() if col_cc_edad in df.columns else 'Sin Edad'
    df['Score_Clean'] = df[col_bz_score].fillna('Sin Score').astype(str).str.strip() if col_bz_score in df.columns else 'Sin Score'
    df['Servidor_Clean'] = df[col_by_servidor].fillna('Sin Servidor').astype(str).str.strip() if col_by_servidor in df.columns else 'Sin Servidor'
    df['Producto_Clean'] = df[col_aw_producto].fillna('Sin Producto').astype(str).str.strip() if col_aw_producto in df.columns else 'Sin Producto'
    df['Tarjeta_Clean'] = df[col_s_tarjeta].fillna('Sin Tarjeta').astype(str).str.strip() if col_s_tarjeta in df.columns else 'Sin Tarjeta'

    def clean_at(val):
        if pd.isna(val) or str(val).strip() in ['', '-', 'nan', 'NONE', 'None']:
            return '-'
        val_u = str(val).strip().upper()
        return val_u if val_u in ['A', 'D', 'C', 'P'] else '-'

    df['Status_AT_Clean'] = df[col_at_decision].apply(clean_at) if col_at_decision in df.columns else '-'

    return df, loaded_file

df_raw, loaded_filename = load_data()

# 3. FILTROS LATERALES DINÁMICOS
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=70)
st.sidebar.title("⚙️ Filtros Operativos")
st.sidebar.caption(f"📁 Origen: `{loaded_filename}`")

if df_raw.empty:
    st.error("No se pudo cargar la base de datos de origen.")
    st.stop()

# Manejo seguro de rangos de fechas (Solución a TypeError)
valid_dates = [d for d in df_raw['fecha_vta_clean'].tolist() if pd.notna(d)]
min_date = min(valid_dates) if valid_dates else date.today()
max_date = max(valid_dates) if valid_dates else date.today()

rango_fechas = st.sidebar.date_input(
    "📅 Rango Fecha Venta (Col E):",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Comparación segura normalizando tipos date
if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
    f_ini, f_fin = rango_fechas
    df = df_raw[(df_raw['fecha_vta_clean'] >= f_ini) & (df_raw['fecha_vta_clean'] <= f_fin)].copy()
else:
    df = df_raw.copy()

with st.sidebar.expander("👥 Edad & Servidor", expanded=True):
    edades_opt = sorted(df['Edad2_Clean'].unique().tolist())
    edad_sel = st.multiselect("Edad (Col CC):", edades_opt, default=edades_opt)

    serv_opt = sorted(df['Servidor_Clean'].unique().tolist())
    serv_sel = st.multiselect("Servidor (Col BY):", serv_opt, default=serv_opt)

with st.sidebar.expander("💳 Producto & Contacto Banco", expanded=False):
    prod_opt = sorted(df['Producto_Clean'].unique().tolist())
    prod_sel = st.multiselect("Tipo Producto (Col AW):", prod_opt, default=prod_opt)

    ce_opt = sorted(df['Contacto_CE_Clean'].unique().tolist())
    ce_sel = st.multiselect("Contacto Final Banco (Col CE):", ce_opt, default=ce_opt)

with st.sidebar.expander("🔗 Thank You Pixel (Col AM)", expanded=False):
    pixel_opt = sorted(df['Thank_You_Pixel'].unique().tolist())
    pixel_sel = st.multiselect("Thank You Pixel:", pixel_opt, default=pixel_opt)

# Filtrado dinámico
df = df[
    (df['Edad2_Clean'].isin(edad_sel)) &
    (df['Servidor_Clean'].isin(serv_sel)) &
    (df['Producto_Clean'].isin(prod_sel)) &
    (df['Contacto_CE_Clean'].isin(ce_sel)) &
    (df['Thank_You_Pixel'].isin(pixel_sel))
]

# 4. ENCABEZADO Y TOP 5 MÉTRICAS
st.markdown("<div class='main-title'>📊 Dashboard: Funnel y Perfil del Trámite</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Consolidado analítico de conversión de funnel, scoring, perfilamiento y atribución de píxel Thank You.</div>", unsafe_allow_html=True)

st.markdown("<h3 class='header-section'>⭐ Top 5 Métricas Destacadas</h3>", unsafe_allow_html=True)

selector_kpi_dim = st.radio(
    "Selecciona la dimensión prioritaria para actualizar el Top 5:",
    ["Edades (Col CC)", "Score (Col BZ)", "List ID (Col AD)"],
    horizontal=True
)

dim_col_map = {
    "Edades (Col CC)": "Edad2_Clean",
    "Score (Col BZ)": "Score_Clean",
    "List ID (Col AD)": "List_ID_Clean"
}
target_dim = dim_col_map[selector_kpi_dim]

c_k1, c_k2, c_k3, c_k4 = st.columns(4)

with c_k1:
    st.markdown("<div class='kpi-card'><div class='kpi-title'>🟢 Top 5 Más Aprueban (A)</div>", unsafe_allow_html=True)
    top_ap = df[df['Status_AT_Clean'] == 'A'][target_dim].value_counts().head(5)
    for idx, (name, val) in enumerate(top_ap.items(), 1):
        st.write(f"**{idx}. {name}**: {val:,}")
    st.markdown("</div>", unsafe_allow_html=True)

with c_k2:
    st.markdown("<div class='kpi-card'><div class='kpi-title'>🔴 Top 5 Menos Contactan</div>", unsafe_allow_html=True)
    top_nocontact = df[df['Contacto_CE_Clean'] == 'No Contacto'][target_dim].value_counts().head(5)
    for idx, (name, val) in enumerate(top_nocontact.items(), 1):
        st.write(f"**{idx}. {name}**: {val:,}")
    st.markdown("</div>", unsafe_allow_html=True)

with c_k3:
    st.markdown("<div class='kpi-card'><div class='kpi-title'>🟠 Top 5 Más Declinan (D)</div>", unsafe_allow_html=True)
    top_decl = df[df['Status_AT_Clean'] == 'D'][target_dim].value_counts().head(5)
    for idx, (name, val) in enumerate(top_decl.items(), 1):
        st.write(f"**{idx}. {name}**: {val:,}")
    st.markdown("</div>", unsafe_allow_html=True)

with c_k4:
    st.markdown("<div class='kpi-card'><div class='kpi-title'>🔵 Top 5 Más / No Evalúan</div>", unsafe_allow_html=True)
    top_eval = df[df['Status_AT_Clean'] != '-'][target_dim].value_counts().head(5)
    for idx, (name, val) in enumerate(top_eval.items(), 1):
        st.write(f"**{idx}. {name}**: {val:,}")
    st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# 5. TABLAS PRINCIPALES DEL DASHBOARD
tab_funnel, tab_list, tab_dia, tab_score = st.tabs([
    "📋 1. Funnel Trámite",
    "🗂️ 2. Funnel por List ID",
    "📅 3. Funnel por Día",
    "📈 4. % AP (Score / Servidor / List ID)"
])

# =====================================================================
# TABLA 1: FUNNEL TRÁMITE
# =====================================================================
with tab_funnel:
    st.markdown("<h3 class='header-section'>📋 Tabla 1: Funnel Trámite (Data Filtrada por Lead Efectivo)</h3>", unsafe_allow_html=True)
    st.caption("Filtra Columna C de Ventas (estatus_val) por 'LEAD EFECTIVO'. Meses asociados a la Columna E (fecha_vta).")

    df_funnel_le = df[df['Lead_Efectivo_ColC'].isin(['LEAD EFECTIVO', 'SI', 'EFECTIVO'])].copy()

    if df_funnel_le.empty:
        st.warning("No hay registros en estado LEAD EFECTIVO con los filtros aplicados.")
    else:
        meses_ordenados = sorted(df_funnel_le['Año_Mes'].unique())

        rows_def = [
            'Lead Efectivo',
            'No Contacto',
            'Contacto (No Interesado)',
            'Contacto (No Califica)',
            'Contacto Final',
            'Sin Gestión Banco',
            'Evaluado',
            'Aprobadas (A)',
            'Declinada (D)',
            'Cancelada (C)',
            'Pendiente (P)',
            'Total'
        ]

        matrix_rows = []
        for r in rows_def:
            row_dict = {'Concepto': r}
            for m in meses_ordenados:
                df_m = df_funnel_le[df_funnel_le['Año_Mes'] == m]
                tot_le_m = len(df_m)

                if r == 'Lead Efectivo':
                    cant = tot_le_m
                    pct = "-"
                elif r == 'No Contacto':
                    cant = len(df_m[df_m['Contacto_CE_Clean'] == 'No Contacto'])
                    pct = f"{(cant/tot_le_m*100):.1f}%" if tot_le_m > 0 else "0.0%"
                elif r == 'Contacto (No Interesado)':
                    cant = len(df_m[df_m['Contacto_CE_Clean'] == 'No Interesado'])
                    pct = f"{(cant/tot_le_m*100):.1f}%" if tot_le_m > 0 else "0.0%"
                elif r == 'Contacto (No Califica)':
                    cant = len(df_m[df_m['Contacto_CE_Clean'] == 'No Califica'])
                    pct = f"{(cant/tot_le_m*100):.1f}%" if tot_le_m > 0 else "0.0%"
                elif r == 'Contacto Final':
                    cant = len(df_m[df_m['Contacto_CE_Clean'].isin(['No Interesado', 'No Califica'])])
                    pct = f"{(cant/tot_le_m*100):.1f}%" if tot_le_m > 0 else "0.0%"
                elif r == 'Sin Gestión Banco':
                    cant = len(df_m[df_m['Contacto_CE_Clean'].isin(['Sin Gestión Banco', 'Sin Gestion Banco'])])
                    pct = f"{(cant/tot_le_m*100):.1f}%" if tot_le_m > 0 else "0.0%"
                elif r == 'Evaluado':
                    cant = len(df_m[df_m['Status_AT_Clean'] != '-'])
                    pct = f"{(cant/tot_le_m*100):.1f}%" if tot_le_m > 0 else "0.0%"
                elif r == 'Aprobadas (A)':
                    cant = len(df_m[df_m['Status_AT_Clean'] == 'A'])
                    pct = f"{(cant/tot_le_m*100):.1f}%" if tot_le_m > 0 else "0.0%"
                elif r == 'Declinada (D)':
                    cant = len(df_m[df_m['Status_AT_Clean'] == 'D'])
                    pct = f"{(cant/tot_le_m*100):.1f}%" if tot_le_m > 0 else "0.0%"
                elif r == 'Cancelada (C)':
                    cant = len(df_m[df_m['Status_AT_Clean'] == 'C'])
                    pct = f"{(cant/tot_le_m*100):.1f}%" if tot_le_m > 0 else "0.0%"
                elif r == 'Pendiente (P)':
                    cant = len(df_m[df_m['Status_AT_Clean'] == 'P'])
                    pct = f"{(cant/tot_le_m*100):.1f}%" if tot_le_m > 0 else "0.0%"
                elif r == 'Total':
                    cant = tot_le_m
                    pct = "100.0%"

                row_dict[f"{m} (Cant)"] = cant
                row_dict[f"{m} (%)"] = pct

            matrix_rows.append(row_dict)

        df_funnel_final = pd.DataFrame(matrix_rows)

        # Aplicación de resaltado de estilo por concepto
        def highlight_funnel_rows(row):
            concepto = str(row['Concepto'])
            if concepto in ['No Contacto', 'Contacto Final', 'Evaluado']:
                return ['background-color: #f1f5f9; font-weight: bold;'] * len(row)
            elif concepto == 'Aprobadas (A)':
                return ['background-color: #dcfce7; font-weight: bold;'] * len(row)
            elif concepto == 'Declinada (D)':
                return ['background-color: #fee2e2;'] * len(row)
            return [''] * len(row)

        st.dataframe(df_funnel_final.style.apply(highlight_funnel_rows, axis=1), use_container_width=True, hide_index=True)

        st.subheader("📊 Gráfica de Embudo de Conversión Operativo")
        funnel_counts = {
            'Lead Efectivo': len(df_funnel_le),
            'No Contacto': len(df_funnel_le[df_funnel_le['Contacto_CE_Clean'] == 'No Contacto']),
            'Contacto Final': len(df_funnel_le[df_funnel_le['Contacto_CE_Clean'].isin(['No Interesado', 'No Califica'])]),
            'Evaluados': len(df_funnel_le[df_funnel_le['Status_AT_Clean'] != '-']),
            'Aprobados (A)': len(df_funnel_le[df_funnel_le['Status_AT_Clean'] == 'A'])
        }
        fig_funnel = px.funnel(
            x=list(funnel_counts.values()),
            y=list(funnel_counts.keys()),
            title="Embudo de Conversión Global",
            color_discrete_sequence=['#2563eb']
        )
        st.plotly_chart(fig_funnel, use_container_width=True)


# =====================================================================
# TABLA 2: FUNNEL POR LIST ID Y AGRUPADORES
# =====================================================================
with tab_list:
    st.markdown("<h3 class='header-section'>🗂️ Tabla 2: Funnel por List ID / Agrupadores Dinámicos</h3>", unsafe_allow_html=True)

    col_sec1, col_sec2 = st.columns([1.5, 1])
    with col_sec1:
        primary_dim = st.selectbox(
            "Seleccionar Agrupador Principal:",
            ["List_ID_Clean", "Edad2_Clean", "Score_Clean", "Thank_You_Pixel", "Servidor_Clean"],
            format_func=lambda x: x.replace('_Clean', '').replace('_', ' ')
        )
    with col_sec2:
        sub_dims = st.multiselect(
            "Seleccionar Sub-datos para desglosar:",
            ["Edad2_Clean", "Score_Clean", "Thank_You_Pixel", "Servidor_Clean"],
            default=[]
        )

    group_cols = [primary_dim] + [sd for sd in sub_dims if sd != primary_dim] + ['Año_Mes']

    df_t2 = df.groupby(group_cols).apply(lambda g: pd.Series({
        'Trámites': len(g),
        'Lead Efectivo': (g['Status_Vta_ColH'] == 'LEAD EFECTIVO').sum(),
        'Otros': (g['Status_Vta_ColH'] != 'LEAD EFECTIVO').sum(),
        'Evaluadas': (g['Status_AT_Clean'] != '-').sum(),
        'Aprobadas': (g['Status_AT_Clean'] == 'A').sum(),
        'Canceladas': (g['Status_AT_Clean'] == 'C').sum(),
        'Declinadas': (g['Status_AT_Clean'] == 'D').sum(),
        'Pendientes': (g['Status_AT_Clean'] == 'P').sum(),
    }), include_groups=False).reset_index()

    df_t2['% LE'] = (df_t2['Lead Efectivo'] / df_t2['Trámites'] * 100).round(1).astype(str) + "%"
    df_t2['% Otros'] = (df_t2['Otros'] / df_t2['Trámites'] * 100).round(1).astype(str) + "%"
    df_t2['% Evaluadas'] = (df_t2['Evaluadas'] / df_t2['Lead Efectivo'] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).round(1).astype(str) + "%"
    df_t2['% AP / LE'] = (df_t2['Aprobadas'] / df_t2['Lead Efectivo'] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).round(1).astype(str) + "%"
    df_t2['% AP / Eval'] = (df_t2['Aprobadas'] / df_t2['Evaluadas'] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).round(1).astype(str) + "%"
    df_t2['% Canc'] = (df_t2['Canceladas'] / df_t2['Evaluadas'] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).round(1).astype(str) + "%"
    df_t2['% Decl'] = (df_t2['Declinadas'] / df_t2['Evaluadas'] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).round(1).astype(str) + "%"
    df_t2['% Pendt'] = (df_t2['Pendientes'] / df_t2['Evaluadas'] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).round(1).astype(str) + "%"

    st.dataframe(df_t2, use_container_width=True, hide_index=True)

    fig_t2 = px.bar(
        df_t2,
        x=primary_dim,
        y=['Aprobadas', 'Declinadas', 'Canceladas', 'Pendientes'],
        title=f"Resoluciones Banco por {primary_dim.replace('_Clean','')}",
        barmode='stack'
    )
    st.plotly_chart(fig_t2, use_container_width=True)


# =====================================================================
# TABLA 3: FUNNEL POR DÍA
# =====================================================================
with tab_dia:
    st.markdown("<h3 class='header-section'>📅 Tabla 3: Funnel Desglosado por Día</h3>", unsafe_allow_html=True)
    
    meses_disponibles = sorted(df['Año_Mes'].unique())
    mes_sel_dia = st.selectbox("📅 Selecciona el Mes a Inspeccionar por Día:", meses_disponibles)

    df_filtered_day = df[df['Año_Mes'] == mes_sel_dia].copy()

    primary_dim_day = st.selectbox(
        "Dimensionar Día por:",
        ["List_ID_Clean", "Edad2_Clean", "Score_Clean", "Thank_You_Pixel", "Servidor_Clean"],
        key="dim_day"
    )

    df_t3 = df_filtered_day.groupby(['fecha_vta_clean', primary_dim_day]).apply(lambda g: pd.Series({
        'Trámites': len(g),
        'Lead Efectivo': (g['Status_Vta_ColH'] == 'LEAD EFECTIVO').sum(),
        'Otros': (g['Status_Vta_ColH'] != 'LEAD EFECTIVO').sum(),
        'Evaluadas': (g['Status_AT_Clean'] != '-').sum(),
        'Aprobadas': (g['Status_AT_Clean'] == 'A').sum(),
        'Declinadas': (g['Status_AT_Clean'] == 'D').sum(),
        'Canceladas': (g['Status_AT_Clean'] == 'C').sum(),
        'Pendientes': (g['Status_AT_Clean'] == 'P').sum()
    }), include_groups=False).reset_index()

    df_t3['% AP / Eval'] = (df_t3['Aprobadas'] / df_t3['Evaluadas'] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).round(1).astype(str) + "%"
    df_t3['% Decl'] = (df_t3['Declinadas'] / df_t3['Evaluadas'] * 100).replace([np.inf, -np.inf], np.nan).fillna(0).round(1).astype(str) + "%"

    st.dataframe(df_t3.sort_values(by='fecha_vta_clean', ascending=False), use_container_width=True, hide_index=True)

    fig_t3_line = px.line(
        df_t3,
        x='fecha_vta_clean',
        y='Aprobadas',
        color=primary_dim_day,
        title=f"Evolución Diaria de Aprobaciones en {mes_sel_dia}"
    )
    st.plotly_chart(fig_t3_line, use_container_width=True)


# =====================================================================
# TABLA 4: % AP (SCORE / SERVIDOR / LIST ID / EDAD POR MES)
# =====================================================================
with tab_score:
    st.markdown("<h3 class='header-section'>📈 Tabla 4: Matriz de % AP por Mes y Dimensión</h3>", unsafe_allow_html=True)

    dim_matriz = st.radio(
        "Seleccionar Dimensión para la Matriz % AP:",
        ["Score_Clean", "Servidor_Clean", "List_ID_Clean", "Edad2_Clean", "Thank_You_Pixel"],
        horizontal=True,
        format_func=lambda x: x.replace('_Clean', '').replace('_', ' ')
    )

    pivot_eval = df.pivot_table(
        index=dim_matriz,
        columns='Año_Mes',
        values='fecha_vta_clean',
        aggfunc='count',
        fill_value=0
    ).reset_index()

    st.markdown("#### 1. Matriz de Leads Totales por Mes")
    st.dataframe(pivot_eval, use_container_width=True, hide_index=True)

    df_ap_only = df[df['Status_AT_Clean'] == 'A']
    pivot_ap = df_ap_only.pivot_table(
        index=dim_matriz,
        columns='Año_Mes',
        values='fecha_vta_clean',
        aggfunc='count',
        fill_value=0
    ).reset_index()

    st.markdown("#### 2. Matriz de Aprobaciones (A) por Mes")
    st.dataframe(pivot_ap, use_container_width=True, hide_index=True)

    if not pivot_ap.empty and len(pivot_ap.columns) > 1:
        st.subheader("🔥 Mapa de Calor de Aprobaciones por Mes")
        heatmap_data = pivot_ap.set_index(dim_matriz)
        fig_heat = px.imshow(
            heatmap_data,
            labels=dict(x="Mes", y="Dimensión", color="Aprobadas"),
            text_auto=True,
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_heat, use_container_width=True)
