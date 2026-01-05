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


def on_pre_build(config: MkDocsConfig, **kwargs):
    """Copy root README.md to docs/README.md before building."""
    root_readme = os.path.join(config["config_file_path"], "..", "README.md")
    docs_readme = os.path.join(config["docs_dir"], "README.md")

    if os.path.exists(root_readme):
        with open(root_readme, "r", encoding="utf-8") as src_file:
            content = src_file.read()

        content = content.replace("docs/", "")

        with open(docs_readme, "w", encoding="utf-8") as dest_file:
            dest_file.write(content)

        log.info("Copied root README.md to docs/README.md")
    else:
        log.warning(f"Root README.md not found at {root_readme}")

    root_license = os.path.join(config["config_file_path"], "..", "LICENSE.md")
    docs_license = os.path.join(config["docs_dir"], "LICENSE.md")

    if os.path.exists(root_license):
        shutil.copy2(root_license, docs_license)
        log.info("Copied root LICENSE.md to docs/LICENSE.md")
    else:
        log.warning(f"Root LICENSE.md not found at {root_license}")


def on_post_build(config: MkDocsConfig, **kwargs):
    # copy_file_safe(config, "tools", "index.html")
    # copy_file_safe(config, "tools", "main.py")
    # copy_file_safe(config, "tools", "pyscript.json")
    pass
