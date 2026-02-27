import streamlit as st
import pandas as pd
import io
import re

# --- CONFIGURATION ---
st.set_page_config(page_title="DOT - ECT", layout="wide")

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

st.title("Exit List Configurator Tool")

# --- LISTE DES MATIÈRES CUIR ---
LEATHER_KEYWORDS = ["CUIR", "LEATHER", "VEAU", "TAUREAU", "VACHE", "CROCODILE", "ALIGATOR", "PYTHON", "AGNEAU", "PEAU", "DAIM", "SHEEP"]

# --- LISTE DES PRODUITS A NE PAS IMPORTER ---
REMOVE_KEYWORDS = ["COLLANT", "CULOTTE", "CHAUSSETTE"]

# --- CHARGEMENT DU MAPPING ---
mapping_data = [
    {"keywords": "mac", "rank": 2}, 
    {"keywords": "manteau", "rank": 2},
    {"keywords": "trench", "rank": 2},
    {"keywords": "parka", "rank": 2},
    {"keywords": "caban", "rank": 2},
    {"keywords": "perfecto", "rank": 4},
    {"keywords": "blouson", "rank": 4},
    {"keywords": "bustier", "rank": 4},
    {"keywords": "gilet", "rank": 4},
    {"keywords": "veste", "rank": 4},
    {"keywords": "doudoune", "rank": 4},
    {"keywords": "bombardier", "rank": 4},
    {"keywords": "vr", "rank": 4},
    {"keywords": "jacket", "rank": 4},
    {"keywords": "blazer", "rank": 4},
    {"keywords": "coupe vent", "rank": 4},
    {"keywords": "combinaison", "rank": 5},
    {"keywords": "jumpsuit", "rank": 5},
    {"keywords": "robe", "rank": 6},
    {"keywords": "dress", "rank": 6},
    {"keywords": "body", "rank": 7},
    {"keywords": "pull", "rank": 8},
    {"keywords": "sweater", "rank": 8},
    {"keywords": "tricot de corps", "rank": 8},
    {"keywords": "maille", "rank": 8},
    {"keywords": "cardigan", "rank": 8},
    {"keywords": "chemise", "rank": 9},
    {"keywords": "shirt", "rank": 9},
    {"keywords": "sr", "rank": 9},
    {"keywords": "chemisier", "rank": 9},
    {"keywords": "blouse", "rank": 9},
    {"keywords": "top", "rank": 10},
    {"keywords": "haut", "rank": 10},
    {"keywords": "debardeur", "rank": 11},
    {"keywords": "tank top", "rank": 11},
    {"keywords": "pantalon", "rank": 13},
    {"keywords": "pr", "rank": 13},
    {"keywords": "pants", "rank": 13},
    {"keywords": "jogging", "rank": 13},
    {"keywords": "legging", "rank": 13},
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

# Affiche les instructions seulement si aucun fichier n'est chargé
if uploaded_file is None:
    st.markdown("""
    <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2rem;">
        PLEASE ENSURE THE FILE MEETS THE FOLLOWING REQUIREMENTS:<br>
        • FORMAT: <b>CSV ( ; FORMAT)</b><br>
        • COLUMN: <b>"SMC"</b> OR <b>"SKU"</b> (UPPERCASE)<br>
        • COLUMN: <b>"LOOK"</b> (UPPERCASE)<br>
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
        
    info_logs = []
    error_logs = []
    export_error_data = []
    export_logs_list = []

    def allocate_category(raw_cat, gender, row_idx, smc):
        if not gender: return ""
        cat = str(raw_cat).upper().strip()
        g_prefix = "M" if gender == "MEN" else "W"
        
        # Logique de transformation
        if "RTW" in cat or cat in ["SOIE", "FLOU", "SPW", "CHEMISE", "JERSEY", "KNITWEAR", "MAILLE", "SPORTSWEAR TECHNIQUE", "TAILLEUR", "DENIM"]:
            return f"{g_prefix}RTW LOOKS"
        elif "SHOES" in cat or cat in ["CHAUSSURE", "CHAUSSURES"]:
            return f"{g_prefix}SHOES"
        elif "BELTS" in cat or cat in ["CEINTURE", "CEINTURES"]:
            return f"{g_prefix}BELTS"
        elif "SMLG" in cat or cat == "MSMLG": # SMLG avant SLG pour éviter les conflits
            return f"{g_prefix}SMLG"
        elif "SLG" in cat:
            return f"{g_prefix}SLG"
        elif cat == "BIJOUX":
            return "JEWELRY"
        elif cat == "BIJOUX CUIR":
            return "LEATHER JEWELRY"
        elif "SUNGLASSES" in cat or cat in ["LUNETTE", "LUNETTES"]:
            return "SUNGLASSES"
        elif cat in ["SOFT ACCESSORIES", "EYEWEAR", "JEWELRY", "LEATHER JEWELRY", "LUGGAGE", "HANDBAGS"]:
            return cat
        
        # Si aucun cas ne correspond
        msg = f"'{cat}' NOT RECOGNIZED FOR CATEGORY ALLOCATION"
        error_logs.append(f"ROW {row_idx + 2} : {smc} — {msg}")
        export_logs_list.append({"ROW": row_idx + 2, "SMC": smc, "TYPE": "ERROR", "ISSUE": msg})
        return cat

    def process_row(row, index):
        mod_c, mat_c, col_c = "", "", ""
        line_num = index + 2  
        
        smc_raw = row.get('SMC') or row.get('SKU')
        smc_val = str(smc_raw).strip() if pd.notna(smc_raw) else ""
        
        comm = str(row.get('COMMENTAIRES') or row.get('COMMENTAIRE') or '').upper().strip()
        name = str(row.get('APPELLATION') or row.get('APPELLATION COMMERCIALE') or row.get('PRODUCT NAME') or '').upper()
        material = str(row.get('DESCRIPTIF MATIERE') or row.get('APPELLATION MATIERE') or '').upper()
        cat = str(row.get('CATEGORY') or row.get('CATEGORIE') or '').upper()
        line_val = str(row.get('LINE') or row.get('LIGNE') or '').upper()
        # Découpage automatique si le SMC est valide (15 chars)
        if len(smc_val) == 15:
            mod_c = smc_val[0:6]   # 6 premiers
            mat_c = smc_val[6:11]  # 5 suivants
            col_c = smc_val[11:15] # 4 derniers
        
        display_smc = smc_val if smc_val else f"UNKNOWN_ROW_{line_num}"

        # --- LOGS DE FORMAT ---
        if smc_val != "":
            if len(smc_val) != 15:
                msg = "SMC FORMAT NOT RESPECTED (15 CHARACTERS REQUIRED) - VERIFY THE DIFFERENT CODES (MODEL, MATERIAL, COLOR)"
                error_logs.append(f"ROW {line_num} : {smc_val} — {msg}")
                export_error_data.append({"SMC": display_smc, "ISSUE": msg})
            elif " " in smc_val:
                msg = "SMC FORMAT NOT RESPECTED (CONTAINING SPACE)"
                error_logs.append(f"ROW {line_num} : {smc_val} — {msg}")
                export_error_data.append({"SMC": display_smc, "ISSUE": msg})

        # --- LOG DE CODES ---
        # checks = {mod_c: (6, "MODEL"), mat_c: (5, "MATERIAL"), col_c: (4, "COLOR")}
        # for val, (length, label) in checks.items():
        #     if val and len(val) != length:
        #         msg = f"{label} CODE FORMAT NOT RESPECTED ({length} CHARACTERS REQUIRED)"
        #         error_logs.append(f"ROW {line_num} : {val} — {msg}")
        #         export_logs_list.append({"ROW": line_num, "SMC": display_smc, "TYPE": "ERROR", "ISSUE": msg})

        # --- LOGS INFO (SMC SWITCH avec commentaire) ---
        if "TBC" in smc_val.upper():
            msg = "SMC TBC - VERIFY THE DIFFERENT CODES (MODEL, MATERIAL, COLOR)"
            info_logs.append(f"ROW {line_num} : {smc_val} — {msg}")
            export_logs_list.append({"ROW": line_num, "SMC": display_smc, "TYPE": "INFO", "ISSUE": msg})

        if any(kw in name for kw in REMOVE_KEYWORDS):
            msg = "SMC TO REMOVE"
            info_logs.append(f"ROW {line_num} : {display_smc} — {msg} (Product: {name})")
            export_logs_list.append({"ROW": line_num, "SMC": display_smc, "TYPE": "INFO", "ISSUE": msg})
            
        if any(x in comm for x in ["LOOK PURPOSE ONLY", "NOT FOR SALE", "LOOK PURPOSES ONLY"]):
            info_logs.append(f"ROW {line_num} : {display_smc} — NOT FOR SALE")
        
        if re.search(r'\bOLD\b', comm):
            msg = f"SMC SWITCH (Comment: {comm})" # Ajout du commentaire ici
            info_logs.append(f"ROW {line_num} : {display_smc} — {msg}")
            export_error_data.append({"SMC": display_smc, "ISSUE": msg})
    
        # 3. DÉTECTION MATIÈRE CUIR
        is_leather = any(k in name for k in LEATHER_KEYWORDS) or \
                     any(k in material for k in LEATHER_KEYWORDS)
    
        # 4. IDENTIFICATION DE LA PIÈCE
        found_rank = None
        
        if "RTW" in cat:
            # --- ÉTAPE A : Recherche dans l'APPELLATION ---
            for _, m_row in df_mapping.iterrows():
                kw_list = str(m_row['keywords']).lower().split()
                if all(k in name.lower() for k in kw_list):
                    found_rank = m_row['rank']
                    break
            
            # --- ÉTAPE B : FALLBACK dans la colonne LINE/LIGNE ---
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
                elif found_rank is None: 
                    found_rank = 17 
    
            final_rank = found_rank if found_rank is not None else 17
        else:
            final_rank = None 
            
        return final_rank
        
    # Traitement
    df['product_ranking'] = [process_row(row, i) for i, row in df.iterrows()]
    df['product_ranking'] = pd.to_numeric(df['product_ranking'], errors='coerce').astype('Int64')

    # ---------------------------------------------------------
    # --- AJOUT RÉORGANISATION ET INTERFACE COLLECTION_ID ---
    # ---------------------------------------------------------
    
    # 1. Définir l'ordre des colonnes cibles
    target_cols = [
        "collection_ids", "look_ids", "smc", "model_code", "product_name", 
        "material_code", "material_description", "color_code", "color_description", 
        "category_ids", "department", "product_ranking", "size_grid"
    ]

    # 2. Détecter les sources
    synonyms = {
        "look_ids": ["LOOK", "LOOKS", "NUMERO LOOK", "LOOK NUMBER"],
        "smc": ["SMC", "SKU"],
        "product_name": ["APPELLATION", "APPELLATION COMMERCIALE", "PRODUCT NAME"],
        "material_description": ["DESCRIPTIF MATIERE", "APPELLATION MATIERE", "MATERIAL DESCRIPTION"],
        "category_ids": ["CATEGORY", "CATEGORIE"],
        "model_code": ["STEALTH","CODE STEALTH","MODEL CODE", "MODELE"],
        "material_code": ["MATERIAL CODE", "CODE MATIERE"],
        "color_code": ["COLOR CODE", "COULEUR", "CODE COULEUR"],
        "color_description": ["COLOR DESCRIPTION", "DESCRIPTIF COULEUR", "APPELLATION COULEUR"],
        "department": ["DEPARTMENT", "DEPARTEMENT","DEPT CODE"],
        "size_grid": ["SIZE GRID", "GRILLE TAILLE"]
    }

    # --- TRAITEMENT DU FORMAT LOOK (01 au lieu de 1) ---
    # On utilise les synonymes pour trouver la colonne à formater
    look_col_to_format = next((opt for opt in synonyms["look_ids"] if opt in df.columns), None)
            
    if look_col_to_format:
        def format_look(val):
            if pd.isna(val) or str(val).strip() == "":
                return val
            val_str = str(val).strip()
            if val_str.isdigit() and len(val_str) < 2:
                return val_str.zfill(2)
            return re.sub(r'(\b\d\b)', lambda m: m.group(1).zfill(2), val_str)

        df[look_col_to_format] = df[look_col_to_format].apply(format_look)
        # On définit look_col pour la suite du mapping source
        look_col = look_col_to_format 
    else:
        look_col = None

    # On prépare le mapping final
    mapping_source = {"look_ids": look_col, "product_ranking": "product_ranking"}
    
    for target, options in synonyms.items():
        if target == "look_ids": continue # Déjà géré au-dessus
        
        if target in ["model_code", "material_code", "color_code"]:
            mapping_source[target] = "AUTO_EXTRACT"
        else:
            found = next((opt for opt in options if opt in df.columns), None)
            mapping_source[target] = found

    # 3. Interface Collection ID
    st.subheader("SETTINGS")
    collection_id_val = st.text_input("Please enter the COLLECTION_ID (required)", key="col_id")
    df["collection_ids"] = collection_id_val

    # Gestion des boutons Gender avec session_state
    if 'gender' not in st.session_state:
        st.session_state.gender = None

    col_men, col_women = st.columns(2)
    
    with col_men:
        if st.button("MEN", use_container_width=True, type="primary" if st.session_state.gender == "MEN" else "secondary"):
            st.session_state.gender = "MEN"
            st.rerun()

    with col_women:
        if st.button("WOMEN", use_container_width=True, type="primary" if st.session_state.gender == "WOMEN" else "secondary"):
            st.session_state.gender = "WOMEN"
            st.rerun()

    current_gender = st.session_state.gender
    if current_gender:
        st.write(f"Selection: **{current_gender}**")

    # 4. Remplissage des colonnes (C'est ici qu'on remplace les valeurs)
    orig_smc_col = mapping_source.get("smc")

    for target in target_cols:
        if target == "collection_ids": continue
        
        source = mapping_source.get(target)
        
        # ICI ON FORCE LE CALCUL SUR LES VALEURS
        if source == "AUTO_EXTRACT" and orig_smc_col:
            if target == "model_code":
                df[target] = df[orig_smc_col].apply(lambda x: str(x).strip()[0:6] if pd.notna(x) and len(str(x).strip()) == 15 else "")
            elif target == "material_code":
                df[target] = df[orig_smc_col].apply(lambda x: str(x).strip()[6:11] if pd.notna(x) and len(str(x).strip()) == 15 else "")
            elif target == "color_code":
                df[target] = df[orig_smc_col].apply(lambda x: str(x).strip()[11:15] if pd.notna(x) and len(str(x).strip()) == 15 else "")
        
        # Pour les autres colonnes, on copie la source si elle existe
        elif source and source in df.columns:
            if target == "category_ids":
                # On applique l'allocation dynamique
                df[target] = df.apply(lambda row: allocate_category(row[source], current_gender, row.name, row[orig_smc_col]), axis=1)
            else:
                df[target] = df[source]
        else:
            df[target] = "" 
            if target not in ["look_ids", "size_grid"]:
                info_logs.append(f"COLUMN '{target.upper()}' NOT FOUND")

    # 4. Réorganiser les colonnes pour suivre la template Exit List IMPORT
    df = df[target_cols]
    # Enlever les espaces début/fin pour TOUTES les colonnes
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    
    # SUPPRESSION DES RETOURS À LA LIGNE (Global)
    df = df.replace(r'\n+|\r+', ' ', regex=True)
    
    # Retirer TOUS les espaces pour Look IDs et Size Grid
    if 'look_ids' in df.columns:
        df['look_ids'] = df['look_ids'].str.replace(" ", "", regex=False)
    if 'size_grid' in df.columns:
        df['size_grid'] = df['size_grid'].str.replace(" ", "", regex=False)
    
    # 5. Regroupement par SMC (Une ligne par produit, Looks concaténés)
    # On définit les colonnes qui identifient de manière unique le produit
    id_columns = [c for c in target_cols if c != 'look_ids']
    
    # On s'assure que look_ids est bien traité comme du texte pour la virgule
    df['look_ids'] = df['look_ids'].astype(str).replace('nan', '')
    
    # On groupe par toutes les colonnes sauf le look
    df = df.groupby(id_columns, as_index=False, dropna=False).agg({
        'look_ids': lambda x: ','.join(sorted(list(set(filter(None, x))), key=str))
    })

    # On remet les colonnes dans le bon ordre (car le groupby peut les décaler)
    df = df[target_cols]
    
    # --- AFFICHAGE DES LOGS ---
    st.subheader("ANALYSIS LOGS")
    
    # Affichage des erreurs critiques d'abord (Rouge)
    if error_logs:
        for err in error_logs:
            st.error(err)

    # Bouton d'export des logs si des erreurs existent
    if export_logs_list:
        df_export = pd.DataFrame(export_logs_list)
        csv_logs = df_export.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="Download All Issues (CSV)",
            data=csv_logs,
            file_name=f"all_issues_{collection_id_val}.csv",
            mime="text/csv"
        )
            
    # Affichage des logs d'information (Gris standard)
    if info_logs:
        for log in info_logs:
            st.info(log)
            
    if not info_logs and not error_logs:
        st.write("NO ALERT DETECTED")


    # --- TELECHARGEMENT ---
    st.subheader("EXPORT")
    if not collection_id_val or not current_gender:
        st.warning("Please enter a Collection ID and select a Gender to enable download.")
    else:
        csv = df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="Download Exit List import file",
            data=csv,
            file_name=f"{collection_id_val}_V1.csv",
            mime="text/csv"
        )
