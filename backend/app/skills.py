"""Skill taxonomy: canonical skill -> aliases, plus a directed 'related skill' map
used to give partial credit (e.g. JD wants SQL, candidate has PostgreSQL)."""
SKILLS = {
    "Python": ["python3"], "Java": [], "JavaScript": ["js", "ecmascript"], "TypeScript": [],
    "Kotlin": [], "Scala": [], "C++": [], "C#": ["csharp"], ".NET": ["dotnet", ".net core"],
    "Go": ["golang", "go language", "go programming"], "PHP": [], "Ruby": [], "Rust": [],
    "Spring Boot": ["springboot", "spring-boot"],
    "Spring": ["spring framework", "spring mvc", "spring security", "spring data"],
    "Hibernate": [], "JPA": ["spring data jpa"], "Maven": [], "Gradle": [],
    "JUnit": ["junit5"], "Mockito": [], "pytest": [],
    "React": ["react.js", "reactjs"], "Next.js": ["nextjs"], "Angular": ["angularjs"],
    "Vue.js": ["vue", "vuejs"], "Redux": [], "HTML": ["html5"], "CSS": ["css3", "sass", "scss"],
    "Node.js": ["nodejs", "node js"], "Express": ["express.js", "expressjs"],
    "FastAPI": [], "Django": [], "Flask": [],
    "SQL": ["pl/sql", "t-sql"], "PostgreSQL": ["postgres"], "MySQL": [], "SQL Server": ["mssql"],
    "Oracle": ["oracle db"], "MongoDB": ["mongo"], "NoSQL": [], "Redis": [], "Cassandra": [],
    "Elasticsearch": ["elastic search"],
    "REST APIs": ["rest api", "restful", "restful api", "restful apis", "restful services", "rest services", "rest"],
    "GraphQL": [], "Microservices": ["microservice", "micro-services", "microservice architecture"],
    "Kafka": ["apache kafka"], "RabbitMQ": [], "ActiveMQ": [],
    "Docker": ["dockerized", "dockerised", "docker compose", "containerized", "containerised"], "Kubernetes": ["k8s"], "Terraform": [], "Linux": [],
    "AWS": ["amazon web services", "ec2", "s3"], "Azure": [], "GCP": ["google cloud"],
    "CI/CD": ["cicd", "ci-cd", "continuous integration"], "Jenkins": [], "GitHub Actions": [], "Git": ["github", "gitlab"],
    "Machine Learning": ["ml"], "Deep Learning": [], "NLP": ["natural language processing"],
    "TensorFlow": [], "PyTorch": [], "scikit-learn": ["sklearn"], "Pandas": [], "NumPy": [],
    "Spark": ["pyspark", "apache spark"], "Tableau": [], "Power BI": ["powerbi"],
    "Agile": ["scrum"], "Selenium": [],
}

# need -> {have: credit}. Directed: what a candidate holding `have` earns for a JD asking `need`.
RELATED = {
    "Spring Boot": {"Spring": 0.8}, "Spring": {"Spring Boot": 1.0},
    "SQL": {"PostgreSQL": 0.9, "MySQL": 0.9, "SQL Server": 0.9, "Oracle": 0.9},
    "PostgreSQL": {"MySQL": 0.6, "SQL Server": 0.5, "Oracle": 0.5, "SQL": 0.5},
    "MySQL": {"PostgreSQL": 0.6, "SQL": 0.5, "SQL Server": 0.5},
    "NoSQL": {"MongoDB": 1.0, "Cassandra": 1.0, "Redis": 0.6},
    "MongoDB": {"NoSQL": 0.5, "Cassandra": 0.5},
    "React": {"Next.js": 0.9, "Angular": 0.5, "Vue.js": 0.5}, "Angular": {"React": 0.5, "Vue.js": 0.5},
    "Vue.js": {"React": 0.5, "Angular": 0.5},
    "JavaScript": {"TypeScript": 0.9, "Node.js": 0.6, "React": 0.6},
    "TypeScript": {"JavaScript": 0.6},
    "Java": {"Kotlin": 0.5, "Scala": 0.4, "C#": 0.4},
    "Python": {"Django": 0.8, "Flask": 0.8, "FastAPI": 0.8},
    "FastAPI": {"Flask": 0.6, "Django": 0.5}, "Django": {"Flask": 0.6, "FastAPI": 0.5},
    "Flask": {"FastAPI": 0.6, "Django": 0.6},
    "AWS": {"Azure": 0.5, "GCP": 0.5}, "Azure": {"AWS": 0.5, "GCP": 0.5}, "GCP": {"AWS": 0.5, "Azure": 0.5},
    "Kubernetes": {"Docker": 0.5}, "Docker": {"Kubernetes": 0.7},
    "Kafka": {"RabbitMQ": 0.6}, "RabbitMQ": {"Kafka": 0.6},
    "Machine Learning": {"scikit-learn": 0.8, "TensorFlow": 0.8, "PyTorch": 0.8, "Deep Learning": 0.8},
    "Deep Learning": {"TensorFlow": 0.8, "PyTorch": 0.8}, "TensorFlow": {"PyTorch": 0.6}, "PyTorch": {"TensorFlow": 0.6},
    "CI/CD": {"Jenkins": 1.0, "GitHub Actions": 1.0},
    "REST APIs": {"FastAPI": 0.7, "Spring Boot": 0.6, "Django": 0.6, "Flask": 0.6, "Express": 0.6},
    "Hibernate": {"JPA": 1.0}, "JPA": {"Hibernate": 1.0},
    "Maven": {"Gradle": 0.8}, "Gradle": {"Maven": 0.8},
    "JUnit": {"Mockito": 0.6, "pytest": 0.5},
    "Microservices": {"Kubernetes": 0.3, "Spring Boot": 0.3},
}


# Aliases that are ordinary English words when lower-cased; they only count when written in a non-lowercase form
# (REST, ML, JS, Spring ...), which avoids matching "the rest of the team" or "spring 2019".
CASE_SENSITIVE_ALIASES = {"rest", "ml", "js", "spring", "s3", "ec2", "express", "oracle"}
