import math
import re
import logging
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
)
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.neighbors import KNeighborsClassifier

from app.services.data_analysis_service import data_analysis_service

logger = logging.getLogger("severus.ml_service")


class MLService:
    """Safe Machine Learning Workspace for classification and regression."""

    MAX_ROWS_TRAINING = 50000
    MAX_FEATURES_TRAINING = 100
    DEFAULT_TEST_SIZE = 0.2
    RANDOM_STATE = 42

    CLASSIFICATION_ALGORITHMS = {
        "logistic_regression": "Logistic Regression",
        "decision_tree": "Decision Tree Classifier",
        "random_forest": "Random Forest Classifier",
        "knn": "K-Nearest Neighbors Classifier",
    }

    REGRESSION_ALGORITHMS = {
        "linear_regression": "Linear Regression",
        "decision_tree_regressor": "Decision Tree Regressor",
        "random_forest_regressor": "Random Forest Regressor",
    }

    SECRET_PATTERNS = [
        r"AIzaSy[A-Za-z0-9_-]{33}",
        r"sk-[A-Za-z0-9_-]{20,}",
        r"\b(bearer|token|access_token|refresh_token)\b\s*[:=\s]\s*[^\s]+",
        r"\b(api_key|apikey|secret|password|passwd)\b\s*[:=]\s*[^\s]+",
    ]

    def contains_secret(self, text: str) -> bool:
        """Return True when text appears to contain credentials/secrets."""
        if not text or not isinstance(text, str):
            return False

        text_lower = text.lower()
        if any(
            keyword in text_lower
            for keyword in [
                "google_api_key",
                "tavily_api_key",
                "sk-",
                "aizasy",
            ]
        ):
            return True

        return any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in self.SECRET_PATTERNS
        )

    def auto_detect_target(self, df: pd.DataFrame) -> Optional[str]:
        """Detect a likely target column."""
        if df.empty:
            return None

        candidate_names = [
            "target",
            "label",
            "churn",
            "class",
            "price",
            "salary",
            "outcome",
            "status",
        ]
        col_map = {str(c).lower().strip(): str(c) for c in df.columns}

        for name in candidate_names:
            if name in col_map:
                return col_map[name]

        return str(df.columns[-1])

    def infer_problem_type(self, df: pd.DataFrame, target_col: str) -> str:
        """Infer classification or regression from the target column."""
        if target_col not in df.columns:
            return "classification"

        series = df[target_col].dropna()
        if series.empty:
            return "classification"

        if pd.api.types.is_numeric_dtype(series):
            if pd.api.types.is_bool_dtype(series):
                return "classification"

            # Float targets are normally continuous regression targets.
            if pd.api.types.is_float_dtype(series):
                return "regression"

            # Small integer targets are normally class labels.
            unique_vals = series.nunique()
            if unique_vals <= 10:
                return "classification"

            return "regression"

        return "classification"

    def recommend_model(
        self,
        df: pd.DataFrame,
        target_col: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Recommend a safe allowlisted algorithm."""
        if df.empty:
            return {"error": "Dataset is empty. Cannot generate model recommendation."}

        target = (
            target_col
            if target_col and target_col in df.columns
            else self.auto_detect_target(df)
        )

        if not target or target not in df.columns:
            return {"error": f"Target column '{target_col}' not found in dataset."}

        problem_type = self.infer_problem_type(df, target)
        num_rows, num_cols = df.shape

        numeric_cols = [
            str(c)
            for c in df.select_dtypes(include=["number"]).columns
            if str(c) != target
        ]
        categorical_cols = [
            str(c)
            for c in df.columns
            if str(c) != target and str(c) not in numeric_cols
        ]

        if problem_type == "classification":
            candidate_algos = self.CLASSIFICATION_ALGORITHMS

            if categorical_cols or num_cols > 5:
                recommended = "random_forest"
                rationale = (
                    "Random Forest handles mixed numeric/categorical features "
                    "and non-linear interactions well."
                )
            elif num_rows < 500:
                recommended = "logistic_regression"
                rationale = (
                    "Logistic Regression provides a clean, fast linear baseline "
                    "for smaller datasets."
                )
            else:
                recommended = "decision_tree"
                rationale = (
                    "Decision Tree Classifier provides easily interpretable "
                    "decision boundaries."
                )
        else:
            candidate_algos = self.REGRESSION_ALGORITHMS

            if categorical_cols or num_cols > 5:
                recommended = "random_forest_regressor"
                rationale = (
                    "Random Forest Regressor excels at capturing complex "
                    "non-linear relationships across tabular features."
                )
            elif num_rows < 500:
                recommended = "linear_regression"
                rationale = (
                    "Linear Regression provides an interpretable parametric "
                    "baseline for continuous regression."
                )
            else:
                recommended = "decision_tree_regressor"
                rationale = (
                    "Decision Tree Regressor fits non-linear tabular "
                    "continuous targets well."
                )

        return {
            "status": "success",
            "target_column": target,
            "problem_type": problem_type,
            "recommended_algorithm": recommended,
            "recommended_algorithm_name": candidate_algos[recommended],
            "rationale": rationale,
            "dataset_shape": {"rows": num_rows, "cols": num_cols},
            "candidate_algorithms": candidate_algos,
        }

    def prepare_dataset(
        self,
        df: pd.DataFrame,
        target_col: str,
        problem_type: str,
    ) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
        """Clean, encode and prepare a DataFrame for safe sklearn training."""
        if df.empty:
            raise ValueError("Dataset is empty.")

        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found in dataset.")

        if len(df) > self.MAX_ROWS_TRAINING:
            logger.info(
                "Subsampling dataset from %s to %s rows for training.",
                len(df),
                self.MAX_ROWS_TRAINING,
            )
            df = df.sample(
                n=self.MAX_ROWS_TRAINING,
                random_state=self.RANDOM_STATE,
            )

        df_clean = df.dropna(subset=[target_col]).copy()

        if len(df_clean) < 5:
            raise ValueError(
                f"Insufficient valid data rows ({len(df_clean)}) "
                "after dropping missing target values."
            )

        y_raw = df_clean[target_col]
        X_raw = df_clean.drop(columns=[target_col])

        if X_raw.empty:
            raise ValueError(
                "No feature columns available for training after removing target column."
            )

        if X_raw.shape[1] > self.MAX_FEATURES_TRAINING:
            X_raw = X_raw.iloc[:, : self.MAX_FEATURES_TRAINING]

        if problem_type == "classification":
            unique_classes = y_raw.nunique()

            if unique_classes < 2:
                raise ValueError(
                    f"Classification target '{target_col}' must contain at least "
                    f"2 distinct classes (found {unique_classes})."
                )

            if (
                pd.api.types.is_object_dtype(y_raw)
                or isinstance(y_raw.dtype, pd.CategoricalDtype)
                or pd.api.types.is_string_dtype(y_raw)
            ):
                label_encoder = LabelEncoder()
                y = pd.Series(
                    label_encoder.fit_transform(y_raw.astype(str)),
                    index=y_raw.index,
                    name=target_col,
                )
            else:
                y = y_raw
        else:
            if not pd.api.types.is_numeric_dtype(y_raw):
                try:
                    y = y_raw.astype(float)
                except (TypeError, ValueError):
                    raise ValueError(
                        f"Regression target '{target_col}' could not be "
                        "converted to continuous numeric values."
                    )
            else:
                y = y_raw

        encoded_parts: List[pd.DataFrame] = []

        for col in X_raw.columns:
            series = X_raw[col]

            if pd.api.types.is_numeric_dtype(series):
                median_value = series.median()
                if pd.isna(median_value):
                    median_value = 0.0

                filled = series.fillna(median_value)
                encoded_parts.append(
                    pd.DataFrame({col: filled}, index=series.index)
                )
            else:
                filled = series.fillna("missing").astype(str)
                dummies = pd.get_dummies(
                    filled,
                    prefix=col,
                    drop_first=False,
                    dtype=float,
                )
                encoded_parts.append(dummies)

        if not encoded_parts:
            raise ValueError("No usable feature columns found.")

        X_processed = pd.concat(encoded_parts, axis=1)
        feature_names = [str(c) for c in X_processed.columns]

        return X_processed, y, feature_names

    def train_and_evaluate(
        self,
        file_bytes: bytes,
        filename: str,
        target_col: str,
        algorithm: str = "random_forest",
        problem_type: Optional[str] = None,
        test_size: float = DEFAULT_TEST_SIZE,
    ) -> Dict[str, Any]:
        """Run the complete safe ML workflow."""
        validation_err = data_analysis_service.validate_dataset(
            file_bytes,
            filename,
        )
        if validation_err:
            return {"error": validation_err}

        try:
            df = data_analysis_service.read_dataframe(
                file_bytes,
                filename,
            )

            if df.empty:
                return {
                    "error": f"Uploaded dataset '{filename}' contains no data rows."
                }

            if target_col not in df.columns:
                return {
                    "error": (
                        f"Target column '{target_col}' not found in dataset "
                        f"columns: {list(df.columns)}."
                    )
                }

            if not problem_type:
                problem_type = self.infer_problem_type(df, target_col)

            if problem_type not in {"classification", "regression"}:
                return {"error": "Problem type must be classification or regression."}

            if not 0 < test_size < 1:
                return {"error": "test_size must be between 0 and 1."}

            if (
                problem_type == "classification"
                and algorithm not in self.CLASSIFICATION_ALGORITHMS
            ):
                return {
                    "error": (
                        f"Unsupported classification algorithm '{algorithm}'. "
                        f"Allowed algorithms: "
                        f"{list(self.CLASSIFICATION_ALGORITHMS.keys())}"
                    )
                }

            if (
                problem_type == "regression"
                and algorithm not in self.REGRESSION_ALGORITHMS
            ):
                return {
                    "error": (
                        f"Unsupported regression algorithm '{algorithm}'. "
                        f"Allowed algorithms: "
                        f"{list(self.REGRESSION_ALGORITHMS.keys())}"
                    )
                }

            X, y, feature_names = self.prepare_dataset(
                df,
                target_col,
                problem_type,
            )

            # Train / Test Split
            stratify_y = None
            split_test_size = test_size

            if problem_type == "classification":
                class_counts = y.value_counts()

                # Stratification is safe only when every class has at least
                # two samples. This also avoids small-dataset split failures.
                if class_counts.min() >= 2:
                    stratify_y = y

                    requested_test_samples = math.ceil(
                        len(y) * test_size
                    )
                    min_test_samples = len(class_counts)

                    # At least one test sample is required for every class.
                    split_test_size = max(
                        requested_test_samples,
                        min_test_samples,
                    )

                    # train_test_split accepts an integer number of test rows.
                    if split_test_size >= len(y):
                        split_test_size = max(
                            min_test_samples,
                            len(y) - 1,
                        )

            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y,
                test_size=split_test_size,
                random_state=self.RANDOM_STATE,
                stratify=stratify_y,
            )

            # Feature scaling for algorithms that benefit from it.
            need_scaling = algorithm in {
                "logistic_regression",
                "linear_regression",
                "knn",
            }

            if need_scaling:
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train)
                X_test_scaled = scaler.transform(X_test)
            else:
                X_train_scaled = X_train
                X_test_scaled = X_test

            # Safe allowlisted model construction.
            model = None

            if problem_type == "classification":
                if algorithm == "logistic_regression":
                    model = LogisticRegression(
                        max_iter=1000,
                        random_state=self.RANDOM_STATE,
                    )
                elif algorithm == "decision_tree":
                    model = DecisionTreeClassifier(
                        max_depth=10,
                        random_state=self.RANDOM_STATE,
                    )
                elif algorithm == "random_forest":
                    model = RandomForestClassifier(
                        n_estimators=50,
                        max_depth=10,
                        random_state=self.RANDOM_STATE,
                    )
                elif algorithm == "knn":
                    n_neighbors = min(
                        5,
                        max(1, len(X_train)),
                    )
                    model = KNeighborsClassifier(
                        n_neighbors=n_neighbors,
                    )
            else:
                if algorithm == "linear_regression":
                    model = LinearRegression()
                elif algorithm == "decision_tree_regressor":
                    model = DecisionTreeRegressor(
                        max_depth=10,
                        random_state=self.RANDOM_STATE,
                    )
                elif algorithm == "random_forest_regressor":
                    model = RandomForestRegressor(
                        n_estimators=50,
                        max_depth=10,
                        random_state=self.RANDOM_STATE,
                    )

            if model is None:
                return {"error": f"Could not create supported model '{algorithm}'."}

            model.fit(X_train_scaled, y_train)
            y_pred = model.predict(X_test_scaled)

            metrics: Dict[str, Any]

            if problem_type == "classification":
                accuracy = float(accuracy_score(y_test, y_pred))
                precision = float(
                    precision_score(
                        y_test,
                        y_pred,
                        average="weighted",
                        zero_division=0,
                    )
                )
                recall = float(
                    recall_score(
                        y_test,
                        y_pred,
                        average="weighted",
                        zero_division=0,
                    )
                )
                f1 = float(
                    f1_score(
                        y_test,
                        y_pred,
                        average="weighted",
                        zero_division=0,
                    )
                )
                cm = confusion_matrix(y_test, y_pred).tolist()
                classes_list = [
                    str(c)
                    for c in np.unique(
                        np.concatenate(
                            [
                                np.asarray(y_test),
                                np.asarray(y_pred),
                            ]
                        )
                    )
                ]

                metrics = {
                    "accuracy": round(accuracy, 4),
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1_score": round(f1, 4),
                    "confusion_matrix": cm,
                    "classes": classes_list,
                }

                algo_display = self.CLASSIFICATION_ALGORITHMS[algorithm]
                summary_markdown = (
                    f"🤖 **Machine Learning Evaluation ({algo_display})**\n"
                    f"- **Task**: Classification on `{target_col}`\n"
                    f"- **Accuracy**: {metrics['accuracy'] * 100:.2f}%\n"
                    f"- **Precision**: {metrics['precision']:.4f}\n"
                    f"- **Recall**: {metrics['recall']:.4f}\n"
                    f"- **F1-Score**: {metrics['f1_score']:.4f}\n"
                    f"- **Train/Test Rows**: {len(X_train)} train / "
                    f"{len(X_test)} test\n"
                )
            else:
                mae = float(mean_absolute_error(y_test, y_pred))
                mse = float(mean_squared_error(y_test, y_pred))
                rmse = float(math.sqrt(mse))
                r2 = float(r2_score(y_test, y_pred))

                metrics = {
                    "mae": round(mae, 4),
                    "mse": round(mse, 4),
                    "rmse": round(rmse, 4),
                    "r2_score": round(r2, 4),
                }

                algo_display = self.REGRESSION_ALGORITHMS[algorithm]
                summary_markdown = (
                    f"🤖 **Machine Learning Evaluation ({algo_display})**\n"
                    f"- **Task**: Regression on `{target_col}`\n"
                    f"- **R² Score**: {metrics['r2_score']:.4f}\n"
                    f"- **RMSE**: {metrics['rmse']:.4f}\n"
                    f"- **MAE**: {metrics['mae']:.4f}\n"
                    f"- **MSE**: {metrics['mse']:.4f}\n"
                    f"- **Train/Test Rows**: {len(X_train)} train / "
                    f"{len(X_test)} test\n"
                )

            if self.contains_secret(summary_markdown):
                summary_markdown = (
                    f"🤖 **Machine Learning Evaluation ({algorithm})**: "
                    f"Model trained successfully on `{target_col}`."
                )

            return {
                "status": "success",
                "filename": filename,
                "target_column": target_col,
                "problem_type": problem_type,
                "algorithm": algorithm,
                "algorithm_name": (
                    self.CLASSIFICATION_ALGORITHMS.get(algorithm)
                    or self.REGRESSION_ALGORITHMS.get(algorithm)
                ),
                "num_train_samples": len(X_train),
                "num_test_samples": len(X_test),
                "num_features": len(feature_names),
                "feature_names": feature_names[:20],
                "metrics": metrics,
                "summary_markdown": summary_markdown,
            }

        except Exception as exc:
            logger.error(
                "ML execution error on dataset '%s': %s",
                filename,
                str(exc),
            )
            return {
                "error": (
                    f"Failed to train ML model on dataset '{filename}': "
                    f"{str(exc)}"
                )
            }


ml_service = MLService()
