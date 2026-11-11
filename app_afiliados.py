import calendar
from datetime import date
import math
import re
import holidays
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="Informe Gerencial Amex", layout="wide")

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


# 1. Termómetro Tipo Pila Segmentada
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


# 2. Termómetro Tipo Gauge Semicírculo Compacto
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


# Interpolación en 2 puntos (Blanco a Verde)
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
    b = int(rgb_mid[2] + t * (rgb_high[2] - rgb_mid[2]))

  return f"background-color: rgb({r}, {g}, {b}); color: #0f172a;"


@st.cache_data
def cargar_pestanas():
  def load_pq(name):
    try:
      return pd.read_parquet(name)
    except:
      return pd.DataFrame()

  return (
      load_pq("ventas.parquet"),
      load_pq("planta.parquet"),
      load_pq("seg_ppto.parquet"),
      load_pq("malla_día.parquet"),
  )


df_ventas, df_planta, df_ppto, df_malla = cargar_pestanas()

if not df_ventas.empty and len(df_ventas.columns) > 45:
  st.sidebar.image(
      "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/American_Express_logo_%282018%29.svg/1200px-American_Express_logo_%282018%29.svg.png",
      width=150,
  )
  st.sidebar.header("🔍 Filtros")

  # PREPARACIÓN VENTAS
  df_ventas["F_VTA"] = pd.to_datetime(
      df_ventas.iloc[:, 4], errors="coerce"
  ).dt.date
  df_ventas["ESTADO"] = (
      df_ventas.iloc[:, 7].astype(str).str.strip().str.upper()
  )
  df_ventas["DECISION"] = (
      df_ventas.iloc[:, 45].astype(str).str.strip().str.upper()
  )

  if len(df_ventas.columns) > 49:
    df_ventas["F_DEC"] = pd.to_datetime(
        df_ventas.iloc[:, 49], errors="coerce"
    ).dt.date
  else:
    df_ventas["F_DEC"] = pd.NaT

  df_ventas["F_DEC_EFF"] = df_ventas["F_DEC"].fillna(df_ventas["F_VTA"])

  fechas_validas = pd.Series(df_ventas["F_VTA"]).dropna()
  años_disp = (
      sorted(pd.to_datetime(fechas_validas).dt.year.unique())
      if not fechas_validas.empty
      else [date.today().year]
  )
  año_sel = st.sidebar.selectbox("Año", años_disp, index=len(años_disp) - 1)

  meses_disp = (
      sorted(
          pd.to_datetime(
              fechas_validas[
                  pd.to_datetime(fechas_validas).dt.year == año_sel
              ]
          ).dt.month.unique()
      )
      if not fechas_validas.empty
      else [date.today().month]
  )
  nombres_meses = {
      1: "Enero",
      2: "Febrero",
      3: "Marzo",
      4: "Abril",
      5: "Mayo",
      6: "Junio",
      7: "Julio",
      8: "Agosto",
      9: "Septiembre",
      10: "Octubre",
      11: "Noviembre",
      12: "Diciembre",
  }
  mes_formateado = [nombres_meses[m] for m in meses_disp if m in nombres_meses]
  mes_sel_nombre = (
      st.sidebar.selectbox(
          "Mes", mes_formateado, index=len(mes_formateado) - 1
      )
      if mes_formateado
      else "Noviembre"
  )
  mes_sel = list(nombres_meses.keys())[
      list(nombres_meses.values()).index(mes_sel_nombre)
  ]

  # REFERENCIA DE AGENTES CONTRATADOS Y AUSENTISMO TEÓRICO
  agentes_contratados_ref = 71 if mes_sel == 11 else (74 if mes_sel == 10 else 71)
  agentes_contratados_input = st.sidebar.number_input(
      "Agentes Contratados (Base)",
      min_value=1,
      max_value=200,
      value=agentes_contratados_ref,
  )

  ausentismo_teorico_input = (
      st.sidebar.number_input(
          "% Ausentismo Esperado (Contratados)",
          min_value=0.0,
          max_value=30.0,
          value=4.0,
          step=0.5,
      )
      / 100.0
  )

  if "asesor" in [str(c).lower() for c in df_ventas.columns]:
    col_as = next(c for c in df_ventas.columns if "asesor" in str(c).lower())
    asesores = ["Todos"] + sorted(
        df_ventas[col_as].dropna().astype(str).unique().tolist()
    )
    asesor_sel = st.sidebar.selectbox("Asesor", asesores)
    if asesor_sel != "Todos":
      df_ventas = df_ventas[df_ventas[col_as] == asesor_sel]

  def parse_fecha_sucia(serie, año):
    def extract_date(val):
      if pd.isna(val) or val == "" or val == "nan":
        return pd.NaT
      val_str = str(val).strip().lower()
      if re.match(r"^\d{4}-\d{2}-\d{2}", val_str):
        try:
          return pd.to_datetime(val_str[:10]).date()
        except:
          pass
      m = re.search(r"(\d{1,2})-([a-z]{3})", val_str)
      if m:
        d, mes_str = int(m.group(1)), m.group(2)
        m_num = {
            "ene": 1,
            "feb": 2,
            "mar": 3,
            "abr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "ago": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dic": 12,
        }.get(mes_str, 1)
        try:
          return date(año, m_num, d)
        except:
          pass
      try:
        return pd.to_datetime(val, errors="coerce").date()
      except:
        return pd.NaT

    return serie.apply(extract_date)

  # CALENDARIO BASE
  festivos_mx = holidays.Mexico(years=año_sel)
  num_dias = calendar.monthrange(año_sel, mes_sel)[1]
  df_cal = pd.DataFrame(
      {"Fecha": [date(año_sel, mes_sel, d) for d in range(1, num_dias + 1)]}
  )
  df_cal["Día_Semana"] = pd.to_datetime(df_cal["Fecha"]).dt.dayofweek
  df_cal["Es_Festivo"] = pd.to_datetime(df_cal["Fecha"]).apply(
      lambda x: x in festivos_mx
  )
  df_cal = df_cal[
      ~((df_cal["Día_Semana"] == 6) | (df_cal["Es_Festivo"]))
  ].copy()

  # FILTROS ADICIONALES SIDEBAR
  dias_nombres_map = {
      0: "Lunes",
      1: "Martes",
      2: "Miércoles",
      3: "Jueves",
      4: "Viernes",
      5: "Sábado",
  }
  df_cal["Nombre_Día"] = df_cal["Día_Semana"].map(dias_nombres_map)

  dias_semana_sel = st.sidebar.multiselect(
      "Día de la Semana",
      options=list(dias_nombres_map.values()),
      default=[],
  )
  if dias_semana_sel:
    df_cal = df_cal[df_cal["Nombre_Día"].isin(dias_semana_sel)]

  fechas_mes_disp = sorted(df_cal["Fecha"].unique())
  fechas_sel = st.sidebar.multiselect(
      "Fechas Específicas",
      options=fechas_mes_disp,
      format_func=lambda x: x.strftime("%d-%b-%Y"),
  )
  if fechas_sel:
    df_cal = df_cal[df_cal["Fecha"].isin(fechas_sel)]

  if not df_cal.empty:
    min_f, max_f = df_cal["Fecha"].min(), df_cal["Fecha"].max()
    rango_f = st.sidebar.date_input(
        "Rango de Fechas", value=(min_f, max_f), min_value=min_f, max_value=max_f
    )
    if isinstance(rango_f, tuple) and len(rango_f) == 2:
      df_cal = df_cal[
          (df_cal["Fecha"] >= rango_f[0]) & (df_cal["Fecha"] <= rango_f[1])
      ]

  # PREPARACIÓN PLANTA
  if not df_planta.empty and len(df_planta.columns) > 2:
    df_planta["Fecha"] = pd.to_datetime(
        df_planta.iloc[:, 0], errors="coerce"
    ).dt.date
    df_planta["Agentes Plantilla"] = (
        pd.to_numeric(df_planta.iloc[:, 1], errors="coerce").fillna(0)
    )
    df_planta["Agentes Log"] = (
        pd.to_numeric(df_planta.iloc[:, 2], errors="coerce").fillna(0)
    )
    df_cal = pd.merge(
        df_cal,
        df_planta.groupby("Fecha")
        .agg({"Agentes Plantilla": "max", "Agentes Log": "max"})
        .reset_index(),
        on="Fecha",
        how="left",
    )

  # PREPARACIÓN SEG PPTO (AJ=35, AK=36, AL=37, AM=38, AN=39)
  if not df_ppto.empty and len(df_ppto.columns) > 35:
    df_ppto["Fecha"] = parse_fecha_sucia(df_ppto.iloc[:, 35], año_sel)
    df_ppto["Meta Día Lead Efectivo"] = (
        pd.to_numeric(df_ppto.iloc[:, 36], errors="coerce").fillna(0)
        if len(df_ppto.columns) > 36
        else 0
    )
    df_ppto["Meta Asesor"] = (
        pd.to_numeric(df_ppto.iloc[:, 37], errors="coerce").fillna(0)
        if len(df_ppto.columns) > 37
        else 0
    )
    df_ppto["Meta AP Mes"] = (
        pd.to_numeric(df_ppto.iloc[:, 38], errors="coerce").fillna(0)
        if len(df_ppto.columns) > 38
        else 0
    )
    df_ppto["Meta AP Cosecha"] = (
        pd.to_numeric(df_ppto.iloc[:, 39], errors="coerce").fillna(0)
        if len(df_ppto.columns) > 39
        else 0
    )

    df_cal = pd.merge(
        df_cal,
        df_ppto.groupby("Fecha")
        .agg({
            "Meta Día Lead Efectivo": "max",
            "Meta Asesor": "max",
            "Meta AP Mes": "max",
            "Meta AP Cosecha": "max",
        })
        .reset_index(),
        on="Fecha",
        how="left",
    )

  # PREPARACIÓN MALLA DÍA Y SPH (Fecha=13, BN=65)
  if not df_malla.empty and len(df_malla.columns) > 13:
    df_malla["Fecha"] = parse_fecha_sucia(df_malla.iloc[:, 13], año_sel)
    col_tr_idx = (
        65
        if len(df_malla.columns) > 65
        else next(
            (
                i
                for i, c in enumerate(df_malla.columns)
                if "tiempo" in str(c).lower()
            ),
            -1,
        )
    )
    if col_tr_idx != -1 and len(df_malla.columns) > col_tr_idx:
      df_malla["Tiempo Real"] = (
          pd.to_numeric(df_malla.iloc[:, col_tr_idx], errors="coerce").fillna(0)
      )
      df_cal = pd.merge(
          df_cal,
          df_malla.groupby("Fecha")
          .agg({"Tiempo Real": "sum"})
          .reset_index(),
          on="Fecha",
          how="left",
      )

  for col in [
      "Agentes Plantilla",
      "Agentes Log",
      "Meta Día Lead Efectivo",
      "Meta Asesor",
      "Meta AP Mes",
      "Meta AP Cosecha",
      "Tiempo Real",
  ]:
    if col not in df_cal.columns:
      df_cal[col] = 0
  df_cal = df_cal.fillna(0)

  # AGRUPACIÓN VENTAS
  df_ventas_vta = df_ventas[
      (pd.to_datetime(df_ventas["F_VTA"]).dt.year == año_sel)
      & (pd.to_datetime(df_ventas["F_VTA"]).dt.month == mes_sel)
  ]
  agrup_vta = (
      df_ventas_vta.groupby("F_VTA")
      .apply(lambda x: pd.Series({
          "Tramites": len(x),
          "Lead Efectivo": (x["ESTADO"] == "LEAD EFECTIVO").sum(),
          "Lead No Capturado": (x["ESTADO"] == "LEAD NO CAPTURADO").sum(),
          "Lead No Condiciones": (x["ESTADO"] == "LEAD NO CONDICIONES").sum(),
          "Otros": (
              ~x["ESTADO"].isin([
                  "LEAD EFECTIVO",
                  "LEAD NO CAPTURADO",
                  "LEAD NO CONDICIONES",
                  "",
                  "NAN",
              ])
          ).sum(),
          "EVALUADO": (
              (x["ESTADO"] == "LEAD EFECTIVO")
              & (x["DECISION"].isin(["A", "D", "P", "C"]))
          ).sum(),
          "NO GESTIONADO": (
              (x["ESTADO"] == "LEAD EFECTIVO") & (x["DECISION"] == "-")
          ).sum(),
          "Declinado": (
              (x["ESTADO"] == "LEAD EFECTIVO") & (x["DECISION"] == "D")
          ).sum(),
          "Cancelado": (
              (x["ESTADO"] == "LEAD EFECTIVO") & (x["DECISION"] == "C")
          ).sum(),
          "Pendiente": (
              (x["ESTADO"] == "LEAD EFECTIVO") & (x["DECISION"] == "P")
          ).sum(),
      }))
      .reset_index()
      .rename(columns={"F_VTA": "Fecha"})
  )

  # AGRUPACIÓN APROBACIONES EN LA TABLA PRINCIPAL:
  # 1) AP MES: Ventas realizadas en el mes seleccionado Y DECIDIDAS en el mes seleccionado.
  #    Se agrupan por F_VTA para reflejar la venta diaria sin cruzar cosechas de meses futuros.
  df_ap_mes = df_ventas[
      (pd.to_datetime(df_ventas["F_VTA"]).dt.year == año_sel)
      & (pd.to_datetime(df_ventas["F_VTA"]).dt.month == mes_sel)
      & (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.year == año_sel)
      & (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.month == mes_sel)
      & (df_ventas["DECISION"] == "A")
  ]
  agrup_ap_mes = (
      df_ap_mes.groupby("F_VTA")
      .size()
      .reset_index(name="AP MES")
      .rename(columns={"F_VTA": "Fecha"})
  )

  # 2) AP COSECHA: Ventas realizadas ANTES del mes seleccionado Y DECIDIDAS en el mes seleccionado.
  #    Se agrupan por F_DEC_EFF (día de decisión en el mes en curso).
  inicio_mes_sel = date(año_sel, mes_sel, 1)
  df_ap_cos = df_ventas[
      (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.year == año_sel)
      & (pd.to_datetime(df_ventas["F_DEC_EFF"]).dt.month == mes_sel)
      & (pd.to_datetime(df_ventas["F_VTA"]) < pd.Timestamp(inicio_mes_sel))
      & (df_ventas["DECISION"] == "A")
  ]
  agrup_ap_cos = (
      df_ap_cos.groupby("F_DEC_EFF")
      .size()
      .reset_index(name="AP COSECHA")
      .rename(columns={"F_DEC_EFF": "Fecha"})
  )

  # CRUCE FINAL Y CÁLCULOS
  df_final = pd.merge(df_cal, agrup_vta, on="Fecha", how="left").fillna(0)
  df_final = pd.merge(df_final, agrup_ap_mes, on="Fecha", how="left").fillna(0)
  df_final = pd.merge(df_final, agrup_ap_cos, on="Fecha", how="left").fillna(0)

  dias_esp = {0: "lun", 1: "mar", 2: "mié", 3: "jue", 4: "vie", 5: "sáb"}
  df_final["Día"] = df_final.apply(
      lambda row: (
          f"{dias_esp[pd.to_datetime(row['Fecha']).dayofweek]}-{pd.to_datetime(row['Fecha']).strftime('%d-%b')}".lower()
      ),
      axis=1,
  )

  df_final["Meta Lead Efectivos Programados"] = (
      df_final["Meta Asesor"] * df_final["Agentes Plantilla"]
  )
  df_final["Meta Lead Efectivos Log"] = (
      df_final["Meta Asesor"] * df_final["Agentes Log"]
  )
  df_final["Diferencia LE"] = (
      df_final["Meta Lead Efectivos Programados"]
      - df_final["Meta Lead Efectivos Log"]
  )

  df_final["GAP LE"] = 0.0
  mask_pasado = df_final["Fecha"] < date.today()
  df_final.loc[mask_pasado, "GAP LE"] = (
      df_final.loc[mask_pasado, "Lead Efectivo"].cumsum()
      - df_final.loc[mask_pasado, "Meta Día Lead Efectivo"].cumsum()
  )

  df_final["% LE"] = np.where(
      df_final["Tramites"] > 0, df_final["Lead Efectivo"] / df_final["Tramites"], 0
  )
  df_final["% REM/RECH"] = np.where(
      df_final["Tramites"] > 0, df_final["Otros"] / df_final["Tramites"], 0
  )
  df_final["Prom"] = np.where(
      df_final["Agentes Log"] > 0,
      df_final["Lead Efectivo"] / df_final["Agentes Log"],
      0,
  )
  df_final["% Ausentismo"] = np.where(
      df_final["Agentes Plantilla"] > 0,
      (df_final["Agentes Plantilla"] - df_final["Agentes Log"])
      / df_final["Agentes Plantilla"],
      0,
  )

  # SPH: Lead Efectivo / Agentes Log
  df_final["SPH"] = np.where(
      df_final["Agentes Log"] > 0,
      df_final["Lead Efectivo"] / df_final["Agentes Log"],
      0,
  )

  df_final["AP Totales"] = df_final["AP MES"] + df_final["AP COSECHA"]
  
  # % AP DIA: Calculado como AP MES / Lead Efectivo (sin acumular ni incluir cosecha)
  df_final["% AP dia"] = np.where(
      df_final["Lead Efectivo"] > 0,
      df_final["AP MES"] / df_final["Lead Efectivo"],
      0,
  )

  # CÁLCULOS ACUMULADOS DE CONVERSIÓN A LA FECHA EN LA TABLA
  df_final["% Aprob Acum Mes"] = np.where(
      df_final["Lead Efectivo"].cumsum() > 0,
      df_final["AP MES"].cumsum() / df_final["Lead Efectivo"].cumsum(),
      0,
  )
  df_final["% AP Acum"] = np.where(
      df_final["Lead Efectivo"].cumsum() > 0,
      df_final["AP Totales"].cumsum() / df_final["Lead Efectivo"].cumsum(),
      0,
  )

  df_final["% EVALUADO"] = np.where(
      df_final["Lead Efectivo"] > 0,
      df_final["EVALUADO"] / df_final["Lead Efectivo"],
      0,
  )
  df_final["% Declinado"] = np.where(
      df_final["Lead Efectivo"] > 0,
      df_final["Declinado"] / df_final["Lead Efectivo"],
      0,
  )
  df_final["% Cancelado"] = np.where(
      df_final["Lead Efectivo"] > 0,
      df_final["Cancelado"] / df_final["Lead Efectivo"],
      0,
  )
  df_final["% Pendiente"] = np.where(
      df_final["Lead Efectivo"] > 0,
      df_final["Pendiente"] / df_final["Lead Efectivo"],
      0,
  )

  columnas_vista = [
      "Día",
      "Tramites",
      "Lead Efectivo",
      "Meta Día Lead Efectivo",
      "Meta Lead Efectivos Programados",
      "Meta Lead Efectivos Log",
      "Diferencia LE",
      "GAP LE",
      "Lead No Capturado",
      "Lead No Condiciones",
      "Otros",
      "% LE",
      "% REM/RECH",
      "Prom",
      "Agentes Log",
      "Agentes Plantilla",
      "% Ausentismo",
      "SPH",
      "AP MES",
      "AP COSECHA",
      "AP Totales",
      "% AP dia",
      "% Aprob Acum Mes",
      "% AP Acum",
      "EVALUADO",
      "% EVALUADO",
      "NO GESTIONADO",
      "Declinado",
      "% Declinado",
      "Cancelado",
      "% Cancelado",
      "Pendiente",
      "% Pendiente",
  ]
  df_vista = df_final[
      [c for c in columnas_vista if c in df_final.columns]
  ].copy()

  # FILA DE TOTALES
  totales = df_final.sum(numeric_only=True).to_dict()
  totales["Día"] = "TOTAL"
  totales["% LE"] = (
      totales["Lead Efectivo"] / totales["Tramites"]
      if totales.get("Tramites", 0) > 0
      else 0
  )
  totales["% REM/RECH"] = (
      totales["Otros"] / totales["Tramites"]
      if totales.get("Tramites", 0) > 0
      else 0
  )
  totales["Prom"] = (
      totales["Lead Efectivo"] / totales["Agentes Log"]
      if totales.get("Agentes Log", 0) > 0
      else 0
  )
  totales["% Ausentismo"] = (
      (totales["Agentes Plantilla"] - totales["Agentes Log"])
      / totales["Agentes Plantilla"]
      if totales.get("Agentes Plantilla", 0) > 0
      else 0
  )
  totales["SPH"] = (
      totales["Lead Efectivo"] / totales["Agentes Log"]
      if totales.get("Agentes Log", 0) > 0
      else 0
  )
  totales["% AP dia"] = (
      totales["AP MES"] / totales["Lead Efectivo"]
      if totales.get("Lead Efectivo", 0) > 0
      else 0
  )
  totales["% Aprob Acum Mes"] = (
      totales["AP MES"] / totales["Lead Efectivo"]
      if totales.get("Lead Efectivo", 0) > 0
      else 0
  )
  totales["% AP Acum"] = (
      totales["AP Totales"] / totales["Lead Efectivo"]
      if totales.get("Lead Efectivo", 0) > 0
      else 0
  )

  df_gap_valido = df_final[df_final["GAP LE"] != 0]
  totales["GAP LE"] = (
      df_gap_valido["GAP LE"].iloc[-1] if not df_gap_valido.empty else 0
  )

  df_totales = pd.DataFrame([totales])[df_vista.columns]
  df_vista = pd.concat([df_vista, df_totales], ignore_index=True)

  # KPIS SUPERIORES
  st.title(f"📊 Informe Gerencial - {mes_sel_nombre} {año_sel}")

  df_aprob_mes = df_final[df_final["AP MES"] > 0]
  if not df_aprob_mes.empty:
    fecha_corte = df_aprob_mes["Fecha"].max()
    ultimo_dia_ap = pd.to_datetime(fecha_corte).strftime("%d-%b").lower()
    pct_ap_acum_mes_ultimo = df_final[df_final["Fecha"] == fecha_corte].iloc[0][
        "% Aprob Acum Mes"
    ]
  else:
    fecha_corte = date.today()
    ultimo_dia_ap = "N/A"
    pct_ap_acum_mes_ultimo = 0

  meta_ap_objetivo = 0.045
  desv_ap = pct_ap_acum_mes_ultimo - meta_ap_objetivo

  df_pasado = df_final[df_final["Fecha"] < date.today()]
  if df_pasado.empty:
    df_pasado = df_final[df_final["Fecha"] <= date.today()]
  if df_pasado.empty:
    df_pasado = df_final

  meta_le_acum_fecha = df_pasado["Meta Día Lead Efectivo"].sum()
  meta_le_total_mes = df_final["Meta Día Lead Efectivo"].sum()
  leads_acum_fecha = df_pasado["Lead Efectivo"].sum()

  pct_cumpl_le_total = (
      (totales["Lead Efectivo"] / meta_le_total_mes)
      if meta_le_total_mes > 0
      else 0
  )
  pct_cumpl_le_fecha = (
      (totales["Lead Efectivo"] / meta_le_acum_fecha)
      if meta_le_acum_fecha > 0
      else 0
  )
  pct_gap_cumpl = (
      (leads_acum_fecha / meta_le_acum_fecha) if meta_le_acum_fecha > 0 else 0
  )

  df_hasta_ap = df_final[df_final["Fecha"] <= fecha_corte]
  meta_ap_mes_fecha = df_hasta_ap["Meta AP Mes"].sum()
  meta_ap_cos_fecha = df_hasta_ap["Meta AP Cosecha"].sum()
  meta_ap_tot_fecha = meta_ap_mes_fecha + meta_ap_cos_fecha

  meta_ap_mes_total = df_final["Meta AP Mes"].sum()
  meta_ap_cos_total = df_final["Meta AP Cosecha"].sum()
  meta_ap_tot_total = meta_ap_mes_total + meta_ap_cos_total

  # TABLERO DE TARJETAS SUPERIORES (FILA 1)
  col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)

  with col_kpi1:
    badg = (
        "kpi-badge-danger"
        if pct_cumpl_le_fecha < 0.80
        else ("kpi-badge-warning" if pct_cumpl_le_fecha < 1.0 else "kpi-badge-success")
    )
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-title">Leads Efectivos</div>
            <div class="kpi-value">{int(totales['Lead Efectivo']):,}</div>
            <div class="kpi-subtext">Meta Mes: <b>{int(meta_le_total_mes):,}</b> ({pct_cumpl_le_total:.1%})</div>
            <div class="kpi-subtext">Cumpl. a la Fecha: <span class="{badg}">{pct_cumpl_le_fecha:.1%}</span></div>
            {render_pila_bar(pct_cumpl_le_fecha)}
        </div>""",
        unsafe_allow_html=True,
    )

  with col_kpi2:
    badg = "kpi-badge-danger" if totales["GAP LE"] < 0 else "kpi-badge-success"
    badg_cumpl = (
        "kpi-badge-danger"
        if pct_gap_cumpl < 0.80
        else ("kpi-badge-warning" if pct_gap_cumpl < 1.0 else "kpi-badge-success")
    )
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-title">GAP LE Acumulado</div>
            <div class="kpi-value"><span class="{badg}">{int(totales['GAP LE']):,}</span></div>
            <div class="kpi-subtext">Esperado a la Fecha: <b>{int(meta_le_acum_fecha):,}</b></div>
            <div class="kpi-subtext">Cumpl. a la Fecha: <span class="{badg_cumpl}">{pct_gap_cumpl:.1%}</span></div>
            {render_pila_bar(pct_gap_cumpl)}
        </div>""",
        unsafe_allow_html=True,
    )

  with col_kpi3:
    badg = "kpi-badge-danger" if desv_ap < 0 else "kpi-badge-success"
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-title">Últ. Aprobación ({ultimo_dia_ap})</div>
            <div class="kpi-value">{pct_ap_acum_mes_ultimo:.1%}</div>
            <div class="kpi-subtext">Objetivo: <b>4.5%</b></div>
            <div class="kpi-subtext">Desviación: <span class="{badg}">{desv_ap:+.1%}</span></div>
        </div>""",
        unsafe_allow_html=True,
    )

  with col_kpi4:
    prom_plantilla = (
        df_final[df_final["Agentes Plantilla"] > 0]["Agentes Plantilla"].mean()
        if not df_final.empty
        else 0
    )
    prom_log = (
        df_final[df_final["Agentes Log"] > 0]["Agentes Log"].mean()
        if not df_final.empty
        else 0
    )
    pct_aus = (
        (prom_plantilla - prom_log) / prom_plantilla if prom_plantilla > 0 else 0
    )

    st.markdown(
        f"""<div class="table-card">
            <div class="table-card-row"><span>Prom. Agentes Plantilla:</span> <b>{prom_plantilla:.0f}</b></div>
            <div class="table-card-row"><span>Prom. Agentes Log:</span> <b>{prom_log:.0f}</b></div>
            <div class="table-card-row"><span>% Ausentismo Prom.:</span> <b style="color:#d97706">{pct_aus:.1%}</b></div>
        </div>""",
        unsafe_allow_html=True,
    )

  # TARJETAS DE APROBACIÓN (FILA 2)
  col_ap1, col_ap2, col_ap3 = st.columns(3)

  with col_ap1:
    cumpl_ap_mes_fecha = (
        totales["AP MES"] / meta_ap_mes_fecha if meta_ap_mes_fecha > 0 else 0
    )
    cumpl_ap_mes_tot = (
        totales["AP MES"] / meta_ap_mes_total if meta_ap_mes_total > 0 else 0
    )
    badg = (
        "kpi-badge-danger"
        if cumpl_ap_mes_fecha < 0.80
        else (
            "kpi-badge-warning"
            if cumpl_ap_mes_fecha < 1.0
            else "kpi-badge-success"
        )
    )
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-title">AP MES (Total)</div>
            <div class="kpi-value">{int(totales['AP MES'])}</div>
            <div class="kpi-subtext">Meta a la Fecha: <b>{int(meta_ap_mes_fecha)}</b> (<span class="{badg}">{cumpl_ap_mes_fecha:.1%}</span>)</div>
            <div class="kpi-subtext">Meta Total Mes: <b>{int(meta_ap_mes_total)}</b> ({cumpl_ap_mes_tot:.1%})</div>
            {render_gauge_svg(cumpl_ap_mes_fecha)}
        </div>""",
        unsafe_allow_html=True,
    )

  with col_ap2:
    cumpl_ap_cos_fecha = (
        totales["AP COSECHA"] / meta_ap_cos_fecha if meta_ap_cos_fecha > 0 else 0
    )
    cumpl_ap_cos_tot = (
        totales["AP COSECHA"] / meta_ap_cos_total if meta_ap_cos_total > 0 else 0
    )
    badg = (
        "kpi-badge-danger"
        if cumpl_ap_cos_fecha < 0.80
        else (
            "kpi-badge-warning"
            if cumpl_ap_cos_fecha < 1.0
            else "kpi-badge-success"
        )
    )
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-title">AP Cosecha (Total)</div>
            <div class="kpi-value">{int(totales['AP COSECHA'])}</div>
            <div class="kpi-subtext">Meta a la Fecha: <b>{int(meta_ap_cos_fecha)}</b> (<span class="{badg}">{cumpl_ap_cos_fecha:.1%}</span>)</div>
            <div class="kpi-subtext">Meta Total Mes: <b>{int(meta_ap_cos_total)}</b> ({cumpl_ap_cos_tot:.1%})</div>
            {render_gauge_svg(cumpl_ap_cos_fecha)}
        </div>""",
        unsafe_allow_html=True,
    )

  with col_ap3:
    cumpl_ap_tot_fecha = (
        totales["AP Totales"] / meta_ap_tot_fecha if meta_ap_tot_fecha > 0 else 0
    )
    cumpl_ap_tot_tot = (
        totales["AP Totales"] / meta_ap_tot_total if meta_ap_tot_total > 0 else 0
    )
    badg = (
        "kpi-badge-danger"
        if cumpl_ap_tot_fecha < 0.80
        else (
            "kpi-badge-warning"
            if cumpl_ap_tot_fecha < 1.0
            else "kpi-badge-success"
        )
    )
    st.markdown(
        f"""<div class="kpi-card">
            <div class="kpi-title">AP Totales</div>
            <div class="kpi-value">{int(totales['AP Totales'])}</div>
            <div class="kpi-subtext">Meta a la Fecha: <b>{int(meta_ap_tot_fecha)}</b> (<span class="{badg}">{cumpl_ap_tot_fecha:.1%}</span>)</div>
            <div class="kpi-subtext">Meta Total Mes: <b>{int(meta_ap_tot_total)}</b> ({cumpl_ap_tot_tot:.1%})</div>
            {render_gauge_svg(cumpl_ap_tot_fecha)}
        </div>""",
        unsafe_allow_html=True,
    )

  st.divider()

  # FORMATO DE DICCIONARIO
  format_dict = {}
  for c in df_vista.columns:
    if c == "Día":
      continue
    if "%" in c or c in ["% Aprob Acum Mes", "% AP Acum"]:
      format_dict[c] = "{:.1%}"
    elif c in ["Prom", "SPH"]:
      format_dict[c] = "{:.1f}"
    else:
      format_dict[c] = "{:.0f}"

  # PALETAS DE COLORES SOBRIAS (RGB)
  rgb_green = (162, 217, 163)  # Verde suave (#a2d9a3)
  rgb_orange = (254, 210, 120)  # Naranja intermedio suave (#fed278)
  rgb_red = (248, 140, 140)  # Rojo suave (#f88c8c)
  rgb_white = (255, 255, 255)  # Blanco (#ffffff)

  mask_hasta_ayer = df_final["Fecha"] < date.today()
  df_pasado_vals = df_final[mask_hasta_ayer]

  min_max_dict = {}
  for col in [
      "Lead Efectivo",
      "% LE",
      "% REM/RECH",
      "Prom",
      "SPH",
      "% AP dia",
      "% Aprob Acum Mes",
      "% AP Acum",
      "NO GESTIONADO",
      "% EVALUADO",
  ]:
    if col == "Lead Efectivo":
      df_no_sab = df_pasado_vals[
          pd.to_datetime(df_pasado_vals["Fecha"]).dt.dayofweek != 5
      ]
      vmin = df_no_sab[col].min() if not df_no_sab.empty else 0
      vmax = df_no_sab[col].max() if not df_no_sab.empty else 1
    elif not df_pasado_vals.empty and col in df_pasado_vals.columns:
      vmin = df_pasado_vals[col].min()
      vmax = df_pasado_vals[col].max()
    else:
      vmin, vmax = 0, 1
    min_max_dict[col] = (vmin, vmax)

  def aplicar_formatos_condicionales(df_input):
    styles = pd.DataFrame("", index=df_input.index, columns=df_input.columns)

    for idx, row in df_input.iterrows():
      dia_str = str(row["Día"])
      base_align = "text-align: center !important;"

      # Resalte Fila TOTAL
      if dia_str == "TOTAL":
        styles.loc[idx, :] = (
            "font-weight: bold; background-color: #f0f2f6; text-align: center"
            " !important;"
        )
        continue

      # Resalte Fila Última Aprobación (Azul Suave)
      es_ultimo_ap = (
          ultimo_dia_ap != "N/A" and ultimo_dia_ap in dia_str.lower()
      )
      row_base_style = (
          "background-color: #dbeafe; font-weight: bold; border-left: 3px solid"
          " #2563eb; "
          if es_ultimo_ap
          else ""
      )

      corresponde_pasado = False
      if idx < len(df_final):
        corresponde_pasado = df_final.iloc[idx]["Fecha"] < date.today()

      for col in df_input.columns:
        cell_style = base_align + row_base_style

        if corresponde_pasado:
          val = row[col]
          if isinstance(val, (int, float, np.number)):
            if col == "Lead Efectivo":
              es_sabado = "sáb" in dia_str.lower()
              if not es_sabado:
                vmin, vmax = min_max_dict["Lead Efectivo"]
                bg = interpolate_color_2pt(
                    val, vmin, vmax, rgb_white, rgb_green
                )
                if bg:
                  cell_style += " " + bg

            elif col in [
                "% LE",
                "Prom",
                "% AP dia",
                "% Aprob Acum Mes",
                "% AP Acum",
                "% EVALUADO",
            ]:
              # Verde a Rojo con Naranja Intermedio
              vmin, vmax = min_max_dict[col]
              bg = interpolate_color_3pt(
                  val, vmin, vmax, rgb_red, rgb_orange, rgb_green
              )
              if bg:
                cell_style += " " + bg

            elif col == "% REM/RECH":
              # Rojo a Verde con Naranja Intermedio
              vmin, vmax = min_max_dict[col]
              bg = interpolate_color_3pt(
                  val, vmin, vmax, rgb_green, rgb_orange, rgb_red
              )
              if bg:
                cell_style += " " + bg

            elif col in ["SPH", "NO GESTIONADO"]:
              # Verde a Blanco
              vmin, vmax = min_max_dict[col]
              bg = interpolate_color_2pt(val, vmin, vmax, rgb_white, rgb_green)
              if bg:
                cell_style += " " + bg

        styles.loc[idx, col] = cell_style

    return styles

  styler = (
      df_vista.style.format(format_dict)
      .set_properties(**{"text-align": "center !important", "font-size": "13px"})
      .apply(aplicar_formatos_condicionales, axis=None)
  )

  st.dataframe(styler, use_container_width=True, height=750, hide_index=True)

  # =========================================================================
  # 🚀 SECCIÓN: ANÁLISIS GERENCIAL DE CAPACIDAD Y DESVIACIÓN DE LEADS
  # =========================================================================
  st.divider()
  st.subheader("🎯 Análisis Comparativo de Capacidad y Desviación de Leads")
  st.caption(
      f"Evaluación diaria de Meta LE basada en Agentes Contratados ({agentes_contratados_input} menos "
      f"{ausentismo_teorico_input:.1%} ausentismo teórico = {agentes_contratados_input * (1 - ausentismo_teorico_input):.2f} netos). "
      "La Meta Asesor de Sábados se calcula a la mitad (4.1 / 2)."
  )

  df_cap = df_final.copy()
  df_cap["Agentes Contratados"] = agentes_contratados_input
  df_cap["Agentes Programados"] = df_cap["Agentes Plantilla"]
  df_cap["Agentes Log"] = df_cap["Agentes Log"]
  df_cap["Ausencias Día"] = df_cap["Agentes Programados"] - df_cap["Agentes Log"]

  # Personal Neto Contratado (-4% o según slider)
  agentes_netos_contratados = agentes_contratados_input * (
      1.0 - ausentismo_teorico_input
  )

  # Función para determinar la Meta Asesor según el día (Semana vs Sábado)
  def obtener_meta_asesor_dia(row):
    es_sabado = "sáb" in str(row["Día"]).lower()
    base = (
        row["Meta Asesor"]
        if ("Meta Asesor" in row and row["Meta Asesor"] > 0)
        else 4.1
    )
    return (base / 2.0) if es_sabado else base

  df_cap["Meta_Asesor_Dia"] = df_cap.apply(obtener_meta_asesor_dia, axis=1)

  # CÁLCULOS DE METAS Y LEADS REALIZADOS
  df_cap["Meta LE Contratados"] = (
      agentes_netos_contratados * df_cap["Meta_Asesor_Dia"]
  )
  df_cap["Meta LE Programados"] = (
      df_cap["Agentes Programados"] * df_cap["Meta_Asesor_Dia"]
  )
  df_cap["Meta LE Logueados"] = (
      df_cap["Agentes Log"] * df_cap["Meta_Asesor_Dia"]
  )
  df_cap["Leads Realizados"] = df_cap["Lead Efectivo"]

  df_cap["Desv vs Contratados"] = (
      df_cap["Leads Realizados"] - df_cap["Meta LE Contratados"]
  )
  df_cap["Desv vs Logueados"] = (
      df_cap["Leads Realizados"] - df_cap["Meta LE Logueados"]
  )

  # Impactos cuantitativos de desviación (leads)
  df_cap["Impacto Ausentismo"] = (
      -1 * df_cap["Ausencias Día"] * df_cap["Meta_Asesor_Dia"]
  )
  df_cap["Impacto Productividad SPH"] = (
      df_cap["Leads Realizados"] - df_cap["Meta LE Logueados"]
  )

  cols_cap_vista = [
      "Día",
      "Agentes Contratados",
      "Agentes Programados",
      "Ausencias Día",
      "Agentes Log",
      "Meta LE Contratados",
      "Meta LE Programados",
      "Meta LE Logueados",
      "Leads Realizados",
      "SPH",
      "Desv vs Contratados",
      "Desv vs Logueados",
  ]
  df_cap_vista = df_cap[cols_cap_vista].copy()

  # Totales Fila Capacidad
  tot_cap = df_cap.sum(numeric_only=True).to_dict()
  tot_cap["Día"] = "TOTAL"
  tot_cap["Agentes Contratados"] = agentes_contratados_input
  tot_cap["Agentes Programados"] = df_cap[df_cap["Agentes Programados"] > 0][
      "Agentes Programados"
  ].mean()
  tot_cap["Agentes Log"] = df_cap[df_cap["Agentes Log"] > 0][
      "Agentes Log"
  ].mean()
  tot_cap["Ausencias Día"] = (
      tot_cap["Agentes Programados"] - tot_cap["Agentes Log"]
  )
  tot_cap["SPH"] = (
      tot_cap["Leads Realizados"] / tot_cap["Agentes Log"]
      if tot_cap["Agentes Log"] > 0
      else 0
  )
  tot_cap["Meta LE Contratados"] = df_cap["Meta LE Contratados"].sum()
  tot_cap["Meta LE Programados"] = df_cap["Meta LE Programados"].sum()
  tot_cap["Meta LE Logueados"] = df_cap["Meta LE Logueados"].sum()
  tot_cap["Leads Realizados"] = df_cap["Leads Realizados"].sum()
  tot_cap["Desv vs Contratados"] = (
      tot_cap["Leads Realizados"] - tot_cap["Meta LE Contratados"]
  )
  tot_cap["Desv vs Logueados"] = (
      tot_cap["Leads Realizados"] - tot_cap["Meta LE Logueados"]
  )

  df_tot_cap = pd.DataFrame([tot_cap])[cols_cap_vista]
  df_cap_vista = pd.concat([df_cap_vista, df_tot_cap], ignore_index=True)

  # Formato numérico de la tabla de capacidad
  format_cap = {
      "Agentes Contratados": "{:.0f}",
      "Agentes Programados": "{:.0f}",
      "Ausencias Día": "{:.0f}",
      "Agentes Log": "{:.0f}",
      "Meta LE Contratados": "{:.0f}",
      "Meta LE Programados": "{:.0f}",
      "Meta LE Logueados": "{:.0f}",
      "Leads Realizados": "{:.0f}",
      "SPH": "{:.1f}",
      "Desv vs Contratados": "{:+,.0f}",
      "Desv vs Logueados": "{:+,.0f}",
  }

  def estilo_desviaciones(val):
    if not isinstance(val, (int, float, np.number)):
      return ""
    if val > 0:
      return "background-color: #dcfce7; color: #15803d; font-weight: bold;"
    if val < 0:
      return "background-color: #fee2e2; color: #b91c1c; font-weight: bold;"
    return ""

  styler_cap = (
      df_cap_vista.style.format(format_cap)
      .set_properties(**{"text-align": "center !important", "font-size": "13px"})
      .map(
          estilo_desviaciones,
          subset=["Desv vs Contratados", "Desv vs Logueados"],
      )
  )

  col_t1, col_t2 = st.columns([2.2, 1])

  with col_t1:
    st.markdown("##### 📋 Matriz de Descomposición de Leads vs Capacidad")
    st.dataframe(
        styler_cap, use_container_width=True, height=450, hide_index=True
    )

  with col_t2:
    st.markdown("##### 🔍 Diagnóstico Gerencial de Causa Raíz")

    dias_disponibles = df_cap["Día"].tolist()
    dia_sel_diag = st.selectbox(
        "Seleccione el Día a Evaluar:", dias_disponibles, index=0
    )

    idx_curr = df_cap[df_cap["Día"] == dia_sel_diag].index[0]
    row_d = df_cap.iloc[idx_curr]

    desv_cont = row_d["Desv vs Contratados"]
    desv_log = row_d["Desv vs Logueados"]
    imp_aus = row_d["Impacto Ausentismo"]
    imp_sph = row_d["Impacto Productividad SPH"]
    sph_real = row_d["SPH"]
    meta_as = row_d["Meta_Asesor_Dia"]
    log_real = row_d["Agentes Log"]

    badge_cont = (
        f'<span class="arrow-badge-up">⬆️ Superávit (+{int(desv_cont):,} LE)</span>'
        if desv_cont >= 0
        else f'<span class="arrow-badge-down">⬇️ Déficit ({int(desv_cont):,} LE)</span>'
    )
    badge_log = (
        f'<span class="arrow-badge-up">⬆️ Superávit (+{int(desv_log):,} LE)</span>'
        if desv_log >= 0
        else f'<span class="arrow-badge-down">⬇️ Déficit ({int(desv_log):,} LE)</span>'
    )

    # CÁLCULOS COMPARATIVOS AVANZADOS
    if idx_curr > 0:
      row_prev = df_cap.iloc[idx_curr - 1]
      dia_prev_nombre = row_prev["Día"]
      diff_sph_ayer = sph_real - row_prev["SPH"]
      diff_log_ayer = log_real - row_prev["Agentes Log"]
      diff_le_ayer = row_d["Leads Realizados"] - row_prev["Leads Realizados"]

      txt_sph_ayer = (
          f"mejora de <b style='color:#15803d;'>+{diff_sph_ayer:.1f} SPH</b>"
          if diff_sph_ayer >= 0
          else f"caída de <b style='color:#b91c1c;'>{diff_sph_ayer:.1f} SPH</b>"
      )
      txt_log_ayer = (
          f"<b>+{int(diff_log_ayer)} asesores logueados</b>"
          if diff_log_ayer >= 0
          else f"<b>{int(diff_log_ayer)} asesores logueados</b>"
      )
      txt_le_ayer = (
          f"<b>+{int(diff_le_ayer):,} LE</b>"
          if diff_le_ayer >= 0
          else f"<b>{int(diff_le_ayer):,} LE</b>"
      )

      comp_ayer_html = (
          f"• <b>vs Día Anterior ({dia_prev_nombre}):</b> Se registra una variación de {txt_le_ayer} "
          f"en volumen, respaldada por {txt_log_ayer} y una {txt_sph_ayer} en la tasa de conversión por hora."
      )
    else:
      comp_ayer_html = (
          "• <b>vs Día Anterior:</b> Primer día registrado del periodo en evaluación."
      )

    dow_curr = (
        row_d["Día_Semana"]
        if "Día_Semana" in row_d
        else pd.to_datetime(row_d["Fecha"]).dayofweek
    )
    nombre_dow = (
        row_d["Nombre_Día"]
        if "Nombre_Día" in row_d
        else dias_nombres_map.get(dow_curr, "Día")
    )

    df_mismo_dow = df_cap.iloc[:idx_curr]
    if "Día_Semana" in df_mismo_dow.columns:
      df_mismo_dow = df_mismo_dow[df_mismo_dow["Día_Semana"] == dow_curr]
    else:
      df_mismo_dow = df_mismo_dow[
          df_mismo_dow["Fecha"].apply(lambda f: pd.to_datetime(f).dayofweek)
          == dow_curr
      ]

    if not df_mismo_dow.empty:
      prom_sph_dow = df_mismo_dow["SPH"].mean()
      prom_log_dow = df_mismo_dow["Agentes Log"].mean()
      diff_sph_dow = sph_real - prom_sph_dow
      diff_log_dow = log_real - prom_log_dow

      txt_sph_dow = (
          f"<b style='color:#15803d;'>+{diff_sph_dow:.1f} SPH</b> por encima"
          if diff_sph_dow >= 0
          else f"<b style='color:#b91c1c;'>{diff_sph_dow:.1f} SPH</b> por debajo"
      )
      txt_log_dow = (
          f"<b>+{diff_log_dow:+.1f} agentes</b>"
          if diff_log_dow >= 0
          else f"<b>{diff_log_dow:+.1f} agentes</b>"
      )

      comp_dow_html = (
          f"• <b>vs Promedio de {nombre_dow}s Anteriores:</b> SPH se ubica {txt_sph_dow} "
          f"del promedio del día ({prom_sph_dow:.1f} SPH), con una asistencia de {txt_log_dow} frente a su media ({prom_log_dow:.1f} agentes)."
      )
    else:
      comp_dow_html = (
          f"• <b>vs Promedio de {nombre_dow}s Anteriores:</b> Corresponde al primer {nombre_dow} del mes."
      )

    if imp_sph > abs(imp_aus) and desv_cont >= 0:
      concl_base = "El superávit fue impulsado principalmente por una alta productividad individual (SPH) que compensó holgadamente el ausentismo."
    elif abs(imp_aus) > abs(imp_sph) and desv_cont < 0:
      concl_base = "El déficit responde primordialmente al faltante de personal logueado en piso de ventas."
    else:
      concl_base = "El resultado refleja directamente el nivel de conversión y eficiencia horaria de los asesores activos."

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

  # =========================================================================
  # 📈 MÓDULO DE GRÁFICOS EJECUTIVOS: SEGUIMIENTO LE REAL VS PTO & GAP
  # =========================================================================
  st.divider()
  st.subheader("📈 Seguimiento Visual LE Real vs. Pto Diario y GAP Acumulado")
  st.caption(
      "Representación gráfica interactiva y estilizada de los Leads Efectivos"
      " realizados frente a la Meta diaria y el seguimiento acumulado del GAP."
  )

  df_chart = df_cap.copy()
  df_chart["Diferencia Neta Acumulada"] = (
      df_chart["Leads Realizados"] - df_chart["Meta LE Contratados"]
  ).cumsum()

  tab_combo, tab_barras3 = st.tabs([
      "📊 Gráfico Combinado Ejecutivo (Barras + Línea)",
      "📊 Gráfico de 3 Barras (Estilo Excel)",
  ])

  with tab_combo:
    fig_combo = make_subplots(specs=[[{"secondary_y": True}]])

    fig_combo.add_trace(
        go.Bar(
            x=df_chart["Día"],
            y=df_chart["Meta LE Contratados"],
            name="LEADS EFECTIVOS PTTO",
            marker_color="#ea580c",
            text=df_chart["Meta LE Contratados"].astype(int),
            textposition="outside",
            textfont=dict(size=11, color="#1e293b", family="sans-serif"),
            hovertemplate="<b>%{x}</b><br>Meta PTTO: <b>%{y:,.0f} LE</b><extra></extra>",
        ),
        secondary_y=False,
    )

    fig_combo.add_trace(
        go.Bar(
            x=df_chart["Día"],
            y=df_chart["Leads Realizados"],
            name="LEADS EFECTIVOS REAL",
            marker_color="#0284c7",
            text=df_chart["Leads Realizados"].astype(int),
            textposition="outside",
            textfont=dict(size=11, color="#1e293b", family="sans-serif"),
            hovertemplate="<b>%{x}</b><br>Realizado: <b>%{y:,.0f} LE</b><extra></extra>",
        ),
        secondary_y=False,
    )

    fig_combo.add_trace(
        go.Scatter(
            x=df_chart["Día"],
            y=df_chart["Diferencia Neta Acumulada"],
            name="DIFERENCIA NETA ACUMULADA",
            mode="lines+markers+text",
            line=dict(color="#15803d", width=3, dash="solid"),
            marker=dict(size=8, color="#15803d", symbol="circle"),
            text=df_chart["Diferencia Neta Acumulada"].astype(int),
            textposition="bottom center",
            textfont=dict(size=11, color="#166534"),
            hovertemplate="<b>%{x}</b><br>Diferencia Acumulada: <b>%{y:,.0f} LE</b><extra></extra>",
        ),
        secondary_y=True,
    )

    fig_combo.update_layout(
        title=dict(
            text="<b>Seguimiento LE Real Vs Pto Diario & Diferencia Acumulada</b>",
            font=dict(size=16, color="#0f172a"),
        ),
        barmode="group",
        bargap=0.2,
        bargroupgap=0.08,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        height=480,
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#cbd5e1",
            borderwidth=1,
        ),
        hovermode="x unified",
    )

    fig_combo.update_xaxes(
        showgrid=True,
        gridcolor="#f1f5f9",
        tickfont=dict(size=12, color="#334155"),
    )
    fig_combo.update_yaxes(
        title_text="Volumen de Leads Diarios",
        showgrid=True,
        gridcolor="#e2e8f0",
        zeroline=True,
        zerolinecolor="#94a3b8",
        tickfont=dict(size=11, color="#475569"),
        secondary_y=False,
    )
    fig_combo.update_yaxes(
        title_text="Diferencia Acumulada (GAP)",
        showgrid=False,
        zeroline=True,
        zerolinecolor="#ef4444",
        tickfont=dict(size=11, color="#166534"),
        secondary_y=True,
    )

    st.plotly_chart(fig_combo, use_container_width=True)

  with tab_barras3:
    fig_barras3 = go.Figure()

    fig_barras3.add_trace(
        go.Bar(
            x=df_chart["Día"],
            y=df_chart["Meta LE Contratados"],
            name="LEADS EFECTIVOS PTTO",
            marker_color="#ea580c",
            text=df_chart["Meta LE Contratados"].astype(int),
            textposition="auto",
            textfont=dict(size=11, color="#ffffff"),
            hovertemplate="<b>%{x}</b><br>Meta PTTO: <b>%{y:,.0f} LE</b><extra></extra>",
        )
    )

    fig_barras3.add_trace(
        go.Bar(
            x=df_chart["Día"],
            y=df_chart["Leads Realizados"],
            name="LEADS EFECTIVOS REAL",
            marker_color="#0284c7",
            text=df_chart["Leads Realizados"].astype(int),
            textposition="auto",
            textfont=dict(size=11, color="#ffffff"),
            hovertemplate="<b>%{x}</b><br>Realizado: <b>%{y:,.0f} LE</b><extra></extra>",
        )
    )

    fig_barras3.add_trace(
        go.Bar(
            x=df_chart["Día"],
            y=df_chart["Diferencia Neta Acumulada"],
            name="DIFERENCIA NETA ACUMULADA",
            marker_color="#15803d",
            text=df_chart["Diferencia Neta Acumulada"].astype(int),
            textposition="auto",
            textfont=dict(size=11, color="#ffffff"),
            hovertemplate="<b>%{x}</b><br>Diferencia Acumulada: <b>%{y:,.0f} LE</b><extra></extra>",
        )
    )

    fig_barras3.update_layout(
        title=dict(
            text="<b>Seguimiento LE Real Vs Pto Diario (Formato Tríptico de Barras)</b>",
            font=dict(size=16, color="#0f172a"),
        ),
        barmode="group",
        bargap=0.18,
        bargroupgap=0.05,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        height=500,
        margin=dict(l=20, r=20, t=60, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#cbd5e1",
            borderwidth=1,
        ),
        hovermode="x unified",
    )

    fig_barras3.update_xaxes(
        showgrid=True,
        gridcolor="#f1f5f9",
        tickfont=dict(size=12, color="#334155"),
    )
    fig_barras3.update_yaxes(
        showgrid=True,
        gridcolor="#e2e8f0",
        zeroline=True,
        zerolinecolor="#475569",
        zerolinewidth=1.5,
        tickfont=dict(size=11, color="#475569"),
    )

    st.plotly_chart(fig_barras3, use_container_width=True)

  # =========================================================================
  # 📉 SECCIÓN: GRÁFICO DE TENDENCIA DE APROBACIÓN (% AP — ÚLTIMOS 4 MESES)
  # =========================================================================
  st.divider()
  st.subheader("📉 Tendencia AP (% Aprobación Acumulada — ÚLTIMOS 4 MESES)")
  st.caption(
      "Seguimiento acumulado diario de la tasa de aprobación (% AP) para los"
      " últimos 4 meses. Para meses anteriores se utiliza (AP Mes + Cosecha) /"
      " Leads Efectivos; para el mes en curso se utiliza AP Mes / Leads"
      " Efectivos a la fecha."
  )

  # Determinación dinámica de los últimos 4 meses
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

    df_v_mes = df_v[
        (pd.to_datetime(df_v["F_VTA"]).dt.year == y)
        & (pd.to_datetime(df_v["F_VTA"]).dt.month == m)
    ]

    f_dec_eff = df_v["F_DEC_EFF"]
    dec_m_mask = (pd.to_datetime(f_dec_eff).dt.year == y) & (
        pd.to_datetime(f_dec_eff).dt.month == m
    )

    es_mes_actual_flag = (y == año_sel) and (m == mes_sel)

    # Para el mes en curso, se limita la serie hasta el último día que registra aprobaciones (Día 3)
    if es_mes_actual_flag:
      df_ap_curr = df_v_mes[
          (pd.to_datetime(df_v_mes["F_DEC_EFF"]).dt.year == y)
          & (pd.to_datetime(df_v_mes["F_DEC_EFF"]).dt.month == m)
          & (df_v_mes["DECISION"] == "A")
      ]
      if not df_ap_curr.empty:
        max_d = int(pd.to_datetime(df_ap_curr["F_VTA"]).dt.day.max())
      else:
        max_d = num_dias_m
    else:
      max_d = num_dias_m

    dias = []
    pct_acum_list = []

    for d in range(1, max_d + 1):
      f_corte = date(y, m, d)

      leads_acum = (df_v_mes["ESTADO"] == "LEAD EFECTIVO") & (
          df_v_mes["F_VTA"] <= f_corte
      )
      total_leads = leads_acum.sum()

      # AP MES: Ventas del mes (y, m) DECIDIDAS en el mes (y, m) a la fecha de corte
      ap_mes_mask = (
          (pd.to_datetime(df_v["F_VTA"]).dt.year == y)
          & (pd.to_datetime(df_v["F_VTA"]).dt.month == m)
          & (pd.to_datetime(f_dec_eff).dt.year == y)
          & (pd.to_datetime(f_dec_eff).dt.month == m)
          & (df_v["DECISION"] == "A")
          & (df_v["F_VTA"] <= f_corte)
      )
      ap_mes_acum = ap_mes_mask.sum()

      # AP COSECHA: Ventas de meses anteriores decididas en el mes (y, m) a la fecha de corte
      ap_cos_mask = (
          dec_m_mask
          & (df_v["DECISION"] == "A")
          & (pd.to_datetime(df_v["F_VTA"]) < pd.Timestamp(inicio_m))
          & (pd.to_datetime(f_dec_eff).dt.date <= f_corte)
      )
      ap_cos_acum = ap_cos_mask.sum()

      # Para el mes actual se evalúa solo AP MES; para meses anteriores se suman (AP MES + AP COSECHA)
      if es_mes_actual_flag:
        ap_total_acum = ap_mes_acum
      else:
        ap_total_acum = ap_mes_acum + ap_cos_acum

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
    if pcts_m:
      last_val = pcts_m[-1]
      text_labels[-1] = f"<b>{last_val:.1f}%</b>".replace(".", ",")

    fig_tend.add_trace(
        go.Scatter(
            x=dias_m,
            y=pcts_m,
            name=nombre_m,
            mode="lines+markers+text",
            line=dict(color=color_m, width=3),
            marker=dict(size=5, color=color_m),
            text=text_labels,
            textposition="top right",
            textfont=dict(size=13, color=color_m, family="sans-serif"),
            hovertemplate=(
                f"<b>Días %{{x}} ({nombre_m}):</b> %{{y:.1f}}%<extra></extra>"
            ),
        )
    )

  m_inicio_str = nombres_meses[meses_tendencia[0][1]][:3]
  m_fin_str = nombres_meses[meses_tendencia[-1][1]][:3]
  yr_str = str(meses_tendencia[-1][0])[2:]

  fig_tend.update_layout(
      title=dict(
          text=f"<b>Tendencia AP ({m_inicio_str}-{m_fin_str}-{yr_str})</b>",
          font=dict(size=18, color="#0f172a"),
          x=0.5,
          xanchor="center",
      ),
      xaxis=dict(
          title="Día del Mes",
          tickmode="linear",
          tick0=1,
          dtick=1,
          range=[0.5, 31.5],
          showgrid=True,
          gridcolor="#f1f5f9",
          tickfont=dict(size=11, color="#334155"),
      ),
      yaxis=dict(
          title="% Aprobación Acumulada",
          ticksuffix="%",
          showgrid=True,
          gridcolor="#e2e8f0",
          zeroline=True,
          tickfont=dict(size=11, color="#475569"),
      ),
      plot_bgcolor="#ffffff",
      paper_bgcolor="#ffffff",
      height=520,
      margin=dict(l=30, r=40, t=60, b=50),
      legend=dict(
          orientation="h",
          yanchor="bottom",
          y=-0.22,
          xanchor="center",
          x=0.5,
          font=dict(size=12),
      ),
      hovermode="x unified",
  )

  st.plotly_chart(fig_tend, use_container_width=True)

else:
  st.warning("⚠️ No se encontró la hoja de Ventas o le faltan columnas.")
