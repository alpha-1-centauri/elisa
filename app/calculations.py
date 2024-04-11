import numpy as np
from scipy.optimize import leastsq

def calculate_limits_of_linearity(A, D):
    # Calculate limits of linear range (Sebaugh & McCray, 2003)
    #Sebaugh, J.L. and McCray, P.D. (2003), Defining the linear portion of a sigmoid-shaped curve: bend points. 
    #Pharmaceut. Statist., 2: 167-174. https://doi.org/10.1002/pst.62

    # A = maximum value of the curve
    # D = minimum value of the curve

    k = 4.680498579882905  # Constant value as per Sebaugh & McCray (2003)
    limit_low = (A-D) / (1 + 1/k) + D
    limit_high = (A-D) / (1 + k) + D
    return limit_low, limit_high

def fit_least_square(resid, p, y, x):
    return leastsq(resid, p, args=(y, x))[0]

def logistic4_y(x, A, B, C, D):
    print('log4y',x)
    x,A,B,C,D = np.array(x),float(A),float(B),float(C),float(D)
    return ((A-D) / (1.0 + ((x / C)**B))) + D

def logistic4_x(y, A, B, C, D):
    print('log4x',x)
    y, A, B, C, D = np.array(y), float(A), float(B), float(C), float(D)
    """Inverse 4PL logistic equation."""
    output = C * ((A-D)/(y-D) - 1)**(1/B)
    output = np.array(output)
    output[np.iscomplex(output)] = np.nan
    return output

def residuals(p, y, x):
    fitted_values = logistic4_y(x, *p)
    res = y - fitted_values
    return res

def calculate_ug_per_million_24h(conc, volume, cell_no, duration, dil_factor):
    vol_ml = volume / 1000
    ng = conc * vol_ml
    ug = ng / 1000
    million_cells = cell_no / 1e6
    duration_24h = duration / 24
    return ug / million_cells / duration_24h * dil_factor
