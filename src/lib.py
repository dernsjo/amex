import pandas as pd
import os

def format_data(df: pd.DataFrame) -> pd.DataFrame:
    """Function that change columns to correct types"""
    df['Belopp'] = df['Belopp'].str.replace(',', '.').astype(float)
    df['Datum'] = pd.to_datetime(df['Datum'])    
    return df

  
def load_data(date: str) -> pd.DataFrame:

    """Function that load data"""
    base_dir = "/Users/axeldernsjo/Documents/amex"
    file_path = os.path.join(base_dir, f"data/raw/activity-{date}.csv")
    df = pd.read_csv(file_path)
    return df