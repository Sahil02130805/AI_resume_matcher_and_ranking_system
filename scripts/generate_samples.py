"""Generate 12 SYNTHETIC resumes (6 PDF + 6 DOCX). All names/contacts are fictional."""
import os, sys, zlib
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import docx

OUT = os.path.join(os.path.dirname(__file__), "..", "sample_data", "resumes")
os.makedirs(OUT, exist_ok=True)

R = [
 dict(name="Aarav Mehta", city="Pune", summary="Backend engineer with 6 years of experience building payment services.",
      skills="Java, Spring Boot, Spring Security, SQL, PostgreSQL, REST APIs, Microservices, Docker, Kubernetes, AWS, Kafka, JUnit, Jenkins, Redis, Agile",
      jobs=[("Senior Software Engineer", "FinCore Labs", "Mar 2020", "Present", ["Built microservices in Java and Spring Boot processing 2M transactions/day", "Tuned PostgreSQL queries and designed schemas; cut p95 latency by 40%", "Containerised services with Docker and deployed on AWS using Jenkins CI/CD", "Introduced Kafka event streaming between services"]),
            ("Software Engineer", "Payzen Tech", "Jul 2018", "Feb 2020", ["Developed REST APIs with Spring Boot and Hibernate", "Wrote JUnit tests achieving 85% coverage"])],
      edu="B.Tech in Computer Science, Pune Institute of Technology, 2014 - 2018", fmt="pdf"),
 dict(name="Priya Nair", city="Bengaluru", summary="Java developer, 4 years in enterprise backend development.",
      skills="Java, Spring Boot, MySQL, SQL, REST APIs, Docker, JUnit, Git, Agile",
      jobs=[("Software Engineer", "RetailHub", "Jun 2022", "Present", ["Implemented Spring Boot REST APIs for order management", "Wrote complex SQL queries on MySQL and optimised indexes", "Containerised apps using Docker; wrote JUnit tests"]),
            ("Junior Developer", "Webnest", "Jul 2021", "May 2022", ["Maintained Java services and fixed production defects"])],
      edu="B.E. in Information Technology, RV College of Engineering, 2017 - 2021", fmt="docx"),
 dict(name="Rohan Kulkarni", city="Mumbai", summary="Full-stack engineer, 5 years, mostly Java services with React front ends.",
      skills="Java, Spring, Hibernate, PostgreSQL, React, JavaScript, REST APIs, Docker, Git",
      jobs=[("Full Stack Developer", "MediaGrid", "Jan 2021", "Present", ["Built Java Spring services with Hibernate and PostgreSQL", "Created React dashboards consuming REST APIs", "Dockerised applications for staging environments"]),
            ("Software Developer", "Infoserve", "Aug 2019", "Dec 2020", ["Developed Java web applications and SQL reports"])],
      edu="Bachelor of Engineering in Computer Engineering, University of Mumbai, 2015 - 2019", fmt="pdf"),
 dict(name="Sneha Iyer", city="Chennai", summary="Backend developer with 3 years of experience in Kotlin and Java microservices.",
      skills="Kotlin, Java, Spring Boot, PostgreSQL, Microservices, Docker, AWS, Kafka, Git",
      jobs=[("Backend Developer", "CloudPay", "Apr 2023", "Present", ["Built Kotlin and Spring Boot microservices on AWS", "Designed PostgreSQL schemas and event pipelines with Kafka", "Packaged services with Docker"])],
      edu="B.Tech in Computer Science, SRM University, 2019 - 2023", fmt="docx"),
 dict(name="Vikram Singh", city="Delhi", summary="Python backend engineer with 5 years of API development experience.",
      skills="Python, Django, Flask, FastAPI, PostgreSQL, SQL, REST APIs, Docker, AWS, Redis, Git, Agile",
      jobs=[("Backend Engineer", "DataBridge", "Feb 2021", "Present", ["Built REST APIs with FastAPI and Django on PostgreSQL", "Deployed Docker containers to AWS ECS", "Added Redis caching layer"]),
            ("Python Developer", "Soft Solutions", "Jun 2019", "Jan 2021", ["Developed Flask microservices and SQL data pipelines"])],
      edu="B.Tech in Electronics, NIT Allahabad, 2015 - 2019", fmt="pdf"),
 dict(name="Ananya Das", city="Kolkata", summary="Frontend engineer with 4 years of experience building React applications.",
      skills="JavaScript, TypeScript, React, Redux, HTML, CSS, Node.js, Git, Agile",
      jobs=[("Frontend Engineer", "PixelWorks", "Sep 2021", "Present", ["Built responsive React and TypeScript interfaces", "Integrated REST APIs and managed state with Redux"]),
            ("UI Developer", "BrightSites", "Jul 2020", "Aug 2021", ["Created HTML/CSS templates and JavaScript widgets"])],
      edu="B.Sc in Computer Science, St. Xavier's College, 2017 - 2020", fmt="docx"),
 dict(name="Karan Patel", city="Ahmedabad", summary="Data scientist with 4 years of experience in machine learning and NLP.",
      skills="Python, Machine Learning, Deep Learning, NLP, TensorFlow, PyTorch, scikit-learn, Pandas, NumPy, SQL, Spark",
      jobs=[("Data Scientist", "InsightAI", "May 2022", "Present", ["Trained NLP classifiers with PyTorch and scikit-learn", "Built Spark and SQL data pipelines for model features"]),
            ("Data Analyst", "NumbersCo", "Jun 2020", "Apr 2022", ["Produced SQL analytics reports with Pandas"])],
      edu="M.Sc in Statistics, University of Pune, 2018 - 2020", fmt="pdf"),
 dict(name="Meera Reddy", city="Hyderabad", summary="Senior Java engineer with 8 years in large-scale distributed systems.",
      skills="Java, Spring Boot, Spring, Hibernate, SQL, Oracle, PostgreSQL, REST APIs, Microservices, Docker, Kubernetes, AWS, Kafka, JUnit, Mockito, Maven, CI/CD, Agile",
      jobs=[("Lead Engineer", "Globex Bank", "Jan 2019", "Present", ["Led a team of 5 building Java Spring Boot microservices", "Operated Kubernetes clusters on AWS with CI/CD pipelines", "Designed Kafka-based event-driven architecture", "Optimised Oracle and PostgreSQL SQL workloads"]),
            ("Software Engineer", "Tradeline", "Jun 2015", "Dec 2018", ["Developed Java Hibernate applications and REST APIs", "Maintained JUnit and Mockito test suites"])],
      edu="M.Tech in Software Engineering, IIIT Hyderabad, 2013 - 2015", fmt="docx"),
 dict(name="Arjun Verma", city="Jaipur", summary="Fresher with internship experience in Java development.",
      skills="Java, SQL, Git, HTML, CSS",
      jobs=[("Software Intern", "StartupX", "Jan 2024", "Jun 2024", ["Built small Java utilities and wrote SQL queries"])],
      edu="B.Tech in Computer Science, Manipal University, 2020 - 2024", fmt="pdf"),
 dict(name="Divya Joshi", city="Pune", summary="QA automation engineer, 5 years, test frameworks and CI.",
      skills="Selenium, Java, JUnit, Jenkins, SQL, Git, Agile",
      jobs=[("QA Automation Engineer", "TestRight", "Mar 2021", "Present", ["Built Selenium and Java test frameworks run via Jenkins", "Validated database results using SQL"]),
            ("QA Analyst", "QualityFirst", "Aug 2019", "Feb 2021", ["Executed manual and automated regression tests"])],
      edu="B.E. in Computer Science, COEP Pune, 2015 - 2019", fmt="docx"),
 dict(name="Sahil Khan", city="Noida", summary="DevOps engineer, 6 years of experience with cloud infrastructure.",
      skills="AWS, Docker, Kubernetes, Terraform, Jenkins, CI/CD, Linux, Python, Git",
      jobs=[("DevOps Engineer", "CloudOps", "Jan 2020", "Present", ["Managed Kubernetes on AWS with Terraform", "Built Jenkins CI/CD pipelines for Java and Python services"]),
            ("System Administrator", "NetServe", "Jun 2018", "Dec 2019", ["Administered Linux servers and Docker hosts"])],
      edu="B.Tech in Information Technology, JSS Noida, 2014 - 2018", fmt="pdf"),
 dict(name="Neha Gupta", city="Pune", summary="Software engineer with 7 years of experience in Java and Spring Boot payments systems.",
      skills="Java, Spring Boot, PostgreSQL, SQL, REST APIs, Microservices, Docker, AWS, JUnit, Kafka, Redis, Agile",
      jobs=[("Software Engineer II", "PayWave", "Jan 2019", "Present", ["Designed Spring Boot microservices for card payments", "Wrote PostgreSQL migrations and tuned SQL", "Deployed Docker images to AWS; JUnit and integration tests", "Used Redis caching and Kafka messaging"])],
      edu="M.Sc in Computer Science, University of Pune, 2016 - 2018", fmt="docx"),
 dict(name="Rahul Bansal", city="Pune", summary="Results-driven professional with 6 years of experience seeking challenging roles.",
      skills="Java, Spring Boot, SQL, PostgreSQL, REST APIs, Microservices, Docker, Kubernetes, AWS, Kafka, JUnit, Jenkins, Redis, Agile, Python, React",
      jobs=[("Customer Support Executive", "CallWell Services", "Jan 2020", "Present", ["Handled customer tickets and escalations", "Prepared weekly service reports", "Trained new joiners on helpdesk tools"]),
            ("Sales Associate", "RetailMart", "Jun 2018", "Dec 2019", ["Managed store inventory and billing", "Achieved quarterly sales targets"])],
      edu="B.Com, Pune University, 2014 - 2018", fmt="docx"),
 dict(name="Isha Rao", city="Bengaluru", summary="Java engineer with 5+ years building RESTful services; also consults independently.",
      skills="Java, SpringBoot, Postgres, RESTful APIs, Dockerised deployments, AWS, microservice architecture, JUnit, Git",
      jobs=[("Software Engineer", "NovaSoft", "Jan 2021", "Present", ["Developed Java SpringBoot microservice architecture for logistics", "Designed Postgres schemas and tuned SQL queries", "Shipped Dockerised services to AWS with JUnit coverage"]),
            ("Freelance Java Consultant", "Self-employed", "Jun 2021", "Dec 2022", ["Built RESTful APIs in Java for two startups"]),
            ("Junior Developer", "CodeCraft", "Jul 2019", "Dec 2020", ["Maintained Java Spring applications and SQL reports"])],
      edu="B.Tech in Computer Science, BMS College of Engineering, 2015 - 2019", fmt="pdf"),
]


