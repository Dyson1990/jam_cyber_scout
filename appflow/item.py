"""Item 数据单元
===============
App 间传输的数据单元基类。子类用 dataclass 字段注解声明结构，
构造 / 反序列化时严格校验，非法输入抛 ItemValidationError。
"""

import json
from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, Union, get_args, get_origin, get_type_hints


class ItemValidationError(ValueError):
    """Item 校验失败，携带具体原因。"""


def _check(name: str, value: Any, typ: Any) -> None:
    """递归严格校验 value 是否符合 typ。"""
    origin = get_origin(typ)

    if origin is Union:  # Optional[T] / Union[...]
        for arg in get_args(typ):
            try:
                _check(name, value, arg)
                return
            except ItemValidationError:
                continue
        raise ItemValidationError(f"字段 {name} 类型不符: 期望 {typ}, 得到 {type(value).__name__}")

    if origin is list:
        if not isinstance(value, list):
            raise ItemValidationError(f"字段 {name} 应为 list, 得到 {type(value).__name__}")
        inner = get_args(typ)
        if inner:
            for i, v in enumerate(value):
                _check(f"{name}[{i}]", v, inner[0])
        return

    if origin is dict:
        if not isinstance(value, dict):
            raise ItemValidationError(f"字段 {name} 应为 dict, 得到 {type(value).__name__}")
        args = get_args(typ)
        if len(args) == 2:
            for k, v in value.items():
                _check(f"{name}.{k}", v, args[1])
        return

    # 基本类型 / Any
    if isinstance(typ, type) and not isinstance(value, typ):
        raise ItemValidationError(f"字段 {name} 类型不符: 期望 {typ.__name__}, 得到 {type(value).__name__}")


@dataclass
class Item:
    """App 间传输的数据单元基类。

    基本约束（所有 Item 共用）：
    - loads() 只接受合法 JSON 且为对象(dict)，否则抛 ItemValidationError
    - 声明字段严格类型校验：必填缺省 / 类型不符 → ItemValidationError
    - 未知字段：默认报错；子类设 allow_unknown = True 时静默丢弃

    子类用 dataclass 字段注解声明「特定约束」：无默认值 = 必填，有默认值 = 可选。
    """

    allow_unknown: ClassVar[bool] = False

    def __post_init__(self) -> None:
        hints = get_type_hints(self.__class__)
        for f in fields(self):
            _check(f.name, getattr(self, f.name), hints.get(f.name, Any))

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def loads(cls, line: str) -> "Item":
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as e:
            raise ItemValidationError(f"非法 JSON: {e}") from e
        if not isinstance(raw, dict):
            raise ItemValidationError(f"Item 必须是 JSON 对象，得到 {type(raw).__name__}")
        known = {f.name for f in fields(cls)}
        if not cls.allow_unknown:
            unknown = set(raw) - known
            if unknown:
                raise ItemValidationError(f"未知字段: {sorted(unknown)}")
        try:
            return cls(**{k: v for k, v in raw.items() if k in known})
        except ItemValidationError:
            raise
        except TypeError as e:  # dataclass: 缺必填字段
            raise ItemValidationError(f"字段校验失败: {e}") from e


# ---- 框架级公共 Item（report/feishu 尾巴使用） ----

@dataclass
class RunSummaryItem(Item):
    """一次 job 运行的结果摘要，由 main.py 生成，喂给 report。"""
    job: str
    status: str
    count: int = 0
    stages: list[dict] = field(default_factory=list)


@dataclass
class ReportItem(Item):
    """report 输出，交给 feishu 发送。"""
    title: str
    content: str = ""
