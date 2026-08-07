import argparse
import asyncio
import os

from dotenv import load_dotenv

from src.database import connection as db_conn
from src.database.models import (
    Base,
)
from src.models.synthetic_engine import SyntheticFraudEngine


async def main():
    parser = argparse.ArgumentParser(description="Synthetic Fraud Scenario Engine Seeder CLI")
    parser.add_argument(
        "--transactions",
        type=int,
        default=1000,
        help="Number of normal transactions to generate (default: 1000)",
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="all",
        choices=["all", "ato", "card_testing", "velocity", "spoofing", "travel", "merchant_abuse"],
        help="Specific fraud scenario to generate (default: all)",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Optional file path to export the generated dataset as CSV",
    )
    parser.add_argument(
        "--db",
        action="store_true",
        help="If set, seeds the generated dataset into the SQL database",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="If set, drops and recreates database tables before seeding (ignored if not seeding)",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)"
    )

    args = parser.parse_args()

    print(f"Initializing Synthetic Fraud Engine with seed={args.seed}...")
    engine = SyntheticFraudEngine(seed=args.seed)

    # Calculate count params based on scenario selection
    num_ato = 5 if args.scenario in ["all", "ato"] else 0
    num_card_testing = 5 if args.scenario in ["all", "card_testing"] else 0
    num_velocity = 5 if args.scenario in ["all", "velocity"] else 0
    num_spoofing = 5 if args.scenario in ["all", "spoofing"] else 0
    num_travel = 5 if args.scenario in ["all", "travel"] else 0
    num_merchant_abuse = 5 if args.scenario in ["all", "merchant_abuse"] else 0

    print("Generating synthetic datasets...")
    df = engine.build_dataset(
        num_normal=args.transactions,
        num_ato=num_ato,
        num_card_testing=num_card_testing,
        num_velocity=num_velocity,
        num_device_spoofing=num_spoofing,
        num_location_anomaly=num_travel,
        num_merchant_abuse=num_merchant_abuse,
    )

    print(f"Successfully generated {len(df)} transactions.")
    print(df["scenario_type"].value_counts())

    # Export to CSV if requested
    if args.csv:
        csv_path = os.path.abspath(args.csv)
        print(f"Exporting dataset to CSV: {csv_path}...")
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False)
        print("CSV export complete.")

    # Seed to Database if requested
    if args.db:
        load_dotenv()
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            os.makedirs("data", exist_ok=True)
            database_url = "sqlite+aiosqlite:///data/fraud_detection_db.db"

        print(f"Connecting to database: {database_url}...")
        db_conn.initialize_db(database_url)

        if args.reset:
            print("Resetting database tables (dropping and recreating)...")
            async with db_conn._engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            print("Database tables reset successfully.")

        print("Seeding database transaction tables...")
        async with db_conn._session_factory() as session:
            await engine.seed_database(session, df)

        await db_conn.close_db()
        print("Database seeding completed successfully.")


if __name__ == "__main__":
    asyncio.run(main())
