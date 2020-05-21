from pathlib import Path
from typing import Optional

import structlog

log = structlog.getLogger(__name__)


class FileStore:
    def __init__(self, working_directory: Path):
        if not working_directory.exists():
            raise FileNotFoundError(
                f"working_directory '{working_directory.resolve()}' does not exist",
            )

        self.__working_directory = working_directory

    @property
    def working_directory(self) -> Path:
        return self.__working_directory

    def save(self, message_id: int, message: str) -> None:
        log.info("saving_message", message_id=message_id, message=message)

        file_path = self.get_file_path(message_id)
        with file_path.open("w") as message_file:
            message_file.write(message)

        log.info("saved_message", message_id=message_id)

    def read(self, message_id: int) -> Optional[str]:
        log.info("reading_message", message_id=message_id)
        file_info = self.get_file_path(message_id)

        if not file_info.exists():
            log.info("message_not_found", message_id=message_id)
            return None

        with file_info.open("r") as message_file:
            msg = message_file.read()
            log.info("returning_message", message_id=message_id, message=msg)

        return msg

    def get_file_path(self, message_id: int) -> Path:
        return self.__working_directory / f"{message_id}.txt"
