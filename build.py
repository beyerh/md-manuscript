#!/usr/bin/env python3
"""
Manuscript Build System - Professional Cross-Platform Build Tool
Usage: python build.py [--last] [--profile NAME] [--list] [--source=FILE] [--frontmatter=FILE] [--png] [--si]
"""

import subprocess
import sys
import os
import re
import json
import shutil
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# --- Configuration ---
FRONTMATTER = "00_frontmatter.md"
MAINTEXT = "01_maintext.md"
SUPPINFO = "02_supp_info.md"
PROFILES_DIR = "resources/profiles"
BASE_PROFILE = "resources/profiles/_base.yaml"
LUA_FILTER = "resources/pdf2png.lua"
SI_HEADER = "_si_header.tex"
EXPORT_DIR = "export"
BUILD_CONFIG = ".build_config.json"
DEFAULTS_CONFIG = ".defaults_config.json"
CITATION_STYLES_DIR = "resources/citation_styles"

# Default settings when nothing is configured
DEFAULT_SETTINGS = {
    "font": "libertinus",
    "fontsize": "11pt",
    "citation_style": "vancouver"
}

# Font presets for PDF output
FONT_PRESETS = {
    "libertinus": {
        "name": "Libertinus (Default)",
        "mainfont": "Libertinus Serif",
        "sansfont": "Libertinus Sans",
        "monofont": "Libertinus Mono",
    },
    "times": {
        "name": "Times/TeX Gyre Termes",
        "mainfont": "TeX Gyre Termes",
        "sansfont": "TeX Gyre Heros",
        "monofont": "TeX Gyre Cursor",
    },
    "palatino": {
        "name": "Palatino/TeX Gyre Pagella",
        "mainfont": "TeX Gyre Pagella",
        "sansfont": "TeX Gyre Heros",
        "monofont": "TeX Gyre Cursor",
    },
    "arial": {
        "name": "Arial",
        "mainfont": "Arial",
        "sansfont": "Arial",
        "monofont": "Courier New",
    },
    "helvetica": {
        "name": "Helvetica-like (TeX Gyre Heros)",
        "mainfont": "TeX Gyre Heros",
        "sansfont": "TeX Gyre Heros",
        "monofont": "TeX Gyre Cursor",
    },
    "charter": {
        "name": "Charter",
        "mainfont": "XCharter",
        "sansfont": "TeX Gyre Heros",
        "monofont": "TeX Gyre Cursor",
    },
    "computer-modern": {
        "name": "Computer Modern (LaTeX default)",
        "mainfont": "Latin Modern Roman",
        "sansfont": "Latin Modern Sans",
        "monofont": "Latin Modern Mono",
    },
}


def _safe_csl_filename(name: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "-", name.strip())
    safe = re.sub(r"-+", "-", safe).strip("- ")
    if not safe:
        safe = "citation-style"
    if not safe.lower().endswith(".csl"):
        safe += ".csl"
    return safe


def _extract_csl_title(csl_path: Path) -> str:
    try:
        tree = ET.parse(str(csl_path))
        root = tree.getroot()
        title_el = root.find('.//{*}info/{*}title')
        if title_el is not None and title_el.text:
            return title_el.text.strip()
    except Exception:
        pass
    return csl_path.stem


def list_local_csl_files() -> List[Tuple[str, str, str]]:
    """Return local CSL files as (key, name, path)."""
    ensure_citation_styles_dir()
    local = []
    for csl in sorted(Path(CITATION_STYLES_DIR).glob('*.csl')):
        key = csl.stem
        name = _extract_csl_title(csl)
        local.append((key, name, str(csl)))
    return local


def download_csl_from_identifier(style_identifier: str) -> Optional[str]:
    """Download CSL by Zotero style ID or URL. Returns path to CSL file."""
    ensure_citation_styles_dir()

    identifier = style_identifier.strip()
    if not identifier:
        return None

    url = identifier
    filename_hint = identifier
    if not (identifier.startswith('http://') or identifier.startswith('https://')):
        url = f"https://www.zotero.org/styles/{identifier}"
        filename_hint = identifier
    else:
        try:
            parsed = urllib.parse.urlparse(identifier)
            slug = parsed.path.rstrip('/').split('/')[-1]
            if slug:
                filename_hint = slug
        except Exception:
            pass

    target = Path(CITATION_STYLES_DIR) / _safe_csl_filename(filename_hint)
    if target.exists():
        return str(target)

    print(f"   Downloading citation style: {identifier}...")
    print(f"   URL: {url}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            csl_content = response.read()
        with open(target, "wb") as f:
            f.write(csl_content)
        print(f"   ✓ Downloaded {target.name}")
        return str(target)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"   Warning: Could not download citation style: {e}")
        # Try raw GitHub as fallback for style IDs
        if not (identifier.startswith('http://') or identifier.startswith('https://')):
            github_url = f"https://raw.githubusercontent.com/citation-style-language/styles/master/{identifier}.csl"
            print(f"   Trying raw GitHub: {github_url}")
            try:
                req = urllib.request.Request(github_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=15) as response:
                    csl_content = response.read()
                with open(target, "wb") as f:
                    f.write(csl_content)
                print(f"   ✓ Downloaded {target.name} from GitHub")
                return str(target)
            except Exception as e2:
                print(f"   Raw GitHub also failed: {e2}")
        return None


