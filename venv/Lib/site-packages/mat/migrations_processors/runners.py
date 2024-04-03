import abc
import mysql.connector

from datetime import datetime

from mat.model.entities import Migration, MigrationStatus
from mat.model.daos import AbstractSchema, AbstractMigrationDao
from mat.migrations_processors.scanners import AbstractScanner
from mat.log_utils import logger


class AbstractRunner(metaclass=abc.ABCMeta):

    @classmethod
    def __subclasshook__(cls, subclass):
        return (
            hasattr(subclass, '_apply') and
            callable(subclass._apply) and
            hasattr(subclass, '_unapply') and
            callable(subclass._unapply) and
            hasattr(subclass, 'migrate') and
            callable(subclass.migrate) and
            hasattr(subclass, 'rollback') and
            callable(subclass.rollback) or
            NotImplemented
        )

    def __init__(self, migration_dao, schema, scanner):
        """
        Initializes runner

        :param migration_dao:
        :type migration_dao: AbstractMigrationDao
        :param schema:
        :type schema: AbstractSchema
        :param scanner:
        :type scanner: AbstractScanner
        """
        self._migration_dao = migration_dao
        self._schema = schema
        self._scanner = scanner

        self._conn = None

    @abc.abstractmethod
    def _apply(self, migration):
        """
        Applies provided migration

        :param migration: Migration to execute
        :type migration: Migration
        :return: True if migration was successfully executed
        """
        raise NotImplementedError

    @abc.abstractmethod
    def _unapply(self, migration):
        """
        Executes rollback script for provided migration
        :param migration: Migration to rollback
        :type migration: Migration
        :return: True if migration was rolled back successfully
        """
        raise NotImplementedError

    @abc.abstractmethod
    def migrate(self, steps=None):
        """
        Runs non applied migrations

        :param steps: Optional value to limit the number of migrations to run
        :type steps: int
        :return: True if all pending migrations were applied successfully
        """
        raise NotImplementedError

    @abc.abstractmethod
    def rollback(self, steps=None):
        """
        Runs rollback scripts for migrations marked as applied in database
        table

        :param steps: Optional value to limit the number of rollbacks to run
        :type steps: int
        :return:
        """
        raise NotImplementedError


class MySQLRunner(AbstractRunner):

    def _apply(self, migration):
        commands = self._scanner.get_commands(migration.file_path)

        try:
            cursor = self._conn.cursor()
            for command in commands:
                if command.strip() != "":
                    cursor.execute(command)

            cursor.close()

            migration.status = MigrationStatus.APPLIED
            migration.status_update = datetime.now()
            self._migration_dao.save(migration)
            return True
        except mysql.connector.Error as e:
            logger.error("Error applying migration {}: {}".format(
                migration.version,
                e
            ))

            migration.status = MigrationStatus.ERROR
            migration.status_update = datetime.now()
            self._migration_dao.save(migration)
            return False

    # noinspection DuplicatedCode
    def _unapply(self, migration):
        commands = self._scanner.get_commands(migration.rollback_file_path)

        try:
            cursor = self._conn.cursor()
            for command in commands:
                if command.strip() != "":
                    cursor.execute(command)
            cursor.close()

            migration.status = MigrationStatus.REVERTED
            migration.status_update = datetime.now()
            self._migration_dao.save(migration)
            return True
        except mysql.connector.Error as e:
            logger.error("Error during rollback of migration {}: {}".format(
                migration.version,
                e
            ))

            migration.status = MigrationStatus.ERROR
            migration.status_update = datetime.now()
            self._migration_dao.save(migration)
            return False

    def migrate(self, steps=None):
        migrations = self._migration_dao.find_all_non_applied()
        if len(migrations) == 0:
            logger.info("There are no pending migrations to apply")
            return False

        self._conn = self._schema.connect()
        counter = 0

        for migration in migrations:
            counter += 1
            if steps is not None and counter > steps:
                break

            if self._apply(migration):
                self._conn.commit()
            else:
                self._conn.rollback()
                self._conn.close()
                return False

        self._conn.close()
        return True

    def rollback(self, steps=None):
        migrations = self._migration_dao.find_all_applied()
        if len(migrations) == 0:
            logger.info("There are no migrations to rollback")
            return False

        self._conn = self._schema.connect()
        counter = 0

        for migration in migrations:
            counter += 1
            if steps is not None and counter > steps:
                break

            if self._unapply(migration):
                self._conn.commit()
            else:
                self._conn.rollback()
                self._conn.close()
                return False

        self._conn.close()
        return True
