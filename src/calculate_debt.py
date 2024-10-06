import pandas as pd
import numpy as np
import streamlit as st

import lib

def save_csv(df: pd.DataFrame) -> None:
    """Stores processed data"""
    min_date = df['Datum'].min()
    max_date = df['Datum'].max()
    file_path = f'../data/processed/period-{min_date}-{max_date}.csv'
    df.to_csv(file_path, index=False)
    st.success("Changes saved successfully.")
    return

def add_column(df: pd.DataFrame,name: str) -> pd.DataFrame:
    """Initiate a Column with the value Delad"""
    if name not in df.columns:
        df[name] = "Delad"  # Initialize column as Delad
    return df

def edit_paid_by_column(df: pd.DataFrame) -> pd.DataFrame:
    """Allows the user to edit the 'Paid By' column using Streamlit's data_editor"""
    edited_df = st.data_editor(
        df,
        column_config={
            "Paid By": st.column_config.SelectboxColumn(
                "Paid By",
                options=["Axel", "Ebba", "Utlägg", "Delad"],
                help="Select who paid for the item.",
            ),
        },
        disabled=[],  # Replace "Other_Columns" with actual column names if you need any columns to be disabled
        hide_index=False,
    )
    return edited_df
def calculate_who_pays_what(df: pd.DataFrame) -> dict:
    """
    Calculate how much Axel and Ebba each owe or should be paid back.
    """
    # Calculate total expenses
    total_expenses = df['Belopp'].sum()

    # Sum of amounts paid by each category
    sum_utlägg = df.loc[df['Paid By'] == 'Utlägg', 'Belopp'].sum()
    sum_axel = df.loc[df['Paid By'] == 'Axel', 'Belopp'].sum()
    sum_ebba = df.loc[df['Paid By'] == 'Ebba', 'Belopp'].sum()

    # Calculate the remaining amount to be divided equally
    remaining_amount = total_expenses - sum_utlägg - sum_axel - sum_ebba
    equal_share = remaining_amount / 2

    # Calculate the final amount Axel and Ebba should pay or receive
    axel_final = sum_axel + equal_share
    ebba_final = sum_ebba + equal_share

    return {
        'Axel': axel_final,
        'Ebba': ebba_final,
        'Utlägg': sum_utlägg,
        'Totalt': axel_final+ebba_final+sum_utlägg,
        'Controll': total_expenses
    }

def main():

    # Load data from CSV
    df = lib.load_data()
    df = lib.format_data(df)
    
    # Store the dataframe in a variable
    st.session_state.df = df
    data = st.session_state.df

    # Add Paid By column
    data = add_column(df,"Paid By")

    st.title("CSV File Viewer and Editor")

    if not data.empty:
        st.subheader("Editable Data")
        
        # Call the function to allow editing of 'Paid By' column
        edited_df = edit_paid_by_column(data)

        # Update the session state with the new data
        st.session_state.data = edited_df

        if st.button('Calculate expenses'):
            result = calculate_who_pays_what(edited_df)
            st.write("**Final Amounts to Pay or Be Refunded:**")
            st.write(result)

        # Save changes button
        if st.button("Save Changes to CSV"):
            save_csv(edited_df)

if __name__ == "__main__":
    main()