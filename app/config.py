from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	# App
	app_name: str = "BC_Cov19 API"
	debug: bool = False

	# Snowflake
	snowflake_account: str
	snowflake_user: str
	snowflake_password: str
	snowflake_warehouse: str
	snowflake_database: str
	snowflake_schema: str
	snowflake_role: str | None = None

	# MongoDB
	mongodb_uri: str = "mongodb://localhost:27017"
	mongodb_db: str = "bc_cov19"

	model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="BC_", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	return Settings()