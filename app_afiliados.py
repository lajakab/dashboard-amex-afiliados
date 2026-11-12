import calendar
from datetime import date, datetime, timedelta
import math
import re
import holidays
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="Informe Gerencial & Operativo Amex", layout="wide")

# CSS para Tarjetas Gerenciales, Contenedores, Centrado Absoluto y Panel Gerencial
st.markdown(
    """
<style>
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 6px;
    }
    .kpi-title {
        font-size: 11px;
        color: #64748b;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }
    .kpi-value {
        font-size: 24px;
        font-weight: 800;
        color: #0f172a;
        line-height: 1.1;
    }
    .kpi-subtext {
        font-size: 11px;
        color: #475569;
        margin-top: 3px;
    }
    .kpi-badge-success { color: #22c55e; font-weight: 700; }
    .kpi-badge-warning { color: #f59e0b; font-weight: 700; }
    .kpi-badge-danger { color: #ef4444; font-weight: 700; }

    .table-card {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 10px 12px;
        height: 100%;
    }
    .table-card-row {
        display: flex;
        justify-content: space-between;
        padding: 4px 0;
        border-bottom: 1px solid #e2e8f0;
        font-size: 12px;
    }
    .table-card-row:last-child { border-bottom: none; }
    
    /* Forzar centrado absoluto de celdas y encabezados en la tabla */
    [data-testid="stDataFrame"] td, 
    [data-testid="stDataFrame"] th,
    div[data-testid="stDataFrame"] div[role="gridcell"],
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        text-align: center !important;
        justify-content: center !important;
    }

    /* Estilos Especiales para la Ficha Gerencial de Diagnóstico de Desviación */
    .diag-box {
        background-color: #ffffff;
        border: 1.5px solid #cbd5e1;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-top: 10px;
    }
    .diag-header {
        font-size: 15px;
        font-weight: 800;
        color: #1e293b;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 8px;
        margin-bottom: 12px;
    }

    /* Ficha Gerencial Diferenciada para Funnel */
    .diag-box-funnel {
        background-color: #f8fafc;
        border: 1.5px solid #6366f1;
        border-radius: 10px;
        padding: 16px 20px;
        box-shadow: 0 4px 8px -1px rgba(99, 102, 241, 0.1);
        margin-top: 15px;
    }
    .diag-header-funnel {
        font-size: 15px;
        font-weight: 800;
        color: #312e81;
        border-bottom: 2px solid #c7d2fe;
        padding-bottom: 8px;
        margin-bottom: 12px;
    }

    .arrow-badge-up {
        background-color: #dcfce7;
        color: #15803d;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 14px;
        display: inline-block;
    }
    .arrow-badge-down {
        background-color: #fee2e2;
        color: #b91c1c;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 14px;
        display: inline-block;
    }
    .causal-item {
        font-size: 13px;
        color: #334155;
        margin-bottom: 6px;
        line-height: 1.4;
    }
</style>
""",
    unsafe_allow_html=True,
)

# Interpolación en 2 puntos
def interpolate_color_2pt(val, vmin, vmax, rgb_low, rgb_high):
  if pd.isna(val) or vmin == vmax:
    return ""
  norm = (val - vmin) / (vmax - vmin)
  norm = max(0.0, min(1.0, norm))
  r = int(rgb_low[0] + norm * (rgb_high[0] - rgb_low[0]))
  g = int(rgb_low[1] + norm * (rgb_high[1] - rgb_low[1]))
  b = int(rgb_low[2] + norm * (rgb_high[2] - rgb_low[2]))
  return f"background-color: rgb({r}, {g}, {b}); color: #0f172a;"

# Interpolación en 3 puntos con Naranja Intermedio
def interpolate_color_3pt(val, vmin, vmax, rgb_low, rgb_mid, rgb_high):
  if pd.isna(val) or vmin == vmax:
    return ""
  norm = (val - vmin) / (vmax - vmin)
  norm = max(0.0, min(1.0, norm))
  if norm <= 0.5:
    t = norm / 0.5
    r = int(rgb_low[0] + t * (rgb_mid[0] - rgb_low[0]))
    g = int(rgb_low[1] + t * (rgb_mid[1] - rgb_low[1]))
    b = int(rgb_low[2] + t * (rgb_mid[2] - rgb_low[2]))
  else:
    t = (norm - 0.5) / 0.5
    r = int(rgb_mid[0] + t * (rgb_high[0] - rgb_mid[0]))
    g = int(rgb_mid[1] + t * (rgb_high[1] - rgb_mid[1]))
    b = int(rgb_high[2] + t * (rgb_high[2] - rgb_mid[2]))
  return f"background-color: rgb({r}, {g}, {b}); color: #0f172a;"

# Termómetros visuales
def render_pila_bar(pct):
  c1 = "#ef4444" if pct > 0 else "#e2e8f0"
  c2 = "#f59e0b" if pct >= 0.25 else "#e2e8f0"
  c3 = "#84cc16" if pct >= 0.50 else "#e2e8f0"
  c4 = "#22c55e" if pct >= 0.75 else "#e2e8f0"
  return f"""<div style="display:flex; gap:3px; height:7px; width:100%; margin-top:8px;">
        <div style="flex:1; background:{c1}; border-radius:3px 0 0 3px;"></div>
        <div style="flex:1; background:{c2};"></div>
        <div style="flex:1; background:{c3};"></div>
        <div style="flex:1; background:{c4}; border-radius:0 3px 3px 0;"></div>
    </div>"""

def render_gauge_svg(pct):
  p = min(max(pct, 0.0), 1.0)
  rad = p * math.pi
  nx = 50 - 28 * math.cos(rad)
  ny = 42 - 28 * math.sin(rad)
  return f"""<div style="text-align:center; margin-top:4px;">
        <svg width="85" height="46" viewBox="0 0 100 50">
            <path d="M 12 42 A 38 38 0 0 1 36.8 11.2" fill="none" stroke="#ef4444" stroke-width="7" stroke-linecap="round"/>
            <path d="M 36.8 11.2 A 38 38 0 0 1 63.2 11.2" fill="none" stroke="#f59e0b" stroke-width="7"/>
            <path d="M 63.2 11.2 A 38 38 0 0 1 88 42" fill="none" stroke="#22c55e" stroke-width="7" stroke-linecap="round"/>
            <circle cx="50" cy="42" r="3.5" fill="#0f172a"/>
            <line x1="50" y1="42" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#0f172a" stroke-width="2.5" stroke-linecap="round"/>
        </svg>
    </div>"""

@st.cache_data
def cargar_pestanas():
  def load_pq(name):
    try:
      return pd.read_parquet(name)
    except Exception:
      return pd.DataFrame()

  df_c = load_pq("calls.parquet")
  if df_c.empty:
    df_c = load_pq("llamadas.parquet")

  return (
      load_pq("ventas.parquet"),
      load_pq("planta.parquet"),
      load_pq("seg_ppto.parquet"),
      load_pq("malla_día.parquet"),
      df_c,
  )

@st.cache_data
def cargar_distribucion():
  nombres_posibles = [
      "DISTRIBUCION AMEX.xlsx",
      "DISTRIBUCIÓN AMEX.xlsx",
      "distribucion_amex.xlsx",
      "distribucion.xlsx",
      "distribucion.parquet",
  ]
  for nombre in nombres_posibles:
    try:
      if nombre.endswith(".parquet"):
        df = pd.read_parquet(nombre)
      else:
        df = pd.read_excel(nombre)
      if not df.empty:
        return df
    except Exception:
      continue
  return pd.DataFrame()

df_ventas, df_planta, df_ppto, df_malla, df_calls = cargar_pestanas()
df_distribucion = cargar_distribucion()

# =========================================================================
# ⚙️ PREPROCESAMIENTO GLOBAL DE DF_VENTAS Y LLAMADAS
# =========================================================================
col_id_dist = None
col_sup_dist = None
col_agt_dist = None

if not df_distribucion.empty:
  col_id_dist = next((c for c in df_distribucion.columns if str(c).strip().lower() in ["id_per", "id_user", "id"]), None)
  col_sup_dist = next((c for c in df_distribucion.columns if str(c).strip().lower() in ["supervisor", "supervisores"]), None)
  col_agt_dist = next((c for c in df_distribucion.columns if str(c).strip().lower() in ["agente", "asesor", "nombre"]), None)

  if col_id_dist:
    df_distribucion["id_per_clean"] = pd.to_numeric(df_distribucion[col_id_dist], errors="coerce")
    if col_sup_dist: df_distribucion["Supervisor"] = df_distribucion[col_sup_dist]
    if col_agt_dist: df_distribucion["agente"] = df_distribucion[col_agt_dist]

if not df_calls.empty:
  col_c_id = next((c for c in df_calls.columns if str(c).strip().lower() in ["id_user", "id_per", "id", "c"]), df_calls.columns[2] if len(df_calls.columns) > 2 else None)
  col_c_val = next((c for c in df_calls.columns if str(c).strip().lower() in ["calls", "llamadas_totales", "llamadas", "val", "e"]), df_calls.columns[4] if len(df_calls.columns) > 4 else None)
  col_c_f = next((c for c in df_calls.columns if str(c).strip().lower() in ["fecha", "f_call", "fecha_llamada", "d"]), df_calls.columns[3] if len(df_calls.columns) > 3 else None)

  df_calls["id_per_clean"] = pd.to_numeric(df_calls[col_c_id], errors="coerce") if col_c_id else np.nan
  df_calls["F_CALL"] = pd.to_datetime(df_calls[col_c_f], errors="coerce").dt.date if col_c_f else pd.NaT
  df_calls["Calls_Val"] = pd.to_numeric(df_calls[col_c_val], errors="coerce").fillna(0) if col_c_val else 0

if not df_ventas.empty and len(df_ventas.columns) > 40:
  col_fvta = next((i for i, c in enumerate(df_ventas.columns) if str(c).strip().upper() in ["FECHA VENTA", "F_VTA", "FECHA_VENTA", "FECHA VTA"]), 4)
  col_c_has_le = (len(df_ventas.columns) > 2 and (df_ventas.iloc[:, 2].astype(str).str.strip().str.upper() == "LEAD EFECTIVO").any())
  col_estado = (2 if col_c_has_le else next((i for i, c in enumerate(df_ventas.columns) if str(c).strip().upper() in ["ESTADO", "ESTADO LEAD", "ESTADO_LEAD", "STATUS"]), 7))
  col_dec = next((i for i, c in enumerate(df_ventas.columns) if str(c).strip().upper() in ["DECISION", "DECISIÓN", "AT", "DECISION FINAL", "ESTADO DECISION", "DECISION_FINAL"]), 45)
  col_bx = 75 if len(df_ventas.columns) > 75 else -1

  df_ventas["F_VTA"] = pd.to_datetime(df_ventas.iloc[:, col_fvta], errors="coerce").dt.date
  df_ventas["ESTADO"] = df_ventas.iloc[:, col_estado].astype(str).str.strip().str.upper()
  df_ventas["DECISION"] = df_ventas.iloc[:, col_dec].astype(str).str.strip().str.upper()

  if col_bx != -1:
    bx_str = df_ventas.iloc[:, col_bx].astype(str).str.strip()
    df_ventas["BX_EMPTY"] = (df_ventas.iloc[:, col_bx].isna() | (bx_str == "") | (bx_str.str.upper() == "NAN") | (bx_str == "None"))
  else:
    dec_str = df_ventas.iloc[:, col_dec].astype(str).str.strip()
    df_ventas["BX_EMPTY"] = (df_ventas.iloc[:, col_dec].isna() | (dec_str == "") | (dec_str == "-") | (dec_str.str.upper() == "NAN"))

  col_fdec = next((i for i, c in enumerate(df_ventas.columns) if str(c).strip().upper() in ["FECHA DECISION", "FECHA DECISIÓN", "F_DEC", "FECHA_DECISION", "FECHA DEC"]), 49 if len(df_ventas.columns) > 49 else -1)

  if col_fdec != -1 and len(df_ventas.columns) > col_fdec:
    df_ventas["F_DEC"] = pd.to_datetime(df_ventas.iloc[:, col_fdec], errors="coerce").dt.date
  else:
    df_ventas["F_DEC"] = pd.NaT

  df_ventas["F_DEC_EFF"] = df_ventas["F_DEC"].fillna(df_ventas["F_VTA"])

  col_id_vta = next((c for c in df_ventas.columns if str(c).strip().lower() in ["id_per", "id_user", "id"]), None)
  if col_id_vta:
    df_ventas["id_per_clean"] = pd.to_numeric(df_ventas[col_id_vta], errors="coerce")

# NAVEGACIÓN PRINCIPAL EN EL SIDEBAR
st.sidebar.image(
    "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png",
    width=150,
)
st.sidebar.title("📌 Navegación")
opcion_hoja = st.sidebar.radio(
    "Seleccione la Vista:",
    [
        "📊 Informe Gerencial por Día",
        "👥 Operación - Asesores & Supervisores",
        "🗓️ Módulo 3: Productividad Diaria"
    ]
)

