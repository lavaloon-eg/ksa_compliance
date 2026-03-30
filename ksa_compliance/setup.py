from ksa_compliance.patches._2025_05_11_add_feedback_links_block import execute as add_feedback_links_block
from ksa_compliance.patches._2026_03_16_add_zatca_images import execute as add_images


def after_install():
    print('Starting post-installation setup...')
    print('Adding custom HTML block for feedback and link section...')
    add_feedback_links_block()
    print("Adding Add images from the app's public folder to File Documents...")
    add_images()
    print('Post-installation setup complete.')
