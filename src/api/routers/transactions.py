import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import get_db_session, get_inference_engine, verify_api_key
from src.api.schemas.risk import FeatureExplanation, RiskAssessmentResponse
from src.api.schemas.transaction import TransactionCreate
from src.features.pipeline import preprocess_single_transaction

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post(
    "/score",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Assess transaction fraud risk",
    description="Receives transaction parameters, preprocesses features, executes ML models, computes SHAP values, and logs result.",
    dependencies=[Depends(verify_api_key)],
)
async def score_transaction(
    payload: TransactionCreate,
    db=Depends(get_db_session),
    inference_engine=Depends(get_inference_engine),
):
    """
    Real-time transaction fraud scoring.
    Fails validation if payload formatting is incorrect.
    """
    if inference_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML Inference Engine is not initialized.",
        )

    # 1. Generate unique Transaction ID and map input payload to dictionary
    tx_id = str(uuid.uuid4())
    raw_data = payload.model_dump()
    raw_data["transaction_id"] = tx_id
    raw_data["timestamp"] = raw_data["timestamp"].isoformat()

    # 2. Run real-time single-record preprocessing
    try:
        transaction_features = preprocess_single_transaction(raw_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Preprocessing error: {e}"
        ) from e

    # 3. Invoke ML scoring engine (defaults to xgboost, or dynamically selected)
    try:
        scoring_out = await inference_engine.score_transaction(
            transaction_features, model_type="xgboost", raw_tx_payload=raw_data, db=db
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inference scoring error: {e}",
        ) from e

    # 4. Map SHAP feature explanations
    explanations = []
    for expl in scoring_out.get("explanations", []):
        explanations.append(
            FeatureExplanation(
                feature_name=expl["feature_name"],
                shap_value=expl["shap_value"],
                impact_score=expl["impact_score"],
                direction=expl["direction"],
                description=expl["description"],
            )
        )

    # 5. Persist scored transaction and assessment records to Database
    from src.database.crud import create_risk_assessment, create_transaction

    try:
        await create_transaction(db, raw_data)

        assessment_id = str(uuid.uuid4())
        assessment_record = {
            "assessment_id": assessment_id,
            "transaction_id": tx_id,
            "risk_score": scoring_out["risk_score"],
            "recommendation": scoring_out["recommendation"],
            "model_version": scoring_out["model_version"],
            "shap_values": {expl.feature_name: expl.shap_value for expl in explanations},
            "assessed_at": datetime.now(UTC).replace(tzinfo=None),
        }
        await create_risk_assessment(db, assessment_record)
    except Exception as e:
        # Log error and continue (resilient serving)
        print(f"Database insertion failed: {e}")

    # 6. Dynamically update graph model in real time
    import os

    from src.features.graph_analysis import GraphFraudDetector

    graph_path = os.path.join("models/registry", "graph_fraud_model.pkl")
    if os.path.exists(graph_path):
        try:
            detector = GraphFraudDetector()
            detector.load_graph(graph_path)
            is_fraud_flag = 1 if scoring_out["recommendation"] == "BLOCK" else 0
            detector.add_transaction(raw_data, is_fraud=is_fraud_flag)
            detector.save_graph(graph_path)
        except Exception as e:
            print(f"Failed to dynamically append transaction to NetworkX graph: {e}")

    # 6.5 Broadcast WebSocket Alert
    import json

    from src.api.routers.websocket import manager as ws_manager

    alert_payload = {
        "transaction_id": tx_id,
        "sender_id": raw_data["sender_id"],
        "receiver_id": raw_data["receiver_id"],
        "amount": raw_data["amount"],
        "location_country": raw_data["location_country"],
        "location_city": raw_data["location_city"],
        "device_id": raw_data["device_id"],
        "ip_address": raw_data["ip_address"],
        "timestamp": raw_data["timestamp"],
        "risk_score": scoring_out["risk_score"],
        "risk_bucket": scoring_out["risk_bucket"],
        "recommendation": scoring_out["recommendation"],
        "decision_action": scoring_out.get("decision_action"),
        "decision_reasons": scoring_out.get("decision_reasons"),
    }
    try:
        await ws_manager.broadcast(json.dumps(alert_payload))
    except Exception as e:
        print(f"Failed to broadcast websocket alert: {e}")

    # 7. Return response
    return RiskAssessmentResponse(
        assessment_id=assessment_id,
        transaction_id=tx_id,
        risk_score=scoring_out["risk_score"],
        risk_bucket=scoring_out["risk_bucket"],
        sub_scores=scoring_out["sub_scores"],
        recommendation=scoring_out["recommendation"],
        model_version=scoring_out["model_version"],
        assessed_at=datetime.now(UTC).replace(tzinfo=None),
        explanations=explanations,
        decision_action=scoring_out.get("decision_action"),
        decision_reasons=scoring_out.get("decision_reasons"),
    )
