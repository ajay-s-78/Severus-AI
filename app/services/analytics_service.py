import io
import math
import logging
from typing import Dict, Any, Optional, List, Tuple

import pandas as pd
import numpy as np
import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from app.services.data_analysis_service import data_analysis_service


logger = logging.getLogger("severus.analytics_service")


class AnalyticsService:
    """
    Safe analytics and visualization service for Severus-AI.

    Provides:
    - Dataset analytics
    - Descriptive statistics
    - Missing-value analysis
    - Duplicate detection
    - IQR-based outlier detection
    - Correlation analysis
    - Safe chart generation

    Does NOT execute arbitrary user Python code.
    """

    MAX_ROWS = 50000
    MAX_COLUMNS = 100

    ALLOWED_CHART_TYPES = {
        "histogram",
        "bar",
        "line",
        "scatter",
        "box",
        "heatmap",
    }

    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """Validate dataset before analytics."""

        if df is None or df.empty:
            raise ValueError("Dataset is empty.")

        if len(df) > self.MAX_ROWS:
            raise ValueError(
                f"Dataset exceeds the maximum limit of {self.MAX_ROWS} rows."
            )

        if len(df.columns) > self.MAX_COLUMNS:
            raise ValueError(
                f"Dataset exceeds the maximum limit of {self.MAX_COLUMNS} columns."
            )

    def _validate_columns(
        self,
        df: pd.DataFrame,
        columns: List[str],
    ) -> None:
        """Validate requested dataset columns."""

        if not columns:
            raise ValueError("At least one column must be selected.")

        missing = [column for column in columns if column not in df.columns]

        if missing:
            raise ValueError(
                f"Column(s) not found in dataset: {missing}"
            )

    def analyze_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate structured analytics for a DataFrame.
        """

        self._validate_dataframe(df)

        numeric_columns = [
            str(column)
            for column in df.select_dtypes(include=[np.number]).columns
        ]

        categorical_columns = [
            str(column)
            for column in df.columns
            if str(column) not in numeric_columns
        ]

        missing_values = {}

        for column in df.columns:
            missing_count = int(df[column].isna().sum())

            missing_values[str(column)] = {
                "count": missing_count,
                "percentage": round(
                    (missing_count / len(df)) * 100,
                    2,
                ),
            }

        statistics = {}

        if numeric_columns:
            numeric_stats = df[numeric_columns].describe()

            for column in numeric_columns:
                statistics[column] = {
                    "count": int(numeric_stats.loc["count", column]),
                    "mean": self._safe_float(
                        numeric_stats.loc["mean", column]
                    ),
                    "std": self._safe_float(
                        numeric_stats.loc["std", column]
                    ),
                    "min": self._safe_float(
                        numeric_stats.loc["min", column]
                    ),
                    "25%": self._safe_float(
                        numeric_stats.loc["25%", column]
                    ),
                    "median": self._safe_float(
                        df[column].median()
                    ),
                    "75%": self._safe_float(
                        numeric_stats.loc["75%", column]
                    ),
                    "max": self._safe_float(
                        numeric_stats.loc["max", column]
                    ),
                }

        unique_counts = {
            str(column): int(df[column].nunique(dropna=True))
            for column in df.columns
        }

        outliers = self.detect_outliers(df)

        correlations = self.analyze_correlations(df)

        insights = self.generate_insights(
            df=df,
            missing_values=missing_values,
            statistics=statistics,
            outliers=outliers,
            correlations=correlations,
        )

        return {
            "status": "success",
            "dataset_shape": {
                "rows": int(df.shape[0]),
                "columns": int(df.shape[1]),
            },
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "missing_values": missing_values,
            "duplicate_rows": int(df.duplicated().sum()),
            "unique_counts": unique_counts,
            "statistics": statistics,
            "outliers": outliers,
            "correlations": correlations,
            "insights": insights,
        }

    def analyze_file(
        self,
        file_bytes: bytes,
        filename: str,
    ) -> Dict[str, Any]:
        """Read and analyze a supported dataset file."""

        validation_error = data_analysis_service.validate_dataset(
            file_bytes,
            filename,
        )

        if validation_error:
            return {"error": validation_error}

        try:
            df = data_analysis_service.read_dataframe(
                file_bytes,
                filename,
            )

            return self.analyze_dataframe(df)

        except Exception as exc:
            logger.error(
                "Analytics error for '%s': %s",
                filename,
                str(exc),
            )

            return {
                "error": (
                    f"Failed to analyze dataset '{filename}': "
                    f"{str(exc)}"
                )
            }

    def detect_outliers(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Detect numerical outliers using the IQR method."""

        numeric_columns = df.select_dtypes(
            include=[np.number]
        ).columns

        result = {}

        for column in numeric_columns:
            series = df[column].dropna()

            if series.empty:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_mask = (
                (series < lower_bound)
                | (series > upper_bound)
            )

            outlier_count = int(outlier_mask.sum())

            result[str(column)] = {
                "q1": round(q1, 4),
                "q3": round(q3, 4),
                "iqr": round(iqr, 4),
                "lower_bound": round(lower_bound, 4),
                "upper_bound": round(upper_bound, 4),
                "outlier_count": outlier_count,
                "outlier_percentage": round(
                    (outlier_count / len(series)) * 100,
                    2,
                ),
            }

        return result

    def analyze_correlations(
        self,
        df: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Calculate Pearson correlations for numeric columns."""

        numeric_df = df.select_dtypes(
            include=[np.number]
        )

        if numeric_df.shape[1] < 2:
            return {
                "available": False,
                "message": (
                    "At least two numerical columns are "
                    "required for correlation analysis."
                ),
                "matrix": {},
                "strongest_positive": [],
                "strongest_negative": [],
            }

        correlation_matrix = numeric_df.corr(
            method="pearson"
        )

        pairs = []

        columns = list(correlation_matrix.columns)

        for i in range(len(columns)):
            for j in range(i + 1, len(columns)):
                value = correlation_matrix.iloc[i, j]

                if pd.isna(value):
                    continue

                pairs.append(
                    {
                        "column_1": str(columns[i]),
                        "column_2": str(columns[j]),
                        "correlation": round(float(value), 4),
                    }
                )

        strongest_positive = sorted(
            pairs,
            key=lambda item: item["correlation"],
            reverse=True,
        )[:5]

        strongest_negative = sorted(
            pairs,
            key=lambda item: item["correlation"],
        )[:5]

        matrix = {}

        for column in correlation_matrix.columns:
            matrix[str(column)] = {
                str(other): self._safe_float(
                    correlation_matrix.loc[column, other]
                )
                for other in correlation_matrix.columns
            }

        return {
            "available": True,
            "matrix": matrix,
            "strongest_positive": strongest_positive,
            "strongest_negative": strongest_negative,
        }

    def generate_insights(
        self,
        df: pd.DataFrame,
        missing_values: Dict[str, Any],
        statistics: Dict[str, Any],
        outliers: Dict[str, Any],
        correlations: Dict[str, Any],
    ) -> List[str]:
        """Generate concise rule-based analytical insights."""

        insights = []

        if missing_values:
            highest_missing = max(
                missing_values.items(),
                key=lambda item: item[1]["percentage"],
            )

            if highest_missing[1]["count"] > 0:
                insights.append(
                    f"'{highest_missing[0]}' has the highest "
                    f"missing-value percentage "
                    f"({highest_missing[1]['percentage']}%)."
                )

        duplicate_count = int(df.duplicated().sum())

        if duplicate_count > 0:
            insights.append(
                f"The dataset contains {duplicate_count} duplicate row(s)."
            )

        if statistics:
            highest_variance_column = None
            highest_std = -1.0

            for column, values in statistics.items():
                std_value = values.get("std")

                if std_value is not None and not pd.isna(std_value):
                    if float(std_value) > highest_std:
                        highest_std = float(std_value)
                        highest_variance_column = column

            if highest_variance_column:
                insights.append(
                    f"'{highest_variance_column}' has the highest "
                    f"standard deviation among numerical columns."
                )

        outlier_columns = [
            column
            for column, values in outliers.items()
            if values["outlier_count"] > 0
        ]

        if outlier_columns:
            insights.append(
                "Outliers were detected in: "
                + ", ".join(outlier_columns[:5])
                + "."
            )

        if correlations.get("available"):
            positive = correlations.get(
                "strongest_positive",
                [],
            )

            negative = correlations.get(
                "strongest_negative",
                [],
            )

            if positive:
                strongest = positive[0]

                if strongest["correlation"] < 0.9999:
                    insights.append(
                        f"The strongest positive correlation is between "
                        f"'{strongest['column_1']}' and "
                        f"'{strongest['column_2']}' "
                        f"({strongest['correlation']})."
                    )

            if negative:
                strongest = negative[0]

                if strongest["correlation"] < -0.1:
                    insights.append(
                        f"The strongest negative correlation is between "
                        f"'{strongest['column_1']}' and "
                        f"'{strongest['column_2']}' "
                        f"({strongest['correlation']})."
                    )

        if not insights:
            insights.append(
                "No major analytical issues were detected "
                "by the automatic checks."
            )

        return insights

    def generate_chart(
        self,
        df: pd.DataFrame,
        chart_type: str,
        columns: List[str],
    ) -> Tuple[bytes, str]:
        """
        Generate a chart safely.

        Returns:
            (PNG bytes, chart title)
        """

        self._validate_dataframe(df)

        chart_type = str(chart_type).lower().strip()

        if chart_type not in self.ALLOWED_CHART_TYPES:
            raise ValueError(
                f"Unsupported chart type '{chart_type}'. "
                f"Allowed types: "
                f"{sorted(self.ALLOWED_CHART_TYPES)}"
            )

        self._validate_columns(df, columns)

        fig, ax = plt.subplots(
            figsize=(9, 6)
        )

        title = ""

        try:
            if chart_type == "histogram":
                if len(columns) != 1:
                    raise ValueError(
                        "Histogram requires exactly one column."
                    )

                column = columns[0]

                if not pd.api.types.is_numeric_dtype(
                    df[column]
                ):
                    raise ValueError(
                        "Histogram requires a numerical column."
                    )

                ax.hist(
                    df[column].dropna(),
                    bins=20,
                )

                title = f"Histogram - {column}"
                ax.set_xlabel(column)
                ax.set_ylabel("Frequency")

            elif chart_type == "bar":
                if len(columns) != 1:
                    raise ValueError(
                        "Bar chart requires exactly one column."
                    )

                column = columns[0]

                counts = (
                    df[column]
                    .astype(str)
                    .value_counts()
                    .head(20)
                )

                ax.bar(
                    counts.index,
                    counts.values,
                )

                title = f"Bar Chart - {column}"
                ax.set_xlabel(column)
                ax.set_ylabel("Count")
                ax.tick_params(
                    axis="x",
                    rotation=45,
                )

            elif chart_type == "line":
                if len(columns) not in (1, 2):
                    raise ValueError(
                        "Line chart requires one or two columns."
                    )

                if len(columns) == 1:
                    column = columns[0]

                    if not pd.api.types.is_numeric_dtype(
                        df[column]
                    ):
                        raise ValueError(
                            "Line chart requires a numerical column."
                        )

                    ax.plot(
                        df[column].reset_index(drop=True)
                    )

                    title = f"Line Chart - {column}"

                else:
                    x_column = columns[0]
                    y_column = columns[1]

                    if not pd.api.types.is_numeric_dtype(
                        df[y_column]
                    ):
                        raise ValueError(
                            "Line chart Y-axis must be numerical."
                        )

                    ax.plot(
                        df[x_column],
                        df[y_column],
                    )

                    title = (
                        f"Line Chart - "
                        f"{x_column} vs {y_column}"
                    )

                ax.set_xlabel(columns[0])
                ax.set_ylabel(
                    columns[-1]
                )

            elif chart_type == "scatter":
                if len(columns) != 2:
                    raise ValueError(
                        "Scatter plot requires exactly two columns."
                    )

                x_column = columns[0]
                y_column = columns[1]

                if not pd.api.types.is_numeric_dtype(
                    df[x_column]
                ):
                    raise ValueError(
                        "Scatter plot X-axis must be numerical."
                    )

                if not pd.api.types.is_numeric_dtype(
                    df[y_column]
                ):
                    raise ValueError(
                        "Scatter plot Y-axis must be numerical."
                    )

                ax.scatter(
                    df[x_column],
                    df[y_column],
                )

                title = (
                    f"Scatter Plot - "
                    f"{x_column} vs {y_column}"
                )

                ax.set_xlabel(x_column)
                ax.set_ylabel(y_column)

            elif chart_type == "box":
                if len(columns) < 1:
                    raise ValueError(
                        "Box plot requires at least one column."
                    )

                for column in columns:
                    if not pd.api.types.is_numeric_dtype(
                        df[column]
                    ):
                        raise ValueError(
                            "Box plot requires numerical columns."
                        )

                ax.boxplot(
                    [
                        df[column].dropna()
                        for column in columns
                    ],
                    labels=columns,
                )

                title = "Box Plot"
                ax.set_ylabel("Value")

                ax.tick_params(
                    axis="x",
                    rotation=45,
                )

            elif chart_type == "heatmap":
                numeric_columns = [
                    column
                    for column in columns
                    if pd.api.types.is_numeric_dtype(
                        df[column]
                    )
                ]

                if len(numeric_columns) < 2:
                    raise ValueError(
                        "Heatmap requires at least two numerical columns."
                    )

                corr = df[numeric_columns].corr()

                image = ax.imshow(
                    corr.values,
                    interpolation="nearest",
                    aspect="auto",
                )

                fig.colorbar(
                    image,
                    ax=ax,
                )

                ax.set_xticks(
                    range(len(numeric_columns))
                )

                ax.set_yticks(
                    range(len(numeric_columns))
                )

                ax.set_xticklabels(
                    numeric_columns,
                    rotation=45,
                    ha="right",
                )

                ax.set_yticklabels(
                    numeric_columns
                )

                title = "Correlation Heatmap"

            ax.set_title(title)
            fig.tight_layout()

            buffer = io.BytesIO()

            fig.savefig(
                buffer,
                format="png",
                dpi=120,
                bbox_inches="tight",
            )

            buffer.seek(0)

            return buffer.read(), title

        finally:
            plt.close(fig)

    def generate_chart_from_file(
        self,
        file_bytes: bytes,
        filename: str,
        chart_type: str,
        columns: List[str],
    ) -> Tuple[bytes, str]:
        """Read a dataset and generate a safe chart."""

        validation_error = data_analysis_service.validate_dataset(
            file_bytes,
            filename,
        )

        if validation_error:
            raise ValueError(validation_error)

        df = data_analysis_service.read_dataframe(
            file_bytes,
            filename,
        )

        return self.generate_chart(
            df=df,
            chart_type=chart_type,
            columns=columns,
        )

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Convert numeric values into JSON-safe floats."""

        if value is None:
            return None

        try:
            value = float(value)

            if math.isnan(value) or math.isinf(value):
                return None

            return round(value, 6)

        except (TypeError, ValueError):
            return None


analytics_service = AnalyticsService()