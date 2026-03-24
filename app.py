import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
import random
from io import BytesIO


class KemmlerB2BTool:
    def __init__(self):
        self.base_url = "https://www.kemmler-shop.de/en/search" 
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
        self.exchange_rate = self.get_nbp_rate()

    def get_nbp_rate(self):
        try:
            res = requests.get("https://api.nbp.pl/api/exchangerates/rates/a/eur/?format=json", timeout=5)
            return res.json()['rates'][0]['mid']
        except Exception:
            return 4.3

    def get_product(self, sku):
        try:
            price, stock, weight = 0, 0, 0
            res_search = requests.get(self.base_url, params={'search': sku}, headers=self.headers, timeout=10)
            soup = BeautifulSoup(res_search.text, 'html.parser')

            if not soup.find('h1', class_='product-detail-name'):
                link_tag = soup.find('a', class_='product-name')
                if link_tag:
                    res_search = requests.get(link_tag.get('href'), headers=self.headers, timeout=10)
                    soup = BeautifulSoup(res_search.text, 'html.parser')

            # PRICE
            p_tag = soup.find('meta', {'itemprop': 'price'}) or soup.find('p', class_='product-detail-price')
            if p_tag:
                val = p_tag.get('content') if p_tag.name == 'meta' else p_tag.get_text()
                price = float(re.sub(r'[^\d.]', '', str(val).replace(',', '.')))

            # STOCK
            s_tag = soup.find('p', class_='stock-information')
            if s_tag:
                txt = s_tag.get_text().lower()
                if "out of stock" not in txt and "no longer available" not in txt:
                    nums = re.findall(r'\d+', txt)
                    stock = int(nums[0]) if nums else 1

            # WEIGHT
            w_label = soup.find(['span', 'td', 'th'], string=re.compile(r'Weight|Gewicht', re.I))
            if w_label:
                row = w_label.find_parent('tr')
                w_txt = row.find_all('td')[-1].get_text() if row else w_label.find_next().get_text()
                w_match = re.findall(r'\d+\.?\d*', w_txt.replace(',', '.'))
                if w_match: weight = float(w_match[0])

            return price, stock, weight
        except:
            return 0, 0, 0

# --- INTERFEJS STREAMLIT ---
st.set_page_config(page_title="Kemmler Offer Builder", layout="wide")

st.title("🛠️ Kemmler B2B Offer Generator")

if 'tool' not in st.session_state:
    st.session_state.tool = KemmlerB2BTool()

# Sidebar 
st.sidebar.metric("Kurs EUR (NBP)", f"{st.session_state.tool.exchange_rate} PLN")

uploaded_file = st.file_uploader("Upload inquiry.xlsx (kolumny: sku, qty)", type=["xlsx"])

if uploaded_file:
    df_in = pd.read_excel(uploaded_file)
    
    if st.button("🔍 Find data"):
        progress_bar = st.progress(0)
        results = []
        
        sku_dict = dict(zip(df_in["sku"], df_in["qty"]))
        total_items = len(sku_dict)
        
        for i, (sku, qty) in enumerate(sku_dict.items()):
            p, s, w = st.session_state.tool.get_product(sku)
            results.append({
                'SKU': sku,
                'Order Qty': qty,
                'Stock Available': s,
                'Unit Weight (kg)': w,
                'Base Price EUR': p,
                'Discount %': 0.0
            })
            progress_bar.progress((i + 1) / total_items)
            time.sleep(random.uniform(0.5, 1.0))
        
        st.session_state.data = pd.DataFrame(results)

# 2. Calculation
if 'data' in st.session_state:
    st.subheader("📋 Edytuj rabaty i weryfikuj dane")
    
    # Wyświetlamy edytowalną tabelę
    edited_df = st.data_editor(
        st.session_state.data,
        column_config={
            "Discount %": st.column_config.NumberColumn("Rabat %", min_value=0, max_value=100, step=1, format="%d%%"),
            "Base Price EUR": st.column_config.NumberColumn("Cena EUR", format="%.2f €"),
            "Unit Weight (kg)": st.column_config.NumberColumn("Waga (kg)", format="%.2f kg")
        },
        disabled=["SKU", "Order Qty", "Stock Available", "Unit Weight (kg)", "Base Price EUR"],
        key="editor"
    )

    # Obliczenia końcowe w locie
    # Cena po rabacie * ilość * kurs NBP
    edited_df['Total Value PLN'] = (
        edited_df['Base Price EUR'] * (1 - edited_df['Discount %'] / 100) * edited_df['Order Qty'] * st.session_state.tool.exchange_rate
    ).round(2)

    # Podsumowanie pod tabelą
    total_pln = edited_df['Total Value PLN'].sum()
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Suma całkowita (PLN)", f"{total_pln:,.2f} PLN")
    
    # 3. Export do Excel
    with col2:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            edited_df.to_excel(writer, index=False, sheet_name='Oferta_Kemmler')
        
        st.download_button(
            label="💾 Pobierz Ofertę (Excel)",
            data=output.getvalue(),
            file_name=f"Oferta_Kemmler_{time.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Podgląd finalnej tabeli z przeliczoną wartością PLN
    st.write("Podgląd wartości PLN:")
    st.dataframe(edited_df[['SKU', 'Discount %', 'Total Value PLN']])