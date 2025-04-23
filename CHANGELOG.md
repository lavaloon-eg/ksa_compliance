# Overview

This file should contain release notes between tagged versions of the product. Please update this file with your pull
requests so that whoever deploys a given version can file the relevant changes under the corresponding version.

Add changes to the "Unreleased Changes" section. Once you create a version (and tag it), move the unreleased changes
to a section with the version name.

## Unreleased Changes

## 0.47.0

* Support displaying `Return Against Additional References` in `ZATCA Phase 2 print format`.
* Fix letter head in ZATCA print formats.
* Add Additional IDs translation.

## 0.46.0

* Use ZATCA CLI 2.7.0

## 0.45.1

* Use ZATCA CLI 2.6.0
  * This fixes an issue with invoice ZATCA validation prior to submission
  * Refer to the [CLI release](https://github.com/lavaloon-eg/zatca-cli/releases/tag/2.6.0) for details

## 0.45.0

* Add `Return Against` in `ZATCA Phase 2 Print Format` for Debit & Credit Notes.

## 0.44.0

* Support multiple billing references for return invoices
  * Add `Return Against Additional References` custom field to sales invoice
  * The field has no ERPNext impact. The additional references are included in the XML for ZATCA
  * The field allows submitted non-return invoices for the same company/customer/supplier as the current invoice

## 0.43.2

* Fetch buyer’s postal zone from buyer details in SIAF instead of incorrectly using the seller’s postal zone.

## 0.43.1

* Consider multiple tax categories in invoice allowance amount.

## 0.43.0

* Support selecting Print Format and Language when downloading PDF/A-3b.

## 0.42.0

* Add support to generate PDF/A-3b for invoices
  * Uses ZATCA CLI 2.5.0

## 0.41.2

* Update ZATCA Phase 2 Print Format for both Sales Invoice and POS Invoice.
  * Consider missing seller and buyer other ids.
  * Consider New Feature `Enable Branch Configuration` to display branch CRN and Address.

## 0.41.1

* Add Arabic translations for multi-branch support

## 0.41.0

* Update ZATCA Business Settings and add checkbox `Enable Branch Configuration`.
* Update Branch doctype add fields for
  * Company
  * Address
  * Branch Commercial Registration Number (CRN)
* When enabling this configuration sales invoice will not be submittable without a branch specified in the sales invoice, 
this requires manual configuration of an accounting dimension for branch and company.

## 0.40.1

* Fix `TaxAmount` rounding in XML if system precision > 2.

## 0.40.0

* CLI setup now grabs version 2.4.0

## 0.39.4

* Fix item line tax amount calculation if invoice is not in `SAR`.

## 0.39.3

* Use flt instead of round when calculating line amount for tax included items to ensure we use the system-configured
  rounding method
* Update "Return Reason" label in sales invoice to "Return/Debit Reason" since it's used in both cases
* Update print formats to be translatable (English/Arabic out of the box)

## 0.39.2

* Fix error messages not showing on frappe versions older than v15.17.0

## 0.39.1

* Prevent cancellation of invoices only when ZATCA phase 2 integration is enabled for the company

## 0.39.0

* CLI setup now grabs version 2.3.0

## 0.38.0

* Fix invalid tax amounts if an item is added to multiple lines
  * We now use ERPNext-computed line-level tax totals instead of item-wise tax details
  * Print formats now use line-level tax totals if present and fall back to item-wise tax details if not, to accomodate
    invoices issued prior to this change

## 0.37.2

* Fix invoice being rejected when pricing rule is applied with discount amount and margin.

## 0.37.1

* Fix various return invoice regressions in 0.37.0
  * Fix negative total and line value errors
  * Fix payable and rounding adjustment amount warnings in case of return

## 0.37.0

* Improve ZATCA validation error messages on submitting invoices (if blocking on invalid invoices is enabled)
  * We now only show errors/warnings headers if we actually have errors/warnings
  * The errors and generated XML is put into the `Error Log` to make it easier to troubleshoot instead of hunting for 
  the XML file in /tmp
* Improve XML generation to avoid excessive blank lines
* Support "Rounded Total" if enabled
  * Output rounding adjustment as is (positive or negative); previously, we used the absolute value which is wrong
  * Use the rounded total (`rounded_total`) as the payable amount instead of the grand total.
    `rounded_total = grand_total + rounding adjustment`

## 0.36.1

* Fix Return Invoice rejection when adding discount amount as amount (not percentage) on grand total

## 0.36.0

* CLI setup now grabs version 2.2.0

# 0.35.0

* Fix handling of B2B customers
  * A B2B customer has a VAT or at least one of the other IDs (TIN, CRN, etc.)
  * The compliance dialog now uses an updated filter for simplified/standard customers that respects this definition
  * When saving an invoice for a company configured to use "Standard Tax Invoices" only, we validate that the customer
    has a valid ID (VAT or other)
  * When generating XML for ZATCA, we no longer include other IDs as a `CompanyID` inside the `PartyTaxScheme` because 
    it results in validation failure

# 0.34.0

* Fix seller additional ids were returned empty in the xml if not filled.
* Include buyer additional ids in case if no vat registration number is provided for the buyer.

# 0.33.1

* Fix JRE extraction error if it was previously extracted

## 0.33.0

* Fix compliance check not showing the error message if an exception occurs
  * This happens for missing configurations, e.g. not having a sales taxes and charges template set for the company
* Migrate ZATCA files under the site directory to avoid loss upon update on frappe cloud
  * Certificates, keys, and CSRs are now stored in `{site}/zatca-files`
  * Tools (CLI and JRE) are now stored in `{site}/zatca-tools`
  * A patch migrates existing files if any, but it'll only work for self-hosted instances (on frappe cloud, the files
    would be lost before the patch is run)

