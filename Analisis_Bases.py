import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import re
import os

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(
    page_title="Análisis Operativo de Estados Leads, Perfiles y Bases",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS
st.markdown("""
<style>
    .sub-header-title {
        color: #1e3a8a;
        font-weight: 700;
        border-bottom: 2px solid #cbd5e1;
        padding-bottom: 8px;
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .metric-box {
        background-color: #f8fafc;
        border-radius: 8px;
        padding: 12px;
        border-left: 4px solid #2563eb;
    }
</style>
""", unsafe_allow_html=True)

meses_es = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

# 2. CARGA Y TRANSFORMACIÓN DE DATOS
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
        return pd.DataFrame(), "No file found"

    df.columns = df.columns.str.strip()

    def get_col(candidates, default_name):
        for c in candidates:
            if c in df.columns:
                return c
        return default_name

    col_vta = get_col(['fecha_vta', 'Fecha Vta', 'FECHA_VTA', 'E'], 'fecha_vta')
    col_lead_efectivo = get_col(['LEAD EFECTIVO', 'lead_efectivo', 'C'], 'LEAD EFECTIVO')
    col_decision_f = get_col(['fecha_decisión', 'fecha_decision', 'AX'], 'fecha_decisión')
    col_status_at = get_col(['status_evaluacion', 'status', 'AT'], 'status_evaluacion')
    col_contacto_ce = get_col(['Contacto Final Banco', 'contacto_final_banco', 'CE'], 'Contacto Final Banco')
    col_sub_contacto_bw = get_col(['Sub Contacto', 'sub_contacto', 'BW'], 'Sub Contacto')
    col_edad_cc = get_col(['edad2', 'Edad2', 'CC'], 'edad2')
    col_score_bz = get_col(['Score', 'score', 'BZ'], 'Score')
    col_servidor_by = get_col(['Servidor', 'servidor', 'BY'], 'Servidor')
    col_producto_aw = get_col(['Tipo de Producto', 'tipo_de_producto', 'AW'], 'Tipo de Producto')
    col_tarjeta_s = get_col(['Tarjeta', 'tarjeta', 'S'], 'Tarjeta')
    col_banco_ac = get_col(['Banco', 'banco', 'AC'], 'Banco')
    col_pixel = get_col(['uri_pixel', 'URI_PIXEL', 'pixel'], 'uri_pixel')

    # Estandarización de Fechas (Col E)
    if col_vta in df.columns:
        df['fecha_vta_clean'] = pd.to_datetime(df[col_vta], errors='coerce').dt.date
    else:
        df['fecha_vta_clean'] = pd.to_datetime(datetime.now().date())

    if col_decision_f in df.columns:
        df['fecha_decision_clean'] = pd.to_datetime(df[col_decision_f], errors='coerce').dt.date
    else:
        df['fecha_decision_clean'] = df['fecha_vta_clean']

    df['Año_Mes'] = pd.to_datetime(df['fecha_vta_clean']).dt.month.map(meses_es) + " " + pd.to_datetime(df['fecha_vta_clean']).dt.year.astype(str)

    # 1. Extracción Columna AT (A, D, C, P, No Evaluado)
    def mapear_status_at(val):
        if pd.isna(val) or str(val).strip() == '' or str(val).strip().lower() == 'nan':
            return 'No Evaluado'
        val_str = str(val).strip().upper()
        if val_str == 'A': return 'Aprobado (A)'
        elif val_str == 'D': return 'Declinado (D)'
        elif val_str == 'C': return 'Cancelado (C)'
        elif val_str == 'P': return 'Pendiente (P)'
        else: return 'No Evaluado'

    if col_status_at in df.columns:
        df['Status_AT_Clean'] = df[col_status_at].apply(mapear_status_at)
    else:
        df['Status_AT_Clean'] = 'No Evaluado'

    # 2. Extracción Columna CE (Contacto Final Banco)
    if col_contacto_ce in df.columns:
        df['Contacto_CE_Clean'] = df[col_contacto_ce].fillna('Sin Gestión Banco').astype(str).str.strip().str.title()
    else:
        df['Contacto_CE_Clean'] = 'Sin Gestión Banco'

    # 3. Sub Contacto BW
    if col_sub_contacto_bw in df.columns:
        df['Sub_Contacto_BW_Clean'] = df[col_sub_contacto_bw].fillna('Sin Sub Contacto').astype(str).str.strip().str.title()
    else:
        df['Sub_Contacto_BW_Clean'] = 'Sin Sub Contacto'

    # 4. Lead Efectivo (Col C)
    if col_lead_efectivo in df.columns:
        df['Lead_Efectivo_Clean'] = df[col_lead_efectivo].fillna('NO').astype(str).str.strip().str.upper()
    else:
        df['Lead_Efectivo_Clean'] = 'SI'

    # 5. Extracción de Pixel "Thank You" de uri_pixel
    if col_pixel in df.columns:
        df['Thank_You_Pixel'] = df[col_pixel].astype(str).str.extract(r'thank-you/([^=?&]+)', expand=False).fillna('Sin Thank You')
        df['Thank_You_Pixel'] = df['Thank_You_Pixel'].str.replace('-', ' ').str.title()
    else:
        df['Thank_You_Pixel'] = 'Sin Thank You'

    # Campos complementarios
    df['Edad2_Clean'] = df[col_edad_cc].fillna('Sin Edad') if col_edad_cc in df.columns else 'Sin Edad'
    df['Score_Clean'] = df[col_score_bz].fillna('Sin Score') if col_score_bz in df.columns else 'Sin Score'
    df['Servidor_Clean'] = df[col_servidor_by].fillna('Sin Servidor') if col_servidor_by in df.columns else 'Sin Servidor'
    df['Producto_Clean'] = df[col_producto_aw].fillna('Sin Producto') if col_producto_aw in df.columns else 'Sin Producto'
    df['Tarjeta_Clean'] = df[col_tarjeta_s].fillna('Sin Tarjeta') if col_tarjeta_s in df.columns else 'Sin Tarjeta'
    df['Banco_Clean'] = df[col_banco_ac].fillna('Sin Banco') if col_banco_ac in df.columns else 'Sin Banco'

    return df, loaded_file

df_raw, loaded_filename = load_data()

# 3. FILTROS LATERALES
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=75)
st.sidebar.title("⚙️ Filtros Operativos")
st.sidebar.caption(f"📁 Origen: `{loaded_filename}`")

