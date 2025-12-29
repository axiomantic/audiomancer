"""Tests for error classes."""
import pytest
from audiomancer.errors import (
    AudiomancerError,
    ConfigError,
    StorageError,
    SampleNotFoundError,
    DuplicateSampleError,
)


class TestAudiomancerError:
    """Tests for base error class."""

    def test_error_has_message(self):
        """Error should store message."""
        error = AudiomancerError("test message")
        assert str(error) == "test message"

    def test_error_has_details(self):
        """Error should store details dict."""
        error = AudiomancerError("test", {"key": "value"})
        assert error.details == {"key": "value"}

    def test_error_without_details(self):
        """Error should work without details."""
        error = AudiomancerError("test message")
        assert error.details == {}

    def test_error_to_dict(self):
        """Error should serialize to dict."""
        error = AudiomancerError("test message", {"key": "value"})
        result = error.to_dict()
        assert result["message"] == "test message"
        assert result["details"]["key"] == "value"
        assert result["type"] == "AudiomancerError"

    def test_error_to_dict_without_details(self):
        """Error should serialize to dict even without details."""
        error = AudiomancerError("test message")
        result = error.to_dict()
        assert result["message"] == "test message"
        assert result["details"] == {}
        assert result["type"] == "AudiomancerError"

    def test_error_is_exception(self):
        """Error should be a proper exception."""
        error = AudiomancerError("test")
        assert isinstance(error, Exception)

    def test_error_can_be_raised(self):
        """Error should be raisable."""
        with pytest.raises(AudiomancerError) as exc_info:
            raise AudiomancerError("test error")
        assert "test error" in str(exc_info.value)

    def test_error_preserves_details_in_to_dict(self):
        """Error to_dict should preserve nested details."""
        details = {
            "file_path": "/path/to/file.wav",
            "metadata": {
                "sample_rate": 44100,
                "channels": 2,
            },
            "tags": ["drum", "kick"],
        }
        error = AudiomancerError("test", details)
        result = error.to_dict()
        assert result["details"]["file_path"] == "/path/to/file.wav"
        assert result["details"]["metadata"]["sample_rate"] == 44100
        assert result["details"]["tags"] == ["drum", "kick"]


class TestConfigError:
    """Tests for ConfigError."""

    def test_config_error_is_audiomancer_error(self):
        """ConfigError should inherit from AudiomancerError."""
        error = ConfigError("test")
        assert isinstance(error, AudiomancerError)

    def test_config_error_type_in_dict(self):
        """ConfigError to_dict should have correct type."""
        error = ConfigError("test")
        result = error.to_dict()
        assert result["type"] == "ConfigError"

    def test_config_error_with_invalid_key(self):
        """ConfigError should include invalid key in details."""
        error = ConfigError(
            "Invalid configuration key",
            {"invalid_key": "logging.invalid_level"}
        )
        assert "invalid_key" in error.details


class TestStorageError:
    """Tests for StorageError."""

    def test_storage_error_is_audiomancer_error(self):
        """StorageError should inherit from AudiomancerError."""
        error = StorageError("test")
        assert isinstance(error, AudiomancerError)

    def test_storage_error_with_path(self):
        """StorageError should include path in details."""
        error = StorageError(
            "Database connection failed",
            {"db_path": "/path/to/db.sqlite"}
        )
        assert error.details["db_path"] == "/path/to/db.sqlite"


class TestSampleNotFoundError:
    """Tests for SampleNotFoundError."""

    def test_sample_not_found_is_storage_error(self):
        """SampleNotFoundError should inherit from StorageError."""
        error = SampleNotFoundError("abc123")
        assert isinstance(error, StorageError)
        assert isinstance(error, AudiomancerError)

    def test_sample_not_found_includes_id(self):
        """Error should include sample ID in details."""
        error = SampleNotFoundError("abc123")
        assert error.sample_id == "abc123"
        assert error.details["sample_id"] == "abc123"

    def test_sample_not_found_message_format(self):
        """Error message should include sample ID."""
        error = SampleNotFoundError("abc123")
        assert "abc123" in str(error)

    def test_sample_not_found_with_additional_details(self):
        """Error should accept additional details."""
        error = SampleNotFoundError(
            "abc123",
            {"search_path": "/path/to/samples"}
        )
        assert error.details["sample_id"] == "abc123"
        assert error.details["search_path"] == "/path/to/samples"


