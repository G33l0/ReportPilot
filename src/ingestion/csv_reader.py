"""
CSV file reader for the activity reporting system.

Reads data from CSV files with configurable encoding and delimiter.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any
from .base import DataReader
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class CSVReader(DataReader):
    """
    Read data from CSV files.

    Configuration parameters:
        - path: Path to CSV file (required)
        - encoding: File encoding (default: 'utf-8')
        - delimiter: Column delimiter (default: ',')
        - skip_rows: Number of rows to skip (default: 0)

    Example:
        >>> config = {'path': 'data/input/activities.csv'}
        >>> reader = CSVReader(config)
        >>> df = reader.read()
    """

    def validate_config(self) -> None:
        """Validate CSV reader configuration."""
        if 'path' not in self.source_config:
            raise ValueError("CSV reader requires 'path' in configuration")

    def read(self) -> pd.DataFrame:
        """
        Read data from CSV file.

        Returns:
            DataFrame containing the CSV data

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            pd.errors.ParserError: If CSV parsing fails
        """
        file_path = Path(self.source_config['path'])

        if not file_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # Get optional parameters
        encoding = self.source_config.get('encoding', 'utf-8')
        delimiter = self.source_config.get('delimiter', ',')
        skip_rows = self.source_config.get('skip_rows', 0)

        logger.info(f"Reading CSV file: {file_path}")

        try:
            df = pd.read_csv(
                file_path,
                encoding=encoding,
                delimiter=delimiter,
                skiprows=skip_rows
            )

            logger.info(f"Successfully read {len(df)} rows from {file_path}")
            return df

        except Exception as e:
            logger.error(f"Failed to read CSV file {file_path}: {str(e)}")
            raise
