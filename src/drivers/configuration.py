from pathlib import Path
import sys
import databroker
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))


class Configuration():
    """
    Represents the system's current hardware configuration.
    """

    def __init__(self,path_to_configuration):
        """
        Builds a configuration object within the colberto instance using a presaved
        configuration file.
        input:
            path_to_configuration: Path to the configuration file
        """
        self.path=Path(path_to_configuration)