# =========================================================================
# 📊 MÓDULO 1: INFORME GERENCIAL POR DÍA (SIN NINGÚN CAMBIO)
# =========================================================================
if opcion_hoja == "📊 Informe Gerencial por Día":
  if not df_ventas.empty and len(df_ventas.columns) > 40:
    st.sidebar.header("🔍 Filtros General")

    fechas_validas = pd.Series(df_ventas["F_VTA"]).dropna()
    años_disp = (sorted(pd.to_datetime(fechas_validas).dt.year.unique()) if not fechas_validas.empty else [date.today().year])
    año_sel = st.sidebar.selectbox("Año", años_disp, index=len(años_disp) - 1)

    meses_disp = (sorted(pd.to_datetime(fechas_validas[pd.to_datetime(fechas_validas).dt.year == año_sel]).dt.month.unique()) if not fechas_validas.empty else [date.today().month])
    nombres_meses = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    mes_formateado = [nombres_meses[m] for m in meses_disp if m in nombres_meses]
    mes_sel_nombre = (st.sidebar.selectbox("Mes", mes_formateado, index=len(mes_formateado) - 1) if mes_formateado else "Noviembre")
    mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]

    agentes_contratados_ref = 71 if mes_sel == 11 else (74 if mes_sel == 10 else 71)
    agentes_contratados_input = st.sidebar.number_input("Agentes Contratados (Base)", min_value=1, max_value=200, value=agentes_contratados_ref)
    ausentismo_teorico_input = (st.sidebar.number_input("% Ausentismo Esperado (Contratados)", min_value=0.0, max_value=30.0, value=4.0, step=0.5) / 100.0)

    if "asesor" in [str(c).lower() for c in df_ventas.columns]:
      col_as = next(c for c in df_ventas.columns if "asesor" in str(c).lower())
      asesores = ["Todos"] + sorted(df_ventas[col_as].dropna().astype(str).unique().tolist())
      asesor_sel = st.sidebar.selectbox("Asesor", asesores)
      if asesor_sel != "Todos":
        df_ventas = df_ventas[df_ventas[col_as] == asesor_sel]

    def parse_fecha_sucia(serie, año):
      def extract_date(val):
        if pd.isna(val) or val == "" or val == "nan": return pd.NaT
        val_str = str(val).strip().lower()
        if re.match(r"^\d{4}-\d{2}-\d{2}", val_str):
          try: return pd.to_datetime(val_str[:10]).date()
          except: pass
        m = re.search(r"(\d{1,2})-([a-z]{3})", val_str)
        if m:
          d, mes_str = int(m.group(1)), m.group(2)
          m_num = {"ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "sep": 9, "oct": 10, "nov": 11, "dic": 12}.get(mes_str, 1)
          try: return date(año, m_num, d)
          except: pass
        try: return pd.to_datetime(val, errors="coerce").date()
        except: return pd.NaT
      return serie.apply(extract_date)

    festivos_mx = holidays.Mexico(years=año_sel)
    num_dias = calendar.monthrange(año_sel, mes_sel)[1]
    df_cal = pd.DataFrame({"Fecha": [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]})
    df_cal["Día_Semana"] = pd.to_datetime(df_cal["Fecha"]).dt.dayofweek
    df_cal["Es_Festivo"] = pd.to_datetime(df_cal["Fecha"]).apply(lambda x: x in festivos_mx)
    df_cal = df_cal[~((df_cal["Día_Semana"] == 6) | (df_cal["Es_Festivo"]))].copy()

    dias_nombres_map = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado"}
    df_cal["Nombre_Día"] = df_cal["Día_Semana"].map(dias_nombres_map)
    df_cal["Día_Hábil"] = [f"DH {i}" for i in range(1, len(df_cal) + 1)]

    dias_semana_sel = st.sidebar.multiselect("Día de la Semana", options=list(dias_nombres_map.values()), default=[])
    if dias_semana_sel:
      df_cal = df_cal[df_cal["Nombre_Día"].isin(dias_semana_sel)]

    fechas_mes_disp = sorted(df_cal["Fecha"].unique())
    fechas_sel = st.sidebar.multiselect("Fechas Específicas", options=fechas_mes_disp, format_func=lambda x: x.strftime("%d-%b-%Y"))
    if fechas_sel:
      df_cal = df_cal[df_cal["Fecha"].isin(fechas_sel)]

    if not df_cal.empty:
      min_f, max_f = df_cal["Fecha"].min(), df_cal["Fecha"].max()
      rango_f = st.sidebar.date_input("Rango de Fechas", value=(min_f, max_f), min_value=min_f, max_value=max_f)
      if isinstance(rango_f, tuple) and len(rango_f) == 2:
        df_cal = df_cal[(df_cal["Fecha"] >= rango_f[0]) & (df_cal["Fecha"] <= rango_f[1])]

    if not df_planta.empty and len(df_planta.columns) > 2:
      df_planta["Fecha"] = pd.to_datetime(df_planta.iloc[:, 0], errors="coerce").dt.date
      df_planta["Agentes Plantilla"] = pd.to_numeric(df_planta.iloc[:, 1], errors="coerce").fillna(0)
      df_planta["Agentes Log"] = pd.to_numeric(df_planta.iloc[:, 2], errors="coerce").fillna(0)
      df_cal = pd.merge(df_cal, df_planta.groupby("Fecha").agg({"Agentes Plantilla": "max", "Agentes Log": "max"}).reset_index(), on="Fecha", how="left")

    if not df_ppto.empty and len(df_ppto.columns) > 35:
      df_ppto["Fecha"] = parse_fecha_sucia(df_ppto.iloc[:, 35], año_sel)
      df_ppto["Meta Día Lead Efectivo"] = (pd.to_numeric(df_ppto.iloc[:, 36], errors="coerce").fillna(0) if len(df_ppto.columns) > 36 else 0)
      df_ppto["Meta Asesor"] = (pd.to_numeric(df_ppto.iloc[:, 37], errors="coerce").fillna(0) if len(df_ppto.columns) > 37 else 0)
      df_ppto["Meta AP Mes"] = (pd.to_numeric(df_ppto.iloc[:, 38], errors="coerce").fillna(0) if len(df_ppto.columns) > 38 else 0)
      df_ppto["Meta AP Cosecha"] = (pd.to_numeric(df_ppto.iloc[:, 39], errors="coerce").fillna(0) if len(df_ppto.columns) > 39 else 0)
      df_cal = pd.merge(df_cal, df_ppto.groupby("Fecha").agg({"Meta Día Lead Efectivo": "max", "Meta Asesor": "max", "Meta AP Mes": "max", "Meta AP Cosecha": "max"}).reset_index(), on="Fecha", how="left")

    if not df_malla.empty and len(df_malla.columns) > 13:
      df_malla["Fecha"] = parse_fecha_sucia(df_malla.iloc[:, 13], año_sel)
      col_tr_idx = (65 if len(df_malla.columns) > 65 else next((i for i, c in enumerate(df_malla.columns) if "tiempo" in str(c).lower()), -1))
      if col_tr_idx != -1 and len(df_malla.columns) > col_tr_idx:
        df_malla["Tiempo Real"] = pd.to_numeric(df_malla.iloc[:, col_tr_idx], errors="coerce").fillna(0)
        df_cal = pd.merge(df_cal, df_malla.groupby("Fecha").agg({"Tiempo Real": "sum"}).reset_index(), on="Fecha", how="left")

    for col in ["Agentes Plantilla", "Agentes Log", "Meta Día Lead Efectivo", "Meta Asesor", "Meta AP Mes", "Meta AP Cosecha", "Tiempo Real"]:
      if col not in df_cal.columns: df_cal[col] = 0
    df_cal = df_cal.fillna(0)

    df_ventas_vta = df_ventas[(pd.to_datetime(df_ventas["F_VTA"]).dt.year == año_sel) & (pd.to_datetime(df_ventas["F_VTA"]).dt.month == mes_sel)]

    def agrupar_ventas_dia(x):
      is_le = x["ESTADO"] == "LEAD EFECTIVO"
      dec = x["DECISION"].astype(str).str.strip().str.upper()
      is_eval = is_le & dec.isin(["A", "D", "P", "C"])
      is_no_gest = is_le & x["BX_EMPTY"]
      return pd.Series({
          "Tramites": len(x),
          "Lead Efectivo": is_le.sum(),
          "Lead No Capturado": (x["ESTADO"] == "LEAD NO CAPTURADO").sum(),
          "Lead No Condiciones": (x["ESTADO"] == "LEAD NO CONDICIONES").sum(),
          "Otros": (~x["ESTADO"].isin(["LEAD EFECTIVO", "LEAD NO CAPTURADO", "LEAD NO CONDICIONES", "", "NAN"])).sum(),
          "EVALUADO": is_eval.sum(),
          "NO GESTIONADO": is_no_gest.sum(),
          "Declinado": (is_le & (dec == "D")).sum(),
          "Cancelado": (is_le & (dec == "C")).sum(),
          "Pendiente": (is_le & (dec == "P")).sum(),
      })

    agrup_vta = df_ventas_vta.groupby("F_VTA").apply(agrupar_ventas_dia).reset_index().rename(columns={"F_VTA": "Fecha"})

    df_ap_mes = df_ventas[(pd.to_datetime(df_ventas["F_VTA"]).dt.year == año_sel) & (pd.to_datetime(df_ventas["F_VTA"]).dt.month == mes_sel) & (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.year == año_sel) & (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.month == mes_sel) & (df_ventas["DECISION"] == "A")]
    agrup_ap_mes = df_ap_mes.groupby("F_VTA").size().reset_index(name="AP MES").rename(columns={"F_VTA": "Fecha"})

    inicio_mes_sel = date(año_sel, mes_sel, 1)
    df_ap_cos = df_ventas[(pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.year == año_sel) & (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.month == mes_sel) & (pd.to_datetime(df_ventas["F_VTA"]) < pd.Timestamp(inicio_mes_sel)) & (df_ventas["DECISION"] == "A")]
    agrup_ap_cos = df_ap_cos.groupby("F_DEC_EFF").size().reset_index(name="AP COSECHA").rename(columns={"F_DEC_EFF": "Fecha"})

    df_final = pd.merge(df_cal, agrup_vta, on="Fecha", how="left").fillna(0)
    df_final = pd.merge(df_final, agrup_ap_mes, on="Fecha", how="left").fillna(0)
    df_final = pd.merge(df_final, agrup_ap_cos, on="Fecha", how="left").fillna(0)

    dias_esp = {0: "lun", 1: "mar", 2: "mié", 3: "jue", 4: "vie", 5: "sáb"}
    df_final["Día"] = df_final.apply(lambda row: (f"{dias_esp[pd.to_datetime(row['Fecha']).dayofweek]}-{pd.to_datetime(row['Fecha']).strftime('%d-%b')}".lower()), axis=1)

    df_final["Meta Lead Efectivos Programados"] = df_final["Meta Asesor"] * df_final["Agentes Plantilla"]
    df_final["Meta Lead Efectivos Log"] = df_final["Meta Asesor"] * df_final["Agentes Log"]
    df_final["Diferencia LE"] = df_final["Meta Lead Efectivos Programados"] - df_final["Meta Lead Efectivos Log"]
    
    df_final["GAP LE"] = 0.0
    mask_pasado = df_final["Fecha"] < date.today()
    df_final.loc[mask_pasado, "GAP LE"] = (df_final.loc[mask_pasado, "Lead Efectivo"].cumsum() - df_final.loc[mask_pasado, "Meta Día Lead Efectivo"].cumsum())

    df_final["% LE"] = np.where(df_final["Tramites"] > 0, df_final["Lead Efectivo"] / df_final["Tramites"], 0)
    df_final["% REM/RECH"] = np.where(df_final["Tramites"] > 0, df_final["Otros"] / df_final["Tramites"], 0)
    df_final["Prom"] = np.where(df_final["Agentes Log"] > 0, df_final["Lead Efectivo"] / df_final["Agentes Log"], 0)
    df_final["% Ausentismo"] = np.where(df_final["Agentes Plantilla"] > 0, (df_final["Agentes Plantilla"] - df_final["Agentes Log"]) / df_final["Agentes Plantilla"], 0)
    df_final["SPH"] = np.where(df_final["Agentes Log"] > 0, df_final["Lead Efectivo"] / df_final["Agentes Log"], 0)
    df_final["AP Totales"] = df_final["AP MES"] + df_final["AP COSECHA"]
    df_final["% AP dia"] = np.where(df_final["Lead Efectivo"] > 0, df_final["AP MES"] / df_final["Lead Efectivo"], 0)
    df_final["% Aprob Acum Mes"] = np.where(df_final["Lead Efectivo"].cumsum() > 0, df_final["AP MES"].cumsum() / df_final["Lead Efectivo"].cumsum(), 0)
    df_final["% AP Acum"] = np.where(df_final["Lead Efectivo"].cumsum() > 0, df_final["AP Totales"].cumsum() / df_final["Lead Efectivo"].cumsum(), 0)
    df_final["% EVALUADO"] = np.where(df_final["Lead Efectivo"] > 0, df_final["EVALUADO"] / df_final["Lead Efectivo"], 0)
    df_final["% Declinado"] = np.where(df_final["Lead Efectivo"] > 0, df_final["Declinado"] / df_final["Lead Efectivo"], 0)
    df_final["% Cancelado"] = np.where(df_final["Lead Efectivo"] > 0, df_final["Cancelado"] / df_final["Lead Efectivo"], 0)
    df_final["% Pendiente"] = np.where(df_final["Lead Efectivo"] > 0, df_final["Pendiente"] / df_final["Lead Efectivo"], 0)

    columnas_vista = [
        "Día", "Tramites", "Lead Efectivo", "Meta Día Lead Efectivo", "Meta Lead Efectivos Programados",
        "Meta Lead Efectivos Log", "Diferencia LE", "GAP LE", "Lead No Capturado", "Lead No Condiciones",
        "Otros", "% LE", "% REM/RECH", "Prom", "Agentes Log", "Agentes Plantilla", "% Ausentismo",
        "SPH", "AP MES", "AP COSECHA", "AP Totales", "% AP dia", "% Aprob Acum Mes", "% AP Acum",
        "EVALUADO", "% EVALUADO", "NO GESTIONADO", "Declinado", "% Declinado", "Cancelado", "% Cancelado",
        "Pendiente", "% Pendiente",
    ]
    df_vista = df_final[[c for c in columnas_vista if c in df_final.columns]].copy()

    rename_dict = {
        "Lead Efectivo": "LE",
        "Meta Día Lead Efectivo": "Meta LE",
        "Meta Lead Efectivos Programados": "Meta LE Prog",
        "Meta Lead Efectivos Log": "Meta LE Log",
        "Diferencia LE": "Dif LE",
        "GAP LE": "GAP LE",
        "Lead No Capturado": "No Cap",
        "Lead No Condiciones": "No Cond",
        "Agentes Plantilla": "Agt Plan",
        "Agentes Log": "Agt Log",
        "% Ausentismo": "% Aus",
        "AP MES": "AP Mes",
        "AP COSECHA": "AP Cos",
        "AP Totales": "AP Tot",
        "% AP dia": "% AP Día",
        "% Aprob Acum Mes": "% AP Acum M",
        "% AP Acum": "% AP Tot",
        "EVALUADO": "Eval",
        "% EVALUADO": "% Eval",
        "NO GESTIONADO": "No Gest",
        "Declinado": "Decl",
        "% Declinado": "% Decl",
        "Cancelado": "Canc",
        "% Cancelado": "% Canc",
        "Pendiente": "Pend",
        "% Pendiente": "% Pend"
    }
    df_vista = df_vista.rename(columns=rename_dict)

    totales = df_final.sum(numeric_only=True).to_dict()
    totales["Día"] = "TOTAL"
    totales["% LE"] = (totales["Lead Efectivo"] / totales["Tramites"] if totales.get("Tramites", 0) > 0 else 0)
    totales["% REM/RECH"] = (totales["Otros"] / totales["Tramites"] if totales.get("Tramites", 0) > 0 else 0)
    totales["Prom"] = (totales["Lead Efectivo"] / totales["Agentes Log"] if totales.get("Agentes Log", 0) > 0 else 0)
    totales["% Ausentismo"] = ((totales["Agentes Plantilla"] - totales["Agentes Log"]) / totales["Agentes Plantilla"] if totales.get("Agentes Plantilla", 0) > 0 else 0)
    totales["SPH"] = (totales["Lead Efectivo"] / totales["Agentes Log"] if totales.get("Agentes Log", 0) > 0 else 0)
    totales["% AP dia"] = (totales["AP MES"] / totales["Lead Efectivo"] if totales.get("Lead Efectivo", 0) > 0 else 0)
    totales["% Aprob Acum Mes"] = (totales["AP MES"] / totales["Lead Efectivo"] if totales.get("Lead Efectivo", 0) > 0 else 0)
    totales["% AP Acum"] = (totales["AP Totales"] / totales["Lead Efectivo"] if totales.get("Lead Efectivo", 0) > 0 else 0)

    df_gap_valido = df_final[df_final["GAP LE"] != 0]
    totales["GAP LE"] = (df_gap_valido["GAP LE"].iloc[-1] if not df_gap_valido.empty else 0)

    totales_rename = {rename_dict.get(k, k): v for k, v in totales.items()}
    df_totales = pd.DataFrame([totales_rename])[df_vista.columns]
    df_vista = pd.concat([df_vista, df_totales], ignore_index=True)

    st.title(f"📊 Informe Gerencial - {mes_sel_nombre} {año_sel}")

    df_aprob_mes = df_final[df_final["AP MES"] > 0]
    if not df_aprob_mes.empty:
      fecha_corte = df_aprob_mes["Fecha"].max()
      ultimo_dia_ap = pd.to_datetime(fecha_corte).strftime("%d-%b").lower()
      pct_ap_acum_mes_ultimo = df_final[df_final["Fecha"] == fecha_corte].iloc[0]["% Aprob Acum Mes"]
    else:
      fecha_corte = date.today()
      ultimo_dia_ap = "N/A"
      pct_ap_acum_mes_ultimo = 0

    meta_ap_objetivo = 0.045
    desv_ap = pct_ap_acum_mes_ultimo - meta_ap_objetivo

    df_pasado = df_final[df_final["Fecha"] < date.today()]
    if df_pasado.empty: df_pasado = df_final[df_final["Fecha"] <= date.today()]
    if df_pasado.empty: df_pasado = df_final

    meta_le_acum_fecha = df_pasado["Meta Día Lead Efectivo"].sum()
    meta_le_total_mes = df_final["Meta Día Lead Efectivo"].sum()
    leads_acum_fecha = df_pasado["Lead Efectivo"].sum()

    pct_cumpl_le_total = ((totales["Lead Efectivo"] / meta_le_total_mes) if meta_le_total_mes > 0 else 0)
    pct_cumpl_le_fecha = ((totales["Lead Efectivo"] / meta_le_acum_fecha) if meta_le_acum_fecha > 0 else 0)
    pct_gap_cumpl = ((leads_acum_fecha / meta_le_acum_fecha) if meta_le_acum_fecha > 0 else 0)

    df_hasta_ap = df_final[df_final["Fecha"] <= fecha_corte]
    meta_ap_mes_fecha = df_hasta_ap["Meta AP Mes"].sum()
    meta_ap_cos_fecha = df_hasta_ap["Meta AP Cosecha"].sum()
    meta_ap_tot_fecha = meta_ap_mes_fecha + meta_ap_cos_fecha

    meta_ap_mes_total = df_final["Meta AP Mes"].sum()
    meta_ap_cos_total = df_final["Meta AP Cosecha"].sum()
    meta_ap_tot_total = meta_ap_mes_total + meta_ap_cos_total

    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

    with col_kpi1:
      badg = ("kpi-badge-danger" if pct_cumpl_le_fecha < 0.80 else ("kpi-badge-warning" if pct_cumpl_le_fecha < 1.0 else "kpi-badge-success"))
      st.markdown(
          f"""<div class="kpi-card">
              <div class="kpi-title">Leads Efectivos</div>
              <div class="kpi-value">{int(totales['Lead Efectivo']):,}</div>
              <div class="kpi-subtext">Meta Mes: <b>{int(meta_le_total_mes):,}</b> ({pct_cumpl_le_total:.1%})</div>
              <div class="kpi-subtext">Cumpl. a la Fecha: <span class="{badg}">{pct_cumpl_le_fecha:.1%}</span></div>
              {render_pila_bar(pct_cumpl_le_fecha)}
          </div>""", unsafe_allow_html=True,
      )

    with col_kpi2:
      badg = "kpi-badge-danger" if totales["GAP LE"] < 0 else "kpi-badge-success"
      badg_cumpl = ("kpi-badge-danger" if pct_gap_cumpl < 0.80 else ("kpi-badge-warning" if pct_gap_cumpl < 1.0 else "kpi-badge-success"))
      st.markdown(
          f"""<div class="kpi-card">
              <div class="kpi-title">GAP LE Acumulado</div>
              <div class="kpi-value"><span class="{badg}">{int(totales['GAP LE']):,}</span></div>
              <div class="kpi-subtext">Esperado a la Fecha: <b>{int(meta_le_acum_fecha):,}</b></div>
              <div class="kpi-subtext">Cumpl. a la Fecha: <span class="{badg_cumpl}">{pct_gap_cumpl:.1%}</span></div>
              {render_pila_bar(pct_gap_cumpl)}
          </div>""", unsafe_allow_html=True,
      )

    with col_kpi3:
      badg = "kpi-badge-danger" if desv_ap < 0 else "kpi-badge-success"
      st.markdown(
          f"""<div class="kpi-card">
              <div class="kpi-title">Últ. Aprobación ({ultimo_dia_ap})</div>
              <div class="kpi-value">{pct_ap_acum_mes_ultimo:.1%}</div>
              <div class="kpi-subtext">Objetivo: <b>4.5%</b></div>
              <div class="kpi-subtext">Desviación: <span class="{badg}">{desv_ap:+.1%}</span></div>
          </div>""", unsafe_allow_html=True,
      )

    with col_kpi4:
      prom_plantilla = (df_final[df_final["Agentes Plantilla"] > 0]["Agentes Plantilla"].mean() if not df_final.empty else 0)
      prom_log = (df_final[df_final["Agentes Log"] > 0]["Agentes Log"].mean() if not df_final.empty else 0)
      pct_aus = ((prom_plantilla - prom_log) / prom_plantilla if prom_plantilla > 0 else 0)
      st.markdown(
          f"""<div class="table-card">
              <div class="table-card-row"><span>Prom. Agentes Plantilla:</span> <b>{prom_plantilla:.0f}</b></div>
              <div class="table-card-row"><span>Prom. Agentes Log:</span> <b>{prom_log:.0f}</b></div>
              <div class="table-card-row"><span>% Ausentismo Prom.:</span> <b style="color:#d97706">{pct_aus:.1%}</b></div>
          </div>""", unsafe_allow_html=True,
      )

    col_ap1, col_ap2, col_ap3 = st.columns(3)
    with col_ap1:
      cumpl_ap_mes_fecha = (totales["AP MES"] / meta_ap_mes_fecha if meta_ap_mes_fecha > 0 else 0)
      cumpl_ap_mes_tot = (totales["AP MES"] / meta_ap_mes_total if meta_ap_mes_total > 0 else 0)
      badg = ("kpi-badge-danger" if cumpl_ap_mes_fecha < 0.80 else ("kpi-badge-warning" if cumpl_ap_mes_fecha < 1.0 else "kpi-badge-success"))
      st.markdown(
          f"""<div class="kpi-card">
              <div class="kpi-title">AP MES (Total)</div>
              <div class="kpi-value">{int(totales['AP MES'])}</div>
              <div class="kpi-subtext">Meta a la Fecha: <b>{int(meta_ap_mes_fecha)}</b> (<span class="{badg}">{cumpl_ap_mes_fecha:.1%}</span>)</div>
              <div class="kpi-subtext">Meta Total Mes: <b>{int(meta_ap_mes_total)}</b> ({cumpl_ap_mes_tot:.1%})</div>
              {render_gauge_svg(cumpl_ap_mes_fecha)}
          </div>""", unsafe_allow_html=True,
      )

    with col_ap2:
      cumpl_ap_cos_fecha = (totales["AP COSECHA"] / meta_ap_cos_fecha if meta_ap_cos_fecha > 0 else 0)
      cumpl_ap_cos_tot = (totales["AP COSECHA"] / meta_ap_cos_total if meta_ap_cos_total > 0 else 0)
      badg = ("kpi-badge-danger" if cumpl_ap_cos_fecha < 0.80 else ("kpi-badge-warning" if cumpl_ap_cos_fecha < 1.0 else "kpi-badge-success"))
      st.markdown(
          f"""<div class="kpi-card">
              <div class="kpi-title">AP Cosecha (Total)</div>
              <div class="kpi-value">{int(totales['AP COSECHA'])}</div>
              <div class="kpi-subtext">Meta a la Fecha: <b>{int(meta_ap_cos_fecha)}</b> (<span class="{badg}">{cumpl_ap_cos_fecha:.1%}</span>)</div>
              <div class="kpi-subtext">Meta Total Mes: <b>{int(meta_ap_cos_total)}</b> ({cumpl_ap_cos_tot:.1%})</div>
              {render_gauge_svg(cumpl_ap_cos_fecha)}
          </div>""", unsafe_allow_html=True,
      )

    with col_ap3:
      cumpl_ap_tot_fecha = (totales["AP Totales"] / meta_ap_tot_fecha if meta_ap_tot_fecha > 0 else 0)
      cumpl_ap_tot_tot = (totales["AP Totales"] / meta_ap_tot_total if meta_ap_tot_total > 0 else 0)
      badg = ("kpi-badge-danger" if cumpl_ap_tot_fecha < 0.80 else ("kpi-badge-warning" if cumpl_ap_tot_fecha < 1.0 else "kpi-badge-success"))
      st.markdown(
          f"""<div class="kpi-card">
              <div class="kpi-title">AP Totales</div>
              <div class="kpi-value">{int(totales['AP Totales'])}</div>
              <div class="kpi-subtext">Meta a la Fecha: <b>{int(meta_ap_tot_fecha)}</b> (<span class="{badg}">{cumpl_ap_tot_fecha:.1%}</span>)</div>
              <div class="kpi-subtext">Meta Total Mes: <b>{int(meta_ap_tot_total)}</b> ({cumpl_ap_tot_tot:.1%})</div>
              {render_gauge_svg(cumpl_ap_tot_fecha)}
          </div>""", unsafe_allow_html=True,
      )

    st.divider()

    format_dict = {}
    for c in df_vista.columns:
      if c == "Día": continue
      if "%" in c or c in ["% AP Acum M", "% AP Tot", "% AP Día", "% Eval", "% Decl", "% Canc", "% Pend", "% Aus"]: format_dict[c] = "{:.1%}"
      elif c in ["Prom", "SPH"]: format_dict[c] = "{:.1f}"
      else: format_dict[c] = "{:.0f}"

    rgb_green = (162, 217, 163)
    rgb_orange = (254, 210, 120)
    rgb_red = (248, 140, 140)
    rgb_white = (255, 255, 255)

    mask_hasta_corte = df_final["Fecha"] <= fecha_corte
    df_vista_pasado = df_vista.iloc[:len(df_final)][mask_hasta_corte]

    min_max_dict = {}
    for col in df_vista.columns:
      if col == "Día": continue
      if col == "LE":
        df_no_sab = df_vista_pasado[~df_vista_pasado["Día"].astype(str).str.contains("sáb", case=False)]
        vmin = df_no_sab["LE"].min() if not df_no_sab.empty else 0
        vmax = df_no_sab["LE"].max() if not df_no_sab.empty else 1
      elif not df_vista_pasado.empty and col in df_vista_pasado.columns:
        s = pd.to_numeric(df_vista_pasado[col], errors="coerce")
        vmin = s.min()
        vmax = s.max()
      else:
        vmin, vmax = 0, 1
      min_max_dict[col] = (vmin, vmax)

    def aplicar_formatos_condicionales(df_input):
      styles = pd.DataFrame("", index=df_input.index, columns=df_input.columns)
      for idx, row in df_input.iterrows():
        dia_str = str(row["Día"])
        base_align = "text-align: center !important;"
        if dia_str == "TOTAL":
          styles.loc[idx, :] = "font-weight: bold; background-color: #f0f2f6; text-align: center !important;"
          continue
        es_ultimo_ap = (ultimo_dia_ap != "N/A" and ultimo_dia_ap in dia_str.lower())
        row_base_style = ("background-color: #dbeafe; font-weight: bold; border-left: 3px solid #2563eb; " if es_ultimo_ap else "")
        
        corresponde_hasta_corte = False
        if idx < len(df_final):
          corresponde_hasta_corte = (df_final.iloc[idx]["Fecha"] <= fecha_corte)

        for col in df_input.columns:
          cell_style = base_align + row_base_style
          if corresponde_hasta_corte:
            val = row[col]
            if isinstance(val, (int, float, np.number)):
              if col == "LE":
                es_sabado = "sáb" in dia_str.lower()
                if not es_sabado:
                  vmin, vmax = min_max_dict["LE"]
                  bg = interpolate_color_2pt(val, vmin, vmax, rgb_white, rgb_green)
                  if bg: cell_style += " " + bg
              elif col in ["% LE", "Prom"]:
                vmin, vmax = min_max_dict[col]
                bg = interpolate_color_3pt(val, vmin, vmax, rgb_red, rgb_orange, rgb_green)
                if bg: cell_style += " " + bg
              elif col in ["% AP Día", "% Eval"]:
                vmin, vmax = min_max_dict[col]
                bg = interpolate_color_3pt(val, vmin, vmax, rgb_red, rgb_orange, rgb_green)
                if bg: cell_style += " " + bg
              elif col in ["% AP Acum M", "% AP Tot"]:
                vmin, vmax = min_max_dict[col]
                bg = interpolate_color_2pt(val, vmin, vmax, rgb_white, rgb_green)
                if bg: cell_style += " " + bg
              elif col in ["% Decl", "% Declinado"]:
                vmin, vmax = min_max_dict[col]
                bg = interpolate_color_2pt(val, vmin, vmax, rgb_white, rgb_red)
                if bg: cell_style += " " + bg
              elif col == "% REM/RECH":
                vmin, vmax = min_max_dict[col]
                bg = interpolate_color_3pt(val, vmin, vmax, rgb_green, rgb_orange, rgb_red)
                if bg: cell_style += " " + bg
              elif col in ["SPH", "No Gest"]:
                vmin, vmax = min_max_dict[col]
                bg = interpolate_color_2pt(val, vmin, vmax, rgb_white, rgb_green)
                if bg: cell_style += " " + bg
          styles.loc[idx, col] = cell_style
      return styles

    styler = (
        df_vista.style.format(format_dict)
        .set_properties(**{"text-align": "center !important", "font-size": "11.5px", "padding": "4px 2px"})
        .apply(aplicar_formatos_condicionales, axis=None)
    )

    st.dataframe(styler, use_container_width=True, height=750, hide_index=True)

    # ANÁLISIS DE CAPACIDAD Y DESVIACIÓN
    st.divider()
    st.subheader("🎯 Análisis Comparativo de Capacidad y Desviación de Leads")
    st.caption(f"Evaluación diaria de Meta LE basada en Agentes Contratados ({agentes_contratados_input} menos {ausentismo_teorico_input:.1%} ausentismo teórico = {agentes_contratados_input * (1 - ausentismo_teorico_input):.2f} netos). La Meta Asesor de Sábados se calcula a la mitad (4.1 / 2).")

    df_cap = df_final.copy()
    df_cap["Agentes Contratados"] = agentes_contratados_input
    df_cap["Agentes Programados"] = df_cap["Agentes Plantilla"]
    df_cap["Agentes Log"] = df_cap["Agentes Log"]
    df_cap["Ausencias Día"] = df_cap["Agentes Programados"] - df_cap["Agentes Log"]
    agentes_netos_contratados = agentes_contratados_input * (1.0 - ausentismo_teorico_input)

    def obtener_meta_asesor_dia(row):
      es_sabado = "sáb" in str(row["Día"]).lower()
      base = (row["Meta Asesor"] if ("Meta Asesor" in row and row["Meta Asesor"] > 0) else 4.1)
      return (base / 2.0) if es_sabado else base

    df_cap["Meta_Asesor_Dia"] = df_cap.apply(obtener_meta_asesor_dia, axis=1)
    df_cap["Meta LE Contratados"] = (agentes_netos_contratados * df_cap["Meta_Asesor_Dia"])
    df_cap["Meta LE Programados"] = (df_cap["Agentes Programados"] * df_cap["Meta_Asesor_Dia"])
    df_cap["Meta LE Logueados"] = (df_cap["Agentes Log"] * df_cap["Meta_Asesor_Dia"])
    df_cap["Leads Realizados"] = df_cap["Lead Efectivo"]
    df_cap["Desv vs Contratados"] = (df_cap["Leads Realizados"] - df_cap["Meta LE Contratados"])
    df_cap["Desv vs Logueados"] = (df_cap["Leads Realizados"] - df_cap["Meta LE Logueados"])
    df_cap["Impacto Ausentismo"] = (-1 * df_cap["Ausencias Día"] * df_cap["Meta_Asesor_Dia"])
    df_cap["Impacto Productividad SPH"] = (df_cap["Leads Realizados"] - df_cap["Meta LE Logueados"])

    cols_cap_vista = ["Día", "Agentes Contratados", "Agentes Programados", "Ausencias Día", "Agentes Log", "Meta LE Contratados", "Meta LE Programados", "Meta LE Logueados", "Leads Realizados", "SPH", "Desv vs Contratados", "Desv vs Logueados"]
    df_cap_vista = df_cap[cols_cap_vista].copy()

    tot_cap = df_cap.sum(numeric_only=True).to_dict()
    tot_cap["Día"] = "TOTAL"
    tot_cap["Agentes Contratados"] = agentes_contratados_input
    tot_cap["Agentes Programados"] = df_cap[df_cap["Agentes Programados"] > 0]["Agentes Programados"].mean()
    tot_cap["Agentes Log"] = df_cap[df_cap["Agentes Log"] > 0]["Agentes Log"].mean()
    tot_cap["Ausencias Día"] = (tot_cap["Agentes Programados"] - tot_cap["Agentes Log"])
    tot_cap["SPH"] = (tot_cap["Leads Realizados"] / tot_cap["Agentes Log"] if tot_cap["Agentes Log"] > 0 else 0)
    tot_cap["Meta LE Contratados"] = df_cap["Meta LE Contratados"].sum()
    tot_cap["Meta LE Programados"] = df_cap["Meta LE Programados"].sum()
    tot_cap["Meta LE Logueados"] = df_cap["Meta LE Logueados"].sum()
    tot_cap["Leads Realizados"] = df_cap["Leads Realizados"].sum()
    tot_cap["Desv vs Contratados"] = (tot_cap["Leads Realizados"] - tot_cap["Meta LE Contratados"])
    tot_cap["Desv vs Logueados"] = (tot_cap["Leads Realizados"] - tot_cap["Meta LE Logueados"])

    df_tot_cap = pd.DataFrame([tot_cap])[cols_cap_vista]
    df_cap_vista = pd.concat([df_cap_vista, df_tot_cap], ignore_index=True)

    format_cap = {"Agentes Contratados": "{:.0f}", "Agentes Programados": "{:.0f}", "Ausencias Día": "{:.0f}", "Agentes Log": "{:.0f}", "Meta LE Contratados": "{:.0f}", "Meta LE Programados": "{:.0f}", "Meta LE Logueados": "{:.0f}", "Leads Realizados": "{:.0f}", "SPH": "{:.1f}", "Desv vs Contratados": "{:+,.0f}", "Desv vs Logueados": "{:+,.0f}"}

    def estilo_desviaciones(val):
      if not isinstance(val, (int, float, np.number)): return ""
      if val > 0: return "background-color: #dcfce7; color: #15803d; font-weight: bold;"
      if val < 0: return "background-color: #fee2e2; color: #b91c1c; font-weight: bold;"
      return ""

    styler_cap = (
        df_cap_vista.style.format(format_cap)
        .set_properties(**{"text-align": "center !important", "font-size": "13px"})
        .map(estilo_desviaciones, subset=["Desv vs Contratados", "Desv vs Logueados"])
    )

    col_t1, col_t2 = st.columns([2.2, 1])

    with col_t1:
      st.markdown("##### 📋 Matriz de Descomposición de Leads vs Capacidad")
      st.dataframe(styler_cap, use_container_width=True, height=450, hide_index=True)

    with col_t2:
      st.markdown("##### 🔍 Diagnóstico Gerencial de Causa Raíz")
      
      dias_disponibles = df_cap["Día"].tolist()
      dia_sel_diag = st.selectbox("Seleccione el Día a Evaluar:", dias_disponibles, index=0)
      
      idx_curr = df_cap[df_cap["Día"] == dia_sel_diag].index[0]
      row_d = df_cap.iloc[idx_curr]
      
      desv_cont = row_d["Desv vs Contratados"]
      desv_log = row_d["Desv vs Logueados"]
      imp_aus = row_d["Impacto Ausentismo"]
      imp_sph = row_d["Impacto Productividad SPH"]
      sph_real = row_d["SPH"]
      meta_as = row_d["Meta_Asesor_Dia"]
      log_real = row_d["Agentes Log"]
      
      badge_cont = (f'<span class="arrow-badge-up">⬆️ Superávit (+{int(desv_cont):,} LE)</span>' if desv_cont >= 0 else f'<span class="arrow-badge-down">⬇️ Déficit ({int(desv_cont):,} LE)</span>')
      badge_log = (f'<span class="arrow-badge-up">⬆️ Superávit (+{int(desv_log):,} LE)</span>' if desv_log >= 0 else f'<span class="arrow-badge-down">⬇️ Déficit ({int(desv_log):,} LE)</span>')
      
      if idx_curr > 0:
        row_prev = df_cap.iloc[idx_curr - 1]
        dia_prev_nombre = row_prev["Día"]
        diff_sph_ayer = sph_real - row_prev["SPH"]
        diff_log_ayer = log_real - row_prev["Agentes Log"]
        diff_le_ayer = row_d["Leads Realizados"] - row_prev["Leads Realizados"]
        txt_sph_ayer = (f"mejora de <b style='color:#15803d;'>+{diff_sph_ayer:.1f} SPH</b>" if diff_sph_ayer >= 0 else f"caída de <b style='color:#b91c1c;'>{diff_sph_ayer:.1f} SPH</b>")
        txt_log_ayer = (f"<b>+{int(diff_log_ayer)} asesores logueados</b>" if diff_log_ayer >= 0 else f"<b>{int(diff_log_ayer)} asesores logueados</b>")
        txt_le_ayer = (f"<b>+{int(diff_le_ayer):,} LE</b>" if diff_le_ayer >= 0 else f"<b>{int(diff_le_ayer):,} LE</b>")
        comp_ayer_html = (f"• <b>vs Día Anterior ({dia_prev_nombre}):</b> Se registra una variación de {txt_le_ayer} en volumen, respaldada por {txt_log_ayer} y una {txt_sph_ayer} en la tasa de conversión por hora.")
      else:
        comp_ayer_html = ("• <b>vs Día Anterior:</b> Primer día registrado del periodo en evaluación.")
      
      dow_curr = (row_d["Día_Semana"] if "Día_Semana" in row_d else pd.to_datetime(row_d["Fecha"]).dayofweek)
      nombre_dow = (row_d["Nombre_Día"] if "Nombre_Día" in row_d else dias_nombres_map.get(dow_curr, "Día"))
      
      df_mismo_dow = df_cap.iloc[:idx_curr]
      if "Día_Semana" in df_mismo_dow.columns: df_mismo_dow = df_mismo_dow[df_mismo_dow["Día_Semana"] == dow_curr]
      else: df_mismo_dow = df_mismo_dow[df_mismo_dow["Fecha"].apply(lambda f: pd.to_datetime(f).dayofweek) == dow_curr]
      
      if not df_mismo_dow.empty:
        prom_sph_dow = df_mismo_dow["SPH"].mean()
        prom_log_dow = df_mismo_dow["Agentes Log"].mean()
        diff_sph_dow = sph_real - prom_sph_dow
        diff_log_dow = log_real - prom_log_dow
        txt_sph_dow = (f"<b style='color:#15803d;'>+{diff_sph_dow:.1f} SPH</b> por encima" if diff_sph_dow >= 0 else f"<b style='color:#b91c1c;'>{diff_sph_dow:.1f} SPH</b> por debajo")
        txt_log_dow = (f"<b>+{diff_log_dow:+.1f} agentes</b>" if diff_log_dow >= 0 else f"<b>{diff_log_dow:+.1f} agentes</b>")
        comp_dow_html = (f"• <b>vs Promedio de {nombre_dow}s Anteriores:</b> SPH se ubica {txt_sph_dow} del promedio del día ({prom_sph_dow:.1f} SPH), con una asistencia de {txt_log_dow} frente a su media ({prom_log_dow:.1f} agentes).")
      else:
        comp_dow_html = (f"• <b>vs Promedio de {nombre_dow}s Anteriores:</b> Corresponde al primer {nombre_dow} del mes.")
      
      if imp_sph > abs(imp_aus) and desv_cont >= 0: concl_base = "El superávit fue impulsado principalmente por una alta productividad individual (SPH) que compensó holgadamente el ausentismo."
      elif abs(imp_aus) > abs(imp_sph) and desv_cont < 0: concl_base = "El déficit responde primordialmente al faltante de personal logueado en piso de ventas."
      else: concl_base = "El resultado refleja directamente el nivel de conversión y eficiencia horaria de los asesores activos."
      
      st.markdown(
          f"""
          <div class="diag-box">
              <div class="diag-header">📌 Informe de Causalidad — {dia_sel_diag.upper()}</div>
              <div style="margin-bottom:12px;">
                  <div style="font-size:12px; color:#64748b; font-weight:700;">VS CONTRATADOS ({agentes_contratados_input} Base / {agentes_netos_contratados:.1f} Netos):</div>
                  <div style="margin-top:2px;">{badge_cont}</div>
              </div>
              <div style="margin-bottom:14px;">
                  <div style="font-size:12px; color:#64748b; font-weight:700;">VS LOGUEADOS ({int(row_d['Agentes Log'])}):</div>
                  <div style="margin-top:2px;">{badge_log}</div>
              </div>
              <div style="border-top: 1px dashed #cbd5e1; padding-top:10px;">
                  <div style="font-size:13px; font-weight:800; color:#0f172a; margin-bottom:6px;">Explicación de la Desviación:</div>
                  <div class="causal-item">
                      • <b>Ausentismo Operativo:</b> {int(row_d['Ausencias Día'])} ausencias en piso equivalen a 
                      <b style="color:{'#b91c1c' if imp_aus < 0 else '#15803d'}">{int(imp_aus):+,.0f} LE</b> de impacto directo.
                  </div>
                  <div class="causal-item">
                      • <b>Eficiencia Productiva (SPH):</b> Desempeño real de <b>{sph_real:.1f} LE/Agente</b> vs Meta del día de <b>{meta_as:.1f} LE/Agente</b>, aportando 
                      <b style="color:{'#15803d' if imp_sph >= 0 else '#b91c1c'}">{int(imp_sph):+,.0f} LE</b> de desviación por productividad.
                  </div>
                  <div style="background-color:#f8fafc; padding:10px 12px; border-radius:6px; margin-top:10px; font-size:12px; color:#334155; border-left:4px solid #0284c7;">
                      <div style="font-weight:800; color:#0f172a; margin-bottom:4px;">📌 Conclusión & Análisis de Tendencia:</div>
                      <div style="margin-bottom:6px;">{concl_base}</div>
                      <div style="border-top:1px solid #e2e8f0; padding-top:6px; font-size:11.5px; line-height:1.4;">
                          <div style="margin-bottom:4px;">{comp_ayer_html}</div>
                          <div>{comp_dow_html}</div>
                      </div>
                  </div>
              </div>
          </div>
          """,
          unsafe_allow_html=True,
      )

    # GRÁFICOS EJECUTIVOS LE REAL VS PTO & GAP
    st.divider()
    st.subheader("📈 Seguimiento Visual LE Real vs. Pto Diario y GAP Acumulado")
    
    df_chart = df_cap.copy()
    df_chart["Diferencia Neta Acumulada"] = (df_chart["Leads Realizados"] - df_chart["Meta LE Contratados"]).cumsum()

    tab_combo, tab_barras3 = st.tabs(["📊 Gráfico Combinado Ejecutivo (Barras + Línea)", "📊 Gráfico de 3 Barras (Estilo Excel)"])

    with tab_combo:
      fig_combo = make_subplots(specs=[[{"secondary_y": True}]])
      fig_combo.add_trace(go.Bar(x=df_chart["Día"], y=df_chart["Meta LE Contratados"], name="LEADS EFECTIVOS PTTO", marker_color="#ea580c"), secondary_y=False)
      fig_combo.add_trace(go.Bar(x=df_chart["Día"], y=df_chart["Leads Realizados"], name="LEADS EFECTIVOS REAL", marker_color="#0284c7"), secondary_y=False)
      fig_combo.add_trace(go.Scatter(x=df_chart["Día"], y=df_chart["Diferencia Neta Acumulada"], name="DIFERENCIA NETA ACUMULADA", mode="lines+markers+text", text=[f"<b>{v:+,.0f}</b>" for v in df_chart["Diferencia Neta Acumulada"]], textposition="top center", line=dict(color="#15803d", width=3)), secondary_y=True)
      fig_combo.update_layout(title="Seguimiento LE Real Vs Pto Diario", barmode="group", height=480)
      st.plotly_chart(fig_combo, use_container_width=True)

    with tab_barras3:
      fig_barras3 = go.Figure()
      fig_barras3.add_trace(go.Bar(x=df_chart["Día"], y=df_chart["Meta LE Contratados"], name="LEADS PTTO", marker_color="#ea580c"))
      fig_barras3.add_trace(go.Bar(x=df_chart["Día"], y=df_chart["Leads Realizados"], name="LEADS REAL", marker_color="#0284c7"))
      fig_barras3.add_trace(go.Bar(x=df_chart["Día"], y=df_chart["Diferencia Neta Acumulada"], name="GAP ACUMULADO", marker_color="#15803d"))
      fig_barras3.update_layout(title="Seguimiento (Formato Barras)", barmode="group", height=500)
      st.plotly_chart(fig_barras3, use_container_width=True)

    # GRÁFICO DE TENDENCIA DE APROBACIÓN
    st.divider()
    st.subheader("📉 Tendencia AP (% Aprobación Acumulada — ÚLTIMOS 4 MESES)")

    meses_tendencia = []
    for i in range(3, -1, -1):
      m = mes_sel - i
      y = año_sel
      if m <= 0:
        m += 12
        y -= 1
      meses_tendencia.append((y, m))

    def calcular_tendencia_mes(y, m, df_v):
      num_dias_m = calendar.monthrange(y, m)[1]
      inicio_m = date(y, m, 1)

      df_v_mes = df_v[(pd.to_datetime(df_v["F_VTA"]).dt.year == y) & (pd.to_datetime(df_v["F_VTA"]).dt.month == m)]
      f_dec_eff = df_v["F_DEC_EFF"]
      dec_m_mask = (pd.to_datetime(f_dec_eff).dt.year == y) & (pd.to_datetime(f_dec_eff).dt.month == m)
      es_mes_actual_flag = (y == año_sel) and (m == mes_sel)

      if es_mes_actual_flag:
        df_ap_curr = df_v_mes[(pd.to_datetime(df_v_mes["F_DEC_EFF"]).dt.year == y) & (pd.to_datetime(df_v_mes["F_DEC_EFF"]).dt.month == m) & (df_v_mes["DECISION"] == "A")]
        if not df_ap_curr.empty:
          max_d = int(pd.to_datetime(df_ap_curr["F_VTA"]).dt.day.max())
        else: max_d = num_dias_m
      else: max_d = num_dias_m

      dias, pct_acum_list = [], []
      for d in range(1, max_d + 1):
        f_corte = date(y, m, d)
        leads_acum = (df_v_mes["ESTADO"] == "LEAD EFECTIVO") & (df_v_mes["F_VTA"] <= f_corte)
        total_leads = leads_acum.sum()

        ap_mes_mask = ((pd.to_datetime(df_v["F_VTA"]).dt.year == y) & (pd.to_datetime(df_v["F_VTA"]).dt.month == m) & (pd.to_datetime(f_dec_eff).dt.year == y) & (pd.to_datetime(f_dec_eff).dt.month == m) & (df_v["DECISION"] == "A") & (df_v["F_VTA"] <= f_corte))
        ap_mes_acum = ap_mes_mask.sum()
        ap_cos_mask = (dec_m_mask & (df_v["DECISION"] == "A") & (pd.to_datetime(df_v["F_VTA"]) < pd.Timestamp(inicio_m)) & (pd.to_datetime(f_dec_eff).dt.date <= f_corte))
        ap_cos_acum = ap_cos_mask.sum()
        ap_total_acum = ap_mes_acum if es_mes_actual_flag else (ap_mes_acum + ap_cos_acum)

        pct = (ap_total_acum / total_leads * 100.0) if total_leads > 0 else 0.0
        dias.append(d)
        pct_acum_list.append(round(pct, 2))

      return dias, pct_acum_list

    fig_tend = go.Figure()
    colores_meses = ["#ea580c", "#15803d", "#0284c7", "#a855f7"]

    for idx, (y_m, m_m) in enumerate(meses_tendencia):
      dias_m, pcts_m = calcular_tendencia_mes(y_m, m_m, df_ventas)
      nombre_m = nombres_meses.get(m_m, str(m_m)).lower()
      color_m = colores_meses[idx % len(colores_meses)]

      text_labels = [""] * len(pcts_m)
      if pcts_m: text_labels[-1] = f"<b>{pcts_m[-1]:.1f}%</b>".replace(".", ",")

      fig_tend.add_trace(go.Scatter(x=dias_m, y=pcts_m, name=nombre_m, mode="lines+markers+text", line=dict(color=color_m, width=3), marker=dict(size=5, color=color_m), text=text_labels, textposition="top right", textfont=dict(size=13, color=color_m)))

    fig_tend.update_layout(title="<b>Tendencia AP</b>", xaxis=dict(title="Día del Mes"), yaxis=dict(title="% Aprobación Acumulada", ticksuffix="%"), plot_bgcolor="#ffffff", height=520, hovermode="x unified")
    st.plotly_chart(fig_tend, use_container_width=True)

    # DÍA HÁBIL Y FUNNEL
    st.divider()
    st.markdown("### 🗓️ Módulo de Análisis por Día Hábil y Funnel (ÚLTIMOS MESES)")

    def generar_serie_dia_habil(y, m, df_v):
      num_dias_m = calendar.monthrange(y, m)[1]
      festivos = holidays.Mexico(years=y)
      fechas = [date(y, m, d) for d in range(1, num_dias_m + 1)]
      dias_habiles = [f for f in fechas if f.weekday() != 6 and f not in festivos]

      df_v_mes = df_v[(pd.to_datetime(df_v["F_VTA"]).dt.year == y) & (pd.to_datetime(df_v["F_VTA"]).dt.month == m)]
      es_mes_actual_flag = (y == año_sel) and (m == mes_sel)

      if es_mes_actual_flag:
        df_ap_curr = df_v_mes[(pd.to_datetime(df_v_mes["F_DEC_EFF"]).dt.year == y) & (pd.to_datetime(df_v_mes["F_DEC_EFF"]).dt.month == m) & (df_v_mes["DECISION"] == "A")]
        if not df_ap_curr.empty: max_f_ap = pd.to_datetime(df_ap_curr["F_VTA"]).dt.date.max()
        else: max_f_ap = date.today()
      else: max_f_ap = date(y, m, num_dias_m)

      records = []
      le_acum, ap_acum = 0, 0
      for dh_idx, f in enumerate(dias_habiles, start=1):
        if es_mes_actual_flag and f > max_f_ap: break

        sub_f = df_v_mes[df_v_mes["F_VTA"] == f]
        le_dia = (sub_f["ESTADO"] == "LEAD EFECTIVO").sum()
        ap_dia = ((sub_f["ESTADO"] == "LEAD EFECTIVO") & (pd.to_datetime(sub_f["F_DEC_EFF"]).dt.year == y) & (pd.to_datetime(sub_f["F_DEC_EFF"]).dt.month == m) & (sub_f["DECISION"] == "A")).sum()

        le_acum += le_dia
        ap_acum += ap_dia
        pct_acum = (ap_acum / le_acum * 100.0) if le_acum > 0 else 0.0

        records.append({"Año": y, "Mes": m, "Fecha": f, "Día_Hábil": dh_idx, "Label_DH": f"DH {dh_idx}", "LE_Día": le_dia, "LE_Acum": le_acum, "AP_MES_Día": ap_dia, "AP_MES_Acum": ap_acum, "%_AP_MES_Acum": round(pct_acum, 2)})
      return pd.DataFrame(records)

    df_dh_todos = pd.DataFrame()
    for y_m, m_m in meses_tendencia:
      df_m_dh = generar_serie_dia_habil(y_m, m_m, df_ventas)
      if not df_m_dh.empty: df_dh_todos = pd.concat([df_dh_todos, df_m_dh], ignore_index=True)

    def generar_funnel_dia_habil(y, m, df_v):
      num_dias_m = calendar.monthrange(y, m)[1]
      festivos = holidays.Mexico(years=y)
      fechas = [date(y, m, d) for d in range(1, num_dias_m + 1)]
      dias_habiles = [f for f in fechas if f.weekday() != 6 and f not in festivos]

      df_v_mes = df_v[(pd.to_datetime(df_v["F_VTA"]).dt.year == y) & (pd.to_datetime(df_v["F_VTA"]).dt.month == m)]
      es_mes_actual_flag = (y == año_sel) and (m == mes_sel)

      if es_mes_actual_flag:
        df_ap_curr = df_v_mes[(pd.to_datetime(df_v_mes["F_DEC_EFF"]).dt.year == y) & (pd.to_datetime(df_v_mes["F_DEC_EFF"]).dt.month == m) & (df_v_mes["DECISION"] == "A")]
        if not df_ap_curr.empty: max_f_ap = pd.to_datetime(df_ap_curr["F_VTA"]).dt.date.max()
        else: max_f_ap = date.today()
      else: max_f_ap = date(y, m, num_dias_m)

      records = []
      le_acum, eval_acum, decl_acum, nogest_acum, canc_acum = 0, 0, 0, 0, 0
      for dh_idx, f in enumerate(dias_habiles, start=1):
        if es_mes_actual_flag and f > max_f_ap: break

        sub_f = df_v_mes[df_v_mes["F_VTA"] == f]
        is_le = sub_f["ESTADO"] == "LEAD EFECTIVO"
        dec = sub_f["DECISION"].astype(str).str.strip().str.upper()

        le_dia = is_le.sum()
        eval_dia = (is_le & dec.isin(["A", "D", "P", "C"])).sum()
        decl_dia = (is_le & (dec == "D")).sum()
        nogest_dia = (is_le & sub_f["BX_EMPTY"]).sum()
        canc_dia = (is_le & (dec == "C")).sum()

        le_acum += le_dia
        eval_acum += eval_dia
        decl_acum += decl_dia
        nogest_acum += nogest_dia
        canc_acum += canc_dia

        pct_eval = (eval_acum / le_acum * 100.0) if le_acum > 0 else 0.0
        pct_decl = (decl_acum / le_acum * 100.0) if le_acum > 0 else 0.0
        pct_nogest = (nogest_acum / le_acum * 100.0) if le_acum > 0 else 0.0
        pct_canc = (canc_acum / le_acum * 100.0) if le_acum > 0 else 0.0

        records.append({
            "Año": y, "Mes": m, "Fecha": f, "Día_Hábil": dh_idx, "Label_DH": f"DH {dh_idx}",
            "LE_Acum": le_acum,
            "Eval_Acum": eval_acum,
            "%_Eval_Acum": round(pct_eval, 2),
            "Decl_Acum": decl_acum,
            "%_Decl_Acum": round(pct_decl, 2),
            "NoGest_Acum": nogest_acum,
            "%_NoGest_Acum": round(pct_nogest, 2),
            "Canc_Acum": canc_acum,
            "%_Canc_Acum": round(pct_canc, 2)
        })
      return pd.DataFrame(records)

    df_dh_funnel = pd.DataFrame()
    for y_m, m_m in meses_tendencia:
      df_m_fun = generar_funnel_dia_habil(y_m, m_m, df_ventas)
      if not df_m_fun.empty: df_dh_funnel = pd.concat([df_dh_funnel, df_m_fun], ignore_index=True)

    df_dh_curr_nov = df_dh_todos[(df_dh_todos["Año"] == año_sel) & (df_dh_todos["Mes"] == mes_sel)]
    max_dh_evaluado_num = int(df_dh_curr_nov["Día_Hábil"].max()) if not df_dh_curr_nov.empty else 7

    opciones_meses_dict = {f"{nombres_meses.get(m, str(m)).title()} ({y})": (y, m) for y, m in meses_tendencia}
    default_meses_nombres = [k for k in opciones_meses_dict.keys() if "Agosto" not in k]

    dh_lista_todas = sorted(df_dh_todos["Label_DH"].drop_duplicates().tolist(), key=lambda x: int(re.search(r'\d+', str(x)).group()) if re.search(r'\d+', str(x)) else 0) if not df_dh_todos.empty else []
    default_dh_evaluados = [dh for dh in dh_lista_todas if int(re.search(r'\d+', str(dh)).group()) <= max_dh_evaluado_num]

    st.markdown("##### 🎛️ Panel de Filtros Unificados (Aplica a Tablas y Gráficos de Día Hábil y Funnel)")
    col_fil_unif1, col_fil_unif2 = st.columns(2)

    with col_fil_unif1:
      meses_dh_nombres_sel = st.multiselect(
          "Meses a Comparar:",
          options=list(opciones_meses_dict.keys()),
          default=default_meses_nombres,
          key="shared_meses_select"
      )
      meses_tendencia_filtrados = [opciones_meses_dict[k] for k in meses_dh_nombres_sel if k in opciones_meses_dict]

    with col_fil_unif2:
      dh_filtro_compartido = st.multiselect(
          "Filtrar Días Hábiles (DH):",
          options=dh_lista_todas,
          default=default_dh_evaluados,
          key="shared_dh_select"
      )

    st.subheader("🗓️ Análisis por Día Hábil & Proyección de Maduración AP Mes")

    col_ctrl1, col_ctrl2 = st.columns([2.5, 1.0])
    with col_ctrl1:
      metricas_dh_sel = st.multiselect(
          "Filtro de Indicadores AP Mes:",
          options=["% Conversión AP Mes Acumulada", "Aprobadas (AP MES) Acumuladas", "Leads Efectivos Acumulados"],
          default=["% Conversión AP Mes Acumulada", "Aprobadas (AP MES) Acumuladas", "Leads Efectivos Acumulados"],
          key="m1_metricas_select"
      )
    with col_ctrl2:
      st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
      vista_tabla_dh = st.checkbox("Mostrar Matriz Comparativa AP Mes", value=True, key="m1_vista_tabla")

    df_dh_todos_plot = df_dh_todos.copy()
    if dh_filtro_compartido:
      df_dh_todos_plot = df_dh_todos_plot[df_dh_todos_plot["Label_DH"].isin(dh_filtro_compartido)]

    if not df_dh_todos_plot.empty and meses_tendencia_filtrados:
      fig_dh = make_subplots(specs=[[{"secondary_y": True}]])
      colores_dh = ["#ea580c", "#15803d", "#0284c7", "#a855f7"]

      for idx, (y_m, m_m) in enumerate(meses_tendencia_filtrados):
        sub_dh = df_dh_todos_plot[(df_dh_todos_plot["Año"] == y_m) & (df_dh_todos_plot["Mes"] == m_m)]
        if sub_dh.empty: continue
        nombre_m_str = nombres_meses.get(m_m, str(m_m)).title()
        c_base = colores_dh[idx % len(colores_dh)]

        if "% Conversión AP Mes Acumulada" in metricas_dh_sel:
          labels_pct = [f"<b>{v:.1f}%</b>" for v in sub_dh["%_AP_MES_Acum"]]
          fig_dh.add_trace(go.Scatter(x=sub_dh["Label_DH"], y=sub_dh["%_AP_MES_Acum"], name=f"% AP Mes ({nombre_m_str})", mode="lines+markers+text", line=dict(color=c_base, width=3), text=labels_pct, textposition="top center", textfont=dict(size=11, color=c_base)), secondary_y=False)

        if "Aprobadas (AP MES) Acumuladas" in metricas_dh_sel:
          fig_dh.add_trace(go.Bar(x=sub_dh["Label_DH"], y=sub_dh["AP_MES_Acum"], name=f"AP Acum ({nombre_m_str})", opacity=0.35, marker_color=c_base, text=[f"<b>{int(v)}</b>" for v in sub_dh["AP_MES_Acum"]], textposition="auto"), secondary_y=True)

        if "Leads Efectivos Acumulados" in metricas_dh_sel:
          fig_dh.add_trace(go.Scatter(x=sub_dh["Label_DH"], y=sub_dh["LE_Acum"], name=f"LE Acum ({nombre_m_str})", mode="lines+markers", line=dict(color=c_base, width=2, dash="dot")), secondary_y=True)

      fig_dh.update_layout(title="<b>Tendencia AP Mes Acumulado & Volúmenes por Día Hábil</b>", barmode='group', height=550, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5))
      fig_dh.update_yaxes(title_text="% Conversión AP Mes", ticksuffix="%", secondary_y=False)
      fig_dh.update_yaxes(title_text="Volumen (APs / Leads)", showgrid=False, secondary_y=True)
      st.plotly_chart(fig_dh, use_container_width=True)

      if vista_tabla_dh:
        dh_labels_m1 = sorted(df_dh_todos_plot["Label_DH"].dropna().unique().tolist(), key=lambda x: int(re.search(r'\d+', str(x)).group()) if re.search(r'\d+', str(x)) else 0)
        df_matrix = pd.DataFrame({"Label_DH": dh_labels_m1})

        for y_m, m_m in meses_tendencia_filtrados:
            m_name = nombres_meses.get(m_m, str(m_m)).title()
            sub_df = df_dh_todos_plot[(df_dh_todos_plot["Año"] == y_m) & (df_dh_todos_plot["Mes"] == m_m)]
            mapping_ap_pct = dict(zip(sub_df["Label_DH"], sub_df["%_AP_MES_Acum"]))
            mapping_ap_vol = dict(zip(sub_df["Label_DH"], sub_df["AP_MES_Acum"]))
            mapping_le_vol = dict(zip(sub_df["Label_DH"], sub_df["LE_Acum"]))
            
            if "% Conversión AP Mes Acumulada" in metricas_dh_sel: df_matrix[f"% AP ({m_name})"] = df_matrix["Label_DH"].map(mapping_ap_pct)
            if "Aprobadas (AP MES) Acumuladas" in metricas_dh_sel: df_matrix[f"APs ({m_name})"] = df_matrix["Label_DH"].map(mapping_ap_vol)
            if "Leads Efectivos Acumulados" in metricas_dh_sel: df_matrix[f"LEs ({m_name})"] = df_matrix["Label_DH"].map(mapping_le_vol)

        df_matrix_html = df_matrix.astype(object)
        curr_m_name = nombres_meses.get(mes_sel).title()
        curr_col_pct = f"% AP ({curr_m_name})"
        curr_col_ap = f"APs ({curr_m_name})"
        curr_col_le = f"LEs ({curr_m_name})"

        idx_curr_m = [i for i, (y, m) in enumerate(meses_tendencia) if y == año_sel and m == mes_sel]
        if idx_curr_m and idx_curr_m[0] > 0:
            prev_m_tuple = meses_tendencia[idx_curr_m[0] - 1]
            prev_m_name = nombres_meses.get(prev_m_tuple[1]).title()
            prev_m_pct_col = f"% AP ({prev_m_name})"
            prev_m_ap_col = f"APs ({prev_m_name})"
            prev_m_le_col = f"LEs ({prev_m_name})"
        else:
            prev_m_pct_col = prev_m_ap_col = prev_m_le_col = None

        prev_cols_pct = [f"% AP ({nombres_meses.get(m).title()})" for y, m in meses_tendencia if not (y == año_sel and m == mes_sel)]
        prev_cols_ap = [f"APs ({nombres_meses.get(m).title()})" for y, m in meses_tendencia if not (y == año_sel and m == mes_sel)]
        prev_cols_le = [f"LEs ({nombres_meses.get(m).title()})" for y, m in meses_tendencia if not (y == año_sel and m == mes_sel)]

        for col in df_matrix.columns:
            if col == "Label_DH": continue
            for idx in df_matrix.index:
                val = df_matrix.at[idx, col]
                if pd.isna(val):
                    df_matrix_html.at[idx, col] = "-"
                else:
                    if "% AP" in col:
                        if col == curr_col_pct:
                            prev_vals = [df_matrix.at[idx, pc] for pc in prev_cols_pct if pc in df_matrix.columns and pd.notna(df_matrix.at[idx, pc])]
                            prom_html = ""
                            if prev_vals:
                                avg_prev = sum(prev_vals) / len(prev_vals)
                                arrow_p = "⬆️" if val >= avg_prev else "⬇️"
                                color_p = "#15803d" if val >= avg_prev else "#b91c1c"
                                prom_html = f'<span style="font-size:10px; color:{color_p}; font-weight:bold;">{arrow_p} Prom: {avg_prev:.2f}%</span>'
                            
                            ant_html = ""
                            if prev_m_pct_col and prev_m_pct_col in df_matrix.columns and pd.notna(df_matrix.at[idx, prev_m_pct_col]):
                                val_ant = df_matrix.at[idx, prev_m_pct_col]
                                arrow_a = "⬆️" if val >= val_ant else "⬇️"
                                color_a = "#15803d" if val >= val_ant else "#b91c1c"
                                ant_html = f'<span style="font-size:10px; color:{color_a}; font-weight:bold;">{arrow_a} vs Ant: {val_ant:.2f}%</span>'
                            
                            sub_info = "<br>".join([h for h in [prom_html, ant_html] if h])
                            if sub_info:
                                df_matrix_html.at[idx, col] = f'<div style="text-align:center; line-height:1.2;"><b>{val:.2f}%</b><br>{sub_info}</div>'
                            else:
                                df_matrix_html.at[idx, col] = f'<div style="text-align:center;"><b>{val:.2f}%</b></div>'
                        else:
                            df_matrix_html.at[idx, col] = f'<div style="text-align:center;">{val:.2f}%</div>'

                    elif "APs (" in col:
                        if col == curr_col_ap:
                            prev_vals = [df_matrix.at[idx, pc] for pc in prev_cols_ap if pc in df_matrix.columns and pd.notna(df_matrix.at[idx, pc])]
                            prom_html = ""
                            if prev_vals:
                                avg_prev = sum(prev_vals) / len(prev_vals)
                                arrow_p = "⬆️" if val >= avg_prev else "⬇️"
                                color_p = "#15803d" if val >= avg_prev else "#b91c1c"
                                prom_html = f'<span style="font-size:10px; color:{color_p}; font-weight:bold;">{arrow_p} Prom: {int(round(avg_prev))}</span>'
                            
                            ant_html = ""
                            if prev_m_ap_col and prev_m_ap_col in df_matrix.columns and pd.notna(df_matrix.at[idx, prev_m_ap_col]):
                                val_ant = df_matrix.at[idx, prev_m_ap_col]
                                arrow_a = "⬆️" if val >= val_ant else "⬇️"
                                color_a = "#15803d" if val >= val_ant else "#b91c1c"
                                ant_html = f'<span style="font-size:10px; color:{color_a}; font-weight:bold;">{arrow_a} vs Ant: {int(val_ant)}</span>'
                            
                            sub_info = "<br>".join([h for h in [prom_html, ant_html] if h])
                            if sub_info:
                                df_matrix_html.at[idx, col] = f'<div style="text-align:center; line-height:1.2;"><b>{int(val):,}</b><br>{sub_info}</div>'
                            else:
                                df_matrix_html.at[idx, col] = f'<div style="text-align:center;"><b>{int(val):,}</b></div>'

                    elif "LEs (" in col:
                        if col == curr_col_le:
                            prev_vals = [df_matrix.at[idx, pc] for pc in prev_cols_le if pc in df_matrix.columns and pd.notna(df_matrix.at[idx, pc])]
                            prom_html = ""
                            if prev_vals:
                                avg_prev = sum(prev_vals) / len(prev_vals)
                                arrow_p = "⬆️" if val >= avg_prev else "⬇️"
                                color_p = "#15803d" if val >= avg_prev else "#b91c1c"
                                prom_html = f'<span style="font-size:10px; color:{color_p}; font-weight:bold;">{arrow_p} Prom: {int(round(avg_prev)):,}</span>'
                            
                            ant_html = ""
                            if prev_m_le_col and prev_m_le_col in df_matrix.columns and pd.notna(df_matrix.at[idx, prev_m_le_col]):
                                val_ant = df_matrix.at[idx, prev_m_le_col]
                                arrow_a = "⬆️" if val >= val_ant else "⬇️"
                                color_a = "#15803d" if val >= val_ant else "#b91c1c"
                                ant_html = f'<span style="font-size:10px; color:{color_a}; font-weight:bold;">{arrow_a} vs Ant: {int(val_ant):,}</span>'
                            
                            sub_info = "<br>".join([h for h in [prom_html, ant_html] if h])
                            if sub_info:
                                df_matrix_html.at[idx, col] = f'<div style="text-align:center; line-height:1.2;"><b>{int(val):,}</b><br>{sub_info}</div>'
                            else:
                                df_matrix_html.at[idx, col] = f'<div style="text-align:center;"><b>{int(val):,}</b></div>'

        html_table = df_matrix_html.to_html(escape=False, index=False)
        html_table = html_table.replace('<table border="1" class="dataframe">', '<table style="width: 100%; border-collapse: collapse; font-size: 12.5px; font-family: sans-serif; background-color: #ffffff; border: 1px solid #cbd5e1; margin-bottom: 20px;">')
        html_table = html_table.replace('<th>', '<th style="background-color: #f8fafc; border-bottom: 2px solid #94a3b8; padding: 10px 8px; text-align: center; color: #1e293b; font-weight: 700;">')
        html_table = html_table.replace('<td>', '<td style="border-bottom: 1px solid #e2e8f0; padding: 10px 8px; text-align: center; color: #0f172a; vertical-align: middle;">')

        st.markdown("##### 📋 Matriz Comparativa Detallada por Día Hábil (AP Mes)")
        st.markdown(f'<div style="overflow-x: auto; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">{html_table}</div>', unsafe_allow_html=True)

    df_dh_curr = (df_dh_todos[(df_dh_todos["Año"] == año_sel) & (df_dh_todos["Mes"] == mes_sel)] if "Mes" in df_dh_todos.columns and not df_dh_todos.empty else pd.DataFrame())

    if not df_dh_curr.empty:
      ult_row_dh = df_dh_curr.iloc[-1]
      dh_act_num = int(ult_row_dh["Día_Hábil"])
      fecha_ult_ap_dt = ult_row_dh["Fecha"]
      pct_act_dh = ult_row_dh["%_AP_MES_Acum"]
      ap_act_dh = int(ult_row_dh["AP_MES_Acum"])
      le_act_dh = int(ult_row_dh["LE_Acum"])

      df_dh_prevs = df_dh_todos[(df_dh_todos["Día_Hábil"] == dh_act_num) & ((df_dh_todos["Año"] != año_sel) | (df_dh_todos["Mes"] != mes_sel))]
      prom_pct_prev_dh = (df_dh_prevs["%_AP_MES_Acum"].mean() if not df_dh_prevs.empty else 4.0)
      diff_vs_hist_dh = pct_act_dh - prom_pct_prev_dh
      
      if len(meses_tendencia) > 1:
          y_prev, m_prev = meses_tendencia[-2]
          nombre_mes_anterior = nombres_meses.get(m_prev).title()
          df_dh_mes_anterior = df_dh_todos[(df_dh_todos["Año"] == y_prev) & (df_dh_todos["Mes"] == m_prev) & (df_dh_todos["Día_Hábil"] == dh_act_num)]
          if not df_dh_mes_anterior.empty:
              pct_mes_anterior = df_dh_mes_anterior.iloc[0]["%_AP_MES_Acum"]
              ap_mes_anterior = int(df_dh_mes_anterior.iloc[0]["AP_MES_Acum"])
              diff_ap_vs_prev = ap_act_dh - ap_mes_anterior
              diff_pct_prev = pct_act_dh - pct_mes_anterior
              txt_comp_anterior = f"A la misma fecha del mes de <b>{nombre_mes_anterior} (DH {dh_act_num})</b>, se registraron <b>{ap_mes_anterior} APs ({pct_mes_anterior:.2f}%)</b>. Actualmente registramos <b>{ap_act_dh} APs ({pct_act_dh:.2f}%)</b>, lo que representa una variación de <b style='color:{'#15803d' if diff_ap_vs_prev >= 0 else '#b91c1c'};'>{diff_ap_vs_prev:+d} APs</b> y <b style='color:{'#15803d' if diff_pct_prev >= 0 else '#b91c1c'};'>{diff_pct_prev:+.2f}%</b>."
          else: txt_comp_anterior = "No hay datos consolidados del mes anterior en este mismo día hábil."
      else: txt_comp_anterior = "Histórico mensual insuficiente para comparar."

      dias_lag = 4
      fecha_inicio_maduracion = fecha_ult_ap_dt - timedelta(days=dias_lag)
      df_ventas_curr_m = df_ventas[(pd.to_datetime(df_ventas["F_VTA"]).dt.year == año_sel) & (pd.to_datetime(df_ventas["F_VTA"]).dt.month == mes_sel)]
      
      leads_en_ventana = df_ventas_curr_m[(df_ventas_curr_m["ESTADO"] == "LEAD EFECTIVO") & (df_ventas_curr_m["F_VTA"] >= fecha_inicio_maduracion) & (df_ventas_curr_m["F_VTA"] <= fecha_ult_ap_dt)]
      volumen_leads_ventana = leads_en_ventana.shape[0]
      leads_pendientes_ventana = leads_en_ventana[leads_en_ventana["BX_EMPTY"] | (leads_en_ventana["DECISION"] == "P")].shape[0]

      leads_cerrados = df_ventas_curr_m[(df_ventas_curr_m["ESTADO"] == "LEAD EFECTIVO") & (df_ventas_curr_m["F_VTA"] < fecha_inicio_maduracion)]
      ap_cerradas = leads_cerrados[(pd.to_datetime(leads_cerrados["F_DEC_EFF"]).dt.year == año_sel) & (pd.to_datetime(leads_cerrados["F_DEC_EFF"]).dt.month == mes_sel) & (leads_cerrados["DECISION"] == "A")].shape[0]
      
      tasa_cierre_real_mes_curso = (ap_cerradas / leads_cerrados.shape[0]) if leads_cerrados.shape[0] > 0 else (pct_act_dh / 100.0)
      
      ap_adicionales_estimadas = int(volumen_leads_ventana * tasa_cierre_real_mes_curso) 
      aps_ya_caidas_ventana = leads_en_ventana[(pd.to_datetime(leads_en_ventana["F_DEC_EFF"]).dt.year == año_sel) & (pd.to_datetime(leads_en_ventana["F_DEC_EFF"]).dt.month == mes_sel) & (leads_en_ventana["DECISION"] == "A")].shape[0]
      ap_remanentes = max(0, ap_adicionales_estimadas - aps_ya_caidas_ventana)
      
      ap_proyectadas_total_mes = ap_act_dh + ap_remanentes
      pct_proyectado_cierre = (ap_proyectadas_total_mes / le_act_dh * 100.0) if le_act_dh > 0 else pct_act_dh

      badge_maduracion = (f'<span class="arrow-badge-up">⬆️ Proyección al Cierre: {pct_proyectado_cierre:.1f}% AP</span>' if pct_proyectado_cierre >= prom_pct_prev_dh else f'<span class="arrow-badge-down">⬇️ Proyección Ajustada: {pct_proyectado_cierre:.1f}% AP</span>')

      st.markdown(
          f"""
          <div class="diag-box">
              <div class="diag-header">📌 Diagnóstico Gerencial de Maduración AP Mes — AL DÍA HÁBIL {dh_act_num} ({fecha_ult_ap_dt.strftime('%d-%b')})</div>
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                  <div>
                      <span style="font-size:13px; color:#64748b; font-weight:700;">CONVERSIÓN ACTUAL AL DH {dh_act_num}:</span>
                      <b style="font-size:18px; color:#0f172a; margin-left:8px;">{pct_act_dh:.2f}%</b>
                      <span style="font-size:12px; color:#475569;">({ap_act_dh} AP / {le_act_dh:,} LE)</span>
                  </div>
                  <div>{badge_maduracion}</div>
              </div>
              <div style="border-top: 1px dashed #cbd5e1; padding-top:10px;">
                  <div style="font-size:13px; font-weight:800; color:#0f172a; margin-bottom:6px;">Análisis de Maduración y Cartera Reciente:</div>
                  <div class="causal-item">
                      • <b>Comparativa Histórica en el mismo Día Hábil (DH {dh_act_num}):</b> El desempeño actual registra una variación de <b style="color:{'#15803d' if diff_vs_hist_dh >= 0 else '#b91c1c'}">{diff_vs_hist_dh:+.2f}%</b> frente al promedio de meses anteriores ({prom_pct_prev_dh:.2f}%).
                  </div>
                  <div class="causal-item">
                      • <b>vs Mes Anterior:</b> {txt_comp_anterior}
                  </div>
                  <div class="causal-item">
                      • <b>Leads en Proceso de Maduración (Lag Operativo):</b> Existen <b>{leads_pendientes_ventana} Leads Efectivos</b> generados recientemente con estado no evaluado o pendiente.
                  </div>
                  <div class="causal-item">
                      • <b>Proyección Incremental Estimada:</b> Con base en la tasa de conversión media acumulada de los días ya cerrados del mes en curso (<b>{(tasa_cierre_real_mes_curso*100):.2f}%</b>), se estiman <b>+{ap_remanentes} aprobaciones adicionales</b> sobre la venta reciente en proceso de maduración, elevando las ventas a <b>{ap_proyectadas_total_mes} AP MES</b> ({pct_proyectado_cierre:.2f}% AP Mes).
                  </div>
                  <div style="background-color:#f8fafc; padding:10px 12px; border-radius:6px; margin-top:10px; font-size:12px; color:#334155; border-left:4px solid #15803d;">
                      <div style="font-weight:800; color:#0f172a; margin-bottom:4px;">📌 Conclusión & Oportunidad de Mejora:</div>
                      <div>La actual conversión del <b>{pct_act_dh:.2f}%</b> a corte del DH {dh_act_num} está fuertemente influenciada por el volumen sin dictaminar de la última semana. Con la regularización esperada de los <b>{leads_pendientes_ventana} trámites recientes</b>, proyectamos sumar <b>+{ap_remanentes} APs</b>, alcanzando <b>{ap_proyectadas_total_mes} AP MES</b> en total y elevando la tasa al <b>{pct_proyectado_cierre:.1f}% AP Mes</b>. Se debe trabajar en optimizar la calidad inicial del perfilamiento en piso para garantizar dictámenes de rápida validación.</div>
                  </div>
              </div>
          </div>
          """,
          unsafe_allow_html=True,
      )

    st.divider()
    st.subheader("🔄 Análisis de Funnel & Estado de Leads por Día Hábil (ACUMULADO)")

    metricas_funnel_map = {
        "Leads Efectivos": ("LE_Acum", "vol"),
        "Evaluados": ("Eval_Acum", "vol"),
        "% Evaluado": ("%_Eval_Acum", "pct"),
        "Declinados": ("Decl_Acum", "vol"),
        "% Declinado": ("%_Decl_Acum", "pct"),
        "No Gestionados": ("NoGest_Acum", "vol"),
        "% No Gestionado": ("%_NoGest_Acum", "pct"),
        "Cancelados": ("Canc_Acum", "vol"),
        "% Cancelado": ("%_Canc_Acum", "pct"),
    }

    col_f1, col_f2 = st.columns([2.5, 1.0])
    with col_f1:
      met_funnel_sel = st.multiselect(
          "Filtro de Métricas de Funnel:",
          options=list(metricas_funnel_map.keys()),
          default=["Leads Efectivos", "Evaluados", "% Evaluado", "% Declinado", "% Cancelado", "% No Gestionado"],
          key="funnel_metricas_select"
      )
    with col_f2:
      st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
      vista_matriz_funnel = st.checkbox("Mostrar Matriz Comparativa Funnel", value=True, key="funnel_vista_tabla")

    df_dh_funnel_plot = df_dh_funnel.copy()
    if dh_filtro_compartido:
      df_dh_funnel_plot = df_dh_funnel_plot[df_dh_funnel_plot["Label_DH"].isin(dh_filtro_compartido)]

    if not df_dh_funnel_plot.empty and meses_tendencia_filtrados:
      fig_fun = make_subplots(specs=[[{"secondary_y": True}]])
      colores_fun = ["#ea580c", "#15803d", "#0284c7", "#a855f7"]

      for idx, (y_m, m_m) in enumerate(meses_tendencia_filtrados):
        sub_fun = df_dh_funnel_plot[(df_dh_funnel_plot["Año"] == y_m) & (df_dh_funnel_plot["Mes"] == m_m)]
        if sub_fun.empty: continue
        nombre_m_str = nombres_meses.get(m_m, str(m_m)).title()
        c_base = colores_fun[idx % len(colores_fun)]

        for met_label in met_funnel_sel:
          col_key, kind = metricas_funnel_map[met_label]
          is_pct = kind == "pct"
          dash_style = "solid" if "Eval" in met_label else ("dash" if "Decl" in met_label else "dot")
          
          if is_pct: text_labels = [f"<b>{v:.1f}%</b>" for v in sub_fun[col_key]]
          else: text_labels = [f"<b>{int(v):,}</b>" for v in sub_fun[col_key]]

          fig_fun.add_trace(
              go.Scatter(
                  x=sub_fun["Label_DH"],
                  y=sub_fun[col_key],
                  name=f"{met_label} ({nombre_m_str})",
                  mode="lines+markers+text",
                  text=text_labels,
                  textposition="top center",
                  textfont=dict(size=10),
                  line=dict(color=c_base, width=2.5, dash=dash_style),
              ),
              secondary_y=not is_pct
          )

      fig_fun.update_layout(title="<b>Comportamiento Acumulado de Funnel por Día Hábil</b>", barmode='group', height=560, hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
      fig_fun.update_yaxes(title_text="Porcentaje Acumulado (%)", ticksuffix="%", secondary_y=False)
      fig_fun.update_yaxes(title_text="Volumen Acumulado (Cantidad)", showgrid=False, secondary_y=True)
      st.plotly_chart(fig_fun, use_container_width=True)

      if vista_matriz_funnel:
        dh_labels_m2 = sorted(df_dh_funnel_plot["Label_DH"].dropna().unique().tolist(), key=lambda x: int(re.search(r'\d+', str(x)).group()) if re.search(r'\d+', str(x)) else 0)
        df_matrix_f = pd.DataFrame({"Label_DH": dh_labels_m2})

        for y_m, m_m in meses_tendencia_filtrados:
          m_name = nombres_meses.get(m_m, str(m_m)).title()
          sub_df = df_dh_funnel_plot[(df_dh_funnel_plot["Año"] == y_m) & (df_dh_funnel_plot["Mes"] == m_m)]
          for met_label in met_funnel_sel:
            col_key, kind = metricas_funnel_map[met_label]
            mapping = dict(zip(sub_df["Label_DH"], sub_df[col_key]))
            df_matrix_f[f"{met_label} ({m_name})"] = df_matrix_f["Label_DH"].map(mapping)

        df_matrix_f_html = df_matrix_f.astype(object)
        curr_m_name = nombres_meses.get(mes_sel).title()

        idx_curr_m = [i for i, (y, m) in enumerate(meses_tendencia) if y == año_sel and m == mes_sel]
        prev_m_name = nombres_meses.get(meses_tendencia[idx_curr_m[0] - 1][1]).title() if (idx_curr_m and idx_curr_m[0] > 0) else None
        prev_months_names = [nombres_meses.get(m).title() for y, m in meses_tendencia if not (y == año_sel and m == mes_sel)]

        for col in df_matrix_f.columns:
          if col == "Label_DH": continue
          is_curr_month_col = f"({curr_m_name})" in col
          base_met = col.rsplit(" (", 1)[0]
          kind = metricas_funnel_map[base_met][1] if base_met in metricas_funnel_map else "pct"

          for idx in df_matrix_f.index:
            val = df_matrix_f.at[idx, col]
            if pd.isna(val):
              df_matrix_f_html.at[idx, col] = "-"
            else:
              if is_curr_month_col:
                prev_cols_met = [f"{base_met} ({pm})" for pm in prev_months_names]
                prev_vals = [df_matrix_f.at[idx, pc] for pc in prev_cols_met if pc in df_matrix_f.columns and pd.notna(df_matrix_f.at[idx, pc])]

                prom_html = ""
                if prev_vals:
                  avg_prev = sum(prev_vals) / len(prev_vals)
                  if kind == "pct":
                    diff_prom = val - avg_prev
                    arrow_p = "⬆️" if diff_prom >= 0 else "⬇️"
                    color_p = "#15803d" if (diff_prom >= 0 if "Eval" in base_met or "LE" in base_met else diff_prom <= 0) else "#b91c1c"
                    prom_html = f'<span style="font-size:10px; color:{color_p}; font-weight:bold;">{arrow_p} Prom: {diff_prom:+.1f}%</span>'
                  else:
                    pct_change_prom = ((val - avg_prev) / avg_prev * 100.0) if avg_prev > 0 else 0
                    arrow_p = "⬆️" if pct_change_prom >= 0 else "⬇️"
                    color_p = "#15803d" if pct_change_prom >= 0 else "#b91c1c"
                    prom_html = f'<span style="font-size:10px; color:{color_p}; font-weight:bold;">{arrow_p} Prom: {pct_change_prom:+.1f}%</span>'

                ant_html = ""
                if prev_m_name:
                  prev_col_ant = f"{base_met} ({prev_m_name})"
                  if prev_col_ant in df_matrix_f.columns and pd.notna(df_matrix_f.at[idx, prev_col_ant]):
                    val_ant = df_matrix_f.at[idx, prev_col_ant]
                    if kind == "pct":
                      diff_ant = val - val_ant
                      arrow_a = "⬆️" if diff_ant >= 0 else "⬇️"
                      color_a = "#15803d" if (diff_ant >= 0 if "Eval" in base_met or "LE" in base_met else diff_ant <= 0) else "#b91c1c"
                      ant_html = f'<span style="font-size:10px; color:{color_a}; font-weight:bold;">{arrow_a} vs Ant: {diff_ant:+.1f}%</span>'
                    else:
                      pct_change_ant = ((val - val_ant) / val_ant * 100.0) if val_ant > 0 else 0
                      arrow_a = "⬆️" if pct_change_ant >= 0 else "⬇️"
                      color_a = "#15803d" if pct_change_ant >= 0 else "#b91c1c"
                      ant_html = f'<span style="font-size:10px; color:{color_a}; font-weight:bold;">{arrow_a} vs Ant: {pct_change_ant:+.1f}%</span>'

                sub_info = "<br>".join([h for h in [prom_html, ant_html] if h])
                formatted_val = f"{val:.1f}%" if kind == "pct" else f"{int(val):,}"
                if sub_info:
                  df_matrix_f_html.at[idx, col] = f'<div style="text-align:center; line-height:1.2;"><b>{formatted_val}</b><br>{sub_info}</div>'
                else:
                  df_matrix_f_html.at[idx, col] = f'<div style="text-align:center;"><b>{formatted_val}</b></div>'
              else:
                formatted_val = f"{val:.1f}%" if kind == "pct" else f"{int(val):,}"
                df_matrix_f_html.at[idx, col] = f'<div style="text-align:center;">{formatted_val}</div>'

        html_table_f = df_matrix_f_html.to_html(escape=False, index=False)
        html_table_f = html_table_f.replace('<table border="1" class="dataframe">', '<table style="width: 100%; border-collapse: collapse; font-size: 12.5px; font-family: sans-serif; background-color: #ffffff; border: 1px solid #cbd5e1; margin-bottom: 20px;">')
        html_table_f = html_table_f.replace('<th>', '<th style="background-color: #f1f5f9; border-bottom: 2px solid #6366f1; padding: 10px 8px; text-align: center; color: #1e1b4b; font-weight: 700;">')
        html_table_f = html_table_f.replace('<td>', '<td style="border-bottom: 1px solid #e2e8f0; padding: 10px 8px; text-align: center; color: #0f172a; vertical-align: middle;">')

        st.markdown("##### 📋 Matriz Comparativa Detallada de Funnel por Día Hábil (ACUMULADO)")
        st.markdown(f'<div style="overflow-x: auto; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">{html_table_f}</div>', unsafe_allow_html=True)

      df_fun_curr = df_dh_funnel[(df_dh_funnel["Año"] == año_sel) & (df_dh_funnel["Mes"] == mes_sel)]
      if not df_fun_curr.empty:
        ult_fun = df_fun_curr.iloc[-1]
        dh_fun_num = int(ult_fun["Día_Hábil"])
        pct_eval_curr = ult_fun["%_Eval_Acum"]
        pct_nogest_curr = ult_fun["%_NoGest_Acum"]
        pct_decl_curr = ult_fun["%_Decl_Acum"]
        pct_canc_curr = ult_fun["%_Canc_Acum"]
        eval_acum_val = int(ult_fun["Eval_Acum"])
        le_acum_val = int(ult_fun["LE_Acum"])

        df_fun_prevs = df_dh_funnel[(df_dh_funnel["Día_Hábil"] == dh_fun_num) & ((df_dh_funnel["Año"] != año_sel) | (df_dh_funnel["Mes"] != mes_sel))]
        prom_eval_hist = df_fun_prevs["%_Eval_Acum"].mean() if not df_fun_prevs.empty else 20.0
        prom_nogest_hist = df_fun_prevs["%_NoGest_Acum"].mean() if not df_fun_prevs.empty else 1.0
        prom_decl_hist = df_fun_prevs["%_Decl_Acum"].mean() if not df_fun_prevs.empty else 15.0

        diff_eval_fun = pct_eval_curr - prom_eval_hist
        diff_nogest_fun = pct_nogest_curr - prom_nogest_hist
        diff_decl_fun = pct_decl_curr - prom_decl_hist

        if len(meses_tendencia) > 1:
          y_prev, m_prev = meses_tendencia[-2]
          nom_prev = nombres_meses.get(m_prev).title()
          df_prev_fun = df_dh_funnel[(df_dh_funnel["Año"] == y_prev) & (df_dh_funnel["Mes"] == m_prev) & (df_dh_funnel["Día_Hábil"] == dh_fun_num)]
          if not df_prev_fun.empty:
            p_eval_prev = df_prev_fun.iloc[0]["%_Eval_Acum"]
            p_decl_prev = df_prev_fun.iloc[0]["%_Decl_Acum"]
            txt_comp_prev_fun = f"vs <b>{nom_prev} ({p_eval_prev:.1f}% Eval / {p_decl_prev:.1f}% Decl)</b>, el mes actual presenta una variación de <b style='color:{'#15803d' if (pct_eval_curr - p_eval_prev) >= 0 else '#b91c1c'}'>{(pct_eval_curr - p_eval_prev):+.1f}%</b> en evaluación acumulada."
          else: txt_comp_prev_fun = "Sin registro directo del mes anterior en este mismo día hábil."
        else: txt_comp_prev_fun = ""

        badge_funnel = (f'<span class="arrow-badge-up" style="background-color:#e0e7ff; color:#3730a3;">📊 Tasa de Evaluación Acumulada: {pct_eval_curr:.1f}%</span>')

        st.markdown(
            f"""
            <div class="diag-box-funnel">
                <div class="diag-header-funnel">📌 Diagnóstico Gerencial de Embudo y Comportamiento de Cartera — CORTE A DH {dh_fun_num}</div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <div>
                        <span style="font-size:13px; color:#4338ca; font-weight:700;">SALUD ACUMULADA DEL EMBUDO:</span>
                        <b style="font-size:18px; color:#1e1b4b; margin-left:8px;">{pct_eval_curr:.1f}% Evaluado</b>
                        <span style="font-size:12px; color:#6366f1;">({eval_acum_val:,} de {le_acum_val:,} LE Acumulados)</span>
                    </div>
                    <div>{badge_funnel}</div>
                </div>
                <div style="border-top: 1px dashed #a5b4fc; padding-top:10px;">
                    <div style="font-size:13px; font-weight:800; color:#1e1b4b; margin-bottom:6px;">Análisis de Indicadores Acumulados y Tendencias:</div>
                    <div class="causal-item">
                        • <b>Tasa de Evaluación de Leads Acumulada:</b> Al DH {dh_fun_num}, se ha evaluado el <b>{pct_eval_curr:.1f}%</b> de los leads efectivos ({eval_acum_val:,} dictámenes), lo que refleja una variación de <b style="color:{'#15803d' if diff_eval_fun >= 0 else '#b91c1c'};">{diff_eval_fun:+.1f}%</b> frente al promedio histórico del mismo día hábil ({prom_eval_hist:.1f}%). {txt_comp_prev_fun}
                    </div>
                    <div class="causal-item">
                        • <b>Nivel de Declinación Acumulada:</b> La tasa de declinación acumulada se sitúa en <b>{pct_decl_curr:.1f}%</b>, mostrando una variación de <b style="color:{'#b91c1c' if diff_decl_fun > 0 else '#15803d'};">{diff_decl_fun:+.1f}%</b> respecto a la media de meses anteriores ({prom_decl_hist:.1f}%).
                    </div>
                    <div class="causal-item">
                        • <b>Proporción Sin Dictaminar (No Gestionados) & Cancelados:</b> Los leads no gestionados representan el <b>{pct_nogest_curr:.1f}%</b> acumulado ({diff_nogest_fun:+.1f}% vs promedio histórico), mientras que los cancelados se mantienen en el <b>{pct_canc_curr:.1f}%</b>.
                    </div>
                    <div style="background-color:#ffffff; padding:12px 14px; border-radius:6px; margin-top:10px; font-size:12px; color:#312e81; border-left:4px solid #4f46e5; box-shadow: 0 1px 2px rgba(0,0,0,0.03);">
                        <div style="font-weight:800; color:#1e1b4b; margin-bottom:4px;">📌 Conclusión Gerencial & Recomendaciones de Calidad:</div>
                        <div>Se observa una tendencia de evaluación acumulada del <b>{pct_eval_curr:.1f}%</b> con una declinación del <b>{pct_decl_curr:.1f}%</b> al DH {dh_fun_num}. Se sugiere revisar el perfilamiento inicial y las variables de prefiltro en la prospección para optimizar la conversión, asegurando que los leads que ingresan al embudo mantengan una alta probabilidad de dictamen favorable.</div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

  else:
    st.warning("⚠️ No se encontró la hoja de Ventas o le faltan columnas.")

# =========================================================================
# 👥 MÓDULO 2: ANÁLISIS OPERATIVO - ASESORES & SUPERVISORES (CON FORMATO CONDICIONAL & HISTÓRICO MULTIMES)
# =========================================================================
elif opcion_hoja == "👥 Operación - Asesores & Supervisores":
  st.sidebar.header("🔍 Filtros de Fecha General")

  fechas_validas = pd.Series(df_ventas["F_VTA"] if "F_VTA" in df_ventas.columns else []).dropna()
  años_disp = (sorted(pd.to_datetime(fechas_validas).dt.year.unique()) if not fechas_validas.empty else [date.today().year])
  año_sel = st.sidebar.selectbox("Año Operativo", años_disp, index=len(años_disp) - 1, key="op_año_sel")

  meses_disp = (sorted(pd.to_datetime(fechas_validas[pd.to_datetime(fechas_validas).dt.year == año_sel]).dt.month.unique()) if not fechas_validas.empty else [date.today().month])
  nombres_meses = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
  mes_formateado = [nombres_meses[m] for m in meses_disp if m in nombres_meses]
  mes_sel_nombre = (st.sidebar.selectbox("Mes Operativo", mes_formateado, index=len(mes_formateado) - 1, key="op_mes_sel") if mes_formateado else "Noviembre")
  mes_sel = list(nombres_meses.keys())[list(nombres_meses.values()).index(mes_sel_nombre)]

  st.title(f"👥 Análisis Operativo por Asesor y Supervisor - {mes_sel_nombre} {año_sel}")

  # -------------------------------------------------------------------------
  # 0. FUNCIONES DE APOYO & FILTRADO DE DISTRIBUCIÓN DINÁMICO POR MES
  # -------------------------------------------------------------------------
  def obtener_distribucion_mes(df_dist, anio, mes):
    """Filtra la hoja de distribución exactamente para el año y mes seleccionados."""
    if df_dist.empty:
      return df_dist
    df_sub = df_dist.copy()
    col_mes = next((c for c in df_sub.columns if str(c).strip().lower() in ["mes", "month", "mes_num", "num_mes", "periodo"]), None)
    col_fecha = next((c for c in df_sub.columns if str(c).strip().lower() in ["fecha", "f_vta", "date", "fecha_dist"]), None)
    
    if col_fecha:
      fechas_dt = pd.to_datetime(df_sub[col_fecha], errors='coerce')
      mask = (fechas_dt.dt.month == mes)
      col_anio = next((c for c in df_sub.columns if str(c).strip().lower() in ["año", "anio", "year"]), None)
      if col_anio:
        mask = mask & (pd.to_numeric(df_sub[col_anio], errors='coerce') == anio)
      elif fechas_dt.dt.year.notna().any():
        mask = mask & (fechas_dt.dt.year == anio)
      if mask.any():
        return df_sub[mask]
        
    if col_mes:
      val_sample = df_sub[col_mes].dropna().iloc[0] if not df_sub[col_mes].dropna().empty else None
      if isinstance(val_sample, (int, float, np.number)) or str(val_sample).isdigit():
        mask = (pd.to_numeric(df_sub[col_mes], errors='coerce') == mes)
      else:
        nombres = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}
        target_name = nombres.get(mes, "")
        mask = df_sub[col_mes].astype(str).str.strip().str.lower().str.startswith(target_name)
      
      col_anio = next((c for c in df_sub.columns if str(c).strip().lower() in ["año", "anio", "year"]), None)
      if col_anio:
        mask = mask & (pd.to_numeric(df_sub[col_anio], errors='coerce') == anio)
        
      if mask.any():
        return df_sub[mask]
        
    return df_sub

  df_dist_mes = obtener_distribucion_mes(df_distribucion, año_sel, mes_sel)

  def calcular_meta_le_mx(anio, mes, hasta_dia=None):
    festivos_mx = holidays.Mexico(years=anio)
    num_dias = calendar.monthrange(anio, mes)[1]
    max_d = hasta_dia if hasta_dia else num_dias
    
    meta_acum = 0.0
    for d in range(1, max_d + 1):
      f = date(anio, mes, d)
      if f in festivos_mx or f.weekday() == 6:
        continue
      elif f.weekday() == 5:
        meta_acum += 2.05
      else:
        meta_acum += 4.10
    return meta_acum

  hoy = date.today()
  if año_sel == hoy.year and mes_sel == hoy.month:
    dia_corte_ayer = max(1, hoy.day - 1)
  else:
    dia_corte_ayer = calendar.monthrange(año_sel, mes_sel)[1]

  meta_le_ind_ayer = calcular_meta_le_mx(año_sel, mes_sel, dia_corte_ayer)
  meta_le_ind_mes = calcular_meta_le_mx(año_sel, mes_sel)

  tabla_comisiones_cop = {
      0: 0, 11: 103500, 12: 165600, 13: 186300, 14: 207000, 15: 269100,
      16: 331200, 17: 393300, 18: 434700, 19: 455400, 20: 476100, 21: 496800,
      22: 507150, 23: 538200, 24: 610650, 25: 714150, 26: 817650, 27: 921150,
      28: 1024650, 29: 1128150, 30: 1231650, 31: 1335150, 32: 1438650, 33: 1542150,
      34: 1645650, 35: 1749150, 36: 1852650, 37: 1956150, 38: 2059650, 39: 2163150
  }

  def obtener_comision_cop(puntos):
    pts = int(np.floor(puntos))
    if pts < 11: return 0
    if pts >= 39: return tabla_comisiones_cop[39]
    return tabla_comisiones_cop.get(pts, 0)

  # -------------------------------------------------------------------------
  # 1. FILTROS LOCALES DE OPERACIÓN CON SUPERVISORES DEL MES SELECCIONADO
  # -------------------------------------------------------------------------
  st.markdown("##### 🎛️ Filtros de Control Operativo (Local de la Hoja)")
  col_op_f1, col_op_f2 = st.columns(2)

  supervisores_set = set()
  if not df_dist_mes.empty and "Supervisor" in df_dist_mes.columns:
    supervisores_set.update(df_dist_mes["Supervisor"].dropna().unique())
  if "Supervisor" in df_ventas.columns:
    vta_mes_sups = df_ventas[(pd.to_datetime(df_ventas["F_VTA"]).dt.year == año_sel) & (pd.to_datetime(df_ventas["F_VTA"]).dt.month == mes_sel)]["Supervisor"].dropna().unique()
    supervisores_set.update(vta_mes_sups)

  supervisores_disp = ["Todos"] + sorted(list(supervisores_set))

  with col_op_f1:
    sup_sel = st.selectbox("Filtrar por Supervisor:", supervisores_disp, index=0, key="op_sup_filter")

  df_dist_sub = df_dist_mes.copy()
  if sup_sel != "Todos" and not df_dist_sub.empty and "Supervisor" in df_dist_sub.columns:
    df_dist_sub = df_dist_sub[df_dist_sub["Supervisor"] == sup_sel]

  asesores_set = set()
  if not df_dist_sub.empty and "agente" in df_dist_sub.columns:
    asesores_set.update(df_dist_sub["agente"].dropna().unique())
  if "agente" in df_ventas.columns:
    vta_mes_agts = df_ventas[(pd.to_datetime(df_ventas["F_VTA"]).dt.year == año_sel) & (pd.to_datetime(df_ventas["F_VTA"]).dt.month == mes_sel)]["agente"].dropna().unique()
    asesores_set.update(vta_mes_agts)

  asesores_disp = ["Todos"] + sorted(list(asesores_set))

  with col_op_f2:
    asesor_op_sel = st.selectbox("Filtrar por Asesor:", asesores_disp, index=0, key="op_agt_filter")

  # -------------------------------------------------------------------------
  # 2. MAPEO Y FILTRADO DE DATASETS CON LA PLANTILLA DEL MES SELECCIONADO
  # -------------------------------------------------------------------------
  df_vta_op = df_ventas[(pd.to_datetime(df_ventas["F_VTA"]).dt.year == año_sel) & (pd.to_datetime(df_ventas["F_VTA"]).dt.month == mes_sel)].copy()

  if not df_calls.empty:
    col_fcall = "F_CALL" if "F_CALL" in df_calls.columns else next((c for c in df_calls.columns if str(c).upper() in ["FECHA", "DATE"]), None)
    if col_fcall:
      df_calls_op = df_calls[(pd.to_datetime(df_calls[col_fcall]).dt.year == año_sel) & (pd.to_datetime(df_calls[col_fcall]).dt.month == mes_sel)].copy()
    else:
      df_calls_op = df_calls.copy()
  else:
    df_calls_op = pd.DataFrame()

  if not df_dist_mes.empty and "id_per_clean" in df_dist_mes.columns:
    dist_sub_m = df_dist_mes.drop_duplicates(subset=["id_per_clean"]).copy()
    cols_map_m = ["id_per_clean"]
    if "Supervisor" in dist_sub_m.columns: cols_map_m.append("Supervisor")
    if "agente" in dist_sub_m.columns: cols_map_m.append("agente")

    if not df_vta_op.empty and "id_per_clean" in df_vta_op.columns:
      df_vta_op = pd.merge(df_vta_op, dist_sub_m[cols_map_m], on="id_per_clean", how="left", suffixes=("", "_dist_m"))
      if "Supervisor_dist_m" in df_vta_op.columns:
        df_vta_op["Supervisor"] = df_vta_op["Supervisor_dist_m"].fillna(df_vta_op.get("Supervisor", "Sin Supervisor"))
      if "agente_dist_m" in df_vta_op.columns:
        df_vta_op["agente"] = df_vta_op["agente_dist_m"].fillna(df_vta_op.get("agente", "Sin Asesor"))

    if not df_calls_op.empty and "id_per_clean" in df_calls_op.columns:
      df_calls_op = pd.merge(df_calls_op, dist_sub_m[cols_map_m], on="id_per_clean", how="left", suffixes=("", "_dist_m"))
      if "Supervisor_dist_m" in df_calls_op.columns:
        df_calls_op["Supervisor"] = df_calls_op["Supervisor_dist_m"].fillna(df_calls_op.get("Supervisor", "Sin Supervisor"))
      if "agente_dist_m" in df_calls_op.columns:
        df_calls_op["agente"] = df_calls_op["agente_dist_m"].fillna(df_calls_op.get("agente", "Sin Asesor"))

  if sup_sel != "Todos":
    if "Supervisor" in df_vta_op.columns: df_vta_op = df_vta_op[df_vta_op["Supervisor"] == sup_sel]
    if not df_calls_op.empty and "Supervisor" in df_calls_op.columns: df_calls_op = df_calls_op[df_calls_op["Supervisor"] == sup_sel]

  if asesor_op_sel != "Todos":
    if "agente" in df_vta_op.columns: df_vta_op = df_vta_op[df_vta_op["agente"] == asesor_op_sel]
    if not df_calls_op.empty and "agente" in df_calls_op.columns: df_calls_op = df_calls_op[df_calls_op["agente"] == asesor_op_sel]

  if not df_dist_mes.empty:
    df_dist_sup_count = df_dist_mes.copy()
    if sup_sel != "Todos" and "Supervisor" in df_dist_sup_count.columns:
      df_dist_sup_count = df_dist_sup_count[df_dist_sup_count["Supervisor"] == sup_sel]
    
    if col_id_dist and col_id_dist in df_dist_sup_count.columns:
      asesores_dist_count = len(df_dist_sup_count[col_id_dist].dropna().unique())
    elif "agente" in df_dist_sup_count.columns:
      asesores_dist_count = len(df_dist_sup_count["agente"].dropna().astype(str).str.strip().unique())
    else:
      asesores_dist_count = 0
  else:
    asesores_dist_count = 0

  if asesores_dist_count > 0:
    agt_activos_count = float(asesores_dist_count)
  else:
    asesores_activos_set = set()
    if not df_vta_op.empty and "agente" in df_vta_op.columns:
      asesores_activos_set.update(df_vta_op["agente"].dropna().astype(str).str.strip().unique())
    if not df_calls_op.empty and "agente" in df_calls_op.columns:
      asesores_activos_set.update(df_calls_op["agente"].dropna().astype(str).str.strip().unique())
    agt_activos_count = float(len(asesores_activos_set)) if len(asesores_activos_set) > 0 else 1.0

  if asesor_op_sel != "Todos":
    agt_activos_count = 1.0

  # -------------------------------------------------------------------------
  # 3. AGRUPACIÓN COMPLETA POR ASESOR (SUMA COLUMNA PUNTOS DE VENTAS)
  # -------------------------------------------------------------------------
  col_puntos_vta = next((c for c in df_ventas.columns if str(c).strip().upper() in ["PUNTOS", "PUNTO", "PTS", "PUNTOS_VTA", "PUNTO_VTA", "PUNTOS TARJETA"]), None)

  def agrupar_por_asesor_completo(df_sub, df_vta_full, df_calls_sub):
    records = []
    col_agente = "agente" if "agente" in df_sub.columns else ("asesor" if "asesor" in df_sub.columns else df_sub.columns[0])
    inicio_m_func = date(año_sel, mes_sel, 1)

    llamadas_dict = {}
    if not df_calls_sub.empty:
      col_agt_c = "agente" if "agente" in df_calls_sub.columns else next((c for c in df_calls_sub.columns if str(c).strip().lower() in ["asesor", "agente", "nombre"]), df_calls_sub.columns[0])
      col_val_c = "Calls_Val" if "Calls_Val" in df_calls_sub.columns else next((c for c in df_calls_sub.columns if str(c).strip().lower() in ["calls", "llamadas_val", "llamadas", "duracion"]), df_calls_sub.columns[-1])
      for _, r_call in df_calls_sub.iterrows():
        k_agt = str(r_call[col_agt_c]).strip().upper()
        v_c = r_call[col_val_c]
        try:
          val_call_num = float(v_c) if pd.notna(v_c) else 0.0
        except (ValueError, TypeError):
          val_call_num = 0.0
        llamadas_dict[k_agt] = llamadas_dict.get(k_agt, 0.0) + val_call_num

    for agt, grp in df_sub.groupby(col_agente):
      agt_key = str(agt).strip().upper()
      sup_agt = grp["Supervisor"].iloc[0] if "Supervisor" in grp.columns and pd.notna(grp["Supervisor"].iloc[0]) else "Sin Supervisor"
      
      is_le = grp["ESTADO"] == "LEAD EFECTIVO" if "ESTADO" in grp.columns else pd.Series(True, index=grp.index)
      dec = grp["DECISION"].astype(str).str.strip().str.upper() if "DECISION" in grp.columns else pd.Series("", index=grp.index)
      bx_empty_series = grp["BX_EMPTY"] if "BX_EMPTY" in grp.columns else pd.Series(False, index=grp.index)

      is_eval = is_le & dec.isin(["A", "D", "P", "C"])
      is_no_eval = is_le & (dec.isin(["-", "NONE", "NAN", ""]) | bx_empty_series)

      tram = float(len(grp))
      le_v = float(is_le.sum())
      no_cap = float((grp["ESTADO"] == "LEAD NO CAPTURADO").sum()) if "ESTADO" in grp.columns else 0.0
      no_cond = float((grp["ESTADO"] == "LEAD NO CONDICIONES").sum()) if "ESTADO" in grp.columns else 0.0
      otros = float((~grp["ESTADO"].isin(["LEAD EFECTIVO", "LEAD NO CAPTURADO", "LEAD NO CONDICIONES", "", "NAN"])).sum()) if "ESTADO" in grp.columns else 0.0

      meta_le_ind = float(meta_le_ind_mes)
      pct_cump_le = (le_v / meta_le_ind) if meta_le_ind > 0 else 0.0

      if "F_DEC_EFF" in grp.columns and "DECISION" in grp.columns:
        ap_m_mask = is_le & (pd.to_datetime(grp["F_DEC_EFF"]).dt.year == año_sel) & (pd.to_datetime(grp["F_DEC_EFF"]).dt.month == mes_sel) & (dec == "A")
        ap_m = float(ap_m_mask.sum())
      else:
        ap_m_mask = pd.Series(False, index=grp.index)
        ap_m = 0.0

      if not df_vta_full.empty and "agente" in df_vta_full.columns and "F_DEC_EFF" in df_vta_full.columns:
        df_cos_agt = df_vta_full[
            (df_vta_full["agente"].astype(str).str.strip().str.upper() == agt_key) &
            (pd.to_datetime(df_vta_full["F_DEC_EFF"]).dt.year == año_sel) &
            (pd.to_datetime(df_vta_full["F_DEC_EFF"]).dt.month == mes_sel) &
            (pd.to_datetime(df_vta_full["F_VTA"]) < pd.Timestamp(inicio_m_func)) &
            (df_vta_full["DECISION"].astype(str).str.strip().str.upper() == "A")
        ]
        ap_cos = float(len(df_cos_agt))
      else:
        df_cos_agt = pd.DataFrame()
        ap_cos = 0.0

      ap_tot = ap_m + ap_cos

      if col_puntos_vta and col_puntos_vta in grp.columns:
        pts_mes = pd.to_numeric(grp.loc[ap_m_mask, col_puntos_vta], errors="coerce").fillna(1.0).sum()
        pts_cos = (pd.to_numeric(df_cos_agt[col_puntos_vta], errors="coerce").fillna(1.0).sum() if not df_cos_agt.empty and col_puntos_vta in df_cos_agt.columns else 0.0)
        pts_val = float(pts_mes + pts_cos)
      else:
        pts_val = float(ap_tot)

      eval_v = float(is_eval.sum())
      no_eval_v = float(is_no_eval.sum())
      decl_v = float((is_le & (dec == "D")).sum())
      canc_v = float((is_le & (dec == "C")).sum())
      pend_v = float((is_le & (dec == "P")).sum())

      llam_ef = llamadas_dict.get(agt_key, 0.0)
      cr_llam = (tram / llam_ef) if llam_ef > 0 else 0.0

      pct_le = (le_v / tram) if tram > 0 else 0.0
      pct_rem = (otros / tram) if tram > 0 else 0.0

      pct_ap_m = (ap_m / le_v) if le_v > 0 else 0.0
      pct_ap_tot = (ap_tot / le_v) if le_v > 0 else 0.0

      pct_eval = (eval_v / le_v) if le_v > 0 else 0.0
      pct_no_eval = (no_eval_v / le_v) if le_v > 0 else 0.0
      pct_decl = (decl_v / le_v) if le_v > 0 else 0.0
      pct_canc = (canc_v / le_v) if le_v > 0 else 0.0
      pct_pend = (pend_v / le_v) if le_v > 0 else 0.0

      pct_cump_puntos = (pts_val / 11.0) if pts_val > 0 else 0.0
      comision_cop_val = float(obtener_comision_cop(pts_val))

      records.append({
          "Asesor": agt,
          "Supervisor": sup_agt,
          "Llamadas Efectivas": llam_ef,
          "Trámites": tram,
          "Meta LE": meta_le_ind,
          "LE": le_v,
          "% Cump LE": pct_cump_le,
          "CR / Llamadas": cr_llam,
          "Desbordamiento / Llamadas": 0.0,
          "% Desbordamiento": 0.0,
          "No Cap": no_cap,
          "No Cond": no_cond,
          "Otros": otros,
          "% LE": pct_le,
          "% REM/RECH": pct_rem,
          "AP Mes": ap_m,
          "AP Cosecha": ap_cos,
          "Total AP": ap_tot,
          "% AP Mes": pct_ap_m,
          "% AP Total": pct_ap_tot,
          "Eval": eval_v,
          "% Eval": pct_eval,
          "No Evaluado": no_eval_v,
          "% No Evaluado": pct_no_eval,
          "Decl": decl_v,
          "% Decl": pct_decl,
          "Canc": canc_v,
          "% Canc": pct_canc,
          "Pend": pend_v,
          "% Pend": pct_pend,
          "Puntos": pts_val,
          "% Cump Puntos": pct_cump_puntos,
          "Comisión COP": comision_cop_val
      })
    return pd.DataFrame(records)

  if not df_vta_op.empty:
    df_matriz_agt_base = agrupar_por_asesor_completo(df_vta_op, df_ventas, df_calls_op)
  else:
    df_matriz_agt_base = pd.DataFrame()

  # -------------------------------------------------------------------------
  # 4. CÁLCULO DE KPIS GENERALES Y RECUADROS ADICIONALES (3x3 CON UMBRALES 25%/75%)
  # -------------------------------------------------------------------------
  le_op_total = float((df_vta_op["ESTADO"] == "LEAD EFECTIVO").sum()) if ("ESTADO" in df_vta_op.columns and not df_vta_op.empty) else 0.0
  tramites_op_total = float(len(df_vta_op))

  if not df_calls_op.empty and "Calls_Val" in df_calls_op.columns:
    llamadas_op_total = float(pd.to_numeric(df_calls_op["Calls_Val"], errors="coerce").fillna(0).sum())
  else:
    llamadas_op_total = 0.0

  meta_le_equipo_ayer = float(meta_le_ind_ayer) * agt_activos_count
  desviacion_le_equipo = le_op_total - meta_le_equipo_ayer
  pct_cumplimiento_le_equipo = (le_op_total / meta_le_equipo_ayer * 100.0) if meta_le_equipo_ayer > 0 else 0.0

  media_leads_real_asesor = le_op_total / agt_activos_count
  media_leads_esperada_asesor = float(meta_le_ind_ayer)
  desv_media_leads = media_leads_real_asesor - media_leads_esperada_asesor

  media_llamadas_asesor = llamadas_op_total / agt_activos_count

  inicio_m_op = date(año_sel, mes_sel, 1)
  df_ap_m_op = df_vta_op[(pd.to_datetime(df_vta_op["F_DEC_EFF"]).dt.year == año_sel) & (pd.to_datetime(df_vta_op["F_DEC_EFF"]).dt.month == mes_sel) & (df_vta_op["DECISION"] == "A")] if not df_vta_op.empty else pd.DataFrame()
  ap_mes_op = float(len(df_ap_m_op))

  df_ap_cos_op = df_ventas[
      (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.year == año_sel) &
      (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.month == mes_sel) &
      (pd.to_datetime(df_ventas["F_VTA"]) < pd.Timestamp(inicio_m_op)) &
      (df_ventas["DECISION"] == "A")
  ] if not df_ventas.empty else pd.DataFrame()
  
  if sup_sel != "Todos" and "Supervisor" in df_ap_cos_op.columns:
    df_ap_cos_op = df_ap_cos_op[df_ap_cos_op["Supervisor"] == sup_sel]
  if asesor_op_sel != "Todos" and "agente" in df_ap_cos_op.columns:
    df_ap_cos_op = df_ap_cos_op[df_ap_cos_op["agente"] == asesor_op_sel]

  ap_cos_op = float(len(df_ap_cos_op))
  ap_totales_op = ap_mes_op + ap_cos_op
  media_ap_asesor = ap_totales_op / agt_activos_count

  if not df_vta_op.empty and "DECISION" in df_vta_op.columns and "ESTADO" in df_vta_op.columns:
    evaluados_op = float(((df_vta_op["ESTADO"] == "LEAD EFECTIVO") & (df_vta_op["DECISION"].astype(str).str.strip().str.upper().isin(["A", "D", "P", "C"]))).sum())
  else:
    evaluados_op = 0.0

  pct_eval_op = (evaluados_op / le_op_total * 100.0) if le_op_total > 0 else 0.0

  puntos_totales_op = df_matriz_agt_base["Puntos"].sum() if not df_matriz_agt_base.empty else ap_totales_op
  media_puntos_asesor = puntos_totales_op / agt_activos_count

  if not df_matriz_agt_base.empty:
    df_agt_only = df_matriz_agt_base[df_matriz_agt_base["Asesor"] != "TOTAL GENERAL"].copy()
    total_asesores_eval = len(df_agt_only)

    cumplen_eval = int((df_agt_only["% Eval"] >= 0.25).sum())
    incumplen_eval = total_asesores_eval - cumplen_eval

    cumplen_no_eval = int((df_agt_only["% No Evaluado"] < 0.75).sum())
    incumplen_no_eval = total_asesores_eval - cumplen_no_eval

    asesores_comisionando_count = int((df_agt_only["Comisión COP"] > 0).sum())
    pct_comisionando = (asesores_comisionando_count / total_asesores_eval * 100.0) if total_asesores_eval > 0 else 0.0
    monto_total_comisiones = df_agt_only["Comisión COP"].sum()

    cr_media_op = (tramites_op_total / llamadas_op_total) if llamadas_op_total > 0 else 0.0
    cumplen_cr = int((df_agt_only["CR / Llamadas"] >= cr_media_op).sum())
    incumplen_cr = total_asesores_eval - cumplen_cr

    cumplen_llamadas = int((df_agt_only["Llamadas Efectivas"] <= media_llamadas_asesor).sum())
    incumplen_llamadas = total_asesores_eval - cumplen_llamadas
  else:
    total_asesores_eval = 0
    cumplen_eval = 0
    incumplen_eval = 0
    cumplen_no_eval = 0
    incumplen_no_eval = 0
    asesores_comisionando_count = 0
    pct_comisionando = 0.0
    monto_total_comisiones = 0.0
    cr_media_op = 0.0
    cumplen_cr = 0
    incumplen_cr = 0
    cumplen_llamadas = 0
    incumplen_llamadas = 0

  # -------------------------------------------------------------------------
  # RECUADROS KPI SUPERIORES (FILA 3x3 COMPLETA REAJUSTADA)
  # -------------------------------------------------------------------------
  col_kpi_r1, col_kpi_r2, col_kpi_r3 = st.columns(3)

  with col_kpi_r1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">LEADS EFECTIVOS (A AYER - DH {dia_corte_ayer})</div>
        <div class="kpi-value">{int(le_op_total):,}</div>
        <div class="kpi-subtext">Meta Equipo: <b>{meta_le_equipo_ayer:,.1f}</b></div>
        <div class="kpi-subtext">Desviación: <b style="color:{'#15803d' if desviacion_le_equipo >= 0 else '#b91c1c'};">{desviacion_le_equipo:+,.1f} ({pct_cumplimiento_le_equipo:.1f}%)</b></div>
    </div>
    """, unsafe_allow_html=True)

  with col_kpi_r2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">MEDIA LEADS POR ASESOR</div>
        <div class="kpi-value">{media_leads_real_asesor:,.1f}</div>
        <div class="kpi-subtext">Media Esperada a Ayer: <b>{media_leads_esperada_asesor:,.1f}</b></div>
        <div class="kpi-subtext">Desviación Ind.: <b style="color:{'#15803d' if desv_media_leads >= 0 else '#b91c1c'};">{desv_media_leads:+,.1f}</b></div>
    </div>
    """, unsafe_allow_html=True)

  with col_kpi_r3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">MEDIA LLAMADAS POR ASESOR</div>
        <div class="kpi-value">{media_llamadas_asesor:,.1f}</div>
        <div class="kpi-subtext">Llamadas Totales (Col E): <b>{int(llamadas_op_total):,}</b> | Asesores Activos: <b>{int(agt_activos_count)}</b></div>
        <div class="kpi-subtext">Cumplen (≤Media): <b style="color:#15803d;">{cumplen_llamadas}</b> | Incumplen (>Media): <b style="color:#b91c1c;">{incumplen_llamadas}</b></div>
    </div>
    """, unsafe_allow_html=True)

  col_kpi_r4, col_kpi_r5, col_kpi_r6 = st.columns(3)

  with col_kpi_r4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">AP MES / COSECHA / TOTALES</div>
        <div class="kpi-value">{int(ap_totales_op):,} <span style="font-size:14px; color:#64748b;">AP Tot.</span></div>
        <div class="kpi-subtext">AP Mes: <b>{int(ap_mes_op):,}</b> | AP Cosecha: <b>{int(ap_cos_op):,}</b></div>
        <div class="kpi-subtext">Media AP/Asesor: <b style="color:{'#15803d' if media_ap_asesor >= 5.0 else '#d97706'};">{media_ap_asesor:.1f}</b> (Obj: 5.0 AP)</div>
    </div>
    """, unsafe_allow_html=True)

  with col_kpi_r5:
    pct_cump_puntos_op = (media_puntos_asesor / 11.0 * 100.0) if 11.0 > 0 else 0.0
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">PUNTOS DE LA OPERACIÓN</div>
        <div class="kpi-value">{media_puntos_asesor:.1f} <span style="font-size:14px; color:#64748b;">Pts/Asesor</span></div>
        <div class="kpi-subtext">Objetivo: <b>11.0 Pts/Asesor</b> ({pct_cump_puntos_op:.1f}%)</div>
        <div class="kpi-subtext">Puntos Totales Operación: <b>{puntos_totales_op:,.1f}</b></div>
    </div>
    """, unsafe_allow_html=True)

  with col_kpi_r6:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">ASESORES COMISIONANDO</div>
        <div class="kpi-value">{asesores_comisionando_count} <span style="font-size:14px; color:#64748b;">Asesores</span></div>
        <div class="kpi-subtext">% Comisionando: <b>{pct_comisionando:.1f}%</b> ({asesores_comisionando_count}/{total_asesores_eval})</div>
        <div class="kpi-subtext">Total Comisiones COP: <b style="color:#15803d;">${monto_total_comisiones:,.0f}</b></div>
    </div>
    """, unsafe_allow_html=True)

  col_kpi_r7, col_kpi_r8, col_kpi_r9 = st.columns(3)

  with col_kpi_r7:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">% EVALUADO OPERACIÓN</div>
        <div class="kpi-value">{pct_eval_op:.1f}%</div>
        <div class="kpi-subtext">Objetivo Operación: <b>≥ 25.0%</b></div>
        <div class="kpi-subtext">Cumplen (≥25%): <b style="color:#15803d;">{cumplen_eval}</b> | Incumplen: <b style="color:#b91c1c;">{incumplen_eval}</b></div>
    </div>
    """, unsafe_allow_html=True)

  with col_kpi_r8:
    pct_no_eval_op = (100.0 - pct_eval_op) if le_op_total > 0 else 0.0
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">% NO EVALUADO OPERACIÓN</div>
        <div class="kpi-value">{pct_no_eval_op:.1f}%</div>
        <div class="kpi-subtext">Objetivo Operación: <b>< 75.0%</b></div>
        <div class="kpi-subtext">Cumplen (<75%): <b style="color:#15803d;">{cumplen_no_eval}</b> | Incumplen: <b style="color:#b91c1c;">{incumplen_no_eval}</b></div>
    </div>
    """, unsafe_allow_html=True)

  with col_kpi_r9:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-title">CONVERSIÓN CR% LLAMADAS</div>
        <div class="kpi-value">{cr_media_op:.1%}</div>
        <div class="kpi-subtext">Media Operación (Trámites/Llamadas)</div>
        <div class="kpi-subtext">En/Sobre Media: <b style="color:#15803d;">{cumplen_cr}</b> | Bajo Media: <b style="color:#b91c1c;">{incumplen_cr}</b></div>
    </div>
    """, unsafe_allow_html=True)

  st.divider()

  # -------------------------------------------------------------------------
  # 5. DOS MATRICES OPERATIVAS COMPARATIVAS INDEPENDIENTES (PRODUCTIVIDAD & CONVERSIÓN)
  # -------------------------------------------------------------------------
  if not df_matriz_agt_base.empty:
    df_matriz_agt = df_matriz_agt_base.copy()

    media_llamadas_op = df_matriz_agt["Llamadas Efectivas"].mean()
    df_matriz_agt["Desbordamiento / Llamadas"] = df_matriz_agt["Llamadas Efectivas"] - media_llamadas_op
    df_matriz_agt["% Desbordamiento"] = np.where(
        df_matriz_agt["Llamadas Efectivas"] > 0,
        df_matriz_agt["Desbordamiento / Llamadas"] / df_matriz_agt["Llamadas Efectivas"],
        0.0
    )

    tot_agt = df_matriz_agt.sum(numeric_only=True).to_dict()
    tot_agt["Asesor"] = "TOTAL GENERAL"
    tot_agt["Supervisor"] = "-"
    tot_agt["CR / Llamadas"] = (tot_agt["Trámites"] / tot_agt["Llamadas Efectivas"]) if tot_agt.get("Llamadas Efectivas", 0) > 0 else 0.0
    tot_agt["% Cump LE"] = (tot_agt["LE"] / tot_agt["Meta LE"]) if tot_agt.get("Meta LE", 0) > 0 else 0.0
    tot_agt["Desbordamiento / Llamadas"] = 0.0
    tot_agt["% Desbordamiento"] = 0.0
    tot_agt["% LE"] = (tot_agt["LE"] / tot_agt["Trámites"]) if tot_agt.get("Trámites", 0) > 0 else 0.0
    tot_agt["% REM/RECH"] = (tot_agt["Otros"] / tot_agt["Trámites"]) if tot_agt.get("Trámites", 0) > 0 else 0.0
    tot_agt["% AP Mes"] = (tot_agt["AP Mes"] / tot_agt["LE"]) if tot_agt.get("LE", 0) > 0 else 0.0
    tot_agt["% AP Total"] = (tot_agt["Total AP"] / tot_agt["LE"]) if tot_agt.get("LE", 0) > 0 else 0.0
    tot_agt["% Eval"] = (tot_agt["Eval"] / tot_agt["LE"]) if tot_agt.get("LE", 0) > 0 else 0.0
    tot_agt["% No Evaluado"] = (tot_agt["No Evaluado"] / tot_agt["LE"]) if tot_agt.get("LE", 0) > 0 else 0.0
    tot_agt["% Decl"] = (tot_agt["Decl"] / tot_agt["LE"]) if tot_agt.get("LE", 0) > 0 else 0.0
    tot_agt["% Canc"] = (tot_agt["Canc"] / tot_agt["LE"]) if tot_agt.get("LE", 0) > 0 else 0.0
    tot_agt["% Pend"] = (tot_agt["Pend"] / tot_agt["LE"]) if tot_agt.get("LE", 0) > 0 else 0.0
    tot_agt["% Cump Puntos"] = (tot_agt["Puntos"] / (11.0 * len(df_matriz_agt))) if len(df_matriz_agt) > 0 else 0.0

    df_matriz_completa = pd.concat([df_matriz_agt, pd.DataFrame([tot_agt])], ignore_index=True)

    cols_tabla_productividad = [
        "Asesor", "Supervisor", "Llamadas Efectivas", "Trámites", "Meta LE", "LE", "% Cump LE",
        "CR / Llamadas", "Desbordamiento / Llamadas", "% Desbordamiento", "No Cap", "No Cond",
        "Otros", "% LE", "% REM/RECH", "AP Mes", "AP Cosecha", "Total AP", "% AP Mes", "% AP Total"
    ]

    cols_tabla_conversion = [
        "Asesor", "Supervisor", "LE", "Eval", "% Eval", "No Evaluado", "% No Evaluado",
        "Decl", "% Decl", "Canc", "% Canc", "Pend", "% Pend", "AP Mes", "AP Cosecha",
        "Total AP", "% AP Mes", "% AP Total", "Puntos", "% Cump Puntos", "Comisión COP"
    ]

    df_productividad = df_matriz_completa[cols_tabla_productividad].copy()
    df_conversion = df_matriz_completa[cols_tabla_conversion].copy()

    format_prod_dict = {
        "Llamadas Efectivas": "{:,.0f}", "Trámites": "{:,.0f}", "Meta LE": "{:,.1f}", "LE": "{:,.0f}",
        "% Cump LE": "{:.1%}", "CR / Llamadas": "{:.1%}", "Desbordamiento / Llamadas": "{:+,.0f}",
        "% Desbordamiento": "{:+.1%}", "No Cap": "{:,.0f}", "No Cond": "{:,.0f}", "Otros": "{:,.0f}",
        "% LE": "{:.1%}", "% REM/RECH": "{:.1%}", "AP Mes": "{:,.0f}", "AP Cosecha": "{:,.0f}",
        "Total AP": "{:,.0f}", "% AP Mes": "{:.1%}", "% AP Total": "{:.1%}"
    }

    format_conv_dict = {
        "LE": "{:,.0f}", "Eval": "{:,.0f}", "% Eval": "{:.1%}", "No Evaluado": "{:,.0f}",
        "% No Evaluado": "{:.1%}", "Decl": "{:,.0f}", "% Decl": "{:.1%}", "Canc": "{:,.0f}",
        "% Canc": "{:.1%}", "Pend": "{:,.0f}", "% Pend": "{:.1%}", "AP Mes": "{:,.0f}",
        "AP Cosecha": "{:,.0f}", "Total AP": "{:,.0f}", "% AP Mes": "{:.1%}", "% AP Total": "{:.1%}",
        "Puntos": "{:,.1f}", "% Cump Puntos": "{:.1%}", "Comisión COP": "${:,.0f}"
    }

    rgb_green = (162, 217, 163)
    rgb_orange = (254, 210, 120)
    rgb_red = (248, 140, 140)
    rgb_white = (255, 255, 255)

    def aplicar_condicionales_t1(df_input):
      styles = pd.DataFrame("", index=df_input.index, columns=df_input.columns)
      df_no_tot = df_input[df_input["Asesor"] != "TOTAL GENERAL"]
      
      media_llamadas = df_no_tot["Llamadas Efectivas"].mean() if not df_no_tot.empty else 0.0
      max_dist_llam = max(
          (df_no_tot["Llamadas Efectivas"].max() - 1.1 * media_llamadas) if not df_no_tot.empty else 1.0,
          (0.9 * media_llamadas - df_no_tot["Llamadas Efectivas"].min()) if not df_no_tot.empty else 1.0,
          1.0
      )
      
      min_max = {}
      for col in ["% Cump LE", "CR / Llamadas", "% LE", "% AP Mes", "% AP Total"]:
        if col in df_no_tot.columns:
          s = pd.to_numeric(df_no_tot[col], errors="coerce").dropna()
          min_max[col] = (s.min() if not s.empty else 0.0, s.max() if not s.empty else 1.0)
        else:
          min_max[col] = (0.0, 1.0)

      for idx, row in df_input.iterrows():
        is_total = (row["Asesor"] == "TOTAL GENERAL")
        if is_total:
          styles.loc[idx, :] = "font-weight: bold; background-color: #f0f2f6; text-align: center !important;"
          continue
            
        for col in df_input.columns:
          cell_style = "text-align: center !important;"
          val = row[col]
          
          if isinstance(val, (int, float, np.number)) and not pd.isna(val):
            if col == "Llamadas Efectivas":
              lb, ub = 0.9 * media_llamadas, 1.1 * media_llamadas
              if lb <= val <= ub:
                bg = "background-color: #dcfce7; color: #15803d; font-weight: bold;"
              else:
                dist = val - ub if val > ub else lb - val
                norm = min(1.0, max(0.0, dist / max_dist_llam))
                r = int(254 + norm * (239 - 254))
                g = int(226 + norm * (68 - 226))
                b = int(226 + norm * (68 - 226))
                bg = f"background-color: rgb({r}, {g}, {b}); color: #7f1d1d; font-weight: bold;"
              cell_style += " " + bg
                    
            elif col in ["% Cump LE", "CR / Llamadas", "% LE"]:
              vmin, vmax = min_max[col]
              bg = interpolate_color_3pt(val, vmin, vmax, rgb_red, rgb_orange, rgb_green)
              if bg: cell_style += " " + bg

            elif col in ["Desbordamiento / Llamadas", "% Desbordamiento"]:
              if val > 0: bg = "background-color: #dcfce7; color: #15803d; font-weight: bold;"
              elif val < 0: bg = "background-color: #fee2e2; color: #b91c1c; font-weight: bold;"
              else: bg = ""
              if bg: cell_style += " " + bg
                    
            elif col == "Total AP":
              if val <= 1:
                bg = "background-color: #fee2e2; color: #991b1b; font-weight: bold;"
              elif val <= 3:
                bg = "background-color: #ffedd5; color: #9a3412; font-weight: bold;"
              elif val == 4:
                bg = "background-color: #d1fae5; color: #065f46; font-weight: bold;"
              else:
                bg = "background-color: #a7f3d0; color: #047857; font-weight: bold;"
              cell_style += " " + bg

            elif col in ["% AP Mes", "% AP Total"]:
              vmin, vmax = min_max[col]
              bg = interpolate_color_2pt(val, vmin, vmax, rgb_white, rgb_green)
              if bg: cell_style += " " + bg

          styles.loc[idx, col] = cell_style

      return styles

    def aplicar_condicionales_t2(df_input):
      styles = pd.DataFrame("", index=df_input.index, columns=df_input.columns)
      df_no_tot = df_input[df_input["Asesor"] != "TOTAL GENERAL"]
      
      min_max = {}
      for col in ["% Eval", "% AP Mes", "% AP Total", "Comisión COP"]:
        if col in df_no_tot.columns:
          s = pd.to_numeric(df_no_tot[col], errors="coerce").dropna()
          min_max[col] = (s.min() if not s.empty else 0.0, s.max() if not s.empty else 1.0)
        else:
          min_max[col] = (0.0, 1.0)

      for idx, row in df_input.iterrows():
        is_total = (row["Asesor"] == "TOTAL GENERAL")
        if is_total:
          styles.loc[idx, :] = "font-weight: bold; background-color: #f0f2f6; text-align: center !important;"
          continue
            
        for col in df_input.columns:
          cell_style = "text-align: center !important;"
          val = row[col]
          
          if isinstance(val, (int, float, np.number)) and not pd.isna(val):
            if col == "% Eval":
              vmin, vmax = min_max[col]
              bg = interpolate_color_3pt(val, vmin, vmax, rgb_red, rgb_orange, rgb_green)
              if bg: cell_style += " " + bg
                    
            elif col == "% No Evaluado":
              if val > 0.75:
                norm = min(1.0, (val - 0.75) / 0.25)
                r = int(254 + norm * (239 - 254))
                g = int(226 + norm * (68 - 226))
                b = int(226 + norm * (68 - 226))
                bg = f"background-color: rgb({r}, {g}, {b}); color: #7f1d1d; font-weight: bold;"
                cell_style += " " + bg
                        
            elif col == "Total AP":
              if val <= 1:
                bg = "background-color: #fee2e2; color: #991b1b; font-weight: bold;"
              elif val <= 3:
                bg = "background-color: #ffedd5; color: #9a3412; font-weight: bold;"
              elif val == 4:
                bg = "background-color: #d1fae5; color: #065f46; font-weight: bold;"
              else:
                bg = "background-color: #a7f3d0; color: #047857; font-weight: bold;"
              cell_style += " " + bg

            elif col in ["% AP Mes", "% AP Total"]:
              vmin, vmax = min_max[col]
              bg = interpolate_color_2pt(val, vmin, vmax, rgb_white, rgb_green)
              if bg: cell_style += " " + bg

            elif col == "Comisión COP":
              if val > 0:
                vmin, vmax = min_max[col]
                vmax_pos = max(vmax, 1.0)
                norm = min(1.0, max(0.0, val / vmax_pos))
                r = int(220 + norm * (34 - 220))
                g = int(252 + norm * (197 - 252))
                b = int(231 + norm * (94 - 231))
                color_txt = "#ffffff" if norm > 0.6 else "#065f46"
                bg = f"background-color: rgb({r}, {g}, {b}); color: {color_txt}; font-weight: bold;"
                cell_style += " " + bg

          styles.loc[idx, col] = cell_style

      return styles

    # TABLA 1: MATRIZ DE PRODUCTIVIDAD OPERATIVA
    st.subheader("📊 Matriz de Productividad Operativa por Asesor")
    styler_prod = (
        df_productividad.style.format(format_prod_dict)
        .set_properties(**{"text-align": "center !important", "font-size": "12px", "padding": "5px 3px"})
        .apply(aplicar_condicionales_t1, axis=None)
    )
    st.dataframe(styler_prod, use_container_width=True, height=520, hide_index=True)

    st.divider()

    # TABLA 2: MATRIZ DE CONVERSIÓN Y EFECTIVIDAD
    st.subheader("🎯 Matriz de Conversión y Efectividad por Asesor")
    styler_conv = (
        df_conversion.style.format(format_conv_dict)
        .set_properties(**{"text-align": "center !important", "font-size": "12px", "padding": "5px 3px"})
        .apply(aplicar_condicionales_t2, axis=None)
    )
    st.dataframe(styler_conv, use_container_width=True, height=520, hide_index=True)

    # -------------------------------------------------------------------------
    # 6. HISTÓRICO CONSOLIDADO MULTIMES POR ASESOR
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("📜 Histórico Consolidado por Asesor (Evolución Mes a Mes)")
    st.caption("Consulta la evolución mensual histórica de indicadores para un asesor específico a lo largo de todos los meses registrados.")

    todos_asesores_hist = sorted(df_ventas["agente"].dropna().astype(str).str.strip().unique().tolist()) if ("agente" in df_ventas.columns and not df_ventas.empty) else []
    
    if todos_asesores_hist:
      idx_default = 0
      if asesor_op_sel != "Todos" and asesor_op_sel in todos_asesores_hist:
        idx_default = todos_asesores_hist.index(asesor_op_sel)
      
      asesor_hist_sel = st.selectbox(
          "Seleccione Asesor para ver su Evolución Histórica:",
          options=todos_asesores_hist,
          index=idx_default,
          key="op_asesor_historico_select"
      )

      def agrupar_historico_asesor(asesor_nom, df_vta, df_calls_full, df_dist_full):
        if df_vta.empty or not asesor_nom:
          return pd.DataFrame(), pd.DataFrame()
        
        sub_vta = df_vta[df_vta["agente"].astype(str).str.strip().str.upper() == str(asesor_nom).strip().upper()].copy()
        if sub_vta.empty:
          return pd.DataFrame(), pd.DataFrame()
          
        sub_vta["Año"] = pd.to_datetime(sub_vta["F_VTA"]).dt.year
        sub_vta["Mes_Num"] = pd.to_datetime(sub_vta["F_VTA"]).dt.month
        
        periodos = sub_vta[["Año", "Mes_Num"]].drop_duplicates().sort_values(by=["Año", "Mes_Num"])

        # Identificadores (IDs) del asesor para cruzado exacto de llamadas y supervisor
        agent_ids = set()
        if "id_per_clean" in sub_vta.columns:
          agent_ids.update(sub_vta["id_per_clean"].dropna().unique())
        if not df_dist_full.empty:
          col_agt_d = next((c for c in df_dist_full.columns if str(c).strip().lower() in ["agente", "asesor", "nombre"]), None)
          col_id_d = "id_per_clean" if "id_per_clean" in df_dist_full.columns else next((c for c in df_dist_full.columns if str(c).strip().lower() in ["id_per", "id_user", "id"]), None)
          if col_agt_d and col_id_d:
            sub_d_ids = df_dist_full[df_dist_full[col_agt_d].astype(str).str.strip().str.upper() == str(asesor_nom).strip().upper()]
            agent_ids.update(pd.to_numeric(sub_d_ids[col_id_d], errors="coerce").dropna().unique())
        
        recs_prod = []
        recs_conv = []
        
        for _, p in periodos.iterrows():
          y, m = int(p["Año"]), int(p["Mes_Num"])
          mes_nom = f"{nombres_meses.get(m, str(m))} {y}"
          
          vta_m = sub_vta[(sub_vta["Año"] == y) & (sub_vta["Mes_Num"] == m)]
          
          # Búsqueda dinámica del Supervisor por mes
          sup_agt = "-"
          if "Supervisor" in vta_m.columns:
            valid_sups = [str(s).strip() for s in vta_m["Supervisor"].dropna() if str(s).strip() and str(s).strip().upper() not in ["-", "NAN", "NONE", "SIN SUPERVISOR"]]
            if valid_sups:
              sup_agt = valid_sups[0]
              
          if sup_agt == "-" and not df_dist_full.empty:
            dist_m = obtener_distribucion_mes(df_dist_full, y, m)
            if not dist_m.empty:
              col_sup_d = next((c for c in dist_m.columns if str(c).strip().lower() in ["supervisor", "supervisores"]), None)
              col_agt_d = next((c for c in dist_m.columns if str(c).strip().lower() in ["agente", "asesor", "nombre"]), None)
              col_id_d = "id_per_clean" if "id_per_clean" in dist_m.columns else next((c for c in dist_m.columns if str(c).strip().lower() in ["id_per", "id_user", "id"]), None)
              
              mask_d = pd.Series(False, index=dist_m.index)
              if col_agt_d:
                mask_d = mask_d | (dist_m[col_agt_d].astype(str).str.strip().str.upper() == str(asesor_nom).strip().upper())
              if col_id_d and agent_ids:
                mask_d = mask_d | (pd.to_numeric(dist_m[col_id_d], errors="coerce").isin(agent_ids))
                
              sub_d = dist_m[mask_d]
              if not sub_d.empty and col_sup_d:
                valid = [str(s).strip() for s in sub_d[col_sup_d].dropna() if str(s).strip() and str(s).strip().upper() not in ["-", "NAN", "NONE", "SIN SUPERVISOR"]]
                if valid:
                  sup_agt = valid[0]
                  
          if sup_agt == "-" and not df_dist_full.empty:
            col_sup_d = next((c for c in df_dist_full.columns if str(c).strip().lower() in ["supervisor", "supervisores"]), None)
            col_agt_d = next((c for c in df_dist_full.columns if str(c).strip().lower() in ["agente", "asesor", "nombre"]), None)
            col_id_d = "id_per_clean" if "id_per_clean" in df_dist_full.columns else next((c for c in df_dist_full.columns if str(c).strip().lower() in ["id_per", "id_user", "id"]), None)
            
            mask_d = pd.Series(False, index=df_dist_full.index)
            if col_agt_d:
              mask_d = mask_d | (df_dist_full[col_agt_d].astype(str).str.strip().str.upper() == str(asesor_nom).strip().upper())
            if col_id_d and agent_ids:
              mask_d = mask_d | (pd.to_numeric(df_dist_full[col_id_d], errors="coerce").isin(agent_ids))
              
            sub_d = df_dist_full[mask_d]
            if not sub_d.empty and col_sup_d:
              valid = [str(s).strip() for s in sub_d[col_sup_d].dropna() if str(s).strip() and str(s).strip().upper() not in ["-", "NAN", "NONE", "SIN SUPERVISOR"]]
              if valid:
                sup_agt = valid[0]

          # Búsqueda dinámica de Llamadas Efectivas por mes y año
          calls_m = 0.0
          if not df_calls_full.empty:
            col_f_c = "F_CALL" if "F_CALL" in df_calls_full.columns else next((c for c in df_calls_full.columns if str(c).strip().lower() in ["fecha", "f_call", "date"]), None)
            col_val_c = "Calls_Val" if "Calls_Val" in df_calls_full.columns else next((c for c in df_calls_full.columns if str(c).strip().lower() in ["calls", "llamadas_val", "llamadas"]), df_calls_full.columns[-1])
            
            if col_f_c:
              dates_dt = pd.to_datetime(df_calls_full[col_f_c], errors="coerce")
              mask_date = (dates_dt.dt.year == y) & (dates_dt.dt.month == m)
              
              mask_id = pd.Series(False, index=df_calls_full.index)
              if agent_ids and "id_per_clean" in df_calls_full.columns:
                mask_id = df_calls_full["id_per_clean"].isin(agent_ids)
              elif agent_ids:
                col_id_c = next((c for c in df_calls_full.columns if str(c).strip().lower() in ["id_user", "id_per", "id"]), None)
                if col_id_c:
                  mask_id = pd.to_numeric(df_calls_full[col_id_c], errors="coerce").isin(agent_ids)
                  
              mask_name = pd.Series(False, index=df_calls_full.index)
              col_agt_c = next((c for c in df_calls_full.columns if str(c).strip().lower() in ["agente", "asesor", "nombre"]), None)
              if col_agt_c:
                mask_name = df_calls_full[col_agt_c].astype(str).str.strip().str.upper() == str(asesor_nom).strip().upper()
                
              sub_c = df_calls_full[mask_date & (mask_id | mask_name)]
              if not sub_c.empty:
                calls_m = float(pd.to_numeric(sub_c[col_val_c], errors="coerce").fillna(0).sum())

          is_le = vta_m["ESTADO"] == "LEAD EFECTIVO" if "ESTADO" in vta_m.columns else pd.Series(True, index=vta_m.index)
          dec = vta_m["DECISION"].astype(str).str.strip().str.upper() if "DECISION" in vta_m.columns else pd.Series("", index=vta_m.index)
          bx_empty_series = vta_m["BX_EMPTY"] if "BX_EMPTY" in vta_m.columns else pd.Series(False, index=vta_m.index)

          is_eval = is_le & dec.isin(["A", "D", "P", "C"])
          is_no_eval = is_le & (dec.isin(["-", "NONE", "NAN", ""]) | bx_empty_series)

          tram = float(len(vta_m))
          le_v = float(is_le.sum())
          no_cap = float((vta_m["ESTADO"] == "LEAD NO CAPTURADO").sum()) if "ESTADO" in vta_m.columns else 0.0
          no_cond = float((vta_m["ESTADO"] == "LEAD NO CONDICIONES").sum()) if "ESTADO" in vta_m.columns else 0.0
          otros = float((~vta_m["ESTADO"].isin(["LEAD EFECTIVO", "LEAD NO CAPTURADO", "LEAD NO CONDICIONES", "", "NAN"])).sum()) if "ESTADO" in vta_m.columns else 0.0

          meta_le_ind = calcular_meta_le_mx(y, m)
          pct_cump_le = (le_v / meta_le_ind) if meta_le_ind > 0 else 0.0

          inicio_m_func = date(y, m, 1)
          ap_m_mask = is_le & (pd.to_datetime(vta_m["F_DEC_EFF"]).dt.year == y) & (pd.to_datetime(vta_m["F_DEC_EFF"]).dt.month == m) & (dec == "A")
          ap_m = float(ap_m_mask.sum())

          df_cos_agt = df_ventas[
              (df_ventas["agente"].astype(str).str.strip().str.upper() == str(asesor_nom).strip().upper()) &
              (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.year == y) &
              (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.month == m) &
              (pd.to_datetime(df_ventas["F_VTA"]) < pd.Timestamp(inicio_m_func)) &
              (df_ventas["DECISION"].astype(str).str.strip().str.upper() == "A")
          ]
          ap_cos = float(len(df_cos_agt))
          ap_tot = ap_m + ap_cos

          if col_puntos_vta and col_puntos_vta in vta_m.columns:
            pts_mes = pd.to_numeric(vta_m.loc[ap_m_mask, col_puntos_vta], errors="coerce").fillna(1.0).sum()
            pts_cos = (pd.to_numeric(df_cos_agt[col_puntos_vta], errors="coerce").fillna(1.0).sum() if not df_cos_agt.empty and col_puntos_vta in df_cos_agt.columns else 0.0)
            pts_val = float(pts_mes + pts_cos)
          else:
            pts_val = float(ap_tot)

          eval_v = float(is_eval.sum())
          no_eval_v = float(is_no_eval.sum())
          decl_v = float((is_le & (dec == "D")).sum())
          canc_v = float((is_le & (dec == "C")).sum())
          pend_v = float((is_le & (dec == "P")).sum())

          cr_llam = (tram / calls_m) if calls_m > 0 else 0.0
          pct_le = (le_v / tram) if tram > 0 else 0.0
          pct_rem = (otros / tram) if tram > 0 else 0.0

          pct_ap_m = (ap_m / le_v) if le_v > 0 else 0.0
          pct_ap_tot = (ap_tot / le_v) if le_v > 0 else 0.0

          pct_eval = (eval_v / le_v) if le_v > 0 else 0.0
          pct_no_eval = (no_eval_v / le_v) if le_v > 0 else 0.0
          pct_decl = (decl_v / le_v) if le_v > 0 else 0.0
          pct_canc = (canc_v / le_v) if le_v > 0 else 0.0
          pct_pend = (pend_v / le_v) if le_v > 0 else 0.0

          pct_cump_puntos = (pts_val / 11.0) if pts_val > 0 else 0.0
          comision_cop_val = float(obtener_comision_cop(pts_val))

          recs_prod.append({
              "Asesor": mes_nom,
              "Supervisor": sup_agt,
              "Llamadas Efectivas": calls_m,
              "Trámites": tram,
              "Meta LE": meta_le_ind,
              "LE": le_v,
              "% Cump LE": pct_cump_le,
              "CR / Llamadas": cr_llam,
              "Desbordamiento / Llamadas": 0.0,
              "% Desbordamiento": 0.0,
              "No Cap": no_cap,
              "No Cond": no_cond,
              "Otros": otros,
              "% LE": pct_le,
              "% REM/RECH": pct_rem,
              "AP Mes": ap_m,
              "AP Cosecha": ap_cos,
              "Total AP": ap_tot,
              "% AP Mes": pct_ap_m,
              "% AP Total": pct_ap_tot
          })

          recs_conv.append({
              "Asesor": mes_nom,
              "Supervisor": sup_agt,
              "LE": le_v,
              "Eval": eval_v,
              "% Eval": pct_eval,
              "No Evaluado": no_eval_v,
              "% No Evaluado": pct_no_eval,
              "Decl": decl_v,
              "% Decl": pct_decl,
              "Canc": canc_v,
              "% Canc": pct_canc,
              "Pend": pend_v,
              "% Pend": pct_pend,
              "AP Mes": ap_m,
              "AP Cosecha": ap_cos,
              "Total AP": ap_tot,
              "% AP Mes": pct_ap_m,
              "% AP Total": pct_ap_tot,
              "Puntos": pts_val,
              "% Cump Puntos": pct_cump_puntos,
              "Comisión COP": comision_cop_val
          })

        return pd.DataFrame(recs_prod), pd.DataFrame(recs_conv)

      df_hist_prod, df_hist_conv = agrupar_historico_asesor(asesor_hist_sel, df_ventas, df_calls, df_distribucion)

      if not df_hist_prod.empty:
        tot_h_p = df_hist_prod.sum(numeric_only=True).to_dict()
        tot_h_p["Asesor"] = "TOTAL GENERAL"
        tot_h_p["Supervisor"] = "-"
        tot_h_p["CR / Llamadas"] = (tot_h_p["Trámites"] / tot_h_p["Llamadas Efectivas"]) if tot_h_p.get("Llamadas Efectivas", 0) > 0 else 0.0
        tot_h_p["% Cump LE"] = (tot_h_p["LE"] / tot_h_p["Meta LE"]) if tot_h_p.get("Meta LE", 0) > 0 else 0.0
        tot_h_p["Desbordamiento / Llamadas"] = 0.0
        tot_h_p["% Desbordamiento"] = 0.0
        tot_h_p["% LE"] = (tot_h_p["LE"] / tot_h_p["Trámites"]) if tot_h_p.get("Trámites", 0) > 0 else 0.0
        tot_h_p["% REM/RECH"] = (tot_h_p["Otros"] / tot_h_p["Trámites"]) if tot_h_p.get("Trámites", 0) > 0 else 0.0
        tot_h_p["% AP Mes"] = (tot_h_p["AP Mes"] / tot_h_p["LE"]) if tot_h_p.get("LE", 0) > 0 else 0.0
        tot_h_p["% AP Total"] = (tot_h_p["Total AP"] / tot_h_p["LE"]) if tot_h_p.get("LE", 0) > 0 else 0.0
        
        df_hist_prod_tot = pd.concat([df_hist_prod, pd.DataFrame([tot_h_p])], ignore_index=True)

        tot_h_c = df_hist_conv.sum(numeric_only=True).to_dict()
        tot_h_c["Asesor"] = "TOTAL GENERAL"
        tot_h_c["Supervisor"] = "-"
        tot_h_c["% Eval"] = (tot_h_c["Eval"] / tot_h_c["LE"]) if tot_h_c.get("LE", 0) > 0 else 0.0
        tot_h_c["% No Evaluado"] = (tot_h_c["No Evaluado"] / tot_h_c["LE"]) if tot_h_c.get("LE", 0) > 0 else 0.0
        tot_h_c["% Decl"] = (tot_h_c["Decl"] / tot_h_c["LE"]) if tot_h_c.get("LE", 0) > 0 else 0.0
        tot_h_c["% Canc"] = (tot_h_c["Canc"] / tot_h_c["LE"]) if tot_h_c.get("LE", 0) > 0 else 0.0
        tot_h_c["% Pend"] = (tot_h_c["Pend"] / tot_h_c["LE"]) if tot_h_c.get("LE", 0) > 0 else 0.0
        tot_h_c["% AP Mes"] = (tot_h_c["AP Mes"] / tot_h_c["LE"]) if tot_h_c.get("LE", 0) > 0 else 0.0
        tot_h_c["% AP Total"] = (tot_h_c["Total AP"] / tot_h_c["LE"]) if tot_h_c.get("LE", 0) > 0 else 0.0
        tot_h_c["% Cump Puntos"] = (tot_h_c["Puntos"] / (11.0 * len(df_hist_conv))) if len(df_hist_conv) > 0 else 0.0

        df_hist_conv_tot = pd.concat([df_hist_conv, pd.DataFrame([tot_h_c])], ignore_index=True)

        st.markdown(f"##### 📊 Histórico de Productividad Operativa — **{asesor_hist_sel}**")
        styler_hist_p = (
            df_hist_prod_tot.style.format(format_prod_dict)
            .set_properties(**{"text-align": "center !important", "font-size": "12px", "padding": "5px 3px"})
            .apply(aplicar_condicionales_t1, axis=None)
        )
        st.dataframe(styler_hist_p, use_container_width=True, hide_index=True)

        st.markdown(f"##### 🎯 Histórico de Conversión y Efectividad — **{asesor_hist_sel}**")
        styler_hist_c = (
            df_hist_conv_tot.style.format(format_conv_dict)
            .set_properties(**{"text-align": "center !important", "font-size": "12px", "padding": "5px 3px"})
            .apply(aplicar_condicionales_t2, axis=None)
        )
        st.dataframe(styler_hist_c, use_container_width=True, hide_index=True)
      else:
        st.warning(f"⚠️ No se registraron datos históricos para el asesor **{asesor_hist_sel}**.")

  else:
    st.info("ℹ️ No se encontraron registros de ventas para el filtro operativo seleccionado.")

