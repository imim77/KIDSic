"""FOIHireloom's caller-owned async CKAN client, extended for JSON resources."""
import json
import math

import httpx
from pydantic import ValidationError

from KIDSic.dto.ckan import CkanPackage, CkanResource
from KIDSic.exceptions import CkanApiError, CkanHttpError, CkanResponseError, CkanTransportError
from KIDSic.integrations.interfaces.ckan import CkanClientInterface


class CkanClient(CkanClientInterface):
    def __init__(self, client: httpx.AsyncClient, base_url: str = 'https://data.gov.hr/ckan',
                 timeout: float = 15.0, max_bytes: int = 10 * 1024 * 1024):
        url = httpx.URL(base_url)
        if url.scheme not in {'http', 'https'} or not url.host or url.query or url.fragment:
            raise ValueError('CKAN base URL must be an HTTP(S) URL without query or fragment.')
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError('CKAN timeout must be positive and finite.')
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError('CKAN maximum response size must be a positive integer.')
        self._client = client
        self._url = f"{str(url).rstrip('/')}/api/3/action/package_show"
        self._timeout = timeout
        self._max_bytes = max_bytes

    async def _read_json(self, url: str, *, params=None):
        try:
            async with self._client.stream('GET', url, params=params, timeout=self._timeout,
                                           follow_redirects=True) as response:
                if not response.is_success:
                    raise CkanHttpError(response.status_code)
                content = bytearray()
                async for part in response.aiter_bytes(chunk_size=64 * 1024):
                    content.extend(part)
                    if len(content) > self._max_bytes:
                        raise CkanResponseError('CKAN response exceeds the configured size limit.')
        except httpx.RequestError as error:
            raise CkanTransportError('Could not reach the CKAN source.') from error
        try:
            return json.loads(content)
        except (ValueError, UnicodeError) as error:
            raise CkanResponseError('CKAN did not return valid JSON.') from error

    async def get_package(self, dataset_id: str) -> CkanPackage:
        if not dataset_id.strip():
            raise ValueError('CKAN dataset ID must not be blank.')
        payload = await self._read_json(self._url, params={'id': dataset_id})
        if not isinstance(payload, dict) or type(payload.get('success')) is not bool:
            raise CkanResponseError('CKAN response must contain a boolean success field.')
        if not payload['success']:
            raise CkanApiError('CKAN reported an unsuccessful package_show response.')
        try:
            return CkanPackage.model_validate(payload.get('result'))
        except ValidationError as error:
            raise CkanResponseError('CKAN returned invalid dataset metadata or resources.') from error

    async def download_records(self, resource: CkanResource) -> list[dict]:
        payload = await self._read_json(str(resource.url))
        if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
            raise CkanResponseError('The JSON resource must contain an array of objects.')
        return payload
