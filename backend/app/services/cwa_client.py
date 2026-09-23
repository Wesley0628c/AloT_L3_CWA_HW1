import logging
import ssl
import json
import urllib.request
import urllib.error
from typing import List, Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

class CWAClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.CWA_API_KEY
        self.dataset_url = settings.CWA_DATASET_URL
        self.bureau_url = settings.CWA_BUREAU_DATASET_URL

    async def fetch_automatic_stations(self) -> List[Dict[str, Any]]:
        """
        Fetch automatic weather station dataset (O-A0001-001)
        """
        return await self._fetch_dataset(self.dataset_url)

    async def fetch_bureau_stations(self) -> List[Dict[str, Any]]:
        """
        Fetch bureau weather station dataset (O-A0003-001)
        """
        return await self._fetch_dataset(self.bureau_url)

    async def _fetch_dataset(self, url: str) -> List[Dict[str, Any]]:
        full_url = f"{url}?Authorization={self.api_key}"

        # Try httpx first if available, fallback to urllib.request
        try:
            import httpx
            async with httpx.AsyncClient(verify=False, timeout=15.0) as client:
                resp = await client.get(url, params={"Authorization": self.api_key})
                resp.raise_for_status()
                data = resp.json()
                if data.get("success") == "true" and "records" in data:
                    records = data["records"]
                    return records.get("Station", []) or records.get("location", [])
        except ImportError:
            # Fallback to standard library urllib with unverified SSL context for Windows
            try:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

                req = urllib.request.Request(full_url, headers={"User-Agent": "CWA-Weather-Client/1.0"})
                with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
                    payload = json.loads(response.read().decode('utf-8'))
                    if payload.get("success") == "true" and "records" in payload:
                        records = payload["records"]
                        return records.get("Station", []) or records.get("location", [])
            except Exception as e:
                logger.error(f"urllib fetch error for {url}: {e}")
        except Exception as e:
            logger.error(f"httpx fetch error for {url}: {e}")

        return []

cwa_client = CWAClient()
