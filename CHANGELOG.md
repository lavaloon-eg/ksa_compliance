# Overview

This file should contain release notes between tagged versions of the product. Please update this file with your pull
requests so that whoever deploys a given version can file the relevant changes under the corresponding version.

Add changes to the "Unreleased Changes" section. Once you create a version (and tag it), move the unreleased changes
to a section with the version name.

## Unreleased Changes
* Consider Is this Tax included in Basic Rate? checkbox in tax calculation per item.

## 0.12.0

* Add ZATCA Phase 1 Print Format.
* Prevent Cancellation of Sales Invoice and Sales Invoice Additional Fields.
* Prevent Deletion of a Configured ZATCA Business Settings, ZATCA EGS, ZATCA Invoice Counting & ZATCA Precomputed Invoice.

## 0.11.0

* Add ZATCA workspace and dashboard
* Remove spurious ZATCA error logs (useless results/validation errors)
* Rework submission to ZATCA to avoid committing partial invoices

This rework addresses a problem in live sync mode, where we immediately submit
invoices to ZATCA upon invoice submission.

Here's how it worked before this change. When an invoice is submitted
(`on_submit` hook), we create an associated 'Sales Invoice Additional Fields'
document (SIAF for short) which produces the signed XML that'll be sent to
ZATCA. If live sync is enabled, we immediately committed at this point
before submitting the SIAF, which submits it to ZATCA in the `before_submit`
method. The db commit was added as part of handling the 'Resend' scenario in
ZATCA where there's an internal ZATCA error requiring us to resend the XML as
is later. In that case, we wanted to keep the SIAF as draft, which we did by
raising an exception in `before_submit`. The database commit was added to
preserve the SIAF, as frappe rolls back the transaction when an exception is
raised.

During frappe's review, they pointed out that committing during the `on_submit`
hook is problematic, since it may involve other apps with hooks that haven't
been called yet. These apps may raise an error that requires rolling back the
invoice submission transaction, only that won't work because we've already
committed.

The old logic has several issues:
* It makes submitting the document submit to ZATCA. Aborting a document
submission requires raising an exception, which gave us no choice other than to
make the problematic commit or switch some tables to MyISAM or Aria
non-transactional engines. If we reverse the notion--i.e. we submit to ZATCA,
and only if that results in a non-Resend status, we submit the document--we
no longer have to raise an exception to abort anything. Submission only happens
when everything's fine, and no custom logic is needed in `before_submit`.
* It runs too much logic in the context of invoice submission. Initially, we
thought it would be a good idea to abort invoice submission completely if it
failed ZATCA integration. However, as the ZATCA integration got more complicated
(e.g. resend), this behavior no longer makes sense. If an ERPNext invoice is
submitted successfully, it should go through. If ZATCA integration fails later
(e.g. due to a misconfiguration), the invoice can be corrected after
fixing the configuration with debit/credit notes.

The new behavior is as follows:

Upon invoice submission, we insert the SIAF as "Ready for Batch". If live sync
is enabled, we queue the submission to ZATCA `submit_to_zatca` after commit
(`enqueue_after_commit=True`). If the transaction rolls back, we're fine because
the ZATCA submission won't run. If the invoice submission commits, our ZATCA
submission logic doesn't run in the context of a document submission, so it
doesn't raise any exceptions. It chugs along, creating logs, updating itself
with the result received from ZATCA. If the integration status is anything
other than 'Resend', it submits itself.

As part of this new behavior, we're removing the permission to "Submit" SIAF
from Desk from users. We'll likely add a new action on the SIAF to submit to
ZATCA at some point. For now, such cases are covered by running the sync process
manually from the 'EInvoicing Sync' page.

## 0.10.1

* Fix jinja error if taxes are not defined for any lines in the invoice
    * Previously, our tax logic only added the relevant fields if tax details were found in the item wise tax details on
      taxes and charges template for the invoice. That meant if this info was missing for any reason, our template would
      raise an excpetion when trying to round the non-existent "total_amount" for the item line
    * We now properly set the tax percent and tax amount to 0 if they're missing
    * This will generate a proper invoice which will later fail ZATCA validation (e.g. during compliance)

