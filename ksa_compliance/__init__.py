import logging

from frappe.utils.logger import get_logger

logger = get_logger('zatca', max_size=1_000_000)
logger.setLevel(logging.INFO)


__version__ = '0.47.0'
