"""Department registry with curated source lists for each engineering department."""

from typing import Dict, List, Any


# ---------------------------------------------------------------------------
# Top 10 Engineering Departments (South Indian colleges)
# ---------------------------------------------------------------------------

DEPARTMENTS: List[Dict[str, Any]] = [
    {
        "key": "CSE",
        "name": "Computer Science & Engineering",
        "icon": "laptop-code",
        "description": "Software development, algorithms, systems programming, and core CS theory.",
    },
    {
        "key": "IT",
        "name": "Information Technology",
        "icon": "server",
        "description": "IT infrastructure, networking, cybersecurity, cloud computing, and DevOps.",
    },
    {
        "key": "AIDS",
        "name": "Artificial Intelligence & Data Science",
        "icon": "brain",
        "description": "Machine learning, deep learning, NLP, computer vision, and data analytics.",
    },
    {
        "key": "ECE",
        "name": "Electronics & Communication Engineering",
        "icon": "microchip",
        "description": "Embedded systems, VLSI, signal processing, IoT, and telecommunications.",
    },
    {
        "key": "EEE",
        "name": "Electrical & Electronics Engineering",
        "icon": "bolt",
        "description": "Power systems, renewable energy, control systems, and electrical machines.",
    },
    {
        "key": "ME",
        "name": "Mechanical Engineering",
        "icon": "gears",
        "description": "Thermodynamics, manufacturing, CAD/CAM, robotics, and automotive engineering.",
    },
    {
        "key": "CE",
        "name": "Civil Engineering",
        "icon": "building",
        "description": "Structural, geotechnical, transportation, environmental, and construction engineering.",
    },
    {
        "key": "BT",
        "name": "Biotechnology Engineering",
        "icon": "dna",
        "description": "Genetic engineering, bioinformatics, pharmaceuticals, and molecular biology.",
    },
    {
        "key": "CH",
        "name": "Chemical Engineering",
        "icon": "flask",
        "description": "Process engineering, petrochemicals, polymers, and industrial chemistry.",
    },
    {
        "key": "AE",
        "name": "Aeronautical / Aerospace Engineering",
        "icon": "plane",
        "description": "Aerodynamics, propulsion, avionics, space systems, and flight mechanics.",
    },
]

# Quick lookup helpers
DEPARTMENT_KEYS: List[str] = [d["key"] for d in DEPARTMENTS]
DEPARTMENT_BY_KEY: Dict[str, Dict] = {d["key"]: d for d in DEPARTMENTS}


# ---------------------------------------------------------------------------
# Per-department source mappings
# ---------------------------------------------------------------------------

