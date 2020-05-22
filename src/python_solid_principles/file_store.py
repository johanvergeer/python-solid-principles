from pathlib import Path
from typing import Callable, Optional

import structlog

log = structlog.getLogger()

UTF_8 = "utf-8"


class MessageStore:
    def __init__(self, working_directory: Path):
        if not working_directory.exists():
            raise FileNotFoundError(
                f"working_directory '{working_directory.resolve()}' does not exist",
            )

        self.__working_directory = working_directory
        self.__logger = StoreLogger()
        self.__cache = StoreCache()
        self.__store = FileStore()

    @property
    def working_directory(self) -> Path:
        return self.__working_directory

    def save(self, message_id: int, message: str) -> None:
        self.__logger.log_saving_message(message_id, message)

        file_path = self.__store.get_file_path(message_id, self.__working_directory)
        self.__store.write_all_text(file_path, message)

        self.__cache.add_or_update(message_id, message)
        self.__logger.log_saved_message(message_id)

    def read(self, message_id: int) -> Optional[str]:
        self.__logger.log_reading_message(message_id)
        file_path = self.__store.get_file_path(message_id, self.__working_directory)

        if not file_path.exists():
            self.__logger.log_message_not_found(message_id)
            return None

        msg = self.__cache.get_or_add(message_id, file_path, self.__store.read_all_text)
        self.__logger.log_returning_message(message_id, msg)

        return msg


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


class FileStore:
    def write_all_text(self, path: Path, message: str) -> None:
        path.write_text(message, encoding=UTF_8)

    def read_all_text(self, path: Path) -> str:
        return path.read_text(encoding=UTF_8)

    def get_file_path(self, message_id: int, working_dir: Path) -> Path:
        return working_dir / f"{message_id}.txt"
