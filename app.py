import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# Page Config
st.set_page_config(page_title="Pokémon Tracker", page_icon="🎴", layout="wide")

# Connexion Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Authentification
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

# Header
st.title("🎴 Suivi d'Achat / Vente Pokémon")

# Formulaire d'ajout dans la barre latérale
with st.sidebar:
    st.header("➕ Ajouter un article")
    with st.form("add_form", clear_on_submit=True):
        type_art = st.selectbox("Type", ["Boîte", "ETB", "Display", "Carte à l'unité", "Coffret", "Autre"])
        nom = st.text_input("Nom de l'article")
        qte = st.number_input("Quantité", min_value=1, value=1)
        prix_a = st.number_input("Prix d'achat unitaire (€)", min_value=0.0, value=0.0, step=1.0)
        prix_v = st.number_input("Prix de vente unitaire (€)", min_value=0.0, value=0.0, step=1.0)
        statut = st.selectbox("Statut", ["En stock", "Vendu"])
        
        submitted = st.form_submit_button("Enregistrer")
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

# Chargement des données
response = supabase.table("inventaire").select("*").execute()
data = response.data
df = pd.DataFrame(data)

if not df.empty:
    # Calculs de base
    df["Total Achat"] = df["prixAchat"] * df["quantite"]
    df["Total Vente"] = df["prixRevente"] * df["quantite"]
    
    # --- BARRE DE RECHERCHE ET FILTRES (Au-dessus du tableau) ---
    st.subheader("🔍 Recherche & Filtres")
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        recherche_texte = st.text_input("🔎 Rechercher par nom (ex: Charizard, 151...)", "")
    with col_f2:
        filtre_types = st.multiselect("🏷️ Filtrer par Type (ex: ETB)", options=df["type"].unique(), default=[])

    # Application des filtres
    df_filtered = df.copy()
    
    if recherche_texte:
        df_filtered = df_filtered[df_filtered["nom"].str.contains(recherche_texte, case=False, na=False)]
        
    if filtre_types:
        df_filtered = df_filtered[df_filtered["type"].isin(filtre_types)]

    st.markdown("---")

    # Indicateurs (KPIs) basés sur l'affichage
    col1, col2, col3, col4 = st.columns(4)
    total_investi = df_filtered["Total Achat"].sum()
    total_revente = df_filtered["Total Vente"].sum()
    benefice_potentiel = total_revente - total_investi
    
    col1.metric("Total Investi", f"{total_investi:.2f} €")
    col2.metric("Valeur Estimée / Réelle", f"{total_revente:.2f} €")
    col3.metric("Bénéfice / Plus-value", f"{benefice_potentiel:.2f} €", delta=f"{benefice_potentiel:.2f} €")
    col4.metric("Articles affichés", int(df_filtered["quantite"].sum()))

    # Affichage du tableau
    st.subheader("📋 Inventaire")
    st.dataframe(
        df_filtered[["id", "type", "nom", "quantite", "prixAchat", "prixRevente", "Total Achat", "Total Vente", "statut"]],
        use_container_width=True,
        hide_index=True
    )

    # Graphiques
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig_type = px.pie(df_filtered, values="quantite", names="type", title="Répartition par Type")
        st.plotly_chart(fig_type, use_container_width=True)
    with col_g2:
        fig_statut = px.bar(df_filtered, x="nom", y="Total Achat", color="statut", title="Investissement par produit")
        st.plotly_chart(fig_statut, use_container_width=True)

    # Zone de suppression
    with st.expander("🗑️ Supprimer un article"):
        article_a_supprimer = st.selectbox(
            "Choisir l'article à supprimer", 
            options=df["id"].tolist(), 
            format_func=lambda x: f"ID {x} - {df[df['id']==x]['nom'].values[0]}"
        )
        if st.button("Confirmer la suppression"):
            supabase.table("inventaire").delete().eq("id", article_a_supprimer).execute()
            st.warning("Article supprimé !")
            st.rerun()

else:
    st.info("Votre inventaire est vide. Ajoutez votre premier article depuis la barre latérale !")
