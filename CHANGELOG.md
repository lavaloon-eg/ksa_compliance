# Overview

This file should contain release notes between tagged versions of the product. Please update this file with your pull
requests so that whoever deploys a given version can file the relevant changes under the corresponding version.

Add changes to the "Unreleased Changes" section. Once you create a version (and tag it), move the unreleased changes
to a section with the version name.

## Unreleased Changes

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