if df_raw.empty:
    st.error("No se encontró la base de datos de origen.")
    st.stop()

min_date = df_raw['fecha_vta_clean'].min()
max_date = df_raw['fecha_vta_clean'].max()

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

with st.sidebar.expander("📌 Filtros por Tarjeta y Banco", expanded=False):
    bancos_opt = sorted(df['Banco_Clean'].unique().tolist())
    banco_sel = st.multiselect("Banco (Col AC):", bancos_opt, default=bancos_opt)
    
    tarjetas_opt = sorted(df['Tarjeta_Clean'].unique().tolist())
    tarjeta_sel = st.multiselect("Tarjeta (Col S):", tarjetas_opt, default=tarjetas_opt)

with st.sidebar.expander("💳 Filtros por Producto y Servidor", expanded=False):
    prod_opt = sorted(df['Producto_Clean'].unique().tolist())
    prod_sel = st.multiselect("Producto (Col AW):", prod_opt, default=prod_opt)
    
    serv_opt = sorted(df['Servidor_Clean'].unique().tolist())
    serv_sel = st.multiselect("Servidor (Col BY):", serv_opt, default=serv_opt)

df = df[
    (df['Banco_Clean'].isin(banco_sel)) &
    (df['Tarjeta_Clean'].isin(tarjeta_sel)) &
    (df['Producto_Clean'].isin(prod_sel)) &
    (df['Servidor_Clean'].isin(serv_sel))
]

# 4. DASHBOARD PESTAÑAS
st.title("📊 Análisis Operativo de Estados Leads, Perfiles y Bases")

tab1, tab2, tab3, tab4 = st.tabs([
    "🚀 Resumen KPIs",
    "📈 Decisión Banco (AT / AX)",
    "🏦 Contacto Banco & Subcontacto (CE / BW)",
    "💳 Perfil Evaluadas & Thank You Pixel"
])

