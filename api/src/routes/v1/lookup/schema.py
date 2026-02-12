from pydantic import BaseModel, model_validator
from src.routes.v1.webhooks.schema import normalize_package_name


class LookupParams(BaseModel):
    ecosystem: str
    package_name: str

    @model_validator(mode="after")
    def normalize_name(self):
        if self.ecosystem == "pypi":
            self.package_name = normalize_package_name(self.package_name)
        return self


class PackageLookupResponse(BaseModel):
    github_url: str
