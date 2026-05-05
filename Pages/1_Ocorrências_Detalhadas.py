# pages/1_Ocorrências_Detalhadas.py
# OCORRÊNCIAS x ORGA – GRÁFICOS POR VP E DIRETORIA

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# =====================================================
# CONFIGURAÇÕES
# =====================================================
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Ocorrências")

COR_PRINCIPAL_VERDE = "#70C247"
COR_CONTRASTE = "#4CAF50"

URL_OCORRENCIAS = (
    "https://raw.githubusercontent.com/"
    "oliveirafabio8813-design/Farol-Sede-Profarma/main/"
    "Relatorio_OcorrenciasNoPonto.xlsx"
)

URL_ORGA = (
    "https://raw.githubusercontent.com/"
    "oliveirafabio8813-design/Farol-Sede-Profarma/main/"
    "ORGA_Diretoria%20e%20VP%20por%20Unidade%20Organizacional.CSV"
)

SHEET_OCORRENCIAS = "OcorrênciasnoPonto"

# =====================================================
# FUNÇÕES DE CARGA
# =====================================================
@st.cache_data(show_spinner="Carregando Ocorrências...")
def load_ocorrencias():
    r = requests.get(URL_OCORRENCIAS, timeout=30)
    r.raise_for_status()
    return pd.read_excel(io.BytesIO(r.content), sheet_name=SHEET_OCORRENCIAS)

@st.cache_data(show_spinner="Carregando estrutura organizacional...")
def load_orga():
    return pd.read_csv(URL_ORGA, sep=";", encoding="utf-8")

def e_marcacoes_impar(x):
    if pd.isna(x):
        return False
    return len(str(x).split()) % 2 != 0

# =====================================================
# CARGA DOS DADOS
# =====================================================
df_ocorr = load_ocorrencias()
df_orga = load_orga()

# =====================================================
# TRATAMENTO
# =====================================================
df_ocorr["CodigoCentroDeCusto"] = df_ocorr["CodigoCentroDeCusto"].astype(str).str.strip()
df_orga["COD UNIDADE ORGANIZACIONAL"] = df_orga["COD UNIDADE ORGANIZACIONAL"].astype(str).str.strip()

df_ocorr["Data"] = pd.to_datetime(df_ocorr["Data"], errors="coerce", dayfirst=True)
df_ocorr["is_impar"] = df_ocorr["Marcacoes"].apply(e_marcacoes_impar)
df_ocorr["is_sem_marcacao"] = df_ocorr["Ocorrencia"].isin(
    ["Sem marcação de entrada", "Sem marcação de saída"]
)

# =====================================================
# MERGE OCORRÊNCIAS x ORGA
# =====================================================
df = df_ocorr.merge(
    df_orga[["COD UNIDADE ORGANIZACIONAL", "VP", "DIRETORIA"]],
    left_on="CodigoCentroDeCusto",
    right_on="COD UNIDADE ORGANIZACIONAL",
    how="left"
)

# Métrica de falta não justificada
df["is_falta"] = (
    (df["Ocorrencia"] == "Falta") &
    (df["Justificativa"] == "Falta")
).astype(int)

# =====================================================
# HEADER
# =====================================================
st.markdown(
    f"<h1 style='color:{COR_PRINCIPAL_VERDE}'>Dashboard Profarma - Ocorrências</h1>",
    unsafe_allow_html=True
)
st.markdown("Relatório e Detalhamento de Ocorrências no Ponto")
st.markdown("---")

# =====================================================
# FILTROS
# =====================================================
st.subheader("Filtros")

col_vp, col_dir, col_est, col_dep, col_btn = st.columns([1,1,1,1,0.6])

for k in ["vp", "dir", "est", "dep"]:
    if k not in st.session_state:
        st.session_state[k] = []

with col_btn:
    st.write("")
    st.write("")
    if st.button("Limpar Filtros"):
        for k in ["vp", "dir", "est", "dep"]:
            st.session_state[k] = []

# VP
with col_vp:
    st.session_state.vp = st.multiselect(
        "VP:", sorted(df["VP"].dropna().unique()), st.session_state.vp
    )

df_f = df.copy()
if st.session_state.vp:
    df_f = df_f[df_f["VP"].isin(st.session_state.vp)]

# Diretoria
with col_dir:
    st.session_state.dir = st.multiselect(
        "Diretoria:", sorted(df_f["DIRETORIA"].dropna().unique()), st.session_state.dir
    )

if st.session_state.dir:
    df_f = df_f[df_f["DIRETORIA"].isin(st.session_state.dir)]

# Estabelecimento
with col_est:
    st.session_state.est = st.multiselect(
        "Estabelecimento:",
        sorted(df_f["Estabelecimento"].dropna().unique()),
        st.session_state.est,
    )

if st.session_state.est:
    df_f = df_f[df_f["Estabelecimento"].isin(st.session_state.est)]

# Departamento
with col_dep:
    st.session_state.dep = st.multiselect(
        "Departamento:",
        sorted(df_f["Departamento"].dropna().unique()),
        st.session_state.dep,
    )

if st.session_state.dep:
    df_f = df_f[df_f["Departamento"].isin(st.session_state.dep)]

# =====================================================
# KPIs
# =====================================================
st.markdown("---")
st.subheader("Resumo das Ocorrências")

col1, col2 = st.columns(2)
with col1:
    st.metric("Faltas Não Justificadas", int(df_f["is_falta"].sum()))
with col2:
    st.metric(
        "Marcações Ímpares / Ausentes",
        int(df_f["is_impar"].sum() + df_f["is_sem_marcacao"].sum())
    )

# =====================================================
# GRÁFICOS POR VP / DIRETORIA
# =====================================================
st.markdown("---")
st.subheader("Análise de Ocorrências por VP e Diretoria")

# --- VP ---
df_vp = df_f.groupby("VP").agg(
    Faltas=("is_falta", "sum"),
    Impares=("is_impar", "sum"),
    Sem_Marcacao=("is_sem_marcacao", "sum"),
).reset_index()

df_vp["Total"] = df_vp[["Faltas", "Impares", "Sem_Marcacao"]].sum(axis=1)
df_vp = df_vp[df_vp["Total"] > 0].sort_values("Total")

if not df_vp.empty:
    fig_vp = px.bar(
        df_vp,
        y="VP",
        x=["Faltas", "Impares", "Sem_Marcacao"],
        orientation="h",
        template="plotly_white",
        color_discrete_sequence=[COR_CONTRASTE, "#ffc107", "#17a2b8"],
        labels={"value": "Total de Ocorrências", "variable": "Tipo"}
    )
    st.plotly_chart(fig_vp, use_container_width=True)

# --- DIRETORIA ---
df_dir = df_f.groupby("DIRETORIA").agg(
    Faltas=("is_falta", "sum"),
    Impares=("is_impar", "sum"),
    Sem_Marcacao=("is_sem_marcacao", "sum"),
).reset_index()

df_dir["Total"] = df_dir[["Faltas", "Impares", "Sem_Marcacao"]].sum(axis=1)
df_dir = df_dir[df_dir["Total"] > 0].sort_values("Total")

if not df_dir.empty:
    fig_dir = px.bar(
        df_dir,
        y="DIRETORIA",
        x=["Faltas", "Impares", "Sem_Marcacao"],
        orientation="h",
        template="plotly_white",
        color_discrete_sequence=[COR_CONTRASTE, "#ffc107", "#17a2b8"],
        labels={"value": "Total de Ocorrências", "variable": "Tipo"}
    )
    st.plotly_chart(fig_dir, use_container_width=True)