# TAB 1: VISIÓN GENERAL
with tab1:
    st.markdown("<h3 class='sub-header-title'>📌 Indicadores Generales de Gestión</h3>", unsafe_allow_html=True)
    
    total_leads = len(df)
    leads_efectivos = len(df[df['Lead_Efectivo_Clean'].isin(['LEAD EFECTIVO', 'SI', 'EFECTIVO'])])
    evaluadas = len(df[df['Contacto_CE_Clean'].str.upper() == 'EVALUADA'])
    aprobadas = len(df[df['Status_AT_Clean'] == 'Aprobado (A)'])
    declinadas = len(df[df['Status_AT_Clean'] == 'Declinado (D)'])
    
    pct_efectividad = (leads_efectivos / total_leads * 100) if total_leads > 0 else 0
    pct_evaluadas = (evaluadas / total_leads * 100) if total_leads > 0 else 0
    pct_aprobacion = (aprobadas / evaluadas * 100) if evaluadas > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Leads", f"{total_leads:,}")
    c2.metric("Leads Efectivos", f"{leads_efectivos:,}", f"{pct_efectividad:.1f}%")
    c3.metric("Evaluadas Banco", f"{evaluadas:,}", f"{pct_evaluadas:.1f}%")
    c4.metric("Aprobadas (A)", f"{aprobadas:,}", f"{pct_aprobacion:.1f}% de Eval.")
    c5.metric("Declinadas (D)", f"{declinadas:,}")

    st.divider()

    g1, g2 = st.columns(2)
    with g1:
        st.subheader("📊 Resoluciones AT")
        df_at_c = df['Status_AT_Clean'].value_counts().reset_index()
        df_at_c.columns = ['Estatus', 'Cantidad']
        fig_at = px.pie(df_at_c, values='Cantidad', names='Estatus', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_at, use_container_width=True)

    with g2:
        st.subheader("🏦 Estatus Contacto Banco (CE)")
        df_ce_c = df['Contacto_CE_Clean'].value_counts().head(8).reset_index()
        df_ce_c.columns = ['Contacto', 'Cantidad']
        fig_ce = px.bar(df_ce_c, x='Cantidad', y='Contacto', orientation='h', text_auto=True, color='Cantidad', color_continuous_scale='Blues')
        st.plotly_chart(fig_ce, use_container_width=True)

# TAB 2: DECISIÓN BANCO (COL AT/AX)
with tab2:
    st.markdown("<h3 class='sub-header-title'>📈 Análisis de Resoluciones Banco (AT) por Fecha Venta (E)</h3>", unsafe_allow_html=True)

    pivot_at_mes = df.pivot_table(
        index='Año_Mes',
        columns='Status_AT_Clean',
        values='fecha_vta_clean',
        aggfunc='count',
        fill_value=0
    ).reset_index()

    cols_at_opt = ['Aprobado (A)', 'Declinado (D)', 'Cancelado (C)', 'Pendiente (P)', 'No Evaluado']
    for cat in cols_at_opt:
        if cat not in pivot_at_mes.columns:
            pivot_at_mes[cat] = 0

    pivot_at_mes['Total Leads'] = pivot_at_mes[cols_at_opt].sum(axis=1)
    pivot_at_mes['% Aprobación'] = (pivot_at_mes['Aprobado (A)'] / pivot_at_mes['Total Leads'] * 100).fillna(0).round(1).astype(str) + "%"

    st.subheader("🗓️ Consolidado Mensual AT")
    st.dataframe(pivot_at_mes[['Año_Mes', 'Total Leads', 'Aprobado (A)', 'Declinado (D)', 'Cancelado (C)', 'Pendiente (P)', 'No Evaluado', '% Aprobación']], use_container_width=True, hide_index=True)

    fig_at_line = px.bar(
        pivot_at_mes,
        x='Año_Mes',
        y=['Aprobado (A)', 'Declinado (D)', 'Cancelado (C)', 'Pendiente (P)', 'No Evaluado'],
        title="Tendencia Mensual por Estatus AT",
        barmode='stack'
    )
    st.plotly_chart(fig_at_line, use_container_width=True)

    st.divider()

    st.subheader("📅 Consolidado Diarios AT")
    pivot_at_dia = df.pivot_table(
        index='fecha_vta_clean',
        columns='Status_AT_Clean',
        values='fecha_decision_clean',
        aggfunc='count',
        fill_value=0
    ).reset_index()

    for cat in cols_at_opt:
        if cat not in pivot_at_dia.columns:
            pivot_at_dia[cat] = 0

    pivot_at_dia['Total Día'] = pivot_at_dia[cols_at_opt].sum(axis=1)
    pivot_at_dia['% Aprobación Día'] = (pivot_at_dia['Aprobado (A)'] / pivot_at_dia['Total Día'] * 100).fillna(0).round(1).astype(str) + "%"

    st.dataframe(pivot_at_dia.sort_values(by='fecha_vta_clean', ascending=False), use_container_width=True, hide_index=True)

