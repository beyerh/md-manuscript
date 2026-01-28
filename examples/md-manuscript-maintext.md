# Abstract {.unnumbered}
**Objective:** Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
**Results:** Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum.

::: {custom-style="FrontMatter"}
`\setlength{\parindent}{0pt}`{=latex}
**Keywords:** template; formatting; zettlr; pandoc
`\setlength{\parindent}{1.5em}`{=latex}
::: 

# Introduction
Profile: Use with pdf-default, pdf-draft, pdf-nature, pdf-cell, or docx-manuscript.
Frontmatter: Pair with 01_frontmatter.md for title page.

**Lorem** *ipsum* ~~dolor~~ ~~sit~~ <u>amet</u>, ==consectetur== adipiscing elit. Nullamin dui mauris.<font color="#ff0000"> Text color is only supported in PDF</font>.

Vivamus hendrerit arcu sed erat molestie vehicula. Sed auctor neque eu tellus rhoncus ut eleifend nibh porttitor. Ut in nulla enim. Phasellus molestie magna non est bibendum non venenatis nisl tempor. Suspendisse dictum feugiat nisl ut dapibus. Mauris iaculis porttitor posuere [@chenSenescencePathways2025].

Praesent id metus massa, ut blandit odio. Proin quis tortor orci. Etiam at risus et justo dignissim congue. Donec congue lacinia dui, a porttitor lectus condimentum laoreet. Nunc eu ullamcorper orci. Quisque eget odio ac lectus vestibulum faucibus eget in metus. In pellentesque faucibus vestibulum. Nulla at nulla justo, eget luctus tortor [@smithDeepTissueImaging2024].

Cras mattis consectetur purus sit amet fermentum. Curabitur blandit tempus porttitor. Nullam quis risus eget urna mollis ornare vel eu leo. Nullam id dolor id nibh ultricies vehicula ut id elit. Etiam porta sem malesuada magna mollis euismod. Cras mattis consectetur purus sit amet fermentum. Aenean lacinia bibendum nulla sed consectetur.

Donec ullamcorper nulla non metus auctor fringilla. Vestibulum id ligula porta felis euismod semper. Praesent commodo cursus magna, vel scelerisque nisl consectetur et. Fusce dapibus, tellus ac cursus commodo, tortor mauris condimentum nibh, ut fermentum massa justo sit amet risus.

Maecenas ultricies mi eget mauris pharetra viverra. The main findings are illustrated in **@Fig:results** and the summary data is provided in **@Tbl:data**. Additional data is available in the Supporting Information (see **Figure S1** and **Table S1**).

# Methods
## A new method
### A very new method
Suspendisse potenti. Sed egestas, ante et vulputate volutpat, eros pede semper est, vitae luctus metus libero eu augue. Morbi purus libero, faucibus adipiscing, commodo quis, gravida id, est. Sed lectus. Praesent elementum hendrerit tortor. Sed semper lorem at felis. Vestibulum volutpat, lacus a ultrices sagittis, mi neque euismod dui, eu pulvinar nunc sapien ornare nisl. Phasellus pede arcu, dapibus eu, fermentum et, dapibus sed, urna [@doeQuantumCoherence2025].

Integer nec odio. Praesent libero. Sed cursus ante dapibus diam. Sed nisi. Nulla quis sem at nibh elementum imperdiet. Duis sagittis ipsum. Praesent mauris. Fusce nec tellus sed augue semper porta. Mauris massa. Vestibulum lacinia arcu eget nulla. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos.

Curabitur sodales ligula in libero. Sed dignissim lacinia nunc. Curabitur tortor. Pellentesque nibh. Aenean quam. In scelerisque sem at dolor. Maecenas mattis. Sed convallis tristique sem. Proin ut ligula vel nunc egestas porttitor. Morbi lectus risus, iaculis vel, suscipit quis, luctus non, massa. Fusce ac turpis quis ligula lacinia aliquet.

## Formatting Guide (Examples)
*The following examples demonstrate common markup patterns.*

### Typography & Units
* **Emphasis:** Use *italics* for emphasis and **bold** for strong emphasis.
* **Sub/Superscript:** H~2~O and E=mc^2^.
* **Non-breaking space:** Use a backslash+space `\ ` to keep numbers and units together (e.g., 10\ kg, p\ <\ 0.05).
* **En-dash:** Use double hyphens `--` for ranges (e.g., 10--20%) to create a proper en-dash (10–20%).

### Lists
1.  First item in a numbered list
2.  Second item
    * Sub-item bullet
    * Another sub-item

### Math Equations
Inline equations look like this: $P < 0.05$.
Block equations are enclosed in double dollar signs:

$$
\sigma = \sqrt{\frac{\sum(x_i - \mu)^2}{N}}
$$

# Results

## Main Findings
Fusce convallis metus id felis luctus adipiscing. Aliquam erat volutpat. Nam dui mi, tincidunt quis, accumsan porttitor, facilisis luctus, metus. As shown in **@Fig:results**, phasellus ultrices nulla quis nibh. Raw unprocessed data for this analysis are provided in **Figure S1** (Supporting Information).

## Figures and Tables

> [!figure] #fig:results width=100%
> ![](figures/figure1.pdf)
>
> **Example Figure.** Lorem ipsum dolor sit amet, consectetur adipiscing elit.

> [!figure] #fig:fullwidth span=full width=90% align=center
> ![](figures/figure2.pdf)
>
> **Example Figure (full width, two-column).** Lorem ipsum dolor sit amet, consectetur adipiscing elit.

> [!table] #tbl:data width=80% align=left columns=0.25,0.45,0.30 colsep=4pt fontsize=footnotesize spacing=1.1
>
> **Example Table.** Results summary.

| Group     | Mean (SD)  | P-value |
| :-------- | :--------: | :-----: |
| Control   | 12.5 (1.2) |    -    |
| Treatment | 18.2 (2.1) | < 0.05  |

## Statistical Analysis
Curabitur malesuada erat sit amet massa. Fusce ac convallis erat, vel aliquet diam. The data is summarized in **@Fig:results** and **@Tbl:data** above.


# Discussion
Pellentesque habitant morbi tristique senectus et netus et malesuada fames ac turpis egestas. Vestibulum tortor quam, feugiat vitae, ultricies eget, tempor sit amet, ante. Donec eu libero sit amet quam egestas semper. Aenean ultricies mi vitae est. Mauris placerat eleifend leo. Additional western blot data is provided in **Figure S1** and primer sequences are listed in **Table S1** in the Supporting Information. Quisque sit amet est et sapien ullamcorper pharetra. Vestibulum erat wisi, condimentum sed, commodo vitae, ornare sit amet, wisi [@leeCarbonCapture2026].

Aenean fermentum, elit eget tincidunt condimentum, eros ipsum rutrum orci, sagittis tempus lacus enim ac dui. Donec non enim in turpis pulvinar facilisis. Ut felis. Praesent dapibus, neque id cursus faucibus, tortor neque egestas augue, eu vulputate magna eros eu erat. Aliquam erat volutpat. Nam dui mi, tincidunt quis, accumsan porttitor, facilisis luctus, metus [@garciaRemoteWorkDynamics2023].

Morbi in sem quis dui placerat ornare. Pellentesque odio nisi, euismod in, pharetra a, ultricies in, diam. Sed arcu. Cras consequat. Praesent dapibus, neque id cursus faucibus, tortor neque egestas augue, eu vulputate magna eros eu erat. Aliquam erat volutpat. Nam dui mi, tincidunt quis, accumsan porttitor, facilisis luctus, metus.

Phasellus ultrices nulla quis nibh. Quisque a lectus. Donec consectetuer ligula vulputate sem tristique cursus. Nam nulla quam, gravida non, commodo a, sodales sit amet, nisi. Pellentesque fermentum dolor. Aliquam quam lectus, facilisis auctor, ultrices ut, elementum vulputate, nunc.

Sed adipiscing ornare risus. Morbi est est, blandit sit amet, sagittis vel, euismod vel, velit. Pellentesque egestas sem. Suspendisse commodo ullamcorper magna. Ut commodo, neque nec porta fringilla, nunc elit tempor metus, vel ultricies nibh ex sit amet dolor. Donec sodales sagittis magna sed consequat finibus.

## Advanced Layout Tips

### Footnotes
You can add footnotes inline like this^[Lorem ipsum dolor sit amet, consectetuer adipiscing elit.].

### Definition Lists
Term 1
:   Definition of term 1

Term 2
:   Definition of term 2

# Declarations

::: {custom-style="First Paragraph"}
`\setlength{\parindent}{0pt}`{=latex}
**Ethics approval:** Not applicable.

**Consent for publication:** Not applicable.

**Competing interests:** The authors declare no competing interests.
`\setlength{\parindent}{1.5em}`{=latex}
::: 

# References
