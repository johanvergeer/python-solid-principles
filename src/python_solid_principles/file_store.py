from pathlib import Path
from typing import Callable, Optional

import structlog

log = structlog.getLogger()


def _read_message(file_path: Path) -> str:
    with file_path.open("r") as message_file:
        return message_file.read()


class FileStore:
    def __init__(self, working_directory: Path):
        if not working_directory.exists():
            raise FileNotFoundError(
                f"working_directory '{working_directory.resolve()}' does not exist",
            )

        self.__working_directory = working_directory
        self.__logger = StoreLogger()
        self.__cache = StoreCache()

    @property
    def working_directory(self) -> Path:
        return self.__working_directory

    def save(self, message_id: int, message: str) -> None:
        self.__logger.log_saving_message(message_id, message)

        file_path = self.get_file_path(message_id)
        with file_path.open("w") as message_file:
            message_file.write(message)

        self.__cache.add_or_update(message_id, message)
        self.__logger.log_saved_message(message_id)

    def read(self, message_id: int) -> Optional[str]:
        self.__logger.log_reading_message(message_id)
        file_path = self.get_file_path(message_id)

        if not file_path.exists():
            self.__logger.log_message_not_found(message_id)
            return None

        msg = self.__cache.get_or_add(message_id, file_path, _read_message)
        self.__logger.log_returning_message(message_id, msg)

        return msg

    def get_file_path(self, message_id: int) -> Path:
        return self.__working_directory / f"{message_id}.txt"


class StoreLogger:
    def log_saving_message(self, message_id: int, message: str) -> None:
        log.info("saving_message", message_id=message_id, message=message)

    def log_saved_message(self, message_id: int) -> None:
        log.info("saved_message", message_id=message_id)

    def log_reading_message(self, message_id: int) -> None:
        log.info("reading_message", message_id=message_id)

    def log_message_not_found(self, message_id: int) -> None:
        log.info("message_not_found", message_id=message_id)

    def log_returning_message(self, message_id: int, message: str) -> None:
        log.info("returning_message", message_id=message_id, message=message)


class StoreCache:
    def __init__(self):
        self._cache = {}

    def add_or_update(self, message_id: int, message: str) -> None:
        self._cache[message_id] = message

    def get_or_add(
        self, message_id: int, message_file: Path, message_reader: Callable[[Path], str]
    ) -> str:
        if message := self._cache.get(message_id):
            return message

        message = message_reader(message_file)
        self._cache[message_id] = message

        return message
