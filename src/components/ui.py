"""Estilo visual + navegação inferior (mobile-first), aproximando o app do mockup."""
import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root{
  --cofre-brand:#0E7C66; --cofre-brand-ink:#0A5A4A; --cofre-japan:#C2442E;
  --cofre-panel:#EFF3EC; --cofre-line:#DBE2D5; --cofre-faint:#8A968C;
}

html, body, [class*="css"], .stApp{
  font-family:'IBM Plex Sans', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
}

/* esconde a lista de páginas padrão da sidebar (navegamos pela barra inferior) */
[data-testid="stSidebarNav"]{ display:none; }

/* respiro no topo e espaço para a barra inferior fixa */
.block-container{ padding-top:2.4rem; padding-bottom:6.5rem; max-width:760px; }

/* KPIs como cartões */
[data-testid="stMetric"]{
  background:var(--cofre-panel); border:1px solid var(--cofre-line);
  border-radius:14px; padding:12px 14px;
}
[data-testid="stMetricValue"]{ font-weight:600; }

/* botões arredondados */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button{
  border-radius:10px; font-weight:600;
}

/* barra de navegação inferior */
.cofre-nav{
  position:fixed; left:50%; transform:translateX(-50%); bottom:0; z-index:9990;
  width:100%; max-width:760px; display:flex; justify-content:space-around; align-items:center;
  background:#FFFFFF; border-top:1px solid var(--cofre-line);
  padding:6px 8px 8px; box-shadow:0 -4px 22px -14px rgba(20,33,28,.35);
}
.cofre-nav a{
  text-decoration:none; color:var(--cofre-faint); font-size:.66rem; font-weight:600;
  display:flex; flex-direction:column; align-items:center; gap:2px; flex:1; padding:3px 0;
}
.cofre-nav a .ic{ font-size:1.18rem; line-height:1; }
.cofre-nav a.on{ color:var(--cofre-brand-ink); }
.cofre-nav a.add .plus{
  width:46px; height:46px; margin-top:-24px; border-radius:50%;
  background:var(--cofre-brand); color:#fff; display:flex; align-items:center; justify-content:center;
  font-size:1.7rem; line-height:1; box-shadow:0 6px 16px -6px rgba(14,124,102,.75);
}
.cofre-nav a.add{ color:var(--cofre-brand-ink); }
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)


# (chave, rótulo, url, ícone)
_ITEMS = [
    ("inicio", "Início", "/", "🏠"),
    ("orcamento", "Orçam.", "/Orcamento", "📊"),
    ("_add", "Lançar", "/Lancar", "＋"),
    ("metas", "Metas", "/Metas", "🎯"),
    ("mais", "Mais", "/Mais", "⚙️"),
]


def bottom_nav(active=""):
    parts = ['<div class="cofre-nav">']
    for key, label, href, icon in _ITEMS:
        if key == "_add":
            parts.append(f'<a class="add" href="{href}" target="_self">'
                         f'<span class="plus">＋</span><span>{label}</span></a>')
        else:
            cls = "on" if key == active else ""
            parts.append(f'<a class="{cls}" href="{href}" target="_self">'
                         f'<span class="ic">{icon}</span>{label}</a>')
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)
