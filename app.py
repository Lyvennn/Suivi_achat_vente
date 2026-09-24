import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from supabase import create_client
from datetime import datetime

# Page Config
st.set_page_config(page_title="Suivi d'Achat / Vente", page_icon="🎴", layout="wide")

# CSS personnalisé : Effet Arc-en-Ciel (> 200%) + Centrage + Espacement vertical de 8px
st.markdown("""
<style>
@keyframes rainbow_animation {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.rainbow-text {
    background: linear-gradient(124deg, #ff2400, #e81d1d, #e8b71d, #1de840, #1ddde8, #2b1de8, #dd00f3, #dd00f3);
    background-size: 180% 180%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: rainbow_animation 3s ease infinite;
    font-weight: bold;
}
.cell-center {
    display: flex;
    justify-content: center;
    align-items: center;
    text-align: center;
    width: 100%;
    min-height: 60px;
    padding-top: 4px;
    padding-bottom: 4px;
}
/* Alignement du bouton Streamlit au centre de sa colonne */
div[data-testid="stColumn"] > div {
    display: flex;
    justify-content: center;
    align-items: center;
}
</style>
""", unsafe_allow_html=True)

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
st.markdown("<h1 style='text-align: center;'>🎴 Suivi d'Achat / Vente</h1>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Liste des types d'articles personnalisée
TYPES_ARTICLES = [
    "Display Booster",
    "Display Mini Tins",
    "Display Bundle",
    "UPC",
    "SPC",
    "ETB",
    "Bundle",
    "Mini Tins",
    "Pokébox",
    "Tripack",
    "Duopack",
    "Artset Mini Tins",
    "Artset Boosters",
    "Booster",
    "Coffret Classeur",
    "Coffret Poster",
    "Coffret Sticker",
    "Coffret",
    "Carte Raw",
    "Carte Gradée",
    "Lot",
    "Autres"
]

# Formulaire d'ajout dans la barre latérale
with st.sidebar:
    st.header("➕ Ajouter un article")
    with st.form("add_form", clear_on_submit=True):
        type_art = st.selectbox("Type", TYPES_ARTICLES)
        nom = st.text_input("Nom de l'article")
        qte = st.number_input("Quantité", min_value=1, value=1)
        
        statut = st.selectbox("Statut", ["En stock", "Vendu"])
        
        prix_a = st.number_input("Prix d'achat unitaire (€)", min_value=0.0, value=None, step=1.0, placeholder="ex: 45.00 (ou 0)")
        prix_v = st.number_input("Prix de vente unitaire réel (€)", min_value=0.0, value=None, step=1.0, placeholder="ex: 60.00 (si déjà vendu)")
        img_url = st.text_input("Lien de l'image (URL optionnel)", placeholder="https://...")
        
        submitted = st.form_submit_button("Enregistrer")
        if submitted and nom:
            nouvel_article = {
                "type": type_art,
                "nom": nom,
                "quantite": int(qte),
                "prixAchat": float(prix_a) if prix_a is not None else 0.0,
                "prixRevente": float(prix_v) if prix_v is not None else 0.0,
                "statut": statut,
                "image_url": img_url if img_url else None
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
            "Prix de vente unitaire réel (€)", 
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
                    "statut": "Vendu",
                    "image_url": item.get('image_url')
                }
                supabase.table("inventaire").insert(article_vendu).execute()

            st.success("Vente enregistrée !")
            st.rerun()

if not df.empty:
    # Calculs de base
    df["Total Achat"] = df["prixAchat"] * df["quantite"]
    df["Total Vente"] = df["prixRevente"] * df["quantite"]

    # --- CALCULS POUR LES METRIQUES ---
    df_stock_global = df[df["statut"] == "En stock"]
    df_vendus_global = df[df["statut"] == "Vendu"].copy()
    
    total_investi_stock = df_stock_global["Total Achat"].sum()
    nb_articles_stock = df_stock_global["quantite"].sum()
    
    total_vente_realisee = df_vendus_global["Total Vente"].sum()
    total_achat_vendus = df_vendus_global["Total Achat"].sum()
    benefice_realise = total_vente_realisee - total_achat_vendus
    
    # Calcul de la Plus-Value Moyenne (%)
    if not df_vendus_global.empty:
        df_vendus_payants = df_vendus_global[df_vendus_global["prixAchat"] > 0].copy()
        if not df_vendus_payants.empty:
            df_vendus_payants["Marge_Pct"] = df_vendus_payants.apply(
                lambda r: ((r["prixRevente"] - r["prixAchat"]) / r["prixAchat"] * 100),
                axis=1
            )
            pourcentage_plus_value_moyen = df_vendus_payants["Marge_Pct"].mean()
        else:
            pourcentage_plus_value_moyen = 0.0
    else:
        pourcentage_plus_value_moyen = 0.0

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
            st.markdown("<p style='text-align: center; color: #aaa; margin-bottom: 5px;'>Plus-Value Moyenne (%)</p>", unsafe_allow_html=True)
            couleur_pct = "#00e676" if pourcentage_plus_value_moyen >= 0 else "#ff4d4d"
            st.markdown(f"<h2 style='text-align: center; color: {couleur_pct}; margin-top: 0;'>{pourcentage_plus_value_moyen:.1f} %</h2>", unsafe_allow_html=True)

    with col4:
        with st.container(border=True):
            st.markdown("<p style='text-align: center; color: #aaa; margin-bottom: 5px;'>Bénéfice Réel (€)</p>", unsafe_allow_html=True)
            couleur_ben = "#00ffcc" if benefice_realise >= 0 else "#ff4d4d"
            st.markdown(f"<h2 style='text-align: center; color: {couleur_ben}; margin-top: 0;'>{benefice_realise:.2f} €</h2>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 2. GRAPHIQUE D'ÉVOLUTION DE LA PLUS-VALUE PAR VENTE ---
    if not df_vendus_global.empty:
        with st.container(border=True):
            date_debut = datetime(2025, 1, 1)
            maintenant = datetime.now()
            
            nb_jours = max((maintenant - date_debut).days, 1)
            nb_mois = max(nb_jours / 30.4375, 0.1)
            nb_annees = max(nb_jours / 365.25, 0.01)
            
            gain_par_mois = benefice_realise / nb_mois
            gain_par_an = benefice_realise / nb_annees

            col_t1, col_t2 = st.columns([1.5, 1])
            with col_t1:
                st.subheader("📈 Évolution du Bénéfice Cumulé")
            with col_t2:
                st.markdown(
                    f"<div style='text-align: right; color: #aaa; font-size: 0.9em; padding-top: 5px;'>"
                    f"Gain mensuel : <b style='color: #00ffcc;'>{gain_par_mois:.2f} €</b> | "
                    f"Gain annuel : <b style='color: #00ffcc;'>{gain_par_an:.2f} €</b>"
                    f"</div>", 
                    unsafe_allow_html=True
                )

            df_vendus_chart = df_vendus_global.copy()
            df_vendus_chart["Benefice_Unitaire"] = df_vendus_chart["Total Vente"] - df_vendus_chart["Total Achat"]
            df_vendus_chart = df_vendus_chart.sort_values(by="id").reset_index(drop=True)
            df_vendus_chart["N_Vente"] = df_vendus_chart.index + 1
            df_vendus_chart["Benefice_Cumule"] = df_vendus_chart["Benefice_Unitaire"].cumsum()
            
            df_chart = pd.concat([
                pd.DataFrame([{"N_Vente": 0, "Benefice_Cumule": 0.0, "nom": "Départ"}]),
                df_vendus_chart[["N_Vente", "Benefice_Cumule", "nom"]]
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
            fig_evo.update_xaxes(dtick=1, tick0=0)
            fig_evo.update_layout(height=300, margin=dict(l=20, r=20, t=10, b=20))
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

    # --- 4. TABLEAU INVENTAIRE (ARTICLES EN STOCK) ---
    st.subheader("📋 Inventaire (En Stock)")
    df_stock_display = df_filtered[df_filtered["statut"] == "En stock"]

    if not df_stock_display.empty:
        cols_header = st.columns([0.5, 0.9, 1.0, 2.0, 0.5, 0.9, 0.9, 0.9, 0.8])
        headers = ["#", "Visuel", "Type", "Nom", "Qté", "P. Achat", "Tot. Achat", "Statut", "Action"]
        for col, h in zip(cols_header, headers):
            col.markdown(f"<div class='cell-center'><b>{h}</b></div>", unsafe_allow_html=True)

        for idx, row in df_stock_display.iterrows():
            c_id, c_img, c_type, c_nom, c_qte, c_pa, c_ta, c_stat, c_act = st.columns([0.5, 0.9, 1.0, 2.0, 0.5, 0.9, 0.9, 0.9, 0.8])
            
            c_id.markdown(f"<div class='cell-center'><code>{row['id']}</code></div>", unsafe_allow_html=True)
            
            if pd.notna(row.get('image_url')) and str(row['image_url']).strip() != "":
                c_img.markdown(f"<div class='cell-center'><img src='{row['image_url']}' width='60' style='border-radius: 4px;'/></div>", unsafe_allow_html=True)
            else:
                c_img.markdown("<div class='cell-center'>🖼️ -</div>", unsafe_allow_html=True)

            c_type.markdown(f"<div class='cell-center'>{row['type']}</div>", unsafe_allow_html=True)
            c_nom.markdown(f"<div class='cell-center'>{row['nom']}</div>", unsafe_allow_html=True)
            c_qte.markdown(f"<div class='cell-center'>{row['quantite']}</div>", unsafe_allow_html=True)
            c_pa.markdown(f"<div class='cell-center'>{row['prixAchat']:.2f} €</div>", unsafe_allow_html=True)
            c_ta.markdown(f"<div class='cell-center'>{row['Total Achat']:.2f} €</div>", unsafe_allow_html=True)
            c_stat.markdown("<div class='cell-center'>🟢 En stock</div>", unsafe_allow_html=True)
            
            with c_act:
                if st.button("🛒", key=f"sell_btn_{row['id']}", help="Vendre cet article"):
                    modal_vente(row.to_dict())
    else:
        st.info("Aucun article en stock correspondant à la recherche.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 5. TABLEAU HISTORIQUE DES VENTES ---
    df_vendu_display = df_filtered[df_filtered["statut"] == "Vendu"].copy()
    
    with st.expander(f"📜 Historique des Ventes ({len(df_vendu_display)} article(s) vendu(s))", expanded=False):
        if not df_vendu_display.empty:
            df_vendu_display["Marge_Calc"] = df_vendu_display.apply(
                lambda r: ((r["prixRevente"] - r["prixAchat"]) / r["prixAchat"] * 100) if r["prixAchat"] > 0 else -1.0,
                axis=1
            )
            max_marge_val = df_vendu_display["Marge_Calc"].max()

            cols_header_v = st.columns([0.5, 0.9, 0.9, 1.8, 0.5, 0.8, 0.8, 0.9, 0.8, 0.8, 0.8])
            headers_v = ["#", "Visuel", "Type", "Nom", "Qté", "P. Achat", "P. Vente", "Marge (%)", "Tot. Vente", "Statut", "Action"]
            for col, h in zip(cols_header_v, headers_v):
                col.markdown(f"<div class='cell-center'><b>{h}</b></div>", unsafe_allow_html=True)

            for idx, row in df_vendu_display.iterrows():
                c_id, c_img, c_type, c_nom, c_qte, c_pa, c_pv, c_marge, c_tv, c_stat, c_act = st.columns([0.5, 0.9, 0.9, 1.8, 0.5, 0.8, 0.8, 0.9, 0.8, 0.8, 0.8])
                
                p_achat = row['prixAchat']
                marge_pct = row["Marge_Calc"]
                
                couronne_str = " 👑" if (p_achat > 0 and marge_pct == max_marge_val and max_marge_val > 0) else ""

                c_id.markdown(f"<div class='cell-center'><code>{row['id']}</code></div>", unsafe_allow_html=True)
                
                if pd.notna(row.get('image_url')) and str(row['image_url']).strip() != "":
                    c_img.markdown(f"<div class='cell-center'><img src='{row['image_url']}' width='60' style='border-radius: 4px;'/></div>", unsafe_allow_html=True)
                else:
                    c_img.markdown("<div class='cell-center'>🖼️ -</div>", unsafe_allow_html=True)

                c_type.markdown(f"<div class='cell-center'>{row['type']}</div>", unsafe_allow_html=True)
                c_nom.markdown(f"<div class='cell-center'>{row['nom']}</div>", unsafe_allow_html=True)
                c_qte.markdown(f"<div class='cell-center'>{row['quantite']}</div>", unsafe_allow_html=True)
                c_pa.markdown(f"<div class='cell-center'>{row['prixAchat']:.2f} €</div>", unsafe_allow_html=True)
                c_pv.markdown(f"<div class='cell-center'>{row['prixRevente']:.2f} €</div>", unsafe_allow_html=True)
                
                if p_achat == 0:
                    c_marge.markdown("<div class='cell-center'><span style='color: #aaa; font-style: italic;'>N/A</span></div>", unsafe_allow_html=True)
                elif marge_pct > 200:
                    c_marge.markdown(f"<div class='cell-center'><span class='rainbow-text'>{marge_pct:+.1f} %</span>{couronne_str}</div>", unsafe_allow_html=True)
                elif 100 <= marge_pct <= 200:
                    c_marge.markdown(f"<div class='cell-center'><span style='color: #ffd700; font-weight: bold;'>{marge_pct:+.1f} %</span>{couronne_str}</div>", unsafe_allow_html=True)
                elif 75 <= marge_pct < 100:
                    c_marge.markdown(f"<div class='cell-center'><span style='color: #69f0ae; font-weight: bold;'>{marge_pct:+.1f} %</span>{couronne_str}</div>", unsafe_allow_html=True)
                elif 50 <= marge_pct < 75:
                    c_marge.markdown(f"<div class='cell-center'><span style='color: #00e676; font-weight: bold;'>{marge_pct:+.1f} %</span>{couronne_str}</div>", unsafe_allow_html=True)
                elif 25 <= marge_pct < 50:
                    c_marge.markdown(f"<div class='cell-center'><span style='color: #2e7d32; font-weight: bold;'>{marge_pct:+.1f} %</span>{couronne_str}</div>", unsafe_allow_html=True)
                elif 0 <= marge_pct < 25:
                    c_marge.markdown(f"<div class='cell-center'><span style='color: #1e4620; font-weight: bold;'>{marge_pct:+.1f} %</span>{couronne_str}</div>", unsafe_allow_html=True)
                else:
                    c_marge.markdown(f"<div class='cell-center'><span style='color: #ff4d4d; font-weight: bold;'>{marge_pct:+.1f} %</span>{couronne_str}</div>", unsafe_allow_html=True)

                c_tv.markdown(f"<div class='cell-center'>{row['Total Vente']:.2f} €</div>", unsafe_allow_html=True)
                c_stat.markdown("<div class='cell-center'>🔴 Vendu</div>", unsafe_allow_html=True)
                
                with c_act:
                    if st.button("↩️", key=f"undo_btn_{row['id']}", help="Annuler la vente et remettre en stock"):
                        supabase.table("inventaire").update({
                            "statut": "En stock",
                            "prixRevente": 0.0
                        }).eq("id", row['id']).execute()
                        st.success("Article remis en stock !")
                        st.rerun()
        else:
            st.write("Aucune vente enregistrée pour le moment.")

    # --- ZONE D'ÉDITION DES VISUELS ET SUPPRESSION ---
    col_e1, col_e2 = st.columns(2)
    
    with col_e1:
        with st.expander("🖼️ Modifier le visuel d'un article"):
            article_a_editer = st.selectbox(
                "Choisir l'article", 
                options=df["id"].tolist(), 
                format_func=lambda x: f"ID {x} - {df[df['id']==x]['nom'].values[0]} ({df[df['id']==x]['statut'].values[0]})",
                key="select_edit_img"
            )
            item_edit = df[df["id"] == article_a_editer].iloc[0]
            
            valeur_url_actuelle = str(item_edit.get("image_url")) if pd.notna(item_edit.get("image_url")) else ""
            
            if valeur_url_actuelle:
                st.image(valeur_url_actuelle, caption="Visuel actuel", width=100)
            
            nouvel_url = st.text_input("Lien de l'image (URL)", value=valeur_url_actuelle, key="input_edit_img")
            
            if st.button("Mettre à jour le visuel"):
                supabase.table("inventaire").update({
                    "image_url": nouvel_url if nouvel_url.strip() else None
                }).eq("id", article_a_editer).execute()
                st.success("Visuel mis à jour !")
                st.rerun()

    with col_e2:
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

    # --- 6. GRAPHIQUES DU BAS ---
    st.markdown("---")
    col_g1, col_g2 = st.columns(2)

    # GRAPHIQUE 1: Pie Chart
    with col_g1:
        with st.container(border=True):
            st.subheader("🥧 Répartition Financière Globale")
            
            cout_achat_vendus = max(total_achat_vendus, 0.0)
            ben_realise_positif = max(benefice_realise, 0.0)
            total_global_pie = total_investi_stock + cout_achat_vendus + ben_realise_positif
            
            p_stock = (total_investi_stock / total_global_pie * 100) if total_global_pie > 0 else 0
            p_cout = (cout_achat_vendus / total_global_pie * 100) if total_global_pie > 0 else 0
            p_ben = (ben_realise_positif / total_global_pie * 100) if total_global_pie > 0 else 0
            
            cat_stock = f"<b>En Stock ({p_stock:.1f}%)</b>"
            cat_cout = f"<b>Coût d'Achat Vendus ({p_cout:.1f}%)</b>"
            cat_ben = f"<b>Bénéfice Réel ({p_ben:.1f}%)</b>"

            data_pie = {
                "Catégorie": [cat_stock, cat_cout, cat_ben],
                "Montant (€)": [total_investi_stock, cout_achat_vendus, ben_realise_positif]
            }
            df_pie = pd.DataFrame(data_pie)
            
            fig_pie = px.pie(
                df_pie, 
                values="Montant (€)", 
                names="Catégorie",
                color="Catégorie",
                color_discrete_map={
                    cat_stock: "#ff9900",
                    cat_cout: "#00bfff",
                    cat_ben: "#00ffcc"
                },
                hole=0
            )
            fig_pie.update_traces(
                textposition='inside', 
                texttemplate='<b>%{value:.2f} €</b>',
                textfont=dict(size=13),
                direction='clockwise',
                sort=False
            )
            fig_pie.update_layout(
                height=350, 
                margin=dict(l=10, r=10, t=30, b=10), 
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(size=12))
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    # GRAPHIQUE 2: Courbes Comparatives CUMULÉES
    with col_g2:
        with st.container(border=True):
            st.subheader("📊 Comparatif Cumulé : Achats vs Ventes")
            
            if not df_vendus_global.empty:
                df_curve = df_vendus_global.sort_values(by="id").reset_index(drop=True)
                df_curve["N_Vente"] = df_curve.index + 1

                df_curve["Total_Achat_Cumule"] = df_curve["Total Achat"].cumsum()
                df_curve["Total_Vente_Cumule"] = df_curve["Total Vente"].cumsum()

                df_curve_chart = pd.concat([
                    pd.DataFrame([{"N_Vente": 0, "Total_Achat_Cumule": 0.0, "Total_Vente_Cumule": 0.0, "nom": "Départ"}]),
                    df_curve[["N_Vente", "Total_Achat_Cumule", "Total_Vente_Cumule", "nom"]]
                ], ignore_index=True)

                fig_curve = go.Figure()
                
                fig_curve.add_trace(go.Scatter(
                    x=df_curve_chart["N_Vente"],
                    y=df_curve_chart["Total_Achat_Cumule"],
                    mode='lines+markers',
                    name="Achats Cumulés (€)",
                    line=dict(color='#00bfff', width=3),
                    marker=dict(size=8),
                    text=df_curve_chart["nom"]
                ))
                
                fig_curve.add_trace(go.Scatter(
                    x=df_curve_chart["N_Vente"],
                    y=df_curve_chart["Total_Vente_Cumule"],
                    mode='lines+markers',
                    name="Ventes Cumulées (€)",
                    line=dict(color='#00ffcc', width=3),
                    marker=dict(size=8),
                    text=df_curve_chart["nom"]
                ))

                fig_curve.update_xaxes(dtick=1, tick0=0, title="Nombre de ventes effectuées")
                fig_curve.update_yaxes(title="Montant Cumulé (€)")
                fig_curve.update_layout(height=350, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                st.plotly_chart(fig_curve, use_container_width=True)
            else:
                st.info("Réalisez au moins une vente pour afficher les courbes comparatives.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 7. GRAPHIQUE 3: BARRE HORIZONTALE DÉCOUPÉE PAR TYPE D'ITEM ---
    if not df_stock_global.empty:
        with st.container(border=True):
            st.subheader("🏷️ Répartition du Stock par Type d'Item (%)")
            
            # Calcul du nombre total d'articles en stock pour les pourcentages
            total_items = df_stock_global["quantite"].sum()
            df_type_stock = df_stock_global.groupby("type")["quantite"].sum().reset_index()
            df_type_stock["Pourcentage"] = (df_type_stock["quantite"] / total_items) * 100
            df_type_stock["Groupe"] = "Stock"  # Axe Y unique pour empiler
            
            fig_bar_stacked = px.bar(
                df_type_stock,
                x="Pourcentage",
                y="Groupe",
                color="type",
                orientation="h",
                text=df_type_stock.apply(lambda r: f"{r['type']} ({r['Pourcentage']:.1f}%)" if r['Pourcentage'] >= 5 else "", axis=1),
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            
            fig_bar_stacked.update_traces(
                textposition="inside",
                insidetextanchor="middle",
                hovertemplate="<b>%{data.name}</b><br>Quantité: %{customdata[0]}<br>Proportion: %{x:.1f}%<extra></extra>",
                customdata=df_type_stock[["quantite"]]
            )
            
            fig_bar_stacked.update_layout(
                barmode="stack",
                height=180,
                margin=dict(l=10, r=10, t=20, b=10),
                xaxis=dict(title="Pourcentage du stock total (%)", range=[0, 100], showgrid=True),
                yaxis=dict(showticklabels=False, title=""),
                legend=dict(orientation="h", yanchor="bottom", y=-0.8, xanchor="center", x=0.5)
            )
            
            st.plotly_chart(fig_bar_stacked, use_container_width=True)
    else:
        st.info("Aucun article en stock pour afficher le graphique de répartition par type.")

else:
    st.info("Votre inventaire est vide. Ajoutez votre premier article depuis la barre latérale !")
