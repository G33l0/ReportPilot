"""
PDF report generator for the activity reporting system.

Creates formatted PDF reports with tables, summaries, and formatting.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from ..utils.logger import setup_logger

logger = setup_logger(__name__)


class PDFReportGenerator:
    """
    Generate formatted PDF reports.

    Creates PDF documents with:
    - Title page
    - Executive summary
    - Formatted tables
    - Section headers
    - Page numbers

    Example:
        >>> generator = PDFReportGenerator()
        >>> generator.generate(summaries, 'reports/weekly_report.pdf')
    """

    def __init__(self):
        """Initialize the PDF report generator."""
        self.styles = getSampleStyleSheet()

        # Define custom styles
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))

        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#2e5c8a'),
            spaceAfter=12,
            spaceBefore=12
        ))

        self.styles.add(ParagraphStyle(
            name='SubHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#4472c4'),
            spaceAfter=6
        ))

    def generate(
        self,
        summaries: Dict[str, pd.DataFrame],
        output_path: str,
        config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate PDF report from summary data.

        Args:
            summaries: Dictionary of summary DataFrames
            output_path: Path for output PDF file
            config: Report configuration options

        Returns:
            Path to generated PDF file

        Configuration options:
            - title: Report title (default: 'Weekly Activity Report')
            - page_size: Page size ('letter' or 'a4', default: 'letter')
            - max_rows_per_table: Maximum rows before splitting (default: 30)
        """
        if config is None:
            config = {}

        logger.info(f"Generating PDF report: {output_path}")

        # Create output directory if needed
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Set up document
        page_size = A4 if config.get('page_size') == 'a4' else letter
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=page_size,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )

        # Build document content
        story = []

        # Add title page
        story.extend(self._create_title_page(config))
        story.append(PageBreak())

        # Add executive summary
        story.extend(self._create_executive_summary(summaries))
        story.append(Spacer(1, 0.3*inch))

        # Add detailed sections
        max_rows = config.get('max_rows_per_table', 30)

        for section_name, df in summaries.items():
            if isinstance(df, pd.DataFrame) and not df.empty:
                story.extend(self._create_section(section_name, df, max_rows))
                story.append(Spacer(1, 0.2*inch))

        # Build PDF
        doc.build(story)

        logger.info(f"PDF report generated successfully: {output_path}")
        return output_path

    def _create_title_page(self, config: Dict[str, Any]) -> List:
        """Create title page elements."""
        elements = []

        title = config.get('title', 'Weekly Activity Report')

        # Add title
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph(title, self.styles['CustomTitle']))
        elements.append(Spacer(1, 0.5*inch))

        # Add date
        date_text = f"Generated: {datetime.now().strftime('%B %d, %Y')}"
        elements.append(Paragraph(date_text, self.styles['Normal']))

        return elements

    def _create_executive_summary(
        self,
        summaries: Dict[str, pd.DataFrame]
    ) -> List:
        """Create executive summary section."""
        elements = []

        elements.append(Paragraph("Executive Summary", self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))

        # Add key metrics from weekly totals
        if 'weekly_totals' in summaries and not summaries['weekly_totals'].empty:
            weekly = summaries['weekly_totals']
            latest = weekly.iloc[-1]

            summary_text = []
            summary_text.append("<b>Latest Week Performance:</b>")

            for col, value in latest.items():
                if col not in ['week_start', 'week_number', 'year']:
                    # Format value
                    if isinstance(value, float):
                        formatted_value = f"{value:,.2f}"
                    elif isinstance(value, int):
                        formatted_value = f"{value:,}"
                    else:
                        formatted_value = str(value)

                    label = col.replace('_', ' ').title()
                    summary_text.append(f"• {label}: {formatted_value}")

            elements.append(Paragraph("<br/>".join(summary_text), self.styles['Normal']))

        # Add trend information if available
        if 'trends' in summaries and not summaries['trends'].empty:
            elements.append(Spacer(1, 0.2*inch))
            elements.append(Paragraph("<b>Trends:</b>", self.styles['Normal']))

            trends = summaries['trends'].iloc[-1]
            trend_text = []

            for col in summaries['trends'].columns:
                if col.endswith('_pct_change'):
                    base_col = col.replace('_pct_change', '')
                    pct_value = trends[col]

                    if pd.notna(pct_value):
                        direction = "↑" if pct_value > 0 else ("↓" if pct_value < 0 else "→")
                        color = "green" if pct_value > 0 else ("red" if pct_value < 0 else "black")

                        trend_text.append(
                            f'• {base_col.replace("_", " ").title()}: '
                            f'<font color="{color}">{direction} {pct_value:+.1f}%</font>'
                        )

            if trend_text:
                elements.append(Paragraph("<br/>".join(trend_text), self.styles['Normal']))

        return elements

    def _create_section(
        self,
        section_name: str,
        df: pd.DataFrame,
        max_rows: int
    ) -> List:
        """Create a section with a table."""
        elements = []

        # Add section header
        header_text = section_name.replace('_', ' ').title()
        elements.append(Paragraph(header_text, self.styles['SectionHeader']))
        elements.append(Spacer(1, 0.1*inch))

        # Limit rows if too many
        if len(df) > max_rows:
            df_display = df.head(max_rows)
            note = f"<i>Showing top {max_rows} of {len(df)} rows</i>"
            elements.append(Paragraph(note, self.styles['Normal']))
            elements.append(Spacer(1, 0.05*inch))
        else:
            df_display = df

        # Create table data
        table_data = [df_display.columns.tolist()]

        for _, row in df_display.iterrows():
            formatted_row = []
            for value in row:
                # Format values
                if pd.isna(value):
                    formatted_row.append('')
                elif isinstance(value, float):
                    formatted_row.append(f"{value:.2f}")
                elif isinstance(value, datetime):
                    formatted_row.append(value.strftime('%Y-%m-%d'))
                else:
                    formatted_row.append(str(value))
            table_data.append(formatted_row)

        # Create table
        table = Table(table_data)

        # Apply table style
        table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472c4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

            # Data style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.white, colors.HexColor('#f0f0f0')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))

        elements.append(table)

        return elements
