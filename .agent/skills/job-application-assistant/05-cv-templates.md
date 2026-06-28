# CV Templates and Tailoring Guide

## Template: LaTeX moderncv (Banking Style)

All CVs use the moderncv LaTeX package with the "banking" style and "blue" color scheme.

**Output file:** `cv/main_<company>.tex`
**Compile with:** **xelatex** (same engine as cover letters).
**Master reference:** `cv/main_example.tex` (comprehensive CV with all competencies, experience, and achievements - use as source when building targeted CVs)

### Compile command

```bash
cd cv && xelatex -interaction=nonstopmode main_<company>.tex
```

Expected output: `Output written on main_<company>.pdf (2 pages, ...)`. Any page count other than 2 is a failure that must be fixed before presenting to the user.

## Document Structure

```latex
\documentclass[11pt,a4paper,sans]{moderncv}
\moderncvstyle{banking}
\moderncvcolor{blue}

% Force both first and last name AND section headings to render in moderncv
% blue (color1) with correct font scaling.
\renewcommand*{\firstnamestyle}[1]{{\fontsize{34}{36}\bfseries\upshape\color{color1}\selectfont#1}}
\renewcommand*{\lastnamestyle}[1]{{\fontsize{34}{36}\bfseries\upshape\color{color1}\selectfont#1}}
\renewcommand*{\sectionstyle}[1]{{\sectionfont\color{color1}#1}}

% moderncv natively loads hyperref; do not call \usepackage{hyperref} here.
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    filecolor=magenta,
    urlcolor=blue,
    pdftitle={Siddhant Gupta - CV},
    pdfpagemode=FullScreen,
}
\usepackage[scale=0.77]{geometry}
\usepackage{import}
\usepackage{needspace} % Required for orphaned entry management

% Personal data
\name{Siddhant}{Gupta}
\address{Trondheimsveien 64, Oslo, Norway}{}{}
\phone[mobile]{+47 92206297}
\email{siddhantbenz@gmail.com}
\social[linkedin]{siddhantgupta1996}

\begin{document}
\makecvtitle

% CV content goes here

\end{document}
```

### Color overrides

