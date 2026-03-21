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
            ("kuka", 2), ("waymo", 2), ("nuro", 2), ("figure ai", 2),
            ("agility robotics", 2), ("intuitive surgical", 2),
            ("yaskawa", 2), ("omron", 2), ("clearpath", 2),
            ("franka", 2), ("universal robots", 2),
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

# ── Cross-department keywords (applied to ALL departments) ────────────────
# Career, opportunities, and South India signals that boost relevance for all students
COMMON_CAREER_KEYWORDS = [
    # Jobs & placements
    ("hiring", 3), ("placement", 3), ("campus placement", 3), ("internship", 3),
    ("fresher", 3), ("freshers", 3), ("walk-in", 2), ("recruitment", 2),
    ("job opening", 3), ("off-campus", 3), ("on-campus", 3),
    ("package", 2), ("salary", 1), ("lpa", 2), ("ctc", 2),
    # Exams & certifications
    ("gate exam", 3), ("gate 2026", 3), ("gate 2027", 3),
    ("gre", 2), ("toefl", 1), ("ielts", 1),
    ("nptel", 3), ("nptel certificate", 3), ("swayam", 2),
    ("aws certified", 2), ("google certified", 2), ("certification", 1),
    # Events & competitions
    ("hackathon", 3), ("coding contest", 3), ("programming contest", 3),
    ("workshop", 2), ("bootcamp", 2), ("webinar", 1),
    ("scholarship", 3), ("fellowship", 3), ("competition", 2),
    ("ideathon", 3), ("makeathon", 3), ("smart india hackathon", 3),
    # South India institutional
    ("chennai", 2), ("tamil nadu", 2), ("bangalore", 2), ("bengaluru", 2),
    ("hyderabad", 2), ("kerala", 1), ("coimbatore", 1), ("madurai", 1),
    ("srm", 3), ("srm university", 3), ("anna university", 3),
    ("vit", 2), ("iit madras", 3), ("iit hyderabad", 2),
    ("iiit hyderabad", 2), ("nit trichy", 2), ("nit surathkal", 2),
    ("bits pilani", 2), ("psg tech", 2),
    # Indian tech companies (hiring signals)
    ("infosys hiring", 3), ("tcs hiring", 3), ("wipro hiring", 3),
    ("zoho", 2), ("freshworks", 2), ("chargebee", 2), ("swiggy", 2),
    ("flipkart", 2), ("razorpay", 2), ("cred", 2),
    ("india tech", 2), ("startup india", 2), ("make in india", 2),
]

COMMON_NEGATIVE_KEYWORDS = [
    # Reduce false positives from non-engineering content
    "cricket", "bollywood", "movie review", "film", "ipl",
    "political party", "election rally", "astrology", "horoscope",
]

# Minimum score to assign an article to a department
RELEVANCE_THRESHOLD = 3
MULTI_DEPT_RELATIVE_THRESHOLD = 0.75
COMMON_SIGNAL_CAP = 3

# Shared/general source types that publish cross-department content
GENERAL_SOURCE_TYPES = {
    "india-news", "india-education", "india-policy", "india-career",
    "india-industry", "india-startup", "india-tech",
    "community", "news", "blog",
}


def _tokenize(text: str) -> str:
    """Lowercase and normalize text for matching."""
    return text.lower()


