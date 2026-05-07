"""Shared subject parsing, tagging, and link extraction for the recordings dataset.
Imported by fetch_emails_msg.py and retag.py."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_FILE = DATA_DIR / "data.json"
STATE_FILE = DATA_DIR / "state.json"

UNCATEGORIZED = "Uncategorized"

SUBJECT_PREFIXES: tuple[str, ...] = (
    "[EXTERNAL] Recording:",
    "[EXTERNAL] Online Training Recording:",
    "[EXTERNAL] Live Training Recording:",
    "[EXTERNAL] Live Online Training Recording:",
    "[EXTERNAL] Training Recording:",
    "Online Training Recording:",
    "Live Training Recording:",
    "Live Online Training Recording:",
    "Training Recording:",
    "Recording:",
)


def matches_subject(subject: str) -> str | None:
    if not subject:
        return None
    s = subject.lstrip().lower()
    for p in SUBJECT_PREFIXES:
        if s.startswith(p.lower()):
            return p
    return None


def parse_event_and_presenter(subject: str) -> tuple[str, str]:
    s = subject.strip()
    matched = matches_subject(s)
    if matched:
        s = s[len(matched):].strip()
    m = re.search(r",\s*presented by\s*(.+)$", s, flags=re.IGNORECASE)
    if m:
        return s[:m.start()].strip().rstrip(",").strip(), m.group(1).strip()
    return s, ""


def normalize_key(event: str, presenter: str) -> str:
    return f"{re.sub(r'\\s+', ' ', event.strip().lower())}||{presenter.strip().lower()}"


_LINK_TEXT_RE = re.compile(
    r'<a\b[^>]*href="([^"]+)"[^>]*>\s*(?:<[^>]+>\s*)*watch\s+the\s+recording\s*(?:<[^>]+>\s*)*</a>',
    re.IGNORECASE | re.DOTALL,
)
_OREILLY_HREF_RE = re.compile(r'href="([^"]*click\.et\.oreilly\.com[^"]*)"', re.IGNORECASE)
_ANY_URL_RE = re.compile(r'https?://[^\s"\'<>]+', re.IGNORECASE)


def unwrap_safelinks(url: str) -> str:
    try:
        p = urlparse(url)
        if p.netloc.endswith("safelinks.protection.outlook.com"):
            qs = parse_qs(p.query)
            if "url" in qs and qs["url"]:
                return unquote(qs["url"][0])
    except Exception:
        pass
    return url


def extract_recording_link(html_body: str) -> str | None:
    if not html_body:
        return None
    for rx in (_LINK_TEXT_RE, _OREILLY_HREF_RE):
        m = rx.search(html_body)
        if m:
            return unwrap_safelinks(m.group(1))
    for u in _ANY_URL_RE.findall(html_body):
        if "click.et.oreilly.com" in u or "learning.oreilly.com" in u:
            return unwrap_safelinks(u)
    return None


# ---------- topic tagging rules ----------
# (keyword substring, [tags]). Tags are unioned across all matching rules.
TOPIC_RULES: list[tuple[str, list[str]]] = [
    ("sql",                    ["SQL", "Data Analysis"]),
    ("data analysis",          ["Data Analysis"]),
    ("data analytics",         ["Data Analysis"]),
    ("data engineer",          ["Data Engineering"]),
    ("data engineering",       ["Data Engineering"]),
    ("data science",           ["Data Science"]),
    ("data visualization",     ["Data Visualization"]),
    ("power bi",               ["Power BI", "Data Visualization"]),
    ("tableau",                ["Tableau", "Data Visualization"]),
    ("excel",                  ["Excel", "Data Analysis"]),
    ("microsoft fabric",       ["Microsoft Fabric", "Data Engineering", "Azure"]),
    ("dp-700",                 ["Microsoft Fabric", "Certification", "Azure"]),
    ("dp-203",                 ["Azure", "Data Engineering", "Certification"]),
    ("dp-300",                 ["Azure", "Database", "Certification"]),
    ("dp-100",                 ["Azure", "Machine Learning", "Certification"]),
    ("dp-900",                 ["Azure", "Data Analysis", "Certification"]),
    ("az-",                    ["Azure", "Certification"]),
    ("aws",                    ["AWS", "Cloud"]),
    ("gcp",                    ["GCP", "Cloud"]),
    ("google cloud",           ["GCP", "Cloud"]),
    ("kubernetes",             ["Kubernetes", "DevOps", "Cloud"]),
    ("docker",                 ["Docker", "DevOps"]),
    ("terraform",              ["Terraform", "DevOps", "IaC"]),
    ("ansible",                ["Ansible", "DevOps"]),
    ("devops",                 ["DevOps"]),
    ("platform engineering",   ["Platform Engineering"]),
    ("site reliability",       ["SRE", "DevOps"]),
    ("ci/cd",                  ["CI/CD", "DevOps"]),
    ("github actions",         ["CI/CD", "GitHub", "DevOps"]),
    ("vibe coding",            ["AI", "GenAI", "Programming"]),
    ("ai-assisted",            ["AI", "GenAI"]),
    ("ai assisted",            ["AI", "GenAI"]),
    ("ai-augmented",           ["AI", "GenAI"]),
    ("ai augmented",           ["AI", "GenAI"]),
    ("ai-generated",           ["AI", "GenAI"]),
    ("ai generated",           ["AI", "GenAI"]),
    ("autogen",                ["AI", "Agentic AI", "AutoGen"]),
    ("mcp",                    ["MCP", "AI"]),
    ("model context protocol", ["MCP", "AI"]),
    ("context engineering",    ["MCP", "AI", "Prompt Engineering"]),
    ("prompting",              ["Prompt Engineering", "AI"]),
    ("prompt",                 ["Prompt Engineering", "AI"]),
    ("distributed system",     ["Distributed Systems", "Architecture"]),
    ("storytelling",           ["Communication", "Soft Skills"]),
    ("presentation",           ["Communication", "Soft Skills"]),
    ("presenter",              ["Communication", "Soft Skills"]),
    ("public speaking",        ["Communication", "Soft Skills"]),
    ("confidence at work",     ["Career", "Soft Skills"]),
    ("growth mindset",         ["Career", "Soft Skills"]),
    ("mental model",           ["Productivity", "Learning"]),
    ("life-hack",              ["Productivity"]),
    ("life hack",              ["Productivity"]),
    ("work on what matters",   ["Productivity", "Career"]),
    ("software design",        ["Software Engineering", "Architecture"]),
    ("software engineering",   ["Software Engineering"]),
    ("enterprise architect",   ["Architecture", "Software Engineering"]),
    ("solid principles",       ["Software Engineering", "Design Patterns"]),
    ("git",                    ["Git", "Version Control"]),
    ("technical writing",      ["Technical Writing", "Documentation"]),
    ("documentation",          ["Documentation"]),
    ("leading high performing",["Leadership", "Career"]),
    ("leading team",           ["Leadership", "Career"]),
    ("managing resistance",    ["Management", "Career"]),
    ("rhce",                   ["Linux", "Certification", "Red Hat"]),
    ("red hat",                ["Linux", "Red Hat"]),
    ("data lake",              ["Data Lake", "Data Engineering"]),
    ("oauth",                  ["OAuth", "Security", "APIs"]),
    ("tls",                    ["TLS", "Security", "Networking"]),
    ("ssl",                    ["TLS", "Security", "Networking"]),
    ("algorithm",              ["Algorithms", "Computer Science", "Programming"]),
    ("data structure",         ["Algorithms", "Computer Science", "Programming"]),
    ("o'reilly demo",          ["Demo"]),
    ("o\u2019reilly demo",     ["Demo"]),
    (" ai ",                   ["AI"]),
    (" ai,",                   ["AI"]),
    ("ai:",                    ["AI"]),
    ("artificial intelligence",["AI"]),
    ("agentic ai",             ["Agentic AI", "AI"]),
    ("agentic",                ["Agentic AI", "AI"]),
    ("genai",                  ["GenAI", "AI"]),
    ("generative ai",          ["GenAI", "AI"]),
    ("large language model",   ["LLM", "AI", "Machine Learning"]),
    (" llm",                   ["LLM", "AI"]),
    ("llms",                   ["LLM", "AI"]),
    ("rag",                    ["RAG", "LLM", "AI"]),
    ("retrieval-augmented",    ["RAG", "LLM", "AI"]),
    ("prompt engineering",     ["Prompt Engineering", "AI"]),
    ("chatgpt",                ["GenAI", "AI"]),
    ("claude",                 ["GenAI", "AI"]),
    ("openai",                 ["OpenAI", "AI"]),
    ("gpt-",                   ["GenAI", "AI"]),
    ("copilot",                ["Copilot", "AI"]),
    ("langchain",              ["LangChain", "LLM", "AI"]),
    ("llamaindex",             ["LlamaIndex", "LLM", "AI"]),
    ("vector database",        ["Vector DB", "AI"]),
    ("embedding",              ["Embeddings", "AI"]),
    ("transformer",            ["Transformers", "Deep Learning", "AI"]),
    ("hugging face",           ["Hugging Face", "AI", "Machine Learning"]),
    ("deep learning",          ["Deep Learning", "Machine Learning", "AI"]),
    ("neural network",         ["Deep Learning", "Machine Learning", "AI"]),
    ("machine learning",       ["Machine Learning", "AI"]),
    (" ml ",                   ["Machine Learning", "AI"]),
    ("mlops",                  ["MLOps", "Machine Learning", "DevOps"]),
    ("reinforcement learning", ["Reinforcement Learning", "Machine Learning", "AI"]),
    ("computer vision",        ["Computer Vision", "Deep Learning", "AI"]),
    ("nlp",                    ["NLP", "Machine Learning", "AI"]),
    ("natural language",       ["NLP", "AI"]),
    ("python",                 ["Python", "Programming"]),
    ("javascript",             ["JavaScript", "Programming"]),
    ("typescript",             ["TypeScript", "Programming"]),
    ("react",                  ["React", "Frontend", "JavaScript"]),
    ("angular",                ["Angular", "Frontend", "JavaScript"]),
    ("vue",                    ["Vue", "Frontend", "JavaScript"]),
    ("node.js",                ["Node.js", "Backend", "JavaScript"]),
    ("nodejs",                 ["Node.js", "Backend", "JavaScript"]),
    ("rust",                   ["Rust", "Programming"]),
    ("go ",                    ["Go", "Programming"]),
    ("golang",                 ["Go", "Programming"]),
    ("java ",                  ["Java", "Programming"]),
    ("spring boot",            ["Spring Boot", "Java", "Backend"]),
    ("c#",                     ["C#", ".NET", "Programming"]),
    (".net",                   [".NET", "Programming"]),
    ("c++",                    ["C++", "Programming"]),
    ("scala",                  ["Scala", "Programming"]),
    ("kotlin",                 ["Kotlin", "Programming"]),
    ("swift",                  ["Swift", "Programming"]),
    ("html",                   ["HTML", "Frontend"]),
    ("css",                    ["CSS", "Frontend"]),
    ("api ",                   ["APIs"]),
    ("rest api",               ["APIs", "REST"]),
    ("graphql",                ["GraphQL", "APIs"]),
    ("microservice",           ["Microservices", "Architecture"]),
    ("system design",          ["System Design", "Architecture"]),
    ("software architect",     ["Architecture"]),
    ("design pattern",         ["Design Patterns", "Architecture"]),
    ("clean code",             ["Clean Code", "Software Engineering"]),
    ("refactor",               ["Refactoring", "Software Engineering"]),
    ("test-driven",            ["TDD", "Testing"]),
    ("tdd",                    ["TDD", "Testing"]),
    ("unit test",              ["Testing"]),
    ("agile",                  ["Agile"]),
    ("scrum",                  ["Scrum", "Agile"]),
    ("kanban",                 ["Kanban", "Agile"]),
    ("product manage",         ["Product Management"]),
    ("project manage",         ["Project Management"]),
    ("leadership",             ["Leadership", "Career"]),
    ("management",             ["Management", "Career"]),
    ("career",                 ["Career"]),
    ("interview",              ["Interview Prep", "Career"]),
    ("resume",                 ["Career"]),
    ("communication",          ["Communication", "Soft Skills"]),
    ("negotiation",            ["Negotiation", "Soft Skills"]),
    ("learning",               ["Learning"]),
    ("neuroscience",           ["Neuroscience", "Productivity"]),
    ("productivity",           ["Productivity"]),
    ("time management",        ["Productivity"]),
    ("security",               ["Security"]),
    ("cybersecurity",          ["Security", "Cybersecurity"]),
    ("ethical hacking",        ["Security", "Ethical Hacking"]),
    ("penetration test",       ["Security", "Pentesting"]),
    ("zero trust",             ["Security", "Zero Trust"]),
    ("attack surface",         ["Security"]),
    ("threat",                 ["Security"]),
    ("blockchain",             ["Blockchain"]),
    ("web3",                   ["Web3", "Blockchain"]),
    ("solidity",               ["Solidity", "Blockchain"]),
    ("crypto",                 ["Crypto", "Blockchain"]),
    ("database",               ["Database"]),
    ("postgres",               ["PostgreSQL", "Database"]),
    ("mysql",                  ["MySQL", "Database"]),
    ("mongodb",                ["MongoDB", "Database", "NoSQL"]),
    ("redis",                  ["Redis", "Database"]),
    ("elasticsearch",          ["Elasticsearch", "Search"]),
    ("kafka",                  ["Kafka", "Streaming", "Data Engineering"]),
    ("spark",                  ["Spark", "Data Engineering"]),
    ("hadoop",                 ["Hadoop", "Data Engineering"]),
    ("airflow",                ["Airflow", "Data Engineering"]),
    ("dbt",                    ["dbt", "Data Engineering"]),
    ("snowflake",              ["Snowflake", "Data Engineering"]),
    ("databricks",             ["Databricks", "Data Engineering"]),
    ("statistics",             ["Statistics", "Data Science"]),
    ("probability",            ["Statistics", "Data Science"]),
    ("linux",                  ["Linux", "Operating Systems"]),
    ("bash",                   ["Bash", "Shell"]),
    ("powershell",             ["PowerShell"]),
    ("network",                ["Networking"]),
    ("mobile",                 ["Mobile"]),
    ("ios",                    ["iOS", "Mobile"]),
    ("android",                ["Android", "Mobile"]),
    ("flutter",                ["Flutter", "Mobile"]),
    ("game develop",           ["Game Dev"]),
    ("unity",                  ["Unity", "Game Dev"]),
    ("unreal",                 ["Unreal", "Game Dev"]),
]


# ---------- top-level domain grouping ----------
TAG_TO_DOMAINS: dict[str, list[str]] = {
    # AI & ML
    "AI": ["AI"], "GenAI": ["AI"], "LLM": ["AI"], "Agentic AI": ["AI"], "MCP": ["AI"], "RAG": ["AI"],
    "Prompt Engineering": ["AI"], "OpenAI": ["AI"], "Copilot": ["AI"], "AutoGen": ["AI"],
    "LangChain": ["AI"], "LlamaIndex": ["AI"], "Embeddings": ["AI"], "Vector DB": ["AI"],
    "Hugging Face": ["AI"], "Transformers": ["AI"], "Computer Vision": ["AI"], "NLP": ["AI"],
    "Reinforcement Learning": ["AI"], "Deep Learning": ["AI"], "Machine Learning": ["AI"],
    "MLOps": ["AI", "DevOps"], "Statistics": ["AI", "Data"],
    # Data
    "Data Analysis": ["Data"], "Data Engineering": ["Data"], "Data Science": ["Data"],
    "Data Visualization": ["Data"], "Data Lake": ["Data"], "SQL": ["Data"],
    "Power BI": ["Data"], "Tableau": ["Data"], "Excel": ["Data"],
    "Microsoft Fabric": ["Data", "Cloud"], "Snowflake": ["Data"], "Databricks": ["Data"],
    "Spark": ["Data"], "Kafka": ["Data"], "Streaming": ["Data"], "Hadoop": ["Data"],
    "Airflow": ["Data"], "dbt": ["Data"], "Database": ["Data"],
    "PostgreSQL": ["Data"], "MySQL": ["Data"], "MongoDB": ["Data"], "NoSQL": ["Data"],
    "Redis": ["Data"], "Elasticsearch": ["Data"], "Search": ["Data"],
    # Cloud
    "Cloud": ["Cloud"], "Azure": ["Cloud"], "AWS": ["Cloud"], "GCP": ["Cloud"],
    # DevOps
    "DevOps": ["DevOps"], "CI/CD": ["DevOps"], "Docker": ["DevOps"], "Kubernetes": ["DevOps"],
    "Terraform": ["DevOps"], "Ansible": ["DevOps"], "IaC": ["DevOps"], "GitHub": ["DevOps"],
    "Git": ["DevOps"], "Version Control": ["DevOps"], "SRE": ["DevOps"], "Platform Engineering": ["DevOps"],
    # Backend
    "Backend": ["Backend"], "Node.js": ["Backend"], "Spring Boot": ["Backend"], ".NET": ["Backend"],
    "APIs": ["Backend"], "REST": ["Backend"], "GraphQL": ["Backend"], "Microservices": ["Backend"],
    # Frontend
    "Frontend": ["Frontend"], "React": ["Frontend"], "Angular": ["Frontend"], "Vue": ["Frontend"],
    "HTML": ["Frontend"], "CSS": ["Frontend"],
    # Languages
    "Programming": ["Languages"], "Python": ["Languages"],
    "JavaScript": ["Languages", "Frontend"], "TypeScript": ["Languages", "Frontend"],
    "Rust": ["Languages"], "Go": ["Languages"], "Java": ["Languages"], "C#": ["Languages"],
    "C++": ["Languages"], "Scala": ["Languages"], "Kotlin": ["Languages"], "Swift": ["Languages"],
    # Security
    "Security": ["Security"], "Cybersecurity": ["Security"], "Ethical Hacking": ["Security"],
    "Pentesting": ["Security"], "Zero Trust": ["Security"], "OAuth": ["Security"], "TLS": ["Security"],
    # Software Engineering
    "Software Engineering": ["Software Engineering"], "Architecture": ["Software Engineering"],
    "Design Patterns": ["Software Engineering"], "System Design": ["Software Engineering"],
    "Clean Code": ["Software Engineering"], "Refactoring": ["Software Engineering"],
    "TDD": ["Software Engineering"], "Testing": ["Software Engineering"],
    "Distributed Systems": ["Software Engineering"], "Documentation": ["Software Engineering"],
    "Technical Writing": ["Software Engineering"], "Algorithms": ["Software Engineering"],
    "Computer Science": ["Software Engineering"], "Certification": ["Software Engineering"],
    # Mobile
    "Mobile": ["Mobile"], "iOS": ["Mobile"], "Android": ["Mobile"], "Flutter": ["Mobile"],
    # Career & Soft Skills
    "Career": ["Career & Soft Skills"], "Leadership": ["Career & Soft Skills"],
    "Management": ["Career & Soft Skills"], "Communication": ["Career & Soft Skills"],
    "Soft Skills": ["Career & Soft Skills"], "Interview Prep": ["Career & Soft Skills"],
    "Negotiation": ["Career & Soft Skills"], "Productivity": ["Career & Soft Skills"],
    "Learning": ["Career & Soft Skills"], "Neuroscience": ["Career & Soft Skills"],
    "Agile": ["Career & Soft Skills"], "Scrum": ["Career & Soft Skills"],
    "Kanban": ["Career & Soft Skills"], "Product Management": ["Career & Soft Skills"],
    "Project Management": ["Career & Soft Skills"],
    # Other / specialised
    "Blockchain": ["Other"], "Web3": ["Other"], "Solidity": ["Other"], "Crypto": ["Other"],
    "Linux": ["Other"], "Red Hat": ["Other"], "Operating Systems": ["Other"],
    "Bash": ["Other"], "Shell": ["Other"], "PowerShell": ["Other"],
    "Networking": ["Other"], "Game Dev": ["Other"], "Unity": ["Other"], "Unreal": ["Other"],
    "Demo": ["Other"], "Uncategorized": ["Other"],
}

DOMAIN_ORDER: list[str] = [
    "AI", "Data", "Cloud", "DevOps", "Backend", "Frontend", "Languages",
    "Security", "Software Engineering", "Mobile", "Career & Soft Skills", "Other",
]


def assign_tags(event: str) -> list[str]:
    s = f" {event.lower()} "
    tags: set[str] = set()
    for kw, kw_tags in TOPIC_RULES:
        if kw.lower() in s:
            tags.update(kw_tags)
    return sorted(tags) if tags else [UNCATEGORIZED]


def assign_domains(tags: list[str]) -> list[str]:
    s: set[str] = set()
    for t in tags:
        for d in TAG_TO_DOMAINS.get(t, ["Other"]):
            s.add(d)
    return [d for d in DOMAIN_ORDER if d in s]
