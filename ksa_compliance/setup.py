from ksa_compliance.patches._2025_05_11_add_feedback_links_block import execute


def after_install():
    print('Starting post-installation setup...')
    print('Adding custom HTML block for feedback and link section...')
    execute()
    print('Post-installation setup complete.')
