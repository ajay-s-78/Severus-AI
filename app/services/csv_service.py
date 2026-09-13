import io
import pandas as pd
from typing import Dict, Any

class CSVService:
    """
    Service for safely analyzing uploaded CSV datasets using Pandas without executing user code.
    Generates structured metadata and summary statistics for AI context ingestion.
    """

    @staticmethod
    def analyze_csv_bytes(file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Parses CSV raw bytes and computes shape, column types, missing values, and stats preview.
        """
        try:
            # Read CSV using pandas into memory
            df = pd.read_csv(io.BytesIO(file_bytes))
            
            num_rows, num_cols = df.shape
            columns = list(df.columns)
            dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
            missing_values = {col: int(df[col].isna().sum()) for col in df.columns}
            
            # Numeric columns summary preview
            numeric_df = df.select_dtypes(include=['number'])
            stats_preview = {}
            if not numeric_df.empty:
                desc = numeric_df.describe().T[['mean', 'std', 'min', '50%', 'max']].to_dict(orient='index')
                stats_preview = {col: {k: round(v, 2) for k, v in stats.items()} for col, stats in desc.items()}

            # Generate markdown summary representation for AI prompt context
            summary_markdown = (
                f"📊 **Uploaded Dataset Profile: `{filename}`**\n"
                f"- **Shape**: {num_rows} rows × {num_cols} columns\n"
                f"- **Columns & Types**: {', '.join([f'`{col}` ({dtypes[col]})' for col in columns[:15]])}"
                f"{' ...' if len(columns) > 15 else ''}\n"
                f"- **Total Missing Values**: {sum(missing_values.values())}\n"
            )

            return {
                "filename": filename,
                "num_rows": num_rows,
                "num_cols": num_cols,
                "columns": columns,
                "dtypes": dtypes,
                "missing_values": missing_values,
                "stats_preview": stats_preview,
                "summary_markdown": summary_markdown
            }
        except Exception as e:
            return {
                "error": f"Failed to parse CSV file '{filename}': {str(e)}"
            }

csv_service = CSVService()
