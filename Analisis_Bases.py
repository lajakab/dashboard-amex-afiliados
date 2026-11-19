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
</style>
""", unsafe_allow_html=True)

meses_es = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}
month_to_num = {v: k for k, v in meses_es.items()}

def get_sort_key(an_mes):
    try:
        parts = str(an_mes).strip().split(' ')
        if len(parts) == 2:
            m_str, y_str = parts
            return (int(y_str), month_to_num.get(m_str, 0))
    except:
        pass
    return (0, 0)

# 2. LOCALIZACIÓN ROBUSTA DE COLUMNAS Y PROCESAMIENTO
def find_best_column(df, candidate_names, fallback_idx):
    # 1. Búsqueda exacta
    for cand in candidate_names:
        for col in df.columns:
            if str(cand).strip().lower() == str(col).strip().lower():
                return col
    # 2. Búsqueda por subcadena
    for cand in candidate_names:
        for col in df.columns:
            if str(cand).strip().lower() in str(col).strip().lower():
                return col
    # 3. Fallback por índice físico
    if fallback_idx < len(df.columns):
        return df.columns[fallback_idx]
    return candidate_names[0]

def clean_at_value(val):
    if pd.isna(val):
        return '-'
    s = str(val).strip().upper()
    if s in ['-', '', 'NAN', 'NONE', 'NULL', 'NO EVALUADO', 'SIN EVALUAR', 'N/A', '0']:
        return '-'
    if s == 'A' or 'APROB' in s or s == 'A - APROBADO':
        return 'A'
    if s == 'D' or 'DECLIN' in s or s == 'D - DECLINADO':
        return 'D'
    if s == 'C' or 'CANCEL' in s or s == 'C - CANCELADO':
        return 'C'
    if s == 'P' or 'PEND' in s or s == 'P - PENDIENTE':
        return 'P'
    return 'EVALUADO'

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

    # Búsqueda de columnas con fallback de índice exacto
    col_c_val = find_best_column(df, ['estatus_val', 'LEAD EFECTIVO', 'Lead Efectivo', 'estatus', 'C'], 2)
    col_e_vta = find_best_column(df, ['fecha_vta', 'Fecha Vta', 'FECHA_VTA', 'E', 'fecha_venta'], 4)
    col_h_status = find_best_column(df, ['status_vta', 'Status Vta', 'STATUS_VTA', 'H', 'status_venta'], 7)
    col_s_tarjeta = find_best_column(df, ['Tarjeta', 'tarjeta', 'S'], 18)
    col_ad_list = find_best_column(df, ['List_ID', 'list_id', 'LIST_ID', 'List ID', 'AD'], 29)
    col_am_pixel = find_best_column(df, ['url_pixel', 'URI_PIXEL', 'pixel', 'AM'], 38)
    col_at_decision = find_best_column(df, ['Decisión', 'decisión', 'DECISIÓN', 'DECISION', 'decision', 'AT Decisión', 'status_evaluacion', 'status_evaluación', 'AT', 'status'], 45)
    col_aw_producto = find_best_column(df, ['Tipo de Producto', 'tipo_de_producto', 'AW', 'Producto'], 48)
    col_by_servidor = find_best_column(df, ['Servidor', 'servidor', 'BY'], 76)
    col_bz_score = find_best_column(df, ['Score', 'score', 'BZ'], 77)
    col_cc_edad = find_best_column(df, ['edad2', 'Edad2', 'edad_2', 'Edad 2', 'edad', 'Edad', 'Rango_Edad', 'CC'], 80)
    col_ce_contacto = find_best_column(df, ['Contacto Final Banco', 'contacto_final_banco', 'Contacto Banco', 'CE'], 82)

    # Fechas (Col E)
    if col_e_vta in df.columns:
        df['fecha_vta_dt'] = pd.to_datetime(df[col_e_vta], errors='coerce')
        df['fecha_vta_clean'] = df['fecha_vta_dt'].dt.date
    else:
        df['fecha_vta_dt'] = pd.to_datetime('today')
        df['fecha_vta_clean'] = datetime.now().date()

    df['Año_Mes'] = df['fecha_vta_dt'].dt.month.map(meses_es) + " " + df['fecha_vta_dt'].dt.year.astype(str)

    # Extracción de Thank You Píxel (Col AM)
    if col_am_pixel in df.columns:
        extracted = df[col_am_pixel].astype(str).str.extract(r'thank-you/([^?&]+)', expand=False)
        df['Thank_You_Pixel'] = extracted.fillna('Sin Thank You').str.replace('-', ' ').str.title()
    else:
        df['Thank_You_Pixel'] = 'Sin Thank You'

    # Estandarización de Campos
    df['Lead_Efectivo_ColC'] = df[col_c_val].fillna('LEAD EFECTIVO').astype(str).str.strip().str.upper() if col_c_val in df.columns else 'LEAD EFECTIVO'
    df['Status_Vta_ColH'] = df[col_h_status].fillna('OTRO').astype(str).str.strip().str.upper() if col_h_status in df.columns else 'LEAD EFECTIVO'
    df['Contacto_CE_Clean'] = df[col_ce_contacto].fillna('Sin Gestión Banco').astype(str).str.strip().str.title() if col_ce_contacto in df.columns else 'Sin Gestión Banco'
    df['List_ID_Clean'] = df[col_ad_list].fillna('Sin List ID').astype(str).str.strip() if col_ad_list in df.columns else 'Sin List ID'
    df['Edad2_Clean'] = df[col_cc_edad].fillna('Sin Edad').astype(str).str.strip() if col_cc_edad in df.columns else 'Sin Edad'
    df['Score_Clean'] = df[col_bz_score].fillna('Sin Score').astype(str).str.strip() if col_bz_score in df.columns else 'Sin Score'
    df['Servidor_Clean'] = df[col_by_servidor].fillna('Sin Servidor').astype(str).str.strip() if col_by_servidor in df.columns else 'Sin Servidor'
    df['Producto_Clean'] = df[col_aw_producto].fillna('Sin Producto').astype(str).str.strip() if col_aw_producto in df.columns else 'Sin Producto'
    df['Tarjeta_Clean'] = df[col_s_tarjeta].fillna('Sin Tarjeta').astype(str).str.strip() if col_s_tarjeta in df.columns else 'Sin Tarjeta'

    df['Status_AT_Clean'] = df[col_at_decision].apply(clean_at_value) if col_at_decision in df.columns else '-'

    return df, loaded_file

df_raw, loaded_filename = load_data()

# 3. FILTROS LATERALES DINÁMICOS
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=70)
st.sidebar.title("⚙️ Filtros Operativos")
st.sidebar.caption(f"📁 Origen: `{loaded_filename}`")

if df_raw.empty:
    st.error("No se pudo cargar la base de datos de origen.")
    st.stop()

valid_dates = [d for d in df_raw['fecha_vta_clean'].tolist() if pd.notna(d)]
min_date = min(valid_dates) if valid_dates else date.today()
max_date = max(valid_dates) if valid_dates else date.today()

rango_fechas = st.sidebar.date_input(
    "📅 Rango Fecha Venta (Col E):",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(rango_fechas, tuple) and len(rango_fechas) == 2:
    f_ini, f_fin = rango_fechas
    df = df_raw[(df_raw['fecha_vta_clean'] >= f_ini) & (df_raw['fecha_vta_clean'] <= f_fin)].copy()
else:
    df = df_raw.copy()

def render_multiselect_filter(label, options, key_prefix, expanded=False):
    if not options:
        return options
    with st.sidebar.expander(label, expanded=expanded):
        col_a, col_b = st.columns(2)
        if col_a.button("✅ Todo", key=f"{key_prefix}_btn_all"):
            st.session_state[f"{key_prefix}_selected"] = list(options)
        if col_b.button("❌ Ninguno", key=f"{key_prefix}_btn_none"):
            st.session_state[f"{key_prefix}_selected"] = []

        if f"{key_prefix}_selected" not in st.session_state:
            st.session_state[f"{key_prefix}_selected"] = list(options)

        valid_selected = [x for x in st.session_state[f"{key_prefix}_selected"] if x in options]
        
        selected = st.multiselect(
            f"Buscar {label}:",
            options=options,
            default=valid_selected,
            key=f"{key_prefix}_ms"
        )
        st.session_state[f"{key_prefix}_selected"] = selected
        return selected

meses_disponibles = sorted(df['Año_Mes'].unique(), key=get_sort_key)
sel_meses = render_multiselect_filter("📅 Meses (Col E)", meses_disponibles, "flt_mes", expanded=True)

list_opt = sorted(df['List_ID_Clean'].unique())
sel_list = render_multiselect_filter("🗂️ List ID (Col AD)", list_opt, "flt_list")

score_opt = sorted(df['Score_Clean'].unique())
sel_score = render_multiselect_filter("📊 Score (Col BZ)", score_opt, "flt_score")

pixel_opt = sorted(df['Thank_You_Pixel'].unique())
sel_pixel = render_multiselect_filter("🔗 Thank You Pixel (Col AM)", pixel_opt, "flt_pixel")

edades_opt = sorted(df['Edad2_Clean'].unique())
sel_edad = render_multiselect_filter("👥 Edad (Col CC)", edades_opt, "flt_edad")

serv_opt = sorted(df['Servidor_Clean'].unique())
sel_serv = render_multiselect_filter("🖥️ Servidor (Col BY)", serv_opt, "flt_serv")

prod_opt = sorted(df['Producto_Clean'].unique())
sel_prod = render_multiselect_filter("💳 Tipo Producto (Col AW)", prod_opt, "flt_prod")

ce_opt = sorted(df['Contacto_CE_Clean'].unique())
sel_ce = render_multiselect_filter("🏦 Contacto Banco (Col CE)", ce_opt, "flt_ce")

# Aplicación segura de filtros (Si el filtro está vacío, se preserva todo)
def safe_filter(df_in, col_name, selected_vals):
    if not selected_vals:
        return df_in
    return df_in[df_in[col_name].isin(selected_vals)]

df = safe_filter(df, 'Año_Mes', sel_meses)
df = safe_filter(df, 'List_ID_Clean', sel_list)
df = safe_filter(df, 'Score_Clean', sel_score)
df = safe_filter(df, 'Thank_You_Pixel', sel_pixel)
df = safe_filter(df, 'Edad2_Clean', sel_edad)
df = safe_filter(df, 'Servidor_Clean', sel_serv)
df = safe_filter(df, 'Producto_Clean', sel_prod)
df = safe_filter(df, 'Contacto_CE_Clean', sel_ce)

# 4. ENCABEZADO Y TOP 5 MÉTRICAS DESTACADAS
st.markdown("<div class='main-title'>📊 Dashboard: Funnel y Perfil del Trámite</div>", unsafe_allow_html=True)
st.markdown("<div class='sub-title'>Consolidado analítico de conversión de funnel, scoring, perfilamiento y atribución de píxel Thank You.</div>", unsafe_allow_html=True)

st.markdown("<h3 class='header-section'>⭐ Top 5 Métricas Destacadas</h3>", unsafe_allow_html=True)

selector_kpi_dim = st.radio(
    "Selecciona la dimensión prioritaria para actualizar el Top 5:",
    ["Edades (Col CC)", "Score (Col BZ)", "List ID (Col AD)", "Thank You Pixel (Col AM)"],
    horizontal=True
)

dim_col_map = {
    "Edades (Col CC)": "Edad2_Clean",
    "Score (Col BZ)": "Score_Clean",
    "List ID (Col AD)": "List_ID_Clean",
    "Thank You Pixel (Col AM)": "Thank_You_Pixel"
}
target_dim = dim_col_map[selector_kpi_dim]

c_k1, c_k2, c_k3, c_k4 = st.columns(4)

with c_k1:
    st.markdown("<div class='kpi-card'><div class='kpi-title'>🟢 Top 5 Más Aprueban (A)</div>", unsafe_allow_html=True)
    top_ap = df[df['Status_AT_Clean'] == 'A'][target_dim].value_counts().head(5)
    for idx, (name, cant) in enumerate(top_ap.items(), 1):
        tot_eval = len(df[(df[target_dim] == name) & (df['Status_AT_Clean'] != '-')])
        pct = (cant / tot_eval * 100) if tot_eval > 0 else 0
        st.write(f"**{idx}. {name}**: {cant:,} ({pct:.1f}%)")
    st.markdown("</div>", unsafe_allow_html=True)

with c_k2:
    st.markdown("<div class='kpi-card'><div class='kpi-title'>🔴 Top 5 Menos Contactan</div>", unsafe_allow_html=True)
    top_nocontact = df[df['Contacto_CE_Clean'] == 'No Contacto'][target_dim].value_counts().head(5)
    for idx, (name, cant) in enumerate(top_nocontact.items(), 1):
        tot_l = len(df[df[target_dim] == name])
        pct = (cant / tot_l * 100) if tot_l > 0 else 0
        st.write(f"**{idx}. {name}**: {cant:,} ({pct:.1f}%)")
    st.markdown("</div>", unsafe_allow_html=True)

with c_k3:
    st.markdown("<div class='kpi-card'><div class='kpi-title'>🟠 Top 5 Más Declinan (D)</div>", unsafe_allow_html=True)
    top_decl = df[df['Status_AT_Clean'] == 'D'][target_dim].value_counts().head(5)
    for idx, (name, cant) in enumerate(top_decl.items(), 1):
        tot_eval = len(df[(df[target_dim] == name) & (df['Status_AT_Clean'] != '-')])
        pct = (cant / tot_eval * 100) if tot_eval > 0 else 0
        st.write(f"**{idx}. {name}**: {cant:,} ({pct:.1f}%)")
    st.markdown("</div>", unsafe_allow_html=True)

with c_k4:
    st.markdown("<div class='kpi-card'><div class='kpi-title'>🔵 Top 5 Más / No Evalúan</div>", unsafe_allow_html=True)
    top_eval = df[df['Status_AT_Clean'] != '-'][target_dim].value_counts().head(5)
    for idx, (name, cant) in enumerate(top_eval.items(), 1):
        tot_l = len(df[df[target_dim] == name])
        pct = (cant / tot_l * 100) if tot_l > 0 else 0
        st.write(f"**{idx}. {name}**: {cant:,} ({pct:.1f}%)")
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
    st.caption("Filtra Columna C (estatus_val) por 'LEAD EFECTIVO'. Meses ordenados cronológicamente desde la Columna E (fecha_vta).")

    # Selección de Lead Efectivo
    mask_le = df['Lead_Efectivo_ColC'].isin(['LEAD EFECTIVO', 'LEAD_EFECTIVO', 'SI', 'SÍ', '1', 'EFECTIVO', 'LE']) | df['Lead_Efectivo_ColC'].str.contains('LEAD', na=False)
    df_funnel_le = df[mask_le].copy()
    if df_funnel_le.empty:
        df_funnel_le = df.copy() # Fallback de seguridad

    meses_ordenados = sorted(df_funnel_le['Año_Mes'].unique(), key=get_sort_key)

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

    def apply_horizontal_gradient(df_in):
        styles = pd.DataFrame('', index=df_in.index, columns=df_in.columns)
        pct_cols = [c for c in df_in.columns if '(%)' in c]
        
        for idx, row in df_in.iterrows():
            concepto = str(row['Concepto'])
            nums = []
            col_val_map = {}
            for c in pct_cols:
                val_str = str(row[c]).replace('%', '').strip()
                try:
                    val_num = float(val_str)
                    nums.append(val_num)
                    col_val_map[c] = val_num
                except:
                    col_val_map[c] = None
                    
            if not nums or min(nums) == max(nums):
                continue
                
            min_v, max_v = min(nums), max(nums)
            span = max_v - min_v if max_v != min_v else 1.0
            
            for c in pct_cols:
                val_num = col_val_map.get(c)
                if val_num is None:
                    continue
                norm = (val_num - min_v) / span
                
                if concepto in ['Declinada (D)', 'Pendiente (P)', 'Cancelada (C)', 'No Contacto']:
                    alpha = 0.12 + 0.50 * norm
                    styles.loc[idx, c] = f'background-color: rgba(239, 68, 68, {alpha:.2f}); font-weight: bold;'
                elif concepto in ['Aprobadas (A)', 'Evaluado']:
                    alpha = 0.12 + 0.50 * norm
                    styles.loc[idx, c] = f'background-color: rgba(34, 197, 94, {alpha:.2f}); font-weight: bold;'
                elif 'Contacto' in concepto:
                    alpha = 0.12 + 0.50 * norm
                    styles.loc[idx, c] = f'background-color: rgba(245, 158, 11, {alpha:.2f}); font-weight: bold;'
        return styles

    st.dataframe(df_funnel_final.style.apply(apply_horizontal_gradient, axis=None), use_container_width=True, hide_index=True)

    st.subheader("📊 Embudo de Conversión Operativo Global")
    tot_le = len(df_funnel_le)
    cnt_nc = len(df_funnel_le[df_funnel_le['Contacto_CE_Clean'] == 'No Contacto'])
    cnt_cf = len(df_funnel_le[df_funnel_le['Contacto_CE_Clean'].isin(['No Interesado', 'No Califica'])])
    cnt_ev = len(df_funnel_le[df_funnel_le['Status_AT_Clean'] != '-'])
    cnt_ap = len(df_funnel_le[df_funnel_le['Status_AT_Clean'] == 'A'])

    funnel_stages = ['Lead Efectivo', 'No Contacto', 'Contacto Final', 'Evaluados', 'Aprobados (A)']
    funnel_values = [tot_le, cnt_nc, cnt_cf, cnt_ev, cnt_ap]
    funnel_text = [f'{v:,} ({(v/tot_le*100):.1f}%)' if tot_le > 0 else f'{v:,} (0.0%)' for v in funnel_values]

    fig_funnel = go.Figure(go.Funnel(
        y=funnel_stages,
        x=funnel_values,
        text=funnel_text,
        textinfo="text",
        marker=dict(color=['#1e3a8a', '#dc2626', '#f59e0b', '#2563eb', '#16a34a'])
    ))
    fig_funnel.update_layout(title_text="Conversión Funnel con Cantidad y Porcentaje")
    st.plotly_chart(fig_funnel, use_container_width=True)


# =====================================================================
# TABLA 2: FUNNEL POR LIST ID Y AGRUPADORES
# =====================================================================
with tab_list:
    st.markdown("<h3 class='header-section'>🗂️ Tabla 2: Funnel por List ID y Agrupadores Jerárquicos</h3>", unsafe_allow_html=True)

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

    df_t2['sort_key'] = df_t2['Año_Mes'].apply(get_sort_key)
    df_t2 = df_t2.sort_values(by=['sort_key', primary_dim]).drop(columns=['sort_key'])

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
    
    meses_disponibles_dia = sorted(df['Año_Mes'].unique(), key=get_sort_key)
    mes_sel_dia = st.selectbox("📅 Selecciona el Mes a Inspeccionar por Día:", meses_disponibles_dia)

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

    st.dataframe(df_t3.sort_values(by='fecha_vta_clean', ascending=True), use_container_width=True, hide_index=True)

    fig_t3_line = px.line(
        df_t3,
        x='fecha_vta_clean',
        y='Aprobadas',
        color=primary_dim_day,
        title=f"Evolución Diaria de Aprobaciones en {mes_sel_dia}"
    )
    st.plotly_chart(fig_t3_line, use_container_width=True)


# =====================================================================
# TABLA 4: MATRIZ DE % AP DESGLOSADA POR MES
# =====================================================================
with tab_score:
    st.markdown("<h3 class='header-section'>📈 Tabla 4: Matrices de Leads Totales y % AP por Mes</h3>", unsafe_allow_html=True)

    dim_matriz = st.radio(
        "Seleccionar Dimensión para la Matriz % AP:",
        ["Score_Clean", "Servidor_Clean", "List_ID_Clean", "Edad2_Clean", "Thank_You_Pixel"],
        horizontal=True,
        format_func=lambda x: x.replace('_Clean', '').replace('_', ' ')
    )

    sorted_months = sorted(df['Año_Mes'].unique(), key=get_sort_key)

    # MATRIZ 1: Leads Totales (Cantidad)
    m1 = df.pivot_table(index=dim_matriz, columns='Año_Mes', values='fecha_vta_clean', aggfunc='count', fill_value=0)
    m1 = m1.reindex(columns=[m for m in sorted_months if m in m1.columns], fill_value=0)

    # MATRIZ 2: Leads Totales (% Distribución por Mes)
    m2 = m1.copy()
    for col in m2.columns:
        col_tot = m2[col].sum()
        m2[col] = (m2[col] / col_tot * 100).round(1).astype(str) + "%" if col_tot > 0 else "0.0%"

    # MATRIZ 3: Aprobaciones A (Cantidad)
    df_ap = df[df['Status_AT_Clean'] == 'A']
    m3 = df_ap.pivot_table(index=dim_matriz, columns='Año_Mes', values='fecha_vta_clean', aggfunc='count', fill_value=0)
    m3 = m3.reindex(index=m1.index, columns=[m for m in sorted_months if m in m1.columns], fill_value=0)

    # MATRIZ 4: % AP sobre Evaluadas
    df_eval = df[df['Status_AT_Clean'] != '-']
    m_eval = df_eval.pivot_table(index=dim_matriz, columns='Año_Mes', values='fecha_vta_clean', aggfunc='count', fill_value=0)
    m_eval = m_eval.reindex(index=m1.index, columns=[m for m in sorted_months if m in m1.columns], fill_value=0)

    m4 = (m3 / m_eval * 100).fillna(0).round(1).astype(str) + "%"

    st.markdown("#### 1. Matriz de Leads Totales (Cantidad)")
    st.dataframe(m1, use_container_width=True)

    st.markdown("#### 2. Matriz de Leads Totales (% Distribución por Mes)")
    st.dataframe(m2, use_container_width=True)

    st.markdown("#### 3. Matriz de Aprobaciones A (Cantidad)")
    st.dataframe(m3, use_container_width=True)

    st.markdown("#### 4. Matriz de % AP (Aprobaciones sobre Evaluadas)")
    st.dataframe(m4, use_container_width=True)

    if not m3.empty and len(m3.columns) > 0:
        st.subheader("🔥 Mapa de Calor de Aprobaciones por Mes")
        fig_heat = px.imshow(
            m3,
            labels=dict(x="Mes", y="Dimensión", color="Aprobadas"),
            text_auto=True,
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig_heat, use_container_width=True)
