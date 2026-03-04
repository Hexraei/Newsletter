"""
Preview server — serves frontend + mock API data so you can preview the full UI
without a live DB connection. Run with: python preview_server.py
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

SAMPLE_ARTICLES = [
    {
        "id": "1", "title": "GPT-5 Sets New Benchmark in Reasoning Tasks",
        "source": "MIT Tech Review", "url": "https://example.com/1",
        "content": "OpenAI's latest model achieves state-of-the-art results on mathematical reasoning and code generation benchmarks.",
        "image": None, "published_at": "2026-03-01T10:00:00Z",
        "categories": ["AI", "Research"], "department_tags": ["CSE", "AIDS"]
    },
    {
        "id": "2", "title": "Rust Takes Over Systems Programming",
        "source": "Hacker News", "url": "https://example.com/2",
        "content": "Major cloud providers are rewriting core infrastructure in Rust for memory safety and performance.",
        "image": None, "published_at": "2026-03-01T09:30:00Z",
        "categories": ["Programming", "Systems"], "department_tags": ["CSE"]
    },
    {
        "id": "3", "title": "Quantum Computing Achieves 1000-Qubit Milestone",
        "source": "Nature", "url": "https://example.com/3",
        "content": "IBM announces a 1000-qubit processor with improved error correction rates, bringing practical quantum computing closer.",
        "image": None, "published_at": "2026-03-01T08:00:00Z",
        "categories": ["Quantum", "Hardware"], "department_tags": ["CSE", "ECE"]
    },
    {
        "id": "4", "title": "Boston Dynamics Spot Robot Now Self-Learning",
        "source": "IEEE Spectrum", "url": "https://example.com/4",
        "content": "Latest firmware update enables Spot to learn new terrain navigation autonomously using reinforcement learning.",
        "image": None, "published_at": "2026-03-01T07:45:00Z",
        "categories": ["Robotics", "AI"], "department_tags": ["RAE", "ME"]
    },
    {
        "id": "5", "title": "Industry 4.0: Smart Factories Reach 90% Uptime",
        "source": "Manufacturing Today", "url": "https://example.com/5",
        "content": "CNC-integrated IoT sensors and digital twin technology help factories hit record uptime with predictive maintenance.",
        "image": None, "published_at": "2026-03-01T07:00:00Z",
        "categories": ["Manufacturing", "IoT"], "department_tags": ["PT", "ME"]
    },
    {
        "id": "6", "title": "IIT Madras Develops Low-Cost Prosthetic Arm with Haptic Feedback",
        "source": "DST India", "url": "https://example.com/6",
        "content": "Researchers at IIT Madras create an affordable myoelectric prosthetic arm with tactile sensation for ₹15,000.",
        "image": None, "published_at": "2026-03-01T06:30:00Z",
        "categories": ["Biotech", "Robotics"], "department_tags": ["BT", "RAE"]
    },
    {
        "id": "7", "title": "5G RedCap Chips Enable Ultra-Low Power IoT Devices",
        "source": "EE Times", "url": "https://example.com/7",
        "content": "New reduced capability 5G chipsets consume 50% less power than existing NB-IoT modules.",
        "image": None, "published_at": "2026-03-01T06:00:00Z",
        "categories": ["5G", "IoT"], "department_tags": ["ECE"]
    },
    {
        "id": "8", "title": "Generative AI in Drug Discovery Cuts R&D Time by 40%",
        "source": "Nature Biotechnology", "url": "https://example.com/8",
        "content": "Pharma companies using AlphaFold-integrated pipelines report dramatic speedups in lead compound identification.",
        "image": None, "published_at": "2026-02-28T20:00:00Z",
        "categories": ["AI", "Drug Discovery"], "department_tags": ["BT", "AIDS"]
    },
    {
        "id": "9", "title": "Solar Panel Efficiency Breaks 35% Barrier",
        "source": "Renewable Energy World", "url": "https://example.com/9",
        "content": "Perovskite-silicon tandem cells achieve 35.1% efficiency in lab conditions, a new world record.",
        "image": None, "published_at": "2026-02-28T18:00:00Z",
        "categories": ["Energy", "Materials"], "department_tags": ["EEE", "CH"]
    },
    {
        "id": "10", "title": "ISRO Successfully Tests Reusable Launch Vehicle",
        "source": "The Hindu", "url": "https://example.com/10",
        "content": "India's space agency completes third successful landing test of RLV-TD, paving way for low-cost orbital missions.",
        "image": None, "published_at": "2026-02-28T15:00:00Z",
        "categories": ["Space", "Aviation"], "department_tags": ["AE"]
    },
    {
        "id": "11", "title": "Smart Concrete with Self-Healing Polymers Triples Bridge Lifespan",
        "source": "Civil Engineering Magazine", "url": "https://example.com/11",
        "content": "Microcapsule-embedded concrete autonomously seals cracks when exposed to moisture, extending structural life.",
        "image": None, "published_at": "2026-02-28T12:00:00Z",
        "categories": ["Materials", "Construction"], "department_tags": ["CE"]
    },
    {
        "id": "12", "title": "Google Introduces Willow: Next-Gen Quantum Chip",
        "source": "Google Research Blog", "url": "https://example.com/12",
        "content": "Willow demonstrates below-threshold error correction and scales to 105 physical qubits with sub-microsecond gates.",
        "image": None, "published_at": "2026-02-27T10:00:00Z",
        "categories": ["Quantum", "Computing"], "department_tags": ["CSE", "ECE"]
    },
]

SAMPLE_PAPERS = [
    {
        "id": "p1",
        "title": "Attention Is All You Need — Revisited: FlashAttention-3",
        "authors": "Tri Dao et al.", "venue": "NeurIPS 2025",
        "summary": "A hardware-aware exact attention algorithm achieving 2× speedup over FlashAttention-2 on H100 GPUs.",
        "url": "https://arxiv.org/abs/2307.08691", "citations": 1842,
        "featured_image_url": None, "department_tags": ["CSE", "AIDS"]
    },
    {
        "id": "p2",
        "title": "RoboAgent: Towards Solving Unstructured Manipulation Tasks at Scale",
        "authors": "Homanga Bharadhwaj et al.", "venue": "ICRA 2025",
        "summary": "Multi-task robotic manipulation trained with semantic augmentation generalises to 38 tasks from 12 hours of real data.",
        "url": "https://arxiv.org/abs/2309.01918", "citations": 412,
        "featured_image_url": None, "department_tags": ["RAE"]
    },
    {
        "id": "p3",
        "title": "Digital Twin-Driven Predictive Maintenance in Additive Manufacturing",
        "authors": "Chen, Liu & Park", "venue": "CIRP Annals 2025",
        "summary": "Physics-informed neural network surrogate models reduce unplanned downtime by 61% in FDM production lines.",
        "url": "https://doi.org/10.1016/j.cirp.2025.04.031", "citations": 88,
        "featured_image_url": None, "department_tags": ["PT", "ME"]
    },
]

DEPT_MAP = {
    "CSE": "Computer Science", "IT": "Information Technology",
    "AIDS": "AI & Data Science", "ECE": "Electronics",
    "EEE": "Electrical", "ME": "Mechanical", "CE": "Civil",
    "BT": "Biotechnology", "CH": "Chemical", "AE": "Aeronautical",
    "RAE": "Robotics & Automation", "PT": "Production Technology",
}

BREAKING = SAMPLE_ARTICLES[0]


def build_feed(dept):
    relevant = [a for a in SAMPLE_ARTICLES if not dept or dept.upper() in a.get("department_tags", [])]
    if not relevant:
        relevant = SAMPLE_ARTICLES[:6]
    papers = [p for p in SAMPLE_PAPERS if not dept or dept.upper() in p.get("department_tags", [])]
    return {
        "department": dept or "ALL",
        "breaking_news": BREAKING,
        "sections": {
            "top_stories": {"title": "Top Stories", "items": relevant[:4]},
            "trending": {"title": "Trending Now", "items": relevant[1:5]},
            "latest": {"title": "Latest", "items": relevant[:6]},
            "india": {"title": "India Focus", "items": relevant[2:6]},
            "opportunities": {"title": "Opportunities", "items": relevant[3:6]},
        },
        "research_papers": {
            "featured": papers,
            "recent": papers,
        },
        "meta": {"total": len(relevant), "dept_label": DEPT_MAP.get(dept, dept)},
    }


# In-memory user store for preview
_users = {}  # email → {name, password, department}


MIME_TYPES = {
    ".html": "text/html", ".css": "text/css", ".js": "application/javascript",
    ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml",
    ".ico": "image/x-icon", ".json": "application/json",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"  {self.address_string()} {fmt % args}")

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            raw = self.rfile.read(length)
            try:
                return json.loads(raw)
            except Exception:
                return {}
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_body()

        # --- Register ---
        if path in ("/api/v1/auth/register", "/api/auth/register"):
            email = (body.get("email") or "").strip().lower()
            name  = (body.get("full_name") or body.get("name") or "").strip()
            pw    = body.get("password") or ""
            dept  = body.get("department") or "CSE"
            if not email or not pw:
                return self.send_json({"detail": "Email and password required"}, 422)
            if email in _users:
                return self.send_json({"detail": "Email already registered"}, 400)
            _users[email] = {"name": name, "password": pw, "department": dept}
            return self.send_json({"id": "preview-user", "email": email, "full_name": name, "department": dept}, 201)

        # --- Login ---
        if path in ("/api/v1/auth/login", "/api/auth/login"):
            # OAuth2 form-encoded or JSON
            ct = self.headers.get("Content-Type", "")
            if "form" in ct:
                from urllib.parse import parse_qs
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode() if length else ""
                qs = parse_qs(raw)
                email = (qs.get("username", [""])[0]).lower()
                pw    = qs.get("password", [""])[0]
            else:
                email = (body.get("email") or body.get("username") or "").lower()
                pw    = body.get("password") or ""
            user = _users.get(email)
            if not user:
                # Auto-create guest in preview mode
                _users[email] = {"name": email.split("@")[0], "password": pw, "department": "CSE"}
                user = _users[email]
            token = f"preview-token-{email}"
            return self.send_json({
                "access_token": token, "token_type": "bearer",
                "user": {"id": "preview-user", "email": email, "full_name": user["name"], "department": user["department"]}
            })

        # --- Other POSTs ---
        return self.send_json({"detail": "not found"}, 404)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        # Normalise: strip /api/v1 prefix so both /api/... and /api/v1/... work
        if path.startswith("/api/v1/"):
            path = "/api/" + path[len("/api/v1/"):]

        # API routes
        if path.startswith("/api/"):
            if path == "/api/health":
                return self.send_json({"status": "ok", "mode": "preview"})
            if path.startswith("/api/feed/"):
                dept = path.split("/api/feed/")[-1].strip("/").upper()
                return self.send_json(build_feed(dept))
            if path == "/api/feed" or path == "/api/feed/":
                return self.send_json(build_feed("CSE"))
            if path.startswith("/api/departments"):
                return self.send_json({"departments": list(DEPT_MAP.keys())})
            if path.startswith("/api/articles"):
                return self.send_json({"items": SAMPLE_ARTICLES, "total": len(SAMPLE_ARTICLES)})
            # Auth endpoints (GET)
            if path in ("/api/auth/me", "/api/auth/profile"):
                auth = self.headers.get("Authorization", "")
                if auth.startswith("Bearer preview-token-"):
                    email = auth.replace("Bearer preview-token-", "").strip()
                    user = _users.get(email, {"name": "Preview User", "department": "CSE"})
                    return self.send_json({"id": "preview-user", "email": email, "full_name": user["name"], "department": user["department"]})
                return self.send_json({"detail": "Not authenticated"}, 401)
            # Swallow all other /api/ GETs gracefully
            return self.send_json({"items": [], "total": 0})

        # Static files
        if path == "/" or path == "":
            path = "/index.html"
        file_path = os.path.join(FRONTEND_DIR, path.lstrip("/"))
        if os.path.isfile(file_path):
            ext = os.path.splitext(file_path)[1]
            mime = MIME_TYPES.get(ext, "application/octet-stream")
            with open(file_path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            # SPA fallback → index.html
            file_path = os.path.join(FRONTEND_DIR, "index.html")
            with open(file_path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)


if __name__ == "__main__":
    port = 8080
    print(f"\n{'='*50}")
    print(f"  NEWS DAY — Preview Server")
    print(f"  http://localhost:{port}/")
    print(f"  (Mock data — no DB needed)")
    print(f"{'='*50}\n")
    server = HTTPServer(("0.0.0.0", port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
