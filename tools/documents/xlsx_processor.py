import os
import pandas as pd
from typing import Dict, Any, List
from .text_normalizer import normalize_text

def process_xlsx_or_csv(file_path: str, max_rows_preview: int = 50) -> Dict[str, Any]:
    """
    Processes XLSX, XLS, and CSV files using pandas / openpyxl:
    1. Extracts sheet names, headers, column data types, row counts.
    2. Generates formatted markdown tables for preview.
    3. Provides statistical summary for numerical columns.
    Returns:
    {
      "text": str,
      "metadata": {"sheets": List[str], "sheet_counts": Dict[str, int], "format": str}
    }
    """
    ext = os.path.splitext(file_path)[1].lower()
    sheet_data = {}
    sheet_counts = {}
    text_blocks = []

    if ext == ".csv":
        # Process CSV
        try:
            df = pd.read_csv(file_path)
            sheet_data["Sheet1"] = df
            sheet_counts["Sheet1"] = len(df)
        except Exception as e:
            # Fallback with python standard encoding options
            df = pd.read_csv(file_path, encoding="latin1")
            sheet_data["Sheet1"] = df
            sheet_counts["Sheet1"] = len(df)
    else:
        # Process Excel (.xlsx, .xls)
        excel_file = pd.ExcelFile(file_path)
        for sheet_name in excel_file.sheet_names:
            df = excel_file.parse(sheet_name)
            sheet_data[sheet_name] = df
            sheet_counts[sheet_name] = len(df)

    for sheet_name, df in sheet_data.items():
        total_rows, total_cols = df.shape
        headers = [str(c) for c in df.columns]
        
        sheet_text = [
            f"## Sheet: {sheet_name}",
            f"- Total Rows: {total_rows}",
            f"- Total Columns: {total_cols}",
            f"- Headers: {', '.join(headers)}"
        ]

        if total_rows > 0:
            # Preview rows
            preview_df = df.head(max_rows_preview)
            # Render markdown table
            sheet_text.append("\n### Data Preview (First " + str(len(preview_df)) + " Rows):")
            sheet_text.append(preview_df.to_markdown(index=False))

            if total_rows > max_rows_preview:
                sheet_text.append(f"\n*Note: {total_rows - max_rows_preview} additional rows present in sheet.*")

            # Column summary statistics for numeric data
            num_cols = df.select_dtypes(include=['number']).columns.tolist()
            if num_cols:
                sheet_text.append("\n### Numeric Column Summary:")
                sheet_text.append(df[num_cols].describe().to_markdown())

        text_blocks.append("\n\n".join(sheet_text))

    full_text = normalize_text("\n\n---\n\n".join(text_blocks))

    return {
        "text": full_text,
        "metadata": {
            "sheets": list(sheet_data.keys()),
            "sheet_counts": sheet_counts,
            "format": ext.lstrip(".")
        }
    }
