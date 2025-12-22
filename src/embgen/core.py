"""Core parsing and rendering logic shared across all domains."""

import logging
from datetime import datetime
from pathlib import Path

import yaml
from jinja2 import Environment

from .domains import DomainGenerator, BaseConfig, detect_domain, discover_domains
from .templates import get_env, MultifileGroup


def parse_yaml(input_path: Path) -> dict:
    """Parse a YAML file and return the data as a dictionary."""
    log = logging.getLogger("embgen")

    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input file {input_path} does not exist")
    elif not input_path.is_file():
        raise FileNotFoundError(f"Input file {input_path} is not a file")
    elif input_path.suffix not in [".yml", ".yaml"]:
        raise FileNotFoundError(f"Input file {input_path} is not a YAML file")

    log.info(f"Loading YAML file from {input_path.as_posix()}")
    try:
        with open(input_path, "r") as file:
            data = yaml.safe_load(file)
    except Exception as e:
        raise RuntimeError("Failed to load YAML file") from e

    return data


def ensure_output_dir(output_path: Path) -> Path:
    """Ensure output directory exists, creating it if necessary."""
    log = logging.getLogger("embgen")

    output_path = Path(output_path).resolve()
    if not output_path.parent.exists():
        raise FileNotFoundError(f"Output directory {output_path.parent} does not exist")
    elif not output_path.parent.is_dir():
        raise FileNotFoundError(
            f"Output directory {output_path.parent} is not a directory"
        )
    elif not output_path.exists():
        log.debug(f"Creating output directory {output_path}")
        output_path.mkdir(exist_ok=True, parents=True)

    return output_path


def render_to_file(
    env: Environment,
    generator: DomainGenerator,
    config: BaseConfig,
    template_name: str,
    output_path: Path,
    output_ext: str,
    suffix: str | None = None,
) -> str:
    """Render a config to a template and write to file.

    Args:
        env: Jinja2 environment.
        generator: Domain generator instance.
        config: Validated configuration.
        template_name: Template filename.
        output_path: Output directory path.
        output_ext: Output file extension.
        suffix: Optional suffix for multifile outputs (e.g., "1", "2").

    Returns:
        The generated filename.
    """
    log = logging.getLogger("embgen")

    template = env.get_template(template_name)
    content = generator.render(config, template)

    if suffix:
        filename = f"{config.output_filename}_{suffix}.{output_ext}"
    else:
        filename = f"{config.output_filename}.{output_ext}"
    output_file = output_path / filename

    log.debug(f"Writing {output_ext} output to '{filename}'")
    with open(output_file, "w") as f:
        f.write(content)

    return filename


def render_multifile_group(
    env: Environment,
    generator: DomainGenerator,
    config: BaseConfig,
    multifile_group: MultifileGroup,
    output_path: Path,
) -> list[str]:
    """Render all templates in a multifile group.

    Args:
        env: Jinja2 environment.
        generator: Domain generator instance.
        config: Validated configuration.
        multifile_group: The multifile group to render.
        output_path: Output directory path.

    Returns:
        List of generated filenames.
    """
    filenames = []

    # Track how many files have been generated per extension to handle same-extension multifiles
    ext_counts: dict[str, int] = {}

    for template_info in multifile_group.templates:
        # For same-extension multifiles, use the template's suffix
        # For different-extension multifiles, suffix is None
        suffix = template_info.suffix

        # If we have multiple files with the same extension but no explicit suffix,
        # generate a numeric suffix to avoid overwriting
        if suffix is None:
            ext = template_info.output_ext
            if ext in ext_counts:
                ext_counts[ext] += 1
                # Only add suffix if this is the second or later file with same extension
                # But we check if there are multiple templates with the same extension
                same_ext_templates = [
                    t for t in multifile_group.templates if t.output_ext == ext
                ]
                if len(same_ext_templates) > 1:
                    suffix = str(ext_counts[ext])
            else:
                ext_counts[ext] = 1
                # Check if there will be more files with same extension
                same_ext_templates = [
                    t for t in multifile_group.templates if t.output_ext == ext
                ]
                if len(same_ext_templates) > 1:
                    suffix = "1"

        filename = render_to_file(
            env,
            generator,
            config,
            template_info.filename,
            output_path,
            template_info.output_ext,
            suffix,
        )
        filenames.append(filename)

    return filenames


def parse_and_render(
    generator: DomainGenerator,
    input_path: Path,
    output_path: Path,
    template_types: dict[str, str],
    multifile_groups: dict[str, MultifileGroup] | None = None,
) -> list[str]:
    """
    Parse a YAML input file and render outputs using the specified generator.

    Args:
        generator: The domain generator to use for validation and rendering.
        input_path: Path to the input YAML file.
        output_path: Path to the output directory.
        template_types: Dict mapping output extension to template filename.
        multifile_groups: Optional dict of multifile groups to render.

    Returns:
        list[str]: List of filenames generated in the output directory.
    """
    log = logging.getLogger("embgen")

    if multifile_groups is None:
        multifile_groups = {}

    # Parse YAML
    data = parse_yaml(input_path)

    # Validate with domain-specific model
    log.debug(f"Validating {generator.name} configuration")
    try:
        config = generator.validate(data)
    except Exception as e:
        log.error(f"Failed to validate {generator.name}: {e}")
        raise RuntimeError(f"Failed to validate {generator.name}") from e

    # Ensure output directory
    output_path = ensure_output_dir(output_path)

    # Create Jinja environment for this domain's templates
    env = get_env(generator.templates_path)

    # Add generated_on to template context
    env.globals["generated_on"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log.info(f"Writing outputs to {output_path.as_posix()}")
    filenames = []

    generated_extensions: set[str] = set()

    # Render single-file templates
    for output_ext, template_name in template_types.items():
        filename = render_to_file(
            env, generator, config, template_name, output_path, output_ext
        )
        filenames.append(filename)
        generated_extensions.add(output_ext)

    # Render multifile groups
    for group_name, mf_group in multifile_groups.items():
        log.debug(f"Rendering multifile group '{group_name}'")
        mf_filenames = render_multifile_group(
            env, generator, config, mf_group, output_path
        )
        filenames.extend(mf_filenames)
        # Add all extensions from the multifile group
        generated_extensions.update(mf_group.output_extensions)

    # Run post-generation hook (e.g., copy extra files)
    extra_files = generator.post_generate(config, output_path, generated_extensions)
    filenames.extend(extra_files)

    log.info(f"Wrote {len(filenames)} files: {', '.join(filenames)}")
    return filenames


def auto_parse_and_render(
    input_path: Path,
    output_path: Path,
    template_types: dict[str, str],
    multifile_groups: dict[str, MultifileGroup] | None = None,
) -> list[str]:
    """
    Auto-detect domain from YAML and render outputs.

    Args:
        input_path: Path to the input YAML file.
        output_path: Path to the output directory.
        template_types: Dict mapping output extension to template filename.
        multifile_groups: Optional dict of multifile groups to render.

    Returns:
        list[str]: List of filenames generated in the output directory.
    """
    log = logging.getLogger("embgen")

    data = parse_yaml(input_path)
    generator = detect_domain(data)

    if generator is None:
        available = list(discover_domains().keys())
        raise RuntimeError(
            f"Could not auto-detect domain from YAML. Available domains: {available}"
        )

    log.info(f"Auto-detected domain: {generator.name}")
    return parse_and_render(
        generator, input_path, output_path, template_types, multifile_groups
    )
