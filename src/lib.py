import pandas as pd

def format_data(df: pd.DataFrame) -> pd.DataFrame:
    """Function that change columns to correct types"""
    df['Belopp'] = df['Belopp'].str.replace(',', '.').astype(float)
    df['Datum'] = pd.to_datetime(df['Datum'])    
    return df