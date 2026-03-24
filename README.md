# 🛠️ Kemmler B2B Offer Builder

An automated tool designed to streamline the quoting process for Kemmler industrial supplies. This application fetches real-time product data and provides an interactive interface for sales teams to manage discounts and generate professional offers.

## 🚀 Key Features

* **Automated Web Scraping**: Fetches live unit prices, stock availability, and technical weights directly from the Kemmler online shop.
* **Dual-Layer Search Logic**: Automatically navigates from search results to detailed product pages to ensure 100% data accuracy for technical specifications.
* **Live Currency Conversion**: Integrates with the National Bank of Poland (NBP) API to fetch the latest EUR/PLN exchange rates.
* **Interactive Data Editor**: Allows users to manually adjust discount percentages for each item with real-time total value updates.
* **Smart Product Handling**: Correctly identifies and reports "Discontinued" or "Out of Stock" items to prevent ordering errors.

## 🛠️ Tech Stack

* **Python 3.x**
* **Streamlit**: For the interactive web interface.
* **BeautifulSoup4 & Requests**: For the core scraping engine.
* **Pandas**: For advanced data processing and Excel integration.
* **XlsxWriter**: For generating formatted output files.

## 📦 Installation & Setup

1.  **Clone the repository**:
    ```bash
    git clone [https://github.com/mrklipinsk-sys/kemmler-b2b-app.git](https://github.com/mrklipinsk-sys/kemmler-b2b-app.git)
    cd kemmler-b2b-app
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application**:
    ```bash
    streamlit run app.py
    ```

## 📝 Usage Instructions

1.  **Prepare Input**: Create an Excel file named `inquiry.xlsx` with at least two columns: `sku` and `qty`.
2.  **Upload**: Use the file uploader in the sidebar/main screen to import your inquiry.
3.  **Process**: Click "Fetch Data" to start the scraping process. The tool will display a progress spinner while it gathers information.
4.  **Edit**: Adjust the **Discount %** column directly in the data table. The **Total Value PLN** will update instantly.
5.  **Export**: Download the finalized offer as a formatted Excel file.

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for more information.

## 🤝 Contact

Project Link: [https://github.com/mrklipinsk-sys/kemmler-b2b-app](https://github.com/mrklipinsk-sys/kemmler-b2b-app)