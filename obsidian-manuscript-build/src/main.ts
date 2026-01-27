import {
	App,
	Modal,
	Notice,
	Plugin,
	PluginSettingTab,
	Setting,
	TFile,
	DropdownComponent,
	ToggleComponent,
	ButtonComponent,
} from "obsidian";
import { spawn, ChildProcess } from "child_process";
import * as path from "path";

// ============================================================================
// Types & Interfaces
// ============================================================================

interface ManuscriptBuildSettings {
	pythonPath: string;
	buildScriptPath: string;
	defaultProfile: string;
	defaultFont: string;
	defaultFontSize: string;
	defaultCitationStyle: string;
	showNotifications: boolean;
	autoOpenExport: boolean;
}

interface BuildConfig {
	sourceFile: string;
	frontmatterFile: string | null;
	profile: string;
	usePng: boolean;
	includeSiRefs: boolean;
	siFile: string | null;
	isSi: boolean;
	font: string;
	fontSize: string;
	citationStyle: string;
	lineSpacing: string;
	paragraphStyle: string;
	lineNumbers: boolean | null;
	numberedHeadings: boolean | null;
	language: string;
}

interface ProfileInfo {
	id: string;
	name: string;
	format: string;
	category: string;
}

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_SETTINGS: ManuscriptBuildSettings = {
	pythonPath: "python3",
	buildScriptPath: "build.py",
	defaultProfile: "pdf-default",
	defaultFont: "",
	defaultFontSize: "11pt",
	defaultCitationStyle: "vancouver",
	showNotifications: true,
	autoOpenExport: false,
};

const FONT_PRESETS: Record<string, string> = {
	libertinus: "Libertinus (Default)",
	"libertinus-serif": "Libertinus Serif",
	"libertinus-sans": "Libertinus Sans",
	inter: "Inter",
	"ibm-plex-sans": "IBM Plex Sans",
	"ibm-plex-serif": "IBM Plex Serif",
	switzer: "Switzer",
	times: "Times/TeX Gyre Termes",
	palatino: "Palatino/TeX Gyre Pagella",
	arial: "Arial",
	helvetica: "Helvetica-like (TeX Gyre Heros)",
	charter: "Charter",
	"computer-modern": "Computer Modern (LaTeX default)",
};

const FONT_SIZES = ["9pt", "10pt", "11pt", "12pt"];

// Line spacing presets
const LINE_SPACING_PRESETS: Record<string, string> = {
	"": "Profile Default",
	single: "Single (1.0)",
	compact: "Compact (1.15)",
	normal: "Normal (1.25)",
	relaxed: "Relaxed (1.5)",
	double: "Double (2.0)",
};

// Paragraph style presets
const PARAGRAPH_STYLE_PRESETS: Record<string, string> = {
	"": "Profile Default",
	indent: "Indented (American)",
	gap: "Gap (European)",
	both: "Gap + Indent (Both)",
};

// Language presets
const LANGUAGE_PRESETS: Record<string, string> = {
	"": "Default (English)",
	en: "English",
	de: "German (Deutsch)",
	fr: "French (Français)",
	es: "Spanish (Español)",
	it: "Italian (Italiano)",
	pt: "Portuguese (Português)",
	nl: "Dutch (Nederlands)",
	pl: "Polish (Polski)",
	ru: "Russian (Русский)",
	zh: "Chinese (中文)",
	ja: "Japanese (日本語)",
};

// Citation styles are loaded dynamically from resources/citation_styles/
// This is a fallback map for display names of common styles
const CITATION_STYLE_NAMES: Record<string, string> = {
	vancouver: "Vancouver",
	nature: "Nature",
	cell: "Cell",
	science: "Science",
	pnas: "PNAS",
	plos: "PLOS",
	apa: "APA 7th Edition",
	"apa-7th-edition": "APA 7th Edition",
	chicago: "Chicago Author-Date",
	"chicago-author-date": "Chicago Author-Date",
	"acs-synthetic-biology": "ACS Synthetic Biology",
	"angewandte-chemie": "Angewandte Chemie",
	"nucleic-acids-research": "Nucleic Acids Research",
};

// Profiles are loaded dynamically from resources/profiles/
// This is a fallback in case dynamic loading fails
const FALLBACK_PROFILES: ProfileInfo[] = [
	{ id: "docx-manuscript", name: "Word Manuscript", format: "docx", category: "General" },
	{ id: "pdf-default", name: "PDF Default", format: "pdf", category: "General" },
];

// ============================================================================
// Main Plugin Class
// ============================================================================

export default class ManuscriptBuildPlugin extends Plugin {
	settings: ManuscriptBuildSettings;
	private buildProcess: ChildProcess | null = null;

	async onload() {
		await this.loadSettings();

		// Add ribbon icon - Open Build Dialog
		this.addRibbonIcon("file-output", "Build Manuscript", async () => {
			const lastConfig = await this.loadLastBuildConfig();
			new BuildModal(this.app, this, lastConfig).open();
		});

		// Add command: Open Build Modal
		this.addCommand({
			id: "open-build-modal",
			name: "Open Build Dialog",
			callback: async () => {
				const lastConfig = await this.loadLastBuildConfig();
				new BuildModal(this.app, this, lastConfig).open();
			},
		});

		// Add command: Build current file
		this.addCommand({
			id: "build-current-file",
			name: "Build Current File",
			callback: () => {
				const activeFile = this.app.workspace.getActiveFile();
				if (activeFile && activeFile.extension === "md") {
					this.buildWithDefaults(activeFile.name);
				} else {
					new Notice("No markdown file is currently active");
				}
			},
		});

		// Add settings tab
		this.addSettingTab(new ManuscriptBuildSettingTab(this.app, this));
	}

