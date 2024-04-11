import streamlit as st
import io
import pandas as pd
from pathlib import Path
from app.calculations import (calculate_limits_of_linearity, fit_least_square, residuals,
                              logistic4_y, logistic4_x, calculate_ug_per_million_24h)
from app.plotting import ELISA_plot, heatmap_plot

css = '''
<style>
{
        min-width: 600px;
        max-width: 1200px;
    }
</style>
'''
st.markdown(css, unsafe_allow_html=True)


class Config:
    def __init__(self, title, analyte, N_STD_CURVES, DILUTION_FACTOR, VOLUME, CELL_NO, DURATION, std_curve_concs, file_path=None):
        self.title = title
        self.analyte = analyte
        self.N_STD_CURVES = N_STD_CURVES
        self.DILUTION_FACTOR = DILUTION_FACTOR
        self.VOLUME = VOLUME
        self.CELL_NO = CELL_NO
        self.DURATION = DURATION
        self.std_curve_concs = std_curve_concs
        self.file_path = file_path

def main():
    st.title("Rashid lab - 4PL analyser")
    st.markdown("""
        <style>
        .blueBox {
            background-color: #e7eff9;  /* Light blue background */
            border-left: 6px solid #2196f3;  /* Blue border */
            padding: 20px;  /* Some padding */
            margin: 10px 0;  /* Some margin */
        }
        </style>
        <div class="blueBox">
            <h3>Instructions for Use</h3>
            <ul>
                <li>Ensure you have an Excel file exported directly from the plate reader.</li>
                <li>The file should contain at least two sheets: 'Microplate End point' for the absorbance measurements and an additonal sheet created by you displaying the plate layout. This sheet should be named 'Layout'.</li>
                <li>Adjust the configuration settings below to match your experiment's setup.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # User inputs for configuration
    col1, col2 = st.columns(2)

    title = st.text_input("Experiment Title", "Experiment")
    with col1:
        analyte = st.selectbox("Select Analyte", ["ALB", "AAT", "mAST", "BCA assay"])
        N_STD_CURVES = st.number_input("Number of Standard Curves", min_value=1, max_value=2,value=2, step=1)
        DILUTION_FACTOR = st.number_input("Dilution Factor", value=50)
    with col2:
        VOLUME = st.number_input("Volume (microlitres)", value=100)
        CELL_NO = st.number_input("Cells per well", value=55000)
        DURATION = st.number_input("Incubation duration (hours)", value=48)
    
    std_curve_concs = {
        'AAT': [1000, 200, 40, 8, 1.6, 0.32, 0.064, 0],
        'ALB': [400, 200, 100, 50, 25, 12.5, 6.25, 0],
        'mAST': [10000, 5000, 2500, 1250, 625, 312.5, 156.25, 0],
        'BCA assay': [1500,1000,750,500,250,125,25,0]
    }

    # File uploader
    uploaded_file = st.file_uploader("Choose a file", type=['xlsx'])
    
    # Initialising experiment variable
    experiment = None
    
    # Processing data if file is uploaded
    if uploaded_file is not None:
        process_and_download(uploaded_file, title, analyte, N_STD_CURVES, DILUTION_FACTOR, VOLUME, CELL_NO, DURATION, std_curve_concs)

def load_data_from_memory(excel_io, sheet_name, index_col=None):
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
    data = pd.read_excel(xls, sheet_name=sheet_name, index_col=index_col)
    data = data.loc['A':, :]
    return data
    
def process_and_download(uploaded_file, title, analyte, N_STD_CURVES, DILUTION_FACTOR, VOLUME, CELL_NO, DURATION, std_curve_concs):
        # Read the uploaded file
        excel_io = io.BytesIO(uploaded_file.getvalue())
        excel_io.seek(0)
        
        if excel_io:
        # Attempt to load 'Microplate End point' data
            try:
                data = load_data_from_memory(excel_io, 'Microplate End point', index_col=[0])
                excel_io.seek(0)
            except ValueError as e:
                st.error(f"Failed to load 'Microplate End point' data: {e}")
                st.error("Please ensure that the 'Microplate End point' sheet is present in the uploaded file (default file from the plate reader).")
                return  # Exit the function early if data loading fails

            # Attempt to load 'Layout' data
            try:
                layout = load_data_from_memory(excel_io, 'Layout', index_col=[0])
                excel_io.seek(0)
            except ValueError as e:
                st.error(f"Failed to load 'Layout' data: {e}")
                st.error("Please ensure that the 'Layout' sheet is present in the uploaded file.")
                return  # Exit the function early if data loading fails

            # Calculate standard curve statistics
            std_curve_concs = pd.Series(std_curve_concs[analyte])

            std_curves = data.iloc[:, :N_STD_CURVES].set_index(std_curve_concs)
            std_curves = layout.iloc[0]
            std_curves.index.name = 'Concentration'
            std_curves.columns=[f'Standard {n+1}'for n in range(N_STD_CURVES)]
            std_curves['Mean'] = std_curves.mean(axis=1)
            std_curves['Standard Deviation'] = std_curves.std(axis=1)
            std_curves['CV (%)'] = std_curves['Standard Deviation'] / std_curves['Mean'] * 100
            std_curves['Acceptable (CV<20%)'] = std_curves['CV (%)'] < 10

            # Initial Parameter Guess
            A, B = std_curves.Mean.min(), std_curves.Mean.min() / 2
            C = (std_curves.Mean.max() + std_curves.Mean.min()) / 1.5
            D = std_curves.Mean.max() * 1.5
            p0 = [A, B, C, D]

            # Fit 4PL curve using least squares optimisation
            params = fit_least_square(residuals, p0, std_curves.Mean, std_curves.index)
            A, B, C, D = params
            x_fit = list(range(0, int(max(std_curve_concs)))) #smooth curve
            y_fit = logistic4_y(x_fit, A, B, C, D)

            y_samples = data.iloc[:, N_STD_CURVES:].values.flatten()
            sample_names = layout.iloc[:, N_STD_CURVES:].values.flatten()
            samples_df = pd.DataFrame({'name': sample_names,
                                    'absorbance': y_samples}).dropna()
            samples_df['interpolated_conc'] = samples_df['absorbance'].apply(lambda x: logistic4_x(x, A, B, C, D))
            limit_low, limit_high = calculate_limits_of_linearity(A, D)
            
            ELISA_plot(x_=samples_df.interpolated_conc,y_=samples_df.absorbance,
                title=title,
                standards=std_curves,
                fit=[x_fit,y_fit],
                sample_names=samples_df.name,
                limit_low=limit_low,
                limit_high=limit_high,
                analyte=analyte,
                four_PL_params=params)

            heatmap_plot(layout,data)

            #samples_df['ug_1e6_24h'] = calculate_ug_per_million_24h(samples_df['interpolated_conc'], VOLUME, CELL_NO, DURATION, DILUTION_FACTOR)
            samples_df['within_range'] = samples_df['absorbance'].apply(lambda x: limit_low < x < limit_high)
            
            # print(std_curves)
            # print(f'4PL Parameters:\n{params}')
            samples_df = samples_df.sort_values(by=['within_range', 'name'], ascending=[False, True])

            metadata_df = pd.DataFrame({'title': [title], 'analyte': [analyte], 'N_STD_CURVES': [N_STD_CURVES], 'DILUTION_FACTOR': [DILUTION_FACTOR], 'VOLUME': [VOLUME], 'CELL_NO': [CELL_NO], 'DURATION': [DURATION]})
                    
            with pd.ExcelWriter(excel_io, engine='openpyxl', mode='a') as writer:
                samples_df.to_excel(writer, sheet_name=f'Sample concentrations')
                std_curves.to_excel(writer, sheet_name=f'Standard curves')
                metadata_df.to_excel(writer, sheet_name=f'Metadata')
                

            excel_io.seek(0)

            # Provide the edited file for download
            st.download_button(label="Download Excel file with results",
                       data=excel_io,
                       file_name=f"Interpolated_{uploaded_file.name}",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    main()
