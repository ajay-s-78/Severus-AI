import io
import json
import re
import logging
import pandas as pd
from typing import Dict, Any, List, Optional

logger = logging.getLogger("severus.data_analysis_service")


class DataAnalysisService:
    """
    Dedicated Data Science Workspace Service.
    Safely loads, inspects, profiles, and analyzes CSV, Excel (.xlsx/.xls), JSON, and TXT datasets.
    Computes dataset shape, column types, summary statistics, missing values, duplicates, numeric correlations,
    and EDA insights without executing arbitrary user python code.
    """

    ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".txt"}
    MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB

    SECRET_PATTERNS = [
        r'AIzaSy[A-Za-z0-9_-]{33}',
        r'sk-[A-Za-z0-9_-]{20,}',
        r'\b(bearer|token|access_token|refresh_token)\b\s*[:=\s]\s*[^\s]+',
        r'\b(api_key|apikey|secret|password|passwd)\b\s*[:=]\s*[^\s]+',
    ]

    def contains_secret(self, text: str) -> bool:
        """Checks if text contains exposed secrets, tokens, or API keys."""
        if not text or not isinstance(text, str):
            return False
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["google_api_key", "tavily_api_key", "sk-", "aizasy"]):
            return True
        for pattern in self.SECRET_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def validate_dataset(self, file_bytes: bytes, filename: str) -> Optional[str]:
        """
        Validates dataset extension, non-empty content, and file size.
        Returns error string if invalid, or None if valid.
        """
        if not file_bytes or len(file_bytes) == 0:
            return f"Dataset file '{filename}' is empty."

        if len(file_bytes) > self.MAX_FILE_SIZE_BYTES:
            size_mb = len(file_bytes) / (1024 * 1024)
            return f"Dataset file size ({size_mb:.2f} MB) exceeds maximum allowed limit of 15 MB."

        ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in self.ALLOWED_EXTENSIONS:
            return f"Unsupported file format '{ext}'. Supported dataset formats: CSV, Excel (.xlsx), JSON, TXT."

        return None

    def read_dataframe(self, file_bytes: bytes, filename: str) -> pd.DataFrame:
        """
        Parses raw file bytes into a Pandas DataFrame based on file extension.
        """
        ext = "." + filename.split(".")[-1].lower() if "." in filename else ""

        if ext == ".csv":
            return pd.read_csv(io.BytesIO(file_bytes))
        elif ext in [".xlsx", ".xls"]:
            return pd.read_excel(io.BytesIO(file_bytes))
        elif ext == ".json":
            try:
                return pd.read_json(io.BytesIO(file_bytes))
            except Exception:
                data = json.loads(file_bytes.decode('utf-8'))
                if isinstance(data, list):
                    return pd.DataFrame(data)
                elif isinstance(data, dict):
                    return pd.DataFrame([data]) if not any(isinstance(v, list) for v in data.values()) else pd.DataFrame(data)
                raise ValueError("JSON content could not be converted to tabular DataFrame.")
        elif ext == ".txt":
            try:
                return pd.read_csv(io.BytesIO(file_bytes), sep=None, engine='python')
            except Exception:
                lines = [line.strip() for line in file_bytes.decode('utf-8', errors='ignore').splitlines() if line.strip()]
                return pd.DataFrame({"text_content": lines})
        else:
            raise ValueError(f"Unsupported file format '{ext}'")

    def analyze_dataset_bytes(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Loads dataset bytes and computes full data science workspace profile & EDA insights.
        """
        validation_error = self.validate_dataset(file_bytes, filename)
        if validation_error:
            return {"error": validation_error}

        try:
            df = self.read_dataframe(file_bytes, filename)
            if df.empty:
                return {"error": f"Uploaded dataset '{filename}' contains no data rows."}

            num_rows, num_cols = df.shape
            columns = [str(c) for c in df.columns]
            dtypes = {str(col): str(dtype) for col, dtype in df.dtypes.items()}

            # Missing Values & Duplicates
            missing_counts = {str(col): int(df[col].isna().sum()) for col in df.columns}
            missing_pct = {col: round((count / num_rows) * 100, 2) for col, count in missing_counts.items()}
            duplicate_rows = int(df.duplicated().sum())

            # Numerical vs Categorical Columns
            numeric_df = df.select_dtypes(include=['number'])
            numeric_columns = [str(c) for c in numeric_df.columns]
            categorical_columns = [str(c) for c in df.columns if c not in numeric_df.columns]

            # Summary Statistics
            stats_preview = {}
            if not numeric_df.empty:
                desc = numeric_df.describe().T
                available_stats = [c for c in ['mean', 'std', 'min', '25%', '50%', '75%', 'max'] if c in desc.columns]
                desc_subset = desc[available_stats].to_dict(orient='index')
                stats_preview = {
                    str(col): {k: round(v, 2) for k, v in stats.items()}
                    for col, stats in desc_subset.items()
                }

            # Correlations (Top pairwise numeric correlations)
            correlations = []
            if len(numeric_columns) >= 2 and num_rows >= 2:
                try:
                    corr_matrix = numeric_df.corr()
                    for i in range(len(numeric_columns)):
                        for j in range(i + 1, len(numeric_columns)):
                            col1, col2 = numeric_columns[i], numeric_columns[j]
                            val = corr_matrix.loc[col1, col2]
                            if not pd.isna(val):
                                correlations.append({
                                    "col1": col1,
                                    "col2": col2,
                                    "correlation": round(float(val), 2)
                                })
                    # Sort by absolute correlation value descending
                    correlations.sort(key=lambda x: abs(x["correlation"]), reverse=True)
                except Exception as corr_err:
                    logger.warning(f"Correlation calculation error: {corr_err}")

            # EDA Insights Generation
            eda_insights = []
            if duplicate_rows > 0:
                eda_insights.append(f"Contains {duplicate_rows} duplicate row(s) ({round(duplicate_rows/num_rows*100, 1)}% of dataset).")

            cols_with_missing = [c for c, count in missing_counts.items() if count > 0]
            if cols_with_missing:
                high_missing = [f"{c} ({missing_pct[c]}%)" for c in cols_with_missing if missing_pct[c] > 20]
                if high_missing:
                    eda_insights.append(f"High missing values (>20%) in: {', '.join(high_missing[:5])}.")
                else:
                    eda_insights.append(f"Missing values detected in {len(cols_with_missing)} column(s).")
            else:
                eda_insights.append("No missing values found across any columns.")

            if correlations:
                top_corr = correlations[0]
                if abs(top_corr["correlation"]) > 0.7:
                    eda_insights.append(f"Strong correlation between `{top_corr['col1']}` and `{top_corr['col2']}` ({top_corr['correlation']}).")

            if numeric_columns:
                eda_insights.append(f"Identified {len(numeric_columns)} numerical feature(s) suitable for ML modeling.")

            # Summary Markdown for Gemini AI context ingestion
            summary_markdown = (
                f"📊 **Data Science Workspace Profile: `{filename}`**\n"
                f"- **Shape**: {num_rows} rows × {num_cols} columns\n"
                f"- **Duplicate Rows**: {duplicate_rows}\n"
                f"- **Numerical Columns ({len(numeric_columns)})**: {', '.join([f'`{c}`' for c in numeric_columns[:10]])}{'...' if len(numeric_columns)>10 else ''}\n"
                f"- **Categorical Columns ({len(categorical_columns)})**: {', '.join([f'`{c}`' for c in categorical_columns[:10]])}{'...' if len(categorical_columns)>10 else ''}\n"
                f"- **Total Missing Values**: {sum(missing_counts.values())}\n"
            )
            if eda_insights:
                summary_markdown += "- **Key EDA Insights**:\n  - " + "\n  - ".join(eda_insights) + "\n"

            # Secret sanitization check
            if self.contains_secret(summary_markdown):
                summary_markdown = f"📊 **Data Science Workspace Profile: `{filename}`**\n- **Shape**: {num_rows} rows × {num_cols} columns\n"

            return {
                "filename": filename,
                "num_rows": num_rows,
                "num_cols": num_cols,
                "columns": columns,
                "dtypes": dtypes,
                "missing_counts": missing_counts,
                "missing_pct": missing_pct,
                "duplicate_rows": duplicate_rows,
                "numeric_columns": numeric_columns,
                "categorical_columns": categorical_columns,
                "stats_preview": stats_preview,
                "correlations": correlations[:10],
                "eda_insights": eda_insights,
                "summary_markdown": summary_markdown
            }
        except Exception as e:
            return {"error": f"Failed to analyze dataset '{filename}': {str(e)}"}


data_analysis_service = DataAnalysisService()