	onunload() {
		if (this.buildProcess) {
			this.buildProcess.kill();
		}
	}

	async loadSettings() {
		this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
	}

	async saveSettings() {
		await this.saveData(this.settings);
	}

	getVaultPath(): string {
		const adapter = this.app.vault.adapter as any;
		return adapter.basePath || "";
	}

	getMarkdownFiles(): string[] {
		const files = this.app.vault.getMarkdownFiles();
		return files
			// Only include files in root directory (no "/" in path means root)
			.filter((f) => !f.path.includes("/"))
			.map((f) => f.name)
			.filter((name) => !name.startsWith("_") && name.toLowerCase() !== "readme.md")
			.sort();
	}

	getCitationStyles(): Record<string, string> {
		const styles: Record<string, string> = {};
		const vaultPath = this.getVaultPath();
		const stylesDir = path.join(vaultPath, "resources", "citation_styles");
		
		try {
			const fs = require("fs");
			if (fs.existsSync(stylesDir)) {
				const files = fs.readdirSync(stylesDir) as string[];
				files
					.filter((f: string) => f.endsWith(".csl"))
					.forEach((f: string) => {
						const id = f.replace(".csl", "");
						// Use known display name or generate from filename
						const displayName = CITATION_STYLE_NAMES[id] || this.formatStyleName(id);
						styles[id] = displayName;
					});
			}
		} catch (e) {
			console.error("Failed to read citation styles:", e);
		}
		
		// If no styles found, return fallback defaults
		if (Object.keys(styles).length === 0) {
			return { vancouver: "Vancouver", nature: "Nature" };
		}
		
		// Sort alphabetically by display name
		const sorted: Record<string, string> = {};
		Object.entries(styles)
			.sort((a, b) => a[1].localeCompare(b[1]))
			.forEach(([k, v]) => { sorted[k] = v; });
		
		return sorted;
	}

	private formatStyleName(id: string): string {
		// Convert "acs-synthetic-biology" to "ACS Synthetic Biology"
		return id
			.split("-")
			.map(word => {
				// Keep acronyms uppercase
				if (word.length <= 3 && word === word.toLowerCase()) {
					return word.toUpperCase();
				}
				return word.charAt(0).toUpperCase() + word.slice(1);
			})
			.join(" ");
	}

	getProfiles(): ProfileInfo[] {
		const profiles: ProfileInfo[] = [];
		const vaultPath = this.getVaultPath();
		const profilesDir = path.join(vaultPath, "resources", "profiles");

		try {
			const fs = require("fs");
			if (fs.existsSync(profilesDir)) {
				const files = fs.readdirSync(profilesDir) as string[];
				files
					.filter((f: string) => f.endsWith(".yaml") && !f.startsWith("_"))
					.forEach((f: string) => {
						const id = f.replace(".yaml", "");
						const filePath = path.join(profilesDir, f);
						try {
							const content = fs.readFileSync(filePath, "utf8") as string;
							const profileInfo = this.parseProfileYaml(id, content);
							if (profileInfo) {
								profiles.push(profileInfo);
							}
						} catch (e) {
							// Skip files that can't be read
							console.error(`Failed to read profile ${f}:`, e);
						}
					});
			}
		} catch (e) {
			console.error("Failed to read profiles directory:", e);
		}

		// If no profiles found, return fallback defaults
		if (profiles.length === 0) {
			return FALLBACK_PROFILES;
		}

		// Sort by category then name
		return profiles.sort((a, b) => {
			const catOrder: Record<string, number> = { General: 0, Thesis: 1, Journals: 2 };
			const catA = catOrder[a.category] ?? 99;
			const catB = catOrder[b.category] ?? 99;
			if (catA !== catB) return catA - catB;
			return a.name.localeCompare(b.name);
		});
	}

	private parseProfileYaml(id: string, content: string): ProfileInfo | null {
		// Parse profile metadata from YAML content
		// Look for profile: block with name, description, format
		const nameMatch = content.match(/^\s*name:\s*["']?([^"'\n]+)["']?\s*$/m);
		const formatMatch = content.match(/^\s*format:\s*["']?([^"'\n]+)["']?\s*$/m);

		if (!nameMatch) {
			// No profile metadata, generate from filename
			return {
				id,
				name: this.formatStyleName(id),
				format: id.startsWith("docx") ? "docx" : "pdf",
				category: this.inferCategory(id),
			};
		}

		const name = nameMatch[1].trim();
		const format = formatMatch ? formatMatch[1].trim() : (id.startsWith("docx") ? "docx" : "pdf");

		return {
			id,
			name,
			format,
			category: this.inferCategory(id),
		};
	}

	private inferCategory(id: string): string {
		if (id.includes("thesis")) return "Thesis";
		if (id.includes("nature") || id.includes("cell") || id.includes("journal")) return "Journals";
		return "General";
	}

	async buildWithDefaults(sourceFile: string) {
		const config: BuildConfig = {
			sourceFile,
			frontmatterFile: null,
			profile: this.settings.defaultProfile,
			usePng: false,
			includeSiRefs: false,
			siFile: null,
			isSi: false,
			font: this.settings.defaultFont,
			fontSize: this.settings.defaultFontSize,
			citationStyle: this.settings.defaultCitationStyle,
			lineSpacing: "",
			paragraphStyle: "",
			lineNumbers: null,
			numberedHeadings: null,
			language: "",
		};
		this.executeBuild(config);
	}

