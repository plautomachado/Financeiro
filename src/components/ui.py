"""Estilo visual + navegação inferior (mobile-first).

A navegação usa st.page_link (nativa do Streamlit): troca de página SEM recarregar,
o que mantém a sessão/login ativos. Links HTML puros recarregavam tudo e deslogavam.
"""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root{
  --cofre-brand:#0E7C66; --cofre-brand-ink:#0A5A4A; --cofre-japan:#C2442E;
  --cofre-brand-soft:#DDEFE8;
  --cofre-panel:#EFF3EC; --cofre-line:#DBE2D5; --cofre-faint:#8A968C;
}

html, body, [class*="css"], .stApp{
  font-family:'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}

/* esconde a lista de páginas padrão da sidebar (usamos a barra inferior) */
[data-testid="stSidebarNav"]{ display:none; }

/* remove a moldura do Streamlit Cloud: header/toolbar/Fork/GitHub (topo) e badge/manage (rodapé) */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stToolbarActions"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
[data-testid="stMainMenu"],
#MainMenu,
.stAppDeployButton,
[data-testid="stAppDeployButton"],
[data-testid="manage-app-button"],
[data-testid="stAppViewBadge"],
[class*="viewerBadge"],
[class*="_profileContainer"],
[class*="_terminalButton"],
a[href*="streamlit.io"],
a[href*="share.streamlit.io"]{ display:none !important; }

/* respiro no topo e espaço para a barra inferior fixa */
.block-container{ padding-top:5rem; padding-bottom:3rem; max-width:760px; }

/* KPIs em grade 2 colunas (estilo mockup) */
.kpi-grid{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:4px 0 2px; }
.kpi{ background:var(--cofre-panel); border:1px solid var(--cofre-line); border-radius:14px; padding:11px 13px; }
.kpi-l{ font-size:.62rem; text-transform:uppercase; letter-spacing:.05em; color:var(--cofre-faint); font-weight:600; }
.kpi-v{ font-family:'IBM Plex Mono', ui-monospace, monospace; font-weight:600; font-size:1.3rem; margin-top:3px; letter-spacing:-.02em; }
.kpi-hero{ grid-column:1 / -1; background:var(--cofre-brand-soft); border-color:var(--cofre-brand); }
.kpi-hero .kpi-v{ color:var(--cofre-brand-ink); font-size:1.7rem; }

/* cartões de insight (relatório) */
.insight{ display:flex; gap:10px; align-items:flex-start; background:var(--cofre-panel);
  border:1px solid var(--cofre-line); border-radius:12px; padding:10px 13px; margin-bottom:8px; font-size:.93rem; }
.insight .ie{ font-size:1.15rem; line-height:1.3; flex:none; }

/* KPIs como cartões */
[data-testid="stMetric"]{
  background:var(--cofre-panel); border:1px solid var(--cofre-line);
  border-radius:14px; padding:12px 14px;
}
[data-testid="stMetricValue"]{ font-weight:600; font-family:'IBM Plex Mono', ui-monospace, monospace; letter-spacing:-.02em; }
[data-testid="stMetricLabel"] p{ font-size:.72rem; text-transform:uppercase; letter-spacing:.04em; color:var(--cofre-faint); }

/* botões arredondados */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button{
  border-radius:10px; font-weight:600;
}

/* campos arredondados + controles em pílula (mais perto do mockup) */
.stTextInput input, .stNumberInput input, .stDateInput input,
[data-baseweb="select"] > div, [data-baseweb="input"]{ border-radius:10px !important; }
[data-testid="stSegmentedControl"] button{ border-radius:9px !important; }

/* ---- barra de navegação inferior (container com key="cofre_nav") ---- */
.st-key-cofre_nav{
  /* menu no TOPO (evita o badge do Streamlit, que fica no rodapé) */
  position:fixed !important; left:50%; transform:translateX(-50%); top:0; z-index:999999;
  width:100% !important; max-width:760px; background:#FFFFFF;
  border-bottom:1px solid var(--cofre-line); border-radius:0 0 16px 16px;
  padding:8px 4px 6px; box-shadow:0 8px 24px -14px rgba(20,33,28,.4);
}
/* mantém os 5 itens lado a lado (o Streamlit empilha colunas no celular) */
/* especificidade dobrada: vence a classe do Streamlit e força a largura total */
/* o PRÓPRIO container vira uma LINHA com 5 itens iguais (filhos diretos) */
.st-key-cofre_nav.st-key-cofre_nav{
  width:100% !important; max-width:760px !important;
  display:flex !important; flex-direction:row !important; flex-wrap:nowrap !important;
  justify-content:space-around !important; align-items:center; gap:0 !important;
}
.st-key-cofre_nav > [data-testid="stElementContainer"]{
  flex:1 1 0 !important; width:20% !important; min-width:0 !important; max-width:20% !important;
}
.st-key-cofre_nav a{
  display:flex !important; flex-direction:column !important; align-items:center; justify-content:center;
  gap:1px; width:100%; padding:5px 0; text-align:center; border-radius:10px;
  font-size:.6rem !important; line-height:1.1;
  color:var(--cofre-faint) !important; text-decoration:none !important;
}
.st-key-cofre_nav a:hover{ background:var(--cofre-panel); color:var(--cofre-brand-ink) !important; }
.st-key-cofre_nav a[aria-current="page"]{ color:var(--cofre-brand-ink) !important; }
.st-key-cofre_nav a p{ margin:0 !important; font-size:.6rem !important; font-weight:600; }
.st-key-cofre_nav a > span:first-child,
.st-key-cofre_nav a [data-testid="stIconMaterial"]{ font-size:1.1rem !important; line-height:1; }
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


# (caminho do arquivo, rótulo, ícone)
_PAGES = [
    ("app.py", "Início", "🏠"),
    ("pages/2_Orcamento.py", "Orçam.", "📊"),
    ("pages/1_Lancar.py", "Lançar", "➕"),
    ("pages/3_Metas.py", "Metas", "🎯"),
    ("pages/4_Mais.py", "Mais", "⚙️"),
]


def bottom_nav(active=""):
    """Barra de menu (topo) com navegação nativa (mantém a sessão ativa)."""
    with st.container(key="cofre_nav"):
        for path, label, icon in _PAGES:
            st.page_link(path, label=label, icon=icon)
