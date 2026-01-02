"""Type stubs for pydantic."""
from typing import Any, TypeVar, Type, ClassVar, Dict, Optional
from typing_extensions import dataclass_transform

_T = TypeVar("_T")

class FieldInfo:
    default: Any
    default_factory: Any

def Field(
    default: Any = ...,
    *,
    default_factory: Any = ...,
    alias: str | None = ...,
    title: str | None = ...,
    description: str | None = ...,
    ge: float | None = ...,
    le: float | None = ...,
    gt: float | None = ...,
    lt: float | None = ...,
    min_length: int | None = ...,
    max_length: int | None = ...,
    **kwargs: Any,
) -> Any: ...

@dataclass_transform(kw_only_default=True, field_specifiers=(Field,))
class BaseModel:
    model_config: ClassVar[Dict[str, Any]]

    def __init__(self, **data: Any) -> None: ...

    @classmethod
    def model_validate(cls: Type[_T], obj: Any) -> _T: ...

    def model_dump(self, *, mode: str = ..., **kwargs: Any) -> Dict[str, Any]: ...

def PrivateAttr(default: Any = ..., **kwargs: Any) -> Any: ...

def field_validator(
    *fields: str,
    mode: str = ...,
    check_fields: bool = ...,
) -> Any: ...