## 0.32.2

* Fix print format company filter for POS Invoice Phase 2
* Fix return POS invoices getting rejected due to missing reason
  * Use hard-coded return reason "Return of goods"

## 0.32.1

* Fix invoice rejection when user increases the item rate on sales invoice.

## 0.32.0

* Delete obsolete print formats
* Add phase 2 support for POS Invoice
  * `Sales Invoice Additional Fields` and `ZATCA Integration Log` can now link to `POS Invoice`
  * `Sales Invoice Additional Fields` are now created for POS invoices and skipped for consolidated sales invoice 
    (created from POS invoices when closing the POS)
  * Added phase 2 print format for POS Invoice that includes the QR from the corresponding additional fields doc

## 0.31.0

* Support invoice discount on `Grand Total`.

## 0.30.3

* Enhance Fatoora Server Url patch to remove spaces for each company fatoora server url.

## 0.30.2

* Fix `ZATCA Integration Log` to store the actual raw response returned by ZATCA instead of a JSON serialization of
  a parsed response. This ensures we can catch bugs in our parsing logic, as well as unexpected changes in the ZATCA
  response format
* Use `clearanceStatus` from ZATCA responses as `ZATCA Integration Log` status instead of `status`. This fixes
  blank status for cleared invoices

## 0.30.1

* Use ZATCA CLI 2.1.1 which includes updated schematrons for validation

## 0.30.0

* Add ZATCA Integration Summary and ZATCA Integration details reports.
* Add Checkbox for automatic configuration for VAT accounts in `ZATCA Business Settings`
* Fix automatic creation of Tax account on creating new `ZATCA Business Settings` when System Language is not English.

## 0.29.1

* Hot Fix for print format displaying last ZATCA Business Settings info. instead of current company settings.

## 0.29.0

* Support blocking sales invoice submission on ZATCA validation failure
  * Add a new setting `Block Invoice on Invalid XML` to `ZATCA Business Settings`
  * CLI setup now grabs version 2.1.0 (required for blocking support)
  * Upon sales invoice submission, we now throw an exception and show errors/warnings from ZATCA validation if any

## 0.28.0