class TestDuplicateSampleError:
    """Tests for DuplicateSampleError."""

    def test_duplicate_sample_is_storage_error(self):
        """DuplicateSampleError should inherit from StorageError."""
        error = DuplicateSampleError("abc123", "/path/to/file.wav")
        assert isinstance(error, StorageError)
        assert isinstance(error, AudiomancerError)

    def test_includes_existing_id(self):
        """Error should include existing sample ID."""
        error = DuplicateSampleError("abc123", "/path/to/file.wav")
        assert error.existing_id == "abc123"
        assert "abc123" in error.details["existing_id"]

    def test_includes_file_path(self):
        """Error should include file path."""
        error = DuplicateSampleError("abc123", "/path/to/file.wav")
        assert error.file_path == "/path/to/file.wav"
        assert error.details["file_path"] == "/path/to/file.wav"

    def test_message_format(self):
        """Error message should include both ID and path."""
        error = DuplicateSampleError("abc123", "/path/to/file.wav")
        message = str(error)
        assert "abc123" in message
        assert "/path/to/file.wav" in message

    def test_with_additional_details(self):
        """Error should accept additional details."""
        error = DuplicateSampleError(
            "abc123",
            "/path/to/file.wav",
            {"original_path": "/original/file.wav"}
        )
        assert error.details["existing_id"] == "abc123"
        assert error.details["file_path"] == "/path/to/file.wav"
        assert error.details["original_path"] == "/original/file.wav"

    def test_to_dict_includes_all_fields(self):
        """to_dict should include all error fields."""
        error = DuplicateSampleError("abc123", "/path/to/file.wav")
        result = error.to_dict()
        assert result["type"] == "DuplicateSampleError"
        assert result["details"]["existing_id"] == "abc123"
        assert result["details"]["file_path"] == "/path/to/file.wav"


class TestErrorInheritanceHierarchy:
    """Tests for error inheritance hierarchy."""

    def test_all_errors_inherit_from_base(self):
        """All custom errors should inherit from AudiomancerError."""
        errors = [
            ConfigError("test"),
            StorageError("test"),
            SampleNotFoundError("test"),
            DuplicateSampleError("test", "/path"),
        ]
        for error in errors:
            assert isinstance(error, AudiomancerError)

    def test_storage_errors_inherit_from_storage_error(self):
        """Storage-related errors should inherit from StorageError."""
        errors = [
            SampleNotFoundError("test"),
            DuplicateSampleError("test", "/path"),
        ]
        for error in errors:
            assert isinstance(error, StorageError)

    def test_all_errors_are_exceptions(self):
        """All errors should be proper Python exceptions."""
        errors = [
            AudiomancerError("test"),
            ConfigError("test"),
            StorageError("test"),
            SampleNotFoundError("test"),
            DuplicateSampleError("test", "/path"),
        ]
        for error in errors:
            assert isinstance(error, Exception)


class TestErrorCatching:
    """Tests for catching errors in try/except blocks."""

    def test_catch_specific_error(self):
        """Specific error types should be catchable."""
        with pytest.raises(SampleNotFoundError):
            raise SampleNotFoundError("abc123")

    def test_catch_by_parent_class(self):
        """Errors should be catchable by parent class."""
        with pytest.raises(StorageError):
            raise SampleNotFoundError("abc123")

    def test_catch_by_base_class(self):
        """Errors should be catchable by base class."""
        with pytest.raises(AudiomancerError):
            raise DuplicateSampleError("abc123", "/path")

    def test_catch_as_generic_exception(self):
        """Errors should be catchable as generic Exception."""
        with pytest.raises(Exception):
            raise ConfigError("test")
