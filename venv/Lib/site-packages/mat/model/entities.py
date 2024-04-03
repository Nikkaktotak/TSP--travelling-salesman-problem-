from enum import Enum


class MigrationStatus(Enum):
    PENDING = "Pending"
    APPLIED = "Applied"
    ERROR = "Error"
    REVERTED = "Reverted"


class Migration:
    def __init__(
            self,
            db_id=None,
            version=None,
            name=None,
            status=None,
            status_update=None,
            file_path=None,
            rollback_file_path=None):
        """
        Represents each migration and its status

        :param db_id: Id will be provided by database
        :param version: Parsed version number from file name
        :param name: Name parsed from file name
        :param status: Status of migration
        :param status_update: Timestamps when the status was updated
        :param file_path: Absolute file path to script file
        :param rollback_file_path: Absolute file path to rollback script file
        """

        self.db_id = db_id
        self.version = version
        self.name = name
        self.status = status
        self.status_update = status_update
        self.file_path = file_path
        self.rollback_file_path = rollback_file_path

    @staticmethod
    def from_row(row):
        return Migration(
            db_id = row[0],
            version = row[1],
            name = row[2],
            status = MigrationStatus(row[3]),
            status_update = row[4],
            file_path = row[5],
            rollback_file_path = row[6]
        )

    def as_row(self, include_id=False, include_paths=False):
        row = []

        if include_id:
            row.append(self.db_id)

        row.extend([
            self.version,
            self.name,
            self.status.value,
            self.status_update
        ])

        if include_paths:
            row.append(self.file_path)
            row.append(self.rollback_file_path)

        return row
