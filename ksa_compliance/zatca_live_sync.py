# Copyright (c) 2026, LavaLoon and contributors
# For license information, please see license.txt


def get_live_zatca_submit_job_id(siaf_name: str) -> str:
    """Stable RQ job id for a live ZATCA submission on one SIAF document."""
    return f'zatca_submit_{siaf_name}'