The three `\renewcommand*` lines in the preamble are required on xelatex. Without them the firstname, lastname, and section headings render in black even though `\moderncvcolor{blue}` is set, which looks inconsistent with the rest of the blue accent scheme (links, bullet markers, contact icons). The override forces all three to use `color1` (moderncv's accent colour, which becomes blue under `\moderncvcolor{blue}`). Both names render bold; if you prefer the firstname in regular weight, change the firstnamestyle override from `\bfseries` to `\mdseries`. Don't drop the override - on most modern installs the defaults render visibly wrong.

### Spacing inside itemize lists (important)

**Do not place `\vspace{...}` between `\item` entries in an `itemize` list.** Even though the source looks symmetric, this pattern occasionally produces a noticeably oversized gap before a single item: the inter-item `\vspace` creates a paragraph break that interacts unpredictably with the list's internal `\itemsep`, so LaTeX renders one of the gaps wider than the rest. Remove the inter-item `\vspace` and let `itemize` use its native uniform spacing.

```latex
% WRONG - intermittently produces an oversized gap before one bullet
\begin{itemize}
\item \textbf{Foo}: ...
\vspace{1pt}
\item \textbf{Bar}: ...
\vspace{1pt}
\item \textbf{Baz}: ...
\end{itemize}

% RIGHT - uniform spacing using the list's native itemsep
\begin{itemize}
\item \textbf{Foo}: ...
\item \textbf{Bar}: ...
\item \textbf{Baz}: ...
\end{itemize}
```

Two related patterns are fine and should be kept:
- `\vspace{1pt}` immediately after `\section{...}` (between section heading and first item) - this is between the heading and the list, not between list items.
- `\vspace{3pt}` between top-level `\cventry` blocks in Professional Experience or Education - this gives breathing room between roles and renders consistently.

## Section-by-Section Tailoring

### Profile Statement / Elevator Pitch (Best Practice)
This is the most important section to customize. It appears right after `\makecvtitle`.

Write 5-7 lines that function as an "elevator pitch": a concise, compelling introduction explaining why you're qualified for *this specific role*. Focus on what the employer gains from hiring you and why you're fit for this job (past experience, education, passionate about it)

**Create 2-3 profile statement templates for your main role types:**

**For ESG / Sustainability Analyst roles:**
> Sustainability analyst with 4+ years of experience in carbon accounting accounting, energy systems modelling, and environmental data analysis.  Combines quantitative skills in Python and SQL with domain expertise in CSRD/ESRS, GHG Protocol, and TCFD frameworks to translate complex environmental data into into actionable insights. Supports organisations in meeting their sustainability goals by identifying practical decarbonisation pathways

**For Data Analyst / Data Scientist roles:**
> Data analyst with 4+ years of experience developing quantitative models, automated data pipelines, and predictive tools. Combines strong Python, SQL, and machine learning skills with deep domain knowledge in carbon accounting and energy systems. Translates raw, technical data into clear, data-driven insights for strategic business stakeholders.

**For Energy / Energy System Analyst roles:**
> Energy systems analyst with 4+ years of experience in energy systems modelling, optimisation, and geospatial analysis. Applies Python, SQL, and GAMS to model renewable integration, grid dynamics, and energy transition scenarios. Translates quantitative analysis of physical energy systems into structured insights for strategic decision-making. Background in sustainable energy systems (M.Sc.) with hands-on simulation and optimisation modelling experience.
> 
> **⚠️ Backtrack Test Warning:** Do NOT use this template for roles requiring actual power trading, market risk, or commodity trading experience. The candidate has energy systems analysis experience — this is adjacent to but distinct from commercial trading. If the posting asks for "power trading" or "commodity risk" experience, use the Analyst/Data template above and frame adjacent quantitative skills honestly.

**For Researcher / Analyst roles at research institutes:**
> Analyst with a Master's in Sustainable Energy Systems, combining quantitative modelling skills (Python, SQL, GAMS) with domain expertise in carbon accounting, energy systems, and lifecycle assessment. Applies data science methods to evaluate decarbonisation pathways, energy transition scenarios, and sustainability metrics. Experienced in translating complex quantitative analysis into clear policy and strategy recommendations.

### Core Competencies / Skills Section (Best Practice)
Tailor, prioritize, and structure this section to align directly with the primary requirements of the target job description.

* **Target Volume:** List **5–7 key competencies** in a bulleted format.
* **Formatting:** Start each bullet with a bold category label (e.g., **Data Engineering & Analysis:**), followed by specific tools or methodologies, and a brief context line.
* **Prioritization:** Reorder the list so the skills most critical to the target role appear at the very top.
* **Context Over Lists:** Avoid raw tool lists (e.g., just listing "Python, SQL"). Instead, briefly explain how you apply those tools to solve a problem (e.g., *"using Python and SQL to automate data pipelines"*). This demonstrates immediate value to the hiring manager.

### Education
- Always include your highest degrees
- For senior roles, keep education brief (dates and titles only)
- Include thesis topics when relevant to the target role

### Professional Experience
- Rewrite bullet points to emphasize aspects most relevant to the target role
- Use 4-6 bullets for most recent role, 3-4 for previous, 2-3 for older
- **Emphasize measurable results** where possible: "Reduced processing time by X%", "Model adopted by the team"

### Handling Employment Gaps (Best Practice)
If there is a gap in your employment history:
- The gap should be explained matter-of-factly if needed
- Describe how professional development continued during the gap
- Frame as deliberate skill-building and career repositioning

### Publications
- Include Google Scholar link if applicable
- Select 3-4 most relevant publications (not always all of them)
- For non-academic roles, keep brief

### Honors and Awards
- Keep format brief, one line each

### References
- List 2-4 references with name, title, company, and contact
- End with: "More references are available upon request."
- **Do not attach reference letters** - employers typically contact references directly

## Compile-and-Inspect Loop (MANDATORY)

After writing the CV and before presenting to the user, always compile and visually inspect the PDF. Iterate until the layout is clean. Workflow:

1. Run `xelatex -interaction=nonstopmode main_<company>.tex`
2. Check the output page count: must be exactly 2
3. Read the PDF via the Read tool and visually inspect both pages
4. Check for **orphaned entries**: a `\cventry` title line must never sit alone at the bottom of page 1 with its bullets on page 2

### Fixing common page-break problems

**Problem: entry title on page 1, bullets orphaned to page 2**
Add `\needspace{5\baselineskip}` immediately before the problematic `\cventry`:
```latex
\needspace{5\baselineskip}
\item{\cventry{YEAR--YEAR}{Role Title}{Organization}{Location}{}{...}}
```
Include `\usepackage{needspace}` in the preamble.

**Problem: one trailing section spills to page 3 (e.g., References alone on page 3)**
Add `\enlargethispage{2-3\baselineskip}` before a late section (e.g., before `\section{Honors and Awards}`) to stretch page 2 by a few lines. This is the standard LaTeX rescue for near-miss overflows.

**Problem: 3 pages with significant content on page 3**
Cut content — do not compress geometry or `\vspace`. See "Relevance-weighted cutting" below for the rule.

**Problem: content finishes early on page 2 (feels thin)**
Restore the highest-relevance item that was previously cut — a CV that ends mid-page 2 looks incomplete.

## ⚠️ Hard Rule: Differentiation Check (anti-copy-paste)
Every CV must be unique to the target role. Before writing the CV, the drafter must pass this self-check:

> **"State in 2-3 sentences how this CV's profile statement, competency ordering, and experience bullets differ from the Position Green CV and the Hydro CV. If you cannot articulate a clear difference, the targeting is insufficient."**

This check exists because in practice, CVs across different roles (e.g., quant risk analyst vs. customer success manager) were being written with nearly identical profile statements and competency lists. Two roles with different requirements need two different CVs.

## Page Budget - Hard 2-Page Limit

The CV **must** fit on exactly 2 pages when compiled. Use these content limits as a guide:

| Section | Max budget |
|---------|-----------|
| Profile statement | 3-4 lines |
| Skills | 5 items, each 1-2 lines |
| Most recent role | 4-5 bullets |
| Previous role | 2-3 bullets |
| Older roles | 2 bullets (1 line each) |
| Education | 2-3 entries |
| Publications | 2-3 entries |
| Awards | 3 entries, single line each |
| References | "Available upon request." (single line) |

**If in doubt, cut rather than squeeze.** Reducing `\vspace` or geometry scale to force-fit content makes the CV look cramped.

## Relevance-weighted cutting (the right way to shrink a CV)

**Cut by signal, not by section.** Static priority lists ("remove oldest education first, then shorten the earliest role...") are wrong when a relevant "lower-priority" item is competing with an irrelevant "higher-priority" item. An older-role bullet that speaks directly to the posting is worth more than a recent-role bullet that does not.

For every candidate line, score three things:

1. **Relevance to THIS posting** — does the line hit a named tool, keyword, or stated responsibility in the job ad?
2. **Uniqueness** — is it the only place this claim appears, or is it duplicated elsewhere in the CV?
3. **Narrative load** — does the cover letter depend on it? If cutting the line would force you to rewrite a cover-letter paragraph, it is load-bearing.

Cut the lowest-total-score line first, regardless of which section it sits in.

### Practical order of cuts (easiest → last resort)

1. **Redundancy.** If an achievement appears in both Core Competencies AND a role bullet, the Core Competencies version is usually the cleaner cut (the experience bullet is more concrete evidence).
2. **Profile-statement fluff.** A sentence that just restates what Publications or Skills will show. ("Peer-reviewed publications on X..." is already a Publications entry — profile can claim it once and stop.)
3. **Low-relevance experience bullets.** A bullet about work that does not touch posting keywords, wherever it sits. This cuts across sections before touching the structural list.
4. **Low-relevance supporting content.** An older-role bullet that does not speak to the target role. A certification that does not touch the posting's stack. A language entry that can be condensed to one line.
5. **Low-relevance publications.** Keep 1-2 publications that best match the posting. Cut the rest before touching experience bullets.
6. **Last-resort structural cuts.** Oldest education entry, tightening an older role to 2 bullets, collapsing Certifications into a single line. These only happen if the relevance-weighted cuts above have already been exhausted.

### Pitfalls to avoid

- Do not mechanically cut from the bottom of a static section list without checking relevance. "Cut the oldest role first" is wrong if that role is literally about the skill the posting asks for.
- Do not cut the one concrete example the cover letter leans on. Relevance is measured against the cover letter you wrote, not just the job posting — interviewers will have read both.
- Do not cut to fit if the fit is borderline (2.02 pages). Prefer `\enlargethispage{2-3\baselineskip}` on a late section for near-misses; reserve content cuts for genuine overflow (content on page 3 that is more than a single trailing section).

## Hard Rule: Backtrack Test on Profile Statements

Every profile statement must pass the **interview backtrack test**: could the candidate comfortably explain every claim in the profile in an interview without backtracking?

- **OK:** "Energy systems modelling experience using GAMS and Python to simulate renewable integration"
- **Flag it:** "Power market dynamics and commercial trading strategies" — the candidate does not have trading experience
- **Never:** Any claim that implies domain experience the candidate does not have

If a profile statement would require the candidate to say "well, what I actually meant was..." in an interview, the statement is too far. Rewrite it.

## Recommended Section Order

The section order varies by role type to ensure your strongest assets are read first:

**For technical / data science / ML roles:**
1. Profile statement / elevator pitch
2. Core competencies / Skills
3. Professional Experience (reverse chronological) — prioritizes technical industry delivery
4. Education (reverse chronological)
5. Languages
6. Publications & Awards (if applicable)
7. References

**For domain-specific / specialist roles (ESG, energy, policy):**
1. Profile statement / elevator pitch
2. Core competencies / Skills
3. Professional Experience (reverse chronological) — highlights practical regulatory and methodology application first
4. Education (reverse chronological) — academic credentials support the practical experience
5. Certifications (e.g., Sustainability Leadership, carbon accounting courses)
6. Languages
7. References

**For analyst roles (data, market, commodity):**
1. Profile statement / elevator pitch
2. Core competencies / Skills
3. Professional Experience (reverse chronological)
4. Education (reverse chronological)
5. Languages
6. References

*Note: For PhD, academic, or research-intensive applications, you may swap Education and Professional Experience to place your academic credentials immediately after your Skills.*
