# Chirp-Scan Fit: Conversion from GDD to Spectral Phase

## Problem

The chirp-scan fit returns the compensating group-delay dispersion as a polynomial of the angular
frequency offset:

```text
D(Ω) = a0 + a1 Ω + a2 Ω² + a3 Ω³ + ...
```

The current GUI code scales these polynomial coefficients and directly stores them as the beam phase
derivatives:

```python
coeffs_scaled = [coeffs[i] * (10**15)**i for i in range(len(coeffs))]
self.last_temp_fit_coeffs = np.concatenate(([0, 0], coeffs_scaled))
```

This is correct for GDD and TOD, but not for FOD or any higher order. The fitted coefficients are
ordinary power-series coefficients, whereas `Beam` stores spectral-phase derivatives and applies the
Taylor-series factorials when generating the SLM phase.

## Physical interpretation

The spectral phase around the carrier frequency is written as:

```text
φ(Ω) = φ0 + φ1 Ω + φ2 Ω²/2! + φ3 Ω³/3! + φ4 Ω⁴/4! + ...
```

Its second derivative is the local GDD:

```text
φ''(Ω) = φ2 + φ3 Ω + φ4 Ω²/2! + φ5 Ω³/3! + ...
```

Comparing this expression with the fitted polynomial gives:

```text
φ(i+2) = i! × ai
```

Therefore, the fitted power-series coefficient `ai` is not directly the corresponding phase
derivative for `i >= 2`.

| Fitted term | Physical quantity | Required conversion | Current result |
| --- | --- | --- | --- |
| `a0` | GDD (`φ2`) | `0! × a0 = a0` | Correct |
| `a1` | TOD (`φ3`) | `1! × a1 = a1` | Correct |
| `a2` | FOD (`φ4`) | `2! × a2` | Too small by 2 |
| `a3` | Fifth-order dispersion (`φ5`) | `3! × a3` | Too small by 6 |
| `a4` | Sixth-order dispersion (`φ6`) | `4! × a4` | Too small by 24 |

A fitted curve can still look correct because it is evaluated using the original `ai` coefficients.
The error appears later, when those same numbers are interpreted as phase derivatives and applied to
the SLM. Visual agreement between the ridge and the fitted GDD curve therefore does not validate the
applied compression phase.

## Recommendation

After fitting the GDD on a frequency axis expressed in `rad/fs`, convert the ordinary polynomial
coefficients into phase derivatives before assigning them to the beam:

```python
import math

gdd_power_coeffs = np.polynomial.polynomial.polyfit(
    omega_shifted_fs,
    max_chirp_values,
    degree,
)

phase_derivative_coeffs = np.array([
    math.factorial(i) * coefficient
    for i, coefficient in enumerate(gdd_power_coeffs)
])

self.last_temp_fit_coeffs = np.concatenate((
    [0.0, 0.0],
    phase_derivative_coeffs,
))
```

The two leading zeros represent the constant phase and group delay, which cannot be recovered from a
GDD measurement. `Beam` can then apply its existing Taylor prefactors when sampling the phase for the
SLM.

The sign should be handled separately from the factorial conversion. In the current workflow, the
scan applies each candidate chirp relative to the existing optimal phase. The chirp value that
maximizes SHG is therefore the additional compensation to apply, so adding it to the stored optimal
phase is consistent with that convention. This sign convention should be confirmed with a known
positive or negative dispersive sample.

## Suggested verification

Add a synthetic test starting from known phase derivatives, for example:

```text
GDD = 1000 fs²
TOD = 5000 fs³
FOD = 12000 fs⁴
```

Generate the expected local GDD curve:

```text
D(Ω) = 1000 + 5000 Ω + (12000 / 2!) Ω²
```

Fit that curve, perform the factorial conversion, and verify that the recovered phase coefficients
are `[0, 0, 1000, 5000, 12000]`. The test should also evaluate the reconstructed phase on the same
frequency grid and compare it with the phase applied by `Beam`.

Finally, validate the sign experimentally with a material whose GDD is independently known. The
assigned correction should increase the integrated SHG signal or reduce the independently measured
pulse duration.
