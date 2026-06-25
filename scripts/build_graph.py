import os

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
USER = os.getenv("NEO4J_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_PASSWORD", "testpassword123")


def create_compliance_graph(driver) -> None:
    clear_query = "MATCH (n) DETACH DELETE n"

    # Concept names must match the Rust rule engine
    build_query = """
    CREATE (f1:Framework {name: "FINRA Retail Communications"})
    CREATE (c1:RestrictedConcept {name: "Guaranteed Returns", action: "APPEND"})
    CREATE (c2:RestrictedConcept {name: "Risk-Free Investment", action: "APPEND"})
    CREATE (d1:Disclaimer {text: "All investments involve risk, including the possible loss of principal."})
    CREATE (d2:Disclaimer {text: "Past performance is not indicative of future results."})

    CREATE (f1)-[:PROHIBITS]->(c1)
    CREATE (f1)-[:PROHIBITS]->(c2)
    CREATE (c1)-[:REQUIRES_DISCLAIMER]->(d1)
    CREATE (c1)-[:REQUIRES_DISCLAIMER]->(d2)
    CREATE (c2)-[:REQUIRES_DISCLAIMER]->(d1)

    CREATE (f2:Framework {name: "Healthcare AI & HIPAA Compliance"})
    CREATE (c3:RestrictedConcept {name: "Guaranteed Cure", action: "BLOCK"})
    CREATE (c4:RestrictedConcept {name: "Definitive Diagnosis", action: "REDACT"})
    CREATE (d3:Disclaimer {text: "This AI tool is an administrative assistant and does not replace professional clinical judgment. A licensed provider must verify all outputs."})
    CREATE (d4:Disclaimer {text: "Ensure no Protected Health Information (PHI) is processed without verifying HIPAA compliance and a signed BAA."})

    CREATE (f2)-[:PROHIBITS]->(c3)
    CREATE (f2)-[:PROHIBITS]->(c4)
    CREATE (c3)-[:REQUIRES_DISCLAIMER]->(d3)
    CREATE (c4)-[:REQUIRES_DISCLAIMER]->(d3)
    CREATE (c4)-[:REQUIRES_DISCLAIMER]->(d4)
    """

    with driver.session() as session:
        session.run(clear_query)
        session.run(build_query)
        print("Knowledge graph loaded in Neo4j.")


if __name__ == "__main__":
    print(f"Connecting to Neo4j at {URI}...")
    with GraphDatabase.driver(URI, auth=(USER, PASSWORD)) as driver:
        driver.verify_connectivity()
        create_compliance_graph(driver)