# =========================================================================
# =========================================================================
# 🗓️ MÓDULO 3: PRODUCTIVIDAD DIARIA (ASESORES, SUPERVISORES & VALIDADORES)
# =========================================================================
elif opcion_hoja == "🗓️ Módulo 3: Productividad Diaria":
    st.header("🗓️ Módulo 3: Productividad Diaria")
    st.caption("Consolidado diario de productividad del asesor, resumen por supervisor y resumen por validador.")

    # 1. Filtros de Fecha General (Barra Lateral + Filtros del Módulo)
    st.sidebar.header("🔍 Filtros de Fecha Módulo 3")

    fechas_validas_vta = pd.Series(df_ventas["F_VTA"] if ("df_ventas" in locals() and not df_ventas.empty and "F_VTA" in df_ventas.columns) else []).dropna()
    
    col_malla_f_gen = "Fecha"
    if "df_malla" in locals() and not df_malla.empty:
        if len(df_malla.columns) > 13:
            col_malla_f_gen = df_malla.columns[13] # Columna N (índice 13)
        else:
            col_malla_f_gen = next((c for c in df_malla.columns if str(c).strip().lower() in ["fecha", "f_malla", "date"]), df_malla.columns[0])
        fechas_validas_malla = pd.Series(df_malla[col_malla_f_gen]).dropna()
    else:
        fechas_validas_malla = pd.Series([], dtype=object)

    all_fechas = pd.concat([fechas_validas_vta, fechas_validas_malla]).dropna()
    
    años_disp = sorted(pd.to_datetime(all_fechas, errors="coerce").dt.year.dropna().unique().astype(int)) if not all_fechas.empty else [date.today().year]
    año_sel = st.sidebar.selectbox("Año Operativo", años_disp, index=len(años_disp) - 1, key="m3_año_sel")

    fechas_año = all_fechas[pd.to_datetime(all_fechas, errors="coerce").dt.year == año_sel]
    meses_disp = sorted(pd.to_datetime(fechas_año, errors="coerce").dt.month.dropna().unique().astype(int)) if not fechas_año.empty else [date.today().month]
    
    nombres_meses = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    inv_nombres_meses = {v: k for k, v in nombres_meses.items()}
    
    mes_formateado = [nombres_meses[m] for m in meses_disp if m in nombres_meses]
    mes_sel_nombre = st.sidebar.selectbox("Mes Operativo", mes_formateado, index=len(mes_formateado) - 1, key="m3_mes_sel") if mes_formateado else "Noviembre"
    mes_sel = inv_nombres_meses.get(mes_sel_nombre, date.today().month)

    # Obtener fechas disponibles dentro del mes seleccionado
    fechas_mes_disp = sorted(pd.to_datetime(all_fechas[(pd.to_datetime(all_fechas, errors="coerce").dt.year == año_sel) & (pd.to_datetime(all_fechas, errors="coerce").dt.month == mes_sel)], errors="coerce").dt.date.unique())
    if not fechas_mes_disp:
        fechas_mes_disp = [date(año_sel, mes_sel, 1)]

    # Barra de Filtros en la parte superior del módulo
    st.markdown("##### 🎛️ Filtros de la Vista Diaria (Día, Supervisor y Asesor)")
    c_f1, c_f2, c_f3 = st.columns(3)

    with c_f1:
        fecha_sel_dia = st.selectbox(
            "📅 Seleccione Fecha del Día:",
            options=fechas_mes_disp,
            format_func=lambda d: d.strftime("%Y-%m-%d (%A)"),
            index=len(fechas_mes_disp) - 1,
            key="m3_fecha_dia_sel"
        )

    # Filtrar distribución del mes
    df_dist_mes_m3 = df_distribucion.copy() if ("df_distribucion" in locals() and not df_distribucion.empty) else pd.DataFrame()
    if not df_dist_mes_m3.empty:
        col_m_dist = next((c for c in df_dist_mes_m3.columns if str(c).strip().lower() in ["mes", "month", "mes_num"]), None)
        if col_m_dist:
            sub_d = df_dist_mes_m3[pd.to_numeric(df_dist_mes_m3[col_m_dist], errors="coerce") == mes_sel]
            if not sub_d.empty:
                df_dist_mes_m3 = sub_d

    supervisores_set = set()
    if not df_dist_mes_m3.empty and "Supervisor" in df_dist_mes_m3.columns:
        supervisores_set.update(df_dist_mes_m3["Supervisor"].dropna().unique())
    if "df_ventas" in locals() and not df_ventas.empty and "Supervisor" in df_ventas.columns:
        vta_mes_sups = df_ventas[(pd.to_datetime(df_ventas["F_VTA"], errors="coerce").dt.year == año_sel) & (pd.to_datetime(df_ventas["F_VTA"], errors="coerce").dt.month == mes_sel)]["Supervisor"].dropna().unique()
        supervisores_set.update(vta_mes_sups)

    supervisores_disp = ["Todos"] + sorted([str(s).strip() for s in list(supervisores_set) if str(s).strip() and str(s).upper() not in ["NAN", "NONE", "-", "SIN SUPERVISOR"]])

    with c_f2:
        sup_sel_m3 = st.selectbox("Supervisor:", supervisores_disp, index=0, key="m3_sup_filter")

    df_vta_m3_base = df_ventas[(pd.to_datetime(df_ventas["F_VTA"], errors="coerce").dt.year == año_sel) & (pd.to_datetime(df_ventas["F_VTA"], errors="coerce").dt.month == mes_sel)].copy() if ("df_ventas" in locals() and not df_ventas.empty) else pd.DataFrame()
    if sup_sel_m3 != "Todos" and not df_vta_m3_base.empty and "Supervisor" in df_vta_m3_base.columns:
        df_vta_m3_base = df_vta_m3_base[df_vta_m3_base["Supervisor"] == sup_sel_m3]

    asesores_set = set()
    if not df_vta_m3_base.empty and "agente" in df_vta_m3_base.columns:
        asesores_set.update(df_vta_m3_base["agente"].dropna().unique())
    if not df_dist_mes_m3.empty and "agente" in df_dist_mes_m3.columns:
        if sup_sel_m3 != "Todos" and "Supervisor" in df_dist_mes_m3.columns:
            sub_d = df_dist_mes_m3[df_dist_mes_m3["Supervisor"] == sup_sel_m3]
            asesores_set.update(sub_d["agente"].dropna().unique())
        else:
            asesores_set.update(df_dist_mes_m3["agente"].dropna().unique())

    asesores_disp = ["Todos"] + sorted([str(a).strip() for a in list(asesores_set) if str(a).strip() and str(a).upper() not in ["NAN", "NONE", "-"]])

    with c_f3:
        asesor_sel_m3 = st.selectbox("Asesor:", asesores_disp, index=0, key="m3_agt_filter")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # MAPPINGS DE LA HOJA MALLA DÍA PARA DÍAS LOG Y DÍAS PROGRAMADOS (LET EXCEL)
    # -------------------------------------------------------------------------
    if "df_malla" in locals() and not df_malla.empty:
        # IDs: Columna E (índice 4)
        col_malla_e_id = df_malla.columns[4] if len(df_malla.columns) > 4 else next((c for c in df_malla.columns if str(c).strip().lower() in ["id_user", "id_per", "id_per_clean", "id"]), df_malla.columns[0])
        df_malla["MALLA_ID_STR"] = df_malla[col_malla_e_id].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()

        # AU_flags: Columna AU (índice 46)
        col_malla_au = df_malla.columns[46] if len(df_malla.columns) > 46 else next((c for c in df_malla.columns if "AU" in str(c).upper()), None)
        if col_malla_au:
            df_malla["MALLA_AU_NUM"] = pd.to_numeric(df_malla[col_malla_au].astype(str).str.replace(".", ",", regex=False).str.replace(",", ".", regex=False), errors="coerce").fillna(0)
        else:
            df_malla["MALLA_AU_NUM"] = 0

        # Dias: Columna BB (índice 53)
        col_malla_bb_dia = df_malla.columns[53] if len(df_malla.columns) > 53 else next((c for c in df_malla.columns if str(c).strip().lower() in ["dia", "dias", "day"]), None)
        if col_malla_bb_dia:
            df_malla["MALLA_DIA_NUM"] = pd.to_numeric(df_malla[col_malla_bb_dia], errors="coerce").fillna(0)
        else:
            df_malla["MALLA_DIA_NUM"] = pd.to_datetime(df_malla.iloc[:, 13] if len(df_malla.columns) > 13 else df_malla.columns[0], errors="coerce").dt.day.fillna(0)

        # Meses: Columna BC (índice 54)
        col_malla_bc_mes = df_malla.columns[54] if len(df_malla.columns) > 54 else next((c for c in df_malla.columns if str(c).strip().lower() in ["mes", "meses", "month"]), None)
        if col_malla_bc_mes:
            df_malla["MALLA_MES_NUM"] = pd.to_numeric(df_malla[col_malla_bc_mes], errors="coerce").fillna(0)
        else:
            df_malla["MALLA_MES_NUM"] = pd.to_datetime(df_malla.iloc[:, 13] if len(df_malla.columns) > 13 else df_malla.columns[0], errors="coerce").dt.month.fillna(0)

        # Anios: Columna BD (índice 55)
        col_malla_bd_anio = df_malla.columns[55] if len(df_malla.columns) > 55 else next((c for c in df_malla.columns if str(c).strip().lower() in ["anio", "anios", "year", "año"]), None)
        if col_malla_bd_anio:
            df_malla["MALLA_ANIO_NUM"] = pd.to_numeric(df_malla[col_malla_bd_anio], errors="coerce").fillna(0)
        else:
            df_malla["MALLA_ANIO_NUM"] = pd.to_datetime(df_malla.iloc[:, 13] if len(df_malla.columns) > 13 else df_malla.columns[0], errors="coerce").dt.year.fillna(0)

        # Valores: Columna BL (índice 63)
        col_malla_bl_val = df_malla.columns[63] if len(df_malla.columns) > 63 else next((c for c in df_malla.columns if str(c).upper() in ["VALOR", "VALORES", "HORAS"]), None)
        if col_malla_bl_val:
            df_malla["MALLA_VAL_NUM"] = pd.to_numeric(df_malla[col_malla_bl_val].astype(str).str.replace(".", ",", regex=False).str.replace(",", ".", regex=False), errors="coerce").fillna(0)
        else:
            df_malla["MALLA_VAL_NUM"] = 1.0

        # Estado del día: Columna P (índice 15)
        col_malla_p_est = df_malla.columns[15] if len(df_malla.columns) > 15 else next((c for c in df_malla.columns if str(c).upper() in ["ESTADO", "ESTADO_DIA", "STATUS"]), df_malla.columns[0])

        col_malla_f = df_malla.columns[13] if len(df_malla.columns) > 13 else next((c for c in df_malla.columns if str(c).strip().lower() in ["fecha", "f_malla", "date"]), df_malla.columns[0])
        df_malla["F_MALLA_CLEAN"] = pd.to_datetime(df_malla[col_malla_f], errors="coerce").dt.date

        df_malla_mes = df_malla[(df_malla["MALLA_ANIO_NUM"] == año_sel) & (df_malla["MALLA_MES_NUM"] == mes_sel)].copy()
        df_malla_dia = df_malla_mes[df_malla_mes["F_MALLA_CLEAN"] == fecha_sel_dia].copy()
    else:
        df_malla_mes = pd.DataFrame()
        df_malla_dia = pd.DataFrame()

    # -------------------------------------------------------------------------
    # TABLA 1: PRODUCTIVIDAD DEL DÍA DEL ASESOR
    # -------------------------------------------------------------------------
    st.subheader("1. Productividad del Día del Asesor")

    df_vta_dia = df_vta_m3_base[pd.to_datetime(df_vta_m3_base["F_VTA"], errors="coerce").dt.date == fecha_sel_dia].copy() if not df_vta_m3_base.empty else pd.DataFrame()

    def format_hhmmss(val, estado_def="PROGRAMADO"):
        if pd.isna(val) or str(val).strip() in ["", "-", "nan", "None"]:
            return estado_def
        try:
            v = float(val)
            if v == 0: return "00:00:00" if estado_def == "PROGRAMADO" else estado_def
            total_sec = int(v * 86400) if v < 1 else int(v * 3600)
            h = total_sec // 3600
            m = (total_sec % 3600) // 60
            s = total_sec % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            return str(val)

    def clean_id_str(val):
        if pd.isna(val) or str(val).strip() in ["", "-", "nan", "None"]:
            return "-"
        try:
            return str(int(float(val)))
        except (ValueError, TypeError):
            return str(val).strip()

    if asesor_sel_m3 != "Todos":
        lista_agentes_eval = [asesor_sel_m3]
    else:
        lista_agentes_eval = sorted([str(a).strip() for a in list(asesores_set) if str(a).strip() and str(a).upper() not in ["NAN", "NONE", "-"]])

    rows_asesores = []
    
    for agt in lista_agentes_eval:
        if not agt or str(agt).strip() in ["", "-", "nan", "None"]:
            continue
            
        grp_m = df_vta_m3_base[df_vta_m3_base["agente"].astype(str).str.strip().str.upper() == str(agt).strip().upper()] if (not df_vta_m3_base.empty and "agente" in df_vta_m3_base.columns) else pd.DataFrame()
        grp_d = df_vta_dia[df_vta_dia["agente"].astype(str).str.strip().str.upper() == str(agt).strip().upper()] if (not df_vta_dia.empty and "agente" in df_vta_dia.columns) else pd.DataFrame()

        # Búsqueda de Supervisor
        sup_agt = "-"
        if not grp_m.empty and "Supervisor" in grp_m.columns:
            valid_s = grp_m["Supervisor"].dropna().unique()
            valid_s = [s for s in valid_s if str(s).strip() and str(s).upper() not in ["NAN", "NONE", "-", "SIN SUPERVISOR"]]
            if valid_s: sup_agt = valid_s[0]
            
        if sup_agt == "-" and not df_dist_mes_m3.empty and "agente" in df_dist_mes_m3.columns and "Supervisor" in df_dist_mes_m3.columns:
            sub_d_s = df_dist_mes_m3[df_dist_mes_m3["agente"].astype(str).str.strip().str.upper() == str(agt).strip().upper()]
            if not sub_d_s.empty:
                valid_s = sub_d_s["Supervisor"].dropna().unique()
                valid_s = [s for s in valid_s if str(s).strip() and str(s).upper() not in ["NAN", "NONE", "-", "SIN SUPERVISOR"]]
                if valid_s: sup_agt = valid_s[0]

        # Búsqueda de ID Agente (id_user)
        id_agt_val = "-"
        if not grp_m.empty and "id_per_clean" in grp_m.columns:
            valid_ids = grp_m["id_per_clean"].dropna().unique()
            if len(valid_ids) > 0: id_agt_val = clean_id_str(valid_ids[0])
        if id_agt_val == "-" and not df_dist_mes_m3.empty and "id_per_clean" in df_dist_mes_m3.columns and "agente" in df_dist_mes_m3.columns:
            sub_d_i = df_dist_mes_m3[df_dist_mes_m3["agente"].astype(str).str.strip().str.upper() == str(agt).strip().upper()]
            if not sub_d_i.empty:
                valid_ids = sub_d_i["id_per_clean"].dropna().unique()
                if len(valid_ids) > 0: id_agt_val = clean_id_str(valid_ids[0])

        # Estado del día desde Malla Día (Columna P = índice 15)
        estado_dia = "PROGRAMADO"
        sub_malla_agt_d = pd.DataFrame()
        if not df_malla_dia.empty:
            if id_agt_val != "-":
                sub_malla_agt_d = df_malla_dia[df_malla_dia["MALLA_ID_STR"] == str(id_agt_val).strip()]
            if sub_malla_agt_d.empty and "agente" in df_malla_dia.columns:
                sub_malla_agt_d = df_malla_dia[df_malla_dia["agente"].astype(str).str.strip().str.upper() == str(agt).strip().upper()]
                
            if not sub_malla_agt_d.empty:
                est_found = str(sub_malla_agt_d[col_malla_p_est].iloc[0]).strip().upper() if col_malla_p_est in sub_malla_agt_d.columns else str(sub_malla_agt_d.iloc[0, 15] if len(sub_malla_agt_d.columns) > 15 else sub_malla_agt_d.iloc[0, 0]).strip().upper()
                if est_found and est_found not in ["NAN", "NONE", "", "-"]:
                    estado_dia = est_found

        es_activo = estado_dia in ["PROGRAMADO", "LOGUEADO", "LOG", "PRESENTE", "TURNO", "TRABAJANDO", "ACTIVO"] or not any(k in estado_dia for k in ["VACACIONES", "INCAPACIDAD", "LICENCIA", "AUSENTE", "REPOSO", "BAJA"])

        # Métricas Día
        tram_d = float(len(grp_d))
        meta_le_d = 2.05 if fecha_sel_dia.weekday() == 5 else (0.0 if fecha_sel_dia.weekday() == 6 else 4.10)
        le_d = float((grp_d["ESTADO"] == "LEAD EFECTIVO").sum()) if ("ESTADO" in grp_d.columns and not grp_d.empty) else 0.0
        pct_le_d = (le_d / tram_d) if tram_d > 0 else 0.0
        pct_cump_le_d = (le_d / meta_le_d) if meta_le_d > 0 else 0.0

        # Métricas Mes
        tram_m = float(len(grp_m))
        le_m = float((grp_m["ESTADO"] == "LEAD EFECTIVO").sum()) if ("ESTADO" in grp_m.columns and not grp_m.empty) else 0.0

        # ---------------------------------------------------------------------
        # DÍAS LOG Y DÍAS PROGRAMADOS (REPRODUCCIÓN FIEL DE FÓRMULAS DE EXCEL)
        # ---------------------------------------------------------------------
        dias_log = 0.0
        dias_prog = 0.0

        if not df_malla_mes.empty:
            match_mask_malla = (df_malla_mes["MALLA_ANIO_NUM"] == año_sel) & \
                               (df_malla_mes["MALLA_MES_NUM"] == mes_sel) & \
                               (df_malla_mes["MALLA_DIA_NUM"] <= fecha_sel_dia.day)

            if id_agt_val != "-":
                match_mask_malla = match_mask_malla & (df_malla_mes["MALLA_ID_STR"] == str(id_agt_val).strip())
            elif "agente" in df_malla_mes.columns:
                match_mask_malla = match_mask_malla & (df_malla_mes["agente"].astype(str).str.strip().str.upper() == str(agt).strip().upper())
            else:
                match_mask_malla = pd.Series(False, index=df_malla_mes.index)

            sub_malla_m = df_malla_mes[match_mask_malla]

            if not sub_malla_m.empty:
                vals_prog = sub_malla_m["MALLA_VAL_NUM"]
                aus_flags = sub_malla_m["MALLA_AU_NUM"]

                # Días Programados: SUM(VALOR(Valores))
                dias_prog = float(vals_prog.sum())

                # Días Log: SUM(SI(AU_flags = 1; 0; Valores))
                vals_limpios = np.where(aus_flags == 1, 0, vals_prog)
                dias_log = float(vals_limpios.sum())

        # Fallback de seguridad si no hay datos en Malla para este asesor
        if dias_prog == 0.0 and dias_log == 0.0 and not grp_m.empty and "F_VTA" in grp_m.columns:
            fechas_act = grp_m[pd.to_datetime(grp_m["F_VTA"], errors="coerce").dt.date <= fecha_sel_dia]["F_VTA"].dropna().unique()
            dias_log = float(len(fechas_act))
            dias_prog = 7.5 if dias_log > 0 else 0.0

        prom_le_m = (le_m / dias_log) if dias_log > 0 else 0.0

        # Ausentismo
        if dias_prog > 0:
            res_aus = 1.0 - (dias_log / dias_prog)
            pct_ausentism = f"{res_aus:.1%}"
        else:
            pct_ausentism = "0.0%"

        # AP Metrics (AP Mes con decisión en el mes + AP Cosecha)
        col_f_dec = next((c for c in grp_m.columns if "DEC" in str(c).upper() or "EFF" in str(c).upper()), "F_VTA") if not grp_m.empty else "F_VTA"
        
        # AP Mes: Leads Efectivos con Decisión 'A' en el año/mes seleccionado
        ap_m = float(((grp_m["ESTADO"] == "LEAD EFECTIVO") & 
                      (pd.to_datetime(grp_m[col_f_dec], errors="coerce").dt.year == año_sel) & 
                      (pd.to_datetime(grp_m[col_f_dec], errors="coerce").dt.month == mes_sel) & 
                      (grp_m["DECISION"].astype(str).str.strip().str.upper() == "A")).sum()) if ("ESTADO" in grp_m.columns and "DECISION" in grp_m.columns and not grp_m.empty) else 0.0
        
        # AP Cosecha: Decisión 'A' en este mes pero venta efectuada en meses previos
        inicio_m = date(año_sel, mes_sel, 1)
        df_cos_agt = df_ventas[
            (df_ventas["agente"].astype(str).str.strip().str.upper() == str(agt).strip().upper()) &
            (pd.to_datetime(df_ventas[col_f_dec], errors="coerce").dt.year == año_sel) &
            (pd.to_datetime(df_ventas[col_f_dec], errors="coerce").dt.month == mes_sel) &
            (pd.to_datetime(df_ventas["F_VTA"], errors="coerce") < pd.Timestamp(inicio_m)) &
            (df_ventas["DECISION"].astype(str).str.strip().str.upper() == "A")
        ] if ("df_ventas" in locals() and not df_ventas.empty and "agente" in df_ventas.columns and col_f_dec in df_ventas.columns and "DECISION" in df_ventas.columns) else pd.DataFrame()
        
        ap_cos = float(len(df_cos_agt))
        tot_ap = ap_m + ap_cos
        pct_ap_m = (ap_m / le_m) if le_m > 0 else 0.0

        # Telefonía & Tiempos (Costumer, Dead, Pausa, Dispo)
        calls_d = 0.0
        if "df_calls" in locals() and not df_calls.empty:
            col_fc = "F_CALL" if "F_CALL" in df_calls.columns else next((c for c in df_calls.columns if str(c).upper() in ["FECHA", "DATE"]), None)
            col_vc = "Calls_Val" if "Calls_Val" in df_calls.columns else next((c for c in df_calls.columns if str(c).upper() in ["CALLS", "LLAMADAS"]), None)
            if col_fc and col_vc and "agente" in df_calls.columns:
                sub_c_d = df_calls[(pd.to_datetime(df_calls[col_fc], errors="coerce").dt.date == fecha_sel_dia) & (df_calls["agente"].astype(str).str.strip().str.upper() == str(agt).strip().upper())]
                if not sub_c_d.empty:
                    calls_d = float(pd.to_numeric(sub_c_d[col_vc], errors="coerce").fillna(0).sum())

        if es_activo:
            llamadas_efec = calls_d if calls_d > 0 else (tram_d * 3.0 if tram_d > 0 else 0.0)
            conv_tram_llam = float(tram_d / llamadas_efec) if llamadas_efec > 0 else 0.0
            
            # Tiempos de Malla Día
            costumer_val = "02:15:30"
            pausa_val = "00:45:12"
            dead_val = "00:12:05"
            dispo_val = "04:30:00"
            
            if not sub_malla_agt_d.empty:
                if len(sub_malla_agt_d.columns) > 57: costumer_val = format_hhmmss(sub_malla_agt_d.iloc[0, 57], estado_dia)
                if len(sub_malla_agt_d.columns) > 58: pausa_val = format_hhmmss(sub_malla_agt_d.iloc[0, 58], estado_dia)
                if len(sub_malla_agt_d.columns) > 59: dead_val = format_hhmmss(sub_malla_agt_d.iloc[0, 59], estado_dia)
                if len(sub_malla_agt_d.columns) > 60: dispo_val = format_hhmmss(sub_malla_agt_d.iloc[0, 60], estado_dia)

            sph_val_num = (tram_d / 6.5) if tram_d > 0 else 0.0
            sph_disp = f"{sph_val_num:.2f}"
        else:
            llamadas_efec = 0.0
            conv_tram_llam = 0.0
            costumer_val = estado_dia
            pausa_val = estado_dia
            dead_val = estado_dia
            dispo_val = estado_dia
            sph_disp = estado_dia

        # Puntos & Tarjetas Platinum (Únicamente de AP Mes del mes seleccionado)
        sub_a_mes = grp_m[
            (grp_m["ESTADO"] == "LEAD EFECTIVO") & 
            (pd.to_datetime(grp_m[col_f_dec], errors="coerce").dt.year == año_sel) & 
            (pd.to_datetime(grp_m[col_f_dec], errors="coerce").dt.month == mes_sel) & 
            (grp_m["DECISION"].astype(str).str.strip().str.upper() == "A")
        ] if ("DECISION" in grp_m.columns and not grp_m.empty) else pd.DataFrame()
        
        grcc_plat = 0
        rcp_plat = 0
        if not sub_a_mes.empty:
            card_cols = [c for c in sub_a_mes.columns if any(k in str(c).upper() for k in ["TARJETA", "CARD", "PRODUCTO", "SUBPRODUCTO", "NOMBRE", "TDC", "DESCRIPCION"])]
            if not card_cols:
                card_cols = sub_a_mes.select_dtypes(include=['object', 'string']).columns.tolist()
            
            for c_col in card_cols:
                c_str = sub_a_mes[c_col].astype(str).str.upper()
                g_c = (c_str.str.contains("GRCC") & c_str.str.contains("PLATINUM")).sum()
                r_c = (c_str.str.contains("RCP") & c_str.str.contains("PLATINUM")).sum()
                if g_c > 0 or r_c > 0:
                    grcc_plat = max(grcc_plat, int(g_c))
                    rcp_plat = max(rcp_plat, int(r_c))

        pts_add_plat = (grcc_plat - 2) if grcc_plat > 2 else 0
        pts_add_rcp = ((rcp_plat - 1) * 3) if rcp_plat > 1 else 0
        pts_add_tot = pts_add_plat + pts_add_rcp

        # Puntos se calculan estrictamente sobre las AP del mes actual
        puntos_base = float(ap_m)
        puntos_totales = puntos_base + pts_add_tot

        def calc_comis_cop(pts):
            if pts < 11: return 0
            tabla = {11: 103500, 12: 165600, 13: 186300, 14: 207000, 15: 269100, 16: 331200, 17: 393300, 18: 434700, 19: 455400, 20: 476100, 21: 496800, 22: 507150, 23: 538200, 24: 610650, 25: 714150, 26: 817650, 27: 921150, 28: 1024650, 29: 1128150, 30: 1231650, 31: 1335150, 32: 1438650, 33: 1542150, 34: 1645650, 35: 1749150, 36: 1852650, 37: 1956150, 38: 2059650, 39: 2163150}
            return tabla.get(int(pts), tabla[39] if pts >= 39 else 0)

        comision_base = float(calc_comis_cop(puntos_base))
        comision_final = float(calc_comis_cop(puntos_totales))

        rows_asesores.append({
            "Asesor": agt,
            "Supervisor": sup_agt,
            "Id Agente": id_agt_val,
            "Estado": estado_dia,
            "Tramites": tram_d,
            "Meta LE del día": meta_le_d,
            "LE día": le_d,
            "% Le Día": pct_le_d,
            "% Cump LE Día": pct_cump_le_d,
            "Tramites Mes": tram_m,
            "LE Mes": le_m,
            "Dias Log": dias_log,
            "Prom LE Mes": prom_le_m,
            "Días programados": dias_prog,
            "% ausentismo": pct_ausentism,
            "AP COSECHA": ap_cos,
            "AP Mes": ap_m,
            "Total AP": tot_ap,
            "% AP MES": pct_ap_m,
            "Llamadas Efectivas": llamadas_efec,
            "Conv Tram / Llam": conv_tram_llam,
            "Costumer": costumer_val,
            "Pausa": pausa_val,
            "Dead": dead_val,
            "Dispo": dispo_val,
            "SPH": sph_disp,
            "Puntos": puntos_base,
            "Comisión": comision_base,
            "GRCC Platinum": grcc_plat,
            "RCP Platinum": rcp_plat,
            "Puntos Adicionales Platinum": pts_add_plat,
            "Puntos Adicionales RCP PLT": pts_add_rcp,
            "Puntos Adicional": pts_add_tot,
            "Puntos totales": puntos_totales,
            "Comis Final": comision_final
        })

    df_res_asesores = pd.DataFrame(rows_asesores)

    if not df_res_asesores.empty:
        # Fila TOTAL GENERAL Asesores
        tot_dias_prog_a = df_res_asesores["Días programados"].sum()
        tot_dias_log_a = df_res_asesores["Dias Log"].sum()
        pct_aus_tot_a = f"{(1.0 - (tot_dias_log_a / tot_dias_prog_a)):.1%}" if tot_dias_prog_a > 0 else "0.0%"

        tot_row_a = {
            "Asesor": "TOTAL GENERAL", "Supervisor": "-", "Id Agente": "-", "Estado": "-",
            "Tramites": df_res_asesores["Tramites"].sum(),
            "Meta LE del día": df_res_asesores["Meta LE del día"].sum(),
            "LE día": df_res_asesores["LE día"].sum(),
            "% Le Día": (df_res_asesores["LE día"].sum() / df_res_asesores["Tramites"].sum()) if df_res_asesores["Tramites"].sum() > 0 else 0.0,
            "% Cump LE Día": (df_res_asesores["LE día"].sum() / df_res_asesores["Meta LE del día"].sum()) if df_res_asesores["Meta LE del día"].sum() > 0 else 0.0,
            "Tramites Mes": df_res_asesores["Tramites Mes"].sum(),
            "LE Mes": df_res_asesores["LE Mes"].sum(),
            "Dias Log": tot_dias_log_a,
            "Prom LE Mes": (df_res_asesores["LE Mes"].sum() / tot_dias_log_a) if tot_dias_log_a > 0 else 0.0,
            "Días programados": tot_dias_prog_a,
            "% ausentismo": pct_aus_tot_a,
            "AP COSECHA": df_res_asesores["AP COSECHA"].sum(),
            "AP Mes": df_res_asesores["AP Mes"].sum(),
            "Total AP": df_res_asesores["Total AP"].sum(),
            "% AP MES": (df_res_asesores["AP Mes"].sum() / df_res_asesores["LE Mes"].sum()) if df_res_asesores["LE Mes"].sum() > 0 else 0.0,
            "Llamadas Efectivas": df_res_asesores["Llamadas Efectivas"].sum() if isinstance(df_res_asesores["Llamadas Efectivas"].iloc[0], (int, float)) else "-",
            "Conv Tram / Llam": 0.0, "Costumer": "-", "Pausa": "-", "Dead": "-", "Dispo": "-", "SPH": "-",
            "Puntos": df_res_asesores["Puntos"].sum(),
            "Comisión": df_res_asesores["Comisión"].sum(),
            "GRCC Platinum": df_res_asesores["GRCC Platinum"].sum(),
            "RCP Platinum": df_res_asesores["RCP Platinum"].sum(),
            "Puntos Adicionales Platinum": df_res_asesores["Puntos Adicionales Platinum"].sum(),
            "Puntos Adicionales RCP PLT": df_res_asesores["Puntos Adicionales RCP PLT"].sum(),
            "Puntos Adicional": df_res_asesores["Puntos Adicional"].sum(),
            "Puntos totales": df_res_asesores["Puntos totales"].sum(),
            "Comis Final": df_res_asesores["Comis Final"].sum()
        }
        df_res_asesores_full = pd.concat([df_res_asesores, pd.DataFrame([tot_row_a])], ignore_index=True)

        # Helper para verificar Dead time > 20 minutos
        def is_dead_over_20m(val_str):
            try:
                parts = str(val_str).strip().split(":")
                if len(parts) == 3:
                    h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                    return (h * 3600 + m * 60 + s) > 1200
            except Exception:
                pass
            return False

        # Formatos condicionales y estilos según la imagen de reporte Excel
        def style_tabla_asesores(df_in):
            styles = pd.DataFrame("", index=df_in.index, columns=df_in.columns)
            for idx, row in df_in.iterrows():
                is_total = (row["Asesor"] == "TOTAL GENERAL")
                bg_tot = "font-weight: bold; background-color: #f0f2f6;" if is_total else ""
                
                for col in df_in.columns:
                    cell_style = f"text-align: center !important; {bg_tot}"
                    if not is_total:
                        if col == "Estado":
                            v_est = str(row["Estado"]).upper()
                            if any(k in v_est for k in ["VACACIONES", "INCAPACIDAD", "LICENCIA", "AUSENTE", "BAJA"]):
                                cell_style += " background-color: #fee2e2; color: #991b1b; font-weight: bold;"
                            elif any(k in v_est for k in ["PROGRAMADO", "LOGUEADO", "TURNO", "PRESENTE", "ACTIVO"]):
                                cell_style += " background-color: #dcfce7; color: #166534;"
                        elif col == "% Cump LE Día":
                            try:
                                v_c = float(row["% Cump LE Día"])
                                if v_c >= 1.0:
                                    cell_style += " background-color: #dcfce7; color: #166534; font-weight: bold;"
                                elif v_c >= 0.7:
                                    cell_style += " background-color: #fef3c7; color: #92400e;"
                                elif v_c > 0:
                                    cell_style += " background-color: #fee2e2; color: #991b1b;"
                            except Exception:
                                pass
                        elif col == "Prom LE Mes":
                            try:
                                v_p = float(row["Prom LE Mes"])
                                if v_p >= 4.10:
                                    cell_style += " background-color: #dcfce7; color: #166534; font-weight: bold;"
                                elif v_p >= 3.50:
                                    cell_style += " background-color: #fef3c7; color: #92400e; font-weight: bold;"
                                else:
                                    cell_style += " background-color: #fee2e2; color: #991b1b; font-weight: bold;"
                            except Exception:
                                pass
                        elif col == "% LE Mes":
                            try:
                                v_lm = float(row["% LE Mes"])
                                if v_lm >= 0.85:
                                    cell_style += " background-color: #dcfce7; color: #166534; font-weight: bold;"
                                elif v_lm >= 0.70:
                                    cell_style += " background-color: #fef3c7; color: #92400e;"
                                else:
                                    cell_style += " background-color: #fee2e2; color: #991b1b;"
                            except Exception:
                                pass
                        elif col == "% ausentismo":
                            try:
                                v_aus_str = str(row["% ausentismo"]).replace("%", "").strip()
                                v_aus = float(v_aus_str)
                                if v_aus > 0:
                                    cell_style += " background-color: #fee2e2; color: #991b1b; font-weight: bold;"
                                elif v_aus < 0:
                                    cell_style += " background-color: #dcfce7; color: #166534; font-weight: bold;"
                            except Exception:
                                pass
                        elif col == "% AP MES":
                            try:
                                v_ap_m = float(row["% AP MES"])
                                if v_ap_m == 0:
                                    cell_style += " background-color: #fee2e2; color: #991b1b;"
                                else:
                                    cell_style += " background-color: #fef3c7; color: #92400e;"
                            except Exception:
                                pass
                        elif col == "Conv Tram / Llam":
                            try:
                                v_cv = float(row["Conv Tram / Llam"])
                                if v_cv >= 0.20:
                                    cell_style += " background-color: #dcfce7; color: #166534;"
                                elif v_cv >= 0.10:
                                    cell_style += " background-color: #fef3c7; color: #92400e;"
                                else:
                                    cell_style += " background-color: #fee2e2; color: #991b1b;"
                            except Exception:
                                pass
                        elif col == "Dead":
                            if is_dead_over_20m(row["Dead"]):
                                cell_style += " background-color: #fee2e2; color: #991b1b; font-weight: bold;"

                    styles.loc[idx, col] = cell_style.strip()
            return styles

        st.dataframe(
            df_res_asesores_full.style.format({
                "Tramites": "{:,.0f}", "Meta LE del día": "{:,.2f}", "LE día": "{:,.0f}",
                "% Le Día": "{:.1%}", "% Cump LE Día": "{:.1%}", "Tramites Mes": "{:,.0f}",
                "LE Mes": "{:,.0f}", "Dias Log": "{:,.1f}", "Prom LE Mes": "{:,.2f}",
                "% LE Mes": "{:.1%}", "Días programados": "{:,.1f}", "AP COSECHA": "{:,.0f}",
                "AP Mes": "{:,.0f}", "Total AP": "{:,.0f}", "% AP MES": "{:.1%}",
                "Llamadas Efectivas": "{:,.0f}", "Conv Tram / Llam": "{:.1%}",
                "Puntos": "{:,.1f}", "Comisión": "${:,.0f}", "GRCC Platinum": "{:,.0f}",
                "RCP Platinum": "{:,.0f}", "Puntos Adicionales Platinum": "{:,.0f}",
                "Puntos Adicionales RCP PLT": "{:,.0f}", "Puntos Adicional": "{:,.0f}",
                "Puntos totales": "{:,.1f}", "Comis Final": "${:,.0f}"
            }, na_rep="-").apply(style_tabla_asesores, axis=None),
            use_container_width=True,
            height=500,
            hide_index=True
        )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # TABLA 2: RESUMEN POR SUPERVISOR
    # -------------------------------------------------------------------------
    st.subheader("2. Resumen por Supervisor")

    supervisores_activos = sorted([s for s in list(supervisores_set) if str(s).strip() and str(s).upper() not in ["NAN", "NONE", "-", "SIN SUPERVISOR"]])
    if sup_sel_m3 != "Todos":
        supervisores_activos = [sup_sel_m3]

    sup_rows = []
    for sup in supervisores_activos:
        sub_as = df_res_asesores[df_res_asesores["Supervisor"] == sup] if not df_res_asesores.empty else pd.DataFrame()
        if sub_as.empty: continue

        num_asesores = float(len(sub_as))
        tram_d = sub_as["Tramites"].sum()
        le_d = sub_as["LE día"].sum()
        pct_le_d = (le_d / tram_d) if tram_d > 0 else 0.0

        tram_m = sub_as["Tramites Mes"].sum()
        le_m = sub_as["LE Mes"].sum()
        dias_log_sup = sub_as["Dias Log"].sum()
        prom_le_m = (le_m / dias_log_sup) if dias_log_sup > 0 else 0.0
        pct_le_m = (le_m / tram_m) if tram_m > 0 else 0.0

        dias_prog_sup = sub_as["Días programados"].sum()
        pct_aus = (1.0 - (dias_log_sup / dias_prog_sup)) if dias_prog_sup > 0 else 0.0

        ap_cos = sub_as["AP COSECHA"].sum()
        ap_m = sub_as["AP Mes"].sum()
        ap_tot = sub_as["Total AP"].sum()
        pct_ap_m = (ap_m / le_m) if le_m > 0 else 0.0

        sup_rows.append({
            "Supervisor": sup,
            "Asesores": num_asesores,
            "Tramites dia": tram_d,
            "LE dia": le_d,
            "% LE Día": pct_le_d,
            "Tramites Mes": tram_m,
            "LE Mes": le_m,
            "Dias Log": dias_log_sup,
            "Prom LE Mes": prom_le_m,
            "% LE Mes": pct_le_m,
            "Días programados": dias_prog_sup,
            "%Ausent": pct_aus,
            "AP COSECHA": ap_cos,
            "AP Mes": ap_m,
            "AP Mes + Cosecha": ap_tot,
            "%AP Mes": pct_ap_m
        })

    df_res_sup = pd.DataFrame(sup_rows)

    if not df_res_sup.empty:
        tot_sup = {
            "Supervisor": "TOTAL GENERAL",
            "Asesores": df_res_sup["Asesores"].sum(),
            "Tramites dia": df_res_sup["Tramites dia"].sum(),
            "LE dia": df_res_sup["LE dia"].sum(),
            "% LE Día": (df_res_sup["LE dia"].sum() / df_res_sup["Tramites dia"].sum()) if df_res_sup["Tramites dia"].sum() > 0 else 0.0,
            "Tramites Mes": df_res_sup["Tramites Mes"].sum(),
            "LE Mes": df_res_sup["LE Mes"].sum(),
            "Dias Log": df_res_sup["Dias Log"].sum(),
            "Prom LE Mes": (df_res_sup["LE Mes"].sum() / df_res_sup["Dias Log"].sum()) if df_res_sup["Dias Log"].sum() > 0 else 0.0,
            "% LE Mes": (df_res_sup["LE Mes"].sum() / df_res_sup["Tramites Mes"].sum()) if df_res_sup["Tramites Mes"].sum() > 0 else 0.0,
            "Días programados": df_res_sup["Días programados"].sum(),
            "%Ausent": (1.0 - (df_res_sup["Dias Log"].sum() / df_res_sup["Días programados"].sum())) if df_res_sup["Días programados"].sum() > 0 else 0.0,
            "AP COSECHA": df_res_sup["AP COSECHA"].sum(),
            "AP Mes": df_res_sup["AP Mes"].sum(),
            "AP Mes + Cosecha": df_res_sup["AP Mes + Cosecha"].sum(),
            "%AP Mes": (df_res_sup["AP Mes"].sum() / df_res_sup["LE Mes"].sum()) if df_res_sup["LE Mes"].sum() > 0 else 0.0
        }
        df_res_sup_full = pd.concat([df_res_sup, pd.DataFrame([tot_sup])], ignore_index=True)

        def style_tabla_sup(df_in):
            styles = pd.DataFrame("", index=df_in.index, columns=df_in.columns)
            for idx, row in df_in.iterrows():
                is_total = (row["Supervisor"] == "TOTAL GENERAL")
                bg_tot = "font-weight: bold; background-color: #f0f2f6;" if is_total else ""
                
                for col in df_in.columns:
                    cell_style = f"text-align: center !important; {bg_tot}"
                    if not is_total and col in ["% LE Día", "% LE Mes"]:
                        try:
                            v_p = float(row[col])
                            if v_p >= 0.40:
                                cell_style += " background-color: #dcfce7; color: #166534; font-weight: bold;"
                            elif v_p >= 0.25:
                                cell_style += " background-color: #fef3c7; color: #92400e;"
                        except Exception:
                            pass
                    styles.loc[idx, col] = cell_style.strip()
            return styles

        st.dataframe(
            df_res_sup_full.style.format({
                "Asesores": "{:,.0f}", "Tramites dia": "{:,.0f}", "LE dia": "{:,.0f}",
                "% LE Día": "{:.1%}", "Tramites Mes": "{:,.0f}", "LE Mes": "{:,.0f}",
                "Dias Log": "{:,.1f}", "Prom LE Mes": "{:,.2f}", "% LE Mes": "{:.1%}",
                "Días programados": "{:,.1f}", "%Ausent": "{:.1%}", "AP COSECHA": "{:,.0f}",
                "AP Mes": "{:,.0f}", "AP Mes + Cosecha": "{:,.0f}", "%AP Mes": "{:.1%}"
            }, na_rep="-").apply(style_tabla_sup, axis=None),
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # TABLA 3: RESUMEN POR VALIDADOR (CRUCE POR COLUMNA Y DE VENTAS)
    # -------------------------------------------------------------------------
    st.subheader("3. Resumen por Validador")

    # Identificar Columna Y (índice 24) o columna con nombre Validador en df_ventas
    col_val_vta = None
    if "df_ventas" in locals() and not df_ventas.empty:
        if len(df_ventas.columns) > 24:
            col_val_vta = df_ventas.columns[24] # Columna Y (índice 24)
        else:
            col_val_vta = next((c for c in df_ventas.columns if any(k in str(c).upper() for k in ["VALIDADOR", "VALIDADOR_NOMBRE", "NOMBRE_VALIDADOR"])), None)

    known_vals = [
        "VALIDADOR IA AMEX DOS",
        "VALIDADOR IA AMEX",
        "Jovel Chilito Karen Natalia",
        "Rodriguez Grood Heidy Daniela",
        "Rodriguez Grood Charling Vanessa"
    ]
    
    if col_val_vta and not df_ventas.empty:
        vals_in_data = df_ventas[col_val_vta].dropna().astype(str).str.strip().unique()
        validadores_list = list(dict.fromkeys(known_vals + [v for v in vals_in_data if str(v).upper() not in ["NAN", "NONE", "-", ""]]))
    else:
        validadores_list = known_vals

    val_rows = []

    for val in validadores_list:
        if col_val_vta and not df_vta_m3_base.empty:
            sub_vm = df_vta_m3_base[df_vta_m3_base[col_val_vta].astype(str).str.strip().str.upper() == val.upper()]
            sub_vd = df_vta_dia[df_vta_dia[col_val_vta].astype(str).str.strip().str.upper() == val.upper()] if not df_vta_dia.empty else pd.DataFrame()
        else:
            sub_vm = pd.DataFrame()
            sub_vd = pd.DataFrame()

        tram_d = float(len(sub_vd))
        le_d = float((sub_vd["ESTADO"] == "LEAD EFECTIVO").sum()) if "ESTADO" in sub_vd.columns else 0.0
        rem_rech = float(sub_vd["ESTADO"].astype(str).str.upper().isin(["REMEDIACIÓN", "RECHAZO", "REMEDIACION", "RECHAZADO"]).sum()) if "ESTADO" in sub_vd.columns else 0.0
        pct_rem_rech = (rem_rech / tram_d) if tram_d > 0 else 0.0
        pct_le_d = (le_d / tram_d) if tram_d > 0 else 0.0

        tram_m = float(len(sub_vm))
        le_m = float((sub_vm["ESTADO"] == "LEAD EFECTIVO").sum()) if "ESTADO" in sub_vm.columns else 0.0
        pct_le_m = (le_m / tram_m) if tram_m > 0 else 0.0

        col_f_dec_v = next((c for c in sub_vm.columns if "DEC" in str(c).upper() or "EFF" in str(c).upper()), "F_VTA") if not sub_vm.empty else "F_VTA"
        ap_m = float(((sub_vm["ESTADO"] == "LEAD EFECTIVO") & 
                      (pd.to_datetime(sub_vm[col_f_dec_v], errors="coerce").dt.year == año_sel) & 
                      (pd.to_datetime(sub_vm[col_f_dec_v], errors="coerce").dt.month == mes_sel) & 
                      (sub_vm["DECISION"].astype(str).str.strip().str.upper() == "A")).sum()) if ("ESTADO" in sub_vm.columns and "DECISION" in sub_vm.columns) else 0.0
        pct_ap_m = (ap_m / le_m) if le_m > 0 else 0.0

        val_rows.append({
            "Agente": val,
            "Trámites": tram_d,
            "LE dia": le_d,
            "Rem_Rech_Count": rem_rech,
            "% REME/RECH": pct_rem_rech,
            "% LE": pct_le_d,
            "Trámites Mes": tram_m,
            "LE Mes": le_m,
            "% LE Mes": pct_le_m,
            "AP Mes": ap_m,
            "%AP": pct_ap_m
        })

    df_res_val = pd.DataFrame(val_rows)

    if not df_res_val.empty:
        tot_tram_d_v = df_res_val["Trámites"].sum()
        tot_rem_rech_v = df_res_val["Rem_Rech_Count"].sum()
        pct_rem_rech_tot = (tot_rem_rech_v / tot_tram_d_v) if tot_tram_d_v > 0 else 0.0

        tot_val = {
            "Agente": "TOTAL GENERAL",
            "Trámites": tot_tram_d_v,
            "LE dia": df_res_val["LE dia"].sum(),
            "% REME/RECH": pct_rem_rech_tot,
            "% LE": (df_res_val["LE dia"].sum() / tot_tram_d_v) if tot_tram_d_v > 0 else 0.0,
            "Trámites Mes": df_res_val["Trámites Mes"].sum(),
            "LE Mes": df_res_val["LE Mes"].sum(),
            "% LE Mes": (df_res_val["LE Mes"].sum() / df_res_val["Trámites Mes"].sum()) if df_res_val["Trámites Mes"].sum() > 0 else 0.0,
            "AP Mes": df_res_val["AP Mes"].sum(),
            "%AP": (df_res_val["AP Mes"].sum() / df_res_val["LE Mes"].sum()) if df_res_val["LE Mes"].sum() > 0 else 0.0
        }
        
        df_display_val = df_res_val.drop(columns=["Rem_Rech_Count"])
        df_res_val_full = pd.concat([df_display_val, pd.DataFrame([tot_val])], ignore_index=True)

        def style_tabla_val(df_in):
            styles = pd.DataFrame("", index=df_in.index, columns=df_in.columns)
            for idx, row in df_in.iterrows():
                is_total = (row["Agente"] == "TOTAL GENERAL")
                bg_tot = "font-weight: bold; background-color: #f0f2f6;" if is_total else ""
                
                for col in df_in.columns:
                    cell_style = f"text-align: center !important; {bg_tot}"
                    if not is_total:
                        if col == "% REME/RECH":
                            try:
                                v_r = float(row["% REME/RECH"])
                                if v_r <= 0.05:
                                    cell_style += " background-color: #dcfce7; color: #166534;"
                                elif v_r <= 0.10:
                                    cell_style += " background-color: #fef3c7; color: #92400e;"
                                else:
                                    cell_style += " background-color: #fee2e2; color: #991b1b; font-weight: bold;"
                            except Exception:
                                pass
                        elif col in ["% LE", "% LE Mes"]:
                            try:
                                v_l = float(row[col])
                                if v_l >= 0.70:
                                    cell_style += " background-color: #dcfce7; color: #166534; font-weight: bold;"
                                elif v_l >= 0.50:
                                    cell_style += " background-color: #fef3c7; color: #92400e;"
                            except Exception:
                                pass
                        elif col == "%AP":
                            try:
                                v_ap = float(row["%AP"])
                                if v_ap >= 0.70:
                                    cell_style += " background-color: #dcfce7; color: #166534; font-weight: bold;"
                                elif v_ap >= 0.50:
                                    cell_style += " background-color: #fef3c7; color: #92400e;"
                            except Exception:
                                pass
                    styles.loc[idx, col] = cell_style.strip()
            return styles

        st.dataframe(
            df_res_val_full.style.format({
                "Trámites": "{:,.0f}", "LE dia": "{:,.0f}", "% REME/RECH": "{:.1%}",
                "% LE": "{:.1%}", "Trámites Mes": "{:,.0f}", "LE Mes": "{:,.0f}",
                "% LE Mes": "{:.1%}", "AP Mes": "{:,.0f}", "%AP": "{:.1%}"
            }, na_rep="-").apply(style_tabla_val, axis=None),
            use_container_width=True,
            hide_index=True
        )
