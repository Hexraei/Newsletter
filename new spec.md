# Feature Spec (Clear Output): “Best Skills to Learn for Placements” (per Department)

## 1) What your client is asking (plain English)
Build a feature where a user selects a **specific department** (ex: CSE / ECE / Mechanical / Civil / MBA / etc.), and your system returns:

1. A **ranked list of the best skills** to learn for getting a job/placement in that department.
2. Each skill is given a **rating out of 10**, sorted **highest → lowest**.
3. The ranking is based on:
   - **Current placement trends** (what is hiring now / last 6–18 months)
   - **Future placement trends** (what is expected to grow next 12–36 months)
   - “Coordinate the date between these two trends” = align both time windows and choose skills that are good **now** AND still useful **soon**.
4. For each skill, also show **where to learn it**:
   - **1st preference:** Tier-1 college courses (IITs/NITs/IISc/IIITs, etc. depending on the country scope)
   - **2nd preference:** High-traffic third-party courses (Coursera/Udemy/etc.)
5. “Repeat the search multiple times through multiple sources” = don’t rely on one website. Use multiple sources and combine.

---

## 2) Inputs (what the user provides)
- **Department** (required)  
  Example: “Computer Science”, “Mechanical Engineering”, “ECE”
- Optional filters (recommended for a useful product):
  - **Target role** (ex: “SDE”, “Data Analyst”, “VLSI”, “Design Engineer”)
  - **Location** (India / Chennai / Bangalore / Global)
  - **Experience level** (Student / Fresher / 1–3 years)
  - **Time available** (2 weeks / 2 months / 6 months)
  - **Preference** (More theory / more projects)

---

## 3) Output (what your UI / API should return)
### A) Summary Block (Top-level)
- Department chosen
- Date generated
- Sources used count (ex: 12 sources)
- Trend windows used:
  - Current: (example) last 12 months
  - Future: (example) next 24 months
- 3–5 line “What’s happening in hiring” overview

### B) Ranked Skills List (core output)
Return **10–20 skills** like this (each item should be consistent):

For each skill:
- **Skill Name**
- **Rating (/10)** (descending)
- **Why it matters for placements** (2–4 bullets)
- **Current trend evidence** (1–3 bullets + sources)
- **Future trend evidence** (1–3 bullets + sources)
- **Recommended learning path**:
  1) Tier-1 college courses (links)
  2) High-traffic third-party courses (links)
  3) Starter project ideas (1–2 projects)
- **Time to become job-ready** (rough range, ex: 2–6 weeks)
- **Prerequisites** (if any)

### C) Sources Section (transparency)
- A list of sources grouped by type, with publish dates:
  - Job postings (LinkedIn, Indeed, Naukri, etc.)
  - Industry reports (WEF, Gartner, McKinsey, etc.)
  - University course pages (IIT/NPTEL/IIIT etc.)
  - Skill trend data (Google Trends / GitHub / StackOverflow surveys)
- Mention how many were used and which were weighted higher.

### D) “How we ranked” (small explanation)
A short explanation of scoring:
- Example weights:
  - Current demand (job postings frequency): 40%
  - Future growth signals (reports/trend signals): 35%
  - Role relevance to department: 15%
  - Learning accessibility & ROI: 10%

---

## 4) What “coordinate the date between trends” means (important)
It means:
- Don’t mix a 2019 report with 2026 job postings blindly.
- Use **time windows**:
  - **Current window**: last 6–18 months (fresh hiring demand)
  - **Future window**: next 12–36 months (growth projections)
- A skill scores highest if it:
  - Appears strongly in current demand **and**
  - Has signals that it will remain/grow soon.

So the output should show both:
- “Hiring now” evidence
- “Hiring soon” evidence

---

## 5) Example Output (shape only)

### Department: Mechanical Engineering (India)
Generated: 2026-02-25  
Sources used: 14  
Trend windows: Current (2025-02 → 2026-02), Future (2026-03 → 2028-03)

#### Top Skills
1. **CAD (SolidWorks / CATIA)** — **9.4/10**
   - Why: used in design roles, product development, manufacturing
   - Current evidence: seen frequently in job descriptions (…)
   - Future evidence: product + manufacturing digitization trend (…)
   - Learn:
     - Tier-1: NPTEL / IIT design courses (…)
     - High-traffic: Coursera/Udemy top enrollments (…)
   - Projects: design a gearbox assembly, tolerance stack-up
   - Time: 3–6 weeks

2. **GD&T + Manufacturing Drawings** — **9.1/10**
   ...

(continue)

---

## 6) “Best sources to learn” rules (your feature logic)
For each skill, show learning sources in this order:

### Priority 1: Tier-1 institutions (first preference)
- Official course pages / syllabi / NPTEL / IIT / IISc / IIIT / NIT, etc.
- Reason: credibility + structured learning.

### Priority 2: High-traffic third-party courses (second preference)
- Courses with strong enrollment/ratings/reviews/traffic.
- Reason: accessible and popular.

### Optional Priority 3: Official docs (bonus)
- Tool documentation (ex: AWS, Google Cloud, SolidWorks docs)
- Standard references (ISO, IEEE, etc.)

---

## 7) What you should store / return in the backend (data model idea)
For each skill:
- skill_id, name, department_tags, role_tags
- score_total (0–10)
- score_current, score_future
- evidence_current: [{source, date, quote/snippet, link}]
- evidence_future: [{source, date, snippet, link}]
- learning_sources_tier1: [{title, institution, link}]
- learning_sources_thirdparty: [{platform, course, link, popularity_metric}]
- project_ideas: [ ... ]
- prerequisites: [ ... ]
- updated_at

---

## 8) “Best summarising prompt” (attach this to the feature)
Use this prompt to summarize raw source text into structured evidence for each skill:

### Summarization Prompt (copy-paste)
You are an analyst summarizing hiring and skill demand evidence.
Input: Department, skill, and a chunk of source text (job posting/report/course page).
Output ONLY valid JSON with no extra commentary.

Rules:
- Be faithful to the source; do not invent facts.
- Extract only job/skill demand signals.
- Always include the source date if present; if missing, set null.
- Keep bullets short.

JSON format:
{
  "department": "<department>",
  "skill": "<skill>",
  "source_type": "job_posting | industry_report | university_course | trend_data | other",
  "source_name": "<website/org>",
  "source_date": "<YYYY-MM-DD or null>",
  "region": "<if known, else null>",
  "signals": {
    "current_demand": [
      "<1 short bullet>",
      "<1 short bullet>"
    ],
    "future_demand": [
      "<1 short bullet>",
      "<1 short bullet>"
    ]
  },
  "key_phrases": ["<phrase1>", "<phrase2>"],
  "confidence": 0.0
}

---

## 9) Minimum viable UI output (if you want simple)
- Department dropdown
- “Top 10 skills” list with rating bars
- Click a skill → expands evidence + learning links
- “Sources & methodology” collapsible section

---

## 10) Done definition (what “good” looks like)
A user selects a department and instantly gets:
- A ranked, rated list of skills (descending)
- Clear reasoning with current + future trend evidence
- Learning sources prioritized Tier-1 then high-traffic platforms
- Transparent sources list and dates