"""
Data summarization for weekly activity reports.

Calculates totals, averages, trends, counts, and other statistics.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class DataSummarizer:
    """
    Calculate weekly summaries and statistics.

    Provides methods for:
    - Weekly aggregations (totals, averages, counts)
    - Trend analysis (week-over-week changes)
    - Category breakdowns
    - Time-based groupings

    Example:
        >>> summarizer = DataSummarizer()
        >>> summary = summarizer.summarize_weekly(df, config)
    """

    def __init__(self):
        """Initialize the data summarizer."""
        self.summary_results: Dict[str, Any] = {}

    def summarize_weekly(
        self,
        df: pd.DataFrame,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Generate weekly summary reports.

        Args:
            df: Input DataFrame with cleaned data
            config: Summarization configuration

        Returns:
            Dictionary containing various summary DataFrames

        Configuration options:
            - date_column: Column name containing dates (required)
            - group_by: Columns to group by (e.g., category, user, project)
            - metrics: Dictionary of metric columns and aggregation functions
            - include_trends: Calculate week-over-week trends (default: True)
            - include_percentages: Calculate percentage breakdowns (default: True)
        """
        if config is None:
            config = {}

        logger.info("Starting weekly summarization")

        # Validate date column
        date_column = config.get('date_column', 'date')
        if date_column not in df.columns:
            raise ValueError(f"Date column '{date_column}' not found in DataFrame")

        # Ensure date column is datetime
        if not pd.api.types.is_datetime64_any_dtype(df[date_column]):
            df[date_column] = pd.to_datetime(df[date_column])

        # Add week-related columns
        df = self._add_time_dimensions(df, date_column)

        # Initialize results dictionary
        summaries = {}

        # Overall weekly summary
        summaries['weekly_totals'] = self._calculate_weekly_totals(df, config)

        # Group-based summaries
        if 'group_by' in config:
            summaries['by_category'] = self._calculate_group_summaries(df, config)

        # Trend analysis
        if config.get('include_trends', True):
            summaries['trends'] = self._calculate_trends(summaries['weekly_totals'])

        # Daily breakdown
        summaries['daily_breakdown'] = self._calculate_daily_breakdown(df, config)

        # Statistics summary
        summaries['statistics'] = self._calculate_statistics(df, config)

        # Top performers/items
        if 'group_by' in config:
            summaries['top_items'] = self._calculate_top_items(df, config)

        logger.info(f"Weekly summarization completed. Generated {len(summaries)} summary reports")

        self.summary_results = summaries
        return summaries

    def _add_time_dimensions(
        self,
        df: pd.DataFrame,
        date_column: str
    ) -> pd.DataFrame:
        """Add week, month, and other time-based columns."""
        df['year'] = df[date_column].dt.year
        df['month'] = df[date_column].dt.month
        df['week'] = df[date_column].dt.isocalendar().week
        df['day_of_week'] = df[date_column].dt.day_name()
        df['week_start'] = df[date_column].dt.to_period('W').dt.start_time

        return df

    def _calculate_weekly_totals(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Calculate overall weekly totals."""
        metrics = config.get('metrics', {})

        if not metrics:
            # Default: count rows per week
            weekly = df.groupby('week_start').size().reset_index(name='count')
        else:
            # Apply configured aggregations
            agg_dict = {}
            for column, functions in metrics.items():
                if column in df.columns:
                    if isinstance(functions, str):
                        agg_dict[column] = functions
                    elif isinstance(functions, list):
                        agg_dict[column] = functions

            weekly = df.groupby('week_start').agg(agg_dict).reset_index()

            # Flatten multi-level columns if multiple aggregations
            if isinstance(weekly.columns, pd.MultiIndex):
                weekly.columns = ['_'.join(col).strip('_') for col in weekly.columns.values]

        # Add week number and year
        weekly['week_number'] = weekly['week_start'].dt.isocalendar().week
        weekly['year'] = weekly['week_start'].dt.year

        logger.info(f"Calculated weekly totals for {len(weekly)} weeks")

        return weekly

    def _calculate_group_summaries(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Calculate summaries grouped by categories."""
        group_by = config['group_by']
        if isinstance(group_by, str):
            group_by = [group_by]

        # Add week_start to grouping
        group_columns = ['week_start'] + group_by

        metrics = config.get('metrics', {})

        if not metrics:
            # Default: count by group
            summary = df.groupby(group_columns).size().reset_index(name='count')
        else:
            # Apply configured aggregations
            agg_dict = {}
            for column, functions in metrics.items():
                if column in df.columns:
                    agg_dict[column] = functions

            summary = df.groupby(group_columns).agg(agg_dict).reset_index()

            # Flatten multi-level columns if multiple aggregations
            if isinstance(summary.columns, pd.MultiIndex):
                summary.columns = ['_'.join(str(c) for c in col).strip('_') if col[1] else col[0]
                                  for col in summary.columns.values]

        # Add percentages if requested
        if config.get('include_percentages', True):
            # Calculate percentage within each week
            numeric_cols = [col for col in summary.columns
                          if col not in group_columns and pd.api.types.is_numeric_dtype(summary[col])]
            for col in numeric_cols:
                total_by_week = summary.groupby('week_start')[col].transform('sum')
                summary[f'{col}_percentage'] = (summary[col] / total_by_week * 100).round(2)

        logger.info(f"Calculated group summaries with {len(summary)} rows")

        return summary

    def _calculate_trends(
        self,
        weekly_df: pd.DataFrame
    ) -> pd.DataFrame:
        """Calculate week-over-week trends."""
        trends = weekly_df.copy()

        # Get numeric columns (excluding date/time columns)
        numeric_cols = trends.select_dtypes(include=[np.number]).columns
        numeric_cols = [col for col in numeric_cols
                       if col not in ['week_number', 'year']]

        # Calculate week-over-week changes
        for col in numeric_cols:
            # Absolute change
            trends[f'{col}_change'] = trends[col].diff()

            # Percentage change
            trends[f'{col}_pct_change'] = trends[col].pct_change() * 100

        # Add trend direction indicators
        for col in numeric_cols:
            change_col = f'{col}_change'
            if change_col in trends.columns:
                trends[f'{col}_trend'] = trends[change_col].apply(
                    lambda x: '↑' if x > 0 else ('↓' if x < 0 else '→')
                )

        logger.info(f"Calculated trends for {len(numeric_cols)} metrics")

        return trends

    def _calculate_daily_breakdown(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Calculate daily breakdown within weeks."""
        metrics = config.get('metrics', {})
        date_column = config.get('date_column', 'date')

        if not metrics:
            daily = df.groupby([date_column, 'day_of_week']).size().reset_index(name='count')
        else:
            agg_dict = {}
            for column, functions in metrics.items():
                if column in df.columns:
                    if isinstance(functions, str):
                        agg_dict[column] = functions
                    elif isinstance(functions, list):
                        agg_dict[column] = functions[0]  # Use first function

            daily = df.groupby([date_column, 'day_of_week']).agg(agg_dict).reset_index()

        # Sort by date
        daily = daily.sort_values(date_column)

        logger.info(f"Calculated daily breakdown for {len(daily)} days")

        return daily

    def _calculate_statistics(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any]
    ) -> pd.DataFrame:
        """Calculate statistical summary (mean, median, std, min, max)."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns

        # Exclude time-related columns
        numeric_cols = [col for col in numeric_cols
                       if col not in ['year', 'month', 'week']]

        if not numeric_cols:
            return pd.DataFrame()

        stats = df[numeric_cols].describe().T
        stats['median'] = df[numeric_cols].median()

        # Reorder columns
        stats = stats[['count', 'mean', 'median', 'std', 'min', 'max']]

        logger.info(f"Calculated statistics for {len(stats)} metrics")

        return stats

    def _calculate_top_items(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any],
        top_n: int = 10
    ) -> Dict[str, pd.DataFrame]:
        """Calculate top N items by various metrics."""
        group_by = config['group_by']
        if isinstance(group_by, str):
            group_by = [group_by]

        metrics = config.get('metrics', {})
        top_items = {}

        for group_col in group_by:
            if group_col not in df.columns:
                continue

            if not metrics:
                # Default: top by count
                top = df[group_col].value_counts().head(top_n).reset_index()
                top.columns = [group_col, 'count']
                top_items[f'top_{group_col}'] = top
            else:
                # Top by each metric
                for metric_col, func in metrics.items():
                    if metric_col not in df.columns:
                        continue

                    if isinstance(func, list):
                        func = func[0]

                    if func in ['sum', 'mean', 'count']:
                        grouped = df.groupby(group_col)[metric_col].agg(func).reset_index()
                        grouped = grouped.sort_values(metric_col, ascending=False).head(top_n)
                        top_items[f'top_{group_col}_by_{metric_col}'] = grouped

        logger.info(f"Calculated top items for {len(top_items)} categories")

        return top_items

    def get_summary_results(self) -> Dict[str, Any]:
        """Get all summary results."""
        return self.summary_results

    def export_summary_text(self, summaries: Dict[str, pd.DataFrame]) -> str:
        """
        Generate a text summary of key findings.

        Args:
            summaries: Dictionary of summary DataFrames

        Returns:
            Formatted text summary
        """
        lines = []
        lines.append("=" * 60)
        lines.append("WEEKLY ACTIVITY REPORT SUMMARY")
        lines.append("=" * 60)
        lines.append("")

        # Weekly totals
        if 'weekly_totals' in summaries:
            weekly = summaries['weekly_totals']
            if not weekly.empty:
                lines.append("WEEKLY TOTALS:")
                latest_week = weekly.iloc[-1]
                for col in weekly.columns:
                    if col not in ['week_start', 'week_number', 'year']:
                        lines.append(f"  Latest {col}: {latest_week[col]}")
                lines.append("")

        # Trends
        if 'trends' in summaries:
            trends = summaries['trends']
            if not trends.empty:
                lines.append("TRENDS (Latest Week):")
                latest = trends.iloc[-1]
                for col in trends.columns:
                    if col.endswith('_trend'):
                        base_col = col.replace('_trend', '')
                        if f'{base_col}_pct_change' in trends.columns:
                            pct = latest[f'{base_col}_pct_change']
                            if pd.notna(pct):
                                lines.append(
                                    f"  {base_col}: {latest[col]} "
                                    f"({pct:+.1f}%)"
                                )
                lines.append("")

        # Statistics
        if 'statistics' in summaries:
            stats = summaries['statistics']
            if not stats.empty:
                lines.append("STATISTICS:")
                for idx, row in stats.iterrows():
                    lines.append(
                        f"  {idx}: mean={row['mean']:.2f}, "
                        f"median={row['median']:.2f}, "
                        f"std={row['std']:.2f}"
                    )
                lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)
