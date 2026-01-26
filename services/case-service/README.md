# Case Service

## Description
This service is responsible for managing fraud cases that are flagged by the `Decision Engine`. It consumes `decision_events` from Kafka, creates cases for suspicious transactions (e.g., decisions like CHALLENGE or DENY), and provides an API for analysts to review, update, and label these cases. It also offers aggregated statistics on fraud cases.

## Technologies
- FastAPI
- aiokafka (for consuming Kafka messages)
- asyncpg (for PostgreSQL interaction)
- SQLAlchemy (ORM)
- PostgreSQL

## Features
- Consumes `decision_events` from Kafka to automatically create fraud cases.
- RESTful API for:
    - Listing all cases with filtering options (`GET /v1/cases`)
    - Retrieving a specific case with its latest label (`GET /v1/cases/{id}`)
    - Updating case details (`PUT /v1/cases/{id}`)
    - Labeling a case as fraud/legitimate (`POST /v1/cases/{id}/label`)
    - Getting overall fraud detection statistics (`GET /v1/stats`)
- Health check endpoint (`GET /health`)

## API Endpoints

### Health Check
- `GET /health`
  - Returns `{ "status": "healthy", "service": "Case Service" }`

### Cases
- `POST /v1/cases`
  - Creates a new fraud case (primarily used by Kafka consumer, but available for testing).
- `GET /v1/cases`
  - Query parameters: `status` (PENDING, REVIEWED), `user_id`
  - Returns a list of `Case` objects.
- `GET /v1/cases/{case_id}`
  - Returns a `Case` object including its latest `Label` if available.
- `PUT /v1/cases/{case_id}`
  - Updates fields of an existing `Case`.
- `POST /v1/cases/{case_id}/label`
  - Labels a case. Automatically sets case status to `REVIEWED`.

### Statistics
- `GET /v1/stats`
  - Returns aggregated statistics about cases, including total, pending, reviewed cases, fraud rate, and cases per day.

## Local Development & Setup (via Docker Compose)

The Case Service is designed to run as part of the larger `bank-security` system using Docker Compose.

1.  **Ensure prerequisites are met**: Docker, Docker Compose are installed. The main project's `docker-compose.yml` should be set up to include Kafka and PostgreSQL.
2.  **Add Case Service to `docker-compose.yml`**: You will need to add a service definition for the `case-service` in the main `docker-compose.yml` (or `docker-compose.override.yml`). An example entry would look like this:
    ```yaml
    case-service:
      build: ./services/case-service
      ports:
        - "8002:8000" # Map host port 8002 to container port 8000
      environment:
        # Example: DATABASE_URL should match your postgres service in docker-compose
        DATABASE_URL: "postgresql+asyncpg://postgres:postgres@postgres:5432/safeguard"
        KAFKA_BOOTSTRAP_SERVERS: "kafka:9092"
        KAFKA_TOPIC_DECISION_EVENTS: "decision_events"
      depends_on:
        - postgres
        - kafka
    ```
    (Note: The actual `DATABASE_URL` and `KAFKA_BOOTSTRAP_SERVERS` might need to be sourced from `config.py` later or environment variables based on project convention.)

3.  **Build and Run**: From the project root, run:
    ```bash
    docker-compose up --build case-service
    ```
    Or to start all services defined in your `docker-compose.yml`:
    ```bash
    make up
    ```

4.  **Access API Docs**: Once running, access the API documentation at `http://localhost:8002/docs` (if mapped to port 8002).

## Configuration
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql+asyncpg://user:password@host:port/dbname`).
- `KAFKA_BOOTSTRAP_SERVERS`: Comma-separated list of Kafka broker addresses (e.g., `kafka:9092`).
- `KAFKA_TOPIC_DECISION_EVENTS`: Kafka topic from which to consume decision events (default: `decision_events`).
- `KAFKA_CONSUMER_GROUP_ID`: Kafka consumer group ID for this service (default: `case-service-group`).
