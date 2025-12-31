"""
Base data reader interface for the activity reporting system.

Defines the contract that all data readers must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
import pandas as pd


class DataReader(ABC):
    """
    Abstract base class for data readers.

    All data source readers must inherit from this class and implement
    the read() method.

    Attributes:
        source_config: Configuration dictionary for the data source
    """

    def __init__(self, source_config: Dict[str, Any]):
        """
        Initialize the data reader.

        Args:
            source_config: Configuration dictionary containing source-specific
                          parameters (paths, credentials, etc.)
        """
        self.source_config = source_config
        self.validate_config()

    @abstractmethod
    def validate_config(self) -> None:
        """
        Validate the source configuration.

        Raises:
            ValueError: If required configuration parameters are missing
        """
        pass

    @abstractmethod
    def read(self) -> pd.DataFrame:
        """
        Read data from the source and return as DataFrame.

        Returns:
            DataFrame containing the ingested data

        Raises:
            Exception: If data cannot be read from the source
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about the data source.

        Returns:
            Dictionary containing metadata (source type, last read time, etc.)
        """
        return {
            'source_type': self.__class__.__name__,
            'config': {k: v for k, v in self.source_config.items()
                      if k not in ['password', 'api_key', 'token']}
        }
