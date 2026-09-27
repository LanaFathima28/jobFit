import re
from typing import List

# Comprehensive dictionary mapping skill aliases/variations to canonical skill names
SKILL_ALIASES = {
    # Frontend
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    "react": "React",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "next js": "Next.js",
    "vuejs": "Vue.js",
    "vue.js": "Vue.js",
    "vue js": "Vue.js",
    "angularjs": "Angular",
    "angular.js": "Angular",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "html5": "HTML",
    "css3": "CSS",
    "tailwind css": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    
    # Backend & Programming Languages
    "py": "Python",
    "python3": "Python",
    "python 3": "Python",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "node js": "Node.js",
    "expressjs": "Express.js",
    "express.js": "Express.js",
    "fast api": "FastAPI",
    "fastapi": "FastAPI",
    "golang": "Go",
    "go lang": "Go",
    "cpp": "C++",
    "c plus plus": "C++",
    "c#": "C#",
    "c sharp": "C#",
    "dotnet": ".NET",
    ".net core": ".NET",
    "ruby on rails": "Ruby on Rails",
    "rails": "Ruby on Rails",
    "spring boot": "Spring Boot",

    # Databases & Vector DBs
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "postgres sql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    "redis db": "Redis",
    "my sql": "MySQL",
    "mysql": "MySQL",
    "mssql": "Microsoft SQL Server",
    "sql server": "Microsoft SQL Server",
    "pgvector": "pgvector",
    "pinecone": "Pinecone",
    "chromadb": "ChromaDB",
    
    # Cloud & DevOps
    "aws": "AWS",
    "amazon web services": "AWS",
    "aws cloud": "AWS",
    "gcp": "Google Cloud Platform",
    "google cloud": "Google Cloud Platform",
    "azure": "Microsoft Azure",
    "ms azure": "Microsoft Azure",
    "docker containers": "Docker",
    "docker container": "Docker",
    "docker": "Docker",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "terraform": "Terraform",
    "ansible": "Ansible",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "github actions": "GitHub Actions",
    
    # AI / ML & Data Science
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence": "Artificial Intelligence",
    "llm": "LLMs",
    "llms": "LLMs",
    "large language models": "LLMs",
    "genai": "Generative AI",
    "generative ai": "Generative AI",
    "nlp": "Natural Language Processing",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "spark": "Apache Spark",
    "pyspark": "PySpark"
}


def normalize_skill(skill: str) -> str:
    """
    Normalizes a single skill string to its canonical representation if matched in SKILL_ALIASES,
    otherwise formats title-case cleanly.
    """
    if not skill or not skill.strip():
        return ""

    raw_clean = skill.strip()
    lookup_key = raw_clean.lower()
    # Strip common leading bullet symbols or punctuation
    lookup_key = re.sub(r"^[•\-\*\s]+", "", lookup_key).strip()

    if lookup_key in SKILL_ALIASES:
        return SKILL_ALIASES[lookup_key]

    # Clean double spaces and preserve standard naming
    normalized = re.sub(r"\s+", " ", raw_clean)
    
    # Default capitalization for unmatched skills
    if len(normalized) <= 3 and normalized.isupper():
        return normalized
    elif normalized.islower():
        return normalized.title()
    
    return normalized


def normalize_skills(skills_list: List[str]) -> List[str]:
    """
    Normalizes a list of skill strings, removing duplicates while maintaining order.
    """
    if not skills_list:
        return []

    normalized_set = set()
    result = []

    for s in skills_list:
        norm = normalize_skill(s)
        if norm and norm.lower() not in normalized_set:
            normalized_set.add(norm.lower())
            result.append(norm)

    return result
