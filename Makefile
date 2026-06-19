.PHONY: neo4j graph rust api ui test dev

neo4j:
\tdocker compose up -d neo4j

graph:
\tpython build_graph.py

rust:
\tmaturin develop

api:
\tuvicorn main:app --reload --host $(API_HOST) --port $(API_PORT)

ui:
\tpython app.py

test:
\tpytest -q

dev:
\t@echo "Start Neo4j: make neo4j"
\t@echo "Load graph:  make graph"
\t@echo "Build Rust:  make rust"
\t@echo "Terminal 1:  make api"
\t@echo "Terminal 2:  make ui"
