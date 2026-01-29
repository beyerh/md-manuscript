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
    "citation_style": "vancouver",
    "linespacing": "",
    "paragraph_style": "",
    "linenumbers": None,
    "pagenumbers": None,
    "numbered_headings": None,
    "language": ""
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
) -> None:
    """Apply font/fontsize/linespacing/paragraph style/headings/language overrides to Pandoc defaults file.

    This avoids situations where multiple settings (from profile + CLI)
    end up concatenated in the generated LaTeX.
    """
    if not any([font, fontsize, linespacing, paragraph_style, linenumbers is not None, pagenumbers is not None, numbered_headings is not None, language]):
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
    
    # Handle page numbers - need to modify header-includes
    if pagenumbers is not None:
        _apply_pagenumbers_override(defaults_path, pagenumbers)
    
    # Handle paragraph style - need to modify parindent/parskip in header-includes
    if paragraph_style:
        _apply_paragraph_style_override(defaults_path, paragraph_style)


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


def _apply_paragraph_style_override(defaults_path: str, style: str) -> None:
    """Modify parindent/parskip in header-includes inside variables block.
    
    Adds settings at END of header-includes to ensure they override profile defaults.
    """
    path = Path(defaults_path)
    if not path.exists():
        return
    
    content = path.read_text()
    lines = content.splitlines(True)
    
    # Remove ALL existing parindent/parskip lines (and any prior AtBeginDocument injection)
    # and any parskip package usage from anywhere in the file.
    new_lines = []
    for line in lines:
        if r'\setlength{\parindent}' in line or r'\setlength{\parskip}' in line:
            continue
        if r'\AtBeginDocument' in line and (r'\parindent' in line or r'\parskip' in line):
            continue
        if r'\usepackage{parskip}' in line:
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
                   si_file: Optional[str] = None, is_si: bool = False,
                   linespacing: Optional[str] = None, paragraph_style: Optional[str] = None,
                   linenumbers: Optional[bool] = None, pagenumbers: Optional[bool] = None,
                   numbered_headings: Optional[bool] = None,
                   language: Optional[str] = None, tex_mode: Optional[str] = None):
    """Build the document with specified profile."""
    # Get profile info
    _, _, fmt = get_profile_info(profile)
    
    # Override format if --tex flag is used (export LaTeX source from PDF profile)
    if tex_mode in ("source", "portable", "body") and fmt == "pdf":
        fmt = "latex"
    
    # Determine output file name from source file
    source_path = Path(source_file)
    output_name = source_path.stem
    
    # Map format to file extension (latex -> .tex for standard naming)
    ext = "tex" if fmt == "latex" else fmt
    output_file = f"{EXPORT_DIR}/{output_name}.{ext}"
    temp_merged = f"_temp_{output_name}_merged.md"
    
    if fmt == "latex" and tex_mode:
        print(f">> Building {source_file} (LATEX/{tex_mode.upper()})...")
    else:
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
    has_overrides = any([effective_font, fontsize, linespacing, paragraph_style, linenumbers is not None, pagenumbers is not None, numbered_headings is not None, language])
    if fmt in ("pdf", "latex") and has_overrides:
        apply_font_overrides_to_defaults_file(
            config_file, font=effective_font, fontsize=fontsize,
            linespacing=linespacing, paragraph_style=paragraph_style,
            linenumbers=linenumbers, pagenumbers=pagenumbers,
            numbered_headings=numbered_headings,
            language=language
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
        create_si_header(pagenumbers=pagenumbers)
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
    
    if fmt == "latex" and tex_mode == "body":
        convert_tex_file_to_body_only(output_file)

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
    print(box_row("3) LaTeX Source (profile exact)"))
    print(box_row("4) Portable LaTeX"))
    print(box_row("5) LaTeX Body-only (for journal templates)"))
    print(box_bottom())
    fmt_choice = input("Select format [1-5]: ").strip()
    if fmt_choice == "1":
        fmt = "docx"
        tex_mode = None
    elif fmt_choice == "3":
        fmt = "pdf"  # Use PDF profile but output LaTeX
        tex_mode = "source"
    elif fmt_choice == "4":
        fmt = "pdf"  # Use PDF profile but output LaTeX
        tex_mode = "portable"
    elif fmt_choice == "5":
        fmt = "pdf"  # Use PDF profile but output LaTeX
        tex_mode = "body"
    else:
        fmt = "pdf"
        tex_mode = None
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
    spacing_list = ", ".join(LINE_SPACING_PRESETS.keys())
    para_list = ", ".join(PARAGRAPH_STYLE_PRESETS.keys())
    lang_list = ", ".join(LANGUAGE_PRESETS.keys())
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
        config.get("linespacing"),
        config.get("paragraph_style"),
        config.get("linenumbers"),
        config.get("pagenumbers"),
        config.get("numbered_headings"),
        config.get("language"),
        config.get("tex_mode"),
    )
    
    print()
    print("✓ Build complete!")
    print()


if __name__ == "__main__":
    main()
