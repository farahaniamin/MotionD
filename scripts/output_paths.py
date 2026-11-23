from pathlib import Path


def get_project_output_dir(project_dir: Path | None = None) -> Path:
    """
    Returns `<workspace>/<project-name>-output` next to the project directory
    so rendered deliverables never clutter the root workspace folder.
    """
    proj = (project_dir or Path.cwd()).resolve()
    raw_name = proj.name or "editorial-reel"
    stem = raw_name[:-7] if raw_name.endswith("-output") and len(raw_name) > 7 else raw_name
    parent = proj.parent if proj.parent != proj else proj
    return parent / f"{stem}-output"


def resolve_mp4_output_path(
    raw_output: str | None = None,
    default_stem: str | None = None,
    project_dir: Path | None = None,
) -> Path:
    """
    Resolves final MP4 output paths into `<workspace>/<project-name>-output/`:
      - Omitted/None:          `../<project-name>-output/<default_stem or project-name>.mp4`
      - Bare filename:         `--output "Final.mp4"` -> `../<project-name>-output/Final.mp4`
      - Legacy parent-root:    `--output "../Final.mp4"` -> `../<project-name>-output/Final.mp4`
      - Explicit directory:    `--output "../custom-out"` -> `../custom-out/<default_stem>.mp4`
      - Explicit nested path:  `--output "../my-dir/Final.mp4"` -> preserved verbatim
    """
    proj = (project_dir or Path.cwd()).resolve()
    raw_name = proj.name or "editorial-reel"
    clean_name = raw_name[:-7] if raw_name.endswith("-output") and len(raw_name) > 7 else raw_name
    default_dir = get_project_output_dir(proj)
    fallback_filename = f"{default_stem or clean_name}.mp4"

    if raw_output is None or not str(raw_output).strip():
        return default_dir / fallback_filename

    out_p = Path(str(raw_output).strip())

    # Bare filename without directory component -> place cleanly in <project>-output/
    if not out_p.is_absolute() and out_p.parent == Path("."):
        if out_p.name.endswith("-output") and not out_p.suffix:
            return default_dir / fallback_filename
        fname = out_p.name if out_p.suffix else f"{out_p.name}.mp4"
        return default_dir / fname

    resolved = out_p.resolve() if out_p.is_absolute() else (proj / out_p).resolve()

    # If user passed a directory path (no extension or existing dir), place MP4 inside it
    if not resolved.suffix or (resolved.exists() and resolved.is_dir()):
        return resolved / fallback_filename

    # Guard against legacy "../Final_Reel.mp4" calls cluttering the workspace root
    if resolved.parent == proj.parent:
        return default_dir / resolved.name

    return resolved