def make_pdf(r, path):
    ss = getSampleStyleSheet()
    doc = SimpleDocTemplate(path, pagesize=A4)
    f = [Paragraph(r["name"], ss["Title"]), Paragraph(f'{r["name"].split()[0].lower()}.{r["name"].split()[1].lower()}@example.com | +91 98765 4{zlib.crc32(r["name"].encode())%9000+1000:04d} | {r["city"]}', ss["Normal"]),
         Spacer(1, 10), Paragraph("SUMMARY", ss["Heading3"]), Paragraph(r["summary"], ss["Normal"]),
         Paragraph("SKILLS", ss["Heading3"]), Paragraph(r["skills"], ss["Normal"]), Paragraph("EXPERIENCE", ss["Heading3"])]
    for t, c, s, e, bl in r["jobs"]:
        f.append(Paragraph(f"<b>{t}</b>, {c} | {s} - {e}", ss["Normal"]))
        f += [Paragraph("• " + b, ss["Normal"]) for b in bl] + [Spacer(1, 6)]
    f += [Paragraph("EDUCATION", ss["Heading3"]), Paragraph(r["edu"], ss["Normal"])]
    doc.build(f)


def make_docx(r, path):
    d = docx.Document()
    d.add_heading(r["name"], 0)
    d.add_paragraph(f'{r["name"].split()[0].lower()}.{r["name"].split()[1].lower()}@example.com | +91 91234 5{zlib.crc32(r["name"].encode())%9000+1000:04d} | {r["city"]}')
    for h, body in (("Summary", r["summary"]), ("Skills", r["skills"])):
        d.add_heading(h, 2); d.add_paragraph(body)
    d.add_heading("Work Experience", 2)
    for t, c, s, e, bl in r["jobs"]:
        d.add_paragraph(f"{t}, {c} | {s} - {e}").runs[0].bold = True
        for b in bl:
            d.add_paragraph(b, style="List Bullet")
    d.add_heading("Education", 2); d.add_paragraph(r["edu"])
    d.save(path)


if __name__ == "__main__":
    for i, r in enumerate(R, 1):
        fn = f'{i:02d}_{r["name"].replace(" ", "_")}.{r["fmt"]}'
        (make_pdf if r["fmt"] == "pdf" else make_docx)(r, os.path.join(OUT, fn))
    print(f"Generated {len(R)} synthetic resumes in {os.path.abspath(OUT)}")
