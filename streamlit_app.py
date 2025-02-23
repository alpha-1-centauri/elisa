import streamlit as st
import numpy as np
import io
import pandas as pd
from pathlib import Path
from app.calculations import (calculate_limits_of_linearity, fit_least_square, residuals,
                              logistic4_y, logistic4_x, calculate_ug_per_million_24h)
from app.plotting import ELISA_plot, heatmap_plot
from app.load_data import load_data_from_memory

css='''
<style>
    section.main > div {max-width:90rem}
</style>
'''
st.markdown(css, unsafe_allow_html=True)

class Config:
    def __init__(self, title, analyte, N_STD_CURVES, DILUTION_FACTOR, VOLUME, CELL_NO, DURATION, std_curve_concentrations, file_path=None):
        self.title = title
        self.analyte = analyte
        self.N_STD_CURVES = N_STD_CURVES
        self.DILUTION_FACTOR = DILUTION_FACTOR
        self.VOLUME = VOLUME
        self.CELL_NO = CELL_NO
        self.DURATION = DURATION
        self.std_curve_concentrations = std_curve_concentrations
        self.file_path = file_path

def main():
    #tab1 = st.tabs(['Four parameter logistic curve','Label generation','Min max viability scaling'])

    
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
                <li>Ensure you have an Excel file exported directly from the plate reader FLUOstar OMEGA.</li>
                <li>The file should contain at least two sheets: 'Microplate End point' for the absorbance measurements and an additonal sheet created by you displaying the plate layout. This sheet should be named 'Layout'.</li>
                <li>Adjust the configuration settings below to match your experiment's setup.</li>
                <li>Standards should be run in the first columns of the 'Microplate End point' sheet.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # User inputs for configuration
    st.header('⚙️ Configuration', divider='blue')
    title=st.text_input("Experiment Title", "Experiment")
    col1, col2, col3 = st.columns(3)
    with col1:
        analyte = st.selectbox("Select Analyte", ["ALB", "AAT", "mAST", "BCA assay"])
        DILUTION_FACTOR = st.number_input("Dilution Factor", value=50)
    with col2:
        N_STD_CURVES = st.number_input("Number of Standard Curves", min_value=1, max_value=2,value=2, step=1)
        CELL_NO = st.number_input("Cells per well", value=55000)
    with col3:
        VOLUME = st.number_input("Volume (microlitres)", value=100)
        DURATION = st.number_input("Incubation duration (hours)", value=48)
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a file", type=['xlsx'])
    
    # Processing data if file is uploaded
    if uploaded_file is not None:
        process_and_download(uploaded_file, title, analyte, N_STD_CURVES, DILUTION_FACTOR, VOLUME, CELL_NO, DURATION)

def process_and_download(uploaded_file, title, analyte, N_STD_CURVES, DILUTION_FACTOR, VOLUME, CELL_NO, DURATION):
        # Read the uploaded file
        excel_io = io.BytesIO(uploaded_file.getvalue())
        excel_io.seek(0)
        
        if excel_io:
        # Attempt to load 'Microplate End point' data
            try:
                data = load_data_from_memory(excel_io, 'Microplate End point', index_col=[0], dtypes=float)
                excel_io.seek(0)
            except ValueError as e:
                st.error(f"Failed to load 'Microplate End point' data: {e}")
                st.error("Please ensure that the 'Microplate End point' sheet is present in the uploaded file (default file from the plate reader).")
                return  # Exit the function early if data loading fails
            # Attempt to load 'Layout' data
            try:
                layout = load_data_from_memory(excel_io, 'Layout', index_col=[0], dtypes=str)
                excel_io.seek(0)
            except ValueError as e:
                st.error(f"Failed to load 'Layout' data: {e}")
                st.error("Please ensure that the 'Layout' sheet is present in the uploaded file.")
                return  # Exit the function early if data loading fails

            # Calculate standard curve statistics
            # std_curve_concentrations = pd.Series(std_curve_concentrations[analyte]).astype(float, errors='ignore')
            std_curve_concentrations = layout.iloc[:,0]
            print(layout)

            std_curves = data.iloc[:, :N_STD_CURVES].set_index(std_curve_concentrations)
            print(std_curves)
    
            std_curves.index.name = 'Concentration'
            std_curves.columns=[f'Standard {n+1}'for n in range(N_STD_CURVES)]
            std_curves['Mean'] = std_curves.mean(axis=1)
            std_curves['Standard Deviation'] = std_curves.std(axis=1)
            std_curves['CV (%)'] = std_curves['Standard Deviation'] / std_curves['Mean'] * 100
            std_curves['Acceptable (CV<20%)'] = std_curves['CV (%)'] < 10

            # Initial Parameter Guess
            A, B = std_curves.Mean.min(), std_curves.Mean.min() / 3
            C = (std_curves.Mean.max() + std_curves.Mean.min()) / 1.5
            D = std_curves.Mean.max() * 1.5
            p0 = [A, B, C, D]
            print(p0)

            # Fit 4PL curve using least squares optimisation
            params = fit_least_square(residuals, p0, std_curves.Mean, std_curves.index)
            A, B, C, D = params
            x_fit = list(range(0, int(max(std_curve_concentrations)))) #smooth curve
            y_fit = logistic4_y(x_fit, A, B, C, D)

            y_samples = data.iloc[:, N_STD_CURVES:].values.flatten()
            sample_names = layout.iloc[:, N_STD_CURVES:].values.flatten()
            samples_df = pd.DataFrame({'name': sample_names,
                                    'absorbance': y_samples}).dropna()
            samples_df['interpolated_conc'] = samples_df['absorbance'].apply(lambda x: logistic4_x(x, A, B, C, D))
            limit_low, limit_high = calculate_limits_of_linearity(A, D)
            
            st.header('Standard curves', divider='blue')
            
            def tickbox_formatter(x):
                if isinstance(x, bool):
                    if x:
                        return '✅'
                    else:
                        return '❌'
                else:
                    return x
            
            st.dataframe(std_curves.applymap(tickbox_formatter))

            ELISA_plot(x_=samples_df.interpolated_conc,y_=samples_df.absorbance,
                title=title,
                standards=std_curves,
                fit=[x_fit,y_fit],
                sample_names=samples_df.name,
                limit_low=limit_low,
                limit_high=limit_high,
                analyte=analyte,
                four_PL_params=params)
            
            with st.container():
                # Use markdown with inline styles for the faint red box
                st.markdown("""
                <style>
                .bluebox {
                    border: 1px solid #a4c8ff;  /* Light blue border */
                    background-color: #ecf4ff;  /* Very light blue background */
                    border-radius: 5px;
                    padding: 10px;
                }S
                </style>
                """, unsafe_allow_html=True)

                st.subheader("📉 Limits of Linearity (Sebaugh & McCray, 2003)", divider='blue')
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"""
                    <div class="bluebox">
                    <b>🔽 Lower Limit</b><br>
                    Absorbance: {limit_low:.2f}<br>
                    Concentration: {logistic4_x(limit_low, A, B, C, D):.2f}
                    </div>
                    """, unsafe_allow_html=True)

                with col2:
                    st.markdown(f"""
                    <div class="bluebox">
                    <b>🔼 Upper Limit</b><br>
                    Absorbance: {limit_high:.2f}<br>
                    Concentration: {logistic4_x(limit_high, A, B, C, D):.2f}
                    </div>
                    """, unsafe_allow_html=True)

            st.header('🔥 Plate heatmap', divider='blue')
            heatmap_plot(layout,data)

            #samples_df['ug_1e6_24h'] = calculate_ug_per_million_24h(samples_df['interpolated_conc'], VOLUME, CELL_NO, DURATION, DILUTION_FACTOR)
            samples_df['within_range'] = samples_df['absorbance'].apply(lambda x: limit_low < x < limit_high)
            samples_df = samples_df.sort_values(by=['within_range', 'name'], ascending=[False, True])
            samples_df.columns = ['Sample', 'Absorbance', 'Interpolated conc. (ng/mL)', 'Within LR?']
            samples_df['Dil. Factor (X)'] = DILUTION_FACTOR
            samples_df['Adj. concentration (ng/mL)'] = samples_df['Interpolated conc. (ng/mL)'] * DILUTION_FACTOR
            samples_df['Incubation vol. (uL)'] = VOLUME
            samples_df['Analyte amt (ng)'] = samples_df['Adj. concentration (ng/mL)'] * VOLUME/1000
            samples_df['Cells/well'] = CELL_NO
            samples_df['ng/1e6 cells'] = samples_df['Analyte amt (ng)'] / (CELL_NO/1e6)
            samples_df['Duration (h)'] = DURATION
            samples_df['ug/1e6 cells/24h'] = samples_df['ng/1e6 cells'] / (DURATION/24)/1000
    

            st.header('📶 Results', divider='blue')

            st.markdown(f"**Samples within linear range (LR) ({limit_low:.2f} - {limit_high:.2f})**")
            st.dataframe(samples_df[samples_df['Within LR?']==True].map(tickbox_formatter),height=samples_df[samples_df['Within LR?']==True].shape[0]*35)
   
            st.markdown(f"**Samples outside linear range (LR)**")
            st.dataframe(samples_df[samples_df['Within LR?']==False].map(tickbox_formatter),height=1000)

            st.subheader('📥 Download', divider='blue')
            
            metadata_df = pd.DataFrame({'title': [title], 'analyte': [analyte], 'N_STD_CURVES': [N_STD_CURVES], 'DILUTION_FACTOR': [DILUTION_FACTOR], 'VOLUME': [VOLUME], 'CELL_NO': [CELL_NO], 'DURATION': [DURATION]})
                    
            with pd.ExcelWriter(excel_io, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                layout.to_excel(writer, sheet_name=f'Layout')
                samples_df.to_excel(writer, sheet_name=f'Sample concentrations')
                std_curves.to_excel(writer, sheet_name=f'Standard curves')
                metadata_df.to_excel(writer, sheet_name=f'Metadata')
                
            excel_io.seek(0)

            # Provide the edited file for download
            st.download_button(label="**Download Excel file with results**",
                    data=excel_io,
                    file_name=f"Interpolated_{uploaded_file.name}",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="pri