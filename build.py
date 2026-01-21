#!/usr/bin/env python3
"""
Manuscript Build System - Professional Cross-Platform Build Tool
Usage: python build.py [--last] [--profile NAME] [--list] [main|si] [--png] [--include-si-refs] [--no-frontmatter]
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

# Citation style URLs from Zotero Style Repository (alphabetical order)
CITATION_STYLES = {
    "acs-synthetic-biology": {
        "name": "ACS Synthetic Biology",
        "url": "https://www.zotero.org/styles/acs-synthetic-biology",
        "file": "acs-synthetic-biology.csl",
    },
    "angewandte-chemie": {
        "name": "Angewandte Chemie",
        "url": "https://www.zotero.org/styles/angewandte-chemie",
        "file": "angewandte-chemie.csl",
    },
    "apa": {
        "name": "APA 7th Edition",
        "url": "https://www.zotero.org/styles/apa",
        "file": "apa.csl",
    },
    "cell": {
        "name": "Cell",
        "url": "https://www.zotero.org/styles/cell",
        "file": "cell.csl",
    },
    "chicago": {
        "name": "Chicago Author-Date",
        "url": "https://www.zotero.org/styles/chicago-author-date",
        "file": "chicago-author-date.csl",
    },
    "nature": {
        "name": "Nature",
        "url": "https://www.zotero.org/styles/nature",
        "file": "nature.csl",
    },
    "nucleic-acids-research": {
        "name": "Nucleic Acids Research",
        "url": "https://www.zotero.org/styles/nucleic-acids-research",
        "file": "nucleic-acids-research.csl",
    },
    "pnas": {
        "name": "PNAS",
        "url": "https://www.zotero.org/styles/pnas",
        "file": "pnas.csl",
    },
    "plos": {
        "name": "PLOS",
        "url": "https://www.zotero.org/styles/plos",
        "file": "plos.csl",
    },
    "science": {
        "name": "Science",
        "url": "https://www.zotero.org/styles/science",
        "file": "science.csl",
    },
    "vancouver": {
        "name": "Vancouver",
        "url": "https://www.zotero.org/styles/vancouver",
        "file": "vancouver.csl",
    },
}

# Profile categories for menu display
PROFILE_CATEGORIES = {
    "General": ["docx-manuscript", "pdf-default", "pdf-draft", "pdf-two-column", "pdf-thesis"],
    "Journals": ["pdf-nature", "pdf-cell"],
}

# Map profiles to their recommended citation styles
PROFILE_CITATION_STYLES = {
    "pdf-nature": "nature",
    "pdf-cell": "cell",
}


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
    """Resolve citation style identifier to a CSL path and display name."""
    if not citation_style:
        return None, None

    style = citation_style.strip()

    # Built-in styles (downloaded on demand)
    if style in CITATION_STYLES:
        style_info = CITATION_STYLES[style]
        ensure_citation_styles_dir()
        csl_path = Path(CITATION_STYLES_DIR) / style_info["file"]
        
        # Download if not exists
        if not csl_path.exists():
            print(f"   Downloading {style_info['name']} citation style...")
            try:
                # Zotero redirects to raw CSL, follow redirects
                url = style_info["url"]
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    csl_content = response.read()
                
                with open(csl_path, "wb") as f:
                    f.write(csl_content)
                
                print(f"   ✓ Downloaded {style_info['file']}")
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                print(f"   Warning: Could not download citation style: {e}")
                return None
        
        return str(csl_path), style_info["name"]

    # Local styles by stem or filename
    ensure_citation_styles_dir()
    candidate_files = [style]
    if not style.lower().endswith('.csl'):
        candidate_files.append(style + '.csl')
    for cand in candidate_files:
        p = Path(CITATION_STYLES_DIR) / cand
        if p.exists():
            return str(p), _extract_csl_title(p)

    # Treat anything else as Zotero style ID or URL
    path = download_csl_from_identifier(style)
    if path:
        return path, _extract_csl_title(Path(path))
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


def extract_si_citations() -> str:
    """Extract literature citations from SI file, excluding cross-references."""
    if not Path(SUPPINFO).exists():
        return ""
    
    with open(SUPPINFO, "r") as f:
        content = f.read()
    
    citations = set(re.findall(r"@[a-zA-Z][a-zA-Z0-9_:-]*", content))
    excluded = {"@Fig:", "@Tbl:", "@email"}
    filtered = [c for c in citations if not any(c.startswith(e.rstrip(":")) for e in excluded)]
    
    return "; ".join(sorted(filtered))


def build_document(doc_type: str, profile: str, use_png: bool, include_si_refs: bool, 
                   include_frontmatter: bool, font: Optional[str] = None, 
                   fontsize: Optional[str] = None, citation_style: Optional[str] = None):
    """Build the document with specified profile."""
    # Get profile info
    _, _, fmt = get_profile_info(profile)
    
    # Determine source and output files
    if doc_type == "main":
        source_file = MAINTEXT
        output_name = "01_maintext"
    else:
        source_file = SUPPINFO
        output_name = "02_supp_info"
    
    output_file = f"{EXPORT_DIR}/{output_name}.{fmt}"
    temp_merged = f"_temp_{doc_type}_merged.md"
    
    print(f">> Building {doc_type.title()} ({fmt.upper()})...")
    
    # Merge frontmatter if requested
    input_file = source_file
    if include_frontmatter and Path(FRONTMATTER).exists():
        print(f"   Merging frontmatter from {FRONTMATTER}...")
        with open(temp_merged, "w") as out:
            with open(FRONTMATTER, "r") as f:
                out.write(f.read())
            out.write("\n")
            with open(source_file, "r") as f:
                out.write(f.read())
        input_file = temp_merged
    
    # Include SI refs for main document
    if doc_type == "main" and include_si_refs:
        print("   Including SI references in bibliography...")
        if not include_frontmatter:
            shutil.copy(source_file, temp_merged)
            input_file = temp_merged
        
        si_cites = extract_si_citations()
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
    if doc_type == "si":
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
    print(box_row(f"Document:     {config['doc_type'].upper()}"))
    print(box_row(f"Profile:      {config['profile']}"))
    print(box_row(f"Format:       {fmt.upper()}"))
    print(box_row(f"Frontmatter:  {'Yes' if config['include_frontmatter'] else 'No'}"))
    if fmt == "docx":
        print(box_row(f"PNG Convert:  {'Yes' if config['use_png'] else 'No'}"))
    if config['doc_type'] == "main":
        print(box_row(f"SI Refs:      {'Yes' if config['include_si_refs'] else 'No'}"))
    elif config['doc_type'] == "both":
        print(box_row("SI Refs:      Yes for Main, No for SI"))
    if fmt == "pdf" and config.get('font'):
        font_name = FONT_PRESETS[config['font']]['name']
        print(box_row(f"Font:         {font_name}"))
    if fmt == "pdf" and config.get('fontsize'):
        print(box_row(f"Font Size:    {config['fontsize']}"))
    if fmt in ("pdf", "docx") and config.get('citation_style'):
        style_key = config['citation_style']
        if style_key in CITATION_STYLES:
            style_name = CITATION_STYLES[style_key]['name']
        else:
            style_name = str(style_key)
        print(box_row(f"Citation:     {style_name}"))
    print(box_bottom())


def print_profiles_list():
    """Print available profiles organized by category."""
    print("\nAvailable Profiles:")
    print("─" * 50)
    
    for category, profiles in PROFILE_CATEGORIES.items():
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
    style_name = CITATION_STYLES.get(defaults['citation_style'], {}).get('name', defaults['citation_style'])
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
    
    # Citation style selection
    print(box_top("Citation Style Selection"))
    builtin = [(k, v["name"]) for k, v in CITATION_STYLES.items()]
    local = [(k, n) for (k, n, _) in list_local_csl_files() if k not in CITATION_STYLES]
    all_styles = builtin + local
    
    for i, (key, name) in enumerate(all_styles, 1):
        marker = " (current)" if key == defaults['citation_style'] else ""
        print(box_row(f"{i:2}) {name}{marker}"))
    print(box_row(f"{len(all_styles)+1:2}) Download by Zotero style ID or URL"))
    print(box_bottom())
    
    style_choice = input(f"Select style [1-{len(all_styles)+1}, Enter=keep current]: ").strip()
    if style_choice:
        try:
            idx = int(style_choice) - 1
            if 0 <= idx < len(all_styles):
                defaults['citation_style'] = all_styles[idx][0]
            elif idx == len(all_styles):
                # Download option
                print("│   Find styles at: https://www.zotero.org/styles")
                ident = input("│  Enter Zotero style ID or URL: ").strip()
                if ident:
                    # Download and use the style
                    csl_path = download_csl_from_identifier(ident)
                    if csl_path:
                        # Extract the key from the downloaded file
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
            print(box_row(f"Last build: {last_config.get('doc_type', 'main').upper()} → {last_config.get('profile', 'pdf-default')}"))
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
    
    # Document selection
    print(box_top("Document"))
    print(box_row("1) Main Text"))
    print(box_row("2) Supporting Information"))
    print(box_row("3) Both (Main Text + Supporting Information)"))
    print(box_bottom())
    doc_choice = input("Select document [1-3]: ").strip()
    if doc_choice == "1":
        doc_type = "main"
    elif doc_choice == "2":
        doc_type = "si"
    elif doc_choice == "3":
        doc_type = "both"
    else:
        doc_type = "main"  # default
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
        for category, profiles in PROFILE_CATEGORIES.items():
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
    include_frontmatter = True
    
    print(box_top("Options"))
    
    # Frontmatter option
    frontmatter_choice = input("│  Include frontmatter? [Y/n]: ").strip().lower()
    include_frontmatter = frontmatter_choice != 'n'
    
    # SI references option (for main text or both documents)
    if doc_type in ("main", "both"):
        si_refs_choice = input("│  Include SI references in bibliography? [y/N]: ").strip().lower()
        include_si_refs = si_refs_choice == 'y'
    
    if fmt == "docx":
        png_choice = input("│  Convert PDF figures to PNG? [y/N]: ").strip().lower()
        use_png = png_choice == 'y'

    print(box_bottom())
    
    return {
        "doc_type": doc_type,
        "profile": profile,
        "use_png": use_png,
        "include_si_refs": include_si_refs,
        "include_frontmatter": include_frontmatter,
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
        "doc_type": "",
        "profile": "pdf-default",
        "use_png": False,
        "include_si_refs": False,
        "include_frontmatter": True,
        "font": None,
        "fontsize": None,
        "citation_style": None,
    }
    
    for arg in args:
        if arg in ("main", "si"):
            config["doc_type"] = arg
        elif arg.startswith("--profile="):
            config["profile"] = arg.split("=", 1)[1]
        elif arg.startswith("--font="):
            config["font"] = arg.split("=", 1)[1]
        elif arg.startswith("--fontsize="):
            config["fontsize"] = arg.split("=", 1)[1]
        elif arg.startswith("--csl="):
            config["citation_style"] = arg.split("=", 1)[1]
        elif arg == "--png":
            config["use_png"] = True
        elif arg == "--include-si-refs":
            config["include_si_refs"] = True
        elif arg == "--no-frontmatter":
            config["include_frontmatter"] = False
    
    if config["doc_type"]:
        return config, False, False
    
    return None, False, False


def print_help():
    """Print help message."""
    font_list = ", ".join(FONT_PRESETS.keys())
    style_list = ", ".join(CITATION_STYLES.keys())
    print(f"""
