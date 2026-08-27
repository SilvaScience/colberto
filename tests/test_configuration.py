import configparser
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from configuration import (  # noqa: E402
    SITE_ENVIRONMENT_VARIABLE,
    SiteConfigurationError,
    csv_values,
    hardware_parameters,
    load_site_config,
    validate_site_config,
)


class SiteConfigurationTests(unittest.TestCase):
    def test_all_site_files_are_valid(self):
        for site in ("udem", "wfu"):
            with self.subTest(site=site):
                config = load_site_config(site)
                self.assertEqual(config.get("site", "name"), site)
                self.assertTrue(csv_values(config, "monochromator", "grating_densities", float))
                parameters = hardware_parameters(config, "stresing")
                self.assertIsInstance(parameters["num_pixels"], int)
                self.assertIn("calibrationThirdOrder", parameters)

    def test_environment_selects_site(self):
        with mock.patch.dict(os.environ, {SITE_ENVIRONMENT_VARIABLE: "WFU"}):
            self.assertEqual(load_site_config().get("site", "name"), "wfu")

    def test_missing_setting_is_reported(self):
        config = configparser.ConfigParser()
        config.add_section("site")
        config.set("site", "name", "udem")
        with self.assertRaisesRegex(SiteConfigurationError, r"\[site\] default_data_directory"):
            validate_site_config(config)


if __name__ == "__main__":
    unittest.main()
