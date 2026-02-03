#!/usr/bin/env python3
"""
Cross-platform font installer for md-manuscript project.
Downloads and installs all fonts used in the manuscript templates.

Usage: python install-fonts.py [--all|--font FONTNAME]
"""

import os
import sys
import platform
import subprocess
import tempfile
import shutil
import zipfile
import tarfile
import ssl
import json
from pathlib import Path
from urllib.request import urlretrieve, Request, urlopen
from urllib.error import URLError

class FontInstaller:
    def __init__(self):
        self.system = platform.system()
        self.fonts_to_install = []
        
        # Tracking file for installed fonts
        self.tracking_file = Path.home() / '.md-manuscript-fonts.json'
        self.installed_fonts = self.load_tracking()
        
        # Ignore SSL certificate errors (fixes issues on some systems)
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
        except:
            pass
        
        # Define font sources and installation methods
        self.fonts = {
            'libertinus': {
                'name': 'Libertinus',
                'description': 'Default manuscript font',
                'url': 'https://github.com/alerque/libertinus/releases/download/v7.040/Libertinus-7.040.zip',
                'type': 'zip'
            },
            'inter': {
                'name': 'Inter',
                'description': 'Notes profile default',
                'url': 'https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip',
                'type': 'zip'
            },
            'ibm-plex-sans': {
                'name': 'IBM Plex Sans',
                'description': 'IBM Plex Sans family',
                'url': 'https://github.com/IBM/plex/releases/download/v6.4.0/OpenType.zip',
                'type': 'zip',
                'filter': 'IBM-Plex-Sans'
            },
            'ibm-plex-mono': {
                'name': 'IBM Plex Mono',
                'description': 'IBM Plex Mono family',
                'url': 'https://github.com/IBM/plex/releases/download/v6.4.0/OpenType.zip',
                'type': 'zip',
                'filter': 'IBM-Plex-Mono'
            },
            'switzer': {
                'name': 'Switzer',
                'description': 'Modern sans-serif font',
                'url': 'https://api.fontshare.com/v2/fonts/download/switzer',
                'type': 'zip'
            },
            'tex-gyre-pagella': {
                'name': 'TeX Gyre Pagella',
                'description': 'Classic Thesis profile font',
                'url': 'https://www.gust.org.pl/projects/e-foundry/tex-gyre/pagella/qpl2_501otf.zip',
                'type': 'zip'
            },
            'xcharter': {
                'name': 'XCharter',
                'description': 'Charter font family',
                'url': 'https://mirrors.ctan.org/fonts/xcharter.zip',
                'type': 'zip'
            }
        }
    
    def load_tracking(self):
        """Load the tracking file of installed fonts."""
        if self.tracking_file.exists():
            try:
                with open(self.tracking_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_tracking(self):
        """Save the tracking file of installed fonts."""
        try:
            with open(self.tracking_file, 'w') as f:
                json.dump(self.installed_fonts, f, indent=2)
        except Exception as e:
            print(f"  Warning: Could not save tracking file: {e}")
    
    def get_font_dir(self):
        """Get the system font directory based on platform."""
        if self.system == 'Darwin':  # macOS
            return Path.home() / 'Library' / 'Fonts'
        elif self.system == 'Linux':
            return Path.home() / '.local' / 'share' / 'fonts'
        elif self.system == 'Windows':
            return Path(os.environ.get('LOCALAPPDATA', '')) / 'Microsoft' / 'Windows' / 'Fonts'
        else:
            raise OSError(f"Unsupported operating system: {self.system}")
    
    def download_file(self, url, dest):
        """Download a file from URL to destination."""
        print(f"  Downloading from {url}...")
        try:
            # Use Request with User-Agent header for API endpoints
            req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req) as response, open(dest, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            return True
        except URLError as e:
            print(f"  ✗ Download failed: {e}")
            return False
    
    def extract_archive(self, archive_path, extract_to):
        """Extract zip or tar archive."""
        if archive_path.suffix == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        elif '.tar' in archive_path.name:
            with tarfile.open(archive_path, 'r:*') as tar_ref:
                tar_ref.extractall(extract_to)
        else:
            raise ValueError(f"Unsupported archive format: {archive_path}")
    
    def find_font_files(self, directory, font_filter=None):
        """Find all font files (.otf, .ttf) in directory tree."""
        font_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.otf', '.ttf')):
                    # Apply filter if specified (e.g., only IBM-Plex-Sans)
                    if font_filter and font_filter not in root:
                        continue
                    font_files.append(Path(root) / file)
        return font_files
    
    def install_font_file(self, font_file, font_dir, font_key):
        """Install a single font file to the system font directory."""
        dest = font_dir / font_file.name
        
        # Skip if already exists
        if dest.exists():
            return False
        
        shutil.copy2(font_file, dest)
        
        # Track installed file
        if font_key not in self.installed_fonts:
            self.installed_fonts[font_key] = []
        self.installed_fonts[font_key].append(str(dest))
        
        return True
    
    def install_font(self, font_key):
        """Download and install a specific font."""
        font_info = self.fonts[font_key]
        print(f"\n{'='*60}")
        print(f"Installing {font_info['name']}")
        print(f"Description: {font_info['description']}")
        print(f"{'='*60}")
        
        # Get font directory
        font_dir = self.get_font_dir()
        font_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Determine archive filename
            archive_name = f"{font_key}.{font_info['type'].split('.')[0]}"
            archive_path = temp_path / archive_name
            
            # Download font
            if not self.download_file(font_info['url'], archive_path):
                return False
            
            # Extract archive
            print("  Extracting archive...")
            extract_path = temp_path / 'extracted'
            self.extract_archive(archive_path, extract_path)
            
            # Find and install font files (walk entire directory tree)
            print("  Finding font files...")
            font_filter = font_info.get('filter', None)
            font_files = self.find_font_files(extract_path, font_filter)
            
            if not font_files:
                print(f"  ✗ No font files found")
                return False
            
            # Install fonts
            installed_count = 0
            skipped_count = 0
            for font_file in font_files:
                if self.install_font_file(font_file, font_dir, font_key):
                    installed_count += 1
                else:
                    skipped_count += 1
            
            # Save tracking file after each font
            self.save_tracking()
            
            if installed_count > 0:
                print(f"  ✓ Installed {installed_count} font file(s)")
            if skipped_count > 0:
                print(f"  ⊙ Skipped {skipped_count} file(s) (already installed)")
            
            return True
    
    def refresh_font_cache(self):
        """Refresh the system font cache."""
        print("\nRefreshing font cache...")
        
        if self.system == 'Linux':
            try:
                subprocess.run(['fc-cache', '-f', '-v'], check=False, capture_output=True)
                print("  ✓ Font cache refreshed")
            except FileNotFoundError:
                print("  ⊙ fc-cache not found, fonts may require logout/login")
        elif self.system == 'Darwin':
            print("  ⊙ On macOS, fonts are available immediately")
        elif self.system == 'Windows':
            print("  ⊙ On Windows, fonts may require logout/login to be fully available")
    
    def list_fonts(self):
        """List all available fonts."""
        print("\nAvailable fonts:")
        print("="*60)
        for key, info in self.fonts.items():
            print(f"  {key:20} - {info['name']}")
            print(f"  {' '*20}   {info['description']}")
        print("="*60)
    
    def install_all(self):
        """Install all fonts."""
        print(f"\nInstalling fonts to: {self.get_font_dir()}")
        print(f"Platform: {self.system}")
        
        success_count = 0
        fail_count = 0
        
        for font_key in self.fonts.keys():
            try:
                if self.install_font(font_key):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                print(f"  ✗ Installation failed: {e}")
                fail_count += 1
        
        # Refresh font cache
        self.refresh_font_cache()
        
        # Summary
        print("\n" + "="*60)
        print("Installation Summary")
        print("="*60)
        print(f"  Successfully installed: {success_count}/{len(self.fonts)}")
        if fail_count > 0:
            print(f"  Failed: {fail_count}")
        print("="*60)
        
        if self.system == 'Windows':
            print("\nNote: On Windows, you may need to log out and log back in")
            print("      for newly installed fonts to appear in all applications.")
        
        return fail_count == 0
    
    def install_selected(self, font_keys):
        """Install selected fonts."""
        print(f"\nInstalling fonts to: {self.get_font_dir()}")
        print(f"Platform: {self.system}")
        
        success_count = 0
        fail_count = 0
        
        for font_key in font_keys:
            if font_key not in self.fonts:
                print(f"\n✗ Unknown font: {font_key}")
                print("  Use --list to see available fonts")
                fail_count += 1
                continue
            
            try:
                if self.install_font(font_key):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                print(f"  ✗ Installation failed: {e}")
                fail_count += 1
        
        # Refresh font cache
        if success_count > 0:
            self.refresh_font_cache()
        
        # Summary
        print("\n" + "="*60)
        print("Installation Summary")
        print("="*60)
        print(f"  Successfully installed: {success_count}/{len(font_keys)}")
        if fail_count > 0:
            print(f"  Failed: {fail_count}")
        print("="*60)
        
        return fail_count == 0
    
    def list_installed_fonts(self):
        """List currently installed fonts that were tracked by this script."""
        if not self.installed_fonts:
            print("\nNo fonts installed by this script.")
            return
        
        print("\nInstalled fonts (tracked by this script):")
        print("="*60)
        for font_key, files in self.installed_fonts.items():
            if font_key in self.fonts:
                font_name = self.fonts[font_key]['name']
            else:
                font_name = font_key
            print(f"  {font_key:20} - {font_name} ({len(files)} files)")
        print("="*60)
    
    def uninstall_font(self, font_key):
        """Uninstall a specific font."""
        if font_key not in self.installed_fonts:
            print(f"\n✗ Font '{font_key}' not found in tracking file.")
            print("  Either it was not installed by this script or tracking data is missing.")
            return False
        
        font_name = self.fonts.get(font_key, {}).get('name', font_key)
        print(f"\n{'='*60}")
        print(f"Uninstalling {font_name}")
        print(f"{'='*60}")
        
        files = self.installed_fonts[font_key]
        removed_count = 0
        missing_count = 0
        
        for file_path in files:
            file_path = Path(file_path)
            if file_path.exists():
                try:
                    file_path.unlink()
                    removed_count += 1
                except Exception as e:
                    print(f"  ✗ Could not remove {file_path.name}: {e}")
            else:
                missing_count += 1
        
        # Remove from tracking
        del self.installed_fonts[font_key]
        self.save_tracking()
        
        if removed_count > 0:
            print(f"  ✓ Removed {removed_count} font file(s)")
        if missing_count > 0:
            print(f"  ⊙ {missing_count} file(s) already removed")
        
        return True
    
    def uninstall_all(self):
        """Uninstall all tracked fonts."""
        if not self.installed_fonts:
            print("\nNo fonts to uninstall (tracking file is empty).")
            return True
        
        print(f"\nUninstalling fonts from: {self.get_font_dir()}")
        print(f"Platform: {self.system}")
        
        success_count = 0
        fail_count = 0
        
        # Copy keys to avoid modifying dict during iteration
        font_keys = list(self.installed_fonts.keys())
        
        for font_key in font_keys:
            try:
                if self.uninstall_font(font_key):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                print(f"  ✗ Uninstallation failed: {e}")
                fail_count += 1
        
        # Refresh font cache
        self.refresh_font_cache()
        
        # Summary
        print("\n" + "="*60)
        print("Uninstallation Summary")
        print("="*60)
        print(f"  Successfully uninstalled: {success_count}/{len(font_keys)}")
        if fail_count > 0:
            print(f"  Failed: {fail_count}")
        print("="*60)
        
        return fail_count == 0
    
    def uninstall_selected(self, font_keys):
        """Uninstall selected fonts."""
        print(f"\nUninstalling fonts from: {self.get_font_dir()}")
        print(f"Platform: {self.system}")
        
        success_count = 0
        fail_count = 0
        
        for font_key in font_keys:
            if font_key not in self.installed_fonts:
                print(f"\n✗ Font '{font_key}' not tracked")
                print("  Use --list-installed to see installed fonts")
                fail_count += 1
                continue
            
            try:
                if self.uninstall_font(font_key):
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                print(f"  ✗ Uninstallation failed: {e}")
                fail_count += 1
        
        # Refresh font cache
        if success_count > 0:
            self.refresh_font_cache()
        
        # Summary
        print("\n" + "="*60)
        print("Uninstallation Summary")
        print("="*60)
        print(f"  Successfully uninstalled: {success_count}/{len(font_keys)}")
        if fail_count > 0:
            print(f"  Failed: {fail_count}")
        print("="*60)
        
        return fail_count == 0


def interactive_mode(installer):
    """Run interactive wizard for font installation."""
    print("\n" + "="*60)
    print("  Font Installation Wizard")
    print("="*60)
    print(f"\nPlatform: {installer.system}")
    print(f"Install location: {installer.get_font_dir()}\n")
    
    # Ask installation type
    print("What would you like to do?")
    print("  1. Install all fonts (recommended)")
    print("  2. Select specific fonts to install")
    print("  3. Uninstall all fonts")
    print("  4. Uninstall specific fonts")
    print("  5. List available fonts")
    print("  6. List installed fonts")
    print("  7. Cancel")
    
    while True:
        choice = input("\nEnter your choice (1-7): ").strip()
        if choice in ['1', '2', '3', '4', '5', '6', '7']:
            break
        print("Invalid choice. Please enter 1-7.")
    
    if choice == '7':
        print("Cancelled.")
        return 0
    
    if choice == '5':
        installer.list_fonts()
        return 0
    
    if choice == '6':
        installer.list_installed_fonts()
        return 0
    
    if choice == '3':
        # Uninstall all fonts
        if not installer.installed_fonts:
            print("\nNo fonts to uninstall (tracking file is empty).")
            return 0
        
        print("\n" + "="*60)
        print("You are about to UNINSTALL all tracked fonts:")
        for font_key, files in installer.installed_fonts.items():
            font_name = installer.fonts.get(font_key, {}).get('name', font_key)
            print(f"  • {font_name} ({len(files)} files)")
        print("="*60)
        
        confirm = input("\nProceed with uninstallation? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Uninstallation cancelled.")
            return 0
        
        success = installer.uninstall_all()
        return 0 if success else 1
    
    if choice == '4':
        # Uninstall specific fonts
        if not installer.installed_fonts:
            print("\nNo fonts to uninstall (tracking file is empty).")
            return 0
        
        print("\n" + "="*60)
        print("Installed fonts:")
        print("="*60)
        
        font_list = list(installer.installed_fonts.items())
        for i, (key, files) in enumerate(font_list, 1):
            font_name = installer.fonts.get(key, {}).get('name', key)
            print(f"  {i}. {font_name:<25} ({len(files)} files)")
        
        print("="*60)
        print("\nEnter font numbers separated by spaces (e.g., '1 3 5')")
        print("Or enter 'all' to uninstall all fonts")
        
        while True:
            selection = input("\nYour selection: ").strip()
            
            if selection.lower() == 'all':
                selected_keys = list(installer.installed_fonts.keys())
                break
            
            try:
                indices = [int(x.strip()) for x in selection.split()]
                if all(1 <= i <= len(font_list) for i in indices):
                    selected_keys = [font_list[i-1][0] for i in indices]
                    break
                else:
                    print(f"Please enter numbers between 1 and {len(font_list)}")
            except ValueError:
                print("Invalid input. Please enter numbers separated by spaces.")
        
        # Confirm selection
        print("\n" + "="*60)
        print("You selected to UNINSTALL:")
        for key in selected_keys:
            font_name = installer.fonts.get(key, {}).get('name', key)
            file_count = len(installer.installed_fonts.get(key, []))
            print(f"  • {font_name} ({file_count} files)")
        print("="*60)
        
        confirm = input("\nProceed with uninstallation? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Uninstallation cancelled.")
            return 0
        
        success = installer.uninstall_selected(selected_keys)
        return 0 if success else 1
    
    if choice == '1':
        # Install all fonts
        print("\n" + "="*60)
        print("You are about to install ALL fonts:")
        for key, info in installer.fonts.items():
            print(f"  • {info['name']} - {info['description']}")
        print("="*60)
        
        confirm = input("\nProceed with installation? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Installation cancelled.")
            return 0
        
        success = installer.install_all()
        return 0 if success else 1
    
    if choice == '2':
        # Select specific fonts
        print("\n" + "="*60)
        print("Available fonts:")
        print("="*60)
        
        font_list = list(installer.fonts.items())
        for i, (key, info) in enumerate(font_list, 1):
            print(f"  {i}. {info['name']:<25} - {info['description']}")
        
        print("="*60)
        print("\nEnter font numbers separated by spaces (e.g., '1 3 5')")
        print("Or enter 'all' to select all fonts")
        
        while True:
            selection = input("\nYour selection: ").strip()
            
            if selection.lower() == 'all':
                selected_keys = list(installer.fonts.keys())
                break
            
            try:
                indices = [int(x.strip()) for x in selection.split()]
                if all(1 <= i <= len(font_list) for i in indices):
                    selected_keys = [font_list[i-1][0] for i in indices]
                    break
                else:
                    print(f"Please enter numbers between 1 and {len(font_list)}")
            except ValueError:
                print("Invalid input. Please enter numbers separated by spaces.")
        
        # Confirm selection
        print("\n" + "="*60)
        print("You selected:")
        for key in selected_keys:
            info = installer.fonts[key]
            print(f"  • {info['name']} - {info['description']}")
        print("="*60)
        
        confirm = input("\nProceed with installation? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Installation cancelled.")
            return 0
        
        success = installer.install_selected(selected_keys)
        return 0 if success else 1


def print_usage():
    """Print usage information."""
    print("""
Font Installer/Uninstaller for md-manuscript
=============================================

Usage:
    python install-fonts.py [options]

Options:
    (no options)         Run interactive wizard (default)
    --all                Install all fonts without prompts
    --font FONTNAME      Install specific font(s) without prompts
    --uninstall-all      Uninstall all tracked fonts
    --uninstall FONTNAME Uninstall specific font(s)
    --list               List available fonts
    --list-installed     List installed fonts (tracked by this script)
    --help               Show this help message

Examples:
    python install-fonts.py                              # Interactive wizard
    python install-fonts.py --all                        # Install all
    python install-fonts.py --font libertinus            # Install one font
    python install-fonts.py --font libertinus inter      # Install multiple
    python install-fonts.py --uninstall-all              # Uninstall all
    python install-fonts.py --uninstall libertinus inter # Uninstall specific
    python install-fonts.py --list                       # List available
    python install-fonts.py --list-installed             # List installed

Available fonts:
    libertinus, inter, ibm-plex-sans, ibm-plex-mono,
    switzer, tex-gyre-pagella, xcharter

Note: 
    - Arial/Helvetica and Latin Modern are typically pre-installed
    - Fonts are tracked in ~/.md-manuscript-fonts.json
    - Only fonts installed by this script can be uninstalled
""")


def main():
    """Main entry point."""
    args = sys.argv[1:]
    
    installer = FontInstaller()
    
    # Parse arguments
    if '--help' in args or '-h' in args:
        print_usage()
        return 0
    
    if '--list' in args:
        installer.list_fonts()
        return 0
    
    if '--list-installed' in args:
        installer.list_installed_fonts()
        return 0
    
    if '--uninstall-all' in args:
        success = installer.uninstall_all()
        return 0 if success else 1
    
    if '--uninstall' in args:
        try:
            idx = args.index('--uninstall')
            # Collect all font names after --uninstall until next --option or end
            font_keys = []
            for i in range(idx + 1, len(args)):
                if args[i].startswith('--'):
                    break
                font_keys.append(args[i])
            
            if not font_keys:
                print("Error: --uninstall requires at least one font name")
                print("Use --list-installed to see installed fonts")
                return 1
            
            success = installer.uninstall_selected(font_keys)
            return 0 if success else 1
        except ValueError:
            pass
    
    if '--font' in args:
        try:
            idx = args.index('--font')
            # Collect all font names after --font until next --option or end
            font_keys = []
            for i in range(idx + 1, len(args)):
                if args[i].startswith('--'):
                    break
                font_keys.append(args[i])
            
            if not font_keys:
                print("Error: --font requires at least one font name")
                print("Use --list to see available fonts")
                return 1
            
            success = installer.install_selected(font_keys)
            return 0 if success else 1
        except ValueError:
            pass
    
    if '--all' in args:
        # Install all fonts without prompts
        success = installer.install_all()
        return 0 if success else 1
    
    # Default: run interactive wizard
    return interactive_mode(installer)


if __name__ == '__main__':
    sys.exit(main())
