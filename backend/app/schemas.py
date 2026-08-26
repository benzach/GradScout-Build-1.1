"""
Pydantic schemas — the API's request/response contract.

Deliberately separate from app/models.py (the SQLAlchemy/database
models), even though they overlap a lot in fields. This separation
matters: the database schema can evolve (new internal columns, renamed
fields) without automatically changing what the API exposes to a
frontend, and vice versa — the API contract can add computed/derived
fields that don't exist as real columns at all.
"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.locations import CANONICAL_LOCATIONS
from app.industries import CANONICAL_INDUSTRIES

MatchStatus = Literal["new", "seen", "applied", "dismissed"]


def _validate_canonical(value: list[str] | None, canonical: list[str], field_name: str, endpoint: str) -> list[str] | None:
    """
    Shared validation for any field whose values must come from a
    finite, backend-defined list (locations, industries — same pattern
    for any future one). Used by both the Create and Update schema for
    each such field, rather than duplicating the same field_validator
    body four times.
    """
    if value is None:
        return value
    invalid = set(value) - set(canonical)
    if invalid:
        raise ValueError(
            f"Invalid {field_name}(s): {sorted(invalid)}. "
            f"Must be one of the values returned by GET {endpoint}"
        )
    return value


# ---------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    # max_length=72 matches bcrypt's own truncation limit (see
    # app/security.py) — enforced here too so a too-long password is a
    # clean 422 instead of a silently-truncated hash.
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class AccountDeleteRequest(BaseModel):
    # Requiring the password again (not just a valid token) matters
    # specifically for a destructive, irreversible action — it's the
    # difference between "anyone with access to an already-open
    # browser tab can delete this account" and "only someone who
    # actually knows the password can".
    password: str = Field(min_length=1, max_length=72)


class UserSettingsUpdate(BaseModel):
    """PATCH /auth/me — currently just the email digest toggle, but a natural home for future account-level preferences too."""
    email_digest_enabled: bool | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    subscription_tier: str
    created_at: datetime
    email_digest_enabled: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------
# Search criteria
# ---------------------------------------------------------------------

class SearchCriteriaCreate(BaseModel):
    # Mandatory as of the Settings/naming update - with several saved
    # searches, "Untitled search" x3 in a list is genuinely hard to
    # tell apart (this was a real complaint, not a hypothetical one).
    # A bare `Field(min_length=1)` would still accept a string of only
    # spaces, so this uses a validator instead to reject that too.
    label: str
    keywords: list[str] = Field(default_factory=list)
    excluded_keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    salary_min: int | None = None
    contract_types: list[str] = Field(default_factory=list)
    sources_enabled: list[str] | None = None  # None = all sources
    active: bool = True

    @field_validator("label")
    @classmethod
    def _check_label(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("label cannot be blank - give this search a name")
        return stripped

    @field_validator("locations")
    @classmethod
    def _check_locations(cls, value):
        return _validate_canonical(value, CANONICAL_LOCATIONS, "location", "/locations")

    @field_validator("industries")
    @classmethod
    def _check_industries(cls, value):
        return _validate_canonical(value, CANONICAL_INDUSTRIES, "industry", "/industries")


class SearchCriteriaUpdate(BaseModel):
    """All fields optional — PATCH semantics, only provided fields change."""
    label: str | None = None
    keywords: list[str] | None = None
    excluded_keywords: list[str] | None = None
    locations: list[str] | None = None
    industries: list[str] | None = None
    salary_min: int | None = None
    contract_types: list[str] | None = None
    sources_enabled: list[str] | None = None
    active: bool | None = None

    @field_validator("label")
    @classmethod
    def _check_label(cls, value: str | None) -> str | None:
        # None here means "leave the label untouched" (PATCH semantics)
        # - but if the field IS included in the request, it can't be
        # used to blank out a name that's supposed to be mandatory.
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("label cannot be blank - give this search a name")
        return stripped

    @field_validator("locations")
    @classmethod
    def _check_locations(cls, value):
        return _validate_canonical(value, CANONICAL_LOCATIONS, "location", "/locations")

    @field_validator("industries")
    @classmethod
    def _check_industries(cls, value):
        return _validate_canonical(value, CANONICAL_INDUSTRIES, "industry", "/industries")


class SearchCriteriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    label: str | None
    keywords: list[str]
    excluded_keywords: list[str]
    locations: list[str]
    industries: list[str]
    salary_min: int | None
    contract_types: list[str]
    sources_enabled: list[str] | None
    active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------

class JobSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    site: str
    source_url: str
    scraped_at: datetime


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    company: str
    location: str | None
    location_category: str | None
    industry_category: str | None
    remote_type: str | None
    salary_text: str | None
    salary_min: int | None
    salary_max: int | None
    contract_type: str | None
    description: str | None
    posted_date: datetime | None
    first_seen_at: datetime
    is_expired: bool
    sources: list[JobSourceOut] = Field(default_factory=list)


# ---------------------------------------------------------------------
# Matches (a job matched against a user's criteria)
# ---------------------------------------------------------------------

class MatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job: JobOut
    status: MatchStatus
    is_favourite: bool
    matched_at: datetime
    notified_at: datetime | None


class MatchUpdate(BaseModel):
    """
    Partial update for a match — status and is_favourite can be set
    independently or together. At least one must be provided; an empty
    patch is almost certainly a frontend bug, not a legitimate no-op,
    so it's rejected rather than silently accepted.
    """

    status: MatchStatus | None = None
    is_favourite: bool | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self):
        if self.status is None and self.is_favourite is None:
            raise ValueError("Provide at least one of: status, is_favourite")
        return self


class PaginatedFeed(BaseModel):
    items: list[MatchOut]
    total: int
    limit: int
    offset: int


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionCreate(BaseModel):
    """
    Matches the browser's own PushSubscription.toJSON() shape exactly
    (endpoint + keys.p256dh + keys.auth) — the frontend sends this
    object directly with no reshaping, so this schema's field names and
    nesting aren't a free choice, they're dictated by the Push API spec.
    """

    endpoint: str
    keys: PushSubscriptionKeys


class PushSubscriptionDelete(BaseModel):
    endpoint: str
