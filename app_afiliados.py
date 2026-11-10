import calendar
from datetime import date
import math
import re
import holidays
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Informe Gerencial Amex", layout="wide")

# CSS para Tarjetas Gerenciales, Contenedores y Alineación de Tabla
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
    
    /* Forzar centrado de celdas en la tabla */
    [data-testid="stDataFrame"] td, [data-testid="stDataFrame"] th {
        text-align: center !important;
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


# Helper para degradado de colores en RGB
def interpolate_color(val, vmin, vmax, rgb_low, rgb_high):
  if pd.isna(val) or vmin == vmax:
    return ""
  norm = (val - vmin) / (vmax - vmin)
  norm = max(0.0, min(1.0, norm))
  r = int(rgb_low[0] + norm * (rgb_high[0] - rgb_low[0]))
  g = int(rgb_low[1] + norm * (rgb_high[1] - rgb_low[1]))
  b = int(rgb_low[2] + norm * (rgb_high[2] - rgb_low[2]))
  return f"background-color: rgb({r}, {g}, {b}); color: black;"


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

  # FILTROS ADICIONALES SIDEBAR (Día Semana, Fechas Específicas, Rango Fechas)
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
          "EVALUADO": (x["DECISION"] != "-").sum(),
          "NO GESTIONADO": (x["DECISION"] == "-").sum(),
          "Declinado": (x["DECISION"] == "D").sum(),
          "Cancelado": (x["DECISION"] == "C").sum(),
          "Pendiente": (x["DECISION"] == "P").sum(),
      }))
      .reset_index()
      .rename(columns={"F_VTA": "Fecha"})
  )

  # AGRUPACIÓN APROBACIONES
  df_ap_mes = df_ventas_vta[df_ventas_vta["DECISION"] == "A"]
  agrup_ap_mes = (
      df_ap_mes.groupby("F_VTA")
      .size()
      .reset_index(name="AP MES")
      .rename(columns={"F_VTA": "Fecha"})
  )

  df_ap_cos = df_ventas[
      (pd.to_datetime(df_ventas["F_DEC"]).dt.year == año_sel)
      & (pd.to_datetime(df_ventas["F_DEC"]).dt.month == mes_sel)
      & (df_ventas["DECISION"] == "A")
      & (pd.to_datetime(df_ventas["F_VTA"]).dt.month != mes_sel)
  ]
  agrup_ap_cos = (
      df_ap_cos.groupby("F_DEC")
      .size()
      .reset_index(name="AP COSECHA")
      .rename(columns={"F_DEC": "Fecha"})
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
  df_final["SPH"] = np.where(
      df_final["Tiempo Real"] > 0,
      df_final["Lead Efectivo"] / df_final["Tiempo Real"],
      0,
  )

  df_final["AP Totales"] = df_final["AP MES"] + df_final["AP COSECHA"]
  df_final["% AP dia"] = np.where(
      df_final["Lead Efectivo"] > 0,
      df_final["AP Totales"] / df_final["Lead Efectivo"],
      0,
  )

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

  # SE AÑADE '% Aprob Acum Mes' JUSTO DESPUÉS DE '% AP dia'
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
      totales["Lead Efectivo"] / totales.get("Tiempo Real", 1)
      if totales.get("Tiempo Real", 0) > 0
      else 0
  )
  totales["% AP dia"] = (
      totales["AP Totales"] / totales["Lead Efectivo"]
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

  # FORMATOS CONDICIONALES APLICADOS HASTA EL DÍA DE AYER
  # Paletas de colores RGB
  rgb_green = (198, 224, 180)  # Verde suave (#c6e0b4)
  rgb_red = (248, 113, 113)  # Rojo suave (#f87171)
  rgb_white = (255, 255, 255)  # Blanco (#ffffff)

  # Precalculamos valores mínimos y máximos hasta ayer
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
    # Dataframe de estilos vacío
    styles = pd.DataFrame("", index=df_input.index, columns=df_input.columns)

    for idx, row in df_input.iterrows():
      dia_str = str(row["Día"])

      # Resalte Fila TOTAL
      if dia_str == "TOTAL":
        styles.loc[idx, :] = "font-weight: bold; background-color: #f0f2f6;"
        continue

      # Resalte Fila Última Aprobación (Azul Suave)
      es_ultimo_ap = (
          ultimo_dia_ap != "N/A" and ultimo_dia_ap in dia_str.lower()
      )
      base_style = (
          "background-color: #dbeafe; font-weight: bold; border-left: 3px"
          " solid #2563eb;"
          if es_ultimo_ap
          else ""
      )

      # Determinar si la fila corresponde a una fecha transcurrida (< ayer)
      corresponde_pasado = False
      if idx < len(df_final):
        corresponde_pasado = df_final.iloc[idx]["Fecha"] < date.today()

      for col in df_input.columns:
        if base_style:
          styles.loc[idx, col] = base_style

        if not corresponde_pasado:
          continue

        val = row[col]
        if not isinstance(val, (int, float, np.number)):
          continue

        # REGULARES CONDICIONALES
        if col == "Lead Efectivo":
          # Verde a Blanco sin contar sábados
          es_sabado = "sáb" in dia_str.lower()
          if not es_sabado:
            vmin, vmax = min_max_dict["Lead Efectivo"]
            styles.loc[idx, col] = interpolate_color(
                val, vmin, vmax, rgb_white, rgb_green
            )

        elif col in [
            "% LE",
            "Prom",
            "% AP dia",
            "% Aprob Acum Mes",
            "% AP Acum",
            "% EVALUADO",
        ]:
          # Verde a Rojo (Mayor es verde, Menor es rojo)
          vmin, vmax = min_max_dict[col]
          styles.loc[idx, col] = interpolate_color(
              val, vmin, vmax, rgb_red, rgb_green
          )

        elif col == "% REM/RECH":
          # Rojo a Verde (Mayor es rojo, Menor es verde)
          vmin, vmax = min_max_dict[col]
          styles.loc[idx, col] = interpolate_color(
              val, vmin, vmax, rgb_green, rgb_red
          )

        elif col in ["SPH", "NO GESTIONADO"]:
          # Verde a Blanco
          vmin, vmax = min_max_dict[col]
          styles.loc[idx, col] = interpolate_color(
              val, vmin, vmax, rgb_white, rgb_green
          )

    return styles

  styler = (
      df_vista.style.format(format_dict)
      .set_properties(**{"text-align": "center", "font-size": "13px"})
      .apply(aplicar_formatos_condicionales, axis=None)
  )

  st.dataframe(styler, use_container_width=True, height=750, hide_index=True)
else:
  st.warning("⚠️ No se encontró la hoja de Ventas o le faltan columnas.")