Manuscript Build System - Professional Cross-Platform Build Tool

Usage:
  python build.py                      Interactive mode
  python build.py --last               Repeat last build
  python build.py --list               List available profiles
  python build.py [options]            Command-line mode

Options:
  main|si                    Document type (main text or supporting info)
  --profile=NAME             Use specific profile (e.g., --profile=pdf-nature)
  --font=NAME                Override font ({font_list})
  --fontsize=SIZE            Override font size (9pt, 10pt, 11pt, 12pt)
  --csl=STYLE                Use citation style ({style_list})
  --png                      Convert PDF figures to PNG (for DOCX)
  --include-si-refs          Include SI citations in main bibliography
  --no-frontmatter           Skip frontmatter merging
  --list, -l                 List all available profiles
  --last                     Repeat last build configuration
  --help, -h                 Show this help message

Examples:
  python build.py main --profile=pdf-nature
  python build.py main --profile=pdf-default --font=palatino --csl=nature
  python build.py si --profile=docx-manuscript --png
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
        print(f"Repeating last build: {config['doc_type'].upper()} → {config['profile']}")
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
    
    # Build
    if config["doc_type"] == "both":
        # Build both documents
        print("Building Main Text...")
        build_document(
            "main",
            config["profile"],
            config["use_png"],
            config["include_si_refs"],
            config["include_frontmatter"],
            config.get("font"),
            config.get("fontsize"),
            config.get("citation_style"),
        )
        print()
        print("Building Supporting Information...")
        build_document(
            "si",
            config["profile"],
            config["use_png"],
            False,  # Never include SI refs for SI document
            config["include_frontmatter"],
            config.get("font"),
            config.get("fontsize"),
            config.get("citation_style"),
        )
    else:
        # Build single document
        build_document(
            config["doc_type"],
            config["profile"],
            config["use_png"],
            config["include_si_refs"],
            config["include_frontmatter"],
            config.get("font"),
            config.get("fontsize"),
            config.get("citation_style"),
        )
    
    print()
    print("✓ Build complete!")
    print()


if __name__ == "__main__":
    main()
