import logging

from frappe.utils.logger import get_logger

logger = get_logger('zatca', max_size=1_000_000)
logger.setLevel(logging.INFO)


__version__ = '0.57.1'


SALES_INVOICE_CODE = '388'
DEBIT_NOTE_CODE = '383'
CREDIT_NOTE_CODE = '381'
PREPAYMENT_INVOICE_CODE = '386'
