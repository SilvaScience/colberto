# Review Guide: Unified Site Configuration

## Purpose

This pull request replaces scattered and hard-coded installation settings with one Colberto
configuration file per site:

- `config/udem.ini`
- `config/wfu.ini`

The active site is selected with the `COLBERTO_SITE` environment variable. When the variable is not
set, Colberto defaults to UdeM.

The Stresing `vendor_config` file remains external because it is maintained by the vendor software.
Its path is declared in the Colberto site configuration; calibration values are not duplicated in
that external file.

## Suggested Review Order

1. Review `src/configuration.py` and both site files. Confirm that required settings are validated
   before hardware initialization.
2. Review `src/drivers/Instruments.py`. Confirm that the selected site controls device availability,
   drivers, ports, calibration dictionaries and default spectrometer priority.
3. Review the constructor changes in the SLM, monochromator, cryostat, Pixis and Stresing drivers.
   Drivers should receive installation settings instead of selecting a site themselves.
4. Review `src/main.py` and `src/DataHandling/`. Confirm that data and temporary-file paths come from
   the active site configuration.
5. Confirm that the obsolete per-driver UdeM/WFU configuration copies were removed and that no
   production code still references them.

## Automated Checks

Run from the repository root:

```powershell
python -m unittest discover -s tests -v
python -c "import sys; sys.path.insert(0, 'src'); import drivers.Instruments"
git diff --check origin/katie/wfu-integration-clean...HEAD
```

The configuration test suite should validate both sites, environment-variable selection, missing
settings, invalid typed values and unsupported drivers.

## Hardware Checks

Perform these checks once at each site:

```powershell
$env:COLBERTO_SITE = "udem"  # Use "wfu" at Wake Forest
python src/main.py
```

Verify the following:

- The log identifies the expected site and does not report a missing configuration section.
- The correct SLM driver, bit depth and LUT are loaded.
- UdeM uses the SpectraPro monochromator; WFU uses the Shamrock implementation.
- The monochromator panel lists the expected gratings and shows the current grating.
- Stresing and Pixis report the expected detector dimensions and wavelength axes.
- A single-spectrum acquisition succeeds and produces a physically reasonable wavelength scale.
- The default spectrometer priority is respected when several cameras are connected.
- Data saving and the temporary HDF5 buffer use the configured paths.
- Disabling an optional device in `[devices]` prevents a real connection attempt and preserves the
  expected demo fallback where applicable.

## Values Requiring Site Confirmation

The following WFU values were taken from the information available in the original branch and
should be confirmed on the physical installation:

- cryostat port: `COM9`;
- SpectraPro serial placeholder: `COM5`;
- oscilloscope address: `169.254.75.129`;
- Shamrock grating density: `150 lines/mm`;
- Stresing vendor configuration: `C:\Program Files\Stresing\Escam\config.ini`.

Also confirm that the DLL and LUT paths in both site files match the installed Meadowlark software.

## Acceptance Criteria

The pull request is ready to merge when automated checks pass, both site files have been reviewed by
their local users, the grating list is visible at both sites, and one real spectrum has been acquired
successfully at UdeM and WFU.
