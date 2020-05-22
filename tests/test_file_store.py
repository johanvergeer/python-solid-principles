from pathlib import Path
from unittest.mock import Mock, patch

import structlog
from structlog.testing import LogCapture

import pytest
from faker import Faker

from python_solid_principles.file_store import (
    MessageStore,
    StoreCache,
    StoreLogger,
    _read_message,
)


@pytest.fixture
def faker():
    return Faker()


@pytest.fixture
def message_id(faker):
    return faker.random_number()


@pytest.fixture
def message(faker):
    return faker.text()


@pytest.fixture
def log_output():
    return LogCapture()


@pytest.fixture(autouse=True)
def configure_structlog(log_output):
    structlog.configure(processors=[log_output])


@pytest.fixture
def working_dir(tmpdir):
    return tmpdir


@pytest.fixture
def message_store(working_dir):
    return MessageStore(working_dir)


class TestMessageStore:
    def test_init__working_dir_does_not_exist(self, tmp_path):
        working_dir = Path("/non_existing_path")

        # path_mock.exists.return_value = False
        # path_mock.resolve.return_value = Path("non_existing_path")

        with pytest.raises(FileNotFoundError) as err:
            MessageStore(working_dir)

        assert "working_directory '/non_existing_path' does not exist" in str(err.value)

    def test_init__working_directory_set(self, tmpdir):
        # GIVEN an existing working directory
        working_dir = tmpdir

        # WHEN creating a MessageStore instance
        fs = MessageStore(working_dir)

        # THEN working_directory should be set
        assert fs.working_directory == working_dir

    def test_get_file_path(self, message_store, working_dir, message_id):
        # GIVEN a FileStorage instance
        # AND a message id

        # WHEN getting the file path
        file_path = message_store.get_file_path(message_id)

        # THEN the file info should contain the file path
        assert file_path == working_dir / f"{message_id}.txt"

    @patch("python_solid_principles.file_store.StoreCache.add_or_update")
    @patch("python_solid_principles.file_store.StoreLogger.log_saving_message")
    @patch("python_solid_principles.file_store.StoreLogger.log_saved_message")
    def test_save__file_save(
        self,
        log_saved_entries_mock,
        log_saving_message_mock,
        add_or_update_mock,
        message_store,
        message_id,
        working_dir,
        log_output,
        message,
    ):
        # GIVEN a file storage
        # AND a message id
        # AND a message

        # WHEN saving the message
        message_store.save(message_id, message)

        # THEN the message file should be created
        file_path = message_store.get_file_path(message_id)
        assert file_path.exists()

        # AND the message file should contain the message
        with file_path.open("r") as message_file:
            assert message_file.read() == message

        # AND log entries are created
        log_saving_message_mock.assert_called_once()
        log_saved_entries_mock.assert_called_once()

        # AND the message is added to the cache
        add_or_update_mock.assert_called_with(message_id, message)

    @patch("python_solid_principles.file_store.StoreCache.get_or_add")
    @patch("python_solid_principles.file_store.StoreLogger.log_reading_message")
    @patch("python_solid_principles.file_store.StoreLogger.log_message_not_found")
    def test_read__message_file_does_not_exist(
        self,
        log_message_not_found_mock,
        log_reading_message_mock,
        get_or_add_mock,
        message_store,
        log_output,
        message_id,
    ):
        # GIVEN a file storage
        # AND the file to read does not exist

        # WHEN trying to read the file
        message = message_store.read(message_id)

        # THEN the message is None
        assert message is None

        # AND two log entries are created
        log_reading_message_mock.assert_called_once_with(message_id)
        log_message_not_found_mock.assert_called_once_with(message_id)

        # AND the cache is not called
        get_or_add_mock.assert_not_called()

    @patch("python_solid_principles.file_store.StoreCache.get_or_add")
    @patch("python_solid_principles.file_store.StoreLogger.log_reading_message")
    @patch("python_solid_principles.file_store.StoreLogger.log_returning_message")
    def test_read__file_read(
        self,
        log_returning_message_mock,
        log_reading_message_mock,
        get_or_add_mock,
        message_store,
        message_id,
        working_dir,
        log_output,
        message,
    ):
        # GIVEN a file storage
        # AND a message id
        # AND a file containing a message
        file_path = message_store.get_file_path(message_id)
        with file_path.open("w") as message_file:
            message_file.write(message)

        get_or_add_mock.return_value = message

        # WHEN reading the file through FileStorage
        message_read = message_store.read(message_id)

        # THEN the message should have been read
        assert message_read == message

        # AND two log entries are created
        log_reading_message_mock.assert_called_once_with(message_id)
        log_returning_message_mock.assert_called_once_with(message_id, message)

        # AND the value is retrieved from the cache
        get_or_add_mock.assert_called_once()


