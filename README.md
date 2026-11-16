# Bank Market Capitalization ETL Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Pandas](https://img.shields.io/badge/Pandas-2.0%2B-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![BeautifulSoup](https://img.shields.io/badge/BeautifulSoup-4-green)](https://www.crummy.com/software/BeautifulSoup/)
[![Status](https://img.shields.io/badge/Status-Production--Ready-success)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An automated, resilient Extract, Transform, Load (ETL) pipeline implemented in Python to compile, normalize, and monitor quarterly financial data for the world's top 10 largest commercial banks ranked by market capitalization.

---

## 🏛️ Architecture & Data Flow

```mermaid
flowchart LR
    A["Wikipedia Archive<br/>(Market Cap Data)"] -->|Extract (BeautifulSoup)| B["Raw DataFrame<br/>(Name, MC_USD_Billion)"]
    C["Cloud Object Storage<br/>(exchange_rate.csv)"] -->|Transform (NumPy & Pandas)| D["Enriched DataFrame<br/>(USD, GBP, EUR, INR)"]
    B --> D
    D -->|Load to CSV| E["Largest_banks_data.csv"]
    D -->|Load to SQLite| F["Banks.db (Table: Largest_banks)"]
    F -->|Analytics / Queries| G["Regional Offices & Analytical Checks"]
    H["Audit Logger"] -.->|code_log.txt| D
```

---

## ⚙️ Key Engineering Decisions & Best Practices

1. **Defensive Web Scraping:**
   - Engineered with custom HTTP header profiles and resilient fallback handling to circumvent aggressive bot-mitigation policies and HTTP 429 rate limits on archive gateways.
   - Robust HTML parsing targeted at the specific `By market capitalization` table structure.

2. **Vectorized Transformations:**
   - Currency conversions utilize vector operations via NumPy and Pandas rather than iterative row processing, maximizing throughput.
   - All converted currency values are strictly rounded to 2 decimal places to adhere to standard financial reporting conventions.

3. **Data Integrity & Schema Contracts:**
   - Explicit column naming and data type enforcement (`Name: TEXT`, `MC_*: REAL / float64`).
   - Replaces database tables atomically on quarterly refresh runs (`if_exists='replace'`), ensuring idempotency and zero state accumulation.

4. **Dual-Tier Audit Logging:**
   - **Audit File (`code_log.txt`):** Generates standardized timestamped log lines formatted to specification (`%Y-%h-%d-%H:%M:%S : <message>`).
   - **Console Observability:** Emits structured Python logging records (`logging.INFO`) to stdout for containerized orchestration and CI/CD pipelines.

---

## 📋 Data Dictionary

| Column Name | Data Type | Currency / Unit | Description |
| :--- | :--- | :--- | :--- |
| `Name` | `TEXT` | N/A | Full name of the commercial banking institution |
| `MC_USD_Billion` | `REAL` (float64) | Billion USD | Market capitalization extracted from primary data source |
| `MC_GBP_Billion` | `REAL` (float64) | Billion GBP | Market capitalization converted to British Pounds (`Rate: 0.80`) |
| `MC_EUR_Billion` | `REAL` (float64) | Billion EUR | Market capitalization converted to Euros (`Rate: 0.93`) |
| `MC_INR_Billion` | `REAL` (float64) | Billion INR | Market capitalization converted to Indian Rupees (`Rate: 82.95`) |

---

## 🚀 Getting Started

### 1. Prerequisites & Environment Setup
Python 3.10+ is recommended. Set up and activate a local virtual environment:

```bash
# Clone the repository
git clone https://github.com/Mohammed-Dahi/largest-banks-etl-pipeline.git
cd largest-banks-etl-pipeline

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running the Pipeline
Execute the main pipeline script:

```bash
python banks_project.py
```

---

## 📊 Pipeline Deliverables & Verification

After pipeline execution, verify the generated artifacts:

- **Cleaned Data Export:** `Largest_banks_data.csv`
- **SQLite Database:** `Banks.db` (Table: `Largest_banks`)
- **Execution Log:** `code_log.txt`

### Sample Output Queries (Regional Offices)

#### London Office Query (`MC_GBP_Billion`)
```sql
SELECT Name, MC_GBP_Billion FROM Largest_banks;
```

#### Berlin Office Query (`MC_EUR_Billion`)
```sql
SELECT Name, MC_EUR_Billion FROM Largest_banks;
```

#### New Delhi Office Query (`MC_INR_Billion`)
```sql
SELECT Name, MC_INR_Billion FROM Largest_banks;
```

#### Portfolio Analytical Check (Average Market Cap in GBP)
```sql
SELECT ROUND(AVG(MC_GBP_Billion), 2) AS [Average_MC_GBP_Billion] FROM Largest_banks;
```

---

## 📁 Repository Structure

```text
├── banks_project.py            # Main ETL pipeline script
├── Largest_banks_data.csv      # Exported multi-currency CSV dataset
├── Banks.db                    # SQLite database containing processed records
├── code_log.txt                # Timestamped execution log
├── requirements.txt            # Project dependencies
├── Final_project_overview.md   # Project scope and business scenarios
├── Project_guide.md            # Detailed lab guide and step-by-step directions
├── .gitignore                  # Git exclusion rules
└── README.md                   # Project documentation
```

---

## 👨‍💻 Author

**Mohammed Dahi**  
*AI & Data Engineer*  
- **GitHub:** [@Mohammed-Dahi](https://github.com/Mohammed-Dahi)  
- **LinkedIn:** [mohammeddahi](https://linkedin.com/in/mohammeddahi)  
- **Email:** Mohameddahi657@gmail.com

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
