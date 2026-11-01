"""CKAN metadata contracts. Unknown catalogue fields are intentionally ignored."""
from pydantic import AnyHttpUrl, BaseModel, Field, StrictStr


class CkanResource(BaseModel):
    # data.gov.hr uses the slug 'djecji-vrtici' as the JSON resource ID.
    id: StrictStr = Field(min_length=1)
    url: AnyHttpUrl
    name: str | None = None
    description: str | None = None
    format: str | None = None
    state: str | None = 'active'
    last_modified: str | None = None


class CkanPackage(BaseModel):
    id: StrictStr = Field(min_length=1)
    name: StrictStr = Field(min_length=1)
    title: StrictStr = Field(min_length=1)
    resources: list[CkanResource]
    organization: dict | None = None
    license_id: str | None = None
    license_title: str | None = None
    license_url: str | None = None
    metadata_modified: str | None = None
