"""
Bank Market Capitalization ETL Pipeline (Senior Data Engineering Implementation)
================================================================================
This script automates the quarterly acquisition, transformation, loading, and
querying of the world's top 10 largest banks by market capitalization.

Pipeline Stages:
  1. Extract: Scrapes top 10 banks ranked by market cap (USD billion) from Wikipedia.
  2. Transform: Enriches data with GBP, EUR, and INR conversions based on live exchange rates.
  3. Load: Persists the structured data to both a CSV file and a SQLite database table.
  4. Query: Executes analytical and regional office queries against the database.
  5. Audit / Logging: Tracks all pipeline milestones with timestamps in 'code_log.txt'.

Author: Senior Data Engineer
Target: IBM Data Engineering Capstone / Project
"""

import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import requests

# -----------------------------------------------------------------------------
# Pipeline Configuration & Constants
# -----------------------------------------------------------------------------
BASE_DIR: Path = Path(__file__).resolve().parent

DATA_URL: str = (
    "https://web.archive.org/web/20230908091635/"
    "https://en.wikipedia.org/wiki/List_of_largest_banks"
)
EXCHANGE_RATE_URL: str = (
    "https://cf-courses-data.s3.us.cloud-object-storage.appdomain.cloud/"
    "IBMSkillsNetwork-PY0221EN-Coursera/labs/v2/exchange_rate.csv"
)

TABLE_ATTRIBS_EXTRACTION: List[str] = ["Name", "MC_USD_Billion"]
TABLE_ATTRIBS_FINAL: List[str] = [
    "Name",
    "MC_USD_Billion",
    "MC_GBP_Billion",
    "MC_EUR_Billion",
    "MC_INR_Billion",
]

OUTPUT_CSV_PATH: Path = BASE_DIR / "Largest_banks_data.csv"
DB_PATH: Path = BASE_DIR / "Banks.db"
TABLE_NAME: str = "Largest_banks"
LOG_FILE_PATH: Path = BASE_DIR / "code_log.txt"

