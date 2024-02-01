from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    TG_TOKEN : str


    @property
    def DATABASE_URL(self):
        return f"mongodb+srv://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}/{self.DB_NAME}"

    # model_config = SettingsConfigDict(env_file='.env')
    model_config = SettingsConfigDict(env_file='.env')


settings = Settings()