import hashlib
import os
import pickle

import networkx as nx
import pandas as pd
from neo4j import GraphDatabase


def get_card_id(sender_id: str, transaction_id: str) -> str:
    """
    Deterministically maps a transaction to a simulated card ID.
    To make it realistic, we allocate 1 primary card (80% of transactions)
    and 1 secondary card (20% of transactions) per user.
    """
    if not sender_id or not transaction_id:
        return "card_unknown"

    # Use MD5 hash of transaction ID to allocate cards deterministically
    h_val = int(hashlib.md5(transaction_id.encode("utf-8")).hexdigest(), 16)
    card_suffix = "0" if (h_val % 10) < 8 else "1"

    # Extract numeric part of sender_id
    user_num = sender_id.split("_")[1] if "_" in sender_id else sender_id
    return f"card_{user_num}_{card_suffix}"


# Global cached Neo4j driver connection to prevent socket pool reuse overhead
_neo4j_driver = None


class GraphFraudDetector:
    """
    Fraud detection engine based on NetworkX and Neo4j graphs representing transactions
    connecting users, devices, cards, and merchants.
    """

    def __init__(self):
        self.G = nx.Graph()
        self.neo4j_driver = None
        self.use_neo4j = False

        # Read environment configuration parameters
        self.neo4j_uri = os.getenv("NEO4J_URI")
        self.neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        self.neo4j_password = os.getenv("NEO4J_PASSWORD")

        if self.neo4j_uri and self.neo4j_password:
            try:
                global _neo4j_driver
                if _neo4j_driver is None:
                    print(f"Initializing Neo4j database driver pool: {self.neo4j_uri}")
                    _neo4j_driver = GraphDatabase.driver(
                        self.neo4j_uri, auth=(self.neo4j_user, self.neo4j_password)
                    )
                    _neo4j_driver.verify_connectivity()
                    self._create_constraints_with_driver(_neo4j_driver)
                self.neo4j_driver = _neo4j_driver
                self.use_neo4j = True
            except Exception as e:
                print(f"Neo4j connection failed: {e}. Falling back to NetworkX.")
                self.use_neo4j = False

    def _create_constraints_with_driver(self, driver):
        """
        Creates uniqueness schema constraints on node IDs.
        """
        queries = [
            "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
            "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT card_id IF NOT EXISTS FOR (c:Card) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT merchant_id IF NOT EXISTS FOR (m:Merchant) REQUIRE m.id IS UNIQUE",
        ]
        with driver.session() as session:
            for q in queries:
                try:
                    session.run(q)
                except Exception as e:
                    print(f"Uniqueness constraint check bypassed: {e}")

    def build_graph(self, df: pd.DataFrame) -> nx.Graph:
        """
        Populates the graph nodes and edges from a transaction DataFrame.
        """
        print("Building transaction graph network...")
        self.G.clear()

        # Always build NetworkX in-memory representation for fallback consistency
        for _, row in df.iterrows():
            tx_id = str(row["transaction_id"])
            sender_id = str(row["sender_id"])
            receiver_id = str(row["receiver_id"])
            device_id = str(row["device_id"])
            amount = float(row["amount"])
            is_fraud = int(row.get("is_fraud", 0))
            timestamp = str(row.get("timestamp", ""))

            # Generate simulated Card ID
            card_id = get_card_id(sender_id, tx_id)

            # Add nodes with types
            self.G.add_node(sender_id, type="user")
            self.G.add_node(device_id, type="device")
            self.G.add_node(card_id, type="card")
            self.G.add_node(receiver_id, type="merchant")

            # Add transaction-linking edges
            edge_attrs = {
                "transaction_id": tx_id,
                "amount": amount,
                "is_fraud": is_fraud,
                "timestamp": timestamp,
            }

            # Edge mappings
            self.G.add_edge(sender_id, device_id, **edge_attrs)
            self.G.add_edge(sender_id, card_id, **edge_attrs)
            self.G.add_edge(card_id, receiver_id, **edge_attrs)
            self.G.add_edge(device_id, receiver_id, **edge_attrs)

        # Bulk write to Neo4j if configured
        if self.use_neo4j and self.neo4j_driver:
            try:
                print("Populating transaction records to Neo4j graph...")
                with self.neo4j_driver.session() as session:
                    # Clear database first
                    session.run("MATCH (n) DETACH DELETE n")

                    def upload_batch(tx, rows_list):
                        query = """
                        UNWIND $rows AS row
                        MERGE (u:User {id: row.sender_id})
                        MERGE (d:Device {id: row.device_id})
                        MERGE (c:Card {id: row.card_id})
                        MERGE (m:Merchant {id: row.receiver_id})

                        CREATE (u)-[:HAS_DEVICE {transaction_id: row.tx_id, amount: row.amount, is_fraud: row.is_fraud, timestamp: row.timestamp}]->(d)
                        CREATE (u)-[:HAS_CARD {transaction_id: row.tx_id, amount: row.amount, is_fraud: row.is_fraud, timestamp: row.timestamp}]->(c)
                        CREATE (c)-[:USED_AT {transaction_id: row.tx_id, amount: row.amount, is_fraud: row.is_fraud, timestamp: row.timestamp}]->(m)
                        CREATE (d)-[:USED_AT {transaction_id: row.tx_id, amount: row.amount, is_fraud: row.is_fraud, timestamp: row.timestamp}]->(m)
                        """
                        tx.run(query, rows=rows_list)

                    batch = []
                    for _, row in df.iterrows():
                        tx_id = str(row["transaction_id"])
                        sender_id = str(row["sender_id"])
                        receiver_id = str(row["receiver_id"])
                        device_id = str(row["device_id"])
                        amount = float(row["amount"])
                        is_fraud = int(row.get("is_fraud", 0))
                        timestamp = str(row.get("timestamp", ""))
                        card_id = get_card_id(sender_id, tx_id)

                        batch.append(
                            {
                                "tx_id": tx_id,
                                "sender_id": sender_id,
                                "receiver_id": receiver_id,
                                "device_id": device_id,
                                "amount": amount,
                                "is_fraud": is_fraud,
                                "timestamp": timestamp,
                                "card_id": card_id,
                            }
                        )

                    session.execute_write(upload_batch, batch)
                    print("Neo4j database loaded successfully.")
            except Exception as e:
                print(f"Failed to populate Neo4j graph: {e}")

        print(
            f"Graph constructed with {self.G.number_of_nodes()} nodes and {self.G.number_of_edges()} edges."
        )
        return self.G

    def add_transaction(self, tx_payload: dict, is_fraud: int = 0) -> None:
        """
        Dynamically adds a single transaction to the graph.
        Useful for real-time streaming updates.
        """
        tx_id = str(tx_payload.get("transaction_id", ""))
        sender_id = str(tx_payload["sender_id"])
        receiver_id = str(tx_payload["receiver_id"])
        device_id = str(tx_payload["device_id"])
        amount = float(tx_payload["amount"])
        timestamp = str(tx_payload.get("timestamp", ""))

        card_id = get_card_id(sender_id, tx_id)

        # Update NetworkX model
        self.G.add_node(sender_id, type="user")
        self.G.add_node(device_id, type="device")
        self.G.add_node(card_id, type="card")
        self.G.add_node(receiver_id, type="merchant")

        edge_attrs = {
            "transaction_id": tx_id,
            "amount": amount,
            "is_fraud": is_fraud,
            "timestamp": timestamp,
        }

        self.G.add_edge(sender_id, device_id, **edge_attrs)
        self.G.add_edge(sender_id, card_id, **edge_attrs)
        self.G.add_edge(card_id, receiver_id, **edge_attrs)
        self.G.add_edge(device_id, receiver_id, **edge_attrs)

        # Update Neo4j
        if self.use_neo4j and self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    query = """
                    MERGE (u:User {id: $sender_id})
                    MERGE (d:Device {id: $device_id})
                    MERGE (c:Card {id: $card_id})
                    MERGE (m:Merchant {id: $receiver_id})

                    CREATE (u)-[:HAS_DEVICE {transaction_id: $tx_id, amount: $amount, is_fraud: $is_fraud, timestamp: $timestamp}]->(d)
                    CREATE (u)-[:HAS_CARD {transaction_id: $tx_id, amount: $amount, is_fraud: $is_fraud, timestamp: $timestamp}]->(c)
                    CREATE (c)-[:USED_AT {transaction_id: $tx_id, amount: $amount, is_fraud: $is_fraud, timestamp: $timestamp}]->(m)
                    CREATE (d)-[:USED_AT {transaction_id: $tx_id, amount: $amount, is_fraud: $is_fraud, timestamp: $timestamp}]->(m)
                    """
                    session.run(
                        query,
                        sender_id=sender_id,
                        device_id=device_id,
                        card_id=card_id,
                        receiver_id=receiver_id,
                        tx_id=tx_id,
                        amount=amount,
                        is_fraud=is_fraud,
                        timestamp=timestamp,
                    )
            except Exception as e:
                print(f"Failed to append transaction to Neo4j: {e}")

    def compute_graph_metrics(
        self,
        sender_id: str,
        device_id: str,
        card_id: str | None = None,
        receiver_id: str | None = None,
    ) -> dict:
        """
        Extracts structural graph metrics for a candidate transaction to assess fraud probability.
        """
        if not card_id:
            card_id = get_card_id(sender_id, "dummy_tx_id")

        if self.use_neo4j and self.neo4j_driver:
            try:
                with self.neo4j_driver.session() as session:
                    res_device_user = session.run(
                        "MATCH (d:Device {id: $device_id})-[r:HAS_DEVICE]-(u:User) RETURN count(distinct u) as count",
                        device_id=device_id,
                    )
                    device_user_count = res_device_user.single()["count"] or 0

                    res_card_user = session.run(
                        "MATCH (c:Card {id: $card_id})-[r:HAS_CARD]-(u:User) RETURN count(distinct u) as count",
                        card_id=card_id,
                    )
                    card_user_count = res_card_user.single()["count"] or 0

                    res_user_device = session.run(
                        "MATCH (u:User {id: $sender_id})-[r:HAS_DEVICE]-(d:Device) RETURN count(distinct d) as count",
                        sender_id=sender_id,
                    )
                    user_device_count = res_user_device.single()["count"] or 0

                    res_user_card = session.run(
                        "MATCH (u:User {id: $sender_id})-[r:HAS_CARD]-(c:Card) RETURN count(distinct c) as count",
                        sender_id=sender_id,
                    )
                    user_card_count = res_user_card.single()["count"] or 0

                    return {
                        "device_user_count": device_user_count,
                        "card_user_count": card_user_count,
                        "user_device_count": user_device_count,
                        "user_card_count": user_card_count,
                        "is_device_shared": device_user_count > 1,
                        "is_card_shared": card_user_count > 1,
                    }
            except Exception as e:
                print(f"Failed to query Neo4j metrics: {e}. Falling back to NetworkX.")

        # NetworkX fallback calculations
        device_user_count = 0
        if self.G.has_node(device_id):
            device_user_count = sum(
                1 for n in self.G.neighbors(device_id) if self.G.nodes[n].get("type") == "user"
            )

        card_user_count = 0
        if self.G.has_node(card_id):
            card_user_count = sum(
                1 for n in self.G.neighbors(card_id) if self.G.nodes[n].get("type") == "user"
            )

        user_device_count = 0
        if self.G.has_node(sender_id):
            user_device_count = sum(
                1 for n in self.G.neighbors(sender_id) if self.G.nodes[n].get("type") == "device"
            )

        user_card_count = 0
        if self.G.has_node(sender_id):
            user_card_count = sum(
                1 for n in self.G.neighbors(sender_id) if self.G.nodes[n].get("type") == "card"
            )

        return {
            "device_user_count": device_user_count,
            "card_user_count": card_user_count,
            "user_device_count": user_device_count,
            "user_card_count": user_card_count,
            "is_device_shared": device_user_count > 1,
            "is_card_shared": card_user_count > 1,
        }

    def detect_suspicious_clusters(self) -> list[dict]:
        """
        Scans the graph network to detect fraud rings, shared card clusters, and device multi-use.
        """
        if self.use_neo4j and self.neo4j_driver:
            try:
                print(
                    "Fetching current graph nodes and relationships from Neo4j for cluster analysis..."
                )
                temp_G = nx.Graph()
                with self.neo4j_driver.session() as session:
                    nodes_res = session.run("MATCH (n) RETURN n.id as id, labels(n)[0] as type")
                    for record in nodes_res:
                        temp_G.add_node(record["id"], type=record["type"].lower())

                    rels_res = session.run("""
                        MATCH (n)-[r]->(m)
                        RETURN n.id as source, m.id as target,
                               r.transaction_id as transaction_id,
                               r.amount as amount,
                               r.is_fraud as is_fraud,
                               r.timestamp as timestamp
                        """)
                    for record in rels_res:
                        temp_G.add_edge(
                            record["source"],
                            record["target"],
                            transaction_id=record["transaction_id"],
                            amount=record["amount"],
                            is_fraud=record["is_fraud"],
                            timestamp=record["timestamp"],
                        )
                G_for_analysis = temp_G
            except Exception as e:
                print(
                    f"Failed to load Neo4j data for cluster scans: {e}. Falling back to NetworkX."
                )
                G_for_analysis = self.G
        else:
            G_for_analysis = self.G

        suspicious_clusters = []

        # 1. Card Sharing (Cards connected to > 1 user)
        for n, attrs in G_for_analysis.nodes(data=True):
            if attrs.get("type") == "card":
                user_neighbors = [
                    neighbor
                    for neighbor in G_for_analysis.neighbors(n)
                    if G_for_analysis.nodes[neighbor].get("type") == "user"
                ]
                if len(user_neighbors) > 1:
                    suspicious_clusters.append(
                        {
                            "cluster_type": "card_sharing",
                            "node_id": n,
                            "description": f"Credit card shared by {len(user_neighbors)} accounts.",
                            "severity": "CRITICAL" if len(user_neighbors) > 2 else "HIGH",
                            "connected_users": user_neighbors,
                        }
                    )

        # 2. Device Sharing (Devices connected to > 2 users)
        for n, attrs in G_for_analysis.nodes(data=True):
            if attrs.get("type") == "device":
                user_neighbors = [
                    neighbor
                    for neighbor in G_for_analysis.neighbors(n)
                    if G_for_analysis.nodes[neighbor].get("type") == "user"
                ]
                if len(user_neighbors) > 2:
                    suspicious_clusters.append(
                        {
                            "cluster_type": "device_sharing",
                            "node_id": n,
                            "description": f"Device shared by {len(user_neighbors)} accounts.",
                            "severity": "HIGH" if len(user_neighbors) > 4 else "MEDIUM",
                            "connected_users": user_neighbors,
                        }
                    )

        # 3. Connected Component Fraud Rings
        components = list(nx.connected_components(G_for_analysis))
        for i, comp in enumerate(components):
            if len(comp) < 4:
                continue

            subg = G_for_analysis.subgraph(comp)
            total_edges = subg.number_of_edges()
            fraud_edges = sum(1 for u, v, dat in subg.edges(data=True) if dat.get("is_fraud") == 1)

            fraud_ratio = (fraud_edges / total_edges) if total_edges > 0 else 0.0

            if fraud_ratio > 0.15 and len(comp) >= 5:
                users_in_comp = [
                    node for node in comp if G_for_analysis.nodes[node].get("type") == "user"
                ]
                suspicious_clusters.append(
                    {
                        "cluster_type": "fraud_ring",
                        "node_id": f"component_{i}",
                        "description": f"Fraud ring detected: {len(comp)} nodes with {fraud_ratio:.1%} fraud transaction rate.",
                        "severity": "CRITICAL" if fraud_ratio > 0.35 else "HIGH",
                        "connected_users": users_in_comp,
                    }
                )

        return suspicious_clusters

    def save_graph(self, file_path: str) -> None:
        """
        Serializes the graph instance to a file.
        """
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as f:
            pickle.dump(self.G, f)
        print(f"Graph serialized successfully to {file_path}")

    def load_graph(self, file_path: str) -> None:
        """
        Loads graph instance from a file.
        """
        if os.path.exists(file_path):
            with open(file_path, "rb") as f:
                self.G = pickle.load(f)
            print(f"Graph deserialized from {file_path} ({self.G.number_of_nodes()} nodes)")
        else:
            print(f"No existing graph file found at {file_path}. Initializing empty graph.")
            self.G = nx.Graph()
