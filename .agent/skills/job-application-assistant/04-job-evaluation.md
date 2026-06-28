# Job Evaluation Framework

## Scoring Dimensions

Evaluate each job posting against these five dimensions:

### 1. Technical Skills Match (0-100)
How well do the required/preferred skills align with the candidate's capabilities?

| Score | Meaning |
|-------|---------|
| 80-100 | Core requirements are primary skills |
| 60-79 | Most requirements match, 1-2 gaps that are learnable |
| 40-59 | Partial match, significant upskilling needed |
| 0-39 | Fundamental mismatch |

**Strong match areas:** Python, SQL, PowerBI, R, Excel, data analysis, ETL pipelines, GHG accounting, ESG reporting, LCA, NLP/ML, data modelling, PowerBI dashboards
**Moderate match areas:** MATLAB, GAMS (optimization), Tableau, Databricks, JavaScript, statistical modelling, scenario analysis, forecasting
**Weak match areas:** Financial modelling, commodity trading, SAP, advanced cloud infrastructure (AWS/Azure/GCP beyond basic use), front-end development

### 2. Experience Match (0-100)
Does work history align with what they're looking for?

| Score | Meaning |
|-------|---------|
| 80-100 | Direct experience in the same domain and role type |
| 60-79 | Related experience, transferable skills clear |
| 40-59 | Adjacent experience, would need to make the case |
| 0-39 | Unrelated experience |

**Strong:** ESG/sustainability analyst, climate data analyst, carbon accounting, energy systems modelling, data analysis in environmental contexts
**Moderate:** Market analysis (transferable quantitative skills), general data analyst roles, energy analyst, sustainability consultant
**Entry-level/adjacent:** Financial services analyst, commodity analyst, investment analyst (analytical skills transfer but domain experience is new)

### 3. Behavioral/Culture Fit (0-100)
Does the role and company culture match the behavioral profile?

| Score | Meaning |
|-------|---------|
| 80-100 | Culture strongly matches behavioral preferences |
| 60-79 | Mixed signals but mostly compatible |
| 40-59 | Some friction areas |
| 0-39 | Significant culture mismatch |

**Red flags to research:** Department disorganization, work dominated by maintenance over development, poor chemistry with leadership, culture mismatches. Check reviews, media coverage, LinkedIn connections, and network contacts for insider perspective.

### 4. Location & Logistics (Pass/Fail + Notes)
- Within commute range: PASS
- Remote with occasional office: PASS
- Requires relocation: FAIL (deal-breaker)
- Frequent international travel: FLAG (discuss with user)

**Current location:** Oslo, Norway (Trondheimsveien 64)
**Commute range:** Greater Oslo Region, hybrid/remote options welcome

### 5. Career Alignment & Motivation (0-100)
Does this role advance career goals and contain tasks that energize?

| Score | Meaning |
|-------|---------|
| 80-100 | Strongly aligned with career direction, clear growth path |
| 60-79 | Good role but only partially aligned with long-term goals |
| 40-59 | Decent job but doesn't build toward career goals |
| 0-39 | Dead end or backwards step |

**Career goals:**
- Grow expertise in climate and ESG data analytics, with a focus on carbon accounting and decarbonisation strategy
- Deepen involvement in the **energy industry** — a sector in constant flux due to renewable energy growth and the massive focus on electrification. Wants to apply analytical skills to help shape the energy transition
- Develop into **consulting roles** focusing on known sectors (energy, sustainability) while staying open to new industries
- Move toward roles that combine technical data skills with strategic decision-making influence
- Build a profile as a trusted analyst who turns complex environmental data into business-relevant insights

**Motivation filter:** Evaluate not just whether you *can* do the tasks, but whether the tasks will *energize* you. Consider:
- Tasks that energize: Building data pipelines and models, solving analytical problems with Python/SQL, translating data into insights for stakeholders, working with sustainability/climate data, learning new tools and domains, collaborating with cross-functional teams
- Tasks that drain: Repetitive manual data entry, purely administrative work, roles with no environmental or analytical substance, excessive travel, high-pressure sales targets
- Non-task factors: Autonomy to own projects, supportive management, mission-driven company culture, work-life balance, professional development opportunities