	async loadLastBuildConfig(): Promise<BuildConfig | null> {
		try {
			const configPath = path.join(this.getVaultPath(), ".build_config.json");
			const fs = require("fs");
			if (fs.existsSync(configPath)) {
				const content = fs.readFileSync(configPath, "utf8");
				const data = JSON.parse(content);
				return {
					sourceFile: data.source_file || "",
					frontmatterFile: data.frontmatter_file || null,
					profile: data.profile || this.settings.defaultProfile,
					usePng: data.use_png || false,
					includeSiRefs: data.include_si_refs || false,
					siFile: data.si_file || null,
					isSi: data.is_si || false,
					font: data.font !== undefined ? data.font : this.settings.defaultFont,
					fontSize: data.fontsize || this.settings.defaultFontSize,
					citationStyle: data.citation_style || this.settings.defaultCitationStyle,
					lineSpacing: data.linespacing || "",
					paragraphStyle: data.paragraph_style || "",
					lineNumbers: data.linenumbers !== undefined ? data.linenumbers : null,
					numberedHeadings: data.numbered_headings !== undefined ? data.numbered_headings : null,
					language: data.language || "",
				};
			}
		} catch (e) {
			console.error("Failed to load last build config:", e);
		}
		return null;
	}

	saveBuildConfig(config: BuildConfig) {
		const fs = require("fs");
		const configPath = path.join(this.getVaultPath(), ".build_config.json");
		const data = {
			source_file: config.sourceFile,
			frontmatter_file: config.frontmatterFile,
			profile: config.profile,
			use_png: config.usePng,
			include_si_refs: config.includeSiRefs,
			si_file: config.siFile,
			is_si: config.isSi,
			font: config.font || null,
			fontsize: config.fontSize,
			citation_style: config.citationStyle,
			linespacing: config.lineSpacing || null,
			paragraph_style: config.paragraphStyle || null,
			linenumbers: config.lineNumbers,
			numbered_headings: config.numberedHeadings,
			language: config.language || null,
		};
		try {
			fs.writeFileSync(configPath, JSON.stringify(data, null, 2));
		} catch (e) {
			console.error("Failed to save build config:", e);
		}
	}

	executeBuild(config: BuildConfig) {
		// Save config immediately so settings are preserved
		this.saveBuildConfig(config);

		const vaultPath = this.getVaultPath();
		const args = this.buildCommandArgs(config);

		if (this.settings.showNotifications) {
			new Notice(`Building ${config.sourceFile}...`);
		}

		const outputModal = new BuildOutputModal(this.app, config.sourceFile);
		outputModal.open();

		this.buildProcess = spawn(this.settings.pythonPath, args, {
			cwd: vaultPath,
			env: { ...process.env, PAGER: "cat" },
		});

		let stdout = "";
		let stderr = "";

		this.buildProcess.stdout?.on("data", (data) => {
			const text = data.toString();
			stdout += text;
			outputModal.appendOutput(text);
		});

		this.buildProcess.stderr?.on("data", (data) => {
			const text = data.toString();
			stderr += text;
			outputModal.appendOutput(text, true);
		});

		this.buildProcess.on("close", (code) => {
			this.buildProcess = null;
			if (code === 0) {
				outputModal.setSuccess();
				if (this.settings.showNotifications) {
					new Notice("✓ Build complete!");
				}
				if (this.settings.autoOpenExport) {
					this.openExportFolder();
				}
			} else {
				outputModal.setError();
				if (this.settings.showNotifications) {
					new Notice("✗ Build failed. Check output for details.");
				}
			}
		});

		this.buildProcess.on("error", (err) => {
			this.buildProcess = null;
			outputModal.appendOutput(`\nError: ${err.message}`, true);
			outputModal.setError();
			new Notice(`Build error: ${err.message}`);
		});
	}

	private buildCommandArgs(config: BuildConfig): string[] {
		const args = [this.settings.buildScriptPath];

		args.push(`--source=${config.sourceFile}`);

		if (config.frontmatterFile) {
			args.push(`--frontmatter=${config.frontmatterFile}`);
		}

		args.push(`--profile=${config.profile}`);

		if (config.usePng) {
			args.push("--png");
		}

		if (config.includeSiRefs) {
			args.push("--include-si-refs");
			if (config.siFile) {
				args.push(`--si-file=${config.siFile}`);
			}
		}

		if (config.isSi) {
			args.push("--si");
		}

		if (config.font) {
			args.push(`--font=${config.font}`);
		}

		if (config.fontSize) {
			args.push(`--fontsize=${config.fontSize}`);
		}

		if (config.lineSpacing) {
			args.push(`--linespacing=${config.lineSpacing}`);
		}

		if (config.paragraphStyle) {
			args.push(`--paragraph-style=${config.paragraphStyle}`);
		}

		if (config.lineNumbers === true) {
			args.push("--linenumbers");
		} else if (config.lineNumbers === false) {
			args.push("--no-linenumbers");
		}

		if (config.numberedHeadings === true) {
			args.push("--numbered-headings");
		} else if (config.numberedHeadings === false) {
			args.push("--no-numbered-headings");
		}

		if (config.language) {
			args.push(`--lang=${config.language}`);
		}

		if (config.citationStyle) {
			args.push(`--csl=${config.citationStyle}`);
		}

		return args;
	}

	openExportFolder() {
		const exportPath = path.join(this.getVaultPath(), "export");
		const { shell } = require("electron");
		shell.openPath(exportPath);
	}

