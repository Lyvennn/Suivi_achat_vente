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
    st.markdown("<h1 style='text-align: center;'>🔒 Accès Protégé</h1>", unsafe_allow_html=True)
    pwd = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if pwd == MOT_DE_PASSE:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect")
    st.stop()

# Header centré
st.markdown("<h1 style='text-align: center;'>🎴 Suivi d'Achat / Vente Pokémon</h1>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Formulaire d'ajout dans la barre latérale
with st.sidebar:
    st.header("➕ Ajouter un article")
    with st.form("add_form", clear_on_submit=True):
        type_art = st.selectbox("Type", ["Boîte", "ETB", "Display", "Carte à l'unité", "Coffret", "Autre"])
        nom = st.text_input("Nom de l'article")
        qte = st.number_input("Quantité", min_value=1, value=1)
        
        prix_a = st.number_input("Prix d'achat unitaire (€)", min_value=0.0, value=None, step=1.0, placeholder="ex: 45.00")
        prix_v = st.number_input("Prix de vente unitaire (€)", min_value=0.0, value=None, step=1.0, placeholder="ex: 60.00")
        statut = st.selectbox("Statut", ["En stock", "Vendu"])
        
        submitted = st.form_submit_button("Enregistrer")
        if submitted and nom:
            nouvel_article = {
                "type": type_art,
                "nom": nom,
                "quantite": int(qte),
                "prixAchat": float(prix_a) if prix_a is not None else 0.0,
                "prixRevente": float(prix_v) if prix_v is not None else 0.0,
                "statut": statut
            }
            supabase.table("inventaire").insert(nouvel_article).execute()
            st.success("Article ajouté !")
            st.rerun()

# Chargement des données
response = supabase.table("inventaire").select("*").execute()
data = response.data
df = pd.DataFrame(data)

# Fenêtre modale (Pop-up) pour la vente
@st.dialog("🛒 Valider la vente d'un article")
def modal_vente(item):
    st.write(f"**Produit :** {item['nom']}")
    st.write(f"**Quantité actuellement en stock :** {item['quantite']}")
    
    with st.form("form_modal_vente"):
        qte_vendue = st.number_input("Quantité vendue", min_value=1, max_value=int(item['quantite']), value=int(item['quantite']))
        prix_vente_unitaire = st.number_input(
            "Prix de vente unitaire (€)", 
            min_value=0.0, 
            value=float(item['prixRevente']) if item['prixRevente'] > 0 else None, 
            placeholder="ex: 60.00",
            step=1.0
        )
        
        valider = st.form_submit_button("Confirmer la vente")
        if valider:
            p_vente = float(prix_vente_unitaire) if prix_vente_unitaire is not None else 0.0
            
            if qte_vendue == item['quantite']:
                supabase.table("inventaire").update({
                    "statut": "Vendu",
                    "prixRevente": p_vente
                }).eq("id", item['id']).execute()
            else:
                nouvelle_qte_stock = item['quantite'] - qte_vendue
                supabase.table("inventaire").update({"quantite": nouvelle_qte_stock}).eq("id", item['id']).execute()
                
                article_vendu = {
                    "type": item['type'],
                    "nom": item['nom'],
                    "quantite": int(qte_vendue),
                    "prixAchat": float(item['prixAchat']),
                    "prixRevente": p_vente,
                    "statut": "Vendu"
                }
                supabase.table("inventaire").insert(article_vendu).execute()

            st.success("Vente enregistrée !")
            st.rerun()

if not df.empty:
    # Calculs de base
    df["Total Achat"] = df["prixAchat"] * df["quantite"]
    df["Total Vente"] = df["prixRevente"] * df["quantite"]

    # --- CALCULS POUR LES METRIQUES ---
    df_stock = df[df["statut"] == "En stock"]
    df_vendus = df[df["statut"] == "Vendu"].copy()
    
    total_investi_stock = df_stock["Total Achat"].sum()
    nb_articles_stock = df_stock["quantite"].sum()
    
    total_vente_realisee = df_vendus["Total Vente"].sum()
    total_achat_vendus = df_vendus["Total Achat"].sum()
    benefice_realise = total_vente_realisee - total_achat_vendus
    
    if total_achat_vendus > 0:
        pourcentage_plus_value = (benefice_realise / total_achat_vendus) * 100
    else:
        pourcentage_plus_value = 0.0

    # --- 1. LES 4 CASES DE STATISTIQUES ---
    st.markdown("<h3 style='text-align: center;'>📊 Statistiques Générales</h3>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.container(border=True):
            st.markdown("<p style='text-align: center; color: #aaa; margin-bottom: 5px;'>Total Investi (En Stock)</p>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align: center; color: #ff9900; margin-top: 0;'>{total_investi_stock:.2f} €</h2>", unsafe_allow_html=True)

    with col2:
        with st.container(border=True):
            st.markdown("<p style='text-align: center; color: #aaa; margin-bottom: 5px;'>Articles en Stock</p>", unsafe_allow_html=True)
            st.markdown(f"<h2 style='text-align: center; color: #00bfff; margin-top: 0;'>{int(nb_articles_stock)}</h2>", unsafe_allow_html=True)

    with col3:
        with st.container(border=True):
            st.markdown("<p style='text-align: center; color: #aaa; margin-bottom: 5px;'>Plus-Value (%)</p>", unsafe_allow_html=True)
            couleur_pct = "#2e7d32" if pourcentage_plus_value >= 0 else "#c62828"
            st.markdown(f"<h2 style='text-align: center; color: {couleur_pct}; margin-top: 0;'>{pourcentage_plus_value:.1f} %</h2>", unsafe_allow_html=True)

    with col4:
        with st.container(border=True):
            st.markdown("<p style='text-align: center; color: #aaa; margin-bottom: 5px;'>Bénéfice Réel (€)</p>", unsafe_allow_html=True)
            # Vert clair vif (#00ffcc) réappliqué
            couleur_ben = "#00ffcc" if benefice_realise >= 0 else "#ff4d4d"
            st.markdown(f"<h2 style='text-align: center; color: {couleur_ben}; margin-top: 0;'>{benefice_realise:.2f} €</h2>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 2. GRAPHIQUE D'ÉVOLUTION DE LA PLUS-VALUE PAR VENTE ---
    if not df_vendus.empty:
        with st.container(border=True):
            st.subheader("📈 Évolution du Bénéfice Cumulé selon les Ventes")
            
            # Calcul du bénéfice unitaire par ligne vendue
            df_vendus["Benefice_Unitaire"] = df_vendus["Total Vente"] - df_vendus["Total Achat"]
            
            # Tri par ID (ordre chronologique de saisie/vente)
            df_vendus = df_vendus.sort_values(by="id").reset_index(drop=True)
            df_vendus["N_Vente"] = df_vendus.index + 1
            
            # Bénéfice cumulé
            df_vendus["Benefice_Cumule"] = df_vendus["Benefice_Unitaire"].cumsum()
            
            # Ajout d'un point 0 initial pour un beau tracé
            df_chart = pd.concat([
                pd.DataFrame([{"N_Vente": 0, "Benefice_Cumule": 0.0, "nom": "Départ"}]),
                df_vendus[["N_Vente", "Benefice_Cumule", "nom"]]
            ], ignore_index=True)

            fig_evo = px.line(
                df_chart, 
                x="N_Vente", 
                y="Benefice_Cumule", 
                markers=True,
                hover_data=["nom"],
                labels={"N_Vente": "Nombre de ventes effectuées", "Benefice_Cumule": "Bénéfice Cumulé (€)"}
            )
            fig_evo.update_traces(line_color="#00ffcc", line_width=3, marker=dict(size=8))
            
            # Force l'axe X à n'afficher strictement que des entiers
            fig_evo.update_xaxes(dtick=1, tick0=0)
            
            fig_evo.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
            st.plotly_chart(fig_evo, use_container_width=True)
            
    st.markdown("<br>", unsafe_allow_html=True)

    # --- 3. FILTRES EN CASES ISOLÉES ---
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        with st.container(border=True):
            recherche_texte = st.text_input("🔎 Rechercher par nom (ex: Charizard, 151...)", "")
            
    with col_f2:
        with st.container(border=True):
            filtre_types = st.multiselect("🏷️ Filtrer par Type (ex: ETB)", options=df["type"].unique(), default=[])

    # Application des filtres
    df_filtered = df.copy()
    
    if recherche_texte:
        df_filtered = df_filtered[df_filtered["nom"].str.contains(recherche_texte, case=False, na=False)]
        
    if filtre_types:
        df_filtered = df_filtered[df_filtered["type"].isin(filtre_types)]

    st.markdown("---")

    # --- 4. INVENTAIRE ---
    st.subheader("📋 Inventaire")

    # En-tête du tableau
    cols_header = st.columns([0.6, 1.2, 2.5, 0.8, 1.2, 1.2, 1.2, 1.2, 1.0, 1.0])
    headers = ["#", "Type", "Nom", "Qté", "P. Achat", "P. Vente", "Tot. Achat", "Tot. Vente", "Statut", "Action"]
    for col, h in zip(cols_header, headers):
        col.markdown(f"**{h}**")

    # Lignes du tableau
    for idx, row in df_filtered.iterrows():
        c_id, c_type, c_nom, c_qte, c_pa, c_pv, c_ta, c_tv, c_stat, c_act = st.columns([0.6, 1.2, 2.5, 0.8, 1.2, 1.2, 1.2, 1.2, 1.0, 1.0])
        
        c_id.write(f"`{row['id']}`")
        c_type.write(row['type'])
        c_nom.write(row['nom'])
        c_qte.write(row['quantite'])
        c_pa.write(f"{row['prixAchat']:.2f} €")
        c_pv.write(f"{row['prixRevente']:.2f} €")
        c_ta.write(f"{row['Total Achat']:.2f} €")
        c_tv.write(f"{row['Total Vente']:.2f} €")
        
        if row['statut'] == "En stock":
            c_stat.markdown("🟢 En stock")
            if c_act.button("🛒", key=f"sell_btn_{row['id']}", help="Vendre cet article"):
                modal_vente(row.to_dict())
        else:
            c_stat.markdown("🔴 Vendu")
            if c_act.button("↩️", key=f"undo_btn_{row['id']}", help="Annuler la vente et remettre en stock"):
                supabase.table("inventaire").update({
                    "statut": "En stock",
                    "prixRevente": 0.0
                }).eq("id", row['id']).execute()
                st.success("Article remis en stock !")
                st.rerun()

    # Zone de suppression
    st.markdown("---")
    with st.expander("🗑️ Supprimer un article"):
        article_a_supprimer = st.selectbox(
            "Choisir l'article à supprimer", 
            options=df["id"].tolist(), 
            format_func=lambda x: f"ID {x} - {df[df['id']==x]['nom'].values[0]}",
            key="select_delete"
        )
        if st.button("Confirmer la suppression"):
            supabase.table("inventaire").delete().eq("id", article_a_supprimer).execute()
            st.warning("Article supprimé !")
            st.rerun()

    # Graphiques complémentaires en bas
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        fig_type = px.pie(df_filtered, values="quantite", names="type", title="Répartition par Type")
        st.plotly_chart(fig_type, use_container_width=True)
    with col_g2:
        fig_statut = px.bar(df_filtered, x="nom", y="Total Achat", color="statut", title="Investissement par produit")
        st.plotly_chart(fig_statut, use_container_width=True)

else:
    st.info("Votre inventaire est vide. Ajoutez votre premier article depuis la barre latérale !")
