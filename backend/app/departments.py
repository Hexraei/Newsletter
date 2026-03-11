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
    {
        "key": "RAE",
        "name": "Robotics & Automation Engineering",
        "icon": "robot",
        "description": "Industrial robots, autonomous systems, ROS, control theory, machine vision, and smart manufacturing.",
    },
    {
        "key": "PT",
        "name": "Production Technology",
        "icon": "industry",
        "description": "CNC machining, lean manufacturing, Industry 4.0, quality control, additive manufacturing, and process optimization.",
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
            "ISRO",
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

    # ── RAE ─────────────────────────────────────────────────────────────────
    "RAE": {
        "reddit": [
            "robotics", "ROS", "SelfDrivingCars", "automation",
            "ControlTheory", "PLC", "industrial_automation",
            "ArtificialIntelligence", "MachineLearning",
        ],
        "medium": [
            "towards-data-science", "geekculture",
        ],
        "youtube": [
            "BostonDynamics", "Veritasium", "RealEngineering",
            "Lesics", "StuffMadeHere", "MarkRober",
        ],
        "rss": [
            # Global news / industry
            {"name": "The Robot Report", "url": "https://www.therobotreport.com/feed/", "type": "news"},
            {"name": "TechCrunch Robotics", "url": "https://techcrunch.com/category/robotics/feed/", "type": "news"},
            {"name": "New Atlas Robotics", "url": "https://newatlas.com/robotics/index.rss", "type": "news"},
            {"name": "Robotics Business Review", "url": "https://www.roboticsbusinessreview.com/feed/", "type": "news"},
            {"name": "IEEE Spectrum", "url": "https://spectrum.ieee.org/feeds/feed.rss", "type": "academic"},
            {"name": "Hackaday", "url": "https://hackaday.com/feed/", "type": "blog"},
            # Major company newsrooms — product launches, job openings, workshops
            {"name": "Boston Dynamics Blog", "url": "https://bostondynamics.com/blog/feed/", "type": "industry"},
            {"name": "ABB Robotics News", "url": "https://new.abb.com/news/rss?category=robotics", "type": "industry"},
            {"name": "Universal Robots Blog", "url": "https://www.universal-robots.com/blog/feed/", "type": "industry"},
            {"name": "ROS Discourse", "url": "https://discourse.ros.org/latest.rss", "type": "community"},
            {"name": "NVIDIA Robotics Blog", "url": "https://developer.nvidia.com/blog/feed/", "type": "industry"},
            {"name": "Siemens Digital Industries", "url": "https://blogs.sw.siemens.com/feed/", "type": "industry"},
            {"name": "FANUC News", "url": "https://www.fanucamerica.com/news-events/feed/rss", "type": "industry"},
            {"name": "KUKA News", "url": "https://www.kuka.com/en-de/press/news/feed.rss", "type": "industry"},
            # Research papers
            {"name": "ArXiv Robotics", "url": "https://rss.arxiv.org/rss/cs.RO", "type": "academic"},
            {"name": "ArXiv Systems & Control", "url": "https://rss.arxiv.org/rss/eess.SY", "type": "academic"},
            {"name": "ArXiv Human-Robot Interaction", "url": "https://rss.arxiv.org/rss/cs.HC", "type": "academic"},
            {"name": "Science Robotics", "url": "https://www.science.org/action/showFeed?type=etoc&feed=rss&jc=scirobotics", "type": "academic"},
        ],
        "github_languages": ["python", "cpp", "ros"],
    },

    # ── PT ──────────────────────────────────────────────────────────────────
    "PT": {
        "reddit": [
            "manufacturing", "Machinists", "PLC", "CNC", "3Dprinting",
            "leanmanufacturing", "qualitycontrol", "industrialengineering",
            "toolmakers", "OSHA", "MechanicalEngineering",
        ],
        "medium": [],
        "youtube": [
            "Lesics", "RealEngineering", "StuffMadeHere",
            "PracticalEngineeringChannel", "FusionManufacturing",
        ],
        "rss": [
            # Global news / industry
            {"name": "Modern Machine Shop", "url": "https://www.mmsonline.com/rss/all", "type": "news"},
            {"name": "Machine Design", "url": "https://www.machinedesign.com/rss", "type": "news"},
            {"name": "Production Machining", "url": "https://www.productionmachining.com/rss/all", "type": "news"},
            {"name": "Control Engineering", "url": "https://www.controleng.com/rss/all", "type": "news"},
            {"name": "Industry Week", "url": "https://www.industryweek.com/rss/all", "type": "news"},
            {"name": "Automation World", "url": "https://www.automationworld.com/rss/all", "type": "news"},
            {"name": "Quality Magazine", "url": "https://www.qualitymag.com/rss/all", "type": "news"},
            {"name": "3D Printing Industry", "url": "https://3dprintingindustry.com/feed/", "type": "news"},
            {"name": "Engineering.com", "url": "https://www.engineering.com/feed", "type": "news"},
            # Major company newsrooms — product launches, CNC, workshops
            {"name": "Siemens Manufacturing Blog", "url": "https://blogs.sw.siemens.com/feed/", "type": "industry"},
            {"name": "Bosch Stories", "url": "https://www.bosch.com/stories/rss/", "type": "industry"},
            {"name": "Rockwell Automation Blog", "url": "https://www.rockwellautomation.com/en-us/company/news/blog/feed.rss", "type": "industry"},
            {"name": "Haas Automation News", "url": "https://www.haascnc.com/news.rss.xml", "type": "industry"},
            {"name": "Autodesk Manufacturing Blog", "url": "https://www.autodesk.com/blogs/manufacturing/feed/", "type": "industry"},
            {"name": "Stratasys Blog", "url": "https://www.stratasys.com/en/blog/feed/", "type": "industry"},
            {"name": "SAE International", "url": "https://www.sae.org/rss/news", "type": "academic"},
            {"name": "Lean.org", "url": "https://www.lean.org/feed/", "type": "blog"},
            # Research papers
            {"name": "ArXiv Materials Science", "url": "https://rss.arxiv.org/rss/cond-mat.mtrl-sci", "type": "academic"},
            {"name": "ArXiv Applied Physics", "url": "https://rss.arxiv.org/rss/physics.app-ph", "type": "academic"},
            {"name": "Journal of Manufacturing Systems", "url": "https://rss.sciencedirect.com/publication/science/02786125", "type": "academic"},
            {"name": "CIRP Annals", "url": "https://rss.sciencedirect.com/publication/science/00078506", "type": "academic"},
            {"name": "ArXiv Systems & Control", "url": "https://rss.arxiv.org/rss/eess.SY", "type": "academic"},
        ],
        "github_languages": ["python", "cpp", "matlab"],
    },
}


