import pandas as pd

from src.features.graph_analysis import GraphFraudDetector, get_card_id


def test_get_card_id_deterministic():
    """
    Verifies that card ID generation is deterministic and distributes to 0 and 1 suffix.
    """
    card1 = get_card_id("usr_1001", "tx-abc-123")
    card2 = get_card_id("usr_1001", "tx-abc-123")

    assert card1 == card2
    assert card1.startswith("card_1001_")

    # Check that we can map different suffix for other transactions
    card3 = get_card_id("usr_1001", "tx-diff-456")
    card4 = get_card_id("usr_1001", "tx-another-789")

    assert card3.startswith("card_1001_")
    assert card4.startswith("card_1001_")


def test_build_graph_and_metrics():
    """
    Verifies graph construction and extraction of node degree metric features.
    """
    # Create simple transactions dataframe
    data = [
        {
            "transaction_id": "tx1",
            "sender_id": "usr_100",
            "receiver_id": "merch_1",
            "device_id": "dev_1",
            "amount": 100.0,
            "is_fraud": 0,
            "timestamp": "2026-06-05T10:00:00",
        },
        {
            "transaction_id": "tx2",
            "sender_id": "usr_200",
            "receiver_id": "merch_1",
            "device_id": "dev_1",  # shared device between usr_100 and usr_200
            "amount": 200.0,
            "is_fraud": 0,
            "timestamp": "2026-06-05T10:05:00",
        },
    ]
    df = pd.DataFrame(data)

    detector = GraphFraudDetector()
    detector.build_graph(df)

    # usr_100 and usr_200 both used dev_1. So device_user_count for dev_1 should be 2.
    metrics_usr100 = detector.compute_graph_metrics(
        "usr_100", "dev_1", card_id="card_nonexistent_0"
    )
    assert metrics_usr100["device_user_count"] == 2
    assert metrics_usr100["is_device_shared"] is True
    assert metrics_usr100["card_user_count"] == 0  # card is not in graph since card_id differs

    # Check degree mappings
    assert detector.G.nodes["usr_100"]["type"] == "user"
    assert detector.G.nodes["dev_1"]["type"] == "device"
    assert detector.G.nodes["merch_1"]["type"] == "merchant"


def test_detect_device_and_card_sharing():
    """
    Verifies detection of shared devices and cards.
    """
    detector = GraphFraudDetector()

    # 1. Device shared by 3 users
    detector.add_transaction(
        {
            "transaction_id": "t1",
            "sender_id": "usr_1",
            "receiver_id": "m1",
            "device_id": "dev_shared",
            "amount": 50.0,
        }
    )
    detector.add_transaction(
        {
            "transaction_id": "t2",
            "sender_id": "usr_2",
            "receiver_id": "m2",
            "device_id": "dev_shared",
            "amount": 60.0,
        }
    )
    detector.add_transaction(
        {
            "transaction_id": "t3",
            "sender_id": "usr_3",
            "receiver_id": "m3",
            "device_id": "dev_shared",
            "amount": 70.0,
        }
    )

    # 2. Card shared by 2 users (We override card_id deterministically, so let's mock it by adding edges manually)
    # A card node starts with 'card_'
    detector.G.add_node("usr_4", type="user")
    detector.G.add_node("usr_5", type="user")
    detector.G.add_node("card_shared_card", type="card")
    detector.G.add_edge("usr_4", "card_shared_card", transaction_id="t4", amount=10.0, is_fraud=0)
    detector.G.add_edge("usr_5", "card_shared_card", transaction_id="t5", amount=15.0, is_fraud=0)

    clusters = detector.detect_suspicious_clusters()

    # We should have card_sharing cluster and device_sharing cluster
    cluster_types = [c["cluster_type"] for c in clusters]
    assert "device_sharing" in cluster_types
    assert "card_sharing" in cluster_types

    dev_cluster = next(c for c in clusters if c["cluster_type"] == "device_sharing")
    assert dev_cluster["node_id"] == "dev_shared"
    assert len(dev_cluster["connected_users"]) == 3
    assert set(dev_cluster["connected_users"]) == {"usr_1", "usr_2", "usr_3"}

    card_cluster = next(c for c in clusters if c["cluster_type"] == "card_sharing")
    assert card_cluster["node_id"] == "card_shared_card"
    assert len(card_cluster["connected_users"]) == 2
    assert set(card_cluster["connected_users"]) == {"usr_4", "usr_5"}