**Ideal role characteristics:**
- **Seniority:** Mid-level (not entry-level — has ~4 years of experience and wants roles that reflect that)
- **Industry preference:** Energy industry (top), sustainability/climate, consulting
- **Organization type:** Corporate, research institutes, and consulting firms. Not keen on startups unless they have a proven track record.
- **Dream organizations:** IEA (International Energy Agency), ITF (International Transport Forum), leading research institutes like **CICERO**, **NORCE**, **IFE** (Institute for Energy Technology)
- **Role type:** Analyst, consultant, or data specialist with strategic influence
- **Company culture:** Mission-driven, intellectually curious, collaborative
- **Work arrangement:** Hybrid/remote-friendly, Oslo-based

**Life situation alignment:** Consider personal constraints:
- **Security:** Currently employed, open to the right opportunity (not urgent)
- **Flexibility:** Open to hybrid/remote arrangements; located in Oslo
- **Professional development:** Looking for roles that build new skills while leveraging existing ones

### 6. Salary Benchmark (Optional)

If the salary lookup tool is configured (`salary_data.json` exists), look up the company:
```
python salary_lookup.py "<Company Name>" --json
```

If a city is known from the posting, add `--city "<City>"` to narrow results.

Present findings as:
```
### Salary Benchmark
| Metric | Value |
|--------|-------|
| [Category] index | XX.X (+/-X.X% vs baseline) |
| Overall index | XX.X (+/-X.X% vs baseline) |
```

Interpret results relative to the baseline defined in the data file's metadata. For index-based data, higher typically means above-market compensation.

If the salary tool is not configured, skip this section.

## Output Format

Present the evaluation as:

```
## Job Fit Evaluation: [Role] at [Company]

| Dimension | Score | Notes |
|-----------|-------|-------|
| Technical Skills | XX/100 | [brief note] |
| Experience Match | XX/100 | [brief note] |
| Behavioral Fit | XX/100 | [brief note] |
| Location | PASS/FAIL | [brief note] |
| Career Alignment | XX/100 | [brief note] |

**Overall Score: XX/100** (weighted average of scored dimensions)

### Verdict: [Strong Fit / Good Fit / Moderate Fit / Weak Fit / Poor Fit]

### Key Strengths for This Role
- [bullet points]

### Gaps to Address
- [bullet points]

### Recommendation
[1-2 sentences: apply/skip/apply with caveats]

### Company Research Checklist
- [ ] Checked company website (mission, values, recent news)
- [ ] Checked review sites (Glassdoor, Finn, etc.)
- [ ] Checked LinkedIn for team size, recent hires, connections
- [ ] Checked media for restructuring, growth, or workplace issues
- [ ] Identified network contacts who may know the team/manager
```

## Weighting
- Technical Skills: 30%
- Experience Match: 25%
- Behavioral Fit: 15%
- Career Alignment: 30%

(Location is pass/fail, not weighted)

## Thresholds
- **Strong Fit** (75+): Definitely apply, tailor everything
- **Good Fit** (60-74): Apply, address gaps in cover letter
- **Moderate Fit** (45-59): Consider carefully, discuss with user
- **Weak Fit** (30-44): Probably skip unless strategic reasons
- **Poor Fit** (<30): Skip

## Pre-Application: Call the Employer (Best Practice)

Before writing the application, consider whether the candidate should call the contact person listed in the posting. **Only call if there are substantive questions** - never call just to "be remembered."

### When to Suggest Calling
- The posting has unclear or ambiguous requirements
- It's unclear which competencies are essential vs. nice-to-have
- The role description is vague about day-to-day tasks
- There's a named contact person who invites questions

### Good Questions to Ask
- "What are the primary challenges in this role?"
- "How is time typically divided across the listed responsibilities?"
- "Which competencies are most critical for success in this position?"
- "What does success look like in the first 6-12 months?"

### Rules for the Call
- Prepare a 30-second "elevator pitch" about your background in case they ask
- The call's purpose is **gathering information**, not delivering a pitch
- Take notes - use what you learn to tailor the application
- Reference the conversation naturally in the cover letter ("After speaking with [name], I was especially drawn to...")
