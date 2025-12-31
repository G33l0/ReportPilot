"""
Data cleaning and validation for the activity reporting system.

Provides comprehensive data cleaning, normalization, and validation.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class DataCleaner:
    """
    Clean and validate data for reporting.

    Provides methods for:
    - Handling missing values
    - Removing duplicates
    - Data type conversion
    - Date/time normalization
    - Outlier detection
    - Custom validation rules

    Example:
        >>> cleaner = DataCleaner()
        >>> cleaned_df = cleaner.clean(raw_df, cleaning_config)
    """

    def __init__(self):
        """Initialize the data cleaner."""
        self.cleaning_stats: Dict[str, Any] = {}

    def clean(
        self,
        df: pd.DataFrame,
        config: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Clean and validate DataFrame according to configuration.

        Args:
            df: Input DataFrame to clean
            config: Cleaning configuration dictionary (optional)

        Returns:
            Cleaned DataFrame

        Configuration options:
            - drop_duplicates: Remove duplicate rows (default: True)
            - drop_empty_rows: Remove rows with all NaN values (default: True)
            - fill_missing: Strategy for missing values ('drop', 'forward', 'mean', 'zero')
            - required_columns: List of column names that must exist
            - date_columns: List of column names to parse as dates
            - numeric_columns: List of column names to convert to numeric
            - remove_outliers: Remove outliers using IQR method (default: False)
            - standardize_strings: Trim and normalize string columns (default: True)
        """
        if config is None:
            config = {}

        logger.info(f"Starting data cleaning. Input shape: {df.shape}")
        original_shape = df.shape

        # Create a copy to avoid modifying original
        df_clean = df.copy()

        # Reset statistics
        self.cleaning_stats = {
            'original_rows': len(df),
            'original_columns': len(df.columns),
            'operations': []
        }

        # Validate required columns
        if 'required_columns' in config:
            df_clean = self._validate_columns(df_clean, config['required_columns'])

        # Remove completely empty rows
        if config.get('drop_empty_rows', True):
            df_clean = self._drop_empty_rows(df_clean)

        # Handle duplicates
        if config.get('drop_duplicates', True):
            df_clean = self._drop_duplicates(df_clean)

        # Standardize string columns
        if config.get('standardize_strings', True):
            df_clean = self._standardize_strings(df_clean)

        # Convert date columns
        if 'date_columns' in config:
            df_clean = self._convert_dates(df_clean, config['date_columns'])

        # Convert numeric columns
        if 'numeric_columns' in config:
            df_clean = self._convert_numeric(df_clean, config['numeric_columns'])

        # Handle missing values
        if 'fill_missing' in config:
            df_clean = self._handle_missing(df_clean, config['fill_missing'])

        # Remove outliers
        if config.get('remove_outliers', False):
            numeric_cols = df_clean.select_dtypes(include=[np.number]).columns.tolist()
            if 'numeric_columns' in config:
                numeric_cols = config['numeric_columns']
            df_clean = self._remove_outliers(df_clean, numeric_cols)

        # Apply custom validation rules
        if 'custom_rules' in config:
            df_clean = self._apply_custom_rules(df_clean, config['custom_rules'])

        # Update final statistics
        self.cleaning_stats['final_rows'] = len(df_clean)
        self.cleaning_stats['final_columns'] = len(df_clean.columns)
        self.cleaning_stats['rows_removed'] = original_shape[0] - len(df_clean)
        self.cleaning_stats['columns_removed'] = original_shape[1] - len(df_clean.columns)

        logger.info(
            f"Data cleaning completed. Output shape: {df_clean.shape}. "
            f"Removed {self.cleaning_stats['rows_removed']} rows, "
            f"{self.cleaning_stats['columns_removed']} columns"
        )

        return df_clean

    def _validate_columns(
        self,
        df: pd.DataFrame,
        required_columns: List[str]
    ) -> pd.DataFrame:
        """Validate that required columns exist."""
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        logger.info(f"Validated {len(required_columns)} required columns")
        return df

    def _drop_empty_rows(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows where all values are NaN."""
        before = len(df)
        df = df.dropna(how='all')
        removed = before - len(df)

        if removed > 0:
            logger.info(f"Removed {removed} completely empty rows")
            self.cleaning_stats['operations'].append({
                'operation': 'drop_empty_rows',
                'rows_removed': removed
            })

        return df

    def _drop_duplicates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove duplicate rows."""
        before = len(df)
        df = df.drop_duplicates()
        removed = before - len(df)

        if removed > 0:
            logger.info(f"Removed {removed} duplicate rows")
            self.cleaning_stats['operations'].append({
                'operation': 'drop_duplicates',
                'rows_removed': removed
            })

        return df

    def _standardize_strings(self, df: pd.DataFrame) -> pd.DataFrame:
        """Trim whitespace and standardize string columns."""
        string_columns = df.select_dtypes(include=['object']).columns

        for col in string_columns:
            # Only process if column contains strings
            if df[col].dtype == 'object':
                df[col] = df[col].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )

        if len(string_columns) > 0:
            logger.info(f"Standardized {len(string_columns)} string columns")

        return df

    def _convert_dates(
        self,
        df: pd.DataFrame,
        date_columns: List[str]
    ) -> pd.DataFrame:
        """Convert specified columns to datetime."""
        converted = []

        for col in date_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                    converted.append(col)
                except Exception as e:
                    logger.warning(f"Failed to convert column '{col}' to datetime: {str(e)}")

        if converted:
            logger.info(f"Converted {len(converted)} columns to datetime: {converted}")

        return df

    def _convert_numeric(
        self,
        df: pd.DataFrame,
        numeric_columns: List[str]
    ) -> pd.DataFrame:
        """Convert specified columns to numeric."""
        converted = []

        for col in numeric_columns:
            if col in df.columns:
                try:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    converted.append(col)
                except Exception as e:
                    logger.warning(f"Failed to convert column '{col}' to numeric: {str(e)}")

        if converted:
            logger.info(f"Converted {len(converted)} columns to numeric: {converted}")

        return df

    def _handle_missing(
        self,
        df: pd.DataFrame,
        strategy: str
    ) -> pd.DataFrame:
        """
        Handle missing values according to strategy.

        Strategies:
            - 'drop': Drop rows with any missing values
            - 'forward': Forward fill missing values
            - 'backward': Backward fill missing values
            - 'mean': Fill with column mean (numeric only)
            - 'zero': Fill with zero
        """
        before_missing = df.isnull().sum().sum()

        if strategy == 'drop':
            df = df.dropna()
        elif strategy == 'forward':
            df = df.ffill()
        elif strategy == 'backward':
            df = df.bfill()
        elif strategy == 'mean':
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
        elif strategy == 'zero':
            df = df.fillna(0)
        else:
            logger.warning(f"Unknown missing value strategy: {strategy}")

        after_missing = df.isnull().sum().sum()

        logger.info(
            f"Handled missing values using '{strategy}' strategy. "
            f"Missing values reduced from {before_missing} to {after_missing}"
        )

        return df

    def _remove_outliers(
        self,
        df: pd.DataFrame,
        numeric_columns: List[str]
    ) -> pd.DataFrame:
        """Remove outliers using IQR method."""
        before = len(df)

        for col in numeric_columns:
            if col not in df.columns:
                continue

            if df[col].dtype in [np.float64, np.int64]:
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1

                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR

                df = df[
                    (df[col] >= lower_bound) &
                    (df[col] <= upper_bound)
                ]

        removed = before - len(df)

        if removed > 0:
            logger.info(f"Removed {removed} outlier rows")
            self.cleaning_stats['operations'].append({
                'operation': 'remove_outliers',
                'rows_removed': removed
            })

        return df

    def _apply_custom_rules(
        self,
        df: pd.DataFrame,
        rules: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Apply custom validation/filtering rules.

        Each rule should be a dictionary with:
            - column: Column name
            - condition: Condition type ('>', '<', '>=', '<=', '==', '!=', 'in', 'not_in')
            - value: Value to compare against
        """
        for rule in rules:
            column = rule.get('column')
            condition = rule.get('condition')
            value = rule.get('value')

            if column not in df.columns:
                logger.warning(f"Column '{column}' not found for custom rule")
                continue

            before = len(df)

            if condition == '>':
                df = df[df[column] > value]
            elif condition == '<':
                df = df[df[column] < value]
            elif condition == '>=':
                df = df[df[column] >= value]
            elif condition == '<=':
                df = df[df[column] <= value]
            elif condition == '==':
                df = df[df[column] == value]
            elif condition == '!=':
                df = df[df[column] != value]
            elif condition == 'in':
                df = df[df[column].isin(value)]
            elif condition == 'not_in':
                df = df[~df[column].isin(value)]

            removed = before - len(df)
            if removed > 0:
                logger.info(
                    f"Custom rule '{column} {condition} {value}' removed {removed} rows"
                )

        return df

    def get_cleaning_stats(self) -> Dict[str, Any]:
        """Get statistics about the cleaning process."""
        return self.cleaning_stats
