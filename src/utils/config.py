import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class SnowflakeConfig:
    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str
    schema: str


def load_config() -> SnowflakeConfig:
    load_dotenv()
    return SnowflakeConfig(
        account=os.getenv("SNOWFLAKE_ACCOUNT", ""),
        user=os.getenv("SNOWFLAKE_USER", ""),
        password=os.getenv("SNOWFLAKE_PASSWORD", ""),
        role=os.getenv("SNOWFLAKE_ROLE", ""),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "COVID_WH"),
        database=os.getenv("SNOWFLAKE_DATABASE", "COVID19_DATA"),
        schema=os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
    )
