import streamlit as st
import pandas as pd
import numpy as np
import holidays
from datetime import date
import calendar
import re

st.set_page_config(page_title="Informe Gerencial Amex", layout="wide")

# CSS estilizado para tarjetas de alto impacto gerencial
st.markdown("""
<style>
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e6e8eb;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        margin-bottom: 10px;
    }
    .kpi-title {
        font-size: 13px;
        color: #6c757d;
        font-weight: 600;
        text-transform: uppercase;
        margin-bottom: 5px;
    }
    .kpi-value {
        font-size: 26px;
        font-weight: 700;
        color: #1f2937;
    }
    .kpi-subtext {
        font-size: 12px;
        color: #4b5563;
        margin-top: 4px;
    }
    .kpi-badge-success {
        color: #15803d;
        font-weight: 600;
    }
    .kpi-badge-danger {
        color: #b91c1c;
        font-weight: 600;
    }
    .table-card {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 12px;
    }
    .table-card-row {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        border-bottom: 1px solid #e2e8f0;
        font-size: 13px;
    }
    .table-card-row:last-child {
        border-bottom: none;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def cargar_pestanas():
    def load_pq(name):
        try: return pd.read_parquet(name)
        except: return pd.DataFrame()
    return load_pq("ventas.parquet"), load_pq("planta.parquet"), load_pq("seg_ppto.parquet"), load_pq("malla_día.parquet")

df_ventas, df_planta, df_ppto, df_malla = cargar_pestanas()

if not df_ventas.empty and len(df_ventas.columns) > 45:
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png", width=150)
    st.sidebar.header("🔍 Filtros")
    
    # 1. PREPARACIÓN VENTAS (E=4, H=7, AT=45, AX=49)
    df_ventas['F_VTA'] = pd.to_datetime(df_ventas.iloc[:, 4], errors='coerce').dt.date
    df_ventas['ESTADO'] = df_ventas.iloc[:, 7].astype(str).str.strip().str.upper()
    df_ventas['DECISION'] = df_ventas.iloc[:, 45].astype(str).str.strip().str.upper()
    
    if len(df_ventas.columns) > 49:
        df_ventas['F_DEC'] = pd.to_datetime(df_ventas.iloc[:, 49], errors='coerce').dt.date
    else:
        df_ventas['F_DEC'] = pd.NaT

    fechas_validas = pd.Series(df_ventas['F_VTA']).dropna()
    años_disp = sorted(pd.to_datetime(fechas_validas).dt.year.unique()) if not fechas_validas.empty else [date.today().year]
    año_sel = st.sidebar.selectbox("Año", años_disp, index=len(años_disp)-1)
    
    meses_disp = sorted(pd.to_datetime(fechas_validas[pd.to_datetime(fechas_validas).dt.year == año_sel]).dt.month.unique()) if not fechas_validas.empty else [date.today().month]
    nombres_meses = {1:"Enero", 2:"Febrero", 3:"Marzo", 4:"Abril", 5:"Mayo", 6:"Junio", 7:"Julio", 8:"Agosto", 9:"Septiembre", 10:"Octubre", 11:"Noviembre", 12:"Diciembre"}
    mes_formateado = [nombres_meses[m] for m in meses_disp if m in nombres_meses]
    mes_sel_nombre = st.sidebar.selectbox("Mes", mes_formateado, index=len(mes_formateado)-1) if mes_formateado else "Noviembre"
    mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]

    if 'asesor' in [str(c).lower() for c in df_ventas.columns]:
        col_as = next(c for c in df_ventas.columns if 'asesor' in str(c).lower())
        asesores = ["Todos"] + sorted(df_ventas[col_as].dropna().astype(str).unique().tolist())
        asesor_sel = st.sidebar.selectbox("Asesor", asesores)
        if asesor_sel != "Todos":
            df_ventas = df_ventas[df_ventas[col_as] == asesor_sel]

    # --- PARSER FECHAS ---
    def parse_fecha_sucia(serie, año):
        def extract_date(val):
            if pd.isna(val) or val == '' or val == 'nan': return pd.NaT
            val_str = str(val).strip().lower()
            if re.match(r'^\d{4}-\d{2}-\d{2}', val_str):
                try: return pd.to_datetime(val_str[:10]).date()
                except: pass
            m = re.search(r'(\d{1,2})-([a-z]{3})', val_str)
            if m:
                d, mes_str = int(m.group(1)), m.group(2)
                m_num = {'ene':1, 'feb':2, 'mar':3, 'abr':4, 'may':5, 'jun':6, 'jul':7, 'ago':8, 'sep':9, 'oct':10, 'nov':11, 'dic':12}.get(mes_str, 1)
                try: return date(año, m_num, d)
                except: pass
            try: return pd.to_datetime(val, errors='coerce').date()
            except: return pd.NaT
        return serie.apply(extract_date)

    # --- CALENDARIO BASE ---
    festivos_mx = holidays.Mexico(years=año_sel)
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    df_cal = pd.DataFrame({"Fecha": [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]})
    df_cal['Día_Semana'] = pd.to_datetime(df_cal['Fecha']).dt.dayofweek
    df_cal['Es_Festivo'] = pd.to_datetime(df_cal['Fecha']).apply(lambda x: x in festivos_mx)
    df_cal = df_cal[~((df_cal['Día_Semana'] == 6) | (df_cal['Es_Festivo']))].copy()

    # --- HOJAS AUXILIARES Y METAS ---
    if not df_planta.empty and len(df_planta.columns) > 2:
        df_planta['Fecha'] = pd.to_datetime(df_planta.iloc[:, 0], errors='coerce').dt.date
        df_planta['Agentes Plantilla'] = pd.to_numeric(df_planta.iloc[:, 1], errors='coerce').fillna(0)
        df_planta['Agentes Log'] = pd.to_numeric(df_planta.iloc[:, 2], errors='coerce').fillna(0)
        df_cal = pd.merge(df_cal, df_planta.groupby('Fecha').agg({'Agentes Plantilla':'max', 'Agentes Log':'max'}).reset_index(), on='Fecha', how='left')

    if not df_ppto.empty and len(df_ppto.columns) > 35:
        df_ppto['Fecha'] = parse_fecha_sucia(df_ppto.iloc[:, 35], año_sel)
        df_ppto['Meta Día Lead Efectivo'] = pd.to_numeric(df_ppto.iloc[:, 36], errors='coerce').fillna(0) if len(df_ppto.columns) > 36 else 0
        df_ppto['Meta Asesor'] = pd.to_numeric(df_ppto.iloc[:, 37], errors='coerce').fillna(0) if len(df_ppto.columns) > 37 else 0
        df_ppto['Meta AP Mes'] = pd.to_numeric(df_ppto.iloc[:, 38], errors='coerce').fillna(0) if len(df_ppto.columns) > 38 else 0
        df_ppto['Meta AP Cosecha'] = pd.to_numeric(df_ppto.iloc[:, 39], errors='coerce').fillna(0) if len(df_ppto.columns) > 39 else 0
        
        df_cal = pd.merge(df_cal, df_ppto.groupby('Fecha').agg({
            'Meta Día Lead Efectivo':'max', 
            'Meta Asesor':'max',
            'Meta AP Mes':'max',
            'Meta AP Cosecha':'max'
        }).reset_index(), on='Fecha', how='left')

    if not df_malla.empty and len(df_malla.columns) > 13:
        df_malla['Fecha'] = parse_fecha_sucia(df_malla.iloc[:, 13], año_sel)
        col_tr_idx = 65 if len(df_malla.columns) > 65 else next((i for i, c in enumerate(df_malla.columns) if 'tiempo' in str(c).lower()), -1)
        if col_tr_idx != -1 and len(df_malla.columns) > col_tr_idx:
            df_malla['Tiempo Real'] = pd.to_numeric(df_malla.iloc[:, col_tr_idx], errors='coerce').fillna(0)
            df_cal = pd.merge(df_cal, df_malla.groupby('Fecha').agg({'Tiempo Real':'sum'}).reset_index(), on='Fecha', how='left')

    for col in ['Agentes Plantilla', 'Agentes Log', 'Meta Día Lead Efectivo', 'Meta Asesor', 'Meta AP Mes', 'Meta AP Cosecha', 'Tiempo Real']:
        if col not in df_cal.columns: df_cal[col] = 0
    df_cal = df_cal.fillna(0)

    # --- AGRUPACIÓN VENTAS ---
    df_ventas_vta = df_ventas[(pd.to_datetime(df_ventas['F_VTA']).dt.year == año_sel) & (pd.to_datetime(df_ventas['F_VTA']).dt.month == mes_sel)]
    agrup_vta = df_ventas_vta.groupby('F_VTA').apply(lambda x: pd.Series({
        'Tramites': len(x),
        'Lead Efectivo': (x['ESTADO'] == 'LEAD EFECTIVO').sum(),
        'Lead No Capturado': (x['ESTADO'] == 'LEAD NO CAPTURADO').sum(),
        'Lead No Condiciones': (x['ESTADO'] == 'LEAD NO CONDICIONES').sum(),
        'Otros': (~x['ESTADO'].isin(['LEAD EFECTIVO', 'LEAD NO CAPTURADO', 'LEAD NO CONDICIONES', '', 'NAN'])).sum(),
        'EVALUADO': (x['DECISION'] != '-').sum(),
        'NO GESTIONADO': (x['DECISION'] == '-').sum(),
        'Declinado': (x['DECISION'] == 'D').sum(),
        'Cancelado': (x['DECISION'] == 'C').sum(),
        'Pendiente': (x['DECISION'] == 'P').sum()
    })).reset_index().rename(columns={'F_VTA': 'Fecha'})

    # --- AGRUPACIÓN APROBACIONES ---
    df_ap_mes = df_ventas_vta[df_ventas_vta['DECISION'] == 'A']
    agrup_ap_mes = df_ap_mes.groupby('F_VTA').size().reset_index(name='AP MES').rename(columns={'F_VTA': 'Fecha'})

    df_ap_cos = df_ventas[(pd.to_datetime(df_ventas['F_DEC']).dt.year == año_sel) & (pd.to_datetime(df_ventas['F_DEC']).dt.month == mes_sel) & (df_ventas['DECISION'] == 'A') & (pd.to_datetime(df_ventas['F_VTA']).dt.month != mes_sel)]
    agrup_ap_cos = df_ap_cos.groupby('F_DEC').size().reset_index(name='AP COSECHA').rename(columns={'F_DEC': 'Fecha'})

    # --- CRUCE Y CÁLCULOS ---
    df_final = pd.merge(df_cal, agrup_vta, on="Fecha", how="left").fillna(0)
    df_final = pd.merge(df_final, agrup_ap_mes, on="Fecha", how="left").fillna(0)
    df_final = pd.merge(df_final, agrup_ap_cos, on="Fecha", how="left").fillna(0)
    
    dias_esp = {0:"lun", 1:"mar", 2:"mié", 3:"jue", 4:"vie", 5:"sáb"}
    df_final['Día'] = df_final.apply(lambda row: f"{dias_esp[pd.to_datetime(row['Fecha']).dayofweek]}-{pd.to_datetime(row['Fecha']).strftime('%d-%b')}".lower(), axis=1)

    df_final['Meta Lead Efectivos Programados'] = df_final['Meta Asesor'] * df_final['Agentes Plantilla']
    df_final['Meta Lead Efectivos Log'] = df_final['Meta Asesor'] * df_final['Agentes Log']
    df_final['Diferencia LE'] = df_final['Meta Lead Efectivos Programados'] - df_final['Meta Lead Efectivos Log']
    
    # GAP LE: (Leads Efectivos Acumulados) - (Meta Acumulada) hasta el día
    df_final['GAP LE'] = 0.0
    mask_pasado = df_final['Fecha'] < date.today()
    df_final.loc[mask_pasado, 'GAP LE'] = df_final.loc[mask_pasado, 'Lead Efectivo'].cumsum() - df_final.loc[mask_pasado, 'Meta Día Lead Efectivo'].cumsum()
    
    df_final['% LE'] = np.where(df_final['Tramites'] > 0, df_final['Lead Efectivo'] / df_final['Tramites'], 0)
    df_final['% REM/RECH'] = np.where(df_final['Tramites'] > 0, df_final['Otros'] / df_final['Tramites'], 0)
    
    # PROMEDIO AJUSTADO: Lead Efectivo / Agentes Log
    df_final['Prom'] = np.where(df_final['Agentes Log'] > 0, df_final['Lead Efectivo'] / df_final['Agentes Log'], 0)
    df_final['% Ausentismo'] = np.where(df_final['Agentes Plantilla'] > 0, (df_final['Agentes Plantilla'] - df_final['Agentes Log']) / df_final['Agentes Plantilla'], 0)
    df_final['SPH'] = np.where(df_final['Tiempo Real'] > 0, df_final['Lead Efectivo'] / df_final['Tiempo Real'], 0)
    
    df_final['AP Totales'] = df_final['AP MES'] + df_final['AP COSECHA']
    df_final['% AP dia'] = np.where(df_final['Lead Efectivo'] > 0, df_final['AP Totales'] / df_final['Lead Efectivo'], 0)
    
    # NUEVA COLUMNA: % Aprob Acum Mes
    df_final['% Aprob Acum Mes'] = np.where(df_final['Lead Efectivo'].cumsum() > 0, df_final['AP MES'].cumsum() / df_final['Lead Efectivo'].cumsum(), 0)
    
    # RENOMBRADA: % AP Acum
    df_final['% AP Acum'] = np.where(df_final['Lead Efectivo'].cumsum() > 0, df_final['AP Totales'].cumsum() / df_final['Lead Efectivo'].cumsum(), 0)
    
    df_final['% EVALUADO'] = np.where(df_final['Lead Efectivo'] > 0, df_final['EVALUADO'] / df_final['Lead Efectivo'], 0)
    df_final['% Declinado'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Declinado'] / df_final['Lead Efectivo'], 0)
    df_final['% Cancelado'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Cancelado'] / df_final['Lead Efectivo'], 0)
    df_final['% Pendiente'] = np.where(df_final['Lead Efectivo'] > 0, df_final['Pendiente'] / df_final['Lead Efectivo'], 0)

    columnas_vista = [
        'Día', 'Tramites', 'Lead Efectivo', 'Meta Día Lead Efectivo', 'Meta Lead Efectivos Programados', 'Meta Lead Efectivos Log', 'Diferencia LE', 'GAP LE',
        'Lead No Capturado', 'Lead No Condiciones', 'Otros', '% LE', '% REM/RECH', 'Prom',
        'Agentes Log', 'Agentes Plantilla', '% Ausentismo', 'SPH', 
        'AP MES', 'AP COSECHA', 'AP Totales', '% AP dia', '% Aprob Acum Mes', '% AP Acum',
        'EVALUADO', '% EVALUADO', 'NO GESTIONADO', 'Declinado', '% Declinado', 'Cancelado', '% Cancelado', 'Pendiente', '% Pendiente'
    ]
    df_vista = df_final[[c for c in columnas_vista if c in df_final.columns]].copy()

    # --- FILA DE TOTALES ---
    totales = df_final.sum(numeric_only=True).to_dict()
    totales['Día'] = 'TOTAL'
    totales['% LE'] = totales['Lead Efectivo'] / totales['Tramites'] if totales.get('Tramites', 0) > 0 else 0
    totales['% REM/RECH'] = totales['Otros'] / totales['Tramites'] if totales.get('Tramites', 0) > 0 else 0
    totales['Prom'] = totales['Lead Efectivo'] / totales['Agentes Log'] if totales.get('Agentes Log', 0) > 0 else 0
    totales['% Ausentismo'] = (totales['Agentes Plantilla'] - totales['Agentes Log']) / totales['Agentes Plantilla'] if totales.get('Agentes Plantilla', 0) > 0 else 0
    totales['SPH'] = totales['Lead Efectivo'] / totales.get('Tiempo Real', 1) if totales.get('Tiempo Real', 0) > 0 else 0
    totales['% AP dia'] = totales['AP Totales'] / totales['Lead Efectivo'] if totales.get('Lead Efectivo', 0) > 0 else 0
    totales['% Aprob Acum Mes'] = totales['AP MES'] / totales['Lead Efectivo'] if totales.get('Lead Efectivo', 0) > 0 else 0
    totales['% AP Acum'] = totales['AP Totales'] / totales['Lead Efectivo'] if totales.get('Lead Efectivo', 0) > 0 else 0
    
    df_gap_valido = df_final[df_final['GAP LE'] != 0]
    totales['GAP LE'] = df_gap_valido['GAP LE'].iloc[-1] if not df_gap_valido.empty else 0
    
    df_totales = pd.DataFrame([totales])[df_vista.columns]
    df_vista = pd.concat([df_vista, df_totales], ignore_index=True)

    # --- KPIS GERENCIALES SUPERIORES ---
    st.title(f"📊 Informe Gerencial - {mes_sel_nombre} {año_sel}")
    
    # 1. Cálculo de Última Aprobación MES
    df_aprob_mes = df_final[df_final['AP MES'] > 0]
    if not df_aprob_mes.empty:
        ultimo_dia_ap = pd.to_datetime(df_aprob_mes['Fecha'].max()).strftime('%d-%b').lower()
        pct_ap_acum_mes_ultimo = df_aprob_mes.iloc[-1]['% Aprob Acum Mes']
    else:
        ultimo_dia_ap = "N/A"
        pct_ap_acum_mes_ultimo = 0

    meta_ap_objetivo = 0.045 # 4.5%
    desv_ap = pct_ap_acum_mes_ultimo - meta_ap_objetivo

    # Metas acumuladas a la fecha actual para KPIs
    df_pasado = df_final[df_final['Fecha'] < date.today()]
    meta_le_acum_fecha = df_pasado['Meta Día Lead Efectivo'].sum() if not df_pasado.empty else df_final['Meta Día Lead Efectivo'].sum()
    meta_le_total_mes = df_final['Meta Día Lead Efectivo'].sum()
    pct_cumpl_le_total = (totales['Lead Efectivo'] / meta_le_total_mes) if meta_le_total_mes > 0 else 0
    pct_cumpl_le_fecha = (totales['Lead Efectivo'] / meta_le_acum_fecha) if meta_le_acum_fecha > 0 else 0

    meta_ap_mes_fecha = df_pasado['Meta AP Mes'].sum() if not df_pasado.empty else df_final['Meta AP Mes'].sum()
    meta_ap_cos_fecha = df_pasado['Meta AP Cosecha'].sum() if not df_pasado.empty else df_final['Meta AP Cosecha'].sum()
    meta_ap_tot_fecha = meta_ap_mes_fecha + meta_ap_cos_fecha

    meta_ap_mes_total = df_final['Meta AP Mes'].sum()
    meta_ap_cos_total = df_final['Meta AP Cosecha'].sum()
    meta_ap_tot_total = meta_ap_mes_total + meta_ap_cos_total

    # --- FILA SUPERIOR 1: LEADS, GAP, ÚLTIMA APROBACIÓN Y PLANTA ---
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

    with col_kpi1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Leads Efectivos</div>
            <div class="kpi-value">{int(totales['Lead Efectivo']):,}</div>
            <div class="kpi-subtext">Meta Mes: <b>{int(meta_le_total_mes):,}</b> ({pct_cumpl_le_total:.1%})</div>
            <div class="kpi-subtext">Cumpl. a la Fecha: <span class="kpi-badge-success">{pct_cumpl_le_fecha:.1%}</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col_kpi2:
        badge_class = "kpi-badge-danger" if totales['GAP LE'] < 0 else "kpi-badge-success"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">GAP LE Acumulado</div>
            <div class="kpi-value <span class="{badge_class}">{int(totales['GAP LE']):,}</span></div>
            <div class="kpi-subtext">Esperado a la Fecha: <b>{int(meta_le_acum_fecha):,}</b></div>
            <div class="kpi-subtext">Desviación: <span class="{badge_class}">{totales['GAP LE']/meta_le_acum_fecha:.1%}</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col_kpi3:
        badge_class_ap = "kpi-badge-success" if desv_ap >= 0 else "kpi-badge-danger"
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Últ. Aprobación ({ultimo_dia_ap})</div>
            <div class="kpi-value">{pct_ap_acum_mes_ultimo:.1%}</div>
            <div class="kpi-subtext">Objetivo: <b>4.5%</b></div>
            <div class="kpi-subtext">Desviación: <span class="{badge_class_ap}">{desv_ap:+.1%}</span></div>
        </div>
        """, unsafe_allow_html=True)

    with col_kpi4:
        prom_plantilla = df_final[df_final['Agentes Plantilla'] > 0]['Agentes Plantilla'].mean() if not df_final.empty else 0
        prom_log = df_final[df_final['Agentes Log'] > 0]['Agentes Log'].mean() if not df_final.empty else 0
        pct_aus = (prom_plantilla - prom_log) / prom_plantilla if prom_plantilla > 0 else 0
        
        st.markdown(f"""
        <div class="table-card">
            <div class="table-card-row"><span>Prom. Agentes Plantilla:</span> <b>{prom_plantilla:.0f}</b></div>
            <div class="table-card-row"><span>Prom. Agentes Log:</span> <b>{prom_log:.0f}</b></div>
            <div class="table-card-row"><span>% Ausentismo Prom.:</span> <b style="color:#d97706">{pct_aus:.1%}</b></div>
        </div>
        """, unsafe_allow_html=True)

    # --- FILA SUPERIOR 2: APROBACIONES DETALLADAS VS METAS ---
    col_ap1, col_ap2, col_ap3 = st.columns(3)

    with col_ap1:
        cumpl_ap_mes_fecha = totales['AP MES'] / meta_ap_mes_fecha if meta_ap_mes_fecha > 0 else 0
        cumpl_ap_mes_tot = totales['AP MES'] / meta_ap_mes_total if meta_ap_mes_total > 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">AP MES (Total)</div>
            <div class="kpi-value">{int(totales['AP MES'])}</div>
            <div class="kpi-subtext">Meta a la Fecha: <b>{int(meta_ap_mes_fecha)}</b> ({cumpl_ap_mes_fecha:.1%})</div>
            <div class="kpi-subtext">Meta Total Mes: <b>{int(meta_ap_mes_total)}</b> ({cumpl_ap_mes_tot:.1%})</div>
        </div>
        """, unsafe_allow_html=True)

    with col_ap2:
        cumpl_ap_cos_fecha = totales['AP COSECHA'] / meta_ap_cos_fecha if meta_ap_cos_fecha > 0 else 0
        cumpl_ap_cos_tot = totales['AP COSECHA'] / meta_ap_cos_total if meta_ap_cos_total > 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">AP Cosecha (Total)</div>
            <div class="kpi-value">{int(totales['AP COSECHA'])}</div>
            <div class="kpi-subtext">Meta a la Fecha: <b>{int(meta_ap_cos_fecha)}</b> ({cumpl_ap_cos_fecha:.1%})</div>
            <div class="kpi-subtext">Meta Total Mes: <b>{int(meta_ap_cos_total)}</b> ({cumpl_ap_cos_tot:.1%})</div>
        </div>
        """, unsafe_allow_html=True)

    with col_ap3:
        cumpl_ap_tot_fecha = totales['AP Totales'] / meta_ap_tot_fecha if meta_ap_tot_fecha > 0 else 0
        cumpl_ap_tot_tot = totales['AP Totales'] / meta_ap_tot_total if meta_ap_tot_total > 0 else 0
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">AP Totales</div>
            <div class="kpi-value">{int(totales['AP Totales'])}</div>
            <div class="kpi-subtext">Meta a la Fecha: <b>{int(meta_ap_tot_fecha)}</b> ({cumpl_ap_tot_fecha:.1%})</div>
            <div class="kpi-subtext">Meta Total Mes: <b>{int(meta_ap_tot_total)}</b> ({cumpl_ap_tot_tot:.1%})</div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- FORMATO DE LA TABLA ---
    format_dict = {}
    for c in df_vista.columns:
        if c == 'Día': continue
        if '%' in c or c in ['% Aprob Acum Mes', '% AP Acum']: format_dict[c] = '{:.1%}'
        elif c in ['Prom', 'SPH']: format_dict[c] = '{:.1f}'
        else: format_dict[c] = '{:.0f}'

    def semaforo_le(val):
        if not isinstance(val, (float, int)): return ''
        if val >= 0.90: return 'background-color: #c6e0b4; color: black;'
        if val >= 0.80: return 'background-color: #ffe699; color: black;'
        if val > 0: return 'background-color: #ffc000; color: black;'
        return ''

    styler = df_vista.style.format(format_dict)\
                           .map(semaforo_le, subset=['% LE'] if '% LE' in df_vista.columns else [])\
                           .set_properties(**{'text-align': 'center', 'font-size': '13px'})
                           
    styler = styler.apply(lambda x: ['font-weight: bold; background-color: #f0f2f6' if x.name == len(df_vista)-1 else '' for i in x], axis=1)

    st.dataframe(styler, use_container_width=True, height=750, hide_index=True)
else:
    st.warning("⚠️ No se encontró la hoja de Ventas o le faltan columnas.")
