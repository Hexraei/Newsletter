"""Department relevance scoring — assigns articles to departments based on content analysis.

Each department has a set of high-signal keywords (weighted) and negative keywords.
An article's title+content is scored against each department; only departments
above a threshold are assigned.

This replaces the old approach of blindly copying source.department_tags.
"""

import re
from typing import Dict, List, Tuple

# ── Department keyword dictionaries ──────────────────────────────────────────
# Format: { "DEPT": { "keywords": [(term, weight), ...], "negative": [term, ...] } }
# Weight scale: 3 = strong signal, 2 = moderate, 1 = weak/contextual

DEPARTMENT_PROFILES: Dict[str, dict] = {
    "CSE": {
        "keywords": [
            # Core CS
            ("computer science", 3), ("software engineering", 3), ("programming", 3),
            ("algorithm", 3), ("data structure", 3), ("compiler", 3),
            ("operating system", 3), ("database", 2), ("sql", 2),
            # Languages
            ("python", 2), ("javascript", 2), ("typescript", 2), ("java", 2),
            ("c++", 2), ("golang", 2), ("rust lang", 2),
            # Web/App
            ("web development", 2), ("frontend", 2), ("backend", 2), ("fullstack", 2),
            ("react", 2), ("angular", 2), ("vue.js", 2), ("node.js", 2),
            ("django", 2), ("fastapi", 2), ("flask", 2),
            # Systems
            ("cloud computing", 2), ("devops", 2), ("docker", 2), ("kubernetes", 2),
            ("aws", 2), ("azure", 2), ("microservice", 2), ("api", 1),
            # Security
            ("cybersecurity", 3), ("cyber security", 3), ("vulnerability", 2),
            ("exploit", 2), ("malware", 2), ("ransomware", 2), ("hacking", 2),
            ("data breach", 2), ("zero-day", 2), ("encryption", 2),
            # Data
            ("big data", 2), ("data engineering", 2), ("data pipeline", 2),
            # General CS
            ("coding", 2), ("developer", 1), ("open source", 2), ("github", 2),
            ("git", 1), ("linux", 2), ("startup", 1), ("tech company", 1),
            ("software", 1), ("app", 1),
        ],
        "negative": [
            "pharmacist", "pharmacy", "nurse", "nursing", "medical college",
            "mbbs", "neet", "civil service", "upsc", "ssc", "railway",
            "agriculture", "farming", "crop", "law college", "judiciary",
        ],
    },
    "IT": {
        "keywords": [
            ("information technology", 3), ("it industry", 3), ("it sector", 3),
            ("networking", 2), ("network security", 3), ("firewall", 2),
            ("tcp/ip", 3), ("dns", 2), ("server", 1), ("sysadmin", 2),
            ("system administration", 2), ("cloud", 2), ("saas", 2),
            ("erp", 2), ("crm", 2), ("it services", 2),
            ("infosys", 2), ("tcs", 2), ("wipro", 2), ("hcl tech", 2),
            ("tech mahindra", 2), ("cognizant", 2),
            ("digital transformation", 2), ("it infrastructure", 2),
            ("helpdesk", 2), ("itsm", 2), ("itil", 2),
            ("software", 1), ("coding", 1), ("developer", 1),
            ("cybersecurity", 2), ("data center", 2),
        ],
        "negative": [
            "pharmacist", "pharmacy", "medical", "mbbs", "agriculture",
        ],
    },
    "AIDS": {
        "keywords": [
            ("artificial intelligence", 3), ("machine learning", 3),
            ("deep learning", 3), ("neural network", 3), ("nlp", 2),
            ("natural language processing", 3), ("computer vision", 3),
            ("data science", 3), ("data analytics", 2),
            ("large language model", 3), ("llm", 2), ("gpt", 2),
            ("openai", 2), ("chatgpt", 2), ("transformer", 2),
            ("generative ai", 3), ("gen ai", 2),
            ("reinforcement learning", 3), ("supervised learning", 2),
            ("unsupervised learning", 2), ("classification", 1),
            ("regression", 1), ("clustering", 1),
            ("tensorflow", 2), ("pytorch", 2), ("keras", 2), ("scikit", 2),
            ("hugging face", 2), ("model training", 2), ("fine-tuning", 2),
            ("prompt engineering", 2), ("embedding", 2),
            ("recommendation system", 2), ("predictive analytics", 2),
            ("autonomous", 1), ("robot", 1),
        ],
        "negative": [
            "pharmacist", "pharmacy", "medical college", "agriculture",
        ],
    },
    "ECE": {
        "keywords": [
            ("electronics", 3), ("communication engineering", 3),
            ("semiconductor", 3), ("microprocessor", 3), ("microcontroller", 3),
            ("vlsi", 3), ("fpga", 3), ("embedded system", 3),
            ("pcb", 2), ("circuit", 2), ("transistor", 2), ("diode", 2),
            ("signal processing", 3), ("digital signal", 3), ("analog", 2),
            ("antenna", 2), ("wireless", 2), ("5g", 2), ("6g", 2),
            ("telecom", 2), ("iot", 2), ("internet of things", 3),
            ("sensor", 2), ("actuator", 2), ("arduino", 2), ("raspberry pi", 2),
            ("rf", 2), ("radar", 2), ("lidar", 2), ("optical fiber", 2),
            ("qualcomm", 2), ("intel", 1), ("amd", 1), ("nvidia", 1),
            ("chip", 2), ("wafer", 2), ("foundry", 2), ("tsmc", 2),
        ],
        "negative": [
            "pharmacist", "pharmacy", "law", "judiciary", "agriculture",
        ],
    },
    "EEE": {
        "keywords": [
            ("electrical engineering", 3), ("power system", 3),
            ("power grid", 3), ("transformer", 2), ("generator", 2),
            ("motor", 2), ("renewable energy", 3), ("solar energy", 3),
            ("wind energy", 3), ("battery", 2), ("energy storage", 2),
            ("electric vehicle", 3), ("ev", 2), ("charging station", 2),
            ("smart grid", 3), ("electricity", 2), ("voltage", 2),
            ("power electronics", 3), ("inverter", 2), ("converter", 2),
            ("power plant", 2), ("turbine", 2), ("substation", 2),
            ("electrical safety", 2), ("insulation", 2),
            ("ntpc", 2), ("adani green", 2), ("tata power", 2),
            ("bhel", 2), ("power ministry", 2),
        ],
        "negative": [
            "pharmacist", "pharmacy", "software", "coding",
        ],
    },
    "ME": {
        "keywords": [
            ("mechanical engineering", 3), ("thermodynamics", 3),
            ("fluid mechanics", 3), ("heat transfer", 3),
            ("manufacturing", 2), ("cnc", 2), ("machining", 2),
            ("cad", 2), ("solidworks", 2), ("catia", 2), ("ansys", 2),
            ("finite element", 3), ("stress analysis", 2),
            ("automobile", 2), ("automotive", 2), ("engine", 2),
            ("turbine", 2), ("hydraulic", 2), ("pneumatic", 2),
            ("material science", 2), ("metallurgy", 2), ("alloy", 2),
            ("3d printing", 2), ("additive manufacturing", 3),
            ("hvac", 2), ("refrigeration", 2),
            ("vibration", 2), ("dynamics", 1), ("kinematics", 2),
            ("gear", 2), ("bearing", 2), ("shaft", 2),
        ],
        "negative": [
            "pharmacist", "pharmacy", "software", "programming",
        ],
    },
    "CE": {
        "keywords": [
            ("civil engineering", 3), ("structural engineering", 3),
            ("construction", 2), ("concrete", 2), ("steel structure", 2),
            ("bridge", 2), ("highway", 2), ("road construction", 2),
            ("geotechnical", 3), ("soil mechanics", 3),
            ("surveying", 2), ("gis", 2), ("remote sensing", 2),
            ("water treatment", 2), ("wastewater", 2), ("sewage", 2),
            ("environmental engineering", 2), ("pollution control", 2),
            ("earthquake engineering", 3), ("seismic", 2),
            ("building", 1), ("architecture", 1), ("urban planning", 2),
            ("smart city", 2), ("infrastructure", 2),
            ("dam", 2), ("canal", 2), ("irrigation", 2),
            ("nhai", 2), ("nhpc", 2),
        ],
        "negative": [
            "pharmacist", "pharmacy", "software", "coding",
        ],
    },
    "CH": {
        "keywords": [
            ("chemical engineering", 3), ("petrochemical", 3),
            ("refinery", 2), ("distillation", 2), ("reactor design", 3),
            ("process engineering", 3), ("catalysis", 2), ("catalyst", 2),
            ("polymer", 2), ("biochemical", 2), ("fermentation", 2),
            ("mass transfer", 3), ("heat exchanger", 2),
            ("separation process", 2), ("absorption", 2),
            ("pharmaceutical manufacturing", 2), ("drug manufacturing", 2),
            ("process control", 2), ("instrumentation", 2),
            ("corrosion", 2), ("material degradation", 2),
            ("green chemistry", 2), ("chemical plant", 2),
            ("ipcl", 2), ("reliance industries", 1),
        ],
        "negative": [
            "software", "programming", "web development",
        ],
    },
    "BT": {
        "keywords": [
            ("biotechnology", 3), ("bioinformatics", 3),
            ("genetic engineering", 3), ("gene editing", 3), ("crispr", 3),
            ("genomics", 3), ("proteomics", 3), ("dna", 2), ("rna", 2),
            ("molecular biology", 3), ("microbiology", 2),
            ("cell biology", 2), ("stem cell", 2),
            ("biomedical", 2), ("pharmaceutical", 2), ("drug discovery", 2),
            ("clinical trial", 2), ("vaccine", 2), ("immunology", 2),
            ("bioreactor", 2), ("fermentation", 2),
            ("agricultural biotech", 2), ("gmo", 2),
            ("bioethics", 2), ("biosafety", 2),
            ("serum institute", 2), ("biocon", 2),
        ],
        "negative": [
            "software", "programming", "web development", "javascript",
        ],
    },
    "AE": {
        "keywords": [
            ("aerospace", 3), ("aeronautical", 3), ("aviation", 3),
            ("aircraft", 3), ("airplane", 2), ("drone", 2), ("uav", 2),
            ("satellite", 2), ("space", 2), ("isro", 3), ("nasa", 2),
            ("spacex", 2), ("rocket", 2), ("launch vehicle", 2),
            ("propulsion", 3), ("jet engine", 3), ("turbofan", 2),
            ("aerodynamics", 3), ("wind tunnel", 2), ("mach", 2),
            ("flight", 1), ("pilot", 1), ("airbus", 2), ("boeing", 2),
            ("hal", 2), ("hindustan aeronautics", 3), ("drdo", 2),
            ("defence", 2), ("defense", 2), ("missile", 2),
            ("orbit", 2), ("lunar", 2), ("mars mission", 2),
        ],
        "negative": [
            "software", "programming", "pharmacy",
        ],
    },
    "RAE": {
        "keywords": [
            ("robotics", 3), ("automation", 3), ("robot", 3),
            ("robotic arm", 3), ("manipulator", 2), ("actuator", 2),
            ("autonomous vehicle", 3), ("self-driving", 3),
            ("plc", 2), ("programmable logic controller", 3),
            ("scada", 2), ("industrial automation", 3),
            ("control system", 2), ("pid controller", 2),
            ("servo", 2), ("stepper motor", 2), ("mechatronics", 3),
            ("humanoid", 2), ("exoskeleton", 2), ("cobot", 2),
            ("drone", 2), ("uav", 2), ("ros", 2),
            ("machine vision", 2), ("lidar", 2),
            ("boston dynamics", 2), ("fanuc", 2), ("abb robotics", 2),
            ("kuka", 2),
        ],
        "negative": [
            "pharmacy", "law", "judiciary",
        ],
    },
    "PT": {
        "keywords": [
            ("production technology", 3), ("manufacturing technology", 3),
            ("production engineering", 3), ("industrial engineering", 3),
            ("lean manufacturing", 3), ("six sigma", 3),
            ("quality control", 2), ("quality assurance", 2),
            ("cnc", 2), ("cnc machining", 3), ("lathe", 2), ("milling", 2),
            ("casting", 2), ("forging", 2), ("welding", 2), ("stamping", 2),
            ("injection molding", 2), ("die casting", 2),
            ("supply chain", 2), ("logistics", 2), ("operations management", 2),
            ("industry 4.0", 3), ("smart factory", 2),
            ("3d printing", 2), ("additive manufacturing", 3),
            ("metrology", 2), ("tolerance", 2), ("surface finish", 2),
            ("tool design", 2), ("jig and fixture", 2),
            ("erp", 1), ("sap", 1),
        ],
        "negative": [
            "pharmacy", "law", "judiciary", "agriculture",
        ],
    },
}