DEPARTMENT_SOURCES: Dict[str, Dict[str, Any]] = {
    # ── CSE ────────────────────────────────────────────────────────────────
    "CSE": {
        "reddit": [
            "programming", "compsci", "Python", "javascript", "golang",
            "rust", "cpp", "java", "webdev", "netsec", "learnprogramming",
            "cscareerquestions", "csMajors", "coding", "softwaredevelopment",
        ],
        "medium": [
            "better-programming", "free-code-camp", "hackernoon",
            "gitconnected", "javascript-in-plain-english",
            "python-in-plain-english", "swlh", "geekculture",
        ],
        "youtube": [
            "Fireship", "TraversyMedia", "cs50", "freecodecamp",
            "NeetCode", "TheCodingTrain", "TechWithTim", "ThePrimeagen",
        ],
        "rss": [
            {"name": "Hacker News", "url": "https://hnrss.org/frontpage", "type": "news"},
            {"name": "TechCrunch", "url": "https://techcrunch.com/feed/", "type": "news"},
            {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/technology-lab", "type": "news"},
            {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml", "type": "news"},
            {"name": "InfoQ", "url": "https://feed.infoq.com/", "type": "news"},
            {"name": "Dev.to", "url": "https://dev.to/feed", "type": "blog"},
            {"name": "ACM TechNews", "url": "https://technews.acm.org/rss.xml", "type": "academic"},
            {"name": "ArXiv CS", "url": "https://rss.arxiv.org/rss/cs", "type": "academic"},
            {"name": "Google AI Blog", "url": "https://blog.research.google/feeds/posts/default?alt=rss", "type": "industry"},
            {"name": "Microsoft Research", "url": "https://www.microsoft.com/en-us/research/feed/", "type": "industry"},
        ],
        "github_languages": ["python", "javascript", "typescript", "go", "rust", "java"],
    },

    # ── IT ─────────────────────────────────────────────────────────────────
    "IT": {
        "reddit": [
            "ITCareerQuestions", "sysadmin", "networking", "cybersecurity",
            "devops", "aws", "azure", "googlecloud", "docker",
            "kubernetes", "linux", "selfhosted", "datascience",
        ],
        "medium": [
            "better-programming", "towards-data-science",
            "aws-in-plain-english", "geekculture",
        ],
        "youtube": [
            "NetworkChuck", "davidbombal", "TechWorldwithNana",
            "KodeKloud", "IBMTechnology",
        ],
        "rss": [
            {"name": "The Register", "url": "https://www.theregister.com/headlines.atom", "type": "news"},
            {"name": "ZDNet", "url": "https://www.zdnet.com/news/rss.xml", "type": "news"},
            {"name": "Bleeping Computer", "url": "https://www.bleepingcomputer.com/feed/", "type": "news"},
            {"name": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/", "type": "blog"},
            {"name": "Dark Reading", "url": "https://www.darkreading.com/rss.xml", "type": "news"},
            {"name": "AWS Blog", "url": "https://aws.amazon.com/blogs/aws/feed/", "type": "industry"},
            {"name": "Google Cloud Blog", "url": "https://cloud.google.com/blog/rss", "type": "industry"},
            {"name": "NIST News", "url": "https://www.nist.gov/news-events/news/rss.xml", "type": "academic"},
        ],
        "github_languages": ["python", "go", "shell", "typescript"],
    },

    # ── AI & DS ────────────────────────────────────────────────────────────
    "AIDS": {
        "reddit": [
            "MachineLearning", "artificial", "deeplearning", "datascience",
            "LocalLLaMA", "LanguageTechnology", "computervision",
            "reinforcementlearning", "MLOps", "statistics",
            "learnmachinelearning",
        ],
        "medium": [
            "towards-data-science", "towards-artificial-intelligence",
            "analytics-vidhya", "mlearning-ai",
        ],
        "youtube": [
            "3blue1brown", "TwoMinutePapers", "Sentdex", "joshstarmer",
            "YannicKilcher", "AIExplained-official",
        ],
        "rss": [
            {"name": "MIT Tech Review AI", "url": "https://www.technologyreview.com/feed/", "type": "news"},
            {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "type": "news"},
            {"name": "ArXiv AI", "url": "https://rss.arxiv.org/rss/cs.AI", "type": "academic"},
            {"name": "ArXiv ML", "url": "https://rss.arxiv.org/rss/cs.LG", "type": "academic"},
            {"name": "ArXiv CV", "url": "https://rss.arxiv.org/rss/cs.CV", "type": "academic"},
            {"name": "ArXiv NLP", "url": "https://rss.arxiv.org/rss/cs.CL", "type": "academic"},
            {"name": "Google AI Blog", "url": "https://blog.research.google/feeds/posts/default?alt=rss", "type": "industry"},
            {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "type": "industry"},
            {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml", "type": "industry"},
            {"name": "Papers With Code", "url": "https://paperswithcode.com/latest", "type": "academic"},
        ],
        "github_languages": ["python", "jupyter-notebook"],
    },

    # ── ECE ─────────────────────────────────────────────────────────────────
    "ECE": {
        "reddit": [
            "ECE", "electronics", "embedded", "FPGA", "arduino",
            "raspberry_pi", "AskElectronics", "signals", "DSP",
            "rfelectronics", "hamradio", "PCB",
        ],
        "medium": [
            "geekculture",
        ],
        "youtube": [
            "BenEater", "greatscottlab", "EEVblog", "PhilsLab",
            "RobertFeranec", "AndreasSpiess", "ElectroBOOM",
        ],
        "rss": [
            {"name": "IEEE Spectrum", "url": "https://spectrum.ieee.org/feeds/feed.rss", "type": "academic"},
            {"name": "EE Times", "url": "https://www.eetimes.com/feed/", "type": "news"},
            {"name": "Embedded.com", "url": "https://www.embedded.com/feed/", "type": "news"},
            {"name": "Hackaday", "url": "https://hackaday.com/feed/", "type": "blog"},
            {"name": "All About Circuits", "url": "https://www.allaboutcircuits.com/feeds/", "type": "blog"},
            {"name": "ArXiv Signal Processing", "url": "https://rss.arxiv.org/rss/eess.SP", "type": "academic"},
            {"name": "ArXiv Systems", "url": "https://rss.arxiv.org/rss/eess.SY", "type": "academic"},
            {"name": "Analog Devices Blog", "url": "https://www.analog.com/en/lp/001/rss.xml", "type": "industry"},
        ],
        "github_languages": ["c", "cpp", "verilog", "python"],
    },

    # ── EEE ─────────────────────────────────────────────────────────────────
    "EEE": {
        "reddit": [
            "electricalengineering", "ECE", "powerelectronics",
            "renewable", "solar", "energy", "engineering", "robotics",
        ],
        "medium": [],
        "youtube": [
            "ElectroBOOM", "greatscottlab", "EEVblog",
            "TheEngineeringMindset", "Lesics", "RealEngineering",
        ],
        "rss": [
            {"name": "IEEE Spectrum", "url": "https://spectrum.ieee.org/feeds/feed.rss", "type": "academic"},
            {"name": "Renewable Energy World", "url": "https://www.renewableenergyworld.com/feed/", "type": "news"},
            {"name": "Utility Dive", "url": "https://www.utilitydive.com/feeds/news/", "type": "news"},
            {"name": "ArXiv Systems", "url": "https://rss.arxiv.org/rss/eess.SY", "type": "academic"},
            {"name": "IEA News", "url": "https://www.iea.org/rss/news.xml", "type": "industry"},
        ],
        "github_languages": ["python", "matlab"],
    },

    # ── ME ──────────────────────────────────────────────────────────────────
    "ME": {
        "reddit": [
            "MechanicalEngineering", "engineering", "manufacturing",
            "3Dprinting", "CAD", "SolidWorks", "Fusion360",
            "robotics", "automotive", "aerospace",
        ],
        "medium": [],
        "youtube": [
            "Lesics", "RealEngineering", "PracticalEngineeringChannel",
            "StuffMadeHere", "MarkRober", "BranchEducation",
            "EngineeringExplained",
        ],
        "rss": [
            {"name": "Engineering.com", "url": "https://www.engineering.com/feed", "type": "news"},
            {"name": "Machine Design", "url": "https://www.machinedesign.com/rss", "type": "news"},
            {"name": "Design News", "url": "https://www.designnews.com/rss.xml", "type": "news"},
            {"name": "SAE International", "url": "https://www.sae.org/rss/news", "type": "academic"},
            {"name": "New Atlas", "url": "https://newatlas.com/index.rss", "type": "news"},
            {"name": "3D Printing Industry", "url": "https://3dprintingindustry.com/feed/", "type": "news"},
            {"name": "ArXiv Fluid Dynamics", "url": "https://rss.arxiv.org/rss/physics.flu-dyn", "type": "academic"},
        ],
        "github_languages": ["python", "cpp"],
    },

    # ── CE ──────────────────────────────────────────────────────────────────
    "CE": {
        "reddit": [
            "civilengineering", "StructuralEngineering", "Construction",
            "Surveying", "urbanplanning", "Geotechnical",
            "infrastructure", "water", "environmental_science",
        ],
        "medium": [],
        "youtube": [
            "PracticalEngineeringChannel", "RealEngineering", "TheB1M",
        ],
        "rss": [
            {"name": "Construction Dive", "url": "https://www.constructiondive.com/feeds/news/", "type": "news"},
            {"name": "The B1M", "url": "https://www.theb1m.com/rss", "type": "news"},
            {"name": "Smart Cities Dive", "url": "https://www.smartcitiesdive.com/feeds/news/", "type": "news"},
            {"name": "ArXiv Geophysics", "url": "https://rss.arxiv.org/rss/physics.geo-ph", "type": "academic"},
            {"name": "ASCE News", "url": "https://news.asce.org/feed/", "type": "academic"},
        ],
        "github_languages": ["python"],
    },

    # ── BT ──────────────────────────────────────────────────────────────────
    "BT": {
        "reddit": [
            "biotech", "biology", "bioinformatics", "genetics",
            "microbiology", "labrats", "pharma", "Biochemistry",
            "molecularbiology", "genomics",
        ],
        "medium": [
            "towards-data-science",
        ],
        "youtube": [
            "inanutshell", "ProfessorDaveExplains", "NinjaNerdOfficial",
            "iBiology",
        ],
        "rss": [
            {"name": "GEN News", "url": "https://www.genengnews.com/feed/", "type": "news"},
            {"name": "STAT News", "url": "https://www.statnews.com/feed/", "type": "news"},
            {"name": "Fierce Biotech", "url": "https://www.fiercebiotech.com/rss/xml", "type": "news"},
            {"name": "Science Daily Biotech", "url": "https://www.sciencedaily.com/rss/top/science/biotech.xml", "type": "news"},
            {"name": "ArXiv Quantitative Biology", "url": "https://rss.arxiv.org/rss/q-bio", "type": "academic"},
            {"name": "BioPharma Dive", "url": "https://www.biopharmadive.com/feeds/news/", "type": "industry"},
            {"name": "Labiotech.eu", "url": "https://www.labiotech.eu/feed/", "type": "news"},
        ],
        "github_languages": ["python", "r"],
    },

    # ── CH ──────────────────────────────────────────────────────────────────
    "CH": {
        "reddit": [
            "ChemicalEngineering", "chemistry", "Petrochemicals",
            "polymers", "materials", "energy", "pharma",
        ],
        "medium": [],
        "youtube": [
            "LearnChemE", "RealEngineering", "NileRed",
            "periodicvideos",
        ],
        "rss": [
            {"name": "C&EN News", "url": "https://cen.acs.org/rss/feed.html", "type": "news"},
            {"name": "The Chemical Engineer", "url": "https://www.thechemicalengineer.com/feed/", "type": "news"},
            {"name": "ArXiv Chemical Physics", "url": "https://rss.arxiv.org/rss/physics.chem-ph", "type": "academic"},
            {"name": "Hydrocarbon Processing", "url": "https://www.hydrocarbonprocessing.com/rss", "type": "industry"},
        ],
        "github_languages": ["python", "matlab"],
    },

    # ── AE ──────────────────────────────────────────────────────────────────
    "AE": {
        "reddit": [
            "aerospace", "spacex", "aviation", "flying",
            "AerospaceEngineering", "space", "rocketry",
            "satellites", "defense",
        ],
        "medium": [],
        "youtube": [
            "EverydayAstronaut", "scottmanley", "RealEngineering",
            "Wendoverproductions", "MustardChannel", "MentourPilot",
        ],
        "rss": [
            {"name": "SpaceNews", "url": "https://spacenews.com/feed/", "type": "news"},
            {"name": "NASA Spaceflight", "url": "https://www.nasaspaceflight.com/feed/", "type": "news"},
            {"name": "Ars Technica Space", "url": "https://feeds.arstechnica.com/arstechnica/science", "type": "news"},
            {"name": "FlightGlobal", "url": "https://www.flightglobal.com/rss", "type": "news"},
            {"name": "ArXiv Astrophysics", "url": "https://rss.arxiv.org/rss/astro-ph", "type": "academic"},
            {"name": "ArXiv Space Physics", "url": "https://rss.arxiv.org/rss/physics.space-ph", "type": "academic"},
            {"name": "NASA Blog", "url": "https://www.nasa.gov/feed/", "type": "industry"},
            {"name": "ISRO News", "url": "https://www.isro.gov.in/rss-feeds.xml", "type": "industry"},
            {"name": "Space.com", "url": "https://www.space.com/feeds/all", "type": "news"},
        ],
        "github_languages": ["python", "cpp", "matlab"],
    },
}


def get_all_reddit_subs_for_department(dept_key: str) -> List[str]:
    """Return the Reddit subreddit list for a department."""
    return DEPARTMENT_SOURCES.get(dept_key, {}).get("reddit", [])


def get_all_rss_feeds_for_department(dept_key: str) -> List[Dict]:
    """Return the RSS feed list for a department."""
    return DEPARTMENT_SOURCES.get(dept_key, {}).get("rss", [])


def get_department_tag(dept_key: str) -> str:
    """Return the canonical tag string used in department_tags arrays."""
    return dept_key
