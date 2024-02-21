import logging

from frappe.utils.logger import get_logger

logger = get_logger('zatca')
logger.setLevel(logging.INFO)

__version__ = '0.1.3'