# Request Headers for resilience against bot blockers
HTTP_HEADERS: Dict[str, str] = {
    "User-Agent": "curl/8.5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# -----------------------------------------------------------------------------
# Console Logging Setup
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("banks_etl")


# -----------------------------------------------------------------------------
# Task 1: Logging Progress
# -----------------------------------------------------------------------------
def log_progress(message: str) -> None:
    """Logs progress messages with timestamps to both code_log.txt and console.

    Uses the course-standard timestamp format '%Y-%h-%d-%H:%M:%S'.

    Args:
        message (str): Milestone or status message to log.
    """
    timestamp_format = "%Y-%h-%d-%H:%M:%S"
    now = datetime.now()
    timestamp = now.strftime(timestamp_format)
    log_entry = f"{timestamp} : {message}\n"

    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(log_entry)
        logger.info(message)
    except IOError as e:
        logger.error(f"Failed to write to log file {LOG_FILE_PATH}: {e}")


# -----------------------------------------------------------------------------
# Task 2: Data Extraction
# -----------------------------------------------------------------------------
def extract(url: str, table_attribs: List[str]) -> pd.DataFrame:
    """Scrapes tabular bank data from Wikipedia under 'By market capitalization'.

    Args:
        url (str): Web address containing the archived Wikipedia article.
        table_attribs (List[str]): Initial column headers for extracted data.

    Returns:
        pd.DataFrame: DataFrame containing bank names and USD market cap.

    Raises:
        RuntimeError: If data extraction or parsing fails.
    """
    try:
        response = requests.get(url, headers=HTTP_HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        # Fallback retry with generic browser agent if initial request fails
        logger.warning(f"Initial fetch failed ({e}). Retrying with alternate User-Agent...")
        fallback_headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
        }
        response = requests.get(url, headers=fallback_headers, timeout=30)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    tables = soup.find_all("tbody")

    if not tables:
        raise RuntimeError("No HTML table bodies found on the webpage.")

    # Target table is the first tbody (under 'By market capitalization')
    target_table = tables[0]
    rows = target_table.find_all("tr")

    extracted_records: List[Dict[str, object]] = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
            # Column 1: Bank Name (nested <a> tag or clean text)
            bank_name = cols[1].get_text(strip=True)
            # Column 2: Market cap in billion USD
            market_cap_raw = cols[2].get_text(strip=True).replace(",", "")

            try:
                market_cap_usd = float(market_cap_raw)
                extracted_records.append({
                    table_attribs[0]: bank_name,
                    table_attribs[1]: market_cap_usd,
                })
            except ValueError:
                continue

    df = pd.DataFrame(extracted_records, columns=table_attribs)

    # Validate output
    if df.empty:
        raise RuntimeError("Extraction completed but 0 records were parsed.")

    # Retain exactly the top 10 banks
    df = df.head(10).copy()
    logger.info(f"Extracted {len(df)} records successfully.")
    return df


# -----------------------------------------------------------------------------
# Task 3: Data Transformation
# -----------------------------------------------------------------------------
def transform(df: pd.DataFrame, csv_path: str) -> pd.DataFrame:
    """Enriches bank data with currency conversions based on exchange rates CSV.

    Converts USD capitalization into GBP, EUR, and INR, rounded to 2 decimal places.

    Args:
        df (pd.DataFrame): DataFrame with columns ['Name', 'MC_USD_Billion'].
        csv_path (str): File path or URL to the exchange rate CSV.

    Returns:
        pd.DataFrame: Transformed DataFrame with additional currency columns.

    Raises:
        ValueError: If required currencies are missing in exchange rates file.
    """
    transformed_df = df.copy()

    # Load exchange rate lookup
    rates_df = pd.read_csv(csv_path)
    # Normalize dictionary: {'EUR': 0.93, 'GBP': 0.8, 'INR': 82.95}
    rate_dict: Dict[str, float] = dict(zip(rates_df["Currency"].str.strip(), rates_df["Rate"]))

    required_currencies = ["GBP", "EUR", "INR"]
    for curr in required_currencies:
        if curr not in rate_dict:
            raise ValueError(f"Missing exchange rate for required currency: {curr}")

    # Add converted and rounded columns using numpy vectorization
    transformed_df["MC_GBP_Billion"] = np.round(
        transformed_df["MC_USD_Billion"] * rate_dict["GBP"], 2
    )
    transformed_df["MC_EUR_Billion"] = np.round(
        transformed_df["MC_USD_Billion"] * rate_dict["EUR"], 2
    )
    transformed_df["MC_INR_Billion"] = np.round(
        transformed_df["MC_USD_Billion"] * rate_dict["INR"], 2
    )

    # Ensure schema matches final specification
    transformed_df = transformed_df[TABLE_ATTRIBS_FINAL]
    logger.info(f"Transformation complete. Schema: {list(transformed_df.columns)}")
    return transformed_df


# -----------------------------------------------------------------------------
# Task 4: Load to CSV
# -----------------------------------------------------------------------------
def load_to_csv(df: pd.DataFrame, output_path: str | Path) -> None:
    """Exports transformed DataFrame to local CSV without pandas default index.

    Args:
        df (pd.DataFrame): Transformed DataFrame.
        output_path (str | Path): Destination file path.
    """
    path = Path(output_path)
    df.to_csv(path, index=False)
    logger.info(f"Successfully saved {len(df)} rows to CSV at: {path}")


# -----------------------------------------------------------------------------
# Task 5: Load to SQL Database
# -----------------------------------------------------------------------------
def load_to_db(
    df: pd.DataFrame, sql_connection: sqlite3.Connection, table_name: str
) -> None:
    """Loads DataFrame into SQLite database table, replacing previous content.

    Args:
        df (pd.DataFrame): Transformed DataFrame.
        sql_connection (sqlite3.Connection): Open SQLite connection.
        table_name (str): Target table name.
    """
    df.to_sql(table_name, sql_connection, if_exists="replace", index=False)
    logger.info(f"Loaded DataFrame to SQLite database table '{table_name}'.")


# -----------------------------------------------------------------------------
# Task 6: Database Query Execution
# -----------------------------------------------------------------------------
def run_queries(
    query_statements: List[str], sql_connection: sqlite3.Connection
) -> None:
    """Executes SQL queries against the database and prints tabular results.

    Args:
        query_statements (List[str]): SQL SELECT statements to execute.
        sql_connection (sqlite3.Connection): Open SQLite connection.
    """
    separator = "=" * 80
    for query in query_statements:
        print(f"\n{separator}")
        print(f"QUERY: {query}")
        print(separator)
        query_output = pd.read_sql(query, sql_connection)
        print(query_output)
        print(f"Total Rows: {len(query_output)}\n")


# -----------------------------------------------------------------------------
# Main ETL Orchestrator
# -----------------------------------------------------------------------------
def main() -> None:
    """Orchestrates end-to-end execution of the ETL pipeline."""
    logger.info("Initializing Bank Market Capitalization ETL Pipeline...")

    # Log Step 1: Preliminaries
    log_progress("Preliminaries complete. Initiating ETL process.")

    # Step 2: Extraction
    raw_df = extract(DATA_URL, TABLE_ATTRIBS_EXTRACTION)
    log_progress("Data extraction complete. Initiating Transformation process.")

    # Step 3: Transformation
    transformed_df = transform(raw_df, EXCHANGE_RATE_URL)
    log_progress("Data transformation complete. Initiating Loading process.")

    # Step 4: Load to CSV
    load_to_csv(transformed_df, OUTPUT_CSV_PATH)

    # Step 5: Load to Database & Execute Queries
    with sqlite3.connect(DB_PATH) as conn:
        load_to_db(transformed_df, conn, TABLE_NAME)
        log_progress("Data loaded to Database as a table. Executing queries.")

        # Define Analytical & Office-Specific Queries
        test_queries = [
            # 1. Full Table Inspection
            f"SELECT * FROM {TABLE_NAME}",
            # 2. Average market cap in GBP across all top banks
            f"SELECT ROUND(AVG(MC_GBP_Billion), 2) AS [Average_MC_GBP_Billion] FROM {TABLE_NAME}",
            # 3. Top 5 largest banks by name
            f"SELECT Name FROM {TABLE_NAME} LIMIT 5",
            # 4. Regional Office Queries (Directions a, b, c)
            f"SELECT Name, MC_GBP_Billion FROM {TABLE_NAME}",  # London Office
            f"SELECT Name, MC_EUR_Billion FROM {TABLE_NAME}",  # Berlin Office
            f"SELECT Name, MC_INR_Billion FROM {TABLE_NAME}",  # New Delhi Office
        ]

        run_queries(test_queries, conn)

    # Log Step 6: Process Complete
    log_progress("Process Complete.")
    logger.info("ETL Pipeline finished successfully.")


if __name__ == "__main__":
    main()

