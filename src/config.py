from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict




class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    

    # ----------------------------------------------
    # API
    # ----------------------------------------------

    api_title: str = "Fraud Detection API"
    api_version: str = "1.0.0"
    api_description: str = (
        "Real-time fraud scoring and risk assessment API."
    )
    
    # ----------------------------------------------
    # API security
    # ----------------------------------------------

    environment: str = "development"

    api_key: str = "dev-api-key-change-me"

    allowed_hosts: str = "127.0.0.1,localhost"

    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    docs_enabled: bool = True

    # ----------------------------------------------
    # Model
    # ----------------------------------------------

    model_path: str = "models/fraud_xgb_model.json"
    preprocessor_path: str = (
        "models/fraud_preprocessor.joblib"
    )
    model_version: str = "1.1.0"

    # ----------------------------------------------
    # Databases
    # ----------------------------------------------

    state_db_path: str = "data/fraud_state.db"
    transaction_db_path: str = "data/transactions.db"
    review_db_path: str = "data/review_queue.db"
    paysim_review_db_path: str = "data/paysim_review_queue.db"
    paysim_transaction_db_path: str = "data/paysim_transactions.db"

    # ----------------------------------------------
    # Risk policy
    # ----------------------------------------------

    review_threshold: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
    )

    high_risk_threshold: float = Field(
        default=0.80,
        ge=0.0,
        le=1.0,
    )
    
    late_night_hours: str = "22,23,0,1,2,3"

    elevated_fraud_categories: str = (
        "shopping_net,misc_net,grocery_pos"
    )

    # ----------------------------------------------
    # Logging
    # ----------------------------------------------

    log_directory: str = "logs"
    log_file_name: str = "fraud_service.log"
    log_level: str = "INFO"

    # ----------------------------------------------
    # Cross-field validation
    # ----------------------------------------------
    

    @field_validator("high_risk_threshold")
    @classmethod
    def validate_high_risk_threshold(
        cls,
        value: float,
        info,
    ) -> float:

        review_threshold = info.data.get(
            "review_threshold"
        )

        if (
            review_threshold is not None
            and value <= review_threshold
        ):
            raise ValueError(
                "high_risk_threshold must be greater than "
                "review_threshold."
            )

        return value
    
    
    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.environment.lower() == "production":
            if self.api_key == "dev-api-key-change-me":
                raise ValueError(
                    "Production environment cannot use the default development API key."
                )

            if self.docs_enabled:
                raise ValueError(
                    "API docs must be disabled in production."
                )

        return self

    # ----------------------------------------------
    # Path helpers
    # ----------------------------------------------

    @property
    def model_file(self) -> Path:
        return Path(self.model_path)

    @property
    def preprocessor_file(self) -> Path:
        return Path(self.preprocessor_path)
    
    
    @property
    def allowed_host_list(self) -> list[str]:
        return [
            host.strip()
            for host in self.allowed_hosts.split(",")
            if host.strip()
        ]


    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]
        
    @property
    def late_night_hour_set(self) -> set[int]:
        return {
            int(hour.strip())
            for hour in self.late_night_hours.split(",")
            if hour.strip()
        }


    @property
    def elevated_fraud_category_set(self) -> set[str]:
        return {
            category.strip()
            for category in self.elevated_fraud_categories.split(",")
            if category.strip()
        }