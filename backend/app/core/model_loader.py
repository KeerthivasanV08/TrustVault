from __future__ import annotations

import json
import logging
import os
import pickle
import tempfile
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
import h5py

from app.core.feature_schema import BEHAVIOR_SCHEMA
from app.db.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class ModelLoaderError(Exception):
    pass


class ModelFormatError(ModelLoaderError):
    pass


class ModelValidationError(ModelLoaderError):
    pass


@dataclass(frozen=True)
class ArtifactInfo:
    path: Path
    kind: str
    exists: bool
    size_bytes: int = 0


class ModelLoader:
    """Enterprise model loader with artifact detection, caching, and diagnostics."""

    def __init__(self) -> None:
        self._loaded: Dict[str, Any] = {}
        self._status: Dict[str, Dict[str, Any]] = {}
        self._health_snapshot: Dict[str, Any] = {}
        self._app_dir = Path(__file__).resolve().parents[1]
        self._models_dir = self._app_dir / "models" / "transaction"
        self._load_order = ("behavioral", "sequence", "graph")
        self._neo4j_client = Neo4jClient()

    # ------------------------------------------------------------------
    # Artifact detection
    # ------------------------------------------------------------------
    def _artifact_info(self, path: Path) -> ArtifactInfo:
        if not path.exists():
            return ArtifactInfo(path=path, kind="missing", exists=False)
        with open(path, "rb") as handle:
            signature = handle.read(8)
        kind = self._detect_kind(path, signature)
        return ArtifactInfo(path=path, kind=kind, exists=True, size_bytes=path.stat().st_size)

    def _detect_kind(self, path: Path, signature: bytes) -> str:
        suffix = path.suffix.lower()
        if signature.startswith(b"\x89HDF\r\n\x1a\n") or suffix in {".h5", ".hdf5"}:
            return "keras_h5"
        if signature.startswith(b"PK\x03\x04") or suffix == ".keras":
            return "keras_native"
        if signature.startswith(b"\x93NUMPY") or suffix == ".npy":
            return "numpy"
        if suffix in {".json", ".jsonl"}:
            return "json"
        if signature[:1] == b"\x80" or suffix in {".pkl", ".pickle", ".joblib"}:
            return "pickle_or_joblib"
        return "unknown"

    def inspect_artifact(self, path: Path) -> Dict[str, Any]:
        info = self._artifact_info(path)
        return {
            "path": str(info.path),
            "kind": info.kind,
            "exists": info.exists,
            "size_bytes": info.size_bytes,
        }

    # ------------------------------------------------------------------
    # Low-level loaders
    # ------------------------------------------------------------------
    def _load_json(self, path: Path) -> Any:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _load_pickle(self, path: Path) -> Any:
        with open(path, "rb") as handle:
            return pickle.load(handle)

    def _load_joblib(self, path: Path) -> Any:
        return joblib.load(path)

    def _load_numpy(self, path: Path) -> Any:
        return np.load(path, allow_pickle=True)

    def _load_keras_model(self, path: Path) -> Any:
        try:
            import tensorflow as tf
        except Exception as exc:  # pragma: no cover - import failure is environment specific
            raise ModelFormatError(f"TensorFlow unavailable: {exc}") from exc

        if path.suffix.lower() == ".keras":
            logger.debug(f"Loading modern .keras format: {path}")
            return tf.keras.models.load_model(path, compile=False)
        if path.suffix.lower() in {".h5", ".hdf5"}:
            logger.debug(f"Loading legacy H5 format: {path}")
            return tf.keras.models.load_model(path, compile=False)
        raise ModelFormatError(f"Unsupported Keras artifact format: {path.suffix}")

    def _save_repaired_keras_model(self, model: Any, target_path: Path) -> Path:
        try:
            import tensorflow as tf
        except Exception as exc:  # pragma: no cover - import failure is environment specific
            raise ModelFormatError(f"TensorFlow unavailable: {exc}") from exc

        target_path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(
            prefix=f".{target_path.stem}.",
            suffix=target_path.suffix,
            dir=str(target_path.parent),
        )
        os.close(fd)
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink()

        try:
            model.save(temp_path)
            tf.keras.models.load_model(temp_path, compile=False)

            if target_path.exists():
                backup_name = f"{target_path.stem}.broken-{importlib_metadata.version('tensorflow').replace('.', '_')}{target_path.suffix}"
                backup_path = target_path.with_name(backup_name)
                if backup_path.exists():
                    backup_path.unlink()
                target_path.replace(backup_path)

            temp_path.replace(target_path)
            logger.info("Repaired sequence model written to %s", target_path)
            return target_path
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _strip_unsupported_lstm_keys(self, payload: Any) -> Any:
        if isinstance(payload, dict):
            cleaned = {}
            for key, value in payload.items():
                if key in {"time_major", "batch_input_shape"}:
                    continue
                cleaned[key] = self._strip_unsupported_lstm_keys(value)
            return cleaned
        if isinstance(payload, list):
            return [self._strip_unsupported_lstm_keys(item) for item in payload]
        return payload

    def _reconstruct_sequence_model(self) -> Any:
        try:
            import tensorflow as tf
        except Exception as exc:
            raise ModelFormatError(f"TensorFlow unavailable: {exc}") from exc

        model = tf.keras.Sequential(
            [
                tf.keras.layers.Input(shape=(10, 5), name="transaction_sequence_input"),
                tf.keras.layers.LSTM(64, return_sequences=True, name="lstm"),
                tf.keras.layers.Dropout(0.3, name="dropout"),
                tf.keras.layers.BatchNormalization(name="batch_normalization"),
                tf.keras.layers.LSTM(32, name="lstm_1"),
                tf.keras.layers.Dropout(0.3, name="dropout_1"),
                tf.keras.layers.Dense(32, activation="relu", name="dense"),
                tf.keras.layers.Dense(1, activation="sigmoid", name="dense_1"),
            ],
            name="sequential",
        )
        model.compile(optimizer="adam", loss="binary_crossentropy", metrics=["accuracy"])
        return model

    def _load_legacy_lstm_h5(self, path: Path) -> Any:
        try:
            import tensorflow as tf
        except Exception as exc:
            raise ModelFormatError(f"TensorFlow unavailable: {exc}") from exc

        if not path.exists():
            raise FileNotFoundError(str(path))

        try:
            with h5py.File(path, "r") as handle:
                model_config = handle.attrs.get("model_config")
                if model_config is None:
                    raise ModelFormatError(f"Missing model_config in legacy H5: {path}")
                if isinstance(model_config, bytes):
                    model_config = model_config.decode("utf-8")

            config_obj = json.loads(model_config)
            patched_config = self._strip_unsupported_lstm_keys(config_obj)
            logger.debug("Patched legacy H5 config for %s", path)
        except Exception:
            logger.debug("Unable to parse legacy model config for %s; falling back to manual reconstruction", path)

        model = self._reconstruct_sequence_model()

        try:
            model.load_weights(path)
        except Exception as exc:
            raise ModelLoaderError(f"Legacy LSTM weights load failed for {path}: {exc}") from exc

        logger.info("Legacy sequence model reconstructed from H5: %s", path)
        return model

    def _load_artifact(self, path: Path, expected_kind: Optional[str] = None) -> Any:
        info = self._artifact_info(path)
        if not info.exists:
            raise FileNotFoundError(str(path))

        kind = info.kind
        if expected_kind == "keras" and kind not in {"keras_h5", "keras_native"}:
            raise ModelFormatError(f"Expected Keras artifact, found {kind} at {path}")
        if expected_kind == "json" and kind != "json":
            raise ModelFormatError(f"Expected JSON artifact, found {kind} at {path}")
        if expected_kind == "numpy" and kind != "numpy":
            raise ModelFormatError(f"Expected NumPy artifact, found {kind} at {path}")
        if expected_kind == "pickle_or_joblib" and kind not in {"pickle_or_joblib"}:
            raise ModelFormatError(f"Expected pickle/joblib artifact, found {kind} at {path}")

        try:
            if kind == "json":
                return self._load_json(path)
            if kind == "numpy":
                return self._load_numpy(path)
            if kind in {"keras_h5", "keras_native"}:
                return self._load_keras_model(path)
            if path.suffix.lower() == ".joblib":
                return self._load_joblib(path)
            if path.suffix.lower() in {".pkl", ".pickle", ".joblib"}:
                return self._load_joblib(path)
            if kind == "pickle_or_joblib":
                return self._load_joblib(path)
        except Exception as exc:
            # Avoid printing full tracebacks at normal info/warn levels for artifact load
            msg = f"Failed loading artifact {path}: {exc}"
            if logger.isEnabledFor(logging.DEBUG):
                logger.exception(msg)
            else:
                logger.warning(msg)
            raise ModelLoaderError(msg) from exc

        raise ModelFormatError(f"Unsupported artifact type for {path}")

    # ------------------------------------------------------------------
    # Bundle loaders
    # ------------------------------------------------------------------
    def get_behavioral_model(self) -> Tuple[Any, Any, Any]:
        if "behavioral_model" not in self._loaded:
            model_path = self._models_dir / "behavioral_lightgbm.pkl"
            scaler_path = self._models_dir / "behavioral_scaler.pkl"
            schema_path = self._models_dir / "behavioral_features.json"

            try:
                model = self._load_artifact(model_path, expected_kind="pickle_or_joblib")
                scaler = self._load_artifact(scaler_path, expected_kind="pickle_or_joblib")
                schema = self._load_artifact(schema_path, expected_kind="json")

                if not hasattr(model, "predict_proba"):
                    raise ModelValidationError("Behavioral model missing predict_proba")
                if not hasattr(scaler, "transform"):
                    raise ModelValidationError("Behavioral scaler missing transform")
                if not isinstance(schema, dict):
                    raise ModelValidationError("Behavioral schema is not a dict")

                self._loaded["behavioral_model"] = model
                self._loaded["behavioral_scaler"] = scaler
                self._loaded["behavioral_features"] = schema
                self._status["behavioral_model"] = {"state": "healthy", "path": str(model_path)}
                self._status["behavioral_scaler"] = {"state": "healthy", "path": str(scaler_path)}
                self._status["behavioral_features"] = {"state": "healthy", "path": str(schema_path)}
            except Exception as exc:
                logger.exception("Behavioral model bundle failed to load")
                self._loaded["behavioral_model"] = None
                self._loaded["behavioral_scaler"] = None
                self._loaded["behavioral_features"] = BEHAVIOR_SCHEMA.copy()
                self._status["behavioral_model"] = {"state": "failed", "reason": str(exc), "path": str(model_path)}
                self._status["behavioral_scaler"] = {"state": "failed", "reason": str(exc), "path": str(scaler_path)}
                self._status["behavioral_features"] = {"state": "failed", "reason": str(exc), "path": str(schema_path)}

        return (
            self._loaded.get("behavioral_model"),
            self._loaded.get("behavioral_scaler"),
            self._loaded.get("behavioral_features"),
        )

    def get_sequence_model(self) -> Tuple[Any, Any, Any]:
        if "sequence_model" not in self._loaded:
            model_path_keras = self._models_dir / "lstm_sequence_model.keras"
            model_path_h5 = self._models_dir / "lstm_sequence_model.h5"
            scaler_path = self._models_dir / "sequence_scaler.pkl"
            metadata_path = self._models_dir / "sequence_model_metadata.pkl"

            try:
                model = None
                model_path = None
                model_format = None
                repair_reason = None

                # Load model registry if present to allow explicit active model selection
                registry_path = self._app_dir / "models" / "metadata" / "model_registry.json"
                active_entry = None
                if registry_path.exists():
                    try:
                        registry = self._load_json(registry_path)
                        active_entry = registry.get("transaction_sequence")
                    except Exception:
                        logger.debug("Unable to read model registry at %s", registry_path)

                # If registry specifies active model, prefer it
                if active_entry and active_entry.get("active_model"):
                    candidate = Path(active_entry.get("active_model"))
                    if not candidate.is_absolute():
                        candidate = (self._app_dir / candidate).resolve()
                    if candidate.exists():
                        model_path = candidate
                        model_format = "registry_specified"
                        logger.info("Using registry active model for sequence: %s", model_path)
                        try:
                            if model_path.suffix.lower() in {".h5", ".hdf5"}:
                                model = self._load_legacy_lstm_h5(model_path)
                                model_format = "h5_legacy"
                            else:
                                model = self._load_artifact(model_path, expected_kind="keras")
                                model_format = "keras_native"
                        except Exception as exc:
                            repair_reason = str(exc)
                            logger.warning("Registry active model failed to load: %s", exc)

                # If no registry or registry failed, prefer legacy H5 (known to be compatible)
                if model is None and model_path is None and model_path_h5.exists():
                    model_path = model_path_h5
                    model_format = "h5_legacy"
                    logger.info("Using legacy H5 format for sequence model: %s", model_path)
                    model = self._load_legacy_lstm_h5(model_path)
                    # attempt to write repaired .keras quietly (debug only)
                    try:
                        self._save_repaired_keras_model(model, model_path_keras)
                        model_path = model_path_keras
                        model_format = "keras_repaired_from_h5"
                        repair_reason = repair_reason or "repaired_from_h5"
                    except Exception as repair_exc:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.exception("Failed to rewrite repaired .keras artifact from legacy H5")
                        else:
                            logger.debug("Failed to rewrite repaired .keras artifact from legacy H5: %s", repair_exc)
                        self._status["sequence_model_repair"] = {
                            "state": "failed",
                            "reason": str(repair_exc),
                            "source": str(model_path_h5),
                            "target": str(model_path_keras),
                        }

                # If still no model, try native .keras but handle known incompatibilities gracefully
                if model is None and model_path_keras.exists():
                    try:
                        model_path = model_path_keras
                        model_format = "keras_native"
                        logger.info("Attempting native .keras load for sequence model: %s", model_path)
                        model = self._load_artifact(model_path, expected_kind="keras")
                    except Exception as exc:
                        repair_reason = str(exc)
                        msg = str(exc).lower()
                        # Detect likely incompatibility and move to archive to avoid repeated noisy failures
                        incompat_keys = ("unrecognized keyword arguments", "inputlayer", "batch_shape", "optional")
                        if any(k in msg for k in incompat_keys):
                            try:
                                archive_dir = self._models_dir / "archive"
                                archive_dir.mkdir(parents=True, exist_ok=True)
                                target = archive_dir / model_path_keras.name
                                model_path_keras.replace(target)
                                logger.warning("Skipped incompatible sequence artifact: %s -> %s", model_path_keras.name, target)
                                self._status["sequence_model"] = {"state": "incompatible", "path": str(target)}
                            except Exception as mv_exc:
                                logger.debug("Failed to archive incompatible .keras: %s", mv_exc)
                        else:
                            logger.warning("Native .keras load failed; attempting legacy H5 recovery: %s", exc)

                if model is None:
                    raise FileNotFoundError(f"No sequence model found (tried {model_path_keras} and {model_path_h5})")

                scaler = self._load_artifact(scaler_path, expected_kind="pickle_or_joblib")
                metadata = self._load_artifact(metadata_path, expected_kind="pickle_or_joblib")

                if not hasattr(model, "predict"):
                    raise ModelValidationError("Sequence model missing predict")
                if not hasattr(scaler, "transform"):
                    raise ModelValidationError("Sequence scaler missing transform")
                if not isinstance(metadata, dict):
                    raise ModelValidationError("Sequence metadata is not a dict")

                self._loaded["sequence_model"] = model
                self._loaded["sequence_scaler"] = scaler
                self._loaded["sequence_metadata"] = metadata
                self._status["sequence_model"] = {
                    "state": "healthy",
                    "path": str(model_path),
                    "format": model_format,
                    "input_shape": str(model.input_shape) if hasattr(model, "input_shape") else "unknown",
                    "repair_reason": repair_reason,
                }
                self._status["sequence_scaler"] = {"state": "healthy", "path": str(scaler_path)}
                self._status["sequence_metadata"] = {"state": "healthy", "path": str(metadata_path)}
                
                logger.info(
                    "Sequence Model Loaded: format=%s, input_shape=%s",
                    model_format,
                    model.input_shape if hasattr(model, "input_shape") else "unknown",
                )
            except Exception as exc:
                logger.exception("Sequence model bundle failed to load")
                self._loaded["sequence_model"] = None
                self._loaded["sequence_scaler"] = None
                self._loaded["sequence_metadata"] = {}
                self._status["sequence_model"] = {
                    "state": "failed",
                    "reason": str(exc),
                    "path": str(model_path_keras if model_path_keras.exists() else model_path_h5),
                    "versions": self._runtime_versions(),
                }
                self._status["sequence_scaler"] = {"state": "failed", "reason": str(exc), "path": str(scaler_path)}
                self._status["sequence_metadata"] = {"state": "failed", "reason": str(exc), "path": str(metadata_path)}

        return (
            self._loaded.get("sequence_model"),
            self._loaded.get("sequence_scaler"),
            self._loaded.get("sequence_metadata"),
        )

    def get_graph_model(self) -> Tuple[Any, Any, Any, Any]:
        if "graph_engine" not in self._loaded:
            graph_health = self._neo4j_client.health_check()
            graph_state = "healthy" if graph_health.get("connected") else "degraded"
            self._loaded["graph_engine"] = self._neo4j_client
            self._status["graph_engine"] = {
                "state": graph_state,
                "uri": graph_health.get("uri"),
                "reason": graph_health.get("reason"),
            }
            self._status["graph_model"] = self._status["graph_engine"]

        return (
            self._loaded.get("graph_engine"),
            self._status.get("graph_engine", {}),
            None,
            None,
        )

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------
    def _runtime_versions(self) -> Dict[str, str]:
        version_names = ["tensorflow", "keras", "scikit-learn", "lightgbm", "numpy", "pandas", "protobuf"]
        versions: Dict[str, str] = {}
        for name in version_names:
            try:
                versions[name] = importlib_metadata.version(name)
            except Exception:
                versions[name] = "unknown"
        return versions

    def validate_all(self) -> Dict[str, Any]:
        behavioral_model, behavioral_scaler, behavioral_features = self.get_behavioral_model()
        sequence_model, sequence_scaler, sequence_metadata = self.get_sequence_model()
        graph_engine, graph_health, graph_index, graph_metadata = self.get_graph_model()

        sequence_self_test = self._run_sequence_self_test(sequence_model, sequence_scaler, sequence_metadata)

        runtime_mode = "FULL"
        bundle_states = {
            "behavioral_model": self._status.get("behavioral_model", {}).get("state", "unknown"),
            "behavioral_scaler": self._status.get("behavioral_scaler", {}).get("state", "unknown"),
            "behavioral_features": self._status.get("behavioral_features", {}).get("state", "unknown"),
            "sequence_model": self._status.get("sequence_model", {}).get("state", "unknown"),
            "sequence_scaler": self._status.get("sequence_scaler", {}).get("state", "unknown"),
            "sequence_metadata": self._status.get("sequence_metadata", {}).get("state", "unknown"),
            "graph_engine": self._status.get("graph_engine", {}).get("state", "unknown"),
        }
        if any(state != "healthy" for state in bundle_states.values()):
            runtime_mode = "DEGRADED"
        if sequence_self_test.get("state") != "healthy":
            runtime_mode = "DEGRADED"

        self._health_snapshot = {
            "behavioral_model": self._status.get("behavioral_model", {}).get("state", "failed"),
            "sequence_model": self._status.get("sequence_model", {}).get("state", "failed"),
            "graph_model": self._status.get("graph_engine", {}).get("state", "failed"),
            "graph_engine": self._status.get("graph_engine", {}).get("state", "failed"),
            "scalers": "healthy" if self._status.get("behavioral_scaler", {}).get("state") == "healthy" and self._status.get("sequence_scaler", {}).get("state") == "healthy" else "failed",
            "encoders": "healthy" if self._status.get("behavioral_features", {}).get("state") == "healthy" else "failed",
            "runtime_mode": runtime_mode,
            "sequence_self_test": sequence_self_test,
            "versions": self._runtime_versions(),
            "artifacts": {
                **self._status,
                "behavioral_model_type": type(behavioral_model).__name__ if behavioral_model is not None else None,
                "sequence_model_type": type(sequence_model).__name__ if sequence_model is not None else None,
                "graph_engine_type": type(graph_engine).__name__ if graph_engine is not None else None,
                "behavioral_scaler_type": type(behavioral_scaler).__name__ if behavioral_scaler is not None else None,
                "sequence_scaler_type": type(sequence_scaler).__name__ if sequence_scaler is not None else None,
                "graph_engine_health": graph_health,
                "sequence_metadata_type": type(sequence_metadata).__name__ if sequence_metadata is not None else None,
                "behavioral_features_type": type(behavioral_features).__name__ if behavioral_features is not None else None,
            },
        }
        return self._health_snapshot

    def get_health_snapshot(self) -> Dict[str, Any]:
        if not self._health_snapshot:
            return self.validate_all()
        return self._health_snapshot

    def initialize_runtime(self) -> Dict[str, Any]:
        snapshot = self.validate_all()
        self._log_startup_report(snapshot)
        return snapshot

    def _log_startup_report(self, snapshot: Dict[str, Any]) -> None:
        logger.info("Model runtime mode: %s", snapshot.get("runtime_mode"))
        for key in ("behavioral_model", "sequence_model", "graph_engine", "scalers", "encoders"):
            logger.info("%s=%s", key, snapshot.get(key))
        versions = snapshot.get("versions", {})
        logger.info("runtime_versions=%s", versions)
        logger.info("sequence_self_test=%s", snapshot.get("sequence_self_test"))

    def _run_sequence_self_test(self, model: Any, scaler: Any, metadata: Any) -> Dict[str, Any]:
        if model is None or scaler is None or not isinstance(metadata, dict):
            return {"state": "failed", "reason": "missing_sequence_artifacts"}

        try:
            import tensorflow as tf
            import pandas as pd
            from app.core.feature_schema import SEQUENCE_FEATURES

            seq_len = int(metadata.get("sequence_length", 10))
            features = metadata.get("features") or SEQUENCE_FEATURES
            frame = pd.DataFrame([[1.0] * len(features) for _ in range(seq_len)], columns=list(features))
            scaled = scaler.transform(frame)
            tensor = np.expand_dims(scaled[-seq_len:], axis=0)
            prediction = model.predict(tensor, verbose=0)
            value = float(prediction[0][0])
            return {"state": "healthy", "shape": list(tensor.shape), "prediction": round(value, 6)}
        except Exception as exc:
            logger.exception("Sequence self-test failed")
            return {"state": "failed", "reason": str(exc)}


_SINGLETON: Optional[ModelLoader] = None


def get_model_loader() -> ModelLoader:
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = ModelLoader()
    return _SINGLETON


def behavioral_model() -> Tuple[Any, Any, Any]:
    return get_model_loader().get_behavioral_model()


def sequence_model() -> Tuple[Any, Any, Any]:
    return get_model_loader().get_sequence_model()


def graph_model() -> Tuple[Any, Any, Any, Any]:
    return get_model_loader().get_graph_model()


def get_model_health() -> Dict[str, Any]:
    return get_model_loader().get_health_snapshot()


def initialize_model_runtime() -> Dict[str, Any]:
    return get_model_loader().initialize_runtime()