def get_profile_default_fontsize(profile: str) -> Optional[str]:
    """Extract fontsize from a profile YAML (best-effort)."""
    profile_path = Path(PROFILES_DIR) / f"{profile}.yaml"
    if not profile_path.exists():
        return None
    try:
        content = profile_path.read_text()
    except Exception:
        return None

    # Look for a variables->fontsize entry.
    m = re.search(r"^\s*fontsize\s*:\s*([^\n#]+)", content, re.MULTILINE)
    if not m:
        return None
    return m.group(1).strip().strip('"\'')

FONT_SIZES = ["9pt", "10pt", "11pt", "12pt"]


def get_profile_categories() -> Dict[str, List[str]]:
    """Dynamically detect profiles and categorize them.
    
    Profiles are read from resources/profiles/*.yaml (excluding _base.yaml).
    Category is inferred from filename or profile metadata.
    """
    categories: Dict[str, List[str]] = {
        "General": [],
        "Thesis": [],
        "Journals": [],
    }
    
    profiles_path = Path(PROFILES_DIR)
    if not profiles_path.exists():
        return categories
    
    for f in sorted(profiles_path.glob("*.yaml")):
        if f.name.startswith('_'):
            continue
        
        profile_id = f.stem
        
        # Infer category from profile name
        if "thesis" in profile_id:
            categories["Thesis"].append(profile_id)
        elif any(x in profile_id for x in ["nature", "cell", "journal", "science", "pnas"]):
            categories["Journals"].append(profile_id)
        else:
            categories["General"].append(profile_id)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


def get_profile_info(profile_name: str) -> Tuple[str, str, str]:
    """Get profile display name, description, and format from profile file."""
    profile_path = Path(PROFILES_DIR) / f"{profile_name}.yaml"
    if not profile_path.exists():
        return profile_name, "", "pdf"
    
    with open(profile_path, 'r') as f:
        content = f.read()
    
    name = profile_name
    description = ""
    fmt = "pdf"
    
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('name:'):
            name = line.split(':', 1)[1].strip().strip('"\'')
        elif line.startswith('description:'):
            description = line.split(':', 1)[1].strip().strip('"\'')
        elif line.startswith('format:'):
            fmt = line.split(':', 1)[1].strip().strip('"\'')
    
    return name, description, fmt


def list_profiles() -> List[str]:
    """List all available profiles."""
    profiles_path = Path(PROFILES_DIR)
    if not profiles_path.exists():
        return []
    
    profiles = []
    for f in profiles_path.glob("*.yaml"):
        if not f.name.startswith('_'):
            profiles.append(f.stem)
    return sorted(profiles)


