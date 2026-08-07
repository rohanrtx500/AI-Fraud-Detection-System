import os
import pickle

import networkx as nx


class KnowledgeGraphAnalyzer:
    """
    Advanced Knowledge Graph Analyzer using NetworkX.
    Detects fraud rings (cliques/cycles), runs risk propagation algorithms,
    and identifies hidden entity sharing clusters.
    """

    def __init__(self, model_dir: str = "models/registry"):
        self.model_dir = model_dir
        self.graph_path = os.path.join(model_dir, "graph_fraud_model.pkl")
        self.G = nx.Graph()
        self.load_graph()

    def load_graph(self):
        """
        Loads the graph from the serialized pickle registry file.
        """
        if os.path.exists(self.graph_path):
            try:
                with open(self.graph_path, "rb") as f:
                    self.G = pickle.load(f)
            except Exception:
                self.G = nx.Graph()
        else:
            self.G = nx.Graph()

    def save_graph(self):
        """
        Saves the graph to the serialized pickle registry file.
        """
        os.makedirs(os.path.dirname(self.graph_path), exist_ok=True)
        with open(self.graph_path, "wb") as f:
            pickle.dump(self.G, f)

    def detect_fraud_rings(self) -> list[dict]:
        """
        Scans graph structure to detect tightly connected cycles or components
        representing structured fraud rings.
        """
        rings = []
        components = list(nx.connected_components(self.G))

        for i, comp in enumerate(components):
            if len(comp) >= 4:
                subg = self.G.subgraph(comp)
                fraud_edges = sum(1 for u, v, d in subg.edges(data=True) if d.get("is_fraud") == 1)
                total_edges = subg.number_of_edges()
                fraud_rate = fraud_edges / total_edges if total_edges > 0 else 0.0

                # Check for cycle basis
                cycles = nx.cycle_basis(subg)
                if len(cycles) > 0 or fraud_rate > 0.1:
                    users_in_comp = [
                        node for node in comp if self.G.nodes[node].get("type") == "user"
                    ]
                    rings.append(
                        {
                            "ring_id": f"ring_{i}",
                            "nodes": list(comp),
                            "node_count": len(comp),
                            "fraud_rate": fraud_rate,
                            "cycle_count": len(cycles),
                            "connected_users": users_in_comp,
                            "severity": "CRITICAL" if fraud_rate > 0.3 else "HIGH",
                        }
                    )
        return rings

    def propagate_risk(self, iterations: int = 3, damping: float = 0.85) -> dict[str, float]:
        """
        Propagates risk from known fraudulent nodes (edges with is_fraud=1)
        to connected neighbors. Returns a mapping of node IDs to risk scores (0-100).
        """
        node_risks = dict.fromkeys(self.G.nodes(), 0.0)

        # Known fraud nodes (connected by at least one fraudulent transaction)
        known_fraud_nodes = set()
        for u, v, d in self.G.edges(data=True):
            if d.get("is_fraud") == 1:
                known_fraud_nodes.add(u)
                known_fraud_nodes.add(v)

        for node in known_fraud_nodes:
            node_risks[node] = 100.0

        # Propagate risk
        for _ in range(iterations):
            new_risks = node_risks.copy()
            for node in self.G.nodes():
                if node in known_fraud_nodes:
                    continue

                neighbors = list(self.G.neighbors(node))
                if not neighbors:
                    continue

                avg_neighbor_risk = sum(node_risks[nbr] for nbr in neighbors) / len(neighbors)
                new_risks[node] = damping * avg_neighbor_risk + (1.0 - damping) * new_risks[node]
            node_risks = new_risks

        return {k: round(v, 2) for k, v in node_risks.items()}

    def detect_hidden_sharing(self) -> list[dict]:
        """
        Identifies users sharing same devices or cards without explicit direct links.
        """
        shared_clusters = []
        users = [n for n, d in self.G.nodes(data=True) if d.get("type") == "user"]

        device_users = {}
        card_users = {}

        for u in users:
            neighbors = list(self.G.neighbors(u))
            for nbr in neighbors:
                nbr_type = self.G.nodes[nbr].get("type")
                if nbr_type == "device":
                    device_users.setdefault(nbr, []).append(u)
                elif nbr_type == "card":
                    card_users.setdefault(nbr, []).append(u)

        for dev, usr_list in device_users.items():
            if len(usr_list) > 1:
                shared_clusters.append(
                    {
                        "entity_type": "device",
                        "entity_id": dev,
                        "shared_by_users": usr_list,
                        "user_count": len(usr_list),
                        "description": f"Device {dev} shared by {len(usr_list)} accounts.",
                    }
                )

        for card, usr_list in card_users.items():
            if len(usr_list) > 1:
                shared_clusters.append(
                    {
                        "entity_type": "card",
                        "entity_id": card,
                        "shared_by_users": usr_list,
                        "user_count": len(usr_list),
                        "description": f"Card {card} shared by {len(usr_list)} accounts.",
                    }
                )

        return shared_clusters