# TAB 3: CONTACTO BANCO & SUB CONTACTO
with tab3:
    st.markdown("<h3 class='sub-header-title'>🏦 Gestión de Contacto Banco (CE) & Sub Contacto (BW)</h3>", unsafe_allow_html=True)

    col1, col2 = st.columns([1.6, 1])
    with col1:
        st.subheader("🗓️ Consolidado Mensual Contacto Banco (CE)")
        pivot_ce_mes = df.pivot_table(
            index='Año_Mes',
            columns='Contacto_CE_Clean',
            values='fecha_vta_clean',
            aggfunc='count',
            fill_value=0
        ).reset_index()
        st.dataframe(pivot_ce_mes, use_container_width=True, hide_index=True)

    with col2:
        st.subheader("📊 Sub Contacto (BW)")
        df_bw_sum = df['Sub_Contacto_BW_Clean'].value_counts().reset_index()
        df_bw_sum.columns = ['Sub Contacto', 'Cantidad']
        df_bw_sum['% Total'] = (df_bw_sum['Cantidad'] / df_bw_sum['Cantidad'].sum() * 100).round(1).astype(str) + "%"
        st.dataframe(df_bw_sum, use_container_width=True, hide_index=True)

    st.divider()

    st.subheader("📅 Desglose Diarios Contacto Banco (CE)")
    pivot_ce_dia = df.pivot_table(
        index='fecha_vta_clean',
        columns='Contacto_CE_Clean',
        values='Año_Mes',
        aggfunc='count',
        fill_value=0
    ).reset_index()
    st.dataframe(pivot_ce_dia.sort_values(by='fecha_vta_clean', ascending=False), use_container_width=True, hide_index=True)

# TAB 4: EVALUADAS & THANK YOU PIXEL
with tab4:
    st.markdown("<h3 class='sub-header-title'>💳 Perfiles de Leads 'Evaluadas' y Atribución Píxel</h3>", unsafe_allow_html=True)
    
    df_eval = df[df['Contacto_CE_Clean'].str.upper() == 'EVALUADA'].copy()

    if df_eval.empty:
        st.info("No se registran solicitudes en estado 'Evaluada' en el rango seleccionado.")
    else:
        st.success(f"🔍 Evaluando **{len(df_eval):,}** registros en estado 'Evaluada'")

        st.subheader("🔗 Segmento Píxel 'Thank You' (Col uri_pixel)")
        df_px_sum = df_eval['Thank_You_Pixel'].value_counts().reset_index()
        df_px_sum.columns = ['Landing / Thank You Segment', 'Cantidad Evaluadas']
        df_px_sum['% Share'] = (df_px_sum['Cantidad Evaluadas'] / len(df_eval) * 100).round(1).astype(str) + "%"
        
        px1, px2 = st.columns([1.3, 1])
        with px1:
            st.dataframe(df_px_sum, use_container_width=True, hide_index=True)
        with px2:
            fig_px = px.pie(df_px_sum, values='Cantidad Evaluadas', names='Landing / Thank You Segment', title="Share Landers Thank You")
            st.plotly_chart(fig_px, use_container_width=True)

        st.divider()

        st.subheader("👥 Demografía y Perfil")
        pf1, pf2, pf3 = st.columns(3)
        with pf1:
            st.markdown("**Edad (Col CC)**")
            st.dataframe(df_eval['Edad2_Clean'].value_counts().reset_index().rename(columns={'index':'Edad', 'Edad2_Clean':'Cant'}), use_container_width=True, hide_index=True)
        with pf2:
            st.markdown("**Score (Col BZ)**")
            st.dataframe(df_eval['Score_Clean'].value_counts().reset_index().rename(columns={'index':'Score', 'Score_Clean':'Cant'}), use_container_width=True, hide_index=True)
        with pf3:
            st.markdown("**Servidor (Col BY)**")
            st.dataframe(df_eval['Servidor_Clean'].value_counts().reset_index().rename(columns={'index':'Servidor', 'Servidor_Clean':'Cant'}), use_container_width=True, hide_index=True)

        st.divider()

        st.subheader("💳 Producto, Tarjeta y Banco Emisor")
        pr1, pr2, pr3 = st.columns(3)
        with pr1:
            st.markdown("**Producto (Col AW)**")
            st.dataframe(df_eval['Producto_Clean'].value_counts().reset_index().rename(columns={'index':'Producto', 'Producto_Clean':'Cant'}), use_container_width=True, hide_index=True)
        with pr2:
            st.markdown("**Tarjeta (Col S)**")
            st.dataframe(df_eval['Tarjeta_Clean'].value_counts().reset_index().rename(columns={'index':'Tarjeta', 'Tarjeta_Clean':'Cant'}), use_container_width=True, hide_index=True)
        with pr3:
            st.markdown("**Banco (Col AC)**")
            st.dataframe(df_eval['Banco_Clean'].value_counts().reset_index().rename(columns={'index':'Banco', 'Banco_Clean':'Cant'}), use_container_width=True, hide_index=True)