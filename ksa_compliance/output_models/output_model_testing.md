

#### Item details

2 Items:
Demo Item Price: 57.38, Vat 15 %
Test 5 Item Price: 22.89, Vat 5 %

#### No Discount on Item and Invoice
First Scenario: *Passed*

#### Discount On Item
Percentage: 1.37 %
First Scenario: *Accepted With Warnings*

> CODE : BR-KSA-51, MESSAGE : [BR-KSA-51]-The line amount with VAT (KSA-12) must be Invoice line net amount (BT-131) + Line VAT amount (KSA-11).

```xml
# Line
<cbc:RoundingAmount currencyID="SAR">25.96</cbc:RoundingAmount>
# Must be equal sum
<cbc:TaxAmount currencyID="SAR">3.39</cbc:TaxAmount>
<cbc:LineExtensionAmount currencyID="SAR">22.58</cbc:LineExtensionAmount>
```

Actual sum = 3.39 + 22.58 = 25.97 != 25.96
#### Discount On Invoice Grand Total And On Net Total
Percentage: 3.53
Amount: 3.26
First Scenario: *Rejected*

> CODE : BR-CO-15, MESSAGE : [BR-CO-15]-Invoice total amount with VAT (BT-112) = Invoice total amount without VAT (BT-109) + Invoice total VAT amount (BT-110).

```xml
# Invoice
<cbc:TaxInclusiveAmount currencyID="SAR">89.05</cbc:TaxInclusiveAmount>
Must be equal Sum
<cbc:TaxExclusiveAmount currencyID="SAR">77.44</cbc:TaxExclusiveAmount>
<cac:TaxTotal><cbc:TaxAmount currencyID="SAR">11.62</cbc:TaxAmount</cac:TaxTotal>
```

Actual Sum: 77.44 + 11.62 = 89.06 != 89.05
#### Discount On Item and Invoice Grand Total and Invoice Net Total
Item discount % = 1.37
Invoice Discount = 3.53
First Scenario: *Rejected* 

Invoice ID : ACC-SINV-2025-00211
CODE : BR-CO-14, MESSAGE : [BR-CO-14]-Invoice total VAT amount (BT-110) = Σ VAT category tax amount (BT-117).

```xml
<cbc:TaxAmount currencyID="SAR">750.88</cbc:TaxAmount>
Equal Sum
<cac:TaxSubtotal><cbc:TaxAmount> -> 738.14 + 12.73 = 750.87
```
Reason: both earlier errors

#### Tax Included Item No Discount
First Scenario: *Passed*

#### Tax Included  Item and Item Discount
Item Discount %: 2.53% and 2.57 %
Fist Scenario: *Rejected*

> CODE : BR-CO-11, MESSAGE : [BR-CO-11]-Sum of allowances on document level (BT-107) = Σ Document level allowance amount (BT-92).  
> 
>CODE : BR-KSA-F-04, MESSAGE : [BR-KSA-F-04]-All the document amounts and quantities must be positive, unless specified otherwise

```
<cbc:AllowanceTotalAmount currencyID="SAR">0.0</cbc:AllowanceTotalAmount>
must be equal
<cac:AllowanceCharge><cbc:Amount currencyID="SAR">-0.01</cbc:Amount>
```

#### Tax Included Item and Invoice Discount Grand Total and Discount Net Total
Item discount:  2.53% and 2.57 %
Invoice discount: 4.57 %
First Scenario: *Rejected*

> CODE : BR-CO-11, MESSAGE : [BR-CO-11]-Sum of allowances on document level (BT-107) = Σ Document level allowance amount (BT-92).

```xml
<cbc:AllowanceTotalAmount currencyID="SAR">3.11</cbc:AllowanceTotalAmount>
must be equal
<cac:AllowanceCharge><cbc:Amount currencyID="SAR">3.10</cbc:Amount>
```

3.11 != 3.10

#### Tax Included Invoice Discount Grand Total and Net Total

Invoice Discount: 34.32 % and 4.57 %
First Scenario: *Accepted*



