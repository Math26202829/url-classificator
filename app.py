import streamlit as st
import pandas as pd
import json
from io import BytesIO
import os
from openai import OpenAI
import time

# -------------------- OpenAI --------------------
# Récupère la clé depuis variable d'environnement
client = OpenAI(api_key="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")

# -------------------- Catégories --------------------
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

BATCH_SIZE = 50  # Nombre d'URLs par batch

# -------------------- Fonction prompt batch --------------------
def create_batch_prompt(batch):
    prompt_lines = []
    for row in batch:
        url = row['Adresse']
        title = row['title 1'] if row['title 1'] else "N/A"
        prompt_lines.append(f"URL: {url}\nTitle: {title}")
    urls_text = "\n\n".join(prompt_lines)
    
    prompt = f"""
Tu es un expert en e-commerce et analyse de sites web.
Pour chaque URL ci-dessous, renvoie un JSON avec "domain_type" et "page_type" pour chaque URL.

Règles :
- "domain_type" doit être une seule catégorie parmi : {', '.join(DOMAIN_CATEGORIES)}
- "page_type" doit être une seule catégorie parmi : {', '.join(PAGE_CATEGORIES)}

Exemples pour "domain_type":
- Brand Site : loewe.com, hermes.com
- Retailer : nordstrom.com, zalando.com
- Marketplace : aliexpress.com, amazon.com
- Media : vogue.com, wsj.com
- Blog : mensflair.com, cupofjo.com
- Forum / Community : reddit.com, forum.hardware.fr
- Social Media : youtube.com, instagram.com
- Other : ebay.com, artprice.com

Exemples pour "page_type":
- Homepage : www.loewe.com
- PLP : www.nordstrom.com/women/shoes
- PDP : www.loewe.com/handbags/classic-bag
- Editorial : www.vogue.com/fashion/shows
- Video : www.youtube.com/watch?v=xxxx
- Other : tout ce qui ne correspond pas aux catégories ci-dessus

Voici les URLs à classer :
{urls_text}

Réponds uniquement par un JSON valide de la forme :
{{{{ "URL1": {{ "domain_type": "...", "page_type": "..." }}, "URL2": {{...}} }}}}
"""
    return prompt

# -------------------- Fonction classification batch --------------------
def classify_batch(batch):
    prompt = create_batch_prompt(batch)
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        text = response.choices[0].message.content.strip()
        data = json.loads(text)
        return data
    except Exception as e:
        st.warning(f"Erreur GPT pour un batch: {e}")
        return {}

# -------------------- Streamlit --------------------
st.title("Classification intelligente de sites web et pages (Screaming Frog CSV)")

uploaded_file = st.file_uploader("Importer un CSV export Screaming Frog", type=["csv"])
if uploaded_file:
    df = pd.read_csv(uploaded_file, low_memory=False)
    
    if "Adresse" not in df.columns:
        st.error("Le fichier doit contenir la colonne 'Adresse' pour les URLs.")
    else:
        df['title 1'] = df['title 1'] if 'title 1' in df.columns else None
        
        st.info("Classification en cours, cela peut prendre un certain temps pour 38 000 URLs...")
        
        results = []
        total_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE
        
        for i in range(0, len(df), BATCH_SIZE):
            batch = df.iloc[i:i+BATCH_SIZE].to_dict('records')
            batch_result = classify_batch(batch)
            
            # Mapping résultats
            for row in batch:
                url = row['Adresse']
                if url in batch_result:
                    results.append({
                        "Adresse": url,
                        "title 1": row['title 1'],
                        "domain_type": batch_result[url].get("domain_type", "Other"),
                        "page_type": batch_result[url].get("page_type", "Other")
                    })
                else:
                    results.append({
                        "Adresse": url,
                        "title 1": row['title 1'],
                        "domain_type": "Other",
                        "page_type": "Other"
                    })
            st.write(f"Batch {i//BATCH_SIZE+1}/{total_batches} traité")
            time.sleep(1)  # pause pour éviter de saturer l'API
        
        result_df = pd.DataFrame(results)
        st.dataframe(result_df)
        
        # Export Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            result_df.to_excel(writer, index=False, sheet_name='Classification')
        output.seek(0)
        
        st.download_button(
            "Télécharger fichier Excel classé",
            data=output,
            file_name="classified_sites.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
