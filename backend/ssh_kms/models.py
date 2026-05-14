import re
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KeyEntry(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    user: str = Field(min_length=1)
    hostname: Optional[str] = None
    hostname_regex: Optional[str] = None
    ssh_key: str = Field(alias="ssh-key", min_length=1)

    @model_validator(mode="after")
    def validate_matchers(self):
        """Validate exact user matching and exactly one host matcher."""
        hostname_matchers = [self.hostname, self.hostname_regex]

        if not self.user.strip():
            raise ValueError("user cannot be empty")
        if not self.ssh_key.strip():
            raise ValueError("ssh_key cannot be empty")
        for field_name in ("hostname", "hostname_regex"):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
        if sum(value is not None for value in hostname_matchers) != 1:
            raise ValueError("Provide exactly one of hostname or hostname_regex")
        if self.hostname_regex is not None:
            try:
                re.compile(self.hostname_regex.strip())
            except re.error as e:
                raise ValueError(f"hostname_regex is invalid: {e}") from e

        return self
