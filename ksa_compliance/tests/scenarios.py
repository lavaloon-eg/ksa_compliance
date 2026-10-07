"""Invoices the rule tests run through ERPNext and the XML output model.

Every set of lines is billed four times: as an invoice and as a credit note, each with prices excluding
and including VAT. Many of them drift: rounding each line's VAT gives a different total than the VAT
ERPNext books for the invoice, which is what ZATCA rejected under BR-CO-14/15 in production.
"""

from dataclasses import dataclass

STANDARD, ZERO_RATED, EXEMPT, OUT_OF_SCOPE = 'S', 'Z', 'E', 'O'


@dataclass(frozen=True)
class Line:
    qty: float
    price: float
    category: str = STANDARD


@dataclass(frozen=True)
class Scenario:
    name: str
    lines: tuple[Line, ...]
    tax_included: bool
    is_return: bool
    drifts: bool


# ACC-SINV-2025-03078 (without its 0.01 workaround discount), 04085 and 05378
ONE_LINE = (Line(1, 10.01),)
TWO_LINES = (Line(50, 9.00), Line(30, 9.00))
THREE_LINES = (Line(5, 8.70), Line(1, 145.00), Line(1, 208.00))
# Each line's VAT lands on or near a half halala, so rounding them one by one drifts
MANY_LINES = tuple(
    Line(qty, price)
    for qty, price in (
        (5, 8.70), (7, 0.99), (3, 12.35), (11, 3.33), (2, 19.99), (1, 45.45), (9, 7.77), (13, 2.15), (1, 99.90),
        (6, 4.45), (4, 15.05), (3, 6.65), (17, 1.75), (2, 33.33), (5, 11.11), (40, 0.35), (1, 27.35), (8, 5.55),
        (3, 13.13), (2, 18.85),
    )
)  # fmt: skip
ZERO_RATED_LINE = Line(2, 75.50, ZERO_RATED)
EXEMPT_LINE = Line(1, 100.00, EXEMPT)

LINE_SETS = {
    'one_line': ONE_LINE,
    'two_lines': TWO_LINES,
    'three_lines': THREE_LINES,
    'many_lines': MANY_LINES,
    'standard_and_zero_rated': THREE_LINES + (ZERO_RATED_LINE,),
    'standard_and_exempt': THREE_LINES + (EXEMPT_LINE,),
    'standard_zero_rated_and_exempt': TWO_LINES + (ZERO_RATED_LINE, EXEMPT_LINE),
    'many_lines_all_categories': MANY_LINES[:10] + (ZERO_RATED_LINE,) + MANY_LINES[10:] + (EXEMPT_LINE,),
    'zero_rated_only': (ZERO_RATED_LINE, Line(3, 7.35, ZERO_RATED)),
    'exempt_only': (EXEMPT_LINE, Line(4, 12.40, EXEMPT)),
    # BR-O-11: an invoice with an out of scope line may not carry any other VAT category
    'out_of_scope_only': (Line(1, 250.00, OUT_OF_SCOPE), Line(2, 33.30, OUT_OF_SCOPE)),
}

# The rounding method of the production site the drifting invoices come from. Under half-up rounding, a line
# VAT ending in exactly half a halala (5 x 8.70 x 15% = 6.525) rounds up, and some of these stop drifting.
ROUNDING_METHOD = "Banker's Rounding"

# Invoices where the sum of the rounded line VAT differs from the VAT ERPNext books, under ROUNDING_METHOD.
# A credit note drifts exactly like the invoice it mirrors.
DRIFTING = {
    'one_line_including_vat',
    'two_lines_including_vat',
    'three_lines_excluding_vat',
    'three_lines_including_vat',
    'many_lines_excluding_vat',
    'many_lines_including_vat',
    'standard_and_zero_rated_excluding_vat',
    'standard_and_zero_rated_including_vat',
    'standard_and_exempt_excluding_vat',
    'standard_and_exempt_including_vat',
    'standard_zero_rated_and_exempt_including_vat',
    'many_lines_all_categories_excluding_vat',
    'many_lines_all_categories_including_vat',
}


def _scenario(set_name: str, lines: tuple[Line, ...], tax_included: bool, is_return: bool) -> Scenario:
    invoice_name = f'{set_name}_{"including" if tax_included else "excluding"}_vat'
    name = f'{invoice_name}_credit_note' if is_return else invoice_name
    return Scenario(name, lines, tax_included, is_return, drifts=invoice_name in DRIFTING)


SCENARIOS = tuple(
    _scenario(set_name, lines, tax_included, is_return)
    for set_name, lines in LINE_SETS.items()
    for tax_included in (False, True)
    for is_return in (False, True)
)


def scenarios_with(category: str) -> list[Scenario]:
    return [scenario for scenario in SCENARIOS if any(line.category == category for line in scenario.lines)]