# ── INDIA-FOCUSED SOURCES──────────────────────────────────────────────
# These are appended to every department so students get Indian industry,
# career, and education signals alongside international sources.

# Sources shared across ALL departments
INDIA_COMMON_RSS: List[Dict[str, str]] = [
    # ─ Major Indian news (tech / business / education sections) ─
    {"name": "Times of India Tech", "url": "https://timesofindia.indiatimes.com/rssfeeds/66949542.cms", "type": "india-news"},
    {"name": "TOI Education", "url": "https://timesofindia.indiatimes.com/rssfeeds/913168846.cms", "type": "india-education"},
    {"name": "The Hindu Sci-Tech", "url": "https://www.thehindu.com/sci-tech/feeder/default.rss", "type": "india-news"},
    {"name": "The Hindu Education", "url": "https://www.thehindu.com/education/feeder/default.rss", "type": "india-education"},
    {"name": "NDTV Gadgets", "url": "https://feeds.feedburner.com/ndtvgadgets-latest", "type": "india-news"},
    {"name": "Indian Express Technology", "url": "https://indianexpress.com/section/technology/feed/", "type": "india-news"},
    {"name": "Hindustan Times Tech", "url": "https://www.hindustantimes.com/feeds/rss/technology/rssfeed.xml", "type": "india-news"},
    {"name": "Livemint Technology", "url": "https://www.livemint.com/rss/technology", "type": "india-news"},
    {"name": "Economic Times Tech", "url": "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms", "type": "india-news"},
    # ─ Indian startup / tech ecosystem ─
    {"name": "YourStory", "url": "https://yourstory.com/feed", "type": "india-startup"},
    {"name": "Inc42", "url": "https://inc42.com/feed/", "type": "india-startup"},
    # ─ New verified Indian sources ─
    {"name": "The Wire Science", "url": "https://science.thewire.in/feed/", "type": "india-news"},
    {"name": "News18 Tech", "url": "https://www.news18.com/rss/tech.xml", "type": "india-news"},
    {"name": "Moneycontrol Tech", "url": "https://www.moneycontrol.com/rss/technology.xml", "type": "india-news"},
    {"name": "MediaNama", "url": "https://www.medianama.com/feed/", "type": "india-tech"},
    # ─ Indian govt / STEM policy ─
    {"name": "PIB India", "url": "https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3", "type": "india-policy"},
    {"name": "ET Govt", "url": "https://government.economictimes.indiatimes.com/rss/topstories", "type": "india-policy"},
    # ─ South India tech ecosystem ─
    {"name": "The News Minute Tech", "url": "https://www.thenewsminute.com/topic/technology/feed", "type": "india-south"},
    {"name": "Citizen Matters Bengaluru", "url": "https://citizenmatters.in/bengaluru/feed", "type": "india-south"},
    {"name": "Citizen Matters Chennai", "url": "https://citizenmatters.in/chennai/feed", "type": "india-south"},
    {"name": "The Hindu Business Line Tech", "url": "https://www.thehindubusinessline.com/info-tech/feeder/default.rss", "type": "india-south"},
    # ─ Jobs, placements, career ─
    {"name": "Freshersworld Blog", "url": "https://www.freshersworld.com/jobs/blog/feed", "type": "india-career"},
    {"name": "Internshala Blog", "url": "https://blog.internshala.com/feed/", "type": "india-career"},
    {"name": "GeeksforGeeks Jobs", "url": "https://www.geeksforgeeks.org/feed/", "type": "india-career"},
    {"name": "Naukri Blog", "url": "https://www.naukri.com/blog/feed/", "type": "india-career"},
    # ─ Indian research & innovation ─
    {"name": "DST India", "url": "https://dst.gov.in/rss/latest-news/rss.xml", "type": "india-research"},
    {"name": "CSIR News", "url": "https://www.csir.res.in/rss.xml", "type": "india-research"},
    {"name": "IIT Madras News", "url": "https://www.iitm.ac.in/feed", "type": "india-research"},
    {"name": "Vigyan Prasar", "url": "https://vigyanprasar.gov.in/feed/", "type": "india-research"},
    # ─ Hackathons, competitions, opportunities ─
    {"name": "Devfolio Blog", "url": "https://blog.devfolio.co/rss/", "type": "india-events"},
    {"name": "Unstop Blog", "url": "https://unstop.com/blog/feed", "type": "india-events"},
    {"name": "NPTEL Announcements", "url": "https://nptel.ac.in/rss/new_courses.xml", "type": "india-events"},
]

