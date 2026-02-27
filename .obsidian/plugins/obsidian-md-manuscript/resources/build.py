#!/usr/bin/env python3
"""
Manuscript Build System - Professional Cross-Platform Build Tool
Usage: python build.py [--last] [--profile NAME] [--list] [--source=FILE] [--frontmatter=FILE] [--png] [--si]
"""

import subprocess
import sys
# Force UTF-8 output to fix Windows console crashes
if sys.version_info >= (3, 7):
    sys.stdout.reconfigure(encoding='utf-8')
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
# Determine script location for relative resource loading
SCRIPT_DIR = Path(__file__).parent.resolve()

FRONTMATTER = "00_frontmatter.md"
MAINTEXT = "01_maintext.md"
SUPPINFO = "02_supp_info.md"
PROFILES_DIR = SCRIPT_DIR / "profiles"
BASE_PROFILE = SCRIPT_DIR / "profiles" / "_base.yaml"
LUA_FILTER = SCRIPT_DIR / "pdf2png.lua"
SI_HEADER = "_si_header.tex"
EXPORT_DIR = "export"
BUILD_CONFIG = ".build_config.json"
DEFAULTS_CONFIG = ".defaults_config.json"
CITATION_STYLES_DIR = SCRIPT_DIR / "citation_styles"

# Default settings when nothing is configured
DEFAULT_SETTINGS = {
    "font": "libertinus",
    "fontsize": "11pt",
    "citation_style": "vancouver",
    "linespacing": "",
    "paragraph_style": "",
    "linenumbers": None,
    "pagenumbers": None,
    "numbered_headings": None,
    "language": "",
    "figure_format": "png",
    "figure_background": "white"
}

# Figure format presets for flattened markdown export
FIGURE_FORMAT_PRESETS = {
    "png": {"name": "PNG", "ext": "png"},
    "webp": {"name": "WebP", "ext": "webp"},
    "jpg": {"name": "JPEG", "ext": "jpg"},
    "original": {"name": "Keep Original", "ext": None}
}

# Figure background presets
FIGURE_BACKGROUND_PRESETS = {
    "white": {"name": "White", "color": "white"},
    "transparent": {"name": "Transparent", "color": "none"}
}

# Font presets for PDF output
FONT_PRESETS = {
    "libertinus": {
        "name": "Libertinus (Default)",
        "mainfont": "Libertinus Serif",
        "sansfont": "Libertinus Sans",
        "monofont": "Libertinus Mono",
    },
    "libertinus-serif": {
        "name": "Libertinus Serif",
        "mainfont": "Libertinus Serif",
        "sansfont": "Libertinus Sans",
        "monofont": "Libertinus Mono",
    },
    "libertinus-sans": {
        "name": "Libertinus Sans",
        "mainfont": "Libertinus Sans",
        "sansfont": "Libertinus Sans",
        "monofont": "Libertinus Mono",
    },
    "inter": {
        "name": "Inter",
        "mainfont": "Inter",
        "sansfont": "Inter",
        "monofont": "Libertinus Mono",
    },
    "ibm-plex-sans": {
        "name": "IBM Plex Sans",
        "mainfont": "IBM Plex Sans",
        "sansfont": "IBM Plex Sans",
        "monofont": "IBM Plex Mono",
    },
    "ibm-plex-serif": {
        "name": "IBM Plex Serif",
        "mainfont": "IBM Plex Serif",
        "sansfont": "IBM Plex Sans",
        "monofont": "IBM Plex Mono",
    },
    "switzer": {
        "name": "Switzer",
        "mainfont": "Switzer",
        "sansfont": "Switzer",
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
        "name": "LaTeX Default (Compatibility)",
    },
}

# Line spacing presets
LINE_SPACING_PRESETS = {
    "single": {"value": "1.0", "name": "Single (1.0)"},
    "compact": {"value": "1.15", "name": "Compact (1.15)"},
    "normal": {"value": "1.25", "name": "Normal (1.25)"},
    "relaxed": {"value": "1.5", "name": "Relaxed (1.5)"},
    "double": {"value": "2.0", "name": "Double (2.0)"},
}

# Paragraph style presets
PARAGRAPH_STYLE_PRESETS = {
    "indent": {"indent": True, "name": "Indented (American)"},
    "gap": {"indent": False, "name": "Gap (European)"},
    "both": {"indent": True, "name": "Gap + Indent (Both)"},
}

# Numbered headings presets
NUMBERED_HEADINGS_PRESETS = {
    "on": {"value": True, "name": "Numbered"},
    "off": {"value": False, "name": "Unnumbered"},
}

# Paper size presets
PAPER_SIZE_PRESETS = {
    "a4": "A4",
    "letter": "US Letter",
}