	openCitationStylesFolder() {
		const stylesPath = path.join(this.getVaultPath(), "resources", "citation_styles");
		const fs = require("fs");
		// Create folder if it doesn't exist
		if (!fs.existsSync(stylesPath)) {
			fs.mkdirSync(stylesPath, { recursive: true });
		}
		const { shell } = require("electron");
		shell.openPath(stylesPath);
	}
}

// ============================================================================
// Build Modal
// ============================================================================

class BuildModal extends Modal {
	plugin: ManuscriptBuildPlugin;
	config: BuildConfig;
	private lastConfig: BuildConfig | null = null;

	// UI Components
	private sourceDropdown: DropdownComponent;
	private frontmatterDropdown: DropdownComponent;
	private formatDropdown: DropdownComponent;
	private profileDropdown: DropdownComponent;
	private fontDropdown: DropdownComponent;
	private fontSizeDropdown: DropdownComponent;
	private lineSpacingDropdown: DropdownComponent;
	private paragraphStyleDropdown: DropdownComponent;
	private lineNumbersDropdown: DropdownComponent;
	private numberedHeadingsDropdown: DropdownComponent;
	private languageDropdown: DropdownComponent;
	private citationDropdown: DropdownComponent;
	private siRefsToggle: ToggleComponent;
	private siFileDropdown: DropdownComponent;
	private siFileContainer: HTMLElement;
	private isSiToggle: ToggleComponent;
	private pngToggle: ToggleComponent;
	private pngContainer: HTMLElement;

	constructor(app: App, plugin: ManuscriptBuildPlugin, lastConfig: BuildConfig | null = null) {
		super(app);
		this.plugin = plugin;
		this.lastConfig = lastConfig;
		
		// Use last config if available, otherwise fall back to plugin defaults
		if (lastConfig) {
			this.config = { ...lastConfig };
		} else {
			this.config = {
				sourceFile: "",
				frontmatterFile: null,
				profile: plugin.settings.defaultProfile,
				usePng: false,
				includeSiRefs: false,
				siFile: null,
				isSi: false,
				font: plugin.settings.defaultFont,
				fontSize: plugin.settings.defaultFontSize,
				citationStyle: plugin.settings.defaultCitationStyle,
				lineSpacing: "",
				paragraphStyle: "",
				lineNumbers: null,
				numberedHeadings: null,
				language: "",
			};
		}
	}

