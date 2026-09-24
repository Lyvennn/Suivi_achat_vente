import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# Connexion à Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Mot de passe d'accès
MOT_DE_PASSE = "Secret123"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.title("🔒 Accès Protégé")
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if pwd == MOT_DE_PASSE:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect")
    st.stop()

st.title("📦 Suivi Achat / Vente Pokémon")

# Récupération des données depuis Supabase
response = supabase.table("inventaire").select("*").execute()
df = pd.DataFrame(response.data)

# Formulaire d'ajout dans la barre latérale
with st.sidebar.form("add_form", clear_on_submit=True):
    st.subheader("Ajouter un article")
    type_art = st.selectbox("Type", ["Boîte", "ETB", "Display", "Carte", "Autre"])
    nom = st.text_input("Nom du produit")
    qte = st.number_input("Quantité", min_value=1, value=1)
    prix_a = st.number_input("Prix d'achat (€)", min_value=0.0, value=0.0)
    prix_v = st.number_input("Prix de revente (€)", min_value=0.0, value=0.0)
    statut = st.selectbox("Statut", ["En stock", "Vendu"])
    
    submitted = st.form_submit_button("Ajouter")
    if submitted and nom:
        nouvel_article = {
            "type": type_art,
            "nom": nom,
            "quantite": int(qte),
            "prixAchat": float(prix_a),
            "prixRevente": float(prix_v),
            "statut": statut
        }
        supabase.table("inventaire").insert(nouvel_article).execute()
        st.success("Article ajouté !")
        st.rerun()

# Affichage du tableau et des métriques
if not df.empty:
    st.dataframe(df, use_container_width=True)
    
    col1, col2 = st.columns(2)
    total_achat = (df["prixAchat"] * df["quantite"]).sum()
    total_vente = (df["prixRevente"] * df["quantite"]).sum()
    col1.metric("Total Investi", f"{total_achat:.2f} €")
    col2.metric("Valeur Totale Revente", f"{total_vente:.2f} €")
    
    fig = px.bar(df, x="nom", y="quantite", color="statut", title="Répartition du stock")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Aucun produit enregistré pour le moment.")
