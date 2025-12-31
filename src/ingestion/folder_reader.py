"""
Folder reader for the activity reporting system.

Reads and combines multiple CSV/Excel files from a folder.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
from .base import DataReader
from .csv_reader import CSVReader
from .excel_reader import ExcelReader
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class FolderReader(DataReader):
    """
    Read and combine multiple files from a folder.

    Configuration parameters:
        - path: Path to folder (required)
        - pattern: File pattern (e.g., '*.csv', '*.xlsx') (default: '*.csv')
        - recursive: Search subdirectories (default: False)
        - encoding: File encoding for CSV files (default: 'utf-8')
        - delimiter: Delimiter for CSV files (default: ',')

    Example:
        >>> config = {'path': 'data/input/daily/', 'pattern': '*.csv'}
        >>> reader = FolderReader(config)
        >>> df = reader.read()
    """

    def validate_config(self) -> None:
        """Validate folder reader configuration."""
        if 'path' not in self.source_config:
            raise ValueError("Folder reader requires 'path' in configuration")

    def read(self) -> pd.DataFrame:
        """
        Read and combine all matching files from folder.

        Returns:
            DataFrame containing combined data from all files

        Raises:
            FileNotFoundError: If folder doesn't exist
            ValueError: If no matching files found
        """
        folder_path = Path(self.source_config['path'])

        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder_path}")

        if not folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {folder_path}")

        # Get file pattern and search mode
        pattern = self.source_config.get('pattern', '*.csv')
        recursive = self.source_config.get('recursive', False)

        # Find matching files
        if recursive:
            files = list(folder_path.rglob(pattern))
        else:
            files = list(folder_path.glob(pattern))

        if not files:
            raise ValueError(f"No files matching pattern '{pattern}' found in {folder_path}")

        logger.info(f"Found {len(files)} files matching pattern '{pattern}' in {folder_path}")

        # Read and combine all files
        dataframes: List[pd.DataFrame] = []

        for file_path in sorted(files):
            try:
                # Determine file type and read accordingly
                if file_path.suffix.lower() in ['.csv', '.txt']:
                    file_config = {
                        'path': str(file_path),
                        'encoding': self.source_config.get('encoding', 'utf-8'),
                        'delimiter': self.source_config.get('delimiter', ',')
                    }
                    reader = CSVReader(file_config)
                elif file_path.suffix.lower() in ['.xlsx', '.xls']:
                    file_config = {
                        'path': str(file_path),
                        'sheet_name': self.source_config.get('sheet_name', 0)
                    }
                    reader = ExcelReader(file_config)
                else:
                    logger.warning(f"Skipping unsupported file type: {file_path}")
                    continue

                df = reader.read()

                # Add source file column
                df['_source_file'] = file_path.name

                dataframes.append(df)

            except Exception as e:
                logger.warning(f"Failed to read file {file_path}: {str(e)}")
                continue

        if not dataframes:
            raise ValueError("Failed to read any files from the folder")

        # Combine all dataframes
        combined_df = pd.concat(dataframes, ignore_index=True)

        logger.info(f"Successfully combined {len(dataframes)} files into {len(combined_df)} total rows")

        return combined_df
