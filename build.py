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
CITATION_STYLES_DIR = "resources/citation_styles"

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

# Citation style URLs from Zotero Style Repository
CITATION_STYLES = {
    "nature": {
        "name": "Nature",
        "url": "https://www.zotero.org/styles/nature",
        "file": "nature.csl",
    },
    "science": {
        "name": "Science",
        "url": "https://www.zotero.org/styles/science",
        "file": "science.csl",
    },
    "cell": {
        "name": "Cell",
        "url": "https://www.zotero.org/styles/cell",
        "file": "cell.csl",
    },
    "plos": {
        "name": "PLOS",
        "url": "https://www.zotero.org/styles/plos",
        "file": "plos.csl",
    },
    "pnas": {
        "name": "PNAS",
        "url": "https://www.zotero.org/styles/pnas",
        "file": "pnas.csl",
    },
    "apa": {
        "name": "APA 7th Edition",
        "url": "https://www.zotero.org/styles/apa",
        "file": "apa.csl",
    },
    "vancouver": {
        "name": "Vancouver",
        "url": "https://www.zotero.org/styles/vancouver",
        "file": "vancouver.csl",
    },
    "chicago": {
        "name": "Chicago Author-Date",
        "url": "https://www.zotero.org/styles/chicago-author-date",
        "file": "chicago-author-date.csl",
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


def load_yaml_simple(filepath: str) -> Dict[str, Any]:
    """Simple YAML loader without external dependencies."""
    if not Path(filepath).exists():
        return {}
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Very basic YAML parsing for our config files
    result = {}
    current_key = None
    current_indent = 0
    list_mode = False
    
    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        
        # Count leading spaces
        indent = len(line) - len(line.lstrip())
        
        if ':' in stripped and not stripped.startswith('-'):
            key, _, value = stripped.partition(':')
            key = key.strip()
            value = value.strip()
            
            if value:
                # Remove quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                # Handle lists in bracket notation
                if value.startswith('[') and value.endswith(']'):
                    value = [v.strip().strip('"\'') for v in value[1:-1].split(',')]
                result[key] = value
            else:
                result[key] = {}
                current_key = key
    
    return result


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
    """Load last build configuration."""
    if Path(BUILD_CONFIG).exists():
        with open(BUILD_CONFIG, 'r') as f:
            return json.load(f)
    return None


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


def download_citation_style(style_key: str) -> Optional[str]:
    """Download a citation style from Zotero repository. Returns path to CSL file."""
    if style_key not in CITATION_STYLES:
        return None
    
    style_info = CITATION_STYLES[style_key]
    ensure_citation_styles_dir()
    
    csl_path = Path(CITATION_STYLES_DIR) / style_info["file"]
    
    # Check if already downloaded
    if csl_path.exists():
        return str(csl_path)
    
    # Download from Zotero
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
        return str(csl_path)
    except (urllib.error.URLError, urllib.error.HTTPError) as e:
        print(f"   Warning: Could not download citation style: {e}")
        return None


def resolve_citation_style(citation_style: str) -> Tuple[Optional[str], Optional[str]]:
    """Resolve citation style identifier to a CSL path and display name."""
    if not citation_style:
        return None, None

    style = citation_style.strip()

    # Built-in styles (downloaded on demand)
    if style in CITATION_STYLES:
        path = download_citation_style(style)
        return path, CITATION_STYLES[style]["name"]

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




def get_available_citation_styles() -> List[str]:
    """Get list of locally available citation styles."""
    ensure_citation_styles_dir()
    styles = []
    for key, info in CITATION_STYLES.items():
        csl_path = Path(CITATION_STYLES_DIR) / info["file"]
        if csl_path.exists():
            styles.append(key)
    return styles


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
        cleanup_temp_files(temp_merged, config_file)
        sys.exit(1)
    
    # Cleanup
    cleanup_temp_files(temp_merged, config_file)
    
    print(f"   ✓ {output_file} created")


def cleanup_temp_files(*files):
    """Remove temporary files."""
    for f in files:
        if f and Path(f).exists():
            os.remove(f)
    if Path(SI_HEADER).exists():
        os.remove(SI_HEADER)


def print_header():
    """Print application header."""
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║               Manuscript Build System                        ║")
    print("║           Cross-Platform • Multi-Profile                     ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()


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


def interactive_menu() -> Dict[str, Any]:
    """Display interactive menu and return configuration."""
    print_header()
    
    # Document selection
    print("┌─ Document ────────────────────────────────────────────────────┐")
    print("│  1) Main Text                                                 │")
    print("│  2) Supporting Information                                    │")
    print("└───────────────────────────────────────────────────────────────┘")
    doc_choice = input("Select document [1-2]: ").strip()
    doc_type = "main" if doc_choice == "1" else "si"
    print()
    
    # Format selection
    print("┌─ Output Format ────────────────────────────────────────────────┐")
    print("│  1) Word Document (DOCX)                                      │")
    print("│  2) PDF                                                       │")
    print("└───────────────────────────────────────────────────────────────┘")
    fmt_choice = input("Select format [1-2]: ").strip()
    fmt = "docx" if fmt_choice == "1" else "pdf"
    print()
    
    # For PDF: offer to repeat last build if available (PDF only)
    if fmt == "pdf":
        last_config = load_last_config()
        # Offer repeat if last build was PDF (allow switching between main/si)
        if last_config and last_config.get('profile', '').startswith('pdf-'):
            print("┌─ Quick Build ─────────────────────────────────────────────────┐")
            print(f"│  Last build: {last_config.get('doc_type', 'main').upper()} → {last_config.get('profile', 'pdf-default')}")
            print("└───────────────────────────────────────────────────────────────┘")
            repeat = input("\nRepeat last build? [Y/n]: ").strip().lower()
            if repeat != 'n':
                # Update doc_type to current selection, keep other settings
                config_to_repeat = last_config.copy()
                config_to_repeat['doc_type'] = doc_type
                # For SI document, force include_si_refs=False
                if doc_type == 'si':
                    config_to_repeat['include_si_refs'] = False
                return config_to_repeat
        print()
    
    # Profile selection (skip for DOCX since there's only one)
    if fmt == "docx":
        profile = "docx-manuscript"
    else:
        print("┌─ Output Profile ──────────────────────────────────────────────┐")
        all_profiles = []
        idx = 1
        for category, profiles in PROFILE_CATEGORIES.items():
            print(f"│  {category}:")
            for profile in profiles:
                name, description, profile_fmt = get_profile_info(profile)
                if profile_fmt == fmt:
                    all_profiles.append(profile)
                    print(f"│    {idx:2}) {name:<20} [{fmt.upper()}]")
                    idx += 1
        print("└───────────────────────────────────────────────────────────────┘")
        
        profile_choice = input(f"Select profile [1-{len(all_profiles)}]: ").strip()
        try:
            profile_idx = int(profile_choice) - 1
            profile = all_profiles[profile_idx]
        except (ValueError, IndexError):
            print("Invalid choice, using default")
            profile = "pdf-default"
    
    print()
    
    # Additional options
    use_png = False
    include_si_refs = False
    include_frontmatter = True
    font = None
    fontsize = None
    citation_style = None
    
    print("┌─ Options ─────────────────────────────────────────────────────┐")
    
    if fmt == "docx":
        png_choice = input("│  Convert PDF figures to PNG? [y/N]: ").strip().lower()
        use_png = png_choice == 'y'
    
    if doc_type == "main":
        si_choice = input("│  Include SI references in bibliography? [y/N]: ").strip().lower()
        include_si_refs = si_choice == 'y'
    
    fm_choice = input("│  Include frontmatter? [Y/n]: ").strip().lower()
    include_frontmatter = fm_choice != 'n'
    
    # Font selection for PDF
    if fmt == "pdf":
        customize = input("│  Customize font/citation style? [y/N]: ").strip().lower()
        if customize == 'y':
            print("│")
            print("│  Font:")
            font_keys = list(FONT_PRESETS.keys())
            for i, key in enumerate(font_keys, 1):
                print(f"│    {i}) {FONT_PRESETS[key]['name']}")
            font_choice = input(f"│  Select font [1-{len(font_keys)}, Enter=default]: ").strip()
            if font_choice:
                try:
                    font = font_keys[int(font_choice) - 1]
                except (ValueError, IndexError):
                    pass
            
            print("│")
            print("│  Font Size:")
            default_size = get_profile_default_fontsize(profile) if profile else None
            for i, size in enumerate(FONT_SIZES, 1):
                suffix = " (default)" if default_size and size == default_size else ""
                print(f"│    {i}) {size}{suffix}")
            default_hint = default_size if default_size else "profile default"
            size_choice = input(f"│  Select size [1-{len(FONT_SIZES)}, Enter={default_hint}]: ").strip()
            if size_choice:
                try:
                    fontsize = FONT_SIZES[int(size_choice) - 1]
                except (ValueError, IndexError):
                    pass
            
            print("│")
            print("│  Citation Style:")
            builtin = [(k, v["name"]) for k, v in CITATION_STYLES.items()]
            local = [(k, n) for (k, n, _) in list_local_csl_files() if k not in CITATION_STYLES]
            all_styles = builtin + local

            print("│    0) Default (from profile)")
            for i, (key, name) in enumerate(all_styles, 1):
                print(f"│    {i}) {name}")
            print(f"│    d) Download by Zotero style ID or URL")

            style_choice = input(f"│  Select style [0-{len(all_styles)} / d, Enter=default]: ").strip().lower()

            if style_choice == 'd':
                print("│   Find styles at: https://www.zotero.org/styles")
                ident = input("│  Enter Zotero style ID or URL: ").strip()
                if ident:
                    citation_style = ident
            elif style_choice and style_choice != "0":
                try:
                    citation_style = all_styles[int(style_choice) - 1][0]
                except (ValueError, IndexError):
                    pass
    
    print("└───────────────────────────────────────────────────────────────┘")
    
    return {
        "doc_type": doc_type,
        "profile": profile,
        "use_png": use_png,
        "include_si_refs": include_si_refs,
        "include_frontmatter": include_frontmatter,
        "font": font,
        "fontsize": fontsize,
        "citation_style": citation_style,
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
    
    # Display build summary
    _, profile_desc, fmt = get_profile_info(config["profile"])
    print()
    print("┌─ Build Configuration ────────────────────────────────────────┐")
    print(f"│  Document:     {config['doc_type'].upper():<45} │")
    print(f"│  Profile:      {config['profile']:<45} │")
    print(f"│  Format:       {fmt.upper():<45} │")
    print(f"│  Frontmatter:  {'Yes' if config['include_frontmatter'] else 'No':<45} │")
    if fmt == "docx":
        print(f"│  PNG Convert:  {'Yes' if config['use_png'] else 'No':<45} │")
    if config['doc_type'] == "main":
        print(f"│  SI Refs:      {'Yes' if config['include_si_refs'] else 'No':<45} │")
    if config.get('font'):
        font_name = FONT_PRESETS[config['font']]['name']
        print(f"│  Font:         {font_name:<45} │")

    # Always show font size for PDF (default from profile if not overridden)
    if fmt == "pdf":
        effective_size = config.get('fontsize') or get_profile_default_fontsize(config['profile'])
        if effective_size:
            print(f"│  Font Size:    {effective_size:<45} │")

    # Always show citation style (default base CSL if not overridden)
    if fmt in ("pdf", "docx"):
        if config.get('citation_style'):
            style_key = config['citation_style']
            if style_key in CITATION_STYLES:
                style_name = CITATION_STYLES[style_key]['name']
            else:
                style_name = str(style_key)
            print(f"│  Citation:     {style_name:<45} │")
        else:
            print(f"│  Citation:     {'Default (resources/citation_style.csl)':<45} │")
    print("└───────────────────────────────────────────────────────────────┘")
    print()
    
    # Build
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
