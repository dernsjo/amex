import os
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
import lib

def save_csv(df: pd.DataFrame, date: str) -> None:
    """Stores processed data"""
    base_dir = os.getcwd()
    file_path = os.path.join(base_dir, f"data/processed/period-{date}.csv")

    df.to_csv(file_path, index=False)
    st.success("Changes saved successfully.")
    return

def add_column(df: pd.DataFrame, name: str, default_value="Delad") -> pd.DataFrame:
    """Initiate a Column if missing"""
    if name not in df.columns:
        df[name] = default_value
    return df


CATEGORY_KEYWORDS = {
    "Groceries": [
        "hemköp", "hemkop", "ica", "coop", "lidl", "willys", "willy",
        "netto", "city gross", "citygross", "maxi", "prisma", "mataffär",
        "bra mat", "saluhall", "matbutik", "snabbköp", "konsum",
    ],
    "Eating out": [
        "restaurang", "restaurant", "pizzeria", "mcdonalds", "mcdonald",
        "burger", "subway", "sushi", "café", "cafe", "bistro", "grill",
        "autogrill", "bar ", "pub ", "7-eleven", "pressbyrån", "pressbyran",
        "max hamburgare", "foodora", "wolt", "pizza",
    ],
    "Shopping": [
        "zara", "h&m", "ikea", "apple", "stadium", "elgiganten", "amazon",
        "kappahl", "lindex", "indiska", "asos", "zalando", "boozt",
        "webhallen", "komplett", "mediamarkt", "kicks", "åhléns", "ahléns",
    ],
}


def map_category(description: str) -> str:
    """Return a category based on keyword matching in the description."""
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Other"


def apply_category_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-fill the Category column using text matching on Beskrivning."""
    df["Category"] = df["Beskrivning"].apply(map_category)
    return df


def edit_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Allows user to edit 'Paid By' and 'Category' columns using Streamlit's data_editor"""
    edited_df = st.data_editor(
        df,
        column_config={
            "Paid By": st.column_config.SelectboxColumn(
                "Paid By",
                options=["Excludera", "Axel", "Ebba", "Utlägg", "Delad"],
                help="Select who paid for the item.",
            ),
            "Category": st.column_config.SelectboxColumn(
                "Category",
                options=["Shopping", "Groceries","Eating out", "Other"],
                help="Select expense category.",
            ),
        },
        disabled=[],
        hide_index=False,
    )
    return edited_df

def plot_expenses_by_category(df: pd.DataFrame):
    """Creates a stacked bar plot showing sum per category and person using Matplotlib"""
    df_filtered = df[df['Paid By'].isin(['Axel', 'Ebba', 'Utlägg', 'Delad'])]

    grouped = df_filtered.groupby(['Category', 'Paid By'], as_index=False)['Belopp'].sum()

    # Pivot for easier plotting
    pivot_df = grouped.pivot(index='Category', columns='Paid By', values='Belopp').fillna(0)

    # Reference (target) values per category
    targets = {
        "Groceries": 6000,
        "Shopping": 8000,
        "Eating out": 2000,
        "Other": 4000
    }

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(8, 5))

    # Plot stacked bars
    pivot_df.plot(kind='bar', stacked=True, ax=ax)

    # Add target bars behind each category
    for i, category in enumerate(pivot_df.index):
        if category in targets:
            target_value = targets[category]
            # Draw a horizontal dashed line at the target value for this category
            ax.plot([i - 0.4, i + 0.4], [target_value, target_value], "k--", lw=2, label="_nolegend_")
            ax.text(i, target_value + 200, f"Target: {target_value}", ha="center", va="bottom", fontsize=8, color="black")

    ax.set_title("Expenses per Category and Person", fontsize=14, pad=10)
    ax.set_xlabel("Category")
    ax.set_ylabel("Total Amount (SEK)")
    ax.grid(axis="y", linestyle="--", alpha=0.7)
    ax.legend(title="Paid By")
    plt.xticks(rotation=0)
    plt.tight_layout()

    st.pyplot(fig)

def calculate_who_pays_what(df: pd.DataFrame) -> dict:
    """
    Calculate how much Axel and Ebba each owe or should be paid back.
    """
    # Remove excluding transactions
    df = df[df['Paid By'] != 'Excludera']

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
    """Main scrpit"""
    uploaded_file = st.file_uploader("Upload a CSV file", type=["csv"])
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            df = lib.format_data(df)
            st.write("Data loaded and formatted successfully!")

            st.session_state.df = df
            data = st.session_state.df

            # Add missing columns
            data = add_column(data, "Paid By", "Delad")
            data = apply_category_mapping(data)

            if not data.empty:
                st.title("CSV File Viewer and Editor")
                st.subheader("Editable Data")

                edited_df = edit_columns(data)
                st.session_state.data = edited_df

                # Calculate button
                if st.button('Calculate expenses'):
                    result = calculate_who_pays_what(edited_df)
                    st.write("**Final Amounts to Pay or Be Refunded:**")
                    st.write(result)

                    # --- New: Plot per category/person ---
                    st.subheader("Expense Breakdown by Category and Person")
                    plot_expenses_by_category(edited_df)

                # Save changes button
                if st.button("Save Changes to CSV"):
                    save_csv(edited_df, date=date)

        except Exception as e:
            st.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()