# Chirp-Scan Polynomial Fit: Numerical Conditioning

## Problem

The chirp-scan analysis fits the measured optimal chirp as a polynomial of angular frequency:

```python
coeffs = np.polyfit(omega_shifted, max_chirp_values, degree)
```

Here, `omega_shifted` is expressed in `rad/s` and typically has values around `10^14`. Raising these
values to powers of five or more produces columns with extremely different numerical scales. The
resulting Vandermonde matrix is ill-conditioned, so small measurement noise or rounding errors can
cause very large changes in the fitted coefficients.

For a representative SHG range of 350–450 nm and a fifth-order fit, the condition number is about
`1.8e72`. Scaling the frequency axis to `fs^-1` reduces it to approximately `1.1e4`.

This problem may not be obvious in the fitted curve: the curve can pass through the measured maxima
while the reported GDD, TOD, FOD, and higher-order coefficients are unstable or physically wrong.

## Physical interpretation

The chirp scan estimates the compensating group-delay dispersion as a function of the fundamental
angular frequency:

```text
D(Ω) = a0 + a1 Ω + a2 Ω² + ...
```

where `Ω = ω - ω0`. The SHG spectrometer measures `2ω`, so the current factor of `0.5` used to recover
the fundamental frequency is appropriate when the recorded wavelength axis is the SHG wavelength.

Changing the numerical frequency unit from `rad/s` to `rad/fs` does not change the physics. It only
expresses the same frequency offset on a scale close to unity:

```text
Ω_fs = Ω_s × 10^-15
```

The resulting coefficients are then naturally expressed using femtosecond units and are much less
sensitive to floating-point errors.

## Recommendation

Perform the fit on the scaled frequency axis and use the ascending-order polynomial API:

```python
omega_values = 0.5 * co.waveToAngFreq(wavelength_values * 1e-9)
omega_carrier = co.waveToAngFreq(carrier_wavelength * 1e-9)
omega_shifted_fs = (omega_values - omega_carrier) * 1e-15

coeffs = np.polynomial.polynomial.polyfit(
    omega_shifted_fs,
    max_chirp_values,
    degree,
)

fit_values = np.polynomial.polynomial.polyval(
    omega_shifted_fs,
    coeffs,
)
```

With this convention:

- `coeffs` is already ordered from the constant term upward;
- the later multiplication by `(10**15)**i` must be removed;
- the carrier frequency remains the physical expansion point;
- the fit should reject non-finite data and require at least `degree + 1` valid points;
- polynomial orders should normally remain low, typically between one and three, unless residuals
  and independent validation justify a higher order.

The conversion from the fitted local GDD polynomial to the spectral-phase derivative coefficients is
a separate step and must still apply the appropriate factorial factors for FOD and higher orders.

## Suggested verification

Add a synthetic regression test with known GDD, TOD, and FOD. Generate a smooth ridge with controlled
noise, fit it using the scaled frequency axis, and verify both the reconstructed coefficients and the
phase applied to the SLM. The test should also confirm that the result remains stable when small noise
is added or the wavelength sampling is changed.