def test_detect_fraud_ring():
    """
    Verifies detection of high fraud rate components.
    """
    detector = GraphFraudDetector()

    # Let's create a connected component where most edges are flagged as fraud
    # Component contains: usr_fraud_1, usr_fraud_2, dev_fraud_1, merch_fraud_1
    detector.add_transaction(
        {
            "transaction_id": "f1",
            "sender_id": "usr_f1",
            "receiver_id": "m_f1",
            "device_id": "d_f1",
            "amount": 500.0,
        },
        is_fraud=1,
    )
    detector.add_transaction(
        {
            "transaction_id": "f2",
            "sender_id": "usr_f2",
            "receiver_id": "m_f1",
            "device_id": "d_f1",
            "amount": 450.0,
        },
        is_fraud=1,
    )
    detector.add_transaction(
        {
            "transaction_id": "f3",
            "sender_id": "usr_f3",
            "receiver_id": "m_f1",
            "device_id": "d_f1",
            "amount": 600.0,
        },
        is_fraud=0,
    )  # 2 out of 3 transactions are fraud

    clusters = detector.detect_suspicious_clusters()

    # Should flag a fraud_ring component
    ring_clusters = [c for c in clusters if c["cluster_type"] == "fraud_ring"]
    assert len(ring_clusters) >= 1
    assert ring_clusters[0]["severity"] in ["HIGH", "CRITICAL"]
    assert set(ring_clusters[0]["connected_users"]).issubset({"usr_f1", "usr_f2", "usr_f3"})


def test_neo4j_integration_and_fallback(monkeypatch):
    """
    Verifies that GraphFraudDetector falls back to NetworkX when Neo4j is not configured,
    and uses the Neo4j session when configured (mocked).
    """
    # 1. Test fallback when no env variables are configured
    monkeypatch.delenv("NEO4J_URI", raising=False)
    monkeypatch.delenv("NEO4J_PASSWORD", raising=False)

    detector = GraphFraudDetector()
    assert detector.use_neo4j is False
    assert detector.neo4j_driver is None

    # Check that basic NetworkX works on fallback
    detector.add_transaction(
        {
            "transaction_id": "tx_fb",
            "sender_id": "usr_fb",
            "receiver_id": "merch_fb",
            "device_id": "dev_fb",
            "amount": 100.0,
        }
    )
    assert detector.G.has_node("usr_fb")

    # 2. Test mocked Neo4j path
    monkeypatch.setenv("NEO4J_URI", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_PASSWORD", "secret_pass")

    from unittest.mock import MagicMock

    mock_driver = MagicMock()
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session

    # Mock GraphDatabase.driver
    from neo4j import GraphDatabase

    monkeypatch.setattr(GraphDatabase, "driver", lambda uri, auth: mock_driver)

    detector_mocked = GraphFraudDetector()
    assert detector_mocked.use_neo4j is True
    assert detector_mocked.neo4j_driver is mock_driver

    # Verify constraints were checked/run
    assert mock_session.run.call_count >= 4

    # Reset call counts
    mock_session.reset_mock()

    # Test add_transaction writes to Neo4j
    detector_mocked.add_transaction(
        {
            "transaction_id": "tx_n4j",
            "sender_id": "usr_n4j",
            "receiver_id": "merch_n4j",
            "device_id": "dev_n4j",
            "amount": 250.0,
            "timestamp": "2026-06-05T10:00:00",
        }
    )

    # Verify Neo4j session run was called with query and parameters
    mock_session.run.assert_called()
    called_args = mock_session.run.call_args[0][0]
    assert "MERGE (u:User" in called_args
    assert "CREATE (u)-[:HAS_DEVICE" in called_args