	onOpen() {
		const { contentEl } = this;
		contentEl.empty();
		contentEl.addClass("manuscript-build-modal");

		// Header
		contentEl.createEl("h2", { text: "Build Manuscript", cls: "modal-title" });

		const mdFiles = this.plugin.getMarkdownFiles();

		// ─────────────────────────────────────────────────────────────────────
		// Document Selection Section
		// ─────────────────────────────────────────────────────────────────────
		this.createSectionHeader(contentEl, "Document");

		// Source file
		new Setting(contentEl)
			.setName("Source File")
			.setDesc("The main document to build")
			.addDropdown((dropdown) => {
				this.sourceDropdown = dropdown;
				mdFiles.forEach((file) => {
					dropdown.addOption(file, file);
				});
				if (mdFiles.length > 0) {
					// Use lastConfig value if available and valid, otherwise find sensible default
					if (this.lastConfig?.sourceFile && mdFiles.includes(this.lastConfig.sourceFile)) {
						this.config.sourceFile = this.lastConfig.sourceFile;
					} else if (!this.config.sourceFile || !mdFiles.includes(this.config.sourceFile)) {
						const maintext = mdFiles.find((f) => f.includes("maintext"));
						this.config.sourceFile = maintext || mdFiles[0];
					}
					dropdown.setValue(this.config.sourceFile);
				}
				dropdown.onChange((value) => {
					this.config.sourceFile = value;
				});
			});

		// Frontmatter file
		new Setting(contentEl)
			.setName("Frontmatter")
			.setDesc("Optional file to prepend (title, authors, etc.)")
			.addDropdown((dropdown) => {
				this.frontmatterDropdown = dropdown;
				dropdown.addOption("", "None");
				mdFiles.forEach((file) => {
					dropdown.addOption(file, file);
				});
				// Use lastConfig value if available, otherwise find sensible default
				if (this.lastConfig?.frontmatterFile && mdFiles.includes(this.lastConfig.frontmatterFile)) {
					this.config.frontmatterFile = this.lastConfig.frontmatterFile;
					dropdown.setValue(this.lastConfig.frontmatterFile);
				} else if (this.config.frontmatterFile && mdFiles.includes(this.config.frontmatterFile)) {
					dropdown.setValue(this.config.frontmatterFile);
				} else {
					const frontmatter = mdFiles.find((f) => f.includes("frontmatter"));
					if (frontmatter) {
						this.config.frontmatterFile = frontmatter;
						dropdown.setValue(frontmatter);
					}
				}
				dropdown.onChange((value) => {
					this.config.frontmatterFile = value || null;
				});
			});

		// ─────────────────────────────────────────────────────────────────────
		// Output Section
		// ─────────────────────────────────────────────────────────────────────
		this.createSectionHeader(contentEl, "Output");

		// Format selection
		const currentFormat = this.config.profile.startsWith("docx") ? "docx" : "pdf";
		new Setting(contentEl)
			.setName("Format")
			.setDesc("Output document format")
			.addDropdown((dropdown) => {
				this.formatDropdown = dropdown;
				dropdown.addOption("pdf", "PDF");
				dropdown.addOption("docx", "Word Document (DOCX)");
				dropdown.setValue(currentFormat);
				dropdown.onChange((value) => {
					this.updateProfilesForFormat(value);
					this.updateFormatOptions(value);
				});
			});

		// Profile selection
		new Setting(contentEl)
			.setName("Profile")
			.setDesc("Document style and layout")
			.addDropdown((dropdown) => {
				this.profileDropdown = dropdown;
				this.populateProfiles(dropdown, currentFormat);
				dropdown.setValue(this.config.profile);
				dropdown.onChange((value) => {
					this.config.profile = value;
				});
			});

		// PNG conversion (DOCX only)
		this.pngContainer = contentEl.createDiv();
		new Setting(this.pngContainer)
			.setName("Convert Figures to PNG")
			.setDesc("Convert PDF figures to PNG for Word compatibility")
			.addToggle((toggle) => {
				this.pngToggle = toggle;
				toggle.setValue(this.config.usePng);
				toggle.onChange((value) => {
					this.config.usePng = value;
				});
			});
		// Show/hide PNG option based on format (must be after pngContainer is created)
		this.updateFormatOptions(currentFormat);

		// ─────────────────────────────────────────────────────────────────────
		// Typography Section (PDF only)
		// ─────────────────────────────────────────────────────────────────────
		this.createSectionHeader(contentEl, "Typography");

		// Font
		new Setting(contentEl)
			.setName("Font")
			.setDesc("Document typeface")
			.addDropdown((dropdown) => {
				this.fontDropdown = dropdown;
				dropdown.addOption("", "Profile Default");
				Object.entries(FONT_PRESETS).forEach(([key, name]) => {
					dropdown.addOption(key, name);
				});
				dropdown.setValue(this.config.font || "");
				dropdown.onChange((value) => {
					this.config.font = value;
				});
			});

		// Font size
		new Setting(contentEl)
			.setName("Font Size")
			.setDesc("Base font size")
			.addDropdown((dropdown) => {
				this.fontSizeDropdown = dropdown;
				FONT_SIZES.forEach((size) => {
					dropdown.addOption(size, size);
				});
				dropdown.setValue(this.config.fontSize);
				dropdown.onChange((value) => {
					this.config.fontSize = value;
				});
			});

		// Line spacing
		new Setting(contentEl)
			.setName("Line Spacing")
			.setDesc("Override line spacing (leave as Profile Default to use profile setting)")
			.addDropdown((dropdown) => {
				this.lineSpacingDropdown = dropdown;
				Object.entries(LINE_SPACING_PRESETS).forEach(([key, name]) => {
					dropdown.addOption(key, name);
				});
				dropdown.setValue(this.config.lineSpacing);
				dropdown.onChange((value) => {
					this.config.lineSpacing = value;
				});
			});

		// Paragraph style
		new Setting(contentEl)
			.setName("Paragraph Style")
			.setDesc("Indented, Gap, or Both")
			.addDropdown((dropdown) => {
				this.paragraphStyleDropdown = dropdown;
				Object.entries(PARAGRAPH_STYLE_PRESETS).forEach(([key, name]) => {
					dropdown.addOption(key, name);
				});
				dropdown.setValue(this.config.paragraphStyle);
				dropdown.onChange((value) => {
					this.config.paragraphStyle = value;
				});
			});

		// Line numbers
		new Setting(contentEl)
			.setName("Line Numbers")
			.setDesc("Override line numbering (three-state: Profile Default / On / Off)")
			.addDropdown((dropdown) => {
				this.lineNumbersDropdown = dropdown;
				dropdown.addOption("default", "Profile Default");
				dropdown.addOption("on", "On");
				dropdown.addOption("off", "Off");
				const currentValue = this.config.lineNumbers === null ? "default" : (this.config.lineNumbers ? "on" : "off");
				dropdown.setValue(currentValue);
				dropdown.onChange((value) => {
					if (value === "default") {
						this.config.lineNumbers = null;
					} else {
						this.config.lineNumbers = value === "on";
					}
				});
			});

		// Numbered headings
		new Setting(contentEl)
			.setName("Numbered Headings")
			.setDesc("Override heading numbering (three-state: Profile Default / On / Off)")
			.addDropdown((dropdown) => {
				this.numberedHeadingsDropdown = dropdown;
				dropdown.addOption("default", "Profile Default");
				dropdown.addOption("on", "Numbered");
				dropdown.addOption("off", "Unnumbered");
				const currentValue = this.config.numberedHeadings === null ? "default" : (this.config.numberedHeadings ? "on" : "off");
				dropdown.setValue(currentValue);
				dropdown.onChange((value) => {
					if (value === "default") {
						this.config.numberedHeadings = null;
					} else {
						this.config.numberedHeadings = value === "on";
					}
				});
			});

		// Language
		new Setting(contentEl)
			.setName("Document Language")
			.setDesc("Set document language for hyphenation and localization")
			.addDropdown((dropdown) => {
				this.languageDropdown = dropdown;
				Object.entries(LANGUAGE_PRESETS).forEach(([key, name]) => {
					dropdown.addOption(key, name);
				});
				dropdown.setValue(this.config.language);
				dropdown.onChange((value) => {
					this.config.language = value;
				});
			});

		// ─────────────────────────────────────────────────────────────────────
		// Citations Section
		// ─────────────────────────────────────────────────────────────────────
		this.createSectionHeader(contentEl, "Citations");

		// Citation style (dynamically loaded from resources/citation_styles/)
		const citationStyles = this.plugin.getCitationStyles();
		new Setting(contentEl)
			.setName("Citation Style")
			.setDesc("Bibliography format")
			.addDropdown((dropdown) => {
				this.citationDropdown = dropdown;
				Object.entries(citationStyles).forEach(([key, name]) => {
					dropdown.addOption(key, name);
				});
				dropdown.setValue(this.config.citationStyle);
				dropdown.onChange((value) => {
					this.config.citationStyle = value;
				});
			});

		// ─────────────────────────────────────────────────────────────────────
		// Supporting Information Section
		// ─────────────────────────────────────────────────────────────────────
		this.createSectionHeader(contentEl, "Supporting Information");

		// Include SI refs
		new Setting(contentEl)
			.setName("Include SI References")
			.setDesc("Add SI citations to the main bibliography")
			.addToggle((toggle) => {
				this.siRefsToggle = toggle;
				toggle.setValue(this.config.includeSiRefs);
				toggle.onChange((value) => {
					this.config.includeSiRefs = value;
					this.siFileContainer.style.display = value ? "block" : "none";
				});
			});

		// SI file selection
		this.siFileContainer = contentEl.createDiv();
		new Setting(this.siFileContainer)
			.setName("SI File")
			.setDesc("File containing SI references")
			.addDropdown((dropdown) => {
				this.siFileDropdown = dropdown;
				mdFiles.forEach((file) => {
					dropdown.addOption(file, file);
				});
				// Use lastConfig value if available, otherwise find sensible default
				if (this.lastConfig?.siFile && mdFiles.includes(this.lastConfig.siFile)) {
					this.config.siFile = this.lastConfig.siFile;
					dropdown.setValue(this.lastConfig.siFile);
				} else if (this.config.siFile && mdFiles.includes(this.config.siFile)) {
					dropdown.setValue(this.config.siFile);
				} else {
					const siFile = mdFiles.find((f) => f.includes("supp"));
					if (siFile) {
						this.config.siFile = siFile;
						dropdown.setValue(siFile);
					} else if (mdFiles.length > 0) {
						this.config.siFile = mdFiles[0];
						dropdown.setValue(mdFiles[0]);
					}
				}
				dropdown.onChange((value) => {
					this.config.siFile = value;
				});
			});
		// Show SI file container if SI refs is enabled
		this.siFileContainer.style.display = this.config.includeSiRefs ? "block" : "none";

		// SI formatting toggle
		new Setting(contentEl)
			.setName("SI Formatting")
			.setDesc("Apply S-prefixed figure/table numbering")
			.addToggle((toggle) => {
				this.isSiToggle = toggle;
				toggle.setValue(this.config.isSi);
				toggle.onChange((value) => {
					this.config.isSi = value;
				});
			});

		// ─────────────────────────────────────────────────────────────────────
		// Action Buttons
		// ─────────────────────────────────────────────────────────────────────
		const buttonContainer = contentEl.createDiv({ cls: "modal-button-container" });

		new ButtonComponent(buttonContainer)
			.setButtonText("Restore Defaults")
			.onClick(() => {
				this.restoreDefaults();
			});

		new ButtonComponent(buttonContainer)
			.setButtonText("Cancel")
			.onClick(() => {
				this.close();
			});

		new ButtonComponent(buttonContainer)
			.setButtonText("Build")
			.setCta()
			.onClick(() => {
				if (!this.config.sourceFile) {
					new Notice("Please select a source file");
					return;
				}
				this.close();
				this.plugin.executeBuild(this.config);
			});
	}

	private restoreDefaults() {
		const mdFiles = this.plugin.getMarkdownFiles();
		const settings = this.plugin.settings;

		// Reset config to plugin defaults
		this.config.profile = settings.defaultProfile;
		this.config.font = settings.defaultFont;
		this.config.fontSize = settings.defaultFontSize;
		this.config.citationStyle = settings.defaultCitationStyle;
		this.config.lineSpacing = "";
		this.config.paragraphStyle = "";
		this.config.lineNumbers = null;
		this.config.numberedHeadings = null;
		this.config.language = "";
		this.config.usePng = false;
		this.config.includeSiRefs = false;
		this.config.isSi = false;

		// Reset source file to sensible default
		const maintext = mdFiles.find((f) => f.includes("maintext"));
		this.config.sourceFile = maintext || mdFiles[0] || "";
		
		// Reset frontmatter to sensible default
		const frontmatter = mdFiles.find((f) => f.includes("frontmatter"));
		this.config.frontmatterFile = frontmatter || null;

		// Reset SI file to sensible default
		const siFile = mdFiles.find((f) => f.includes("supp"));
		this.config.siFile = siFile || mdFiles[0] || null;

		// Update UI components
		const currentFormat = this.config.profile.startsWith("docx") ? "docx" : "pdf";
		
		this.sourceDropdown?.setValue(this.config.sourceFile);
		this.frontmatterDropdown?.setValue(this.config.frontmatterFile || "");
		this.formatDropdown?.setValue(currentFormat);
		this.populateProfiles(this.profileDropdown, currentFormat);
		this.profileDropdown?.setValue(this.config.profile);
		this.fontDropdown?.setValue(this.config.font);
		this.fontSizeDropdown?.setValue(this.config.fontSize);
		this.lineSpacingDropdown?.setValue(this.config.lineSpacing);
		this.paragraphStyleDropdown?.setValue(this.config.paragraphStyle);
		this.lineNumbersDropdown?.setValue("default");
		this.numberedHeadingsDropdown?.setValue("default");
		this.languageDropdown?.setValue(this.config.language);
		this.citationDropdown?.setValue(this.config.citationStyle);
		this.pngToggle?.setValue(this.config.usePng);
		this.siRefsToggle?.setValue(this.config.includeSiRefs);
		this.siFileDropdown?.setValue(this.config.siFile || "");
		this.isSiToggle?.setValue(this.config.isSi);

		// Update visibility
		this.updateFormatOptions(currentFormat);
		this.siFileContainer.style.display = "none";

		new Notice("Settings restored to defaults");
	}

	onClose() {
		const { contentEl } = this;
		contentEl.empty();
	}

	private createSectionHeader(container: HTMLElement, title: string) {
		container.createEl("h3", { text: title, cls: "setting-section-header" });
	}

	private populateProfiles(dropdown: DropdownComponent, format: string) {
		// Clear existing options
		dropdown.selectEl.empty();

		// Group profiles by category
		const profiles = this.plugin.getProfiles();
		const categories = new Map<string, ProfileInfo[]>();
		profiles.filter((p) => p.format === format).forEach((profile) => {
			if (!categories.has(profile.category)) {
				categories.set(profile.category, []);
			}
			categories.get(profile.category)?.push(profile);
		});

		// Add options with category groups
		categories.forEach((profiles, category) => {
			const optgroup = dropdown.selectEl.createEl("optgroup", { attr: { label: category } });
			profiles.forEach((profile) => {
				optgroup.createEl("option", {
					value: profile.id,
					text: profile.name,
				});
			});
		});
	}

	private updateProfilesForFormat(format: string) {
		this.populateProfiles(this.profileDropdown, format);

		// Set default profile for format
		const defaultProfile = format === "docx" ? "docx-manuscript" : "pdf-default";
		this.profileDropdown.setValue(defaultProfile);
		this.config.profile = defaultProfile;
	}

	private updateFormatOptions(format: string) {
		// Show/hide PNG option for DOCX
		this.pngContainer.style.display = format === "docx" ? "block" : "none";
	}
}

// ============================================================================
// Build Output Modal
// ============================================================================

class BuildOutputModal extends Modal {
	private outputEl: HTMLElement;
	private statusEl: HTMLElement;
	private fileName: string;

	constructor(app: App, fileName: string) {
		super(app);
		this.fileName = fileName;
	}

	onOpen() {
		const { contentEl } = this;
		contentEl.empty();
		contentEl.addClass("manuscript-build-output-modal");

		// Header
		const header = contentEl.createDiv({ cls: "output-header" });
		header.createEl("h2", { text: "Building Manuscript" });
		this.statusEl = header.createEl("span", { cls: "build-status building", text: "Building..." });

		// File info
		contentEl.createEl("p", { text: `Source: ${this.fileName}`, cls: "output-file-info" });

		// Output container
		this.outputEl = contentEl.createEl("pre", { cls: "build-output" });

		// Close button
		const buttonContainer = contentEl.createDiv({ cls: "modal-button-container" });
		new ButtonComponent(buttonContainer)
			.setButtonText("Close")
			.onClick(() => {
				this.close();
			});
	}

	onClose() {
		const { contentEl } = this;
		contentEl.empty();
	}

	appendOutput(text: string, isError = false) {
		const span = this.outputEl.createEl("span", {
			text,
			cls: isError ? "output-error" : "output-text",
		});
		this.outputEl.scrollTop = this.outputEl.scrollHeight;
	}

	setSuccess() {
		this.statusEl.setText("✓ Complete");
		this.statusEl.removeClass("building");
		this.statusEl.addClass("success");
	}

	setError() {
		this.statusEl.setText("✗ Failed");
		this.statusEl.removeClass("building");
		this.statusEl.addClass("error");
	}
}

// ============================================================================
// Settings Tab
// ============================================================================

class ManuscriptBuildSettingTab extends PluginSettingTab {
	plugin: ManuscriptBuildPlugin;

	constructor(app: App, plugin: ManuscriptBuildPlugin) {
		super(app, plugin);
		this.plugin = plugin;
	}

	display(): void {
		const { containerEl } = this;
		containerEl.empty();

		containerEl.createEl("h2", { text: "Manuscript Build Settings" });

		// ─────────────────────────────────────────────────────────────────────
		// System Settings
		// ─────────────────────────────────────────────────────────────────────
		containerEl.createEl("h3", { text: "System", cls: "setting-section-header" });

		new Setting(containerEl)
			.setName("Python Path")
			.setDesc("Path to Python executable (python3, python, or full path)")
			.addText((text) =>
				text
					.setPlaceholder("python3")
					.setValue(this.plugin.settings.pythonPath)
					.onChange(async (value) => {
						this.plugin.settings.pythonPath = value || "python3";
						await this.plugin.saveSettings();
					})
			);

		new Setting(containerEl)
			.setName("Build Script Path")
			.setDesc("Path to build.py relative to vault root")
			.addText((text) =>
				text
					.setPlaceholder("build.py")
					.setValue(this.plugin.settings.buildScriptPath)
					.onChange(async (value) => {
						this.plugin.settings.buildScriptPath = value || "build.py";
						await this.plugin.saveSettings();
					})
			);

		// ─────────────────────────────────────────────────────────────────────
		// Default Settings
		// ─────────────────────────────────────────────────────────────────────
		containerEl.createEl("h3", { text: "Defaults", cls: "setting-section-header" });

		new Setting(containerEl)
			.setName("Default Profile")
			.setDesc("Default output profile for new builds")
			.addDropdown((dropdown) => {
				this.plugin.getProfiles().forEach((profile) => {
					dropdown.addOption(profile.id, `${profile.name} (${profile.format.toUpperCase()})`);
				});
				dropdown.setValue(this.plugin.settings.defaultProfile);
				dropdown.onChange(async (value) => {
					this.plugin.settings.defaultProfile = value;
					await this.plugin.saveSettings();
				});
			});

		new Setting(containerEl)
			.setName("Default Font")
			.setDesc("Default typeface for PDF builds")
			.addDropdown((dropdown) => {
				dropdown.addOption("", "Profile Default");
				Object.entries(FONT_PRESETS).forEach(([key, name]) => {
					dropdown.addOption(key, name);
				});
				dropdown.setValue(this.plugin.settings.defaultFont || "");
				dropdown.onChange(async (value) => {
					this.plugin.settings.defaultFont = value;
					await this.plugin.saveSettings();
				});
			});

		new Setting(containerEl)
			.setName("Default Font Size")
			.setDesc("Default font size for PDF builds")
			.addDropdown((dropdown) => {
				FONT_SIZES.forEach((size) => {
					dropdown.addOption(size, size);
				});
				dropdown.setValue(this.plugin.settings.defaultFontSize);
				dropdown.onChange(async (value) => {
					this.plugin.settings.defaultFontSize = value;
					await this.plugin.saveSettings();
				});
			});

		// Citation styles (dynamically loaded from resources/citation_styles/)
		const citationStyles = this.plugin.getCitationStyles();
		new Setting(containerEl)
			.setName("Default Citation Style")
			.setDesc("Default bibliography format")
			.addDropdown((dropdown) => {
				Object.entries(citationStyles).forEach(([key, name]) => {
					dropdown.addOption(key, name);
				});
				dropdown.setValue(this.plugin.settings.defaultCitationStyle);
				dropdown.onChange(async (value) => {
					this.plugin.settings.defaultCitationStyle = value;
					await this.plugin.saveSettings();
				});
			});

		// ─────────────────────────────────────────────────────────────────────
		// Citation Style Management
		// ─────────────────────────────────────────────────────────────────────
		containerEl.createEl("h3", { text: "Add Citation Styles", cls: "setting-section-header" });

		const styleInfoEl = containerEl.createDiv({ cls: "setting-item-description citation-style-info" });
		styleInfoEl.innerHTML = `
			<p>To add a new citation style:</p>
			<ol>
				<li>Find your style at <strong>zotero.org/styles</strong></li>
				<li>Download the <code>.csl</code> file</li>
				<li>Place it in <code>resources/citation_styles/</code></li>
				<li>Reopen this dialog to see the new style</li>
			</ol>
		`;

		new Setting(containerEl)
			.setName("Browse Zotero Styles")
			.setDesc("Open the Zotero Style Repository to find citation styles")
			.addButton((button) =>
				button.setButtonText("Open Zotero Styles").onClick(() => {
					window.open("https://www.zotero.org/styles", "_blank");
				})
			);

		new Setting(containerEl)
			.setName("Open Styles Folder")
			.setDesc("Open the folder where citation style files are stored")
			.addButton((button) =>
				button.setButtonText("Open Folder").onClick(() => {
					this.plugin.openCitationStylesFolder();
				})
			);

		// ─────────────────────────────────────────────────────────────────────
		// Behavior Settings
		// ─────────────────────────────────────────────────────────────────────
		containerEl.createEl("h3", { text: "Behavior", cls: "setting-section-header" });

		new Setting(containerEl)
			.setName("Show Notifications")
			.setDesc("Display build status notifications")
			.addToggle((toggle) =>
				toggle.setValue(this.plugin.settings.showNotifications).onChange(async (value) => {
					this.plugin.settings.showNotifications = value;
					await this.plugin.saveSettings();
				})
			);

		new Setting(containerEl)
			.setName("Auto-open Export Folder")
			.setDesc("Open the export folder after successful builds")
			.addToggle((toggle) =>
				toggle.setValue(this.plugin.settings.autoOpenExport).onChange(async (value) => {
					this.plugin.settings.autoOpenExport = value;
					await this.plugin.saveSettings();
				})
			);

		// ─────────────────────────────────────────────────────────────────────
		// Actions
		// ─────────────────────────────────────────────────────────────────────
		containerEl.createEl("h3", { text: "Actions", cls: "setting-section-header" });

		new Setting(containerEl)
			.setName("Open Export Folder")
			.setDesc("Open the folder containing built documents")
			.addButton((button) =>
				button.setButtonText("Open").onClick(() => {
					this.plugin.openExportFolder();
				})
			);

		new Setting(containerEl)
			.setName("Test Python")
			.setDesc("Verify Python is accessible")
			.addButton((button) =>
				button.setButtonText("Test").onClick(() => {
					this.testPython();
				})
			);
	}

	private testPython() {
		const { spawn } = require("child_process");
		const process = spawn(this.plugin.settings.pythonPath, ["--version"]);

		let output = "";
		process.stdout?.on("data", (data: Buffer) => {
			output += data.toString();
		});
		process.stderr?.on("data", (data: Buffer) => {
			output += data.toString();
		});

		process.on("close", (code: number) => {
			if (code === 0) {
				new Notice(`✓ Python found: ${output.trim()}`);
			} else {
				new Notice(`✗ Python not found at: ${this.plugin.settings.pythonPath}`);
			}
		});

		process.on("error", () => {
			new Notice(`✗ Python not found at: ${this.plugin.settings.pythonPath}`);
		});
	}
}
