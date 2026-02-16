import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Product Ranking & Logs", layout="wide")

st.title("Outil de Ranking et de vérification de fichier")

# --- CHARGEMENT DU MAPPING ---
# On définit le mapping en dur pour simplifier, ou on pourrait l'uploader
mapping_data = [
    {"keywords": "manteau cuir", "rank": 1},
    {"keywords": "mac", "rank": 1},
    {"keywords": "trench cuir", "rank": 1},
    {"keywords": "manteau", "rank": 2},
    {"keywords": "trench", "rank": 2},
    {"keywords": "parka", "rank": 2},
    {"keywords": "blouson cuir", "rank": 3},
    {"keywords": "veste cuir", "rank": 3},
    {"keywords": "perfecto", "rank": 3},
    {"keywords": "veste", "rank": 4},
    {"keywords": "jacket", "rank": 4},
    {"keywords": "blazer", "rank": 4},
    {"keywords": "combinaison", "rank": 5},
    {"keywords": "jumpsuit", "rank": 5},
    {"keywords": "robe", "rank": 6},
    {"keywords": "dress", "rank": 6},
    {"keywords": "body", "rank": 7},
    {"keywords": "pull", "rank": 8},
    {"keywords": "sweater", "rank": 8},
    {"keywords": "maille", "rank": 8},
    {"keywords": "cardigan", "rank": 8},
    {"keywords": "chemise", "rank": 9},
    {"keywords": "shirt", "rank": 9},
    {"keywords": "chemisier", "rank": 9},
    {"keywords": "blouse", "rank": 9},
    {"keywords": "top", "rank": 10},
    {"keywords": "haut", "rank": 10},
    {"keywords": "debardeur", "rank": 11},
    {"keywords": "tank top", "rank": 11},
    {"keywords": "pantalon cuir", "rank": 12},
    {"keywords": "pantalon", "rank": 13},
    {"keywords": "pants", "rank": 13},
    {"keywords": "jean", "rank": 13},
    {"keywords": "denim", "rank": 13},
    {"keywords": "jupe", "rank": 14},
    {"keywords": "skirt", "rank": 14},
    {"keywords": "bermuda", "rank": 15},
    {"keywords": "short", "rank": 15},
    {"keywords": "lingerie", "rank": 16},
    {"keywords": "underwear", "rank": 16}
]
df_mapping = pd.DataFrame(mapping_data)

# --- INTERFACE ---
uploaded_file = st.file_uploader("Choisissez votre fichier CSV d'import", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1', dtype=str)
    except Exception:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig', dtype=str)
        
    logs = []
    
    def process_row(row, index):
        line_num = index + 2  # +2 car index commence à 0 et ligne 1 est le header
        smc_val = row.get('smc') or row.get('sku') or "Inconnu"
        comm = str(row.get('commentaires', '')).upper()
        name = str(row.get('product_name', row.get('APPELLATION', ''))).lower()
        cat = str(row.get('category_ids', row.get('CATEGORY', ''))).upper()
        
        # --- LOGS DES COMMENTAIRES ---
        if "LOOK PURPOSE ONLY" in comm or "NOT FOR SALE" in comm:
            logs.append(f"Row {line_num} : {smc_val} - NOT FOR SALE")
        
        if "OLD" in comm:
            logs.append(f"Row {line_num} : {smc_val} - SMC SWITCH")
            
        # --- LOGIQUE DE RANKING ---
        final_rank = row.get('product_ranking', None)
        if "RTW" in cat:
            found_rank = None
            for _, m_row in df_mapping.iterrows():
                keywords = str(m_row['keywords']).lower().split()
                if all(k in name for k in keywords):
                    found_rank = m_row['rank']
                    break
            final_rank = found_rank if found_rank else 17
            
        return final_rank

    # Traitement
    df['product_ranking'] = [process_row(row, i) for i, row in df.iterrows()]
    
    # --- AFFICHAGE DES LOGS ---
    st.subheader("Logs d'analyse")
    if logs:
        for log in logs:
            st.error(log)
    else:
        st.success("Aucun log d'alerte détecté.")

    # --- TELECHARGEMENT ---
    st.subheader("Télécharger le résultat")
    csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="Télécharger le CSV corrigé",
        data=csv,
        file_name="resultat_ranking.csv",
        mime="text/csv"
    )
