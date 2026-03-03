import streamlit as st
import pandas as pd
import openai
import json
from io import BytesIO
import os

# Récupération de la clé OpenAI depuis variable d'environnement
openai.api_key = "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"

# Catégories
DOMAIN_CATEGORIES = [
    "Brand Site",
    "Retailer",
    "Marketplace",
    "Media",
    "Blog",
    "Forum / Community",
    "Social Media",
    "Other"
]

PAGE_CATEGORIES = [
    "Homepage",
    "PLP",
    "PDP",
    "Editorial",
    "Video",
    "Other"
]

def classify_url(url, title=None):
    prompt = f"""
Tu es un expert en e-commerce et analyse de sites web. 
Pour le site suivant, réponds par un JSON avec deux champs : "domain_type" et "page_type".

Règles :
1. "domain_type" doit être une seule catégorie parmi : {', '.join(DOMAIN_CATEGORIES)}
2. "page_type" doit être une seule catégorie parmi : {', '.join(PAGE_CATEGORIES)}

Exemples pour "domain_type" :
- Brand Site : loewe.com, hermes.com
- Retailer : nordstrom.com, zalando.com
- Marketplace : aliexpress.com, amazon.com
- Media : vogue.com, wsj.com
- Blog : mensflair.com, cupofjo.com
- Forum / Community : reddit.com, forum.hardware.fr
- Social Media : youtube.com, instagram.com
- Other : ebay.com, artprice.com

Exemples pour "page_type" :
- Homepage : www.loewe.com
- PLP : www.nordstrom.com/women/shoes
- PDP : www.loewe.com/handbags/classic-bag
- Editorial : www.vogue.com/fashion/shows
- Video : www.youtube.com/watch?v=xxxx
- Other : tout ce qui ne correspond pas aux catégories ci-dessus

URL: {url}
Titre de la page: {title if title else 'N/A'}

Réponds uniquement par un JSON valide, exemple :
{{"domain_type": "Brand Site", "page_type": "PDP"}}
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        result_text = response.choices[0].message.content.strip()
        result_json = json.loads(result_text)
        domain = result_json.get("domain_type")
        page = result_json.get("page_type")
        if domain not in DOMAIN_CATEGORIES:
            domain = "Other"
        if page not in PAGE_CATEGORIES:
            page = "Other"
        return domain, page
    except Exception as e:
        st.warning(f"Erreur GPT pour {url}: {e}")
        return "Other", "Other"

# Streamlit interface
st.title("Classification intelligente de sites web et pages (Screaming Frog CSV)")

uploaded_file = st.file_uploader("Importer un CSV export Screaming Frog", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    
    # Vérification des colonnes
    if "Adresse" not in df.columns:
        st.error("Le fichier doit contenir la colonne 'Adresse' pour les URLs.")
    else:
        # On récupère la colonne title 1 si elle existe
        df['title 1'] = df['title 1'] if 'title 1' in df.columns else None
        
        st.info("Classification en cours, cela peut prendre quelques secondes par ligne...")
        
        # Application de GPT pour chaque ligne
        df[['domain_type','page_type']] = df.apply(
            lambda row: pd.Series(classify_url(row['Adresse'], row['title 1'])),
            axis=1
        )
        
        st.dataframe(df)
        
        # Export Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Classification')
        output.seek(0)
        
        st.download_button(
            "Télécharger fichier Excel classé",
            data=output,
            file_name="classified_sites.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
