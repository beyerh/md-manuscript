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
	bibliographyPath: string;
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
	texMode: "" | "source" | "portable" | "body";
	font: string;
	fontSize: string;
	citationStyle: string;
	lineSpacing: string;
	paragraphStyle: string;
	lineNumbers: boolean | null;
	pageNumbers: boolean | null;
	numberedHeadings: boolean | null;
	language: string;
	figureFormat: string;
	figureBackground: string;
	paperSize: string;
	margins: string;
	visualizeCaptions: boolean;
	captionStyle: string;
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
	bibliographyPath: "references.json",
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
	"computer-modern": "LaTeX Default (Compatibility)",
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

const PAPER_SIZE_PRESETS: Record<string, string> = {
	"": "Profile Default",
	a4: "A4",
	letter: "US Letter",
};

const MARGIN_PRESETS: Record<string, string> = {
	"": "Profile Default",
	standard: "Standard (2.5cm)",
	narrow: "Narrow (1.27cm)",
	wide: "Wide (3.0cm)",
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
					this.buildWithDefaults(activeFile.path);
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
			.filter((f) => !f.name.startsWith("_") && f.name.toLowerCase() !== "readme.md")
			.sort((a, b) => {
				// Sort root files first, then alphabetically by path
				const aIsRoot = !a.path.includes("/");
				const bIsRoot = !b.path.includes("/");
				
				if (aIsRoot && !bIsRoot) return -1;
				if (!aIsRoot && bIsRoot) return 1;
				
				return a.path.localeCompare(b.path);
			})
			.map((f) => f.path);
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
			texMode: "",
			font: this.settings.defaultFont,
			fontSize: this.settings.defaultFontSize,
			citationStyle: this.settings.defaultCitationStyle,
			lineSpacing: "",
			paragraphStyle: "",
			lineNumbers: null,
			pageNumbers: null,
			numberedHeadings: null,
			language: "",
			figureFormat: "png",
			figureBackground: "white",
			paperSize: "",
			margins: "",
			visualizeCaptions: false,
			captionStyle: "plain",
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
					texMode: (data.tex_mode as BuildConfig["texMode"]) || (data.output_tex ? "portable" : ""),
					font: data.font !== undefined ? data.font : this.settings.defaultFont,
					fontSize: data.fontsize || this.settings.defaultFontSize,
					citationStyle: data.citation_style || this.settings.defaultCitationStyle,
					lineSpacing: data.linespacing || "",
					paragraphStyle: data.paragraph_style || "",
					lineNumbers: data.linenumbers !== undefined ? data.linenumbers : null,
					pageNumbers: data.pagenumbers !== undefined ? data.pagenumbers : null,
					numberedHeadings: data.numbered_headings !== undefined ? data.numbered_headings : null,
					language: data.language || "",
					figureFormat: data.figure_format || "png",
					figureBackground: data.figure_background || "white",
					paperSize: data.papersize || "",
					margins: data.margins || "",
					visualizeCaptions: data.visualize_captions || false,
					captionStyle: data.caption_style || "plain",
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
			tex_mode: config.texMode || null,
			font: config.font || null,
			fontsize: config.fontSize,
			citation_style: config.citationStyle,
			linespacing: config.lineSpacing || null,
			paragraph_style: config.paragraphStyle || null,
			linenumbers: config.lineNumbers,
			pagenumbers: config.pageNumbers,
			numbered_headings: config.numberedHeadings,
			language: config.language || null,
			figure_format: config.figureFormat || null,
			figure_background: config.figureBackground || null,
			papersize: config.paperSize || null,
			margins: config.margins || null,
			visualize_captions: config.visualizeCaptions || false,
			caption_style: config.captionStyle || "plain",
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

		if (config.texMode === "source") {
			args.push("--tex-source");
		} else if (config.texMode === "portable") {
			args.push("--tex");
		} else if (config.texMode === "body") {
			args.push("--tex-body");
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

		if (config.pageNumbers === true) {
			args.push("--pagenumbers");
		} else if (config.pageNumbers === false) {
			args.push("--no-pagenumbers");
		}

		if (config.numberedHeadings === true) {
			args.push("--numbered-headings");
		} else if (config.numberedHeadings === false) {
			args.push("--no-numbered-headings");
		}

		if (config.language) {
			args.push(`--lang=${config.language}`);
		}

		if (config.paperSize) {
			args.push(`--papersize=${config.paperSize}`);
		}

		if (config.margins) {
			args.push(`--margins=${config.margins}`);
		}

		if (config.citationStyle) {
			args.push(`--csl=${config.citationStyle}`);
		}

		// Flattened markdown options
		if (config.profile === "md-flattened") {
			if (config.figureFormat) {
				args.push(`--figure-format=${config.figureFormat}`);
			}
			if (config.figureBackground) {
				args.push(`--figure-bg=${config.figureBackground}`);
			}
			if (config.visualizeCaptions) {
				args.push("--captions");
			}
			if (config.captionStyle === "html") {
				args.push("--html-captions");
			}
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
	private pageNumbersDropdown: DropdownComponent;
	private numberedHeadingsDropdown: DropdownComponent;
	private languageDropdown: DropdownComponent;
	private paperSizeDropdown: DropdownComponent;
	private marginsDropdown: DropdownComponent;
	private citationDropdown: DropdownComponent;
	private siRefsToggle: ToggleComponent;
	private siFileDropdown: DropdownComponent;
	private siFileContainer: HTMLElement;
	private isSiToggle: ToggleComponent;
	private pngToggle: ToggleComponent;
	private pngContainer: HTMLElement;
	private latexModeContainer: HTMLElement;
	private flattenedMdContainer: HTMLElement;
	private figureFormatDropdown: DropdownComponent;
	private figureBackgroundDropdown: DropdownComponent;
	private figureBackgroundContainer: HTMLElement;
	private visualizeCaptionsToggle: ToggleComponent;
	private captionStyleToggle: ToggleComponent;
	private typographySection: HTMLElement;
	private citationsSection: HTMLElement;
	private showAllFiles: boolean = false;
	private allFiles: string[] = [];

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
				texMode: "",
				font: plugin.settings.defaultFont,
				fontSize: plugin.settings.defaultFontSize,
				citationStyle: plugin.settings.defaultCitationStyle,
				lineSpacing: "",
				paragraphStyle: "",
				lineNumbers: null,
				pageNumbers: null,
				numberedHeadings: null,
				language: "",
				figureFormat: "png",
				figureBackground: "white",
				paperSize: "",
				margins: "",
				visualizeCaptions: false,
				captionStyle: "plain",
			};
		}
	}

	private updateFileDropdowns() {
		const visibleFiles = this.showAllFiles
			? this.allFiles
			: this.allFiles.filter(f => !f.includes("/"));
		
		const update = (dropdown: DropdownComponent, currentValue: string | null, allowNone: boolean = false) => {
			if (!dropdown) return;
			
			// Clear existing options
			dropdown.selectEl.innerHTML = "";
			
			if (allowNone) dropdown.addOption("", "None");
			
			visibleFiles.forEach(f => dropdown.addOption(f, f));
			
			// Ensure current value is present if it exists in allFiles but hidden
			if (currentValue && !visibleFiles.includes(currentValue) && this.allFiles.includes(currentValue)) {
				 dropdown.addOption(currentValue, currentValue);
			}
			
			// Restore value
			if (currentValue !== null) dropdown.setValue(currentValue);
		};

		update(this.sourceDropdown, this.config.sourceFile);
		update(this.frontmatterDropdown, this.config.frontmatterFile, true);
		update(this.siFileDropdown, this.config.siFile);
	}

	onOpen() {
		const { contentEl } = this;
		contentEl.empty();
		contentEl.addClass("manuscript-build-modal");

		// Header
		contentEl.createEl("h2", { text: "Build Manuscript", cls: "modal-title" });

		this.allFiles = this.plugin.getMarkdownFiles();
		const mdFiles = this.allFiles; // Alias for convenience in initialization logic

		// Initialize defaults if needed
		if (mdFiles.length > 0) {
			// Source File Default
			if (this.lastConfig?.sourceFile && mdFiles.includes(this.lastConfig.sourceFile)) {
				this.config.sourceFile = this.lastConfig.sourceFile;
			} else if (!this.config.sourceFile || !mdFiles.includes(this.config.sourceFile)) {
				const maintext = mdFiles.find((f) => f.includes("maintext"));
				this.config.sourceFile = maintext || mdFiles[0];
			}

			// Frontmatter Default
			if (this.lastConfig && this.lastConfig.frontmatterFile !== undefined) {
				this.config.frontmatterFile = this.lastConfig.frontmatterFile;
			} else if (this.config.frontmatterFile && mdFiles.includes(this.config.frontmatterFile)) {
				// Keep current
			} else {
				const frontmatter = mdFiles.find((f) => f.includes("frontmatter"));
				if (frontmatter) {
					this.config.frontmatterFile = frontmatter;
				}
			}

			// SI File Default
			if (this.lastConfig?.siFile && mdFiles.includes(this.lastConfig.siFile)) {
				this.config.siFile = this.lastConfig.siFile;
			} else if (this.config.siFile && mdFiles.includes(this.config.siFile)) {
				// Keep current
			} else {
				const siFile = mdFiles.find((f) => f.includes("supp"));
				if (siFile) {
					this.config.siFile = siFile;
				} else if (mdFiles.length > 0) {
					this.config.siFile = mdFiles[0];
				}
			}
		}

		// ─────────────────────────────────────────────────────────────────────
		// Document Selection Section
		// ─────────────────────────────────────────────────────────────────────
		this.createSectionHeader(contentEl, "Document");

		// Show Subfolders Toggle
		new Setting(contentEl)
			.setName("Show files in subfolders")
			.setDesc("Toggle visibility of files located in subdirectories")
			.addToggle((toggle) => {
				toggle.setValue(this.showAllFiles);
				toggle.onChange((value) => {
					this.showAllFiles = value;
					this.updateFileDropdowns();
				});
			});

		// Source file
		new Setting(contentEl)
			.setName("Source File")
			.setDesc("The main document to build")
			.addDropdown((dropdown) => {
				this.sourceDropdown = dropdown;
				// Initial population handled by updateFileDropdowns
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
				// Initial population handled by updateFileDropdowns
				dropdown.onChange((value) => {
					this.config.frontmatterFile = value || null;
				});
			});

		// ─────────────────────────────────────────────────────────────────────
		// Output Section
		// ─────────────────────────────────────────────────────────────────────
		this.createSectionHeader(contentEl, "Output");

		const outputGrid = contentEl.createDiv({ cls: "manuscript-settings-grid" });

		// Format selection
		// Determine current format: docx, pdf, md (flattened), or latex (pdf with texMode set)
		let currentFormat = this.config.profile.startsWith("docx") ? "docx" :
			this.config.profile === "md-flattened" ? "md" : "pdf";
		if (currentFormat === "pdf" && this.config.texMode) {
			currentFormat = "latex";
		}
		new Setting(outputGrid)
			.setClass("manuscript-setting-compact")
			.setName("Format")
			.setDesc("Output document format")
			.addDropdown((dropdown) => {
				this.formatDropdown = dropdown;
				dropdown.addOption("pdf", "PDF");
				dropdown.addOption("latex", "LaTeX");
				dropdown.addOption("docx", "Word Document (DOCX)");
				dropdown.addOption("md", "Flattened Markdown (Digital Garden)");
				dropdown.setValue(currentFormat);
				dropdown.onChange((value) => {
					// LaTeX uses PDF profiles but outputs .tex
					// Flattened markdown uses its own profile
					let profileFormat = value;
					if (value === "latex") {
						profileFormat = "pdf";
					} else if (value === "md") {
						this.config.profile = "md-flattened";
					}
					if (value !== "latex") {
						this.config.texMode = "";
					} else if (!this.config.texMode) {
						this.config.texMode = "portable";
					}
					if (value !== "md") {
						this.updateProfilesForFormat(profileFormat);
					}
					this.updateFormatOptions(value);
				});
			});

		// LaTeX mode selection (only relevant when format is LaTeX)
		this.latexModeContainer = outputGrid.createDiv();
		this.latexModeContainer.addClass("manuscript-setting-compact");
		// Note: The container itself becomes the grid item.
		// The Setting inside should also be compact if we want the same styling, but if the container is the grid item, flex direction applies to container?
		// No, CSS targets .manuscript-setting-compact which is usually the Setting element.
		// So we apply the class to the Setting.
		// BUT if we wrap it in a div, the DIV is the grid item.
		// To fix layout, the DIV should just be a wrapper (display contents?) or handle the layout.
		// Actually, if we apply "manuscript-setting-compact" to the Setting, it applies flex-direction: column.
		// If the wrapper div is the grid item, the Setting is inside.
		// We want the Setting to be the visual item.
		// So we apply style to wrapper? Or make wrapper display: contents?
		// Let's make the wrapper match the compact style.
		
		new Setting(this.latexModeContainer)
			.setClass("manuscript-setting-compact")
			.setName("LaTeX Mode")
			.setDesc("Choose how LaTeX is exported")
			.addDropdown((dropdown) => {
				dropdown.addOption("source", "LaTeX Source (profile exact)");
				dropdown.addOption("portable", "Portable LaTeX");
				dropdown.addOption("body", "Body-only (paste into journal templates)");
				dropdown.setValue(this.config.texMode || "portable");
				dropdown.onChange((value) => {
					this.config.texMode = value as BuildConfig["texMode"];
				});
			});

		// Profile selection
		const profileFormat = currentFormat === "latex" ? "pdf" : currentFormat;
		new Setting(outputGrid)
			.setClass("manuscript-setting-compact")
			.setName("Profile")
			.setDesc("Document style and layout")
			.addDropdown((dropdown) => {
				this.profileDropdown = dropdown;
				this.populateProfiles(dropdown, profileFormat);
				dropdown.setValue(this.config.profile);
				dropdown.onChange((value) => {
					this.config.profile = value;
				});
			});

		// PNG conversion (DOCX only)
		this.pngContainer = outputGrid.createDiv();
		new Setting(this.pngContainer)
			.setClass("manuscript-setting-compact")
			.setName("Convert Figures to PNG")
			.setDesc("Convert PDF figures to PNG for Word compatibility")
			.addToggle((toggle) => {
				this.pngToggle = toggle;
				toggle.setValue(this.config.usePng);
				toggle.onChange((value) => {
					this.config.usePng = value;
				});
			});

		// Flattened Markdown options container
		// We make this a grid too, separate from outputGrid to ensure it takes full width below
		this.flattenedMdContainer = contentEl.createDiv({ cls: "manuscript-settings-grid" });
		
		// Figure format (Flattened Markdown only)
		new Setting(this.flattenedMdContainer)
			.setClass("manuscript-setting-compact")
			.setName("Figure Format")
			.setDesc("Output format for figures")
			.addDropdown((dropdown) => {
				this.figureFormatDropdown = dropdown;
				dropdown.addOption("png", "PNG");
				dropdown.addOption("webp", "WebP");
				dropdown.addOption("jpg", "JPEG");
				dropdown.addOption("original", "Keep Original");
				dropdown.setValue(this.config.figureFormat || "png");
				dropdown.onChange((value) => {
					this.config.figureFormat = value;
					// Show/hide background option based on format
					if (this.figureBackgroundContainer) {
						this.figureBackgroundContainer.style.display = value !== "original" ? "block" : "none";
					}
				});
			});

		// Figure background (Flattened Markdown only, not for original format)
		this.figureBackgroundContainer = this.flattenedMdContainer.createDiv();
		new Setting(this.figureBackgroundContainer)
			.setClass("manuscript-setting-compact")
			.setName("Figure Background")
			.setDesc("Background color for converted figures")
			.addDropdown((dropdown) => {
				this.figureBackgroundDropdown = dropdown;
				dropdown.addOption("white", "White");
				dropdown.addOption("transparent", "Transparent");
				dropdown.setValue(this.config.figureBackground || "white");
				dropdown.onChange((value) => {
					this.config.figureBackground = value;
				});
			});
		// Hide background option if format is "original"
		this.figureBackgroundContainer.style.display = this.config.figureFormat !== "original" ? "block" : "none";

		// Visualize Captions (Flattened Markdown only)
		new Setting(this.flattenedMdContainer)
			.setClass("manuscript-setting-compact")
			.setName("Visualize Captions")
			.setDesc("Output visible captions below images (for digital gardens)")
			.addToggle((toggle) => {
				this.visualizeCaptionsToggle = toggle;
				toggle.setValue(this.config.visualizeCaptions || false);
				toggle.onChange((value) => {
					this.config.visualizeCaptions = value;
				});
			});

		// HTML Captions (Flattened Markdown only)
		new Setting(this.flattenedMdContainer)
			.setClass("manuscript-setting-compact")
			.setName("HTML Figures & Captions")
			.setDesc("Use HTML <figure> tags to retain size/alignment")
			.addToggle((toggle) => {
				this.captionStyleToggle = toggle;
				toggle.setValue(this.config.captionStyle === "html");
				toggle.onChange((value) => {
					this.config.captionStyle = value ? "html" : "plain";
				});
			});

		// Show/hide PNG/LaTeX/Flattened MD options based on format (must be after containers are created)
		this.updateFormatOptions(currentFormat);

		// ─────────────────────────────────────────────────────────────────────
		// Typography Section (PDF only)
		// ─────────────────────────────────────────────────────────────────────
		this.typographySection = contentEl.createDiv();
		this.createSectionHeader(this.typographySection, "Typography");

		const typeGrid = this.typographySection.createDiv({ cls: "manuscript-settings-grid" });

		// Font
		new Setting(typeGrid)
			.setClass("manuscript-setting-compact")
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
		new Setting(typeGrid)
			.setClass("manuscript-setting-compact")
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
		new Setting(typeGrid)
			.setClass("manuscript-setting-compact")
			.setName("Line Spacing")
			.setDesc("Override line spacing")
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
		new Setting(typeGrid)
			.setClass("manuscript-setting-compact")
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

		// Paper size
		new Setting(typeGrid)
			.setClass("manuscript-setting-compact")
			.setName("Paper Size")
			.setDesc("Override paper size")
			.addDropdown((dropdown) => {
				this.paperSizeDropdown = dropdown;
				Object.entries(PAPER_SIZE_PRESETS).forEach(([key, name]) => {
					dropdown.addOption(key, name);
				});
				dropdown.setValue(this.config.paperSize);
				dropdown.onChange((value) => {
					this.config.paperSize = value;
				});
			});

		// Margins
		new Setting(typeGrid)
			.setClass("manuscript-setting-compact")
			.setName("Margins")
			.setDesc("Override document margins")
			.addDropdown((dropdown) => {
				this.marginsDropdown = dropdown;
				Object.entries(MARGIN_PRESETS).forEach(([key, name]) => {
					dropdown.addOption(key, name);
				});
				dropdown.setValue(this.config.margins);
				dropdown.onChange((value) => {
					this.config.margins = value;
				});
			});

		// Line numbers
		new Setting(typeGrid)
			.setClass("manuscript-setting-compact")
			.setName("Line Numbers")
			.setDesc("Three-state: Default / On / Off")
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

		// Page numbers
		new Setting(typeGrid)
			.setClass("manuscript-setting-compact")
			.setName("Page Numbers")
			.setDesc("Three-state: Default / On / Off")
			.addDropdown((dropdown) => {
				this.pageNumbersDropdown = dropdown;
				dropdown.addOption("default", "Profile Default");
				dropdown.addOption("on", "On");
				dropdown.addOption("off", "Off");
				const currentValue = this.config.pageNumbers === null ? "default" : (this.config.pageNumbers ? "on" : "off");
				dropdown.setValue(currentValue);
				dropdown.onChange((value) => {
					if (value === "default") {
						this.config.pageNumbers = null;
					} else {
						this.config.pageNumbers = value === "on";
					}
				});
			});

		// Numbered headings
		new Setting(typeGrid)
			.setClass("manuscript-setting-compact")
			.setName("Numbered Headings")
			.setDesc("Three-state: Default / On / Off")
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
		new Setting(typeGrid)
			.setClass("manuscript-setting-compact")
			.setName("Document Language")
			.setDesc("Hyphenation and localization")
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
		this.citationsSection = contentEl.createDiv();
		this.createSectionHeader(this.citationsSection, "Citations");

		// Citation style (dynamically loaded from resources/citation_styles/)
		const citationStyles = this.plugin.getCitationStyles();
		new Setting(this.citationsSection)
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

		const siGrid = contentEl.createDiv({ cls: "manuscript-settings-grid" });

		// Include SI refs
		new Setting(siGrid)
			.setClass("manuscript-setting-compact")
			.setName("Include SI References")
			.setDesc("Add SI citations to main bib")
			.addToggle((toggle) => {
				this.siRefsToggle = toggle;
				toggle.setValue(this.config.includeSiRefs);
				toggle.onChange((value) => {
					this.config.includeSiRefs = value;
					this.siFileContainer.style.display = value ? "block" : "none";
				});
			});

		// SI file selection
		this.siFileContainer = siGrid.createDiv();
		new Setting(this.siFileContainer)
			.setClass("manuscript-setting-compact")
			.setName("SI File")
			.setDesc("File containing SI references")
			.addDropdown((dropdown) => {
				this.siFileDropdown = dropdown;
				// Initial population handled by updateFileDropdowns
				dropdown.onChange((value) => {
					this.config.siFile = value;
				});
			});
		// Show SI file container if SI refs is enabled
		this.siFileContainer.style.display = this.config.includeSiRefs ? "block" : "none";

		// SI formatting toggle
		new Setting(siGrid)
			.setClass("manuscript-setting-compact")
			.setName("SI Formatting")
			.setDesc("S-prefixed figures/tables")
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

		// Initialize file dropdowns
		this.updateFileDropdowns();
	}

	private restoreDefaults() {
		const mdFiles = this.allFiles;
		const settings = this.plugin.settings;
		
		this.showAllFiles = false;

		// Reset config to plugin defaults
		this.config.profile = settings.defaultProfile;
		this.config.font = settings.defaultFont;
		this.config.fontSize = settings.defaultFontSize;
		this.config.citationStyle = settings.defaultCitationStyle;
		this.config.lineSpacing = "";
		this.config.paragraphStyle = "";
		this.config.lineNumbers = null;
		this.config.pageNumbers = null;
		this.config.numberedHeadings = null;
		this.config.language = "";
		this.config.usePng = false;
		this.config.includeSiRefs = false;
		this.config.isSi = false;
		this.config.texMode = "";
		this.config.figureFormat = "png";
		this.config.figureBackground = "white";
		this.config.paperSize = "";
		this.config.margins = "";
		this.config.visualizeCaptions = false;
		this.config.captionStyle = "plain";

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
		let currentFormat = this.config.profile.startsWith("docx") ? "docx" : "pdf";
		if (currentFormat === "pdf" && this.config.texMode) {
			currentFormat = "latex";
		}
		const profileFormat = currentFormat === "latex" ? "pdf" : currentFormat;
		
		this.sourceDropdown?.setValue(this.config.sourceFile);
		this.frontmatterDropdown?.setValue(this.config.frontmatterFile || "");
		this.formatDropdown?.setValue(currentFormat);
		this.populateProfiles(this.profileDropdown, profileFormat);
		this.profileDropdown?.setValue(this.config.profile);
		this.fontDropdown?.setValue(this.config.font);
		this.fontSizeDropdown?.setValue(this.config.fontSize);
		this.lineSpacingDropdown?.setValue(this.config.lineSpacing);
		this.paragraphStyleDropdown?.setValue(this.config.paragraphStyle);
		this.lineNumbersDropdown?.setValue("default");
		this.pageNumbersDropdown?.setValue("default");
		this.numberedHeadingsDropdown?.setValue("default");
		this.languageDropdown?.setValue(this.config.language);
		this.paperSizeDropdown?.setValue(this.config.paperSize);
		this.marginsDropdown?.setValue(this.config.margins);
		this.citationDropdown?.setValue(this.config.citationStyle);
		this.pngToggle?.setValue(this.config.usePng);
		this.siRefsToggle?.setValue(this.config.includeSiRefs);
		this.siFileDropdown?.setValue(this.config.siFile || "");
		this.isSiToggle?.setValue(this.config.isSi);
		this.figureFormatDropdown?.setValue(this.config.figureFormat);
		this.figureBackgroundDropdown?.setValue(this.config.figureBackground);
		this.visualizeCaptionsToggle?.setValue(this.config.visualizeCaptions);
		this.captionStyleToggle?.setValue(this.config.captionStyle === "html");

		// Update visibility
		this.updateFormatOptions(currentFormat);
		this.siFileContainer.style.display = "none";
		if (this.figureBackgroundContainer) {
			this.figureBackgroundContainer.style.display = "block";
		}
		
		this.updateFileDropdowns();

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
		// Show/hide LaTeX mode for LaTeX
		if (this.latexModeContainer) {
			this.latexModeContainer.style.display = format === "latex" ? "block" : "none";
		}
		// Show/hide Flattened Markdown options
		if (this.flattenedMdContainer) {
			this.flattenedMdContainer.style.display = format === "md" ? "block" : "none";
		}
		// Show/hide profile dropdown (hide for flattened markdown since it has only one profile)
		if (this.profileDropdown) {
			const profileContainer = this.profileDropdown.selectEl.closest(".setting-item");
			if (profileContainer) {
				(profileContainer as HTMLElement).style.display = format === "md" ? "none" : "block";
			}
		}

		// Show/hide Typography section (PDF/LaTeX only)
		if (this.typographySection) {
			this.typographySection.style.display = (format === "pdf" || format === "latex") ? "block" : "none";
		}

		// Citations section is valid for all formats (including Markdown via citeproc)
		if (this.citationsSection) {
			this.citationsSection.style.display = "block";
		}
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

		new Setting(containerEl)
			.setName("Bibliography File")
			.setDesc("Path to references.json file relative to vault root")
			.addText((text) =>
				text
					.setPlaceholder("references.json")
					.setValue(this.plugin.settings.bibliographyPath)
					.onChange(async (value) => {
						this.plugin.settings.bibliographyPath = value || "references.json";
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
