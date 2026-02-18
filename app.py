import streamlit as st
import pandas as pd
import io
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="DOT import verificator", layout="wide")

# --- DESIGN SAINT LAURENT ---
st.markdown("""
    <style>
        @import url('https://fonts.cdnfonts.com/css/helvetica-neue-55');
        
        html, body, [class*="css"] {
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            color: #000000;
        }

        .main {
            background-color: #ffffff;
        }

        h1 {
            font-weight: 800;
            letter-spacing: -1px;
            text-transform: uppercase;
            font-size: 2rem !important;
            padding-bottom: 2rem;
            border-bottom: 2px solid #000000;
        }

        h3 {
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 1rem !important;
            margin-top: 2rem !important;
        }

        .stButton>button {
            border-radius: 0px;
            border: 1px solid #000000;
            background-color: #000000;
            color: #ffffff;
            font-weight: 600;
            text-transform: uppercase;
            padding: 0.5rem 2rem;
            transition: 0.3s;
        }

        .stButton>button:hover {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #000000;
        }

        section[data-testid="stFileUploadDropzone"] {
            border-radius: 0px;
            border: 1px dashed #000000;
        }

        .stAlert {
            border-radius: 0px;
            border: none;
            border-left: 5px solid #000000;
            background-color: #f2f2f2;
            color: #000000;
        }

        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.title("Verifications & Product Ranking")

# --- LISTE DES MATIÈRES CUIR ---
LEATHER_KEYWORDS = ["CUIR", "LEATHER", "VEAU", "TAUREAU", "VACHE", "CROCODILE", "ALIGATOR", "PYTHON", "AGNEAU", "PEAU", "DAIM", "SHEEP"]

# --- CHARGEMENT DU MAPPING ---
mapping_data = [
    {"keywords": "mac", "rank": 2}, 
    {"keywords": "manteau", "rank": 2},
    {"keywords": "trench", "rank": 2},
    {"keywords": "parka", "rank": 2},
    {"keywords": "perfecto", "rank": 4},
    {"keywords": "blouson", "rank": 4},
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
uploaded_file = st.file_uploader("Please import your csv Exit list file", type="csv")

st.markdown("""
<div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2rem;">
    PLEASE ENSURE THE FILE MEETS THE FOLLOWING REQUIREMENTS:<br>
    • FORMAT: <b>CSV (SEMICOLON-DELIMITED)</b><br>
    • COLUMN: <b>"SMC"</b> OR <b>"SKU"</b> (UPPERCASE)<br>
    • COLUMN: <b>"COMMENTAIRES"</b> OR <b>"COMMENTAIRE"</b> (UPPERCASE)<br>
    • COLUMN: <b>"APPELLATION"</b> OR <b>"APPELLATION COMMERCIALE"</b> (UPPERCASE)<br>
    • COLUMN: <b>"CATEGORY"</b> OR <b>"CATEGORIE"</b> (UPPERCASE)<br>
    • COLUMN: <b>"LINE"</b> OR <b>"LIGNE"</b> (UPPERCASE)<br>
    • COLUMN: <b>"DESCRIPTIF MATIERE"</b> OR <b>"APPELLATION MATIERE"</b> (UPPERCASE)
</div>
""", unsafe_allow_html=True)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1', dtype=str)
    except Exception:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig', dtype=str)

    # --- NORMALISATION DES COLONNES ---
    df.columns = [c.strip().upper() for c in df.columns]
    df.columns = [" ".join(c.split()) for c in df.columns]
        
    logs = []
    
    def process_row(row, index):
        line_num = index + 2  
        
        # Récupération flexible des colonnes
        smc_val = row.get('SMC') or row.get('SKU') or "N/A"
        comm = str(row.get('COMMENTAIRES') or row.get('COMMENTAIRE') or '').upper()
        name = str(row.get('APPELLATION') or row.get('APPELLATION COMMERCIALE') or row.get('PRODUCT NAME') or '').upper()
        material = str(row.get('DESCRIPTIF MATIERE') or row.get('APPELLATION MATIERE') or '').upper()
        cat = str(row.get('CATEGORY') or row.get('CATEGORIE') or '').upper()
        line_val = str(row.get('LINE') or row.get('LIGNE') or '').upper()
        
        # 1. LOGS 
        if any(x in comm for x in ["LOOK PURPOSE ONLY", "NOT FOR SALE", "LOOK PURPOSES ONLY"]):
            logs.append(f"ROW {line_num} : {smc_val} — NOT FOR SALE")
        if re.search(r'\bOLD\b', comm):
            logs.append(f"ROW {line_num} : {smc_val} — SMC SWITCH")
    
        # 2. DÉTECTION MATIÈRE CUIR
        # On vérifie si un mot-clé de cuir est présent dans le nom OU dans la matière
        is_leather = any(k in name for k in LEATHER_KEYWORDS) or \
                     any(k in material for k in LEATHER_KEYWORDS)
    
        # 3. IDENTIFICATION DE LA PIÈCE
        found_rank = None
        
        if "RTW" in cat:
            # --- ÉTAPE A : Recherche dans l'APPELLATION ---
            for _, m_row in df_mapping.iterrows():
                kw_list = str(m_row['keywords']).lower().split()
                if all(k in name.lower() for k in kw_list):
                    found_rank = m_row['rank']
                    break
            
            # --- ÉTAPE B : FALLBACK dans la colonne LINE/LIGNE si rien trouvé ---
            if found_rank is None and line_val != '':
                for _, m_row in df_mapping.iterrows():
                    kw_list = str(m_row['keywords']).lower().split()
                    if all(k in line_val.lower() for k in kw_list):
                        found_rank = m_row['rank']
                        break

            # --- ÉTAPE C : APPLICATION DU SURCLASSEMENT CUIR ---
            if is_leather:
                if found_rank == 2:   # Manteau -> Rank 1
                    found_rank = 1
                elif found_rank == 4: # Veste -> Rank 3
                    found_rank = 3
                elif found_rank == 13: # Pantalon -> Rank 12
                    found_rank = 12
                elif found_rank is None: # Cuir détecté mais pièce toujours non identifiée
                    found_rank = 17 
    
            # Valeur finale (si rien trouvé = 17)
            final_rank = found_rank if found_rank is not None else 17
        else:
            final_rank = None 
            
        return final_rank

    # Traitement
    df['product_ranking'] = [process_row(row, i) for i, row in df.iterrows()]
    df['product_ranking'] = pd.to_numeric(df['product_ranking'], errors='coerce').astype('Int64')
    
    # --- AFFICHAGE DES LOGS ---
    st.subheader("ANALYSIS LOGS")
    if logs:
        for log in logs:
            st.info(log)
    else:
        st.write("NO ALERT DETECTED")

    # --- TELECHARGEMENT ---
    st.subheader("EXPORT")
    csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button(
        label="Download Ranking Result",
        data=csv,
        file_name="resultat_ranking.csv",
        mime="text/csv"
    )