class TestStoreLogger:
    @pytest.fixture
    def store_logger(self):
        return StoreLogger()

    def test_log_saving_message(self, log_output, message_id, message, store_logger):
        store_logger.log_saving_message(message_id, message)

        assert log_output.entries == [
            {
                "event": "saving_message",
                "log_level": "info",
                "message": message,
                "message_id": message_id,
            },
        ]

    def test_log_saved_message(self, log_output, message_id, store_logger):
        store_logger.log_saved_message(message_id)

        assert log_output.entries == [
            {"event": "saved_message", "log_level": "info", "message_id": message_id},
        ]

    def test_log_reading_message(self, log_output, message_id, store_logger):
        store_logger.log_reading_message(message_id)

        assert log_output.entries == [
            {"event": "reading_message", "log_level": "info", "message_id": message_id},
        ]

    def test_log_message_not_found(self, log_output, message_id, store_logger):
        store_logger.log_message_not_found(message_id)

        assert log_output.entries == [
            {
                "event": "message_not_found",
                "log_level": "info",
                "message_id": message_id,
            },
        ]

    def test_log_returning_message(self, log_output, message_id, message, store_logger):
        store_logger.log_returning_message(message_id, message)

        assert log_output.entries == [
            {
                "event": "returning_message",
                "log_level": "info",
                "message_id": message_id,
                "message": message,
            },
        ]


class TestStoreCache:
    @pytest.fixture
    def cache(self) -> StoreCache:
        return StoreCache()

    def test_init(self, cache):
        assert cache is not None

    def test_add_or_update__new(self, cache, message_id, message):
        cache.add_or_update(message_id, message)

        assert cache._cache[message_id] == message

    def test_add_or_update__update(self, cache, message_id, message, faker):
        # GIVEN an initial value is set for a message_id
        cache.add_or_update(message_id, message)

        # AND a new message
        new_message = faker.text()

        # WHEN the new message is set for the message_id
        cache.add_or_update(message_id, new_message)

        # THEN the cache message for the message_id should be changed
        assert cache._cache[message_id] == new_message

    def test_get_or_add__add(self, cache, message_id, message):
        # GIVEN the cache is empty
        assert len(cache._cache) == 0

        read_message_mock = Mock(obj=_read_message, return_value=message)
        message_file = Path()

        # WHEN a message is added with the message_id
        found_message = cache.get_or_add(message_id, message_file, read_message_mock)

        # THEN the message is read from the file
        read_message_mock.assert_called_once_with(message_file)
        assert found_message == message
        # AND the message is added with the message_id
        assert cache._cache[message_id] == message

    def test_get_or_add__get(self, cache, message_id, message):
        # GIVEN the message is added with the message_id
        cache._cache[message_id] = message
        # AND a message file
        message_file = Path()

        # AND a function to get the message from the file when it's not in the cache yet
        read_message_mock = Mock(obj=_read_message, return_value=message)

        # WHEN the message is requested from the cache
        found_message = cache.get_or_add(message_id, message_file, read_message_mock)

        # THEN the message is found
        assert found_message == message
        # AND the file is not read because the cache is used
        read_message_mock.assert_not_called()