def _keyword_present(text: str, keyword: str) -> bool:
    """Check keyword presence with boundary logic for single alphanumeric tokens."""
    if keyword.isalnum():
        return bool(re.search(r"\b" + re.escape(keyword) + r"\b", text))
    return keyword in text


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

    # Common student-career signals should not assign departments on their own.
    common_signal_hits = sum(1 for keyword, _ in COMMON_CAREER_KEYWORDS if _keyword_present(text, keyword))
    common_signal_bonus = min(COMMON_SIGNAL_CAP, common_signal_hits)

    results = []
    for dept, profile in DEPARTMENT_PROFILES.items():
        # Department assignment must be driven by department-specific signals.
        dept_keywords = profile["keywords"]
        all_negatives = profile.get("negative", []) + COMMON_NEGATIVE_KEYWORDS

        # Check negative keywords first
        neg_count = sum(1 for neg in all_negatives if neg in text)
        if neg_count >= 2:
            continue  # strong negative signal, skip this dept

        # Score department-specific keywords only.
        score = 0
        specific_matches = 0
        for keyword, weight in dept_keywords:
            if _keyword_present(text, keyword):
                score += weight
                specific_matches += 1

        # Bonus if source is explicitly tagged for this dept (and not a general source)
        if source_dept_tags and dept in source_dept_tags:
            if source_type not in GENERAL_SOURCE_TYPES:
                score += 3  # source tagging bonus for specific sources
                specific_matches = max(specific_matches, 1)
            else:
                # For general/news sources, a mild tag lift helps low-volume departments
                # without allowing tags to assign departments alone.
                score += 1

        # Career/event/South India source type bonuses
        india_career_types = {"india-career", "india-events", "india-south", "india-research"}
        if source_type in india_career_types and specific_matches > 0:
            score += 1

        # Apply limited common signal bonus only after dept-specific evidence exists.
        if specific_matches > 0:
            score += common_signal_bonus

        if score >= RELEVANCE_THRESHOLD and specific_matches >= 1:
            results.append((dept, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def assign_departments(
    title: str,
    content: str,
    source_dept_tags: List[str] = None,
    source_type: str = "",
    max_depts: int = 2,
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

    # Keep secondary tags only when they are very close to the top score.
    best_score = scored[0][1]
    threshold = best_score * MULTI_DEPT_RELATIVE_THRESHOLD
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
        "ai", "ml", "neural net", "transformer", "diffusion",
        "gemini", "claude", "copilot",
        "language model", "vision model", "embedding", "agent",
        "multimodal", "image generation", "text-to-image", "model training",
        "inference", "benchmark", "prompt", "xai", "grok",
    ],
    "security": [
        "cybersecurity", "cyber security", "vulnerability", "exploit",
        "malware", "ransomware", "data breach", "zero-day", "cve",
        "hacking", "phishing", "ddos", "firewall", "encryption",
        "hack", "cyber", "intrusion detection", "threat",
    ],
    "webdev": [
        "web development", "javascript", "typescript", "react",
        "angular", "vue.js", "svelte", "css", "html", "frontend",
        "next.js", "nuxt", "tailwind", "webpack", "vite",
        "vue", "nextjs", "web app", "blazor", "webassembly", "wasm",
        "browser", "dom",
    ],
    "backend": [
        "backend", "server-side", "fastapi", "django", "flask",
        "spring boot", "node.js", "express.js", "graphql",
        "microservice", "rest api",
        "python", "java", "golang", "rust", "node", "nodejs",
        "api", "database", "sql", "redis", "postgresql", "mongodb",
        "mysql", "c++", "gitops", "argo cd", "asp.net",
    ],
    "mobile": [
        "android", "ios", "flutter", "react native", "swift",
        "kotlin", "mobile app", "mobile development",
        "smartphone", "iphone", "ipad", "samsung galaxy", "pixel",
        "xiaomi", "oneplus", "nothing phone", "mobile phone",
    ],
    "devops": [
        "devops", "docker", "kubernetes", "ci/cd", "terraform",
        "ansible", "jenkins", "github actions", "aws", "azure",
        "gcp", "cloud computing", "infrastructure",
        "k8s", "cloud", "serverless", "saas", "data center",
        "vmware", "sre",
    ],
    "career": [
        "campus placement", "placement drive", "job opening", "walk-in interview",
        "off campus", "on campus hiring", "fresher job", "entry level",
        "internship opportunity", "summer internship", "winter internship",
        "hiring drive", "recruitment drive", "pool campus",
        "career opportunity", "job fair", "career fair",
        "hiring", "placement", "internship", "recruiter", "recruitment",
        "resume", "fresher", "freshers", "vacancy", "vacancies",
        "ctc", "lpa", "salary", "package", "shortlist", "walk-in",
        "openings", "positions",
        "interview", "career", "job market",
        "job", "layoff", "recruit", "headcount", "workforce",
        "employee", "leadership", "workplace", "talent",
    ],
    "opportunity": [
        "hackathon", "coding contest", "programming competition",
        "scholarship program", "fellowship program", "research grant",
        "coding challenge", "innovation challenge",
        "smart india hackathon", "topcoder", "codeforces",
        "google summer of code", "gsoc", "mlh fellowship",
        "gate exam", "gate preparation", "nptel course",
        "workshop registration", "certification program",
        "competition", "scholarship", "fellowship",
        "bootcamp", "workshop", "webinar", "certificate",
        "challenge", "olympiad", "contest",
    ],
    "startup": [
        "startup", "funding round", "venture capital", "series a",
        "series b", "ipo", "unicorn", "entrepreneur", "founded",
        "seed funding", "angel investor",
        "funding", "vc", "valuation", "seed round", "acquisition",
        "techcrunch", "disrupt", "polymarket", "fintech",
    ],
    "research": [
        "research paper", "arxiv", "ieee", "acm", "journal",
        "conference paper", "peer-reviewed", "citation",
        "preprint", "publication",
        "researcher", "scientist", "study finds", "study reveals",
        "fossil", "archaeolog", "paleontolog", "physicist",
        "discovery", "experiment",
    ],
    "electronics": [
        "semiconductor", "chip", "vlsi", "fpga", "microcontroller",
        "pcb", "circuit", "transistor", "embedded", "iot",
        "processor", "sensor", "rfid", "mipi", "5g", "6g",
        "telecom", "spectrum", "wireless", "antenna",
    ],
    "robotics": [
        "robot", "robotics", "automation", "autonomous", "drone",
        "plc", "scada", "manipulator", "humanoid",
        "lidar", "actuator", "ros", "gazebo", "blender",
    ],
    "energy": [
        "renewable energy", "solar", "wind energy", "battery",
        "electric vehicle", "power grid", "smart grid",
        "wind", "ev", "renewable", "hydrogen", "nuclear", "grid",
        "electricity", "power plant", "coal", "oil supply",
        "energy security", "gasification", "refinery", "petroleum",
        "ntpc", "charging station", "sodium-ion",
    ],
    "biotech": [
        "biotechnology", "genetic", "crispr", "dna", "genome",
        "pharmaceutical", "drug discovery", "vaccine",
        "gene", "protein", "rna", "pharma", "clinical trial",
        "biomedical", "fda", "drug", "therapy", "oncology",
        "cancer", "immunology", "biosafety",
    ],
    "aerospace": [
        "aerospace", "aviation", "aircraft", "airplane", "satellite",
        "space", "isro", "nasa", "spacex", "rocket", "launch vehicle",
        "orbit", "lunar", "mars", "astronaut", "starship",
        "fighter jet", "stealth", "missile", "air force", "iaf",
        "hal", "rafale", "drdo", "defence", "defense",
        "airspace", "flight cancell",
    ],
    "automotive": [
        "automobile", "automotive", "car sales", "suv", "sedan",
        "vehicle sales", "ev sales", "electric car",
        "maruti", "hyundai", "tata motors", "mahindra",
        "mercedes", "bmw", "audi", "toyota", "honda",
        "ducati", "triumph", "hero", "bajaj", "motorcycle",
        "ebike", "scooter",
    ],
    "gadgets": [
        "gadget", "wearable", "smartwatch", "headphone", "earbuds",
        "projector", "printer", "camera", "speaker", "display",
        "tablet", "laptop", "macbook", "apple watch", "airpods",
        "lego", "kickstarter",
    ],
    "healthcare": [
        "health care", "healthcare", "hospital", "medical device",
        "patient", "diagnosis", "clinical", "telemedicine",
        "surgery", "physician", "dermatology", "pathology",
        "disease", "disorder", "treatment", "symptom",
        "geriatric", "abortion", "snakebite", "disability",
    ],
    "education": [
        "education", "university", "college", "campus", "exam",
        "admission", "scholarship", "neet", "cbse", "cuet",
        "ignou", "registration", "classroom", "curriculum",
        "student", "teacher", "learning environment",
    ],
}


def detect_category(title: str, content: str) -> str:
    """Detect content category using phrase and keyword matching.

    Uses word boundary matching for short keywords (<=3 chars) to avoid
    false positives (e.g. "ai" matching inside "maintain").
    """
    text = _tokenize(f"{title} {content}")

    scores = {}
    for cat, phrases in CATEGORY_KEYWORDS.items():
        score = 0
        for phrase in phrases:
            if len(phrase) <= 3:
                if re.search(r'\b' + re.escape(phrase) + r'\b', text):
                    score += 1
            elif phrase in text:
                score += 1
        if score > 0:
            scores[cat] = score

    if scores:
        return max(scores, key=scores.get)

    # Broad fallback before returning "general"
    if any(term in text for term in [
        'code', 'program', 'software', 'developer', 'coding',
        'github', 'stack overflow', 'open source', 'terminal',
    ]):
        return 'backend'
    if any(term in text for term in [
        'research', 'study', 'paper', 'journal', 'conference',
        'ieee', 'acm', 'scientists', 'laboratory',
    ]):
        return 'research'
    if any(term in text for term in [
        'launch', 'spacecraft', 'orbit', 'astronaut', 'airspace',
    ]):
        return 'aerospace'
    if any(term in text for term in [
        'power', 'fuel', 'mining', 'crude oil', 'natural gas',
    ]):
        return 'energy'
        return 'research'

    return "general"
