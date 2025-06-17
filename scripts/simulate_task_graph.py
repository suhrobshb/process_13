import yaml
from ai_engine.task_relationship_builder import TaskRelationshipBuilder

def simulate(graph_yaml_path: str):
    with open(graph_yaml_path) as f:
        graph = yaml.safe_load(f)
    builder = TaskRelationshipBuilder()
    adj = builder.build_graph(graph["tasks"])
    print("Dependency adjacency:", adj)

if __name__ == "__main__":
    import sys
    simulate(sys.argv[1])