## 0.10.0

* Create ZATCA phase 1 business settings.
* Add phase 1 QR code generator jinja function: `get_zatca_phase_1_qr_for_invoice`, which accepts a single
  parameter: `invoice_name`
* Fix `Sales Invoice Additional Fields` not created for standard tax invoices
* Update item tax calculation to use sales taxes and charges if item has no item tax template.
* Rename KSA Simplfied print format to ZATCA Phase 2 Print Format.

## 0.9.0

* Fix tax calculation to consider items quantities.
* Remove references to 'Lava' from the app (mainly lava-cli to zatca-cli)

## 0.8.0

* Add Qr Image to sales invoice additional fields, to be used in print format.
* Create print format for all types of invoices
* Add Purchase Order Reference to Zatca generated XML file.

## 0.7.0

* Ignore permissions when inserting ZATCA integration log
* Fix item total amount in sales invoice additional fields for return invoices
* Abort submission for sales invoice additional field document if the status is resend.
* Update ZATCA integration log with Zatca status.
* Autoname method for ZATCA integration log.
* Add Last Attempt field in additional field doctype.
* Update incorrect sales invoice additional fields.
    * Set blank integration status to Resend.
    * Draft the updated documents to resend them again.
* Update NULL last attempt in sales invoice additional fields set equal to modified.
* Fix invoice submission error when lava_custom is not installed

## 0.6.0

* Add support for precomputed invoices from POS devices
* Make precomputed invoice and sales invoice additional fields UUID unique to safeguard against bugs causing double
  ZATCA submissions

## 0.5.0

* Update e-invoice sync patch
    * Change timeout to 58 minutes so that we can run it hourly
    * Run it hourly
    * Sort additional fields by creation (oldest first)
    * Run in batches (of 100 by default)
    * Add more logging

## 0.4.0

* Ignore permissions when creating sales invoice additional fields
* Skip additional fields for invoices issued before 2024-03-01
* Add a flag to control ZATCA XML validation and make it disabled by default
* Switch signed invoice XML from an attachment to a field for performance reasons

## 0.3.0

* Submit Sales invoice additional field directly only if the sync mode is live.
* Initialize e_invoicing_sync page to run the batch mode.
* Fix error when storing ZATCA API result
* Update invoice counter/hash logic to use locking to guarantee serialization
* Fix buyer details street name being included in the XML if not defined (used to insert an error as the street name)
* Fix payable amount in XML to be set using grand total.
* Adding Tax Total with Subtotal in XML To handle sending tax currency code.
* Adding integration status field in sales invoice additional fields depends on response status code.
* Set invoice hash in sales invoice additional fields read only.
* E Invoicing Sync page to be shown in search bar.
* Fix taxable amount and Line price amount in XML to be net amount.
* Fix Credit note invoice submission issue.
* Skip additional fields if ZATCA settings are missing or setup is incomplete
* Add mode of payment "payment means code" custom field
* Use payment means code when generating XML to pass credit note validation
* Add support for compliance checks

## 0.2.0

* Use a hard-coded private key if the configured URL is for the sandbox environment
* Do not use ':' in XML filenames (from timestamp)
* Various fixes to simplified invoice format to pass validation
* Add invoice validation; messages/errors show up on a validation tab on the Sales Invoice Additional Fields doctype
* Improve API response handling

## 0.1.3

* Make the temp prefix is random

## 0.1.2

* Use a temporary prefix with temp file names to avoid clashes

## 0.1.1

* Fix certificate extraction from production CSID
* Fix previous invoice hash

## 0.1.0

* XML Templates:
    * Create Tax invoice template.
    * Create Simplified tax invoice template.
    * Add a method to generate XML regarding invoice type.
* Create E-Invoicing-Sync page to run the sync batch.
    * Initiate the batch flow to Sync E-invoices Individually.
* ZATCA Business Settings
    * Onboarding: Compliance and production CSID support
    * Signing and QR generation
    * Invoice reporting and clearance support, although it currently fails with bad request
