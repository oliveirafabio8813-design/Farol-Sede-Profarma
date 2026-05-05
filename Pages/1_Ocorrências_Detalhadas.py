# pages/1_Ocorrências_Detalhadas.py
# AJUSTADO – VP / DIRETORIA VIA RAW GITHUB

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests
import io

# =====================================================
# CONFIGURAÇÕES
# =====================================================
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Ocorrências")

COR_PRINCIPAL_VERDE = "#70C247"
COR_CONTRASTE = "#4CAF50"

REPO_URL_BASE = (
    "https://raw.githubusercontent.com/"
    "oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/"
)

URL_OCORRENCIAS = REPO_URL_BASE + "Relatorio_OcorrenciasNoPonto.xlsx"
SHEET_OCORRENCIAS = "OcorrênciasnoPonto"

URL_BANCO_HORAS = REPO_URL_BASE + "Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx"
SHEET_BANCO_HORAS = "ContaCorrenteBancodeHorasResum"

URL_ORGA = (
    "https://raw.githubusercontent.com/"
    "oliveirafabio8813-design/Farol-Sede-Profarma/main/"
    "ORGA_Diretoria%20e%20VP%20por%20Unidade%20Organizacional.CSV"
)

# =====================================================
# FUNÇÕES DE CARGA
# =====================================================
@st.cache_data(show_spinner="Carregando dados do GitHub...")
def load_excel(url, sheet):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return pd.read_excel(io.BytesIO(r.content), sheet_name=sheet)

@st.cache_data(show_spinner="Carregando estrutura organizacional (VP/Diretoria)...")
def load_orga():
    return pd.read_csv(URL_ORGA, sep=";", encoding="utf-8")

def e_marcacoes_impar(marc):
    if pd.isna(marc):
        return False
    return len(str(marc).split()) % 2 != 0

def convert_to_hours(time_str):
    if pd.isna(time_str) or time_str == "00:00":
        return 0.0
    try:
        neg = str(time_str).startswith("-")
        if neg:
            time_str = str(time_str)[1:]
        h, m = map(int, str(time_str).split(":"))
        total = h + m / 60
        return -total if neg else total
    except:
        return 0.0

# =====================================================
# CARGA DAS BASES
# =====================================================
df_ocorr = load_excel(URL_OCORRENCIAS, SHEET_OCORRENCIAS)
df_banco = load_excel(URL_BANCO_HORAS, SHEET_BANCO_HORAS)
df_orga = load_orga()

# =====================================================
# TRATAMENTOS INICIAIS
# =====================================================
df_ocorr["Data"] = pd.to_datetime(df_ocorr["Data"], errors="coerce", dayfirst=True)
df_ocorr["is_impar"] = df_ocorr["Marcacoes"].apply(e_marcacoes_impar)
df_ocorr["is_sem_marcacao"] = df_ocorr["Ocorrencia"].isin(
    ["Sem marcação de entrada", "Sem marcação de saída"]
)

df_banco["SaldoFinal_Horas"] = df_banco["SaldoFinal"].apply(convert_to_hours)

# =====================================================
# PADRONIZAÇÃO DE CHAVES
# =====================================================
df_ocorr["Matricula"] = df_ocorr["Matricula"].astype(str).str.strip()
df_banco["Matricula"] = df_banco["Matricula"].astype(str).str.strip()

df_banco["COD_UNIDADE"] = (
    df_banco["Código Unidade Organizacional"]
    .astype(str)
    .str.strip()
)

df_orga["COD UNIDADE ORGANIZACIONAL"] = (
    df_orga["COD UNIDADE ORGANIZACIONAL"]
    .astype(str)
    .str.strip()
)

# =====================================================
# MERGE – BANCO + ORGA (VP / DIRETORIA)
# =====================================================
df_banco_org = df_banco.merge(
    df_orga[["COD UNIDADE ORGANIZACIONAL", "VP", "DIRETORIA"]],
    left_on="COD_UNIDADE",
    right_on="COD UNIDADE ORGANIZACIONAL",
    how="left"
)

# =====================================================
# MERGE – OCORRÊNCIAS + BANCO_ORG
# =====================================================
df = df_ocorr.merge(
    df_banco_org[
        ["Matricula", "Estabelecimento", "Departamento", "VP", "DIRETORIA"]
    ],
    on="Matricula",
    how="left"
)

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
# FILTROS (VP → DIRETORIA → ESTAB → DEP)
# =====================================================
st.subheader("Filtros")

col_vp, col_dir, col_est, col_dep, col_btn = st.columns([1,1,1,1,0.6])

for k in ["vp","dir","est","dep"]:
    if k not in st.session_state:
        st.session_state[k] = []

with col_btn:
    st.write("")
    st.write("")
    if st.button("Limpar Filtros"):
        for k in ["vp","dir","est","dep"]:
            st.session_state[k] = []

# VP
with col_vp:
    vps = sorted(df["VP"].dropna().unique())
    st.session_state.vp = st.multiselect("VP:", vps, st.session_state.vp)

df_f = df.copy()
if st.session_state.vp:
    df_f = df_f[df_f["VP"].isin(st.session_state.vp)]

# Diretoria
with col_dir:
    dirs = sorted(df_f["DIRETORIA"].dropna().unique())
    st.session_state.dir = st.multiselect("Diretoria:", dirs, st.session_state.dir)

if st.session_state.dir:
    df_f = df_f[df_f["DIRETORIA"].isin(st.session_state.dir)]

# Estabelecimento
with col_est:
    ests = sorted(df_f["Estabelecimento"].dropna().unique())
    st.session_state.est = st.multiselect("Estabelecimento:", ests, st.session_state.est)

if st.session_state.est:
    df_f = df_f[df_f["Estabelecimento"].isin(st.session_state.est)]

# Departamento
with col_dep:
    deps = sorted(df_f["Departamento"].dropna().unique())
    st.session_state.dep = st.multiselect("Departamento:", deps, st.session_state.dep)

if st.session_state.dep:
    df_f = df_f[df_f["Departamento"].isin(st.session_state.dep)]

# =====================================================
# KPIs
# =====================================================
st.markdown("---")
st.subheader("Resumo das Ocorrências (Filtros Aplicados)")

df_f["is_falta"] = (
    (df_f["Ocorrencia"] == "Falta") &
    (df_f["Justificativa"] == "Falta")
).astype(int)

col1, col2 = st.columns(2)
with col1:
    st.metric("Faltas Não Justificadas", int(df_f["is_falta"].sum()))
with col2:
    st.metric(
        "Marcações Ímpares / Ausentes",
        int(df_f["is_impar"].sum() + df_f["is_sem_marcacao"].sum())
    )