# Minimum score to assign an article to a department
RELEVANCE_THRESHOLD = 3

# Shared/general source types that publish cross-department content
GENERAL_SOURCE_TYPES = {
    "india-news", "india-education", "india-policy", "india-career",
    "india-industry", "india-startup", "india-tech",
    "community", "news", "blog",
}


def _tokenize(text: str) -> str:
    """Lowercase and normalize text for matching."""
    return text.lower()


def score_article_departments(
    title: str,
    content: str,
    source_dept_tags: List[str] = None,
    source_type: str = "",
) -> List[Tuple[str, int]]:
    """Score an article against all departments and return matching ones.

    Returns list of (department, score) tuples sorted by score descending.
    Only departments above RELEVANCE_THRESHOLD are included.
    """
    text = _tokenize(f"{title} {title} {content}")  # title weighted 2x

    results = []
    for dept, profile in DEPARTMENT_PROFILES.items():
        # Check negative keywords first
        negatives = profile.get("negative", [])
        neg_count = sum(1 for neg in negatives if neg in text)
        if neg_count >= 2:
            continue  # strong negative signal, skip this dept

        # Score positive keywords
        score = 0
        matched = 0
        for keyword, weight in profile["keywords"]:
            if keyword in text:
                # Use word boundary check for short keywords (<=3 chars)
                if len(keyword) <= 3:
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, text):
                        score += weight
                        matched += 1
                else:
                    score += weight
                    matched += 1

        # Bonus if source is explicitly tagged for this dept (and not a general source)
        if source_dept_tags and dept in source_dept_tags:
            if source_type not in GENERAL_SOURCE_TYPES:
                score += 3  # source tagging bonus for specific sources

        if score >= RELEVANCE_THRESHOLD and matched >= 1:
            results.append((dept, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def assign_departments(
    title: str,
    content: str,
    source_dept_tags: List[str] = None,
    source_type: str = "",
    max_depts: int = 3,
) -> List[str]:
    """Assign department tags to an article based on content analysis.

    Returns list of department keys, max `max_depts`.
    For general/shared sources, only assigns departments with content relevance.
    For specific sources (e.g. ArXiv CS), falls back to source tags.
    """
    scored = score_article_departments(title, content, source_dept_tags, source_type)

    if not scored:
        # No content match — only fall back to source tags for specific sources
        if source_type not in GENERAL_SOURCE_TYPES:
            return (source_dept_tags or [])[:max_depts]
        # General source with no relevance match → empty (will show in "general" feed)
        return []

    # Take top departments, but only if they're within 50% of the best score
    best_score = scored[0][1]
    threshold = best_score * 0.5
    depts = [dept for dept, score in scored if score >= threshold]

    return depts[:max_depts]


# ── Category detection (replaces broken substring matching) ──────────────────

CATEGORY_KEYWORDS = {
    "ai_ml": [
        "artificial intelligence", "machine learning", "deep learning",
        "neural network", "nlp", "natural language processing",
        "computer vision", "large language model", "llm", "gpt",
        "openai", "chatgpt", "generative ai", "transformer model",
        "reinforcement learning", "classification model", "pytorch",
        "tensorflow", "hugging face", "fine-tuning",
    ],
    "security": [
        "cybersecurity", "cyber security", "vulnerability", "exploit",
        "malware", "ransomware", "data breach", "zero-day", "cve",
        "hacking", "phishing", "ddos", "firewall", "encryption",
    ],
    "webdev": [
        "web development", "javascript", "typescript", "react",
        "angular", "vue.js", "svelte", "css", "html", "frontend",
        "next.js", "nuxt", "tailwind", "webpack", "vite",
    ],
    "backend": [
        "backend", "server-side", "fastapi", "django", "flask",
        "spring boot", "node.js", "express.js", "graphql",
        "microservice", "rest api",
    ],
    "mobile": [
        "android", "ios", "flutter", "react native", "swift",
        "kotlin", "mobile app", "mobile development",
    ],
    "devops": [
        "devops", "docker", "kubernetes", "ci/cd", "terraform",
        "ansible", "jenkins", "github actions", "aws", "azure",
        "gcp", "cloud computing", "infrastructure",
    ],
    "career": [
        "job opening", "hiring", "interview", "salary", "career",
        "placement", "internship", "recruitment", "campus placement",
        "job fair", "resume", "job market",
    ],
    "startup": [
        "startup", "funding round", "venture capital", "series a",
        "series b", "ipo", "unicorn", "entrepreneur", "founded",
        "seed funding", "angel investor",
    ],
    "research": [
        "research paper", "arxiv", "ieee", "acm", "journal",
        "conference paper", "peer-reviewed", "citation",
        "preprint", "publication",
    ],
    "electronics": [
        "semiconductor", "chip", "vlsi", "fpga", "microcontroller",
        "pcb", "circuit", "transistor", "embedded", "iot",
    ],
    "robotics": [
        "robot", "robotics", "automation", "autonomous", "drone",
        "plc", "scada", "manipulator", "humanoid",
    ],
    "energy": [
        "renewable energy", "solar", "wind energy", "battery",
        "electric vehicle", "power grid", "smart grid",
    ],
    "biotech": [
        "biotechnology", "genetic", "crispr", "dna", "genome",
        "pharmaceutical", "drug discovery", "vaccine",
    ],
}


def detect_category(title: str, content: str) -> str:
    """Detect content category using multi-word phrase matching.

    Uses full phrases to avoid false positives from short substring matches.
    """
    text = _tokenize(f"{title} {content}")

    scores = {}
    for cat, phrases in CATEGORY_KEYWORDS.items():
        score = 0
        for phrase in phrases:
            if phrase in text:
                score += 1
        if score > 0:
            scores[cat] = score

    if scores:
        return max(scores, key=scores.get)

    return "general"
