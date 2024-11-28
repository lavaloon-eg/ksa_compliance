import os
import shutil
from dataclasses import dataclass
from typing import cast, List

import frappe

from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.zatca_files import (
    get_zatca_tool_path,
    get_sandbox_private_key_path,
    get_csr_path,
    get_cert_path,
    get_compliance_cert_path,
    get_private_key_path,
)


@dataclass
class FileCopy:
    """
    Copies a file from [src] to [dest], creating destination directories as needed
    """

    src: str
    dest: str

    def describe(self) -> str:
        return f"Copying '{self.src}' to '{self.dest}'"

    # noinspection PyUnusedLocal
    def apply(self, verbose=False) -> None:
        print(self.describe())
        if not os.path.isdir(os.path.dirname(self.dest)):
            os.makedirs(os.path.dirname(self.dest))
        shutil.copy2(self.src, self.dest)


@dataclass
class DirectoryCopy:
    """
    Copies a directory recursively from [src] to [dest], deleting [dest] first if it already exists. Use caution to
    avoid unintended directory deletion
    """

    src: str
    dest: str

    def describe(self) -> str:
        if os.path.isdir(self.dest):
            return f"Deleting '{self.dest}', then copying '{self.src}' to '{self.dest}'"
        return f"Copying directory '{self.src}' to '{self.dest}'"

    def apply(self, verbose=False) -> None:
        def copy(src, dest):
            if verbose:
                print(f"Copying '{src}' to '{dest}'")
            shutil.copy2(src, dest, follow_symlinks=False)

        print(self.describe())
        # If we do not delete the existing directory/files, we get permission errors (at least during local testing)
        # when trying to set permissions on already existing files. This deletion is still scary because it's a tree
        # deletion
        if os.path.isdir(self.dest):
            shutil.rmtree(self.dest)

        shutil.copytree(self.src, self.dest, dirs_exist_ok=True, copy_function=copy)


class Migration:
    """
    A migration describes a list of file/directory copy operations
    """

    operations: List[FileCopy | DirectoryCopy]

    def __init__(self):
        self.operations = []

    def add(self, operation: FileCopy | DirectoryCopy) -> None:
        self.operations.append(operation)

    def describe(self) -> str:
        if not self.operations:
            return 'No files to migrate'

        return '\n'.join([op.describe() for op in self.operations])

    def apply(self, verbose=False) -> None:
        for op in self.operations:
            op.apply(verbose)


def execute(dry_run=False, verbose=False):
    """
    Migrates ZATCA files (certs, keys, csrs) and tools (CLI and JRE) from under sites and sites/zatca to
    sites/{site}/zatca-files and sites/{site}/zatca-tools
    """
    if os.path.isdir('zatca'):
        migration = Migration()
        migration.add(DirectoryCopy('zatca', get_zatca_tool_path('.')))
        if dry_run:
            print(migration.describe())
        else:
            migration.apply(verbose)

    records = cast(list[dict], frappe.get_all('ZATCA Business Settings'))
    for record in records:
        settings = cast(ZATCABusinessSettings, frappe.get_doc('ZATCA Business Settings', record['name']))
        print(f'Analyzing {settings.name}')
        migration = prepare_migration(settings)
        if dry_run:
            print(migration.describe())
        else:
            migration.apply(verbose)
            # We need to update the CLI and JRE path to point to the ones inside the site
            # CLI/JRE paths are stored in absolute form. We first get the existing path relative to 'zatca' in the
            # 'sites' directory, so instead of '/home/frappe/frappe-bench/sites/zatca/{path} we get '{path}'
            # We then get that relative to the new tools directory, and convert to an absolute path again
            if settings.zatca_cli_path:
                new_cli_path = os.path.abspath(get_zatca_tool_path(os.path.relpath(settings.zatca_cli_path, 'zatca')))
                if os.path.isfile(new_cli_path):
                    print(f'Updating CLI path from {settings.zatca_cli_path} to {new_cli_path}')
                    settings.zatca_cli_path = new_cli_path

            if settings.java_home:
                new_java_home = os.path.abspath(get_zatca_tool_path(os.path.relpath(settings.java_home, 'zatca')))
                if os.path.isdir(new_java_home):
                    print(f'Updating Java home from {settings.java_home} to {new_java_home}')
                    settings.java_home = new_java_home

            settings.save()


def prepare_migration(settings: ZATCABusinessSettings) -> Migration:
    migration = Migration()

    # We used to use the VAT as the prefix for file names (e.g. {vat}.pem for the certificate) which caused collisions
    # if the VAT is used by more than one company. We'll use the ID of the business settings going forward instead
    old_prefix = settings.vat_registration_number
    new_prefix = settings.file_prefix

    file_map = {
        old_prefix + '.csr': get_csr_path(new_prefix),
        old_prefix + '.privkey': get_private_key_path(new_prefix),
        old_prefix + '-compliance.pem': get_compliance_cert_path(new_prefix),
        old_prefix + '.pem': get_cert_path(new_prefix),
        'sandbox_private_key.pem': get_sandbox_private_key_path(),
    }

    for src, dest in file_map.items():
        if os.path.isfile(src):
            migration.add(FileCopy(src, dest))

    return migration