def load_last_config() -> Optional[Dict[str, Any]]:
    """Load the last build configuration."""
    if Path(BUILD_CONFIG).exists():
        try:
            with open(BUILD_CONFIG, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def load_defaults() -> Dict[str, Any]:
    """Load default settings or return defaults if none exist."""
    if Path(DEFAULTS_CONFIG).exists():
        try:
            with open(DEFAULTS_CONFIG, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()


def save_defaults(defaults: Dict[str, Any]) -> None:
    """Save default settings to file."""
    try:
        with open(DEFAULTS_CONFIG, 'w') as f:
            json.dump(defaults, f, indent=2)
    except Exception:
        pass


def save_config(config: Dict[str, Any]):
    """Save build configuration for quick rebuild."""
    with open(BUILD_CONFIG, 'w') as f:
        json.dump(config, f, indent=2)


def merge_configs(base_path: str, profile_path: str) -> str:
    """Merge base config with profile config, return path to merged config."""
    temp_config = "_temp_config.yaml"
    
    # Read both files
    base_content = ""
    profile_content = ""
    
    if Path(base_path).exists():
        with open(base_path, 'r') as f:
            base_content = f.read()
    
    if Path(profile_path).exists():
        with open(profile_path, 'r') as f:
            profile_content = f.read()
    
    # Filter out profile metadata from profile content
    filtered_lines = []
    skip_profile_block = False
    for line in profile_content.split('\n'):
        if line.strip().startswith('profile:'):
            skip_profile_block = True
            continue
        if skip_profile_block:
            if line.startswith('  ') or line.strip() == '':
                continue
            else:
                skip_profile_block = False
        filtered_lines.append(line)
    
    profile_content = '\n'.join(filtered_lines)
    
    # Write merged config (profile overrides base)
    with open(temp_config, 'w') as f:
        f.write(base_content)
        f.write("\n\n# --- Profile Overrides ---\n")
        f.write(profile_content)
    
    return temp_config


def strip_csl_from_defaults_file(defaults_path: str) -> None:
    """Remove any csl setting from a Pandoc defaults YAML file.

    We do this so a user-selected CSL can be provided via metadata without
    triggering Pandoc's "--csl option can only be used once" error.
    """
    path = Path(defaults_path)
    if not path.exists():
        return

    lines = path.read_text().splitlines(True)
    out: List[str] = []
    skip_next_csl_value_line = False

    for line in lines:
        stripped = line.strip()

        if skip_next_csl_value_line:
            # If the previous line was "csl:" with no inline value, remove the
            # first indented value line (e.g. "  resources/foo.csl").
            if stripped and (line.startswith(' ') or line.startswith('\t')):
                skip_next_csl_value_line = False
                continue
            skip_next_csl_value_line = False

        # Matches both top-level "csl:" and nested metadata "csl:" entries.
        if stripped.startswith('csl:'):
            # If it is just "csl:" with no inline value, also skip the next
            # indented value line.
            if stripped == 'csl:':
                skip_next_csl_value_line = True
            continue

        out.append(line)

    path.write_text(''.join(out))


def apply_font_overrides_to_defaults_file(
    defaults_path: str,
    font: Optional[str] = None,
    fontsize: Optional[str] = None,
) -> None:
    """Apply font/fontsize overrides directly to the merged Pandoc defaults file.

    This avoids situations where multiple font settings (from profile + CLI)
    end up concatenated in the generated LaTeX.
    """
    if not font and not fontsize:
        return

    path = Path(defaults_path)
    if not path.exists():
        return

    lines = path.read_text().splitlines(True)

    # Locate the first variables: block.
    variables_idx = None
    variables_indent = None
    for i, line in enumerate(lines):
        if line.strip() == "variables:":
            variables_idx = i
            variables_indent = len(line) - len(line.lstrip())
            break

    # If there's no variables block, we can't safely inject (all PDF profiles
    # currently have it, but keep this defensive).
    if variables_idx is None or variables_indent is None:
        return

    child_indent_str = " " * (variables_indent + 2)

    # Determine end of variables block.
    end_idx = len(lines)
    for j in range(variables_idx + 1, len(lines)):
        candidate = lines[j]
        stripped = candidate.strip()
        if not stripped:
            continue
        indent = len(candidate) - len(candidate.lstrip())
        if indent <= variables_indent and not stripped.startswith('#'):
            end_idx = j
            break

    # Remove existing font/fontsize keys inside the variables block.
    keys_to_remove = {"mainfont:", "sansfont:", "monofont:", "fontsize:"}
    new_block: List[str] = []
    for line in lines[variables_idx + 1 : end_idx]:
        stripped = line.strip()
        if any(stripped.startswith(k) for k in keys_to_remove):
            continue
        new_block.append(line)

    # Build override lines.
    override_lines: List[str] = []
    if font and font in FONT_PRESETS:
        font_info = FONT_PRESETS[font]
        override_lines.extend(
            [
                f"{child_indent_str}mainfont: \"{font_info['mainfont']}\"\n",
                f"{child_indent_str}sansfont: \"{font_info['sansfont']}\"\n",
                f"{child_indent_str}monofont: \"{font_info['monofont']}\"\n",
            ]
        )
    if fontsize:
        override_lines.append(f"{child_indent_str}fontsize: {fontsize}\n")

    # Write back file: keep everything, but replace variables block content.
    out = []
    out.extend(lines[: variables_idx + 1])
    out.extend(override_lines)
    out.extend(new_block)
    out.extend(lines[end_idx:])
    path.write_text(''.join(out))


def create_export_dir():
    """Create export directory if it doesn't exist."""
    Path(EXPORT_DIR).mkdir(exist_ok=True)


def ensure_citation_styles_dir():
    """Create citation styles directory if it doesn't exist."""
    Path(CITATION_STYLES_DIR).mkdir(exist_ok=True)




def resolve_citation_style(citation_style: str) -> Tuple[Optional[str], Optional[str]]:
    """Resolve citation style identifier to a CSL path and display name.
    
    Looks for local .csl files in resources/citation_styles/.
    If not found locally, attempts to download from Zotero.
    """
    if not citation_style:
        return None, None

    style = citation_style.strip()
    ensure_citation_styles_dir()

    # Check local styles first (by stem or filename)
    candidate_files = [style]
    if not style.lower().endswith('.csl'):
        candidate_files.append(style + '.csl')
    for cand in candidate_files:
        p = Path(CITATION_STYLES_DIR) / cand
        if p.exists():
            return str(p), _extract_csl_title(p)

    # Not found locally - try to download from Zotero
    path = download_csl_from_identifier(style)
    if path:
        return path, _extract_csl_title(Path(path))
    
    print(f"   Warning: Citation style '{style}' not found")
    return None, None


def create_si_header():
    """Create the SI header file for LaTeX."""
    content = r"""\usepackage{lineno}
\setcounter{page}{1}
\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\thepage}{S\arabic{page}}
"""
    with open(SI_HEADER, "w") as f:
        f.write(content)


def convert_figures_to_png():
    """Convert PDF figures to PNG using ImageMagick."""
    figures_dir = Path("figures")
    if figures_dir.exists():
        pdf_files = list(figures_dir.glob("*.pdf"))
        if pdf_files:
            print("   Converting PDF figures to PNG...")
            for pdf_file in pdf_files:
                try:
                    png_file = pdf_file.with_suffix('.png')
                    subprocess.run(
                        ["magick", "-density", "300", str(pdf_file), str(png_file)],
                        capture_output=True,
                        check=False
                    )
                except Exception:
                    pass


def list_markdown_files() -> List[str]:
    """List all markdown files in the current directory."""
    md_files = sorted([f.name for f in Path(".").glob("*.md") 
                      if not f.name.startswith("_") and f.name.lower() != "readme.md"])
    return md_files


def extract_si_citations(si_file: Optional[str] = None) -> str:
    """Extract literature citations from SI file, excluding cross-references."""
    si_path = Path(si_file) if si_file else Path(SUPPINFO)
    if not si_path.exists():
        return ""
    
    with open(si_path, "r") as f:
        content = f.read()
    
    citations = set(re.findall(r"@[a-zA-Z][a-zA-Z0-9_:-]*", content))
    excluded = {"@Fig:", "@Tbl:", "@email"}
    filtered = [c for c in citations if not any(c.startswith(e.rstrip(":")) for e in excluded)]
    
    return "; ".join(sorted(filtered))


def build_document(source_file: str, profile: str, use_png: bool, include_si_refs: bool, 
                   frontmatter_file: Optional[str] = None, font: Optional[str] = None, 
                   fontsize: Optional[str] = None, citation_style: Optional[str] = None,
                   si_file: Optional[str] = None, is_si: bool = False):
    """Build the document with specified profile."""
    # Get profile info
    _, _, fmt = get_profile_info(profile)
    
    # Determine output file name from source file
    source_path = Path(source_file)
    output_name = source_path.stem
    
    output_file = f"{EXPORT_DIR}/{output_name}.{fmt}"
    temp_merged = f"_temp_{output_name}_merged.md"
    
    print(f">> Building {source_file} ({fmt.upper()})...")
    
    # Merge frontmatter if requested
    input_file = source_file
    if frontmatter_file and Path(frontmatter_file).exists():
        print(f"   Merging frontmatter from {frontmatter_file}...")
        with open(temp_merged, "w") as out:
            with open(frontmatter_file, "r") as f:
                out.write(f.read())
            out.write("\n")
            with open(source_file, "r") as f:
                out.write(f.read())
        input_file = temp_merged
    
    # Include SI refs for main document
    if include_si_refs and not is_si:
        print("   Including SI references in bibliography...")
        if not frontmatter_file:
            shutil.copy(source_file, temp_merged)
            input_file = temp_merged
        
        si_cites = extract_si_citations(si_file)
        if si_cites:
            with open(temp_merged, "r") as f:
                original_content = f.read()
            nocite_header = f"---\nnocite: |\n  {si_cites}\n---\n\n"
            with open(temp_merged, "w") as f:
                f.write(nocite_header + original_content)
    
    # Convert figures for DOCX
    if fmt == "docx" and use_png:
        convert_figures_to_png()
    
    # Merge configs
    profile_path = f"{PROFILES_DIR}/{profile}.yaml"
    config_file = merge_configs(BASE_PROFILE, profile_path)

    # Apply font overrides directly to defaults file (prevents fontspec issues)
    if fmt == "pdf" and (font or fontsize):
        apply_font_overrides_to_defaults_file(config_file, font=font, fontsize=fontsize)
        if font and font in FONT_PRESETS:
            print(f"   Using font: {FONT_PRESETS[font]['name']}")
        if fontsize:
            print(f"   Using font size: {fontsize}")
    
    # Build pandoc command
    cmd = ["pandoc", input_file, "-o", output_file, f"--defaults={config_file}"]
    
    # Add citation style
    if citation_style:
        csl_path, csl_name = resolve_citation_style(citation_style)
        if csl_path:
            strip_csl_from_defaults_file(config_file)
            cmd.extend(["--metadata", f"csl:{csl_path}"])
            if csl_name:
                print(f"   Using citation style: {csl_name}")
    
    # Add SI-specific options
    if is_si:
        create_si_header()
        cmd.extend([
            "--metadata", 'figPrefix=["Fig.","Figs."]',
            "--metadata", 'tblPrefix=["Table","Tables"]',
            f"--include-in-header={SI_HEADER}"
        ])
    
    # Add lua filter for DOCX
    if fmt == "docx":
        cmd.append(f"--lua-filter={LUA_FILTER}")
    
    # Run pandoc
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"   Error: {e.stderr if e.stderr else 'Unknown error'}")
        # Remove temporary files
        for f in [temp_merged, config_file]:
            if f and Path(f).exists():
                os.remove(f)
        if Path(SI_HEADER).exists():
            os.remove(SI_HEADER)
        sys.exit(1)
    
    # Cleanup
    # Remove temporary files
    for f in [temp_merged, config_file]:
        if f and Path(f).exists():
            os.remove(f)
    if Path(SI_HEADER).exists():
        os.remove(SI_HEADER)
    
    print(f"   ✓ {output_file} created")


# UI Constants
BOX_WIDTH = 64  # Inner width for all frame boxes

def box_top(title: str = "") -> str:
    """Return top border with optional title."""
    if title:
        return f"┌─ {title} " + "─" * (BOX_WIDTH - len(title) - 3) + "┐"
    return "┌" + "─" * BOX_WIDTH + "┐"

def box_row(text: str) -> str:
    """Return a row with content, padded to box width."""
    return f"│  {text:<{BOX_WIDTH - 4}}  │"

def box_bottom() -> str:
    """Return bottom border."""
    return "└" + "─" * BOX_WIDTH + "┘"

def print_header():
    """Print application header."""
    print()
    print("╔" + "═" * BOX_WIDTH + "╗")
    print("║" + "Manuscript Build System".center(BOX_WIDTH) + "║")
    print("║" + "Cross-Platform • Multi-Profile".center(BOX_WIDTH) + "║")
    print("╚" + "═" * BOX_WIDTH + "╝")
    print()

def print_build_summary(config: Dict[str, Any]) -> None:
    """Print build configuration summary."""
    _, _, fmt = get_profile_info(config["profile"])
    print(box_top("Build Configuration"))
    print(box_row(f"Document:     {config.get('source_file', config.get('doc_type', 'unknown'))}"))
    print(box_row(f"Profile:      {config['profile']}"))
    print(box_row(f"Format:       {fmt.upper()}"))
    fm_display = config.get('frontmatter_file') or 'None'
    print(box_row(f"Frontmatter:  {fm_display}"))
    if fmt == "docx":
        print(box_row(f"PNG Convert:  {'Yes' if config['use_png'] else 'No'}"))
    print(box_row(f"SI Refs:      {'Yes' if config['include_si_refs'] else 'No'}"))
    if config.get('is_si'):
        print(box_row("SI Format:    Yes (S-prefixed figures/tables)"))
    if fmt == "pdf" and config.get('font'):
        font_name = FONT_PRESETS[config['font']]['name']
        print(box_row(f"Font:         {font_name}"))
    if fmt == "pdf" and config.get('fontsize'):
        print(box_row(f"Font Size:    {config['fontsize']}"))
    if fmt in ("pdf", "docx") and config.get('citation_style'):
        style_key = config['citation_style']
        # Get display name from local file or use key
        local_styles = list_local_csl_files()
        style_name = next((n for k, n, _ in local_styles if k == style_key), style_key)
        print(box_row(f"Citation:     {style_name}"))
    print(box_bottom())


def print_profiles_list():
    """Print available profiles organized by category."""
    print("\nAvailable Profiles:")
    print("─" * 50)
    
    for category, profiles in get_profile_categories().items():
        print(f"\n{category}:")
        for profile in profiles:
            name, description, fmt = get_profile_info(profile)
            print(f"  • {profile:<25} {description}")
    
    print()


def configure_defaults() -> None:
    """Configure default font, font size, and citation style."""
    print_header()
    
    defaults = load_defaults()
    
    print(box_top("Current Defaults"))
    print(box_row(f"Font: {FONT_PRESETS[defaults['font']]['name']}"))
    print(box_row(f"Font Size: {defaults['fontsize']}"))
    # Get citation style display name from local file or show the key
    style_key = defaults['citation_style']
    local_styles = list_local_csl_files()
    style_name = next((n for k, n, _ in local_styles if k == style_key), style_key)
    print(box_row(f"Citation Style: {style_name}"))
    print(box_bottom())
    print()
    
    # Font selection
    print(box_top("Font Selection"))
    font_list = list(FONT_PRESETS.keys())
    for i, key in enumerate(font_list, 1):
        name = FONT_PRESETS[key]["name"]
        marker = " (current)" if key == defaults['font'] else ""
        print(box_row(f"{i:2}) {name}{marker}"))
    print(box_bottom())
    
    font_choice = input(f"Select font [1-{len(font_list)}, Enter=keep current]: ").strip()
    if font_choice:
        try:
            idx = int(font_choice) - 1
            if 0 <= idx < len(font_list):
                defaults['font'] = font_list[idx]
        except (ValueError, IndexError):
            pass
    
    print()
    
    # Font size selection
    print(box_top("Font Size Selection"))
    for i, size in enumerate(FONT_SIZES, 1):
        marker = " (current)" if size == defaults['fontsize'] else ""
        print(box_row(f"{i:2}) {size}{marker}"))
    print(box_bottom())
    
    size_choice = input(f"Select size [1-{len(FONT_SIZES)}, Enter=keep current]: ").strip()
    if size_choice:
        try:
            idx = int(size_choice) - 1
            if 0 <= idx < len(FONT_SIZES):
                defaults['fontsize'] = FONT_SIZES[idx]
        except (ValueError, IndexError):
            pass
    
    print()
    
    # Citation style selection - show only local files + download option
    print(box_top("Citation Style Selection"))
    local_styles = list_local_csl_files()  # Returns [(key, name, path), ...]
    
    if local_styles:
        for i, (key, name, _) in enumerate(local_styles, 1):
            marker = " (current)" if key == defaults['citation_style'] else ""
            print(box_row(f"{i:2}) {name}{marker}"))
        print(box_row(f"{len(local_styles)+1:2}) Download by Zotero style ID or URL"))
    else:
        print(box_row("   No citation styles installed yet"))
        print(box_row(" 1) Download by Zotero style ID or URL"))
    print(box_bottom())
    
    max_choice = len(local_styles) + 1 if local_styles else 1
    style_choice = input(f"Select style [1-{max_choice}, Enter=keep current]: ").strip()
    if style_choice:
        try:
            idx = int(style_choice) - 1
            if local_styles and 0 <= idx < len(local_styles):
                defaults['citation_style'] = local_styles[idx][0]
            elif idx == len(local_styles) if local_styles else idx == 0:
                # Download option
                print("│   Find styles at: https://www.zotero.org/styles")
                ident = input("│  Enter Zotero style ID or URL: ").strip()
                if ident:
                    csl_path = download_csl_from_identifier(ident)
                    if csl_path:
                        csl_key = Path(csl_path).stem
                        defaults['citation_style'] = csl_key
        except (ValueError, IndexError):
            pass
    
    print()
    save_defaults(defaults)
    print("✓ Defaults saved successfully!")
    input("Press Enter to continue...")


def interactive_menu() -> Dict[str, Any]:
    """Display interactive menu and return configuration."""
    print_header()
    
    # Check if we have a last build for quick build
    last_config = load_last_config()
    
    # Main menu
    print(box_top("Main Menu"))
    print(box_row("1) Build Document"))
    print(box_row("2) Quick Build (Repeat Last Build)"))
    print(box_row("3) Configure Style/Citation Defaults"))
    print(box_bottom())
    
    main_choice = input("Select option [1-3]: ").strip()
    
    if main_choice == "3":
        configure_defaults()
        return interactive_menu()  # Show menu again after configuring
    
    if main_choice == "2":
        # Quick build - use last configuration
        if last_config:
            print()
            print(box_top("Quick Build"))
            source = last_config.get('source_file', last_config.get('doc_type', 'unknown'))
            print(box_row(f"Last build: {source} → {last_config.get('profile', 'pdf-default')}"))
            print(box_bottom())
            
            # Show build summary
            print()
            print_build_summary(last_config)
            print()
            
            # Ask for confirmation
            confirm = input("Continue with these settings? [Y/n]: ").strip().lower()
            if confirm == 'n':
                print()
                return interactive_menu()
            
            return last_config
        else:
            print()
            print(box_top("Quick Build"))
            print(box_row("No previous build found. Please build a document first."))
            print(box_bottom())
            input("Press Enter to continue...")
            return interactive_menu()
    
    # Document selection - list all markdown files
    md_files = list_markdown_files()
    if not md_files:
        print("No markdown files found in the current directory.")
        sys.exit(1)
    
    print(box_top("Select Document"))
    for i, f in enumerate(md_files, 1):
        print(box_row(f"{i:2}) {f}"))
    print(box_bottom())
    doc_choice = input(f"Select document [1-{len(md_files)}]: ").strip()
    try:
        doc_idx = int(doc_choice) - 1
        source_file = md_files[doc_idx]
    except (ValueError, IndexError):
        source_file = md_files[0]  # default to first file
    print()
    
    # Format selection
    print(box_top("Output Format"))
    print(box_row("1) Word Document (DOCX)"))
    print(box_row("2) PDF"))
    print(box_bottom())
    fmt_choice = input("Select format [1-2]: ").strip()
    fmt = "docx" if fmt_choice == "1" else "pdf"
    print()
    
    # Profile selection (skip for DOCX since there's only one)
    if fmt == "docx":
        profile = "docx-manuscript"
    else:
        print(box_top("Output Profile"))
        all_profiles = []
        idx = 1
        for category, profiles in get_profile_categories().items():
            print(box_row(f"{category}:"))
            for profile in profiles:
                name, description, profile_fmt = get_profile_info(profile)
                if profile_fmt == fmt:
                    all_profiles.append(profile)
                    print(box_row(f"  {idx:2}) {name}"))
                    idx += 1
        print(box_bottom())
        
        profile_choice = input(f"Select profile [1-{len(all_profiles)}]: ").strip()
        try:
            profile_idx = int(profile_choice) - 1
            profile = all_profiles[profile_idx]
        except (ValueError, IndexError):
            print("Invalid choice, using default")
            profile = "pdf-default"
    
    print()
    
    # Load defaults
    defaults = load_defaults()
    
    # Additional options
    use_png = False
    include_si_refs = False
    
    # Frontmatter selection - list all markdown files plus "None" option
    print(box_top("Select Frontmatter"))
    print(box_row(f" 0) None (no frontmatter)"))
    for i, f in enumerate(md_files, 1):
        print(box_row(f"{i:2}) {f}"))
    print(box_bottom())
    fm_choice = input(f"Select frontmatter [0-{len(md_files)}]: ").strip()
    frontmatter_file = None
    try:
        fm_idx = int(fm_choice)
        if fm_idx > 0:
            frontmatter_file = md_files[fm_idx - 1]
    except (ValueError, IndexError):
        frontmatter_file = None
    print()
    
    print(box_top("Options"))
    
    # SI references option
    si_refs_choice = input("│  Include SI references in bibliography? [y/N]: ").strip().lower()
    include_si_refs = si_refs_choice == 'y'
    
    # If including SI refs, ask which file contains SI
    si_file = None
    if include_si_refs:
        print("│")
        print("│  Select SI file for reference extraction:")
        for i, f in enumerate(md_files, 1):
            print(f"│    {i:2}) {f}")
        si_choice = input(f"│  Select SI file [1-{len(md_files)}]: ").strip()
        try:
            si_idx = int(si_choice) - 1
            si_file = md_files[si_idx]
        except (ValueError, IndexError):
            si_file = SUPPINFO if Path(SUPPINFO).exists() else None
    
    if fmt == "docx":
        png_choice = input("│  Convert PDF figures to PNG? [y/N]: ").strip().lower()
        use_png = png_choice == 'y'
    
    # Ask if this is an SI document (for SI-specific formatting)
    is_si_choice = input("│  Apply SI formatting (S-prefixed figures/tables)? [y/N]: ").strip().lower()
    is_si = is_si_choice == 'y'

    print(box_bottom())
    
    return {
        "source_file": source_file,
        "frontmatter_file": frontmatter_file,
        "profile": profile,
        "use_png": use_png,
        "include_si_refs": include_si_refs,
        "si_file": si_file,
        "is_si": is_si,
        "font": defaults.get('font'),
        "fontsize": defaults.get('fontsize'),
        "citation_style": defaults.get('citation_style'),
    }


def parse_arguments() -> Tuple[Optional[Dict[str, Any]], bool, bool]:
    """Parse command line arguments. Returns (config, show_list, use_last)."""
    args = sys.argv[1:]
    
    if not args:
        return None, False, False
    
    if "--list" in args or "-l" in args:
        return None, True, False
    
    if "--last" in args:
        return None, False, True
    
    if "--help" in args or "-h" in args:
        print_help()
        sys.exit(0)
    
    # Parse explicit arguments
    config = {
        "source_file": "",
        "frontmatter_file": None,
        "profile": "pdf-default",
        "use_png": False,
        "include_si_refs": False,
        "si_file": None,
        "is_si": False,
        "font": None,
        "fontsize": None,
        "citation_style": None,
    }
    
    for arg in args:
        if arg.startswith("--source="):
            config["source_file"] = arg.split("=", 1)[1]
        elif arg.startswith("--frontmatter="):
            config["frontmatter_file"] = arg.split("=", 1)[1]
        elif arg.startswith("--profile="):
            config["profile"] = arg.split("=", 1)[1]
        elif arg.startswith("--font="):
            config["font"] = arg.split("=", 1)[1]
        elif arg.startswith("--fontsize="):
            config["fontsize"] = arg.split("=", 1)[1]
        elif arg.startswith("--csl="):
            config["citation_style"] = arg.split("=", 1)[1]
        elif arg.startswith("--si-file="):
            config["si_file"] = arg.split("=", 1)[1]
            config["include_si_refs"] = True
        elif arg == "--png":
            config["use_png"] = True
        elif arg == "--include-si-refs":
            config["include_si_refs"] = True
        elif arg == "--si":
            config["is_si"] = True
        # Legacy support for main|si
        elif arg == "main":
            config["source_file"] = MAINTEXT
        elif arg == "si":
            config["source_file"] = SUPPINFO
            config["is_si"] = True
    
    if config["source_file"]:
        return config, False, False
    
    return None, False, False


def print_help():
    """Print help message."""
    font_list = ", ".join(FONT_PRESETS.keys())
    # Get installed citation styles or show placeholder
    local_styles = list_local_csl_files()
    style_list = ", ".join(k for k, _, _ in local_styles) if local_styles else "install from zotero.org/styles"
    print(f"""
Manuscript Build System - Professional Cross-Platform Build Tool

Usage:
  python build.py                      Interactive mode
  python build.py --last               Repeat last build
  python build.py --list               List available profiles
  python build.py [options]            Command-line mode

Options:
  --source=FILE              Source markdown file to build
  --frontmatter=FILE         Frontmatter file to prepend (optional)
  --profile=NAME             Use specific profile (e.g., --profile=pdf-nature)
  --font=NAME                Override font ({font_list})
  --fontsize=SIZE            Override font size (9pt, 10pt, 11pt, 12pt)
  --csl=STYLE                Use citation style (installed: {style_list})
  --png                      Convert PDF figures to PNG (for DOCX)
  --include-si-refs          Include SI citations in bibliography
  --si-file=FILE             SI file for reference extraction
  --si                       Apply SI formatting (S-prefixed figures/tables)
  --list, -l                 List all available profiles
  --last                     Repeat last build configuration
  --help, -h                 Show this help message

  main|si                    Legacy: build 01_maintext.md or 02_supp_info.md

Examples:
  python build.py --source=01_maintext.md --frontmatter=00_frontmatter.md
  python build.py --source=my_draft.md --profile=pdf-nature --csl=nature
  python build.py --source=02_supp_info.md --si --profile=pdf-default
  python build.py main --profile=pdf-nature
  python build.py --last
""")


def main():
    """Main entry point."""
    create_export_dir()
    
    # Parse arguments
    config, show_list, use_last = parse_arguments()
    
    if show_list:
        print_profiles_list()
        sys.exit(0)
    
    if use_last:
        config = load_last_config()
        if not config:
            print("No previous build configuration found.")
            print("Run interactively first or specify options.")
            sys.exit(1)
        print_header()
        source = config.get('source_file', config.get('doc_type', 'unknown'))
        print(f"Repeating last build: {source} → {config['profile']}")
        print()
    
    if not config:
        config = interactive_menu()
    
    # Save configuration
    save_config(config)
    
    # Display build summary (skip if already shown in quick build)
    if not use_last:
        print()
        print_build_summary(config)
        print()
    
    # Build document
    build_document(
        config["source_file"],
        config["profile"],
        config["use_png"],
        config["include_si_refs"],
        config.get("frontmatter_file"),
        config.get("font"),
        config.get("fontsize"),
        config.get("citation_style"),
        config.get("si_file"),
        config.get("is_si", False),
    )
    
    print()
    print("✓ Build complete!")
    print()


if __name__ == "__main__":
    main()
