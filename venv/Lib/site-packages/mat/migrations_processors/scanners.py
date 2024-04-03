import abc
import os

from mat.config_loader import ConfigLoader


class ScriptMetadata:
    def __init__(self, version, name, file_path, rollback_file_path):
        self.version = version
        self.name = name
        self.file_path = file_path
        self.rollback_file_path = rollback_file_path


class AbstractScanner(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
                hasattr(subclass, 'scan') and
                callable(subclass.scan) and
                hasattr(subclass, '_parse_name') and
                callable(subclass._parse_name) and
                hasattr(subclass, '_find_rollback') and
                callable(subclass._find_rollback) and
                hasattr(subclass, 'get_commands') and
                callable(subclass.get_commands) or
                NotImplemented
        )

    def __init__(self, conf_loader):
        """
        Initializes migrations scanner

        :param conf_loader:
        :type conf_loader: ConfigLoader
        """
        path_conf = conf_loader.get_migrations_path()
        self.up_path = path_conf['up']
        self.down_path = path_conf['down']

    def scan(self):
        """
        Scans for migrations and rollbacks in up and down paths and parses
        metadata from file names. Scanned migrations are returned as a list
        of ScriptMetadata instances
        :return: Scanned scripts
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _parse_name(self, file):
        """
        Parses file name and retrieves migration version and name

        :param file: File name
        :type file: str
        :return: Tuple with (version, name) for file
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _find_rollback(self, version):
        """
        Looks for rollback script for provided migration version
        :param version: Version to look for
        :type version: str
        :return: absolute path to rollback script
        """
        raise NotImplementedError

    @abc.abstractmethod
    def get_commands(self, abspath):
        """
        Parses provided sql file and returns a list of sql commands
        :param abspath: SQL File to parse
        :type abspath: str
        :return:
        """
        raise NotImplementedError


class FileScanner(AbstractScanner):

    def scan(self):
        files = os.listdir(self.up_path)
        files_metadata = []

        for file in files:
            version, name = self._parse_name(file)
            file_path = os.path.abspath(os.path.join(self.up_path, file))
            rollback_file_path = self._find_rollback(version)

            files_metadata.append(ScriptMetadata(
                version,
                name,
                file_path,
                rollback_file_path
            ))

        return files_metadata

    def _parse_name(self, file):
        migration_parts = os.path.splitext(file)[0].split("_", 1)
        version = migration_parts[0]
        name = migration_parts[1] \
            .replace("_", " ") \
            .capitalize()

        return version, name

    def _find_rollback(self, version):
        files = os.listdir(self.down_path)
        for file in files:
            file_version, _ = self._parse_name(file)
            if file_version == version:
                return os.path.abspath(os.path.join(self.down_path, file))

        # TODO: Raise custom exception for rollback not found
        return None

    def get_commands(self, abspath):
        with open(abspath, 'r') as file:
            sql = file.read()
            commands = sql.split(";")

        return commands
