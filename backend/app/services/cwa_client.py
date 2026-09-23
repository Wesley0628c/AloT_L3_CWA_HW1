import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class CWAClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or settings.CWA_API_KEY

    async def fetch_json(self, url):
        if not self.api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=25, follow_redirects=True) as client:
                response = await client.get(url, params={'Authorization': self.api_key, 'format': 'JSON'})
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # URLs in exception strings can contain the CWA credential.
            logger.warning('CWA request failed (%s)', type(exc).__name__)
            return None

    async def _fetch_dataset(self, url):
        payload = await self.fetch_json(url)
        if not payload or str(payload.get('success')).lower() != 'true':
            return []
        records = payload.get('records', {})
        return records.get('Station', []) or records.get('location', [])

    async def fetch_automatic_stations(self):
        return await self._fetch_dataset(settings.CWA_DATASET_URL)

    async def fetch_bureau_stations(self):
        return await self._fetch_dataset(settings.CWA_BUREAU_DATASET_URL)

cwa_client = CWAClient()
