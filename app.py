import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Gestion Achat-Revente",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS (Effet Rainbow + Couleurs de gains/pertes) ---
st.markdown("""
    <style>
    @keyframes rainbow-text {
        0% { color: #ff0000; }
        14% { color: #ff7f00; }
        28% { color: #ffff00; }
        42% { color: #00ff00; }
        57% { color: #0000ff; }
        71% { color: #4b0082; }
        85% { color: #9400d3; }
        100% { color: #ff0000; }
    }
    .rainbow-text {
        animation: rainbow-text 2s linear infinite;
        font-weight: bold;
        font-size: 1.1em;
    }
    .profit-pos { color: #28a745; font-weight: bold; }
    .profit-neg { color: #dc3545; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- PROTECTION PAR MOT DE PASSE ---
MOT_DE_PASSE_SECRET = "Falconn29"  # <--- Change ton mot de passe ici !

if "authentifie" not in st.session_state:
    st.session_state.authentifie = False

if not st.session_state.authentifie:
    st.title("🔒 Accès Protégé")
    mp = st.text_input("Saisis ton mot de passe :", type="password")
    if st.button("Se connecter", use_container_width=True):
        if mp == MOT_DE_PASSE_SECRET:
            st.session_state.authentifie = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect !")
    st.stop()

# --- INITIALISATION DES DONNÉES EN MÉMOIRE ---
if "inventaire" not in st.session_state:
    st.session_state.inventaire = [
        {
            "type": "ETB", 
            "nom": "Exemple Coffret ETB", 
            "quantite": 2, 
            "prixAchat": 50.0, 
            "prixRevente": 80.0, 
            "statut": "Vendu"
        },
        {
            "type": "Display de boosters", 
            "nom": "Exemple Display EV05", 
            "quantite": 1, 
            "prixAchat": 140.0, 
            "prixRevente": 0.0, 
            "statut": "En stock"
        }
    ]

# --- BOUTON DE DÉCONNEXION ---
if st.sidebar.button("🔒 Se déconnecter"):
    st.session_state.authentifie = False
    st.rerun()

st.title("💼 Gestion d'Inventaire Achat-Revente")

# --- SÉLECTIONS ---
TYPES_PRODUITS = [
    "Display de bundle", "Display de boosters", "Display de mini tins", 
    "UPC", "SPC", "ETB", "Bundle", "Tripack", "Duopack", "Pokébox", 
    "Coffret classeur", "Coffret poster", "Coffret", "Mini tins", 
    "Artset de booster", "Booster", "Autre"
]
STATUTS = ["Commandé", "En stock", "Vendu", "Expédié"]

# --- CALCULS STATISTIQUES ---
inv = st.session_state.inventaire

# Produits en stock vs vendus
en_stock = [p for p in inv if p["statut"] not in ["Vendu", "Expédié"]]
produits_vendus = [p for p in inv if p["statut"] in ["Vendu", "Expédié"] and p["prixRevente"] > 0]

# Trésorerie Stockée (Uniquement les items non vendus)
tresorerie_stock = sum(p["prixAchat"] * p["quantite"] for p in en_stock)

# Plus-value réalisée sur les vendus
total_plus_value = sum((p["prixRevente"] - p["prixAchat"]) * p["quantite"] for p in produits_vendus)

# Bénéfice Moyen %
benefices_pct = [
    ((p["prixRevente"] - p["prixAchat"]) / p["prixAchat"]) * 100 
    for p in produits_vendus if p["prixAchat"] > 0
]
benefice_moyen = (sum(benefices_pct) / len(benefices_pct)) if benefices_pct else 0.0

# Valeurs max pour effets visuels Rainbow
max_benef_stock = max([((p["prixRevente"] - p["prixAchat"]) / p["prixAchat"]) * 100 for p in en_stock if p["prixRevente"] > 0 and p["prixAchat"] > 0], default=-999)
max_benef_histo = max(benefices_pct, default=-999)

# --- 1. STATISTIQUES GÉNÉRALES ---
st.subheader("📊 Statistiques Générales")
c1, c2, c3 = st.columns(3)
c1.metric("📦 Trésorerie Stockée", f"{tresorerie_stock:.2f} €")
c2.metric("📈 Bénéfice Moyen", f"{benefice_moyen:.2f} %")
c3.metric("💰 Plus-Value Totale", f"{total_plus_value:.2f} €", delta=f"{total_plus_value:.2f} €")

st.divider()

# --- 2. FORMULAIRE D'AJOUT (Simplifié) ---
st.subheader("➕ Ajouter un produit")
with st.form("form_ajout", clear_on_submit=True):
    col_a, col_b, col_c = st.columns([2, 3, 1])
    p_type = col_a.selectbox("Type de produit", TYPES_PRODUITS)
    p_nom = col_b.text_input("Nom du produit")
    p_qte = col_c.number_input("Qté", min_value=1, value=1, step=1)

    col_d, col_e, col_f = st.columns(3)
    p_achat = col_d.number_input("Prix d'achat unitaire (€)", min_value=0.0, step=1.0, format="%.2f")
    p_revente = col_e.number_input("Prix de revente estimé (€)", min_value=0.0, step=1.0, format="%.2f")
    p_statut = col_f.selectbox("Statut", STATUTS, index=1)

    btn_ajouter = st.form_submit_button("Ajouter le produit", use_container_width=True)

    if btn_ajouter and p_nom:
        nouveau = {
            "type": p_type,
            "nom": p_nom,
            "quantite": int(p_qte),
            "prixAchat": float(p_achat),
            "prixRevente": float(p_revente),
            "statut": p_statut
        }
        st.session_state.inventaire.append(nouveau)
        st.success("Produit ajouté !")
        st.rerun()

st.divider()

# --- FONCTION RENDU DES TABLEAUX ---
def afficher_tableau(liste_produits, max_benef_val):
    if not liste_produits:
        st.info("Aucun produit dans cette catégorie.")
        return

    for idx, p in enumerate(st.session_state.inventaire):
        if p in liste_produits:
            pv = (p["prixRevente"] - p["prixAchat"]) * p["quantite"] if p["prixRevente"] > 0 else 0
            
            if p["prixRevente"] > 0 and p["prixAchat"] > 0:
                pct = ((p["prixRevente"] - p["prixAchat"]) / p["prixAchat"]) * 100
                pct_str = f"{pct:.2f} %"
                is_max = (pct == max_benef_val)
            else:
                pct_str = "-"
                is_max = False

            pct_html = f'<span class="rainbow-text">{pct_str}</span>' if is_max else pct_str
            pv_class = "profit-pos" if pv >= 0 else "profit-neg"
            pv_html = f'<span class="{pv_class}">{pv:.2f} €</span>' if p["prixRevente"] > 0 else "-"

            with st.expander(f"📦 **{p['nom']}** ({p['type']}) — Statut: **{p['statut']}** | Qté: {p['quantite']}"):
                col_i1, col_i2, col_i3 = st.columns(3)
                col_i1.write(f"**Prix d'Achat :** {p['prixAchat']:.2f} € / u")
                col_i2.write(f"**Prix de Revente :** {p['prixRevente']:.2f} € / u")
                col_i3.markdown(f"**Plus-value globale :** {pv_html}", unsafe_allow_html=True)
                
                st.markdown(f"**Bénéfice estimé / réel :** {pct_html}", unsafe_allow_html=True)

                c_action1, c_action2 = st.columns([3, 1])
                nouveau_statut = c_action1.selectbox("Changer statut", STATUTS, index=STATUTS.index(p["statut"]), key=f"statut_{idx}")
                
                if nouveau_statut != p["statut"]:
                    p["statut"] = nouveau_statut
                    st.rerun()

                if c_action2.button("🗑️ Supprimer", key=f"del_{idx}"):
                    st.session_state.inventaire.pop(idx)
                    st.rerun()

# --- 3. INVENTAIRE EN STOCK ---
st.subheader("📦 Inventaire des produits en stock")
afficher_tableau(en_stock, max_benef_stock)

st.divider()

# --- 4. HISTORIQUE DES VENTES ---
st.subheader("✅ Historique des ventes")
afficher_tableau(produits_vendus, max_benef_histo)

st.divider()

# --- 5. GRAPHIQUES ---
st.subheader("📈 Analyses Visuelles")
g1, g2 = st.columns(2)

# Graphique Barres
total_achat_vendu = sum(p["prixAchat"] * p["quantite"] for p in produits_vendus)
total_revenu_vendu = sum(p["prixRevente"] * p["quantite"] for p in produits_vendus)

df_bar = pd.DataFrame({
    "Catégorie": ["Achats (Objets Vendus)", "Revenus de Vente"],
    "Montant (€)": [total_achat_vendu, total_revenu_vendu]
})
fig_bar = px.bar(df_bar, x="Catégorie", y="Montant (€)", text_auto=".2f", color="Catégorie",
                 color_discrete_sequence=["#ff9f40", "#20c997"])
fig_bar.update_layout(template="plotly_dark", showlegend=False)
g1.plotly_chart(fig_bar, use_container_width=True)

# Graphique Camembert
df_pie = pd.DataFrame({
    "Type": ["Trésorerie en stock", "Coût d'achat (Vendus)", "Plus-value réalisée"],
    "Valeur": [tresorerie_stock, total_achat_vendu, max(0, total_plus_value)]
})
fig_pie = px.pie(df_pie, names="Type", values="Valeur", hole=0.3,
                 color_discrete_sequence=["#36a2eb", "#ff9f40", "#20c997"])
fig_pie.update_layout(template="plotly_dark")
g2.plotly_chart(fig_pie, use_container_width=True)
