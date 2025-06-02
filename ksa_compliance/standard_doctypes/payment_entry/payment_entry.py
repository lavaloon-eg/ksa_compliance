from frappe import _
import frappe

from ksa_compliance.ksa_compliance.doctype\
    .zatca_business_settings.zatca_business_settings import ZATCABusinessSettings
from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
    SalesInvoiceAdditionalFields,
)
from erpnext.accounts.doctype.payment_entry.payment_entry import PaymentEntry
from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.zatca_precomputed_invoice import (
    ZATCAPrecomputedInvoice,
)
from ksa_compliance.ksa_compliance.doctype.zatca_egs.zatca_egs import ZATCAEGS


from ksa_compliance import logger
from result import is_ok
from ksa_compliance.translation import ft

def create_prepayment_invoice_additional_fields_doctype(self: PaymentEntry, method : str = None):
    if self.doctype == 'Payment Entry' and not ZATCABusinessSettings._should_enable_zatca_for_invoice(self.name):
        logger.info(f"Skipping additional fields for {self.name} because it's before start date")
        return
    if not ZATCABusinessSettings.is_prepayment_invoice(self.name):
        logger.info(f"Skipping additional fields for {self.name} because it's not a prepayment invoice")
        return
    settings = ZATCABusinessSettings.for_invoice(self.name, self.doctype)
    if not settings:
        logger.info(f'Skipping additional fields for {self.name} because of missing ZATCA settings')
        return

    if not settings.enable_zatca_integration:
        logger.info(f'Skipping additional fields for {self.name} because ZATCA integration is disabled in settings')
        return
    prepayment_additional_fields_doc = SalesInvoiceAdditionalFields.create_for_invoice(self.name, self.doctype)
    precomputed_invoice = ZATCAPrecomputedInvoice.for_invoice(self.name)
    is_live_sync = settings.is_live_sync
    if precomputed_invoice:
        logger.info(f'Using precomputed invoice {precomputed_invoice.name} for {self.name}')
        prepayment_additional_fields_doc.use_precomputed_invoice(precomputed_invoice)

        egs_settings = ZATCAEGS.for_device(precomputed_invoice.device_id)
        if not egs_settings:
            logger.warning(f'Could not find EGS for device {precomputed_invoice.device_id}')
        else:
            # EGS Setting overrides company-wide setting
            is_live_sync = egs_settings.is_live_sync
    prepayment_additional_fields_doc.prepayment_invoice = 1
    prepayment_additional_fields_doc.insert()
    
    if is_live_sync:
        # We're running in the context of invoice submission (on_submit hook). We only want to run our ZATCA logic if
        # the invoice submits successfully after on_submit is run successfully from all apps.
        frappe.utils.background_jobs.enqueue(
            _submit_additional_fields, doc=prepayment_additional_fields_doc, enqueue_after_commit=True
        )
 
 
def _submit_additional_fields(doc: SalesInvoiceAdditionalFields):
    logger.info(f'Submitting {doc.name}')
    result = doc.submit_to_zatca()
    message = result.ok_value if is_ok(result) else result.err_value
    logger.info(f'Submission result: {message}')

def validate_prepayment_invoice(self: PaymentEntry, method):
    pass

def prevent_cancellation_of_prepayment_invoice(self: PaymentEntry, method):
    pass