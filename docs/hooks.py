import os
import shutil
from mkdocs.config.defaults import MkDocsConfig

# from mkdocs.structure.files import Files
# from mkdocs.structure.pages import Page
from mkdocs.utils import log


def copy_file_safe(config: MkDocsConfig, dir: str, filename: str):
    """Safely copy a file from source to destination."""
    source_file = os.path.join(config["docs_dir"], dir, filename)
    dest_file = os.path.join(config["site_dir"], dir, filename)

    # Create destination directory if it doesn't exist
    os.makedirs(os.path.dirname(dest_file), exist_ok=True)

    # Copy the file if it exists
    if os.path.exists(source_file):
        shutil.copy2(source_file, dest_file)
        log.info(f"Copied {source_file} to {dest_file}")
    else:
        log.warning(f"{source_file} not found")


def on_post_build(config: MkDocsConfig, **kwargs):
    # copy_file_safe(config, "tools", "index.html")
    # copy_file_safe(config, "tools", "main.py")
    # copy_file_safe(config, "tools", "pyscript.json")
    pass
