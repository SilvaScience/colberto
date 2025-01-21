import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

# Lire le fichier CSV
data = pd.read_csv('Raw3.csv')
x = data['x'].values  # indices de 0 à 255
y = data['y'].values  # intensité normalisée de 0 à 1

# Trouver les deux premiers maxima
peaks = np.argsort(y)[-2:]  # indices des deux premiers maxima
peak1, peak2 = sorted(peaks)

# Calculer les indices associés dans le LUT linéaire
lut_linear = np.linspace(0, 4080, 256)
v1, v2 = lut_linear[peak1], lut_linear[peak2]

# Transformer la section non linéaire en linéaire (0 à 2π) en utilisant arcsin
linear_section = np.arcsin(y[peak1:peak2])
linear_section = (linear_section - np.min(linear_section)) / (np.max(linear_section) - np.min(linear_section))

# Interpolation des valeurs de voltage
interp_func = interp1d([0, 1], [v1, v2])
voltage_values = interp_func(linear_section)

# Générer le fichier LUT avec interpolation linéaire
lut_values = np.interp(np.arange(256), [peak1, peak2], [v1, v2])

# Sauvegarder le LUT dans un fichier
lut_df = pd.DataFrame({'Index': np.arange(256), 'Voltage': lut_values})
lut_df.to_csv('output.lut', index=False, header=False)