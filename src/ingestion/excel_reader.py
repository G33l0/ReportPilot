"""
Excel file reader for the activity reporting system.

Reads data from Excel files (.xlsx, .xls) with support for multiple sheets.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional
from .base import DataReader
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class ExcelReader(DataReader):
    """
    Read data from Excel files.

    Configuration parameters:
        - path: Path to Excel file (required)
        - sheet_name: Sheet name or index (default: 0 - first sheet)
        - skip_rows: Number of rows to skip (default: 0)
        - header_row: Row number for headers (default: 0)

    Example:
        >>> config = {'path': 'data/input/activities.xlsx', 'sheet_name': 'Weekly'}
        >>> reader = ExcelReader(config)
        >>> df = reader.read()
    """

    def validate_config(self) -> None:
        """Validate Excel reader configuration."""
        if 'path' not in self.source_config:
            raise ValueError("Excel reader requires 'path' in configuration")

    def read(self) -> pd.DataFrame:
        """
        Read data from Excel file.

        Returns:
            DataFrame containing the Excel data

        Raises:
            FileNotFoundError: If Excel file doesn't exist
            ValueError: If sheet doesn't exist
        """
        file_path = Path(self.source_config['path'])

        if not file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {file_path}")

        # Get optional parameters
        sheet_name = self.source_config.get('sheet_name', 0)
        skip_rows = self.source_config.get('skip_rows', 0)
        header_row = self.source_config.get('header_row', 0)

        logger.info(f"Reading Excel file: {file_path}, sheet: {sheet_name}")

        try:
            df = pd.read_excel(
                file_path,
                sheet_name=sheet_name,
                skiprows=skip_rows,
                header=header_row
            )

            logger.info(f"Successfully read {len(df)} rows from {file_path}")
            return df

        except Exception as e:
            logger.error(f"Failed to read Excel file {file_path}: {str(e)}")
            raise
