import pandas as pd
import streamlit as st
def load_data_from_memory(excel_io, sheet_name, index_col=None,dtypes=None):
    try:
        # Read the Excel file from the BytesIO object
        xls = pd.ExcelFile(excel_io)
    except ValueError as e:
        st.error(f"Error reading the Excel file: {e}")
        return None

    # Check if the sheet_name exists in the Excel file
    if sheet_name not in xls.sheet_names:
        st.error(f"Worksheet named '{sheet_name}' not found. Available sheets are: {', '.join(xls.sheet_names)}")
        return None

    # Load data from the specified sheet
    data = pd.read_excel(xls, sheet_name=sheet_name, index_col=index_col, dtype=dtypes)
    data = data.loc['A':, :]
    return data