* Support multiple tax categories in sales invoice.
* Add new ZATCA Tax Category
  * Code: VATEX-SA-DUTYFREE,
  * Reason: Qualified Supply of Goods in Duty Free area

## 0.27.0

* Add a new tab in ZATCA Phase 2 Business Settings for configuration of the tax account per company.
* Create Tax Category, Sales Taxes and Charges template and Item tax template and link them to the tax account created on creating new ZATCA Business Settings
* Set ZATCA Business Settings Fields to Be readonly only after onboarding except for system manager.
  * Updated fields: Company, Unit Name, Unit Serial, Address, seller name, VAT Registration Number and additional ids.

## 0.26.0

* Remove `Fatoora Server Url` field and replace it with `Fatoora Server` Select Field with 3 options `['Sandbox', 'Simulation', 'Production']`
* Automatic update of the new `Fatoora server` field with the server that was already in the `Fatoora Server Url` field. 

## 0.25.1

* Merge hot fixes from master (from 0.23.2)

## 0.25.0

* Support item tax included in basic rate.

## 0.24.2

* Hot fix for customer creation on frappe v15.38.0 ([Issue](https://github.com/lavaloon-eg/ksa_compliance/issues/86))
* Fix showing done only without displaying error message on Perform Compliance Check when there is an issue in company setup.

## 0.24.1

* Fix not showing additional buyer ids for customer when creating a new customer using quick entry.

## 0.24.0

* Support item discounts

## 0.23.3

* Hot Fix for print format displaying last ZATCA Business Settings info. instead of current company settings.

## 0.23.2

* Hot fix: Use seller name instead of company name when generating CSR. Seller name is meant to be the company name
  in communications with ZATCA, and can be edited directly (whereas company name is internal)
* Hot fix: When parsing ZATCA errors, handle plain string errors without code or category. In certain cases, like the 
  seller name being too long, the ZATCA response included plain errors which caused error parsing itself to fail prior
  to logging the failure

## 0.23.1

* Hot fix for customer creation on frappe v15.38.0 ([Issue](https://github.com/lavaloon-eg/ksa_compliance/issues/86))

## 0.23.0

* Support submitting sales invoice with different currencies as per ZATCA acceptance criteria.
* Show print format of POS, Phase 1 and Phase 2 in current invoice currency.

## 0.22.1

* Include ZATCA Validation on sales taxes and charges table only if company has active phase 1 or phase 2 business settings

## 0.22.0

* Add ZATCA phase 1 print format for `POS Invoice`

## 0.21.1

* Fix compliance errors when specifying "simplified" or "standard" explicitly

## 0.21.0

* Track which `Sales Invoice Additional Fields` is latest in case of multiple submissions for the same invoice  due to
  rejection
* Limit fixing rejection to the latest sales invoice additional fields document
* Fix dashboard rejected invoice count
  * If an invoice receives multiple rejections, it counts as one rejected invoice now.

## 0.20.2

* Validate that sales invoice has tax rate in Sales Taxes and Charges Table in Phase 1 and Phase 2.
* Show all validation errors in one message on saving sales invoice.

## 0.20.1

* Fix parsing of ZATCA API responses
  * This should result in displaying actual error messages instead of just reporting the HTTP exception
* Fix simulation environment compliance CSID request
  * Requires ZATCA CLI version >= 2.0.1

## 0.20.0

* Update ZATCA workspace
  * Add link to overall integration dashboard
  * Add link to phase 1 business settings
  * Add link to tax categories
* Use `item_code` instead of `item_name` when accessing item tax details in print format of phase 1 and phase 2
* Fix a bug in phase 1 print format where the company address is displayed for the buyer instead of the buyer address in case 
  of Standard Tax Invoice
* Fix calculation of sum of allowance on invoice to be (invoice discount amount) + (sum discount amount on item)
* Validate that sales invoice has tax rate in Sales Taxes and Charges Table in case of enabled ZATCA Phase 2 integration

## 0.19.0

* Update compliance to handle both simplified and standard checks based on the configured type of transactions
  * If it's "Let the system decide", we prompt the user for simplified and standard customers and perform compliance
    for both
* Do not require a tax category if the sales invoice company does not have an enabled ZATCA phase 2 integration (`ZATCA
  Business Settings` with `Enable ZATCA Integration` checked)

## 0.18.0

* Support arabic translation for ZATCA tax categories.
* Add link for related integration log in Sales Invoice Additional Fields.
* Fix buyer country code in ZATCA XML
  * We used to include the country ID itself (e.g. Saudi Arabia) instead of the code (SA)
* Fix detection of standard sales invoices when ZATCA business settings is set to "Let the system decide"
  * We rely on whether the buyer has a VAT registration number, but we were setting buyer info after we've already
    detected invoice type, resulting in always thinking it's a simplified invoice.
* Specify invoice types when generating CSR
  * We used to hard code 0100 (simplified). Now we generate 1000 (standard), 0100 (simplified), or 1100 (both) depending
    on the configuration in ZATCA business settings
  * Note that this requires redoing the onboarding (production only) if the setting is changed because it requires 
    doing compliance checks for that invoice type.
* Update clearance API integration to send the "Clearance-Status" flag
* Fix company ID in buyer details (XML)
* Use due date as delivery date for standard invoices
* Rely on standard calculations of item tax details in print format.
  * Remove custom tax total and custom total after tax from sales invoice items.
* Remove custom qr code field in sales invoice

## 0.17.0

* Fix errors from non-escaped content in simplified invoice XML: Customer name, item name, etc.
* Fix and revamp simplified invoice compliance checks
  * Move compliance checks to the background queue to avoid timeouts
  * Add progress reporting
  * Tax category is now required for the compliance check since we've added a validation for it on invoice validate
  * Require all fields in the compliance prompt
  * Report the detailed ZATCA responses in an error log and link to it after the operation to enable users to report 
    problems

## 0.16.0

* Default to "Standard rate" if a sales invoice doesn't specify a tax category
  * We added a validation check to ensure a tax category is present, but that doesn't work for old submitted invoices.
    Such invoices could have been rejected for a variety of reasons, and we need to default to S tax category if they
    don't specify one when attempting to fix the rejection.
* Support fixing rejected sales invoices 
  * A fixable rejection can happen in mainly two cases:
    1) Bad or missing ZATCA configuration that leads to rejection. These cases can be fixed by updating the 
       configuration and generating another 'Sales Invoice Additional Fields' document for the invoice to submit to
       ZATCA
    2) An application bug that results in generating an invalid XML. These cases can be fixed by updating the app to a 
       later version that fixes the issue, then generating another 'Sales Invoice Additional Fields' document to submit
       to ZATCA
  * This change adds a custom button to the 'Sales Invoice Additional Fields' document that allows users to trigger the
    aforementioned generation.
  * Also, the invoice counter was appended to the 'Sales Invoice Additional Fields' name expression to ensure uniqueness.

## 0.15.0

* Add invoice line tax category and taxable amount in ZATCA XML
* Filter addresses in ZATCA phase 1 settings based on company

## 0.14.0

* Add QR code as a scannable image in Sales Invoice Additional Fields.
* Add ZATCA tax category exemption reason and code if applicable
* Remove negative values in print format on credit note issue

## 0.13.0

* Add automatic ZATCA CLI setup
  * There's now a new "CLI" tab in "ZATCA Business Settings"
  * In "Automatic" mode, we download the JRE and CLI automatically and fill in the CLI path and Java home path
  * In "Manual" mode, CLI path is specified by the user. Java home path is optional
  * Existing "ZATCA Business Settings" are automatically set to "Manual" by a patch upon deploying this change
  * New "ZATCA Business Settings" default to "Automatic"

## 0.12.1

* Use ZATCA phase 1 settings in phase 1 print format
* Fix tax calculation for tax templates with tax included in basic rate.

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
