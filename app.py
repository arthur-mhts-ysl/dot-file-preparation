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
        html, body, [class*="css"] { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #000000; }
        .main { background-color: #ffffff; }
        h1 { font-weight: 800; letter-spacing: -1px; text-transform: uppercase; font-size: 2rem !important; padding-bottom: 2rem; border-bottom: 2px solid #000000; }
        h3 { font-weight: 700; text-transform: uppercase; letter-spacing: 1px; font-size: 1rem !important; margin-top: 2rem !important; }
        .stButton>button { border-radius: 0px; border: 1px solid #000000; background-color: #000000; color: #ffffff; font-weight: 600; text-transform: uppercase; padding: 0.5rem 2rem; transition: 0.3s; }
        .stButton>button:hover { background-color: #ffffff; color: #000000; border: 1px solid #000000; }
        section[data-testid="stFileUploadDropzone"] { border-radius: 0px; border: 1px dashed #000000; }
        .stAlert { border-radius: 0px; border: none; border-left: 5px solid #000000; background-color: #f2f2f2; color: #000000; }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

st.title("Exit List Configurator Tool")

# ==========================================
# --- CONFIGURATION DU MAPPING & LOGIQUE ---
# ==========================================

# 1. SYNONYMES POUR L'IMPORT (Flexible)
SYNONYMS = {
    "look_ids": ["LOOK", "LOOKS", "NUMERO LOOK", "LOOK NUMBER"],
    "smc": ["SMC", "SKU", "ARTICLE"],
    "product_name": ["APPELLATION", "APPELLATION COMMERCIALE", "PRODUCT NAME", "STYLE DESC"],
    "material_description": ["DESCRIPTIF MATIERE", "APPELLATION MATIERE", "MATERIAL DESCRIPTION"],
    "category_ids": ["CATEGORY", "CATEGORIE"],
    "line": ["LINE", "LIGNE"], # Ajouté pour le ranking dynamique
    "model_code": ["STEALTH","CODE STEALTH","MODEL CODE", "MODELE"],
    "material_code": ["MATERIAL CODE", "CODE MATIERE"],
    "color_code": ["COLOR CODE", "COULEUR", "CODE COULEUR"],
    "color_description": ["COLOR DESCRIPTION", "COLOR DESC", "DESCRIPTIF COULEUR", "APPELLATION COULEUR"],
    "department": ["DEPARTMENT", "DEPARTEMENT","DEPT CODE"],
    "size_grid": ["SIZE GRID", "SIZE_GRID"]
}

# 2. ORDRE FINAL DES COLONNES
TARGET_COLS = [
    "collection_ids", "look_ids", "smc", "model_code", "product_name", 
    "material_code", "material_description", "color_code", "color_description", 
    "category_ids", "department", "product_ranking", "size_grid"
]

LEATHER_KEYWORDS = ["CUIR", "LEATHER", "VEAU", "TAUREAU", "VACHE", "CROCODILE", "ALIGATOR", "PYTHON", "AGNEAU", "PEAU", "DAIM", "SHEEP"]
REMOVE_KEYWORDS = ["COLLANT", "CULOTTE", "CHAUSSETTE"]

# 3. MAPPING RANKING RTW
ranking_data = [
    {"keywords": "mac", "rank": 2}, {"keywords": "manteau", "rank": 2}, {"keywords": "trench", "rank": 2},
    {"keywords": "parka", "rank": 2}, {"keywords": "caban", "rank": 2}, {"keywords": "perfecto", "rank": 4},
    {"keywords": "blouson", "rank": 4}, {"keywords": "bustier", "rank": 4}, {"keywords": "gilet", "rank": 4},
    {"keywords": "veste", "rank": 4}, {"keywords": "doudoune", "rank": 4}, {"keywords": "bombardier", "rank": 4},
    {"keywords": "vr", "rank": 4}, {"keywords": "jacket", "rank": 4}, {"keywords": "blazer", "rank": 4},
    {"keywords": "coupe vent", "rank": 4}, {"keywords": "combinaison", "rank": 5}, {"keywords": "jumpsuit", "rank": 5},
    {"keywords": "robe", "rank": 6}, {"keywords": "dress", "rank": 6}, {"keywords": "body", "rank": 7},
    {"keywords": "pull", "rank": 8}, {"keywords": "sweater", "rank": 8}, {"keywords": "tricot de corps", "rank": 8},
    {"keywords": "maille", "rank": 8}, {"keywords": "cardigan", "rank": 8}, {"keywords": "chemise", "rank": 9},
    {"keywords": "shirt", "rank": 9}, {"keywords": "sr", "rank": 9}, {"keywords": "chemisier", "rank": 9},
    {"keywords": "blouse", "rank": 9}, {"keywords": "top", "rank": 10}, {"keywords": "haut", "rank": 10},
    {"keywords": "debardeur", "rank": 11}, {"keywords": "tank top", "rank": 11}, {"keywords": "pantalon", "rank": 13},
    {"keywords": "pr", "rank": 13}, {"keywords": "pants", "rank": 13}, {"keywords": "jogging", "rank": 13},
    {"keywords": "legging", "rank": 13}, {"keywords": "jean", "rank": 13}, {"keywords": "denim", "rank": 13},
    {"keywords": "jupe", "rank": 14}, {"keywords": "skirt", "rank": 14}, {"keywords": "bermuda", "rank": 15},
    {"keywords": "short", "rank": 15}, {"keywords": "lingerie", "rank": 16}, {"keywords": "underwear", "rank": 16}
]
df_mapping = pd.DataFrame(ranking_data)

# ==========================================
# --- FONCTIONS UTILITAIRES ---
# ==========================================

def allocate_category(raw_cat, gender, row_idx, smc, error_logs, export_logs_list):
    if not gender: return ""
    cat = str(raw_cat).upper().strip()
    g_prefix = "M" if gender == "MEN" else "W"
    
    if "RTW" in cat or cat in ["SOIE", "FLOU", "SPW", "CHEMISE", "JERSEY", "KNITWEAR", "MAILLE", "SPORTSWEAR TECHNIQUE", "TAILLEUR", "DENIM"]:
        return f"{g_prefix}RTW LOOKS"
    elif "SHOES" in cat or cat in ["CHAUSSURE", "CHAUSSURES"]:
        return f"{g_prefix}SHOES"
    elif "BELTS" in cat or cat in ["CEINTURE", "CEINTURES"]:
        return f"{g_prefix}BELTS"
    elif "SMLG" in cat or cat == "MSMLG":
        return f"{g_prefix}SMLG"
    elif "SLG" in cat:
        return f"{g_prefix}SLG"
    elif cat == "BIJOUX": return "JEWELRY"
    elif cat == "BIJOUX CUIR": return "LEATHER JEWELRY"
    elif "SUNGLASSES" in cat or cat in ["LUNETTE", "LUNETTES"]: return "SUNGLASSES"
    elif cat in ["SOFT ACCESSORIES", "EYEWEAR", "JEWELRY", "LEATHER JEWELRY", "LUGGAGE", "HANDBAGS"]: return cat
    
    msg = f"'{cat}' NOT RECOGNIZED FOR CATEGORY ALLOCATION"
    error_logs.append(f"ROW {row_idx + 2} : {smc} — {msg}")
    export_logs_list.append({"ROW": row_idx + 2, "SMC": smc, "ISSUE": msg, "TAB": "CATEGORY ISSUES"})
    return cat

# ==========================================
# --- CHARGEMENT DU FICHIER ---
# ==========================================

uploaded_file = st.file_uploader("Please import your csv Exit list file", type="csv")

if uploaded_file is None:
    st.markdown("""
    <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 2rem;">
        PLEASE ENSURE THE FILE CONTAINS THE STANDARD COLUMNS (SMC, LOOK, APPELLATION, CATEGORY, etc.)
    </div>
    """, unsafe_allow_html=True)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, sep=';', encoding='latin-1', dtype=str)
    except Exception:
        uploaded_file.seek(0)
        df = pd.read_csv(uploaded_file, sep=';', encoding='utf-8-sig', dtype=str)

    df.columns = [c.strip().upper() for c in df.columns]
    df.columns = [" ".join(c.split()) for c in df.columns]
    
    info_logs = []
    error_logs = []
    export_logs_list = []

    # --- DÉTECTION DYNAMIQUE DES COLONNES SOURCE POUR LE RANKING ---
    def get_col_val(row, target_key):
        options = SYNONYMS.get(target_key, [])
        for opt in options:
            if opt in row: return str(row[opt])
        return ""

    def process_row(row, index):
        line_num = index + 2  
        
        # Récupération propre pour éviter le "nan" textuel
        smc_raw = get_col_val(row, "smc")
        if pd.isna(smc_raw) or str(smc_raw).strip().lower() == "nan" or str(smc_raw).strip() == "":
            smc_val = ""
        else:
            smc_val = str(smc_raw).strip()
            
        name = get_col_val(row, "product_name").upper()
        material = get_col_val(row, "material_description").upper()
        cat = get_col_val(row, "category_ids").upper()
        line_val = get_col_val(row, "line").upper()
        comm = str(row.get('COMMENTAIRES') or row.get('COMMENTAIRE') or '').upper().strip()
        
        display_smc = smc_val if smc_val else f"UNKNOWN_ROW_{line_num}"

        # --- LOGS SMC ---
        if smc_val == "nan":
            # Cas où le SMC est totalement absent
            msg = "MISSING SMC"
            error_logs.append(f"ROW {line_num} : {msg}")
            export_logs_list.append({"ROW": line_num, "SMC": "N/A", "ISSUE": msg, "TAB": "SMC FORMAT ISSUES"})
        else:
            # Cas où le SMC existe mais a un mauvais format
            if len(smc_val) != 15:
                msg = "SMC FORMAT NOT RESPECTED (15 CHARACTERS REQUIRED)"
                error_logs.append(f"ROW {line_num} : {smc_val} — {msg}")
                export_logs_list.append({"ROW": line_num, "SMC": display_smc, "ISSUE": msg, "TAB": "SMC FORMAT ISSUES"})
            elif " " in smc_val:
                msg = "SMC FORMAT NOT RESPECTED (CONTAINING SPACE)"
                error_logs.append(f"ROW {line_num} : {smc_val} — {msg}")
                export_logs_list.append({"ROW": line_num, "SMC": display_smc, "ISSUE": msg, "TAB": "SMC FORMAT ISSUES"})

        if "TBC" in smc_val.upper():
            msg = "SMC TBC - VERIFY CODES"
            info_logs.append(f"ROW {line_num} : {smc_val} — {msg}")
            export_logs_list.append({"ROW": line_num, "SMC": display_smc, "ISSUE": msg, "TAB": "SMC FORMAT ISSUES"})

        if any(kw in name for kw in REMOVE_KEYWORDS):
            msg = "SMC TO REMOVE"
            info_logs.append(f"ROW {line_num} : {display_smc} — {msg} (Product: {name})")
            export_logs_list.append({"ROW": line_num, "SMC": display_smc, "ISSUE": "SMC TO REMOVE", "TAB": "SMC TO REMOVE", "DETAIL": name})
            
        if any(x in comm for x in ["LOOK PURPOSE ONLY", "NOT FOR SALE", "LOOK PURPOSES ONLY"]):
            msg = f"SMC NOT FOR SALE (Comment: {comm})"
            info_logs.append(f"ROW {line_num} : {display_smc} — {msg}")
            export_logs_list.append({"ROW": line_num, "SMC": display_smc, "ISSUE": "SMC NOT FOR SALE", "TAB": "SMC NOT FOR SALE", "DETAIL": comm})
        
        if re.search(r'\bOLD\b', comm):
            msg = f"SMC SWITCH (Comment: {comm})"
            info_logs.append(f"ROW {line_num} : {display_smc} — {msg}")
            export_logs_list.append({"ROW": line_num, "SMC": display_smc, "ISSUE": "SMC SWITCH", "TAB": "SMC SWITCH", "DETAIL": comm})

        # --- RANKING LOGIC ---
        is_leather = any(k in name for k in LEATHER_KEYWORDS) or any(k in material for k in LEATHER_KEYWORDS)
        found_rank = None
        
        if "RTW" in cat:
            for _, m_row in df_mapping.iterrows():
                kw_list = str(m_row['keywords']).lower().split()
                if all(k in name.lower() for k in kw_list):
                    found_rank = m_row['rank']
                    break
            if found_rank is None and line_val != '':
                for _, m_row in df_mapping.iterrows():
                    kw_list = str(m_row['keywords']).lower().split()
                    if all(k in line_val.lower() for k in kw_list):
                        found_rank = m_row['rank']
                        break
            if is_leather:
                if found_rank == 2: found_rank = 1
                elif found_rank == 4: found_rank = 3
                elif found_rank == 13: found_rank = 12
                elif found_rank is None: found_rank = 17 
            final_rank = found_rank if found_rank is not None else 17
        else:
            final_rank = None 
        return final_rank

    # --- TRAITEMENT DU FORMAT LOOK (01 au lieu de 1) ---
    look_col_source = next((opt for opt in SYNONYMS["look_ids"] if opt in df.columns), None)
    if look_col_source:
        def format_look(val):
            if pd.isna(val) or str(val).strip() == "": return val
            val_str = str(val).strip()
            if val_str.isdigit() and len(val_str) < 2: return val_str.zfill(2)
            return re.sub(r'(\b\d\b)', lambda m: m.group(1).zfill(2), val_str)
        df[look_col_source] = df[look_col_source].apply(format_look)

    # Lancer le calcul du ranking
    df['product_ranking'] = [process_row(row, i) for i, row in df.iterrows()]
    df['product_ranking'] = pd.to_numeric(df['product_ranking'], errors='coerce').astype('Int64')

    # ==========================================
    # --- INTERFACE SETTINGS & GENDER ---
    # ==========================================
    st.subheader("SETTINGS")
    collection_id_val = st.text_input("Please enter the COLLECTION_ID (required)", key="col_id")

    if 'gender' not in st.session_state: st.session_state.gender = None
    col_m, col_w = st.columns(2)
    with col_m:
        if st.button("MEN", use_container_width=True, type="primary" if st.session_state.gender == "MEN" else "secondary"):
            st.session_state.gender = "MEN"; st.rerun()
    with col_w:
        if st.button("WOMEN", use_container_width=True, type="primary" if st.session_state.gender == "WOMEN" else "secondary"):
            st.session_state.gender = "WOMEN"; st.rerun()

    current_gender = st.session_state.gender
    if current_gender: st.write(f"Selection: **{current_gender}**")

    # ==========================================
    # --- RECONSTRUCTION DU DATAFRAME ---
    # ==========================================
    
    # On identifie les sources réelles
    mapping_source = {"product_ranking": "product_ranking"}
    for target, opts in SYNONYMS.items():
        if target in ["model_code", "material_code", "color_code", "department"]: 
            mapping_source[target] = "AUTO_EXTRACT"
        else: mapping_source[target] = next((opt for opt in opts if opt in df.columns), None)
    
    df["collection_ids"] = collection_id_val
    orig_smc_col = mapping_source.get("smc")

    cat_source = mapping_source.get("category_ids")
    if cat_source and cat_source in df.columns:
        df["category_ids"] = df.apply(
            lambda row: allocate_category(
                row[cat_source], current_gender, row.name, row.get(orig_smc_col, "N/A"), error_logs, export_logs_list
            ), axis=1
        )
        
    for target in TARGET_COLS:
        if target == "collection_ids": continue
        # On saute category_ids car on vient de le faire au-dessus
        if target == "category_ids": continue 
        
        source = mapping_source.get(target)
        
        if source == "AUTO_EXTRACT":
            if target == "model_code" and orig_smc_col:
                df[target] = df[orig_smc_col].apply(lambda x: str(x).strip()[0:6] if pd.notna(x) and len(str(x).strip()) == 15 else "")
            elif target == "material_code" and orig_smc_col:
                df[target] = df[orig_smc_col].apply(lambda x: str(x).strip()[6:11] if pd.notna(x) and len(str(x).strip()) == 15 else "")
            elif target == "color_code" and orig_smc_col:
                df[target] = df[orig_smc_col].apply(lambda x: str(x).strip()[11:15] if pd.notna(x) and len(str(x).strip()) == 15 else "")
            elif target == "department":
                def compute_dept(cat_val, gender):
                    val = str(cat_val).upper()
                    if "RTW" in val:
                        return "MRTW" if gender == "MEN" else "WRTW"
                    return val
                # Ici, x sera la catégorie "allouée" (ex: WRTW LOOKS) car calculée au-dessus
                df[target] = df["category_ids"].apply(lambda x: compute_dept(x, current_gender))
        
        elif source and source in df.columns:
            df[target] = df[source]
        else:
            df[target] = ""
            if target not in ["look_ids", "size_grid"]: 
                info_logs.append(f"COLUMN '{target.upper()}' NOT FOUND")
                
    # --- NETTOYAGE & GROUPBY ---
    df = df[TARGET_COLS]
   
    df = df.astype(str).replace(['nan', 'None', '<NA>'], '')
    df = df.apply(lambda x: x.str.strip())
    df = df.replace(r'\n+|\r+', ' ', regex=True)

    # Définir les colonnes sur lesquelles grouper (tout sauf look_ids)
    id_cols_group = [c for c in TARGET_COLS if c != 'look_ids']
    
    # Groupement avec sécurisation du tri des looks
    def combine_looks(x):
        # On filtre les valeurs vides et on dédoublonne
        clean_list = list(set(filter(None, x)))
        # On trie (zfill permet de trier 02 avant 10 correctement)
        return ','.join(sorted(clean_list))

    df = df.groupby(id_cols_group, as_index=False, dropna=False).agg({'look_ids': combine_looks})
    
    # Réorganiser les colonnes une dernière fois
    df = df[TARGET_COLS]

    # --- LOGS & EXPORTS ---
    st.subheader("ANALYSIS LOGS")
    if export_logs_list:
        df_logs_full = pd.DataFrame(export_logs_list)
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for tab_name in df_logs_full['TAB'].unique():
                # Filtrage et renommage dynamique
                df_tab = df_logs_full[df_logs_full['TAB'] == tab_name][['ROW', 'SMC', 'ISSUE', 'DETAIL']].copy()
                col_name = "APPELLATION" if tab_name == "SMC TO REMOVE" else "COMMENTAIRE"
                df_tab.rename(columns={'DETAIL': col_name}, inplace=True)
                
                df_tab.to_excel(writer, sheet_name=tab_name[:31], index=False)
                
                # Ajustement largeur colonnes
                worksheet = writer.sheets[tab_name[:31]]
                for idx, col in enumerate(df_tab.columns):
                    worksheet.set_column(idx, idx, 20)

        st.download_button(
            label="Download All Issues",
            data=output.getvalue(),
            file_name=f"all_issues_{collection_id_val}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    if error_logs:
        for err in error_logs: st.error(err)
    if info_logs:
        for log in info_logs: st.info(log)
    if not info_logs and not error_logs: st.write("NO ALERT DETECTED")

    st.subheader("EXPORT")
    if not collection_id_val or not current_gender:
        st.warning("Please enter a Collection ID and select a Gender.")
    else:
        st.download_button("Download Exit List import file", df.to_csv(index=False, sep=';', encoding='utf-8-sig').encode('utf-8-sig'), f"{collection_id_val}_V1.csv", "text/csv")
