import logging
import os
import subprocess
import zipfile
from logging import Logger
from typing import Callable

import frappe
import requests
from frappe.utils.logger import get_logger
from requests import RequestException
from requests.structures import CaseInsensitiveDict
from result import Result, Err, Ok, is_err

from ksa_compliance.translation import ft


def download_with_progress(url: str, target_dir: str, progress: Callable[[float], None]) -> Result[str, str]:
    """
    Downloads a file from [url] to [target_dir], reporting progress to [progress] (0.0 - 100.0)

    Returns the file name on success, an error message on failure. Request exceptions are automatically caught and
    reported to the 'Error Log'

    Only .gz and .zip files are allowed
    """
    logger = _get_logger()
    try:
        with requests.get(url, stream=True) as response:
            file_name = _extract_filename_from_headers(response.headers)
            if is_err(file_name):
                return file_name

            extension = os.path.splitext(file_name.ok_value)[1]
            if not extension or extension not in ['.gz', '.zip']:
                return Err(
                    ft('Only .zip and .gz files are supported. Extension deduced from server: $ext', ext=extension)
                )

            current_size = 0
            total_size = int(response.headers.get('content-length', 0))

            file_path = os.path.join(target_dir, file_name.ok_value)
            logger.info(f"Downloading '{file_path}' from '{url}' ({total_size / 1024} kib)")

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024 * 64):
                    f.write(chunk)
                    current_size += len(chunk)
                    # noinspection PyBroadException
                    try:
                        progress(100 * float(current_size) / total_size)
                    except Exception:
                        pass

            return Ok(file_path)
    except RequestException as e:
        logger.error('Download failed', exc_info=True)
        frappe.log_error(title='ZATCA Setup Error')
        return Err(str(e))


def extract_archive(path: str) -> Result[str, str]:
    """
    Extracts a tar.gz or zip archive into its containing directory. This expects the archives to contain a top-level
    directory
    """
    base_dir = os.path.dirname(path)
    if path.endswith('.tar.gz'):
        # We get permissions error when overwriting existing files (previously extracted), so we recursively unlink first
        result = subprocess.run(['tar', 'zxvf', path, '-C', base_dir, '--recursive-unlink'], capture_output=True)
        if result.returncode != 0:
            return Err(ft("Failed to extract archive: '$path'", path=path))

        home_dir = result.stdout.splitlines()[0].decode('utf-8')
        return Ok(os.path.join(base_dir, home_dir))

    if path.endswith('.zip'):
        with zipfile.ZipFile(path, 'r') as archive:
            # We're assuming the archive contains a top-level directory
            home_dir = list(zipfile.Path(archive).iterdir())[0]
            archive.extractall(base_dir)
            return Ok(os.path.join(base_dir, home_dir.name))

    return Err(ft('Unsupported archive format: $path', path=path))


def _extract_filename_from_headers(headers: CaseInsensitiveDict[str]) -> Result[str, str]:
    """
    Extracts the filename from the response content disposition header and fails if it can't find and resolve a
    file name
    """
    content_disposition = headers.get('content-disposition')
    if not content_disposition:
        return Err(
            ft("Can't figure out file name because the server response is missing the " "'Content-Disposition' header")
        )

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition#syntax
    # We're expecting something like:
    # Content-Disposition: attachment; filename="..."
    # The quotes are optional. They'll be stripped out if present
    parts = [p.strip() for p in content_disposition.split(';')]
    if len(parts) < 2 or parts[0] != 'attachment':
        return Err(ft("Expected an attachment 'Content-Disposition', got '$value' instead", value=parts[0]))

    if not parts[1].startswith('filename='):
        return Err(ft("'Content-Disposition' header doesn't specify a file name"))

    filename = parts[1][len('filename=') :].strip('"')
    if not filename:
        return Err(ft("'Content-Disposition' header doesn't specify a file name"))

    # Extract file name only and ignore any path-like parts (e.g. ../)
    return Ok(os.path.basename(filename))


def _get_logger() -> Logger:
    logger = get_logger('zatca-cli-setup')
    logger.setLevel(logging.INFO)
    return logger
