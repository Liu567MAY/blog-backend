from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，统一从环境变量 / .env 读取，业务代码禁止硬编码连接信息。"""

    app_name: str = "AKiL Blog"
    app_env: str = "development"
    debug: bool = True
    # 开发占位默认值，实际部署必须通过 .env 或环境变量覆盖
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/akil_blog?charset=utf8mb4"

    # JWT 密钥必填，无默认值，强制从环境变量 / .env 读取
    jwt_secret_key: str
    jwt_expire_minutes: int = 1440

    # 仅供管理员初始化脚本非交互模式使用，可选
    admin_username: str | None = None
    admin_password: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
