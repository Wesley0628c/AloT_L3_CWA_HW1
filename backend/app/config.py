import os

class Settings:
    CWA_API_KEY: str = os.getenv("CWA_API_KEY", "CWA-58A4BB8E-5E3A-41EF-98A9-753DD0F1EF89")
    CWA_DATASET_URL: str = os.getenv("CWA_DATASET_URL", "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001")
    CWA_BUREAU_DATASET_URL: str = os.getenv("CWA_BUREAU_DATASET_URL", "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001")
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "600"))

settings = Settings()
