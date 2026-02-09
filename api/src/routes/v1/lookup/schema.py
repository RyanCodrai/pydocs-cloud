from fastapi import HTTPException
from pydantic import BaseModel, model_validator
from src.routes.v1.webhooks.schema import normalize_package_name

SUPPORTED_ECOSYSTEMS = {"pypi", "npm"}


class EcosystemNotFoundError(HTTPException):
    def __init__(self, ecosystem: str):
        super().__init__(status_code=404, detail=f"Ecosystem '{ecosystem}' is not supported")


class SourceCodeNotFoundError(HTTPException):
    def __init__(self, package_name: str):
        super().__init__(status_code=404, detail=f"No source code repository found for '{package_name}'")


class LookupParams(BaseModel):
    ecosystem: str
    package_name: str

    @model_validator(mode="after")
    def normalize_name(self):
        if self.ecosystem == "pypi":
            self.package_name = normalize_package_name(self.package_name)
        return self


def get_lookup_params(ecosystem: str, package_name: str) -> LookupParams:
    if ecosystem not in SUPPORTED_ECOSYSTEMS:
        raise EcosystemNotFoundError(ecosystem)
    return LookupParams(ecosystem=ecosystem, package_name=package_name)


class PackageLookupResponse(BaseModel):
    github_url: str
