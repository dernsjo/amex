import pandas as pd

def format_data(df: pd.DataFrame) -> pd.DataFrame:
    """Function that change columns to correct types"""
    df['Belopp'] = df['Belopp'].str.replace(',', '.').astype(float)
    df['Datum'] = pd.to_datetime(df['Datum'])    
    return df

def load_data() -> pd.DataFrame:
    """Function that load data"""
    df = pd.read_csv('../data/raw/activity.csv')
    return df