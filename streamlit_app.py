import streamlit as st
import io
import pandas as pd
from pathlib import Path
from app.load_data import load_data
from app.calculations import (calculate_limits_of_linearity, fit_least_square, residuals,
                              logistic4_y, logistic4_x, calculate_ug_per_million_24h)
from app.plotting import ELISA_plot, heatmap_plot

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
    st.title("Rashid lab - 4 parameter logistic curve fitting for ELISA data analysis")
    
    # User inputs for configuration
    title = st.text_input("Experiment Title", "SEN06B-ALB_ELISA")
    analyte = st.selectbox("Select Analyte", ["ALB", "AAT", "mAST"])
    N_STD_CURVES = st.number_input("Number of Standard Curves", min_value=1, value=2, step=1)
    DILUTION_FACTOR = st.number_input("Dilution Factor", value=50)
    VOLUME = st.number_input("Volume (microlitres)", value=100)
    CELL_NO = st.number_input("Cells per well", value=55000)
    DURATION = st.number_input("Duration (hours)", value=48)
    
    std_curve_concs = {
        'AAT': [1000, 200, 40, 8, 1.6, 0.32, 0.064, 0],
        'ALB': [400, 200, 100, 50, 25, 12.5, 6.25, 0],
        'mAST': [10000, 5000, 2500, 1250, 625, 312.5, 156.25, 0]
    }

    # File uploader
    uploaded_file = st.file_uploader("Choose a file", type=['xlsx'])
    
    # Initialising experiment variable
    experiment = None
    
    # Processing data if file is uploaded
    if uploaded_file is not None:
        file_path = Path(uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        experiment = Config(title, analyte, N_STD_CURVES, DILUTION_FACTOR, VOLUME, CELL_NO, DURATION, std_curve_concs, file_path)
        process_data(experiment)

    
def process_data(experiment):
        if experiment.file_path:

            # The rest of your processing code goes here
            # For instance, load data:
            data = load_data(experiment.file_path, 'Microplate End point', [0], package=pd)
            layout = load_data(experiment.file_path, 'Layout', [0], package=pd)

            # Calculate standard curve statistics
            std_curve_concs = pd.Series(experiment.std_curve_concs[experiment.analyte])
            std_curves = data.iloc[:, :experiment.N_STD_CURVES].set_index(std_curve_concs)
            std_curves.index.name = 'Concentration'
            std_curves.columns=[f'Standard {n+1}'for n in range(experiment.N_STD_CURVES)]
            std_curves['average'] = std_curves.mean(axis=1)
            std_curves['std'] = std_curves.std(axis=1)
            std_curves['cv'] = std_curves['std'] / std_curves['average'] * 100
            std_curves['acceptable (cv<20%)'] = std_curves['cv'] < 10

            # Initial Parameter Guess
            A, B = std_curves.average.min(), std_curves.average.min() / 2
            C = (std_curves.average.max() + std_curves.average.min()) / 1.5
            D = std_curves.average.max() * 1.5
            p0 = [A, B, C, D]

            # Fit 4PL curve using least squares optimisation
            params = fit_least_square(residuals, p0, std_curves.average, std_curves.index)
            A, B, C, D = params
            x_fit = list(range(0, int(max(std_curve_concs)))) #smooth curve
            y_fit = logistic4_y(x_fit, A, B, C, D)

            y_samples = data.iloc[:, experiment.N_STD_CURVES:].values.flatten()
            sample_names = layout.iloc[:, experiment.N_STD_CURVES:].values.flatten()
            samples_df = pd.DataFrame({'name': sample_names,
                                    'absorbance': y_samples}).dropna()
            samples_df['interpolated_conc'] = samples_df['absorbance'].apply(lambda x: logistic4_x(x, A, B, C, D))
            limit_low, limit_high = calculate_limits_of_linearity(A, D)
            
            ELISA_plot(x_=samples_df.interpolated_conc,y_=samples_df.absorbance,
                title=experiment.title+' ELISA',
                standards=std_curves,
                fit=[x_fit,y_fit],
                sample_names=samples_df.name,
                limit_low=limit_low,
                limit_high=limit_high,
                analyte=experiment.analyte,
                four_PL_params=params)

            heatmap_plot(layout,data)

            samples_df['ug_1e6_24h'] = calculate_ug_per_million_24h(samples_df['interpolated_conc'], experiment.VOLUME, experiment.CELL_NO, experiment.DURATION, experiment.DILUTION_FACTOR)
            samples_df['within_range'] = samples_df['absorbance'].apply(lambda x: limit_low < x < limit_high)
            
            print(std_curves)
            print(f'4PL Parameters:\n{params}')
            samples_df = samples_df.sort_values(by=['within_range', 'name', 'ug_1e6_24h'], ascending=[False, True, False])

            metadata_df = pd.DataFrame({'title': [experiment.title], 'analyte': [experiment.analyte], 'N_STD_CURVES': [experiment.N_STD_CURVES], 'DILUTION_FACTOR': [experiment.DILUTION_FACTOR], 'VOLUME': [experiment.VOLUME], 'CELL_NO': [experiment.CELL_NO], 'DURATION': [experiment.DURATION]})
                    
            def create_excel_in_memory(samples_df, std_curves, metadata_df):
                # Use a BytesIO buffer as a file-like object
                output = io.BytesIO()

                # Write dataframes to different sheets in the same Excel file
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    samples_df.to_excel(writer, sheet_name='Sample Data')
                    std_curves.to_excel(writer, sheet_name='Standard Curves')
                    metadata_df.to_excel(writer, sheet_name='Metadata', index=False)

                # Move back to the beginning of the BytesIO buffer
                output.seek(0)
                return output

            @st.cache
            def get_excel_file_as_bytes(samples_df, std_curves, metadata_df):
                return create_excel_in_memory(samples_df, std_curves, metadata_df).getvalue()

            # Assuming your DataFrames are ready to be written to the Excel file
            # samples_df, std_curves, metadata_df = get_your_dataframes_here()

            # Get the Excel file as bytes, cached by Streamlit
            excel_bytes = get_excel_file_as_bytes(samples_df, std_curves, metadata_df)

            # Create a download button for the Excel file
            st.download_button(label="Download Excel File",
                            data=excel_bytes,
                            file_name="experiment_results.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            return samples_df.sort_values(by='ug_1e6_24h')

if __name__ == "__main__":
    main()
