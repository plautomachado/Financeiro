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
  --cofre-panel:#EFF3EC; --cofre-line:#DBE2D5; --cofre-faint:#8A968C;
}

html, body, [class*="css"], .stApp{
  font-family:'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}

/* esconde a lista de páginas padrão da sidebar (usamos a barra inferior) */
[data-testid="stSidebarNav"]{ display:none; }

/* remove a moldura do Streamlit Cloud: toolbar/Fork/GitHub (topo) e badge/manage (rodapé) */
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
.block-container{ padding-top:2.4rem; padding-bottom:6.5rem; max-width:760px; }

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
  position:fixed !important; left:50%; transform:translateX(-50%); bottom:0; z-index:999999;
  width:100%; max-width:760px; background:#FFFFFF; border-top:1px solid var(--cofre-line);
  /* padding-right maior reserva o canto pro badge do Streamlit não cobrir o "Mais" */
  padding:4px 60px 6px 4px; box-shadow:0 -4px 22px -14px rgba(20,33,28,.35);
}
/* mantém os 5 itens lado a lado (o Streamlit empilha colunas no celular) */
.st-key-cofre_nav [data-testid="stHorizontalBlock"]{
  flex-direction:row !important; flex-wrap:nowrap !important; gap:0 !important; align-items:center;
}
.st-key-cofre_nav [data-testid="stColumn"]{
  flex:1 1 0 !important; width:auto !important; min-width:0 !important;
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
    """Barra inferior com navegação nativa (mantém a sessão ativa)."""
    with st.container(key="cofre_nav"):
        cols = st.columns(5)
        for col, (path, label, icon) in zip(cols, _PAGES):
            with col:
                st.page_link(path, label=label, icon=icon)
