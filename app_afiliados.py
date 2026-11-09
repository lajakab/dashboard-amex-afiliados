import streamlit as st
import pandas as pd

st.set_page_config(page_title="Detector de Columnas", layout="wide")

st.title("🕵️‍♂️ Detector de Columnas del Archivo Parquet")

try:
    # Intenta leer el archivo
    df = pd.read_parquet("Amex_Afiliados.parquet")
    
    st.success("✅ Archivo leído correctamente. Estas son las columnas que realmente existen dentro del archivo:")
    
    # Muestra los nombres exactos como una lista
    st.write(df.columns.tolist())
    
    # Muestra una muestra de los datos (las primeras 5 filas) para que veas qué contiene cada una
    st.subheader("Muestra de datos (primeras 5 filas):")
    st.dataframe(df.head())
    
except Exception as e:
    st.error(f"❌ No se pudo leer el archivo. Error: {e}")
