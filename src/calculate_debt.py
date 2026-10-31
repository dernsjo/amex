import os
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import streamlit as st
from decimal import Decimal
from spending_core import (
    DEFAULT_CATEGORIES,
    DEFAULT_TARGETS_SEK,
    Allocation,
    Line,
    allocation_from_label,
    categorize,
    format_minor,
    settle,
    to_minor,
)
import lib

MEMBERS = ["Axel", "Ebba"]

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


def apply_category_mapping(df: pd.DataFrame) -> pd.DataFrame:
    """Pre-fill the Category column using text matching on Beskrivning."""
    df["Category"] = df["Beskrivning"].apply(categorize)
    return df


def edit_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Allows user to edit 'Paid By' and 'Category' columns using Streamlit's data_editor"""
    edited_df = st.data_editor(
        df,
        column_config={
            "Paid By": st.column_config.SelectboxColumn(
                "Paid By",
                options=["Excludera", *MEMBERS, "Utlägg", "Delad"],
                help="Select who paid for the item.",
            ),
            "Category": st.column_config.SelectboxColumn(
                "Category",
                options=DEFAULT_CATEGORIES,
                help="Select expense category.",
            ),
        },
        disabled=[],
        hide_index=False,
    )
    return edited_df

def plot_expenses_by_category(df: pd.DataFrame):
    """Creates a stacked bar plot showing sum per category and person using Matplotlib"""
    df_filtered = df[df['Paid By'].isin([*MEMBERS, 'Utlägg', 'Delad'])]

    grouped = df_filtered.groupby(['Category', 'Paid By'], as_index=False)['Belopp'].sum()

    # Pivot for easier plotting
    pivot_df = grouped.pivot(index='Category', columns='Paid By', values='Belopp').fillna(0)

    targets = DEFAULT_TARGETS_SEK

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
    lines = [
        Line(to_minor(Decimal(str(amount))), *allocation_from_label(paid_by, MEMBERS))
        for amount, paid_by in zip(df['Belopp'], df['Paid By'])
    ]
    result = settle(lines, dict.fromkeys(MEMBERS, 1))
    kr = lambda minor: float(format_minor(minor))

    return {
        'Axel': kr(result.per_member['Axel']),
        'Ebba': kr(result.per_member['Ebba']),
        'Utlägg': kr(result.outlay),
        'Totalt': kr(result.total),
        'Controll': kr(sum(l.amount_minor for l in lines if l.allocation != Allocation.EXCLUDED))
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