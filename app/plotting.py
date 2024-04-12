def ELISA_plot(x_, y_, title, standards, fit, sample_names,limit_low,limit_high,analyte, four_PL_params):
    import plotly.graph_objects as go
    from IPython.display import display, HTML
    from math import log10
    from app.calculations import logistic4_x
    import streamlit as st
    title_text = {'ALB': 'Albumin concentration (ng/mL)', 'AAT': 'AAT concentration (ng/mL)', 'mAST':'mAST concentration (pg/mL)', 'BCA assay':'Protein concentration (ug/mL)'}  
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=fit[0], y=fit[1], name='Fit', mode='lines'))

    for std in standards.columns:
        if 'Standard' in std:
            fig.add_trace(go.Scatter(x=standards[std].index, y=standards[std], name=std, mode='markers'))

    # Configure plot layout, axes, and background
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20),
                      shapes=[dict(type="rect", xref="x", yref="y", x0='0', y0=str(limit_low), x1=max(standards.index)+100, y1=str(limit_high),
                                  fillcolor="limegreen", opacity=0.05, line_width=0, layer="above")],
                      yaxis=dict(titlefont=dict(size=20), tickfont=dict(size=16)),
                      xaxis=dict(titlefont=dict(size=20), tickfont=dict(size=16), tickangle=-45),
                      title=title, plot_bgcolor='rgb(255,255,255)',
                      xaxis_tickformat='.1f', yaxis_tickformat='.1f',yaxis_title='Absorbance',xaxis_title=title_text[analyte])

    # Update tick format and add spike lines
    fig.add_trace(go.Scatter(x=x_, y=y_, name='Samples', customdata=sample_names,
                             hovertemplate='<b>%{customdata}</b><br>Conc: %{x:.2f}, Abs: %{y:.2f}',
                             mode='markers', marker_symbol='x-thin', marker_line_width=2,
                             marker_line_color='#AB63FA', marker_size=7))

    A,B,C,D = four_PL_params
    fig.update_yaxes(showline=True, linewidth=1, linecolor='gray', mirror=True, showspikes=True, spikethickness=1,range=[A-0.2,D+0.2], showgrid=True, gridwidth=1, gridcolor='lightgray')
    # fig.update_xaxes(showline=True, linewidth=1, linecolor='gray', mirror=True, anchor='x2', showspikes=True, spikethickness=1,type='log',range=[log10(standards.index[-2]-3),log10(max(standards.index))+0.1], showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig.update_xaxes(showline=True, linewidth=1, linecolor='gray', mirror=True, anchor='x2', showspikes=True, spikethickness=1,type='log',range=[0.1,log10(max(standards.index))+0.1], showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig.add_vline(x=C, opacity=0.4, line=dict(color='green'))
    fig.add_hline(y=A, opacity=0.5, line=dict(color='red'))
    fig.add_hline(y=D, opacity=0.5, line=dict(color='red'))

    # Display the plot in Streamlit
    st.plotly_chart(fig, use_container_width=True)





def heatmap_plot(layout,data):# Define x and y axis labels
    import plotly.express as px
    import streamlit as st
    x_heat = list(range(1, 13))
    y_heat = list('ABCDEFGH')

    #fill in missing values
    layout = layout.fillna('')

    # Create heatmap plot
    fig = px.imshow(data, x=x_heat, y=y_heat, color_continuous_scale='Magma', aspect="auto",title='Absorbance measurements')

    # Add text annotations to heatmap cells
    fig.update_traces(text=layout, texttemplate="%{text}", hovertemplate="<b>%{y}%{x}</b><br>Sample: %{text}<br>Absorbance: %{z:.3f}")
    fig.update_xaxes(side="top")
    # Update x-axis and y-axis properties
    fig.update_xaxes(side="top", tickmode="array", tickvals=x_heat, showgrid=False)
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(fig, use_container_width=True)
