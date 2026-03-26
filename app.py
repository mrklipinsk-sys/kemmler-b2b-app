"""
KEMMLER B2B OFFER GENERATOR
---------------------------
A Streamlit application designed to automate the quoting process for Kemmler tools.

Key Features:
1. Web Scraping: Extracts prices, stock levels, and weights directly from the Kemmler shop.
2. Currency: Automatically fetches the EUR exchange rate via NBP API and calculates a "Commercial Rate".
3. Logistics: Dynamically calculates shipping costs based on total order weight.
4. Export: Generates professional Excel offers with currency formatting and totals.

Author: Marek Lipiński
Version: 1.1 (Logistics & Summaries)
"""

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

# --- tRANSPORT---
def calculate_shipping(weight_kg):
    if weight_kg == 0: return 0
    if weight_kg <= 30: return 29.0
    if weight_kg <= 60: return 38.0
    if weight_kg <= 90: return 57.0
    if weight_kg <= 120: return 76.0
    if weight_kg <= 150: return 95.0
    return 150.0 

# --- STREAMLIT ---
st.set_page_config(page_title="Kemmler Offer Builder", layout="wide")
st.title("🛠️ Kemmler B2B Offer Generator")

if 'tool' not in st.session_state:
    st.session_state.tool = KemmlerB2BTool()

uploaded_file = st.file_uploader("Załaduj plik: inquiry.xlsx (kolumny: sku, qty)", type=["xlsx"])

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
                'Numer produktu': sku,
                'Ilość': qty,
                'Ilość na magazynie': s,
                'Waga [kg]': w,
                'Cena kat. EUR': p,
                'Rabat %': 40.0
            })
            progress_bar.progress((i + 1) / total_items)
            time.sleep(random.uniform(0.5, 1.0))
        
        st.session_state.data = pd.DataFrame(results)

# --- 2. Calculation & Display ---
if 'data' in st.session_state:
    raw_rate = st.session_state.tool.exchange_rate
    final_rate = round(round(raw_rate, 2), 1)
    
    st.subheader("📋 Edytuj rabaty i weryfikuj dane")
    
    edited_df = st.data_editor(
        st.session_state.data,
        column_config={
            "Numer produktu": st.column_config.TextColumn("Produkt (SKU)", width=150),
            "Ilość": st.column_config.NumberColumn("Zamówienie [szt.]", width=100, format="%d"),
            "Ilość na magazynie": st.column_config.NumberColumn("Stan mag. [szt]", width=100, format="%d"),
            "Waga [kg]": st.column_config.NumberColumn("Waga [kg]", width=100, format="%.2f"),
            "Cena kat. EUR": st.column_config.NumberColumn("Cena EUR", width=120, format="%.2f"),
            "Rabat %": st.column_config.NumberColumn(
                "👉 JAKI RABAT (%)",
                help="Wpisz wartość rabatu (0-100)", 
                min_value=0, max_value=100, step=1, format="%d%%", required=True
            )
        },
        disabled=["Numer produktu", "Ilość", "Ilość na magazynie", "Waga [kg]", "Cena kat. EUR"],
        hide_index=True,
        use_container_width=True, 
        key="editor"
    )

    # Products
    edited_df['Cena kat. PLN'] = (edited_df['Cena kat. EUR'] * final_rate).round(0)
    edited_df['Suma PLN'] = (
        edited_df['Cena kat. EUR'] * (1 - edited_df['Rabat %'] / 100) * edited_df['Ilość'] * final_rate
    ).round(0)
    
    # Shipping
    total_weight = (edited_df['Waga [kg]'] * edited_df['Ilość']).sum()
    shipping_eur = calculate_shipping(total_weight)
    shipping_pln = round(shipping_eur * final_rate, 0)
    
    total_netto_pln = edited_df['Suma PLN'].sum()
    grand_total_pln = total_netto_pln + shipping_pln

    if (edited_df['Cena kat. EUR'] == 0).any():
        st.warning("⚠️ Uwaga: Niektóre produkty mają cenę 0.00!")

    # Final View
    final_view = edited_df[['Numer produktu', 'Ilość', 'Cena kat. EUR', 'Cena kat. PLN', 'Rabat %', 'Suma PLN']].copy()
    final_view.columns = ['Artykuł', 'Ilość (szt)', 'Cena kat. EUR', 'Cena kat. PLN', 'Rabat %', 'Wartość Netto PLN']

    # --- 3. SIDEBAR ---
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; padding: 10px;">
                <a href="https://www.kemmler-tools.de" target="_blank" 
                   style="text-decoration: none; color: #FFFFFF; background-color: #262730; 
                          padding: 8px 20px; border-radius: 10px; border: 1px solid #444; 
                          font-size: 14px; font-weight: 400;">
                    🌐 Strona Kemmler Tools
                </a>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("---")
        st.subheader("🏦 Kursy walut")
        c1, c2 = st.columns(2)
        c1.metric("Kurs NBP", f"{raw_rate:.4f}")
        c2.metric("Kurs handlowy", f"{final_rate:.1f}")
        
        st.write("---")
        st.subheader("💰 Podsumowanie")
        st.metric("RAZEM DO ZAPŁATY", f"{grand_total_pln:,.2f} PLN".replace(',', ' ').replace('.', ','))
   
        st.write("---")
        st.subheader("📤 Eksport")
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            final_view.to_excel(writer, index=False, sheet_name='Oferta')
            workbook  = writer.book
            worksheet = writer.sheets['Oferta']
            
            fmt_pln = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
            fmt_eur = workbook.add_format({'num_format': '#,##0.00', 'align': 'right'})
            fmt_bold = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'num_format': '#,##0.00'})
            
           
            for i, col in enumerate(final_view.columns):
                column_len = max(final_view[col].astype(str).map(len).max(), len(col)) + 5
                if col == 'Cena kat. EUR':
                    worksheet.set_column(i, i, column_len, fmt_eur)
                elif col in ['Cena kat. PLN', 'Wartość Netto PLN']:
                    worksheet.set_column(i, i, column_len, fmt_pln)
                else:
                    worksheet.set_column(i, i, column_len)

            
            last_row = len(final_view) + 2
            worksheet.write(last_row, 0, "Koszt transportu", workbook.add_format({'italic': True}))
            worksheet.write(last_row, 5, shipping_pln, fmt_pln)
            
            worksheet.write(last_row + 1, 0, "SUMA CAŁKOWITA NETTO", workbook.add_format({'bold': True}))
            worksheet.write(last_row + 1, 5, grand_total_pln, fmt_bold)

        st.download_button(
            label="💾 Pobierz Excel",
            data=output.getvalue(),
            file_name=f"Oferta_Kemmler_{time.strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # --- 4. Preview ---
    st.write("### 📄 Podgląd dokumentu dla klienta:")
    st.dataframe(final_view, use_container_width=True, hide_index=True)
    
    # Extra info
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.info(f"Całkowita waga przesyłki to **{total_weight:.2f} kg**.")
    with col_info2:
        st.success(f"**Transport:** Koszt dostawy: {shipping_pln:.0f} PLN.")
    with col_info3:
        st.info(f"Pozycje: {len(final_view)}")