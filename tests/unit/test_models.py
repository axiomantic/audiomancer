"""Tests for ML model management."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from audiomancer.analyzers.models import (
    get_model_dir,
    get_model_path,
    verify_model_checksum,
    download_model,
    load_model,
    list_models,
    clear_cache,
)
from audiomancer.errors import ModelLoadError


class TestModelPaths:
    """Test model path utilities."""

    def test_get_model_dir(self):
        """Test model directory path."""
        model_dir = get_model_dir()
        assert model_dir.is_dir()
        assert model_dir.name == "models"
        assert "audiomancer" in str(model_dir)

    def test_get_model_path(self):
        """Test model file path generation."""
        path = get_model_path("musicnn")
        assert path.name == "musicnn.pb"
        assert "models" in str(path)


class TestModelVerification:
    """Test model checksum verification."""

    def test_verify_checksum_valid(self, tmp_path):
        """Test checksum verification with valid file."""
        # Create test file
        test_file = tmp_path / "test.pb"
        test_content = b"test model data"
        test_file.write_bytes(test_content)

        # Compute expected hash
        import hashlib
        expected_hash = hashlib.sha256(test_content).hexdigest()

        # Verify
        assert verify_model_checksum(test_file, expected_hash) is True

    def test_verify_checksum_invalid(self, tmp_path):
        """Test checksum verification with mismatched hash."""
        # Create test file
        test_file = tmp_path / "test.pb"
        test_file.write_bytes(b"test model data")

        # Use wrong hash
        wrong_hash = "0" * 64

        # Verify
        assert verify_model_checksum(test_file, wrong_hash) is False

    def test_verify_checksum_missing_file(self, tmp_path):
        """Test checksum verification with missing file."""
        missing_file = tmp_path / "missing.pb"
        # Use valid SHA256 format (64 hex chars) to avoid placeholder logic
        valid_sha256 = "a" * 64
        assert verify_model_checksum(missing_file, valid_sha256) is False


class TestModelDownload:
    """Test model downloading."""

    @patch("urllib.request.urlretrieve")
    def test_download_model_success(self, mock_retrieve, tmp_path, monkeypatch):
        """Test successful model download."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Mock checksum verification
        monkeypatch.setattr(
            "audiomancer.analyzers.models.verify_model_checksum",
            lambda path, expected: True
        )

        # Download model
        result = download_model("musicnn", verify_checksum=True)

        # Verify download was called
        assert mock_retrieve.called
        assert result.name == "musicnn.pb"

    def test_download_model_invalid_type(self):
        """Test download with invalid model type."""
        with pytest.raises(ModelLoadError) as exc_info:
            download_model("nonexistent_model")

        assert "Unknown model type" in str(exc_info.value)
        assert "nonexistent_model" in exc_info.value.details["model_type"]

    @patch("urllib.request.urlretrieve")
    def test_download_model_checksum_failure(self, mock_retrieve, tmp_path, monkeypatch):
        """Test download with checksum verification failure."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Create a dummy file that will fail verification
        model_path = tmp_path / "musicnn.pb"
        mock_retrieve.side_effect = lambda url, path: model_path.write_bytes(b"fake model")

        # Mock checksum to fail
        monkeypatch.setattr(
            "audiomancer.analyzers.models.verify_model_checksum",
            lambda path, expected: False
        )

        # Should raise error on checksum mismatch
        with pytest.raises(ModelLoadError) as exc_info:
            download_model("musicnn", verify_checksum=True)

        assert "checksum verification" in str(exc_info.value).lower()

    @patch("urllib.request.urlretrieve")
    def test_download_model_force_redownload(self, mock_retrieve, tmp_path, monkeypatch):
        """Test forced re-download of existing model."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Create existing model file
        model_path = tmp_path / "musicnn.pb"
        model_path.write_bytes(b"existing model")

        # Mock checksum
        monkeypatch.setattr(
            "audiomancer.analyzers.models.verify_model_checksum",
            lambda path, expected: True
        )

        # Download with force=True
        result = download_model("musicnn", force=True, verify_checksum=True)

        # Should have downloaded even though file exists
        assert mock_retrieve.called
        assert result == model_path


class TestModelLoading:
    """Test model loading."""

    def test_load_model_existing(self, tmp_path, monkeypatch):
        """Test loading existing model."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Create model file
        model_path = tmp_path / "musicnn.pb"
        model_path.write_bytes(b"model data")

        # Load model
        result = load_model("musicnn", auto_download=False)
        assert result == model_path

    def test_load_model_missing_no_download(self, tmp_path, monkeypatch):
        """Test loading missing model without auto-download."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Should raise error
        with pytest.raises(ModelLoadError) as exc_info:
            load_model("musicnn", auto_download=False)

        assert "not found" in str(exc_info.value).lower()
        assert "musicnn" in exc_info.value.details["model_type"]

    @patch("audiomancer.analyzers.models.download_model")
    def test_load_model_auto_download(self, mock_download, tmp_path, monkeypatch):
        """Test loading with auto-download."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Mock download to create file
        model_path = tmp_path / "musicnn.pb"
        mock_download.return_value = model_path

        # Load with auto-download
        result = load_model("musicnn", auto_download=True)

        # Should have called download
        assert mock_download.called
        mock_download.assert_called_once_with("musicnn")


class TestModelListing:
    """Test model listing."""

    def test_list_models_empty_cache(self, tmp_path, monkeypatch):
        """Test listing models with empty cache."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # List all models
        models = list_models(include_cached_only=False)

        # Should include all registry entries
        assert "musicnn" in models
        assert "vggish" in models
        assert "mtg_jamendo_instrument" in models

        # All should be marked as not cached
        for model_info in models.values():
            assert model_info["cached"] is False
            assert model_info["path"] is None

    def test_list_models_with_cache(self, tmp_path, monkeypatch):
        """Test listing models with some cached."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Create cached model
        cached_model = tmp_path / "musicnn.pb"
        cached_model.write_bytes(b"cached model")

        # List models
        models = list_models(include_cached_only=False)

        # musicnn should be cached
        assert models["musicnn"]["cached"] is True
        assert models["musicnn"]["path"] == str(cached_model)

        # Others should not be cached
        assert models["vggish"]["cached"] is False

    def test_list_models_cached_only(self, tmp_path, monkeypatch):
        """Test listing only cached models."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Create cached model
        cached_model = tmp_path / "musicnn.pb"
        cached_model.write_bytes(b"cached model")

        # List cached only
        models = list_models(include_cached_only=True)

        # Should only include musicnn
        assert "musicnn" in models
        assert "vggish" not in models


class TestCacheClear:
    """Test cache clearing."""

    def test_clear_specific_model(self, tmp_path, monkeypatch):
        """Test clearing specific model from cache."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Create multiple cached models
        model1 = tmp_path / "musicnn.pb"
        model2 = tmp_path / "vggish.pb"
        model1.write_bytes(b"model1")
        model2.write_bytes(b"model2")

        # Clear specific model
        clear_cache("musicnn")

        # musicnn should be deleted
        assert not model1.exists()

        # vggish should still exist
        assert model2.exists()

    def test_clear_all_models(self, tmp_path, monkeypatch):
        """Test clearing all models from cache."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Create multiple cached models
        model1 = tmp_path / "musicnn.pb"
        model2 = tmp_path / "vggish.pb"
        model1.write_bytes(b"model1")
        model2.write_bytes(b"model2")

        # Clear all
        clear_cache()

        # Both should be deleted
        assert not model1.exists()
        assert not model2.exists()

    def test_clear_nonexistent_model(self, tmp_path, monkeypatch):
        """Test clearing model that doesn't exist (should not error)."""
        # Mock model directory
        monkeypatch.setattr(
            "audiomancer.analyzers.models.get_model_dir",
            lambda: tmp_path
        )

        # Should not raise error
        clear_cache("musicnn")
