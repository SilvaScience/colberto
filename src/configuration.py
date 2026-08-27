"""Load and validate the configuration for a Colberto installation site."""

import configparser
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_DIR = PROJECT_ROOT / "config"
SITE_ENVIRONMENT_VARIABLE = "COLBERTO_SITE"
DEFAULT_SITE = "udem"

REQUIRED_OPTIONS = {
    "site": ("name", "default_data_directory", "default_filename", "temp_data_file", "spectrometer_priority"),
    "devices": ("cryostat", "slm", "monochromator", "stresing", "pixis", "ocean", "oscilloscope", "demo"),
    "cryostat": ("driver", "port"),
    "slm": (
        "driver_name", "c_wrapper", "image_gen", "lut_file", "rgb",
        "is_eight_bit_image", "height", "width", "depth", "bytes_per_pixel",
    ),
    "stresing": (
        "driver", "vendor_config", "pixel_size_mm", "num_pixels", "calibrated",
        "calibration_third_order", "calibration_second_order",
        "calibration_first_order", "calibration_offset",
    ),
    "monochromator": ("driver", "serial_port", "baud_rate", "center_wavelength", "grating_densities"),
    "stresing_optics": ("f", "delta", "gamma", "n0", "offset_adjust", "d_grating", "x_pixel", "curvature"),
    "pixis": ("driver", "pixel_size_mm", "num_pixels", "sensor_height", "calibrated"),
    "pixis_optics": ("focal_length_mm", "f", "delta", "gamma", "n0", "offset_adjust", "d_grating", "x_pixel", "curvature"),
    "oscilloscope": ("driver", "ip_address"),
}


class SiteConfigurationError(ValueError):
    """Raised when a site configuration is absent or incomplete."""


def load_site_config(site=None, config_dir=None):
    """Return the validated configuration selected explicitly or through COLBERTO_SITE."""
    selected_site = (site or os.environ.get(SITE_ENVIRONMENT_VARIABLE, DEFAULT_SITE)).strip().lower()
    if not selected_site or not selected_site.replace("-", "").replace("_", "").isalnum():
        raise SiteConfigurationError("Invalid site name: %r" % selected_site)

    directory = Path(config_dir) if config_dir is not None else DEFAULT_CONFIG_DIR
    config_path = directory / (selected_site + ".ini")
    if not config_path.is_file():
        raise SiteConfigurationError(
            "Unknown Colberto site %r: %s does not exist" % (selected_site, config_path)
        )

    config = configparser.ConfigParser(interpolation=None)
    loaded = config.read(config_path, encoding="utf-8")
    if not loaded:
        raise SiteConfigurationError("Could not read site configuration: %s" % config_path)
    validate_site_config(config, config_path)
    return config


def validate_site_config(config, source="<configuration>"):
    """Fail early with a useful message instead of failing while initializing hardware."""
    missing = []
    for section, options in REQUIRED_OPTIONS.items():
        if not config.has_section(section):
            missing.append("[%s]" % section)
            continue
        for option in options:
            if not config.has_option(section, option) or not config.get(section, option).strip():
                missing.append("[%s] %s" % (section, option))
    if missing:
        raise SiteConfigurationError(
            "%s is missing required settings: %s" % (source, ", ".join(missing))
        )

    configured_name = config.get("site", "name").strip().lower()
    if configured_name not in ("udem", "wfu"):
        raise SiteConfigurationError("Unsupported site name in %s: %s" % (source, configured_name))


def csv_values(config, section, option, converter=str):
    """Read a comma-separated setting and convert every non-empty value."""
    return [converter(value.strip()) for value in config.get(section, option).split(",") if value.strip()]


def hardware_parameters(config, section):
    """Convert a calibration/geometry section to values expected by camera drivers."""
    driver_names = {
        "calibration_third_order": "calibrationThirdOrder",
        "calibration_second_order": "calibrationSecondOrder",
        "calibration_first_order": "calibrationFirstOrder",
        "calibration_offset": "calibrationOffset",
    }
    values = {}
    for key, raw_value in config.items(section):
        if key in ("driver", "vendor_config"):
            continue
        output_key = driver_names.get(key, key)
        if key == "calibrated":
            values[output_key] = config.getboolean(section, key)
        else:
            values[output_key] = float(raw_value)
    for integer_key in ("num_pixels", "sensor_height", "roi_y0", "roi_height", "roi_binning"):
        if integer_key in values:
            values[integer_key] = int(values[integer_key])
    return values
