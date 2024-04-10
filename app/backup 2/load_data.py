def load_data(file_path, sheet_name, index_col, package):
    pd = package
    
    # Check if the sheet_name exists in the Excel file
    xls = pd.ExcelFile(file_path)
    if sheet_name not in xls.sheet_names:
        raise ValueError(f"Worksheet named '{sheet_name}' not found in '{file_path}'. Available sheets are: {', '.join(xls.sheet_names)}")

    # Load data from the specified sheet
    data = pd.read_excel(file_path, sheet_name=sheet_name, index_col=index_col)
    data = data.loc['A':,:]
    return data
