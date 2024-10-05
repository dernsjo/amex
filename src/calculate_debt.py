import pandas as pd

import lib

import numpy as np

def add_paid_by(df: pd.DataFrame) -> pd.DataFrame:
    # Initialize the 'paid_by' column with NaN values and set the dtype to 'object'
    df['paid_by'] = np.nan
    df['paid_by'] = df['paid_by'].astype(object)

    # Loop through each row and ask the user for input
    for index, transaction in df.iterrows():
        # Displaying the transaction details
        print(f"Transaction ID: {transaction['Beskrivning']}, Belopp: {transaction['Belopp']}")
        
        # Taking user input for who paid
        paid_by = input("Enter the person who paid for this transaction: ")

        # Assigning the value to the 'paid_by' column
        df.at[index, 'paid_by'] = paid_by
    
    return df

def main():

    df = lib.load_data()
    df = lib.format_data(df)
    df = add_paid_by(df)

    # Additional code can be added here to implement any functionality you need.
    # For example:
    print("Hello from main()!")


if __name__ == "__main__":
    main()
