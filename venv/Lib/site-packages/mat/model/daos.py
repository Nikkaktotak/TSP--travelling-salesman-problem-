import abc
import mysql.connector

from datetime import datetime

from mat.config_loader import ConfigLoader
from mat.model.entities import Migration, MigrationStatus
from mat.migrations_processors.scanners import ScriptMetadata
from mat.log_utils import logger


class AbstractSchema(metaclass=abc.ABCMeta):
    TABLE = "migrations"
    COL_ID = "id"
    COL_VERSION = "version"
    COL_NAME = "name"
    COL_STATUS = "status"
    COL_STATUS_UPDATE = "status_update"
    COL_FILE_PATH = "file_path"
    COL_ROLLBACK_FILE_PATH = "rollback_file_path"

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, 'connect') and
            callable(subclass.connect) and
            hasattr(subclass, 'verify_table') and
            callable(subclass.verify_table) or
            NotImplemented
        )

    def __init__(self, config_loader):
        """
        Initializes the schema utils
        :param config_loader:
        :type config_loader: ConfigLoader
        """
        self.conf_loader = config_loader

    @abc.abstractmethod
    def connect(self):
        """
        Creates a connection to database, caller is responsible
        of closing connection and free resources when no more
        necessary
        :return: Database connection
        """
        raise NotImplementedError

    @abc.abstractmethod
    def verify_table(self):
        """
        Check if migrations table is already created and creates it
        in case of table not found
        """
        raise NotImplementedError


