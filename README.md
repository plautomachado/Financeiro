# Cofre — App de finanças da família 💰

App web (Streamlit + Supabase) para o controle financeiro da família entre **Brasil e Japão**, em **R$ e ¥**.
Simples para lançar no dia a dia pelo celular, completo para analisar. Foco em duas metas: **reserva de emergência** e **entrada da casa**.

> Fase 1 (MVP) em construção. Desenho completo: veja o documento de arquitetura.

## Pré-requisitos
- Python 3.11+
- Conta no [Supabase](https://supabase.com) (plano free)

## 1. Banco de dados (Supabase)
1. Crie um projeto no Supabase.
2. **SQL Editor** → cole e rode [`src/db/schema.sql`](src/db/schema.sql) (tabelas + RLS).
3. **Authentication → Users** → crie o seu login (e-mail/senha).
4. **SQL Editor** → rode [`src/db/seed.sql`](src/db/seed.sql) (cria família, categorias e metas; vincula o seu login).
   - Ajuste a **taxa de câmbio** e o **e-mail** no topo do seed se necessário.

## 2. Configuração local
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
```
Copie `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` e preencha
`SUPABASE_URL` e `SUPABASE_ANON_KEY` (em **Supabase → Project Settings → API**).

## 3. Rodar
```bash
streamlit run app.py
```

## Segurança
- **Nunca** comite `.streamlit/secrets.toml` nem `.env` (já no `.gitignore`).
- Acesso protegido por login (Supabase Auth) + **Row Level Security**: cada família só enxerga os próprios dados.
- A chave `service_role` (admin) nunca vai para o app — apenas scripts locais.

## Estrutura
```
cofre/
├── app.py                # entrada · login · navegação
├── pages/                # Dashboard · Lançar · Orçamento · Metas · Mais
├── src/
│   ├── config/           # settings · constantes
│   ├── db/               # client Supabase · schema.sql · seed.sql
│   ├── models/           # dataclasses
│   ├── services/         # regras de negócio (transações, orçamento, metas, câmbio)
│   ├── components/       # blocos de UI (KPIs, gráficos, formulários, navegação)
│   └── utils/            # formatação (R$/¥) · datas · cálculos
└── tests/
```

## Fases
- **Fase 1 (MVP):** auth · 3 membros · contas · categorias · receitas/despesas · lançamento rápido · BRL+JPY · dashboard · orçamento mensal · reserva + entrada da casa.
- **Fase 2:** cartões · parcelamentos · recorrências · patrimônio · câmbio automático · relatórios.
- **Fase 3:** importação de extratos · categorização automática · lançamento por texto · insights · simulações.
