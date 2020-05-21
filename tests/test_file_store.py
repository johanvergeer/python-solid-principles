from pathlib import Path

import structlog
from structlog.testing import LogCapture

import pytest
from faker import Faker

from python_solid_principles.file_store import FileStore


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
def file_storage(working_dir):
    return FileStore(working_dir)


class TestFileStore:
    def test_init__working_dir_does_not_exist(self, tmp_path):
        working_dir = Path("/non_existing_path")

        # path_mock.exists.return_value = False
        # path_mock.resolve.return_value = Path("non_existing_path")

        with pytest.raises(FileNotFoundError) as err:
            FileStore(working_dir)

        assert "working_directory '/non_existing_path' does not exist" in str(err.value)

    def test_init__working_directory_set(self, tmpdir):
        # GIVEN an existing working directory
        working_dir = tmpdir

        # WHEN creating a FileStore instance
        fs = FileStore(working_dir)

        # THEN working_directory should be set
        assert fs.working_directory == working_dir

    def test_get_file_path(self, file_storage, working_dir, message_id):
        # GIVEN a FileStorage instance
        # AND a message id

        # WHEN getting the file path
        file_path = file_storage.get_file_path(message_id)

        # THEN the file info should contain the file path
        assert file_path == working_dir / f"{message_id}.txt"

    def test_save__file_save(
        self, file_storage, message_id, working_dir, log_output, message
    ):
        # GIVEN a file storage
        # AND a message id
        # AND a message

        # WHEN saving the message
        file_storage.save(message_id, message)

        # THEN the message file should be created
        file_path = file_storage.get_file_path(message_id)
        assert file_path.exists()

        # AND the message file should contain the message
        with file_path.open("r") as message_file:
            assert message_file.read() == message

        # AND log entries are created
        assert log_output.entries == [
            {
                "event": "saving_message",
                "log_level": "info",
                "message": message,
                "message_id": message_id,
            },
            {"event": "saved_message", "log_level": "info", "message_id": message_id},
        ]

    def test_read__message_file_does_not_exist(self, file_storage, log_output):
        # GIVEN a file storage
        # AND the file to read does not exist

        # WHEN trying to read the file
        message = file_storage.read(1)

        # THEN the message is None
        assert message is None

        # AND two log entries are created
        assert log_output.entries == [
            {"event": "reading_message", "log_level": "info", "message_id": 1},
            {"event": "message_not_found", "log_level": "info", "message_id": 1},
        ]

    def test_read__file_read(
        self, file_storage, message_id, working_dir, log_output, message
    ):
        # GIVEN a file storage
        # AND a message id
        # AND a file containing a message
        file_path = file_storage.get_file_path(message_id)
        with file_path.open("w") as message_file:
            message_file.write(message)

        # WHEN reading the file through FileStorage
        message_read = file_storage.read(message_id)

        # THEN the message should have been read
        assert message_read == message

        # AND two log entries are created
        assert log_output.entries == [
            {"event": "reading_message", "log_level": "info", "message_id": message_id},
            {
                "event": "returning_message",
                "log_level": "info",
                "message_id": message_id,
                "message": message,
            },
        ]