# Language presets (ISO 639-1 codes)
LANGUAGE_PRESETS = {
    "en": "English",
    "de": "German (Deutsch)",
    "fr": "French (Français)",
    "es": "Spanish (Español)",
    "it": "Italian (Italiano)",
    "pt": "Portuguese (Português)",
    "nl": "Dutch (Nederlands)",
    "pl": "Polish (Polski)",
    "ru": "Russian (Русский)",
    "zh": "Chinese (中文)",
    "ja": "Japanese (日本語)",
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

FONT_SIZES = ["9pt", "10pt", "11pt", "12pt", "13pt", "14pt", "15pt", "16pt"]


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
    
    # Rewrite "resources/" paths to absolute SCRIPT_DIR paths
    # This ensures resources are found even if the script/resources are moved (e.g. to a plugin folder)
    resource_replacement = str(SCRIPT_DIR).replace("\\", "/") + "/"
    
    if Path(base_path).exists():
        with open(base_path, 'r') as f:
            base_content = f.read().replace("resources/", resource_replacement)
    
    if Path(profile_path).exists():
        with open(profile_path, 'r') as f:
            profile_content = f.read().replace("resources/", resource_replacement)
    
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


def strip_font_variables_from_defaults_file(defaults_path: str) -> None:
    path = Path(defaults_path)
    if not path.exists():
        return

    lines = path.read_text().splitlines(True)

    variables_idx = None
    variables_indent = None
    for i, line in enumerate(lines):
        if line.strip() == "variables:":
            variables_idx = i
            variables_indent = len(line) - len(line.lstrip())
            break

    if variables_idx is None or variables_indent is None:
        return

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

    keys_to_remove = {"mainfont:", "sansfont:", "monofont:"}
    new_block: List[str] = []
    for line in lines[variables_idx + 1 : end_idx]:
        stripped = line.strip()
        if any(stripped.startswith(k) for k in keys_to_remove):
            continue
        new_block.append(line)

    out = []
    out.extend(lines[: variables_idx + 1])
    out.extend(new_block)
    out.extend(lines[end_idx:])
    path.write_text(''.join(out))


def convert_tex_file_to_body_only(tex_path: str) -> None:
    path = Path(tex_path)
    if not path.exists():
        return

    text = path.read_text()

    begin = "\\begin{document}"
    end = "\\end{document}"

    begin_idx = text.find(begin)
    end_idx = text.rfind(end)
    if begin_idx == -1 or end_idx == -1 or end_idx <= begin_idx:
        return

    body = text[begin_idx + len(begin) : end_idx]
    body = body.lstrip("\r\n")
    body = body.rstrip() + "\n"
    path.write_text(body)


def apply_font_overrides_to_defaults_file(
    defaults_path: str,
    font: Optional[str] = None,
    fontsize: Optional[str] = None,
    linespacing: Optional[str] = None,
    paragraph_style: Optional[str] = None,
    linenumbers: Optional[bool] = None,
    pagenumbers: Optional[bool] = None,
    numbered_headings: Optional[bool] = None,
    language: Optional[str] = None,
    papersize: Optional[str] = None,
    margin_top: Optional[str] = None,
    margin_bottom: Optional[str] = None,
    margin_left: Optional[str] = None,
    margin_right: Optional[str] = None,
) -> None:
    """Apply font/fontsize/linespacing/paragraph style/headings/language overrides to Pandoc defaults file.

    This avoids situations where multiple settings (from profile + CLI)
    end up concatenated in the generated LaTeX.
    """
    # Check if we have explicit overrides or titlesec conflicts
    has_explicit_overrides = any([font, fontsize, linespacing, paragraph_style, linenumbers is not None, pagenumbers is not None, numbered_headings is not None, language, papersize, margin_top, margin_bottom, margin_left, margin_right])
    has_titlesec_conflict = _profile_uses_titlesec_paragraph(defaults_path)
    
    if not (has_explicit_overrides or has_titlesec_conflict):
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
            
    if variables_idx is not None:
        print(f"DEBUG: Found variables block at line {variables_idx}")

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

    # Remove existing keys we're overriding inside the variables block.
    keys_to_remove = set()
    if font:
        keys_to_remove.update({"mainfont:", "sansfont:", "monofont:"})
    if fontsize:
        keys_to_remove.add("fontsize:")
    if linespacing:
        keys_to_remove.add("linestretch:")
    if paragraph_style:
        keys_to_remove.add("indent:")
    if numbered_headings is not None:
        keys_to_remove.add("numbersections:")
    if language:
        keys_to_remove.add("lang:")
    if papersize:
        keys_to_remove.add("papersize:")
    if any([margin_top, margin_bottom, margin_left, margin_right]):
        keys_to_remove.add("geometry:")
    
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
        if all(k in font_info for k in ("mainfont", "sansfont", "monofont")):
            override_lines.extend(
                [
                    f"{child_indent_str}mainfont: \"{font_info['mainfont']}\"\n",
                    f"{child_indent_str}sansfont: \"{font_info['sansfont']}\"\n",
                    f"{child_indent_str}monofont: \"{font_info['monofont']}\"\n",
                ]
            )
    if fontsize:
        override_lines.append(f"{child_indent_str}fontsize: {fontsize}\n")
    if linespacing and linespacing in LINE_SPACING_PRESETS:
        spacing_value = LINE_SPACING_PRESETS[linespacing]["value"]
        override_lines.append(f"{child_indent_str}linestretch: {spacing_value}\n")
    if paragraph_style and paragraph_style in PARAGRAPH_STYLE_PRESETS:
        indent_value = "true" if PARAGRAPH_STYLE_PRESETS[paragraph_style]["indent"] else "false"
        override_lines.append(f"{child_indent_str}indent: {indent_value}\n")
    if numbered_headings is not None:
        override_lines.append(f"{child_indent_str}numbersections: {'true' if numbered_headings else 'false'}\n")
    if language and language in LANGUAGE_PRESETS:
        override_lines.append(f"{child_indent_str}lang: {language}\n")
    if papersize and papersize in PAPER_SIZE_PRESETS:
        override_lines.append(f"{child_indent_str}papersize: {papersize}\n")
    if any([margin_top, margin_bottom, margin_left, margin_right]):
        override_lines.append(f"{child_indent_str}geometry:\n")
        if margin_top:
            override_lines.append(f"{child_indent_str}  - top={margin_top}\n")
        if margin_bottom:
            override_lines.append(f"{child_indent_str}  - bottom={margin_bottom}\n")
        if margin_left:
            override_lines.append(f"{child_indent_str}  - left={margin_left}\n")
        if margin_right:
            override_lines.append(f"{child_indent_str}  - right={margin_right}\n")

    # Write back file: keep everything, but replace variables block content.
    out = []
    out.extend(lines[: variables_idx + 1])
    out.extend(override_lines)
    out.extend(new_block)
    out.extend(lines[end_idx:])
    
    path.write_text(''.join(out))
    
    # Handle line numbers - need to modify header-includes
    if linenumbers is not None:
        _apply_linenumbers_override(defaults_path, linenumbers)
    
    # Handle paragraph style - need to modify parindent/parskip in header-includes
    # Also handle titlesec conflicts even if no explicit paragraph style is set
    uses_titlesec = _profile_uses_titlesec_paragraph(defaults_path)
    if paragraph_style or uses_titlesec:
        # If no explicit style, use empty string to indicate "profile default"
        effective_style = paragraph_style if paragraph_style else ""
        _apply_paragraph_style_override(defaults_path, effective_style)
    
    # Handle page numbers - need to modify header-includes
    if pagenumbers is not None:
        _apply_pagenumbers_override(defaults_path, pagenumbers)


def _apply_linenumbers_override(defaults_path: str, enable: bool) -> None:
    r"""Add or remove \linenumbers from header-includes inside variables block."""
    path = Path(defaults_path)
    if not path.exists():
        return
    
    content = path.read_text()
    lines = content.splitlines(True)
    
    # First, remove any existing lineno-related lines
    new_lines = []
    for line in lines:
        if r'\usepackage{lineno}' in line or r'\linenumbers' in line:
            continue
        new_lines.append(line)
    
    if enable:
        # Add \usepackage{lineno} and \linenumbers to header-includes inside variables block
        result_lines = []
        in_variables = False
        in_header_includes = False
        added = False
        
        for line in new_lines:
            result_lines.append(line)
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            
            if stripped == "variables:":
                in_variables = True
            elif in_variables and stripped == "header-includes:":
                in_header_includes = True
            elif in_header_includes and not added:
                if stripped.startswith("- "):
                    item_indent = indent
                    indent_str = " " * item_indent
                    # Add both usepackage and linenumbers command
                    result_lines.insert(-1, f"{indent_str}- \\usepackage{{lineno}}\n")
                    result_lines.insert(-1, f"{indent_str}- \\linenumbers\n")
                    added = True
                    in_header_includes = False
        
        if added:
            path.write_text(''.join(result_lines))
    else:
        # Just write back the file with lineno lines removed
        path.write_text(''.join(new_lines))


def _apply_pagenumbers_override(defaults_path: str, enable: bool) -> None:
    """Add or remove page numbering from header-includes inside variables block."""
    path = Path(defaults_path)
    if not path.exists():
        return
    
    content = path.read_text()
    lines = content.splitlines(True)
    
    # First, remove any existing page numbering related lines
    new_lines = []
    for line in lines:
        if r'\pagenumbering{gobble}' in line or r'\pagenumbering{arabic}' in line:
            continue
        new_lines.append(line)
    
    # If disabling page numbers, add \pagenumbering{gobble}
    # If enabling explicitly, add \pagenumbering{arabic}
    result_lines = []
    in_variables = False
    in_header_includes = False
    added = False
    
    for line in new_lines:
        result_lines.append(line)
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        
        if stripped == "variables:":
            in_variables = True
        elif in_variables and stripped == "header-includes:":
            in_header_includes = True
        elif in_header_includes and not added:
            if stripped.startswith("- "):
                item_indent = indent
                indent_str = " " * item_indent
                injection = r"\pagenumbering{arabic}" if enable else r"\pagenumbering{gobble}"
                result_lines.insert(-1, f"{indent_str}- {injection}\n")
                added = True
                in_header_includes = False
    
    if added:
        path.write_text(''.join(result_lines))
    else:
        path.write_text(''.join(new_lines))


def _normalize_inline_parindent_for_gap(markdown_path: str) -> None:
    path = Path(markdown_path)
    if not path.exists():
        return

    content = path.read_text()

    content = re.sub(
        r"`\\setlength\{\\parindent\}\{[^}]+\}`\{=latex\}",
        r"`\\setlength{\\parindent}{0pt}`{=latex}",
        content,
    )

    def _rewrite_raw_latex_block(match: re.Match) -> str:
        block = match.group(0)
        return re.sub(
            r"\\setlength\{\\parindent\}\{[^}]+\}",
            r"\\setlength{\\parindent}{0pt}",
            block,
        )

    content = re.sub(
        r"```\{=latex\}[\s\S]*?```",
        _rewrite_raw_latex_block,
        content,
    )

    content = re.sub(
        r":::\s*\{=latex\}[\s\S]*?:::",
        _rewrite_raw_latex_block,
        content,
    )
    path.write_text(content)


def _profile_uses_gap_paragraphs(defaults_path: str) -> bool:
    path = Path(defaults_path)
    if not path.exists():
        return False

    lines = path.read_text().splitlines()
    in_variables = False
    for line in lines:
        stripped = line.strip()
        if stripped == "variables:":
            in_variables = True
            continue
        if in_variables and stripped and not stripped.startswith("#"):
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                in_variables = False
                continue
            if stripped.startswith("indent:"):
                value = stripped.split(":", 1)[1].strip().lower()
                return value == "false"
    return False


def _profile_uses_titlesec_paragraph(defaults_path: str) -> bool:
    """Check if profile uses titlesec package for paragraph formatting."""
    path = Path(defaults_path)
    if not path.exists():
        return False
    
    content = path.read_text()
    return r'\usepackage{titlesec}' in content and r'\titleformat{\paragraph}' in content


def _apply_paragraph_style_override(defaults_path: str, style: str) -> None:
    """Modify parindent/parskip in header-includes inside variables block.
    
    Adds settings at END of header-includes to ensure they override profile defaults.
    Also removes conflicting \renewcommand{\paragraph} when titlesec is used.
    """
    path = Path(defaults_path)
    if not path.exists():
        return
    
    content = path.read_text()
    lines = content.splitlines(True)
    
    # Check if this profile uses titlesec for paragraph formatting
    uses_titlesec = _profile_uses_titlesec_paragraph(defaults_path)
    
    # Remove existing parindent/parskip lines and conflicting paragraph commands
    new_lines = []
    for line in lines:
        if r'\setlength{\parindent}' in line or r'\setlength{\parskip}' in line:
            continue
        if r'\AtBeginDocument' in line and (r'\parindent' in line or r'\parskip' in line):
            continue
        if r'\usepackage{parskip}' in line:
            continue
        # Remove conflicting \renewcommand{\paragraph} when titlesec is used
        if uses_titlesec and r'\renewcommand{\paragraph}' in line:
            continue
        if uses_titlesec and r'\renewcommand{\subparagraph}' in line:
            continue
        new_lines.append(line)
    
    # Find the LAST item in header-includes inside variables block
    # and add our settings AFTER it (at end of header-includes)
    in_variables = False
    in_header_includes = False
    last_header_item_idx = -1
    item_indent = 4  # default
    
    for i, line in enumerate(new_lines):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        
        if stripped == "variables:":
            in_variables = True
        elif in_variables and stripped == "header-includes:":
            in_header_includes = True
        elif in_header_includes:
            if stripped.startswith("- "):
                last_header_item_idx = i
                item_indent = indent
            elif stripped and not stripped.startswith("#") and not stripped.startswith("-") and not stripped.startswith("|"):
                # End of header-includes block (new key at same or lower indent)
                if indent <= item_indent - 2:
                    in_header_includes = False
    
    if last_header_item_idx > 0:
        indent_str = " " * item_indent
        if style == "indent":
            injection = r"\AtBeginDocument{\setlength{\parindent}{1.5em}\setlength{\parskip}{0pt}}"
        elif style == "both":
            injection = r"\AtBeginDocument{\setlength{\parindent}{1.5em}\setlength{\parskip}{0.5\baselineskip}}"
        else:
            injection = r"\AtBeginDocument{\setlength{\parindent}{0pt}\setlength{\parskip}{0.5\baselineskip}}"

        if style == "gap":
            new_lines.insert(last_header_item_idx + 1, f"{indent_str}- \\usepackage{{parskip}}\n")
            last_header_item_idx += 1

        new_lines.insert(last_header_item_idx + 1, f"{indent_str}- {injection}\n")
        
        path.write_text(''.join(new_lines))


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


def create_si_header(pagenumbers: Optional[bool] = None):
    """Create the SI header file for LaTeX.
    
    Args:
        pagenumbers: If False, skip the \\thepage redefinition to allow
                     \\pagenumbering{gobble} to work. If True or None,
                     include S-prefixed page numbering.
    """
    lines = [
        r"\usepackage{lineno}",
        r"\setcounter{page}{1}",
        r"\renewcommand{\thefigure}{S\arabic{figure}}",
        r"\renewcommand{\thetable}{S\arabic{table}}",
    ]
    # Only include S-prefixed page numbers if page numbering is not explicitly disabled
    if pagenumbers in (None, True):
        lines.append(r"\renewcommand{\thepage}{S\arabic{page}}")
    
    content = "\n".join(lines) + "\n"
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


def convert_figures_for_web(
    figure_format: str = "png",
    figure_background: str = "white",
    density: int = 300,
    quality: int = 90,
    copy_to_export: bool = False
) -> None:
    """Convert PDF figures to web-friendly formats with background options.
    
    Args:
        figure_format: Output format (png, webp, jpg, or original to skip)
        figure_background: Background color (white, transparent)
        density: DPI for PDF rasterization
        quality: JPEG/WebP quality (1-100)
        copy_to_export: If True, copy converted figures to export/figures/
    """
    figures_dir = Path("figures")
    export_figures_dir = Path("export/figures")
    
    if figure_format == "original":
        # Just copy original figures to export if requested
        if copy_to_export and figures_dir.exists():
            export_figures_dir.mkdir(parents=True, exist_ok=True)
            for fig_file in figures_dir.iterdir():
                if fig_file.is_file():
                    shutil.copy2(fig_file, export_figures_dir / fig_file.name)
            print("   Copied original figures to export/figures/")
        return
    
    if not figures_dir.exists():
        return
    
    # Create export figures directory if copying
    if copy_to_export:
        export_figures_dir.mkdir(parents=True, exist_ok=True)
    
    format_info = FIGURE_FORMAT_PRESETS.get(figure_format, FIGURE_FORMAT_PRESETS["png"])
    bg_info = FIGURE_BACKGROUND_PRESETS.get(figure_background, FIGURE_BACKGROUND_PRESETS["white"])
    
    # Convert PDF figures to web-friendly format
    pdf_files = list(figures_dir.glob("*.pdf"))
    if pdf_files:
        print(f"   Converting PDF figures to {format_info['name']} ({bg_info['name']} background)...")
        
        for pdf_file in pdf_files:
            try:
                output_file = pdf_file.with_suffix(f".{format_info['ext']}")
                
                # Build ImageMagick command with correct order:
                # magick -density DPI input.pdf [processing options] output.png
                cmd = ["magick", "-density", str(density), str(pdf_file)]
                
                # Handle background
                if figure_background == "transparent":
                    cmd.extend(["-background", "none", "-alpha", "set"])
                else:
                    cmd.extend(["-background", bg_info["color"], "-alpha", "remove", "-alpha", "off"])
                
                # Add quality for lossy formats
                if figure_format in ("webp", "jpg"):
                    cmd.extend(["-quality", str(quality)])
                
                cmd.append(str(output_file))
                
                subprocess.run(cmd, capture_output=True, check=False)
                
                # Copy to export directory if requested
                if copy_to_export and output_file.exists():
                    shutil.copy2(output_file, export_figures_dir / output_file.name)
            except Exception as e:
                print(f"   Warning: Failed to convert {pdf_file.name}: {e}")
    
    # Copy non-PDF figures (PNG, JPG, WebP, etc.) directly to export
    if copy_to_export:
        non_pdf_exts = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
        non_pdf_files = [f for f in figures_dir.iterdir() 
                         if f.is_file() and f.suffix.lower() in non_pdf_exts]
        if non_pdf_files:
            for fig_file in non_pdf_files:
                shutil.copy2(fig_file, export_figures_dir / fig_file.name)
            print(f"   Copied {len(non_pdf_files)} non-PDF figures to export/figures/")
        
        print(f"   Copied converted figures to export/figures/")


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


def resolve_transclusions(content: str, base_dir: Path) -> str:
    """Recursively resolve Obsidian transclusions ![[filename]]."""
    
    def _replace_transclusion(match):
        filename = match.group(1).strip()
        
        # Handle cases like ![[filename|alias]] - take only filename
        if "|" in filename:
            filename = filename.split("|", 1)[0]
            
        file_path = base_dir / filename
        
        # Try appending .md if missing
        if not file_path.exists() and not file_path.suffix:
            file_path = file_path.with_suffix(".md")
            
        if not file_path.exists():
            print(f"   Warning: Transcluded file not found: {filename}")
            return match.group(0)  # Return original string if not found
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                transcluded_content = f.read()
                
            # Strip YAML frontmatter from transcluded file
            if transcluded_content.startswith("---"):
                try:
                    _, frontmatter, body = transcluded_content.split("---", 2)
                    transcluded_content = body
                except ValueError:
                    pass # Not valid frontmatter format
            
            # Recursively resolve transclusions in the included content
            return resolve_transclusions(transcluded_content, base_dir)
            
        except Exception as e:
            print(f"   Warning: Error reading transcluded file {filename}: {e}")
            return match.group(0)

    # Regex for ![[filename]]
    pattern = r"!\[\[(.*?)\]\]"
    return re.sub(pattern, _replace_transclusion, content)


def build_digital_garden(source_file: str, config: Dict[str, Any]):
    """Build a Digital Garden (collection of interlinked files)."""
    print_header()
    print(box_top("Digital Garden Build"))
    
    garden_dir = Path("export/garden")
    if garden_dir.exists():
        shutil.rmtree(garden_dir)
    garden_dir.mkdir(parents=True, exist_ok=True)
    
    print(box_row(f"Source: {source_file}"))
    print(box_row(f"Output: {garden_dir}"))
    print(box_bottom())
    print()
    
    # 1. Parse Master file to find list of files
    if not Path(source_file).exists():
        print(f"Error: Source file {source_file} not found.")
        return

    with open(source_file, "r") as f:
        master_content = f.read()
    
    # Find all ![[filename]] transclusions in Master file
    # We assume these are the files we want to include in the garden
    transclusions = re.findall(r"!\[\[(.*?)\]\]", master_content)
    
    files_to_build = []
    base_dir = Path(source_file).parent
    
    for link in transclusions:
        filename = link.split("|")[0].strip()
        file_path = base_dir / filename
        if not file_path.suffix:
            file_path = file_path.with_suffix(".md")
            
        if file_path.exists():
            files_to_build.append(file_path)
    
    if not files_to_build:
        print("No files found in Master file transclusions.")
        return

    print(f"Found {len(files_to_build)} files to build.")
    
    master_stem = Path(source_file).stem

    # 2. Build each file individually
    cumulative_figures = 0
    cumulative_tables = 0
    file_offsets = []

    # Pre-scan to calculate offsets and build global label map
    print("   Pre-scanning files for figure/table numbering...")
    global_label_map = {}
    
    for file_path in files_to_build:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Count figures and tables
            num_figures = len(re.findall(r"\[!figure\]", content))
            num_tables = len(re.findall(r"\[!table\]", content))
            
            file_offsets.append({
                "figure_offset": cumulative_figures,
                "table_offset": cumulative_tables
            })
            
            # Extract labels and assign global numbers
            # Figure labels
            # We match lines starting with > [!figure] ... #fig:label
            # But in the file it might be just [!figure] if the blockquote > is stripped or handled differently?
            # The regex in figure-callouts-md.lua is text:match("%[!figure%]") and label = text:match("#(fig:[%w%-_]+)")
            # In the raw file it's likely "> [!figure] ..."
            
            # We need to iterate through the file to find them in order to assign correct numbers
            # relative to the cumulative count.
            
            current_fig = cumulative_figures
            current_tbl = cumulative_tables
            file_stem = f"garden_{file_path.stem}"
            
            for line in content.splitlines():
                if "[!figure]" in line:
                    match = re.search(r"#(fig:[a-zA-Z0-9_\-]+)", line)
                    if match:
                        current_fig += 1
                        global_label_map[match.group(1)] = {"num": current_fig, "file": file_stem}
                    else:
                        # Even if no label, it increments the counter
                        current_fig += 1
                elif "[!table]" in line:
                    match = re.search(r"#(tbl:[a-zA-Z0-9_\-]+)", line)
                    if match:
                        current_tbl += 1
                        global_label_map[match.group(1)] = {"num": current_tbl, "file": file_stem}
                    else:
                        current_tbl += 1

            cumulative_figures += num_figures
            cumulative_tables += num_tables
        except Exception as e:
            print(f"   Warning: Could not pre-scan {file_path.name}: {e}")
            file_offsets.append({"figure_offset": 0, "table_offset": 0})

    for i, file_path in enumerate(files_to_build):
        print(f"[{i+1}/{len(files_to_build)}] Building {file_path.name}...")
        
        new_stem = f"garden_{file_path.stem}"
        
        # Calculate navigation links (Prev / Next)
        prev_file = files_to_build[i-1] if i > 0 else None
        next_file = files_to_build[i+1] if i < len(files_to_build) - 1 else None
        
        # Create a temp file with nav links injected
        temp_file = f"_temp_garden_{file_path.name}"
        
        with open(file_path, "r") as f:
            content = f.read()
            
        # Add Nav Links
        nav_links = "\n\n---\n\n"
        if prev_file:
            prev_stem = f"garden_{prev_file.stem}"
            nav_links += f"[← Previous]({prev_stem}.md) "
        if prev_file and next_file:
            nav_links += " | "
        if next_file:
            next_stem = f"garden_{next_file.stem}"
            nav_links += f"[Next →]({next_stem}.md)"
        
        if prev_file or next_file:
            content += nav_links
            
        with open(temp_file, "w") as f:
            f.write(content)
            
        # Build it
        # We reuse build_document but target the garden directory
        # We pass the new prefixed filename as output_filename
        build_document(
            temp_file,
            "md-flattened", # Force flat markdown profile
            use_png=False,
            include_si_refs=False,
            frontmatter_file=None, # No frontmatter for individual garden pages usually
            figure_format=config.get("figure_format", "png"),
            figure_background=config.get("figure_background", "white"),
            visualize_captions=config.get("visualize_captions", False),
            caption_style=config.get("caption_style", "plain"),
            margin_top=config.get("margin_top"),
            margin_bottom=config.get("margin_bottom"),
            margin_left=config.get("margin_left"),
            margin_right=config.get("margin_right"),
            output_dir=str(garden_dir),
            output_filename=new_stem,
            figure_offset=file_offsets[i]["figure_offset"],
            table_offset=file_offsets[i]["table_offset"],
            global_label_map=global_label_map
        )
        
        # Cleanup temp
        if Path(temp_file).exists():
            os.remove(temp_file)
            
        # Inject frontmatter to the output file
        out_filepath = garden_dir / f"{new_stem}.md"
        if out_filepath.exists():
            with open(out_filepath, "r") as f:
                built_content = f.read()
            
            # Remove Pandoc's unnecessary escapes for wikilinks, underscores and stars
            # Pandoc escapes [[ as \[\[, _ as \_, and * as \*
            # We also handle escaped brackets to ensure clean links
            built_content = built_content.replace("\\[\\[", "[[").replace("\\]\\]", "]]")
            built_content = built_content.replace("\\[", "[").replace("\\]", "]")
            built_content = built_content.replace("\\_", "_")
            built_content = built_content.replace("\\*", "*")
            
            frontmatter = f"---\ntitle: \"{file_path.stem}\"\n---\n\n"
            with open(out_filepath, "w") as f:
                f.write(frontmatter + built_content)

    # 3. Create Master file (with links instead of transclusions)
    print("Building Master file...")
    index_content = master_content
    
    # Replace ![[filename]] with - [[new_filename|filename]]
    index_content = re.sub(r"!\[\[(.*?)\]\]", r"- [[\1]]", index_content)
    
    def _fix_links(match):
        inner = match.group(1)
        # remove path components, keep just filename/stem
        parts = inner.split("|")
        path_part = parts[0]
        alias_part = parts[1] if len(parts) > 1 else None
        
        stem = Path(path_part).stem
        new_stem = f"garden_{stem}"
        
        if alias_part:
            return f"[[{new_stem}|{alias_part}]]"
        else:
            return f"[[{new_stem}|{stem}]]"

    index_content = re.sub(r"\[\[(.*?)\]\]", _fix_links, index_content)
    
    # Write Master file
    master_output_filename = f"garden_{master_stem}.md"
    with open(garden_dir / master_output_filename, "w") as f:
        # No need to clean index_content as it hasn't passed through Pandoc
        f.write(index_content)
        
    print(f"✓ Digital Garden built in {garden_dir}")


def build_document(source_file: str, profile: str, use_png: bool, include_si_refs: bool,
                   frontmatter_file: Optional[str] = None, font: Optional[str] = None,
                   fontsize: Optional[str] = None, citation_style: Optional[str] = None,
                   si_file: Optional[str] = None, is_si: bool = False,
                   linespacing: Optional[str] = None, paragraph_style: Optional[str] = None,
                   linenumbers: Optional[bool] = None, pagenumbers: Optional[bool] = None,
                   numbered_headings: Optional[bool] = None,
                   language: Optional[str] = None, tex_mode: Optional[str] = None,
                   figure_format: Optional[str] = None, figure_background: Optional[str] = None,
                   papersize: Optional[str] = None,
                   margin_top: Optional[str] = None, margin_bottom: Optional[str] = None,
                   margin_left: Optional[str] = None, margin_right: Optional[str] = None,
                   visualize_captions: bool = False, caption_style: str = "plain",
                   output_dir: Optional[str] = None, output_filename: Optional[str] = None,
                   figure_offset: int = 0, table_offset: int = 0,
                   global_label_map: Optional[Dict[str, int]] = None):
    """Build the document with specified profile."""
    # Get profile info
    _, _, fmt = get_profile_info(profile)
    
    # Override format if --tex flag is used (export LaTeX source from PDF profile)
    if tex_mode in ("source", "portable", "body") and fmt == "pdf":
        fmt = "latex"
    
    # Determine output file name from source file
    source_path = Path(source_file)
    
    if output_filename:
        output_name = output_filename
    else:
        output_name = source_path.stem
        # Add suffix for flattened markdown (unless overridden)
        if fmt == "md":
            output_name += "_flat"
    
    # Map format to file extension (latex -> .tex for standard naming)
    ext = "tex" if fmt == "latex" else fmt
    
    if output_dir:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        output_file = str(target_dir / f"{output_name}.{ext}")
    else:
        output_file = f"{EXPORT_DIR}/{output_name}.{ext}"
    temp_merged = f"_temp_{output_name}_merged.md"
    
    if fmt == "latex" and tex_mode:
        print(f">> Building {source_file} (LATEX/{tex_mode.upper()})...")
    elif fmt == "md":
        print(f">> Building {source_file} (FLATTENED MARKDOWN)...")
    else:
        print(f">> Building {source_file} ({fmt.upper()})...")
    
    # Resolve transclusions and merge frontmatter
    # We always read source file and resolve transclusions now
    print(f"   Resolving transclusions in {source_file}...")
    try:
        with open(source_file, "r", encoding="utf-8") as f:
            source_content = f.read()
            
        # Resolve transclusions relative to source file directory
        # If source_file is "src/Master.md", base_dir is "src"
        source_dir = Path(source_file).parent
        resolved_content = resolve_transclusions(source_content, source_dir)
        
        # Write to temp merged file
        with open(temp_merged, "w", encoding="utf-8") as out:
            # Prepend frontmatter if requested
            if frontmatter_file and Path(frontmatter_file).exists():
                print(f"   Merging frontmatter from {frontmatter_file}...")
                with open(frontmatter_file, "r", encoding="utf-8") as f:
                    out.write(f.read())
                out.write("\n")
                
                # If source had frontmatter, strip it to avoid duplication when merging
                if resolved_content.startswith("---"):
                    try:
                        _, fm, body = resolved_content.split("---", 2)
                        out.write(body)
                    except ValueError:
                        out.write(resolved_content)
                else:
                    out.write(resolved_content)
            else:
                out.write(resolved_content)
                
        input_file = temp_merged
        
    except Exception as e:
        print(f"   Error processing file: {e}")
        sys.exit(1)
    
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
    
    # Convert figures for flattened markdown (always copy to export for md format)
    if fmt == "md":
        # If output_dir is specified (e.g. garden), copy figures there too
        copy_to_custom = False
        custom_figures_dir = None
        if output_dir:
            custom_figures_dir = Path(output_dir) / "figures"
            custom_figures_dir.mkdir(parents=True, exist_ok=True)
            copy_to_custom = True

        convert_figures_for_web(
            figure_format=figure_format or "png",
            figure_background=figure_background or "white",
            copy_to_export=True
        )
        
        # Also copy to custom output directory if needed
        if copy_to_custom and custom_figures_dir:
            figures_dir = Path("export/figures")
            if figures_dir.exists():
                for fig in figures_dir.glob("*"):
                    shutil.copy2(fig, custom_figures_dir / fig.name)
    
    # Merge configs
    profile_path = f"{PROFILES_DIR}/{profile}.yaml"
    config_file = merge_configs(BASE_PROFILE, profile_path)

    is_latex_default_compat_font = font == "computer-modern"
    if fmt == "latex" and tex_mode in ("portable", "body"):
        strip_font_variables_from_defaults_file(config_file)
    if fmt in ("pdf", "latex") and is_latex_default_compat_font:
        strip_font_variables_from_defaults_file(config_file)

    effective_gap = paragraph_style == "gap" or (
        not paragraph_style and _profile_uses_gap_paragraphs(config_file)
    )
    if effective_gap:
        if input_file != temp_merged:
            shutil.copy(source_file, temp_merged)
            input_file = temp_merged
        _normalize_inline_parindent_for_gap(input_file)

    # Apply typography overrides directly to defaults file
    # Portable/body modes explicitly ignore explicit font selection for portability.
    effective_font = None if (
        (fmt == "latex" and tex_mode in ("portable", "body"))
        or is_latex_default_compat_font
    ) else font
    has_overrides = any([effective_font, fontsize, linespacing, paragraph_style, linenumbers is not None, pagenumbers is not None, numbered_headings is not None, language, papersize, margin_top, margin_bottom, margin_left, margin_right])
    
    # Always check for titlesec conflicts in PDF/LaTeX builds
    has_titlesec_conflict = fmt in ("pdf", "latex") and _profile_uses_titlesec_paragraph(config_file)
    
    if fmt in ("pdf", "latex") and (has_overrides or has_titlesec_conflict):
        apply_font_overrides_to_defaults_file(
            config_file, font=effective_font, fontsize=fontsize,
            linespacing=linespacing, paragraph_style=paragraph_style,
            linenumbers=linenumbers, pagenumbers=pagenumbers,
            numbered_headings=numbered_headings,
            language=language,
            papersize=papersize,
            margin_top=margin_top, margin_bottom=margin_bottom,
            margin_left=margin_left, margin_right=margin_right
        )
        if effective_font and effective_font in FONT_PRESETS:
            print(f"   Using font: {FONT_PRESETS[effective_font]['name']}")
        elif fmt == "pdf" and is_latex_default_compat_font:
            print(f"   Using font: {FONT_PRESETS[font]['name']}")
        if fontsize:
            print(f"   Using font size: {fontsize}")
        if linespacing and linespacing in LINE_SPACING_PRESETS:
            print(f"   Using line spacing: {LINE_SPACING_PRESETS[linespacing]['name']}")
        if paragraph_style and paragraph_style in PARAGRAPH_STYLE_PRESETS:
            print(f"   Using paragraph style: {PARAGRAPH_STYLE_PRESETS[paragraph_style]['name']}")
        if linenumbers is True:
            print(f"   Line numbers: enabled")
        elif linenumbers is False:
            print(f"   Line numbers: disabled")
        if pagenumbers is True:
            print(f"   Page numbers: enabled")
        elif pagenumbers is False:
            print(f"   Page numbers: disabled")
        if numbered_headings is True:
            print(f"   Numbered headings: enabled")
        elif numbered_headings is False:
            print(f"   Numbered headings: disabled")
        if language and language in LANGUAGE_PRESETS:
            print(f"   Using language: {LANGUAGE_PRESETS[language]}")
        if papersize and papersize in PAPER_SIZE_PRESETS:
            print(f"   Using paper size: {PAPER_SIZE_PRESETS[papersize]}")
        if any([margin_top, margin_bottom, margin_left, margin_right]):
            customs = []
            if margin_top: customs.append(f"T:{margin_top}")
            if margin_bottom: customs.append(f"B:{margin_bottom}")
            if margin_left: customs.append(f"L:{margin_left}")
            if margin_right: customs.append(f"R:{margin_right}")
            print(f"   Using margins: {' '.join(customs)}")
    
    # Build pandoc command
    cmd = ["pandoc", input_file, "-o", output_file, f"--defaults={config_file}"]
    
    # Add standalone flag for LaTeX output (PDF output is always standalone)
    if fmt == "latex":
        cmd.append("-s")

    
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
        if fmt in ("pdf", "latex"):
            create_si_header(pagenumbers=pagenumbers)
            cmd.extend([
                "--metadata", 'figPrefix=["Fig.","Figs."]',
                "--metadata", 'tblPrefix=["Table","Tables"]',
                f"--include-in-header={SI_HEADER}"
            ])
        elif fmt == "md":
            # For markdown, append metadata to the config file to ensure it overrides
            # profile defaults (CLI args might not correctly override list structures in defaults)
            with open(config_file, "a") as f:
                f.write('\n\n# --- SI Metadata Overrides ---\n')
                f.write('metadata:\n')
                f.write('  is_si: true\n')
                f.write('  figPrefix: ["Figure", "Figures"]\n')
                f.write('  tblPrefix: ["Table", "Tables"]\n')
    
    # Add lua filter for DOCX
    if fmt == "docx":
        cmd.append(f"--lua-filter={LUA_FILTER}")
    
    # Add figure format metadata for flattened markdown
    if fmt == "md" and figure_format:
        cmd.extend(["--metadata", f"figure-format:{figure_format}"])
    
    # Add visualize captions metadata for flattened markdown
    if fmt == "md":
        if visualize_captions:
            cmd.extend(["--metadata", "visualize-captions=true"])
        if caption_style and caption_style != "plain":
            cmd.extend(["--metadata", f"caption-style:{caption_style}"])
        
        # Add offsets
        if figure_offset > 0:
            cmd.extend(["--metadata", f"figure-offset:{figure_offset}"])
        if table_offset > 0:
            cmd.extend(["--metadata", f"table-offset:{table_offset}"])
            
        # Add global label map if provided
        if global_label_map:
            # Create a temporary metadata file for the map
            labels_meta_file = f"_temp_labels_{output_name}.json"
            labels_data = {"global-labels": global_label_map}
            with open(labels_meta_file, "w") as f:
                json.dump(labels_data, f)
            cmd.extend(["--metadata-file", labels_meta_file])
    
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
    
    if fmt == "latex" and tex_mode == "body":
        convert_tex_file_to_body_only(output_file)

    # Cleanup
    # Remove temporary files
    cleanup_files = [temp_merged, config_file]
    if 'labels_meta_file' in locals() and Path(labels_meta_file).exists():
        cleanup_files.append(labels_meta_file)
        
    for f in cleanup_files:
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
    if fmt == "pdf" and config.get("tex_mode") in ("source", "portable", "body"):
        fmt = "latex"
    if fmt == "pdf" and config.get("output_tex") and not config.get("tex_mode"):
        fmt = "latex"
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
    if fmt == "md":
        if config.get('visualize_captions'):
            print(box_row("Captions:     Visible (Visualized)"))
        if config.get('caption_style') == "html":
            print(box_row("Caption Style: HTML"))
    if config.get('tex_mode') in ("source", "portable", "body"):
        print(box_row(f"LaTeX Mode:   {config.get('tex_mode')}"))
    elif config.get('output_tex'):
        print(box_row("LaTeX Mode:   portable"))
    if fmt in ("pdf", "latex") and config.get('font'):
        font_name = FONT_PRESETS[config['font']]['name']
        print(box_row(f"Font:         {font_name}"))
    if fmt in ("pdf", "latex") and config.get('fontsize'):
        print(box_row(f"Font Size:    {config['fontsize']}"))
    if fmt in ("pdf", "latex", "docx") and config.get('citation_style'):
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
    """Configure default font, font size, citation style, and typography settings."""
    print_header()
    
    defaults = load_defaults()
    
    # Show current defaults
    print(box_top("Current Defaults"))
    current_font_key = defaults.get('font', '')
    if current_font_key:
        current_font_name = FONT_PRESETS.get(current_font_key, FONT_PRESETS['libertinus'])['name']
    else:
        current_font_name = 'Profile Default'
    print(box_row(f"Font: {current_font_name}"))
    print(box_row(f"Font Size: {defaults.get('fontsize', '11pt')}"))
    style_key = defaults.get('citation_style', 'vancouver')
    local_styles = list_local_csl_files()
    style_name = next((n for k, n, _ in local_styles if k == style_key), style_key)
    print(box_row(f"Citation Style: {style_name}"))
    # Typography settings
    ls = defaults.get('linespacing', '')
    print(box_row(f"Line Spacing: {LINE_SPACING_PRESETS[ls]['name'] if ls else 'Profile Default'}"))
    ps = defaults.get('paragraph_style', '')
    print(box_row(f"Paragraph Style: {PARAGRAPH_STYLE_PRESETS[ps]['name'] if ps else 'Profile Default'}"))
    ln = defaults.get('linenumbers')
    ln_str = "Profile Default" if ln is None else ("Enabled" if ln else "Disabled")
    print(box_row(f"Line Numbers: {ln_str}"))
    nh = defaults.get('numbered_headings')
    nh_str = "Profile Default" if nh is None else ("Numbered" if nh else "Unnumbered")
    print(box_row(f"Headings: {nh_str}"))
    pn = defaults.get('pagenumbers')
    pn_str = "Profile Default" if pn is None else ("Enabled" if pn else "Disabled")
    print(box_row(f"Page Numbers: {pn_str}"))
    lang = defaults.get('language', '')
    print(box_row(f"Language: {LANGUAGE_PRESETS.get(lang, 'Profile Default')}"))
    print(box_bottom())
    print()
    
    # Font selection
    print(box_top("Font Selection"))
    print(box_row(f" 0) Profile Default{' (current)' if not defaults.get('font') else ''}"))
    font_list = list(FONT_PRESETS.keys())
    for i, key in enumerate(font_list, 1):
        name = FONT_PRESETS[key]["name"]
        marker = " (current)" if key == defaults.get('font') else ""
        print(box_row(f"{i:2}) {name}{marker}"))
    print(box_bottom())
    
    font_choice = input(f"Select font [0-{len(font_list)}, Enter=keep current]: ").strip()
    if font_choice:
        try:
            if int(font_choice) == 0:
                defaults['font'] = ''
            else:
                idx = int(font_choice) - 1
                if 0 <= idx < len(font_list):
                    defaults['font'] = font_list[idx]
        except (ValueError, IndexError):
            pass
    
    print()
    
    # Font size selection
    print(box_top("Font Size Selection"))
    for i, size in enumerate(FONT_SIZES, 1):
        marker = " (current)" if size == defaults.get('fontsize') else ""
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
    local_styles = list_local_csl_files()
    
    if local_styles:
        for i, (key, name, _) in enumerate(local_styles, 1):
            marker = " (current)" if key == defaults.get('citation_style') else ""
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
    
    # Typography settings (PDF only)
    print(box_top("Typography Settings (PDF only)"))
    print(box_row("These override profile defaults for PDF output"))
    print(box_row(""))
    
    # Line spacing
    spacing_list = list(LINE_SPACING_PRESETS.items())
    print(box_row("Line Spacing:"))
    print(box_row("  0) Profile Default"))
    for i, (key, info) in enumerate(spacing_list, 1):
        marker = " (current)" if key == defaults.get('linespacing') else ""
        print(box_row(f"  {i}) {info['name']}{marker}"))
    spacing_choice = input("│  Select line spacing [0-5, Enter=keep current]: ").strip()
    if spacing_choice:
        try:
            spacing_idx = int(spacing_choice)
            if spacing_idx == 0:
                defaults['linespacing'] = ""
            elif spacing_idx > 0:
                defaults['linespacing'] = spacing_list[spacing_idx - 1][0]
        except (ValueError, IndexError):
            pass
    
    # Paragraph style
    print(box_row(""))
    print(box_row("Paragraph Style:"))
    cur_ps = defaults.get('paragraph_style', '')
    print(box_row(f"  0) Profile Default{' (current)' if not cur_ps else ''}"))
    print(box_row(f"  1) Indented (American){' (current)' if cur_ps == 'indent' else ''}"))
    print(box_row(f"  2) Gap (European){' (current)' if cur_ps == 'gap' else ''}"))
    print(box_row(f"  3) Gap + Indent (Both){' (current)' if cur_ps == 'both' else ''}"))
    para_choice = input("│  Select paragraph style [0-3, Enter=keep current]: ").strip()
    if para_choice:
        if para_choice == "0":
            defaults['paragraph_style'] = ""
        elif para_choice == "1":
            defaults['paragraph_style'] = "indent"
        elif para_choice == "2":
            defaults['paragraph_style'] = "gap"
        elif para_choice == "3":
            defaults['paragraph_style'] = "both"
    
    # Line numbers
    print(box_row(""))
    cur_ln = defaults.get('linenumbers')
    print(box_row("Line Numbers:"))
    print(box_row(f"  0) Profile Default{' (current)' if cur_ln is None else ''}"))
    print(box_row(f"  1) Enable{' (current)' if cur_ln is True else ''}"))
    print(box_row(f"  2) Disable{' (current)' if cur_ln is False else ''}"))
    ln_choice = input("│  Select line numbers [0-2, Enter=keep current]: ").strip()
    if ln_choice:
        if ln_choice == "0":
            defaults['linenumbers'] = None
        elif ln_choice == "1":
            defaults['linenumbers'] = True
        elif ln_choice == "2":
            defaults['linenumbers'] = False
    
    # Numbered headings
    print(box_row(""))
    cur_nh = defaults.get('numbered_headings')
    print(box_row("Numbered Headings:"))
    print(box_row(f"  0) Profile Default{' (current)' if cur_nh is None else ''}"))
    print(box_row(f"  1) Numbered{' (current)' if cur_nh is True else ''}"))
    print(box_row(f"  2) Unnumbered{' (current)' if cur_nh is False else ''}"))
    nh_choice = input("│  Select heading numbering [0-2, Enter=keep current]: ").strip()
    if nh_choice:
        if nh_choice == "0":
            defaults['numbered_headings'] = None
        elif nh_choice == "1":
            defaults['numbered_headings'] = True
        elif nh_choice == "2":
            defaults['numbered_headings'] = False

    # Page numbers
    print(box_row(""))
    cur_pn = defaults.get('pagenumbers')
    print(box_row("Page Numbers:"))
    print(box_row(f"  0) Profile Default{' (current)' if cur_pn is None else ''}"))
    print(box_row(f"  1) Enable{' (current)' if cur_pn is True else ''}"))
    print(box_row(f"  2) Disable{' (current)' if cur_pn is False else ''}"))
    pn_choice = input("│  Select page numbering [0-2, Enter=keep current]: ").strip()
    if pn_choice:
        if pn_choice == "0":
            defaults['pagenumbers'] = None
        elif pn_choice == "1":
            defaults['pagenumbers'] = True
        elif pn_choice == "2":
            defaults['pagenumbers'] = False
    
    # Language
    print(box_row(""))
    lang_list = list(LANGUAGE_PRESETS.items())
    cur_lang = defaults.get('language', '')
    print(box_row("Document Language:"))
    print(box_row(f"  0) Profile Default{' (current)' if not cur_lang else ''}"))
    for i, (key, name) in enumerate(lang_list, 1):
        marker = " (current)" if key == cur_lang else ""
        print(box_row(f"  {i}) {name}{marker}"))
    lang_choice = input(f"│  Select language [0-{len(lang_list)}, Enter=keep current]: ").strip()
    if lang_choice:
        try:
            lang_idx = int(lang_choice)
            if lang_idx == 0:
                defaults['language'] = ""
            elif lang_idx > 0:
                defaults['language'] = lang_list[lang_idx - 1][0]
        except (ValueError, IndexError):
            pass
    
    print(box_bottom())
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
    print(box_row("3) Flattened Markdown (for digital gardens)"))
    print(box_row("4) LaTeX Source (profile exact)"))
    print(box_row("5) Portable LaTeX"))
    print(box_row("6) LaTeX Body-only (for journal templates)"))
    print(box_bottom())
    fmt_choice = input("Select format [1-6]: ").strip()
    if fmt_choice == "1":
        fmt = "docx"
        tex_mode = None
    elif fmt_choice == "3":
        fmt = "md"  # Flattened markdown
        tex_mode = None
    elif fmt_choice == "4":
        fmt = "pdf"  # Use PDF profile but output LaTeX
        tex_mode = "source"
    elif fmt_choice == "5":
        fmt = "pdf"  # Use PDF profile but output LaTeX
        tex_mode = "portable"
    elif fmt_choice == "6":
        fmt = "pdf"  # Use PDF profile but output LaTeX
        tex_mode = "body"
    else:
        fmt = "pdf"
        tex_mode = None
    print()
    
    # Profile selection (skip for DOCX and flattened markdown since there's only one each)
    if fmt == "docx":
        profile = "docx-manuscript"
    elif fmt == "md":
        profile = "md-flattened"
    else:
        print(box_top("Output Profile"))
        all_profiles = []
        idx = 1
        for category, profiles in get_profile_categories().items():
            print(box_row(f"{category}:"))
            for profile in profiles:
                name, description, profile_fmt = get_profile_info(profile)
                # All LaTeX modes use the PDF profiles as their base configuration.
                desired_profile_fmt = "pdf" if tex_mode in ("source", "portable", "body") else fmt
                if profile_fmt == desired_profile_fmt:
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
    
    # Figure format options for flattened markdown
    figure_format = defaults.get('figure_format', 'png')
    figure_background = defaults.get('figure_background', 'white')
    
    if fmt == "md":
        print("│")
        print("│  Figure Format:")
        format_list = list(FIGURE_FORMAT_PRESETS.items())
        for i, (key, info) in enumerate(format_list, 1):
            marker = " (current)" if key == figure_format else ""
            print(f"│    {i}) {info['name']}{marker}")
        fig_fmt_choice = input(f"│  Select figure format [1-{len(format_list)}, Enter=keep current]: ").strip()
        if fig_fmt_choice:
            try:
                fig_fmt_idx = int(fig_fmt_choice) - 1
                if 0 <= fig_fmt_idx < len(format_list):
                    figure_format = format_list[fig_fmt_idx][0]
            except (ValueError, IndexError):
                pass
        
        # Only ask for background if not keeping original format
        if figure_format != "original":
            print("│")
            print("│  Figure Background:")
            bg_list = list(FIGURE_BACKGROUND_PRESETS.items())
            for i, (key, info) in enumerate(bg_list, 1):
                marker = " (current)" if key == figure_background else ""
                print(f"│    {i}) {info['name']}{marker}")
            fig_bg_choice = input(f"│  Select background [1-{len(bg_list)}, Enter=keep current]: ").strip()
            if fig_bg_choice:
                try:
                    fig_bg_idx = int(fig_bg_choice) - 1
                    if 0 <= fig_bg_idx < len(bg_list):
                        figure_background = bg_list[fig_bg_idx][0]
                except (ValueError, IndexError):
                    pass
    
    # Ask if this is an SI document (for SI-specific formatting)
    is_si_choice = input("│  Apply SI formatting (S-prefixed figures/tables)? [y/N]: ").strip().lower()
    is_si = is_si_choice == 'y'

    if fmt == "md":
        visualize_captions_choice = input("│  Visualize captions? [y/N]: ").strip().lower()
        visualize_captions = visualize_captions_choice == 'y'
        
        # HTML Captions option
        html_captions_choice = input("│  Use HTML <figure> tags (for sizing/alignment)? [y/N]: ").strip().lower()
        caption_style = "html" if html_captions_choice == 'y' else "plain"
    else:
        visualize_captions = False
        caption_style = "plain"

    print(box_bottom())
    
    return {
        "source_file": source_file,
        "frontmatter_file": frontmatter_file,
        "profile": profile,
        "use_png": use_png,
        "include_si_refs": include_si_refs,
        "si_file": si_file,
        "is_si": is_si,
        "tex_mode": tex_mode,
        "font": defaults.get('font'),
        "fontsize": defaults.get('fontsize'),
        "citation_style": defaults.get('citation_style'),
        "linespacing": defaults.get('linespacing') or None,
        "paragraph_style": defaults.get('paragraph_style') or None,
        "linenumbers": defaults.get('linenumbers'),
        "pagenumbers": defaults.get('pagenumbers'),
        "numbered_headings": defaults.get('numbered_headings'),
        "language": defaults.get('language') or None,
        "figure_format": figure_format if fmt == "md" else None,
        "figure_background": figure_background if fmt == "md" else None,
        "papersize": defaults.get('papersize'),
        "margin_top": defaults.get('margin_top'),
        "margin_bottom": defaults.get('margin_bottom'),
        "margin_left": defaults.get('margin_left'),
        "margin_right": defaults.get('margin_right'),
        "visualize_captions": visualize_captions if fmt == "md" else False,
        "caption_style": caption_style if fmt == "md" else "plain",
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
        "tex_mode": None,
        "font": None,
        "fontsize": None,
        "citation_style": None,
        "linespacing": None,
        "paragraph_style": None,
        "linenumbers": None,
        "pagenumbers": None,
        "numbered_headings": None,
        "language": None,
        "figure_format": None,
        "figure_background": None,
        "papersize": None,
        "margin_top": None,
        "margin_bottom": None,
        "margin_left": None,
        "margin_right": None,
        "visualize_captions": None,
        "caption_style": None,
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
        elif arg.startswith("--linespacing="):
            config["linespacing"] = arg.split("=", 1)[1]
        elif arg.startswith("--paragraph-style="):
            config["paragraph_style"] = arg.split("=", 1)[1]
        elif arg == "--linenumbers":
            config["linenumbers"] = True
        elif arg == "--no-linenumbers":
            config["linenumbers"] = False
        elif arg == "--pagenumbers":
            config["pagenumbers"] = True
        elif arg == "--no-pagenumbers":
            config["pagenumbers"] = False
        elif arg == "--numbered-headings":
            config["numbered_headings"] = True
        elif arg == "--no-numbered-headings":
            config["numbered_headings"] = False
        elif arg.startswith("--lang="):
            config["language"] = arg.split("=", 1)[1]
        elif arg == "--png":
            config["use_png"] = True
        elif arg == "--include-si-refs":
            config["include_si_refs"] = True
        elif arg == "--si":
            config["is_si"] = True
        elif arg == "--tex":
            config["tex_mode"] = "portable"
        elif arg == "--tex-portable":
            config["tex_mode"] = "portable"
        elif arg == "--tex-source":
            config["tex_mode"] = "source"
        elif arg == "--tex-body":
            config["tex_mode"] = "body"
        # Flattened markdown options
        elif arg == "--flatten":
            config["profile"] = "md-flattened"
        elif arg == "--digital-garden":
            config["digital_garden"] = True
            config["profile"] = "md-flattened" # Garden uses flattened profile by default
        elif arg.startswith("--figure-format="):
            config["figure_format"] = arg.split("=", 1)[1]
        elif arg.startswith("--figure-bg="):
            config["figure_background"] = arg.split("=", 1)[1]
        elif arg.startswith("--papersize="):
            config["papersize"] = arg.split("=", 1)[1]
        elif arg.startswith("--margin-top="):
            config["margin_top"] = arg.split("=", 1)[1]
        elif arg.startswith("--margin-bottom="):
            config["margin_bottom"] = arg.split("=", 1)[1]
        elif arg.startswith("--margin-left="):
            config["margin_left"] = arg.split("=", 1)[1]
        elif arg.startswith("--margin-right="):
            config["margin_right"] = arg.split("=", 1)[1]
        elif arg == "--captions" or arg == "--visualize-captions":
            config["visualize_captions"] = True
        elif arg == "--html-captions":
            config["caption_style"] = "html"
        elif arg.startswith("--caption-style="):
            config["caption_style"] = arg.split("=", 1)[1]
        # Legacy support for main|si
        elif arg == "main":
            config["source_file"] = MAINTEXT
        elif arg == "si":
            config["source_file"] = SUPPINFO
            config["is_si"] = True
    
    # Apply defaults for markdown/garden builds: captions ON by default
    if config.get("profile") == "md-flattened" or config.get("digital_garden"):
        if config["visualize_captions"] is None:
            config["visualize_captions"] = True
        if config["caption_style"] is None:
            config["caption_style"] = "html"
    
    # Apply fallback defaults for non-markdown builds
    if config["visualize_captions"] is None:
        config["visualize_captions"] = False
    if config["caption_style"] is None:
        config["caption_style"] = "plain"
    
    if config["source_file"]:
        return config, False, False
    
    return None, False, False


def print_help():
    """Print help message."""
    font_list = ", ".join(FONT_PRESETS.keys())
    spacing_list = ", ".join(LINE_SPACING_PRESETS.keys())
    para_list = ", ".join(PARAGRAPH_STYLE_PRESETS.keys())
    lang_list = ", ".join(LANGUAGE_PRESETS.keys())
    papersize_list = ", ".join(PAPER_SIZE_PRESETS.keys())
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
  --linespacing=NAME         Override line spacing ({spacing_list})
  --paragraph-style=NAME     Override paragraph style ({para_list})
  --linenumbers              Enable line numbers
  --no-linenumbers           Disable line numbers
  --pagenumbers              Enable page numbers
  --no-pagenumbers           Disable page numbers
  --numbered-headings        Enable numbered headings
  --no-numbered-headings     Disable numbered headings
  --papersize=SIZE           Set paper size ({papersize_list})
  --margin-top=SIZE          Set top margin
  --margin-bottom=SIZE       Set bottom margin
  --margin-left=SIZE         Set left margin
  --margin-right=SIZE        Set right margin
  --lang=CODE                Set document language ({lang_list})
  --csl=STYLE                Use citation style (installed: {style_list})
  --png                      Convert PDF figures to PNG (for DOCX)
  --include-si-refs          Include SI citations in bibliography
  --si-file=FILE             SI file for reference extraction
  --si                       Apply SI formatting (S-prefixed figures/tables)
  --tex                      Export Portable LaTeX (.tex) instead of PDF
  --tex-source               Export LaTeX source that matches the PDF profile (including fonts)
  --tex-portable             Export Portable LaTeX (.tex) instead of PDF
  --tex-body                 Export LaTeX body-only (no preamble/document wrapper)
  --flatten                  Export as flattened markdown (for digital gardens)
  --figure-format=FORMAT     Figure format for flattened markdown (png, webp, jpg, original)
  --figure-bg=COLOR          Figure background for flattened markdown (white, transparent)
  --captions                 Visualize captions in flattened markdown (output text below image)
  --html-captions            Use HTML <figure> tags in flattened markdown (preserves sizing/alignment)
  --list, -l                 List all available profiles
  --last                     Repeat last build configuration
  --help, -h                 Show this help message

  main|si                    Legacy: build 01_maintext.md or 02_supp_info.md

Examples:
  python build.py --source=01_maintext.md --frontmatter=00_frontmatter.md
  python build.py --source=my_draft.md --profile=pdf-nature --csl=nature
  python build.py --source=02_supp_info.md --si --profile=pdf-default
  python build.py --source=manuscript.md --profile=pdf-default --tex
  python build.py --source=manuscript.md --profile=pdf-default --tex-source
  python build.py --source=manuscript.md --profile=pdf-default --tex-body
  python build.py --source=manuscript.md --flatten --figure-format=png --figure-bg=white --captions
  python build.py main --profile=pdf-nature
  python build.py --last
""")


def setup_working_directory():
    """Ensure we are running from the project root."""
    current = Path.cwd()
    
    # Check if we are already in root (has .obsidian folder)
    if (current / ".obsidian").exists():
        return

    # Check if we are in resources dir or subdirectory
    # Walk up to find .obsidian
    p = current
    while p != p.parent:
        if (p / ".obsidian").exists():
            os.chdir(p)
            return
        p = p.parent
    
    # Fallback: Infer from script location
    # Script is expected to be at root/resources/build.py
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    if (project_root / ".obsidian").exists():
        os.chdir(project_root)
        return

    # If we still can't find it, do nothing and hope for the best (or print warning)
    # print("Warning: Could not determine project root. Running from current directory.")


def main():
    """Main entry point."""
    setup_working_directory()
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

    if config is not None and "tex_mode" not in config:
        if config.get("output_tex"):
            config["tex_mode"] = "portable"
        else:
            config["tex_mode"] = None
    if config is not None and "output_tex" in config:
        config.pop("output_tex", None)
    
    # Save configuration
    save_config(config)
    
    # Display build summary (skip if already shown in quick build)
    if not use_last:
        print()
        print_build_summary(config)
        print()
    
    # Build document or garden
    if config.get("digital_garden"):
        build_digital_garden(config["source_file"], config)
    else:
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
            config.get("linespacing"),
            config.get("paragraph_style"),
            config.get("linenumbers"),
            config.get("pagenumbers"),
            config.get("numbered_headings"),
            config.get("language"),
            config.get("tex_mode"),
            config.get("figure_format"),
            config.get("figure_background"),
            config.get("papersize"),
            config.get("margin_top"),
            config.get("margin_bottom"),
            config.get("margin_left"),
            config.get("margin_right"),
            config.get("visualize_captions", False),
            config.get("caption_style", "plain"),
        )
    
    print()
    print("✓ Build complete!")
    print()


if __name__ == "__main__":
    main()
