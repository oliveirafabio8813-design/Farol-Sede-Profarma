import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import requests
import io
import os

# ===============================
# CONFIGURAÇÕES GERAIS
# ===============================
st.set_page_config(
    layout="wide",
    page_title="Dashboard Profarma - Ocorrências"
)

COR_PRINCIPAL_VERDE = "#70C247"
COR_CONTRASTE = "#4CAF50"

REPO_URL_BASE = 'https://raw.githubusercontent.com/oliveirafabio8813-design/meu-dashboard-profarma/main/Dashboard/'

URL_OCORRENCIAS = REPO_URL_BASE + 'Relatorio_OcorrenciasNoPonto.xlsx'
SHEET_OCORRENCIAS = 'OcorrênciasnoPonto'

URL_BANCO_HORAS_RESUMO = REPO_URL_BASE + 'Relatorio_ContaCorrenteBancoDeHorasResumo.xlsx'
SHEET_BANCO_HORAS = 'ContaCorrenteBancodeHorasResum'

FILE_ORGA_VP_DIR = 'ORGA_Diretoria e VP por Unidade Organizacional.CSV'


# ===============================
# FUNÇÕES DE CARGA
# ===============================
@st.cache_data(show_spinner="Carregando dados do GitHub...")
def load_data_from_github(url, sheet_name):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return pd.read_excel(io.BytesIO(response.content), sheet_name=sheet_name)


@st.cache_data(show_spinner="Carregando estrutura VP/Diretoria...")
def load_orga_data():
    df = pd.read_csv(FILE_ORGA_VP_DIR, sep=';', encoding='utf-8')
    df.columns = df.columns.str.strip()
    return df


def e_marcacoes_impar(marcacoes):
    if pd.isna(marcacoes):
        return False
    return len(str(marcacoes).split()) % 2 != 0


# ===============================
# CARGA E PROCESSAMENTO
# ===============================
df_ocorrencias = load_data_from_github(URL_OCORRENCIAS, SHEET_OCORRENCIAS)

df_ocorrencias['Data'] = pd.to_datetime(
    df_ocorrencias['Data'], errors='coerce', dayfirst=True
)

df_ocorrencias['is_impar'] = df_ocorrencias['Marcacoes'].apply(e_marcacoes_impar)
df_ocorrencias['is_sem_marcacao'] = df_ocorrencias['Ocorrencia'].isin(
    ['Sem marcação de entrada', 'Sem marcação de saída']
)

df_orga = load_orga_data()
df_orga = df_orga.rename(columns={
    'DESCRICAO UNIDADE ORGANIZACIONAL': 'Departamento'
})

df_ocorrencias = df_ocorrencias.merge(
    df_orga[['Departamento', 'VP', 'DIRETORIA']],
    on='Departamento',
    how='left'
)


# ===============================
# HEADER
# ===============================
col_logo, col_title, _ = st.columns([1, 4, 1])
with col_logo:
    st.image("image_ccccb7.png", width=110)

with col_title:
    st.markdown(
        f"<h1 style='color:{COR_PRINCIPAL_VERDE};'>Dashboard Profarma - Ocorrências</h1>",
        unsafe_allow_html=True
    )
    st.markdown("Relatório e Detalhamento de Ocorrências no Ponto")

st.markdown("---")


# ===============================
# FILTROS
# ===============================
st.subheader("Filtros")

col_vp, col_dir, col_est, col_dep, col_btn = st.columns([1,1,1,1,0.6])

for key in [
    'selected_vp',
    'selected_diretoria',
    'selected_establishment',
    'selected_department'
]:
    if key not in st.session_state:
        st.session_state[key] = []


def reset_filters():
    for key in st.session_state:
        st.session_state[key] = []


with col_btn:
    st.write("")
    st.write("")
    st.button("Limpar Filtros", on_click=reset_filters, use_container_width=True)


# --- VP ---
with col_vp:
    vps = sorted(df_ocorrencias['VP'].dropna().unique())
    st.multiselect("VP:", vps, key="selected_vp")

df_filtro = df_ocorrencias.copy()
if st.session_state.selected_vp:
    df_filtro = df_filtro[df_filtro['VP'].isin(st.session_state.selected_vp)]

# --- Diretoria ---
with col_dir:
    dirs = sorted(df_filtro['DIRETORIA'].dropna().unique())
    st.session_state.selected_diretoria = [
        d for d in st.session_state.selected_diretoria if d in dirs
    ]
    st.multiselect("Diretoria:", dirs, key="selected_diretoria")

if st.session_state.selected_diretoria:
    df_filtro = df_filtro[
        df_filtro['DIRETORIA'].isin(st.session_state.selected_diretoria)
    ]

# --- Estabelecimento ---
with col_est:
    estabs = sorted(df_filtro['Estabelecimento'].unique())
    st.multiselect("Estabelecimento:", estabs, key="selected_establishment")

if st.session_state.selected_establishment:
    df_filtro = df_filtro[
        df_filtro['Estabelecimento'].isin(st.session_state.selected_establishment)
    ]

# --- Departamento ---
with col_dep:
    deps = sorted(df_filtro['Departamento'].unique())
    st.session_state.selected_department = [
        d for d in st.session_state.selected_department if d in deps
    ]
    st.multiselect("Departamento:", deps, key="selected_department")

if st.session_state.selected_department:
    df_filtro = df_filtro[
        df_filtro['Departamento'].isin(st.session_state.selected_department)
    ]


# ===============================
# KPIs
# ===============================
df_filtro['is_falta'] = (
    (df_filtro['Ocorrencia'] == 'Falta') &
    (df_filtro['Justificativa'] == 'Falta')
).astype(int)

st.markdown("---")
st.subheader("Resumo das Ocorrências")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Faltas Não Justificadas", int(df_filtro['is_falta'].sum()))

with col2:
    st.metric("Marcações Ímpares", int(df_filtro['is_impar'].sum()))

with col3:
    st.metric(
        "Sem Marcação",
        int(df_filtro['is_sem_marcacao'].sum())
    )


# ===============================
# GRÁFICO
# ===============================
st.markdown("---")
st.subheader("Ocorrências por Departamento")

df_chart = df_filtro.groupby("Departamento").agg(
    Faltas=('is_falta', 'sum'),
    Ímpares=('is_impar', 'sum'),
    Sem_Marcação=('is_sem_marcacao', 'sum')
).reset_index()

df_chart['Total'] = df_chart[['Faltas','Ímpares','Sem_Marcação']].sum(axis=1)
df_chart = df_chart[df_chart['Total'] > 0].sort_values("Total")

if not df_chart.empty:
    fig = px.bar(
        df_chart,
        y="Departamento",
        x=["Faltas", "Ímpares", "Sem_Marcação"],
        orientation="h",
        height=min(len(df_chart) * 40 + 100, 700),
        template="plotly_white",
        color_discrete_sequence=[COR_CONTRASTE, "#ffc107", "#17a2b8"]
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhuma ocorrência para os filtros selecionados.")