# India-specific Reddit subs shared across departments
INDIA_COMMON_REDDIT: List[str] = [
    "india", "Indian_Academia", "developersIndia", "Btechtards",
    "Indian_Startups", "chennai", "TamilNadu",
    "Indian_Jobs", "GATE", "gradadmissions",
    "IndianGaming",
]

# Department-specific Indian sources (only added to matching department)
INDIA_DEPT_RSS: Dict[str, List[Dict[str, str]]] = {
    "CSE": [
        {"name": "Trak.in", "url": "https://trak.in/feed/", "type": "india-startup"},
        {"name": "ET CIO", "url": "https://cio.economictimes.indiatimes.com/rss/topstories", "type": "india-industry"},
        {"name": "GeeksforGeeks", "url": "https://www.geeksforgeeks.org/feed/", "type": "india-career"},
    ],
    "IT": [
        {"name": "ETTelecom", "url": "https://telecom.economictimes.indiatimes.com/rss/topstories", "type": "india-industry"},
        {"name": "CIO India", "url": "https://www.cio.com/in/feed/", "type": "india-industry"},
        {"name": "ET HR", "url": "https://hr.economictimes.indiatimes.com/rss/topstories", "type": "india-industry"},
        {"name": "NASSCOM Blog", "url": "https://nasscom.in/knowledge-center/rss.xml", "type": "india-industry"},
    ],
    "AIDS": [
        {"name": "Analytics Vidhya Blog", "url": "https://www.analyticsvidhya.com/feed/", "type": "india-tech"},
        {"name": "IIIT Hyderabad ML", "url": "https://ml.iiit.ac.in/feed/", "type": "india-research"},
    ],
    "ECE": [
        {"name": "Electronics For You", "url": "https://www.electronicsforu.com/feed", "type": "india-tech"},
    ],
    "EEE": [
        {"name": "Mercom India Solar", "url": "https://mercomindia.com/feed/", "type": "india-energy"},
        {"name": "ETEnergyWorld", "url": "https://energy.economictimes.indiatimes.com/rss/topstories", "type": "india-energy"},
    ],
    "ME": [
        {"name": "ETAuto", "url": "https://auto.economictimes.indiatimes.com/rss/topstories", "type": "india-industry"},
        {"name": "Manufacturing Today India", "url": "https://www.manufacturingtodayindia.com/feed", "type": "india-industry"},
        {"name": "Autocar India", "url": "https://www.autocarindia.com/RSS/rss.ashx", "type": "india-industry"},
    ],
    "CE": [
        {"name": "ETInfra", "url": "https://infra.economictimes.indiatimes.com/rss/topstories", "type": "india-industry"},
        {"name": "EPC World", "url": "https://www.epcworld.in/feed", "type": "india-industry"},
        {"name": "Smart Cities Mission", "url": "https://smartcities.gov.in/rss.xml", "type": "india-policy"},
        {"name": "NHAI News", "url": "https://nhai.gov.in/rss.xml", "type": "india-industry"},
    ],
    "BT": [
        {"name": "BioVoice News", "url": "https://www.biovoicenews.com/feed/", "type": "india-industry"},
        {"name": "Express Pharma", "url": "https://www.expresspharma.in/feed/", "type": "india-industry"},
        {"name": "ET Health", "url": "https://health.economictimes.indiatimes.com/rss/topstories", "type": "india-industry"},
        {"name": "DBT India", "url": "https://dbtindia.gov.in/rss.xml", "type": "india-research"},
        {"name": "BIRAC News", "url": "https://birac.nic.in/rss.xml", "type": "india-research"},
    ],
    "CH": [
        {"name": "Chemical Industry Digest", "url": "https://www.chemindigest.com/feed/", "type": "india-industry"},
        {"name": "ETEnergyWorld", "url": "https://energy.economictimes.indiatimes.com/rss/topstories", "type": "india-energy"},
    ],
    "AE": [
        {"name": "Livefist Defence", "url": "https://www.livefistdefence.com/feed/", "type": "india-defence"},
        {"name": "Indian Defence Review", "url": "https://www.indiandefencereview.com/feed/", "type": "india-defence"},
        {"name": "Defence Star", "url": "https://www.defencestar.in/feed/", "type": "india-defence"},
    ],
    "RAE": [
        {"name": "ETAuto", "url": "https://auto.economictimes.indiatimes.com/rss/topstories", "type": "india-industry"},
        {"name": "Manufacturing Today India", "url": "https://www.manufacturingtodayindia.com/feed", "type": "india-industry"},
        {"name": "ET Manufacturing", "url": "https://economictimes.indiatimes.com/industry/indl-goods/svs/rssfeeds/9990025.cms", "type": "india-industry"},
        {"name": "DST India", "url": "https://dst.gov.in/rss/latest-news/rss.xml", "type": "india-policy"},
        {"name": "iCreate India", "url": "https://icreateindia.org/feed/", "type": "india-startup"},
        {"name": "Techgig", "url": "https://www.techgig.com/feed/news", "type": "india-tech"},
        {"name": "Automation India", "url": "https://www.automationindia.net/feed/", "type": "india-industry"},
    ],
    "PT": [
        {"name": "Manufacturing Today India", "url": "https://www.manufacturingtodayindia.com/feed", "type": "india-industry"},
        {"name": "ETAuto", "url": "https://auto.economictimes.indiatimes.com/rss/topstories", "type": "india-industry"},
        {"name": "ET Manufacturing", "url": "https://economictimes.indiatimes.com/industry/indl-goods/svs/rssfeeds/9990025.cms", "type": "india-industry"},
        {"name": "IMTMA News", "url": "https://www.imtma.in/feed/", "type": "india-industry"},
        {"name": "CII News", "url": "https://www.cii.in/rss.aspx", "type": "india-policy"},
        {"name": "Autocar Pro India", "url": "https://www.autocarpro.in/rss/feed", "type": "india-industry"},
        {"name": "MSME Ministry", "url": "https://msme.gov.in/hi/rss.xml", "type": "india-policy"},
        {"name": "ET Infra", "url": "https://infra.economictimes.indiatimes.com/rss/topstories", "type": "india-industry"},
    ],
}


def get_all_rss_feeds_for_department(dept_key: str) -> List[Dict]:
    """Return the RSS feed list for a department, including India-focused sources."""
    base = list(DEPARTMENT_SOURCES.get(dept_key, {}).get("rss", []))
    # Append India common + department-specific Indian sources
    seen_urls = {f["url"] for f in base}
    for feed in INDIA_COMMON_RSS + INDIA_DEPT_RSS.get(dept_key, []):
        if feed["url"] not in seen_urls:
            base.append(feed)
            seen_urls.add(feed["url"])
    return base


def get_all_reddit_subs_for_department(dept_key: str) -> List[str]:
    """Return Reddit subs for a department, including India-focused subs."""
    base = list(DEPARTMENT_SOURCES.get(dept_key, {}).get("reddit", []))
    seen = {s.lower() for s in base}
    for sub in INDIA_COMMON_REDDIT:
        if sub.lower() not in seen:
            base.append(sub)
            seen.add(sub.lower())
    return base


def get_department_tag(dept_key: str) -> str:
    """Return the canonical tag string used in department_tags arrays."""
    return dept_key
