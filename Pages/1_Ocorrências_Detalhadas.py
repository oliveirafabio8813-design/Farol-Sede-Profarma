# pages/1_Ocorrências_Detalhadas.py
# AJUSTADO – VP / DIRETORIA VIA COLA + ORGA

import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests
import io
import os

# =====================================================
# CONFIGURAÇÕES
# =====================================================
st.set_page_config(layout="wide", page_title="Dashboard Profarma - Ocorrências")

COR_PRINCIPAL_VERDE = "#70C247"
COR_CONTRASTE = "#4CAF50"

REPO_URL_BASE = "https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/"

URL_OCORRENCIAS = REPO_URL_BASE + "Relatorio_OcorrenciasNoPonto.xlsx"
SHEET_OCORRENCIAS = "OcorrênciasnoPonto"

URL_BANCO_HORAS_RESUMO = REPO_URL_BASE + "Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx"
SHEET_BANCO_HORAS = "ContaCorrenteBancodeHorasResum"

FILE_COLA = "COLA_Colaboradores_CSV_Gestor.CSV"
FILE_ORGA = "ORGA_Diretoria e VP por Unidade Organizacional.CSV"

# =====================================================
# FUNÇÕES
# =====================================================
@st.cache_data(show_spinner="Carregando dados do GitHub...")
def load_excel_github(url, sheet):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return pd.read_excel(io.BytesIO(r.content), sheet_name=sheet)

@st.cache_data(show_spinner="Carregando base de colaboradores...")
def load_cola():
    if not os.path.exists(FILE_COLA):
        st.error(f"Arquivo {FILE_COLA} não encontrado no repositório.")
        st.stop()
    return pd.read_csv(FILE_COLA, sep=";", encoding="utf-8", low_memory=False)

@st.cache_data(show_spinner="Carregando estrutura organizacional...")
def load_orga():
    if not os.path.exists(FILE_ORGA):
        st.error(f"Arquivo {FILE_ORGA} não encontrado no repositório.")
        st.stop()
    return pd.read_csv(FILE_ORGA, sep=";", encoding="utf-8")

def e_marcacoes_impar(marc):
    if pd.isna(marc):
        return False
    return len(str(marc).split()) % 2 != 0

# =====================================================
# CARGA DAS BASES
# =====================================================
df_ocorrencias = load_excel_github(URL_OCORRENCIAS, SHEET_OCORRENCIAS)
df_banco_horas = load_excel_github(URL_BANCO_HORAS_RESUMO, SHEET_BANCO_HORAS)
df_cola = load_cola()
df_orga = load_orga()

# =====================================================
# TRATAMENTOS
# =====================================================
df_ocorrencias["Data"] = pd.to_datetime(df_ocorrencias["Data"], errors="coerce", dayfirst=True)
df_ocorrencias["is_impar"] = df_ocorrencias["Marcacoes"].apply(e_marcacoes_impar)
df_ocorrencias["is_sem_marcacao"] = df_ocorrencias["Ocorrencia"].isin(
    ["Sem marcação de entrada", "Sem marcação de saída"]
)

# Padronização de chaves
df_ocorrencias["Matricula"] = df_ocorrencias["Matricula"].astype(str).str.strip()
df_cola["Matrícula"] = df_cola["Matrícula"].astype(str).str.strip()

df_cola["Código da Unidade Organizacional"] = (
    df_cola["Código da Unidade Organizacional"].astype(str).str.strip()
)
df_orga["COD UNIDADE ORGANIZACIONAL"] = (
    df_orga["COD UNIDADE ORGANIZACIONAL"].astype(str).str.strip()
)

# =====================================================
# MERGE 1 – COLA + ORGA
# =====================================================
df_cola_org = df_cola.merge(
    df_orga[["COD UNIDADE ORGANIZACIONAL", "VP", "DIRETORIA"]],
    left_on="Código da Unidade Organizacional",
    right_on="COD UNIDADE ORGANIZACIONAL",
    how="left"
)

# =====================================================
# MERGE 2 – OCORRÊNCIAS + COLA_ORG
# =====================================================
df_ocorrencias = df_ocorrencias.merge(
    df_cola_org[
        ["Matrícula", "Estabelecimento", "Unidade Organizacional", "VP", "DIRETORIA"]
    ],
    left_on="Matricula",
    right_on="Matrícula",
    how="left"
)

df_ocorrencias.rename(
    columns={"Unidade Organizacional": "Departamento"}, inplace=True
)

# =====================================================
# HEADER
# =====================================================
st.markdown(
    f"<h1 style='color:{COR_PRINCIPAL_VERDE}'>Dashboard Profarma - Ocorrências</h1>",
    unsafe_allow_html=True,
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
    vps = sorted(df_ocorrencias["VP"].dropna().unique())
    st.session_state.vp = st.multiselect("VP:", vps, st.session_state.vp)

df_filtro = df_ocorrencias.copy()
if st.session_state.vp:
    df_filtro = df_filtro[df_filtro["VP"].isin(st.session_state.vp)]

# Diretoria
with col_dir:
    dirs = sorted(df_filtro["DIRETORIA"].dropna().unique())
    st.session_state.dir = st.multiselect("Diretoria:", dirs, st.session_state.dir)

if st.session_state.dir:
    df_filtro = df_filtro[df_filtro["DIRETORIA"].isin(st.session_state.dir)]

# Estabelecimento
with col_est:
    ests = sorted(df_filtro["Estabelecimento"].dropna().unique())
    st.session_state.est = st.multiselect("Estabelecimento:", ests, st.session_state.est)

if st.session_state.est:
    df_filtro = df_filtro[df_filtro["Estabelecimento"].isin(st.session_state.est)]

# Departamento
with col_dep:
    deps = sorted(df_filtro["Departamento"].dropna().unique())
    st.session_state.dep = st.multiselect("Departamento:", deps, st.session_state.dep)

if st.session_state.dep:
    df_filtro = df_filtro[df_filtro["Departamento"].isin(st.session_state.dep)]

# =====================================================
# KPIs
# =====================================================
st.markdown("---")
st.subheader("Resumo das Ocorrências (Filtros Aplicados)")

df_filtro["is_falta_nao_justificada"] = (
    (df_filtro["Ocorrencia"] == "Falta") &
    (df_filtro["Justificativa"] == "Falta")
).astype(int)

col1, col2 = st.columns(2)

with col1:
    st.metric("Faltas Não Justificadas", int(df_filtro["is_falta_nao_justificada"].sum()))

with col2:
    st.metric(
        "Marcações Ímpares / Ausentes",
        int(df_filtro["is_impar"].sum() + df_filtro["is_sem_marcacao"].sum())
    )