class MySQLSchema(AbstractSchema):

    def connect(self):
        connection = None

        try:
            datasource = self.conf_loader.get_datasource()

            connection = mysql.connector.connect(
                host=datasource['host'],
                user=datasource['username'],
                passwd=datasource['password'],
                database=datasource['database']
            )
        except mysql.connector.Error as e:
            logger.error("Error during connection: {}".format(e))

        return connection

    def verify_table(self):
        conn = self.connect()
        database_name = self.conf_loader.get_datasource()['database']

        # Check if table already exists
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = '{}'
              AND TABLE_NAME = '{}'
        """.format(database_name, AbstractSchema.TABLE))

        table_exists = cursor.fetchone()[0] == 1
        cursor.close()

        if not table_exists:
            try:
                cursor = conn.cursor()
                query = """
                    CREATE TABLE {} (
                        {} INTEGER PRIMARY KEY AUTO_INCREMENT,
                        {} VARCHAR(500) NOT NULL,
                        {} VARCHAR(1000) NOT NULL,
                        {} VARCHAR(255) NOT NULL,
                        {} DATETIME NOT NULL DEFAULT NOW(),
                        {} VARCHAR(3000) NOT NULL,
                        {} VARCHAR(3000) NOT NULL
                    )
                """

                cursor.execute(query.format(
                    AbstractSchema.TABLE,
                    AbstractSchema.COL_ID,
                    AbstractSchema.COL_VERSION,
                    AbstractSchema.COL_NAME,
                    AbstractSchema.COL_STATUS,
                    AbstractSchema.COL_STATUS_UPDATE,
                    AbstractSchema.COL_FILE_PATH,
                    AbstractSchema.COL_ROLLBACK_FILE_PATH
                ))
                cursor.close()
            except mysql.connector.Error as e:
                logger.error("table '{}' could not be created: {}".format(
                    AbstractSchema.TABLE,
                    e
                ))


class AbstractMigrationDao(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, 'destroy') and
            callable(subclass.destroy) and
            hasattr(subclass, 'save') and
            callable(subclass.save) and
            hasattr(subclass, 'find_all') and
            callable(subclass.find_all) and
            hasattr(subclass, 'find_all_applied') and
            callable(subclass.find_all_applied) and
            hasattr(subclass, 'find_all_non_applied') and
            callable(subclass.find_all_non_applied) and
            hasattr(subclass, 'find_by_version') and
            callable(subclass.find_by_version) or
            NotImplemented
        )

    def __init__(self, schema):
        """
        Initializes dao to be used
        :param schema: Database schema utils
        :type schema: AbstractSchema
        """
        self._conn = schema.connect()
        schema.verify_table()

    def upsert(self, metadata_list):
        """
        Updates or inserts a list  metadata files as migration objects

        :param metadata_list: Migration files to process
        :type metadata_list: list[ScriptMetadata]
        """
        for metadata in metadata_list:
            migration = self.find_by_version(metadata.version)

            if not migration:
                migration = Migration(
                    version=metadata.version,
                    status=MigrationStatus.PENDING,
                    status_update=datetime.now()
                )

            migration.name = metadata.name
            migration.file_path = metadata.file_path
            migration.rollback_file_path = metadata.rollback_file_path
            self.save(migration)

    @abc.abstractmethod
    def destroy(self):
        """
        Close db connections and free all unnecessary resources
        when dao is not anymore necessary. Note: User is responsible of
        invoke this method before finish execution
        """
        raise NotImplementedError

    @abc.abstractmethod
    def save(self, migration):
        """
        Persists (Inserts or update) migration into database, also migration
        object will be updated with right id in case of an insert

        :param migration: Entity to be persisted
        :type migration: Migration
        :return: The id of inserted/updated record
        """
        raise NotImplementedError

    @abc.abstractmethod
    def find_all(self):
        """
        Retrieves all migrations from db table ordered by version
        :return: Registered migrations
        """
        raise NotImplementedError

    @abc.abstractmethod
    def find_all_applied(self, desc=True):
        """
        Retrieves all applied migrations from database
        :param desc: If true, migrations will be in descending order by version
        :type desc: bool
        :return: list[Migration]
        """
        raise NotImplementedError

    @abc.abstractmethod
    def find_all_non_applied(self, desc=False):
        """
        Retrieves all migrations with status different of applied
        :param desc: If true, migrations will be in descending order by version
        :type desc: bool
        :return: list[Migration]
        """
        raise NotImplementedError

    @abc.abstractmethod
    def find_by_version(self, version):
        """
        Finds a migration by specified version number
        :param version: The version to filter by
        :type version: str
        :return: The migration with specified version or None
        """
        raise NotImplementedError


class MySQLMigrationDao(AbstractMigrationDao):
    def destroy(self):
        self._conn.close()

    def save(self, migration):
        cursor = self._conn.cursor()
        db_migration = self.find_by_version(migration.version)

        if db_migration:
            query = """
                UPDATE {} SET 
                    {}='{}',
                    {}='{}',
                    {}='{}',
                    {}='{}',
                    {}='{}'
                WHERE {} = '{}'
            """

            cursor.execute(query.format(
                AbstractSchema.TABLE,
                AbstractSchema.COL_NAME,
                migration.name,
                AbstractSchema.COL_STATUS,
                migration.status.value,
                AbstractSchema.COL_STATUS_UPDATE,
                migration.status_update.strftime("%Y-%m-%d %H:%M:%S"),
                AbstractSchema.COL_FILE_PATH,
                migration.file_path,
                AbstractSchema.COL_ROLLBACK_FILE_PATH,
                migration.rollback_file_path,
                AbstractSchema.COL_VERSION,
                migration.version
            ))
        else:
            query = """
                INSERT INTO {} VALUES(
                    NULL,
                    '{}',
                    '{}',
                    '{}',
                    '{}',
                    '{}',
                    '{}'
                )
            """
            cursor.execute(query.format(
                AbstractSchema.TABLE,
                migration.version,
                migration.name,
                migration.status.value,
                migration.status_update.strftime("%Y-%m-%d %H:%M:%S"),
                migration.file_path,
                migration.rollback_file_path
            ))

        cursor.close()
        self._conn.commit()

    def find_all(self):
        query = "SELECT * FROM {} ORDER BY {}"

        cursor = self._conn.cursor()
        cursor.execute(query.format(
            AbstractSchema.TABLE,
            AbstractSchema.COL_VERSION
        ))

        return [Migration.from_row(row) for row in cursor.fetchall()]

    def find_all_applied(self, desc=True):
        query = "SELECT * FROM {} WHERE {} = '{}' ORDER BY {} {}"
        cursor = self._conn.cursor()
        cursor.execute(query.format(
            AbstractSchema.TABLE,
            AbstractSchema.COL_STATUS,
            MigrationStatus.APPLIED.value,
            AbstractSchema.COL_VERSION,
            'DESC' if desc else 'ASC'
        ))

        return [Migration.from_row(row) for row in cursor.fetchall()]

    def find_all_non_applied(self, desc=False):
        query = "SELECT * FROM {} WHERE {} <> '{}' ORDER BY {} {}"
        cursor = self._conn.cursor()
        cursor.execute(query.format(
            AbstractSchema.TABLE,
            AbstractSchema.COL_STATUS,
            MigrationStatus.APPLIED.value,
            AbstractSchema.COL_VERSION,
            'DESC' if desc else 'ASC'
        ))

        return [Migration.from_row(row) for row in cursor.fetchall()]

    def find_by_version(self, version):
        cursor = self._conn.cursor()

        query = "SELECT * FROM {} WHERE {} = '{}' LIMIT 1"
        cursor.execute(query.format(
            AbstractSchema.TABLE,
            AbstractSchema.COL_VERSION,
            version
        ))

        db_migration = cursor.fetchone()
        cursor.close()

        if db_migration:
            return Migration.from_row(db_migration)

        return None
