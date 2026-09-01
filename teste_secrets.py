import streamlit as st

st.write("URL encontrada:", st.secrets.get("SUPABASE_URL"))
st.write(
    "KEY encontrada:",
    "SIM" if st.secrets.get("SUPABASE_ANON_KEY") else "NÃO"
)