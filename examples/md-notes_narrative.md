---
title: "Introduction to Research Methods"
subtitle: "Lecture Notes — Week 3"
author: "Dr. Jane Smith"
date: "Winter Semester 2024"
toc: true
---
\newpage

> **Profile:** Use with `pdf-notes` (Notes & Scripts) for digital sharing.
> Also works with `pdf-default` or `pdf-draft` for printing.

# Learning Goals

After this lecture, you should be able to:

- Distinguish between qualitative and quantitative research designs
- Identify common sources of bias in experimental studies
- Explain why replication matters for scientific claims

# What is Research?

Research is the systematic investigation of a question or problem. Good research is **reproducible** — others can follow your methods and obtain similar results [@wilsonStatisticalMethods2023].

> *"The goal of science is to build better models of reality."*
> — Anonymous

The research process typically follows these stages:

1. Formulate a question
2. Review existing literature
3. Design a study
4. Collect and analyze data
5. Interpret and communicate findings

# Research Designs

## Quantitative vs. Qualitative

**Quantitative research** uses numerical data and statistical analysis. It answers questions like "how much?" or "how often?"

**Qualitative research** uses non-numerical data (interviews, observations, texts). It answers questions like "why?" or "how do people experience this?"

| Aspect | Quantitative | Qualitative |
| --- | --- | --- |
| Data type | Numbers, measurements | Words, images, observations |
| Sample size | Usually large | Usually small |
| Analysis | Statistical | Thematic, interpretive |
| Goal | Generalize | Understand depth |

## Experimental vs. Observational

In **experimental** studies, researchers manipulate variables and measure outcomes. In **observational** studies, researchers observe without intervention.

# Bias and Validity

Bias is systematic error that distorts results. Common sources include:

- **Selection bias** — participants are not representative
- **Confirmation bias** — researchers see what they expect
- **Publication bias** — only positive results get published

To reduce bias, use randomization, blinding, and pre-registration of hypotheses.

# Figures

Figures help illustrate concepts. Reference them with `@Fig:label` syntax.

![**Example figure.** This figure demonstrates how to include images in notes.](figures/figure1.pdf){#fig:research width=85%}

As shown in **@Fig:research**, visual elements make notes more engaging and easier to understand.

# Markdown Features

## Text Formatting

Use **bold** for emphasis, *italics* for terms, and `inline code` for commands.

You can also use:
- ~~Strikethrough~~ for corrections
- ==Highlighting== for key points (PDF only)
- Sub~script~ and super^script^ for formulas like H~2~O or E=mc^2^

## Block Quotes

Use block quotes for important statements or citations:

> Research is formalized curiosity. It is poking and prying with a purpose.
> — Zora Neale Hurston

## Definition Lists

Reproducibility
:   The ability to obtain consistent results using the same data and methods.

Replicability
:   The ability to obtain consistent results across different studies with new data.

## Code Example

Include code sparingly — one runnable snippet is often enough:

```python
# Calculate mean and standard deviation
import statistics
data = [23.5, 24.1, 22.8, 25.0, 23.9]
print(f"Mean: {statistics.mean(data):.2f}")
print(f"SD: {statistics.stdev(data):.2f}")
```

# Citations and References

Citations work just like in manuscripts. Use `[@key]` syntax:

- Single citation: [@smithDeepTissueImaging2024]
- Multiple citations: [@wilsonStatisticalMethods2023; @doeQuantumCoherence2025]

The bibliography is automatically generated at the end.

# Key Takeaways

- Research requires systematic methods, not just curiosity
- Choose your design based on your question
- Be aware of bias at every stage
- Replication strengthens scientific claims

# Exercises

1. Find a published study in your field. Is it quantitative or qualitative?
2. List two potential sources of bias in that study.
3. How could the study be improved?

# Further Reading

- Deep tissue imaging methods: [@smithDeepTissueImaging2024]
- Statistical foundations: [@wilsonStatisticalMethods2023]
