from tabulate import tabulate

from mat.log_utils import logger
from mat.config_loader import ConfigLoader
from mat.migrations_processors.scanners import FileScanner
from mat.migrations_processors.runners import MySQLRunner
from mat.model.daos import MySQLSchema, MySQLMigrationDao


class Mat:
    def __init__(self, config_file_path):
        """
        Initializes mat client

        :param config_file_path: Path to configuration file
        :type config_file_path: str
        """
        conf_loader = ConfigLoader(config_file_path)
        self.scanner = FileScanner(conf_loader)

        schema = MySQLSchema(conf_loader)
        self.migrations_dao = MySQLMigrationDao(schema)
        self.runner = MySQLRunner(self.migrations_dao, schema, self.scanner)

    def _scan(self):
        """
        Looks for migration scripts and registers it into
        database migrations table

        :return:
        """
        migrations_metas = self.scanner.scan()
        self.migrations_dao.upsert(migrations_metas)

    def status(self, skip_scan=False):
        """
        Show status of all migrations, by default will scan directories and
        update migrations table before list results

        :param skip_scan: if True directory will be scanned before print state
        :type skip_scan: bool
        """
        if not skip_scan:
            self._scan()

        migrations = self.migrations_dao.find_all()
        headers = ["Version", "Name", "Status", "Status Update"]
        table = (migration.as_row() for migration in migrations)
        logger.info(tabulate(table, headers, tablefmt="psql"))

    def migrate(self, steps=None):
        self._scan()

        if self.runner.migrate(steps):
            self.status(skip_scan=True)

    def rollback(self, steps=None):
        self._scan()

        if self.runner.rollback(steps):
            self.status(skip_scan=True)
