"""
データの属性名やデータ型、デフォルト値などの情報を定義するモジュールです。
"""

from typing import Any

import pydantic

from .config import ConfigYaml, FieldInfo
from .enums import Language

global config_yaml
config_yaml = ConfigYaml()


class BaseFields(pydantic.BaseModel):
    """属性管理の基底クラス

    属性管理クラスは、データの属性名やデータ型、デフォルト値などの情報を定義するクラスです。
    """

    fields: dict[str, FieldInfo] = pydantic.Field(default_factory=dict)

    @pydantic.field_validator("fields", mode="before")
    def validate_fields(cls, v):
        if not isinstance(v, dict):
            raise ValueError("fieldsは辞書でなければなりません。")
        for key, value in v.items():
            if not isinstance(key, str):
                raise ValueError("fieldsのキーは文字列でなければなりません。")
            if not isinstance(value, FieldInfo):
                raise ValueError(
                    "fieldsの値はFieldInfoのインスタンスでなければなりません。"
                )
        return v

    def original_field_names(self) -> list[str]:
        """元の属性名のリストを返します。"""
        return list(self.fields.keys())

    def japanese_field_names(self) -> list[str]:
        """日本語の属性名のリストを返します。"""
        return [field_info.ja for field_info in self.fields.values()]

    def english_field_names(self) -> list[str]:
        """英語の属性名のリストを返します。"""
        return [field_info.en for field_info in self.fields.values()]

    def get_field_info(self, name: str, lang: Language = "en") -> FieldInfo:
        """元の属性名からFieldInfoを取得します。

        Args:
            name: 属性名（元の属性名、または日本語、英語のいずれか）
            lang: 属性名の言語（"original", "ja", "en"のいずれか）

        Returns:
            FieldInfo: 指定された属性名に対応するFieldInfoオブジェクト

        Raises:
            ValueError: 指定された属性名が見つからない場合、またはサポートされていない言語が指定された場合

        ## FieldInfo:
            - ja: 日本語の属性名
            - en: 英語の属性名
            - dtype: データ型（str, int, floatなど）
            - default: デフォルト値
        """
        if lang not in Language:
            raise ValueError(f"Unsupported language: {lang}")
        for original_field_name, field_info in self.fields.items():
            if lang == Language.ORGINAL and original_field_name == name:
                return field_info
            elif lang == Language.JA and field_info.ja == name:
                return field_info
            elif lang == Language.EN and field_info.en == name:
                return field_info
        raise ValueError(f"Field name '{name}' not found for language '{lang}'")

    def type_cast(self, value: Any, name: str, lang: Language = "en") -> Any:
        """元の属性名と値を受け取り、dtypeに基づいて型変換した値を返します

        Args:
            value: 変換する値
            name: 属性名（元の属性名、または日本語、英語のいずれか）
            lang: 属性名の言語（"original", "ja", "en"のいずれか）

        Returns:
            Any: 型変換後の値

        Raises:
            ValueError: 指定された属性名が見つからない場合、またはサポートされていない言語が指定された場合
        """
        field_info = self.get_field_info(name, lang)
        return field_info.type_cast(value)


class GsShpFields(BaseFields):
    """G空間センターで公開されている、国有林の林小班区画データの属性管理クラスです。"""

    def __init__(self):
        super().__init__(fields=config_yaml.gs_shp_fields)


class GsForestRoadFields(BaseFields):
    """G空間センターで公開されている、国有林の林道データの属性管理クラスです。"""

    def __init__(self):
        super().__init__(fields=config_yaml.gs_forest_road_shp_fields)


class DissolvedOfficeFields(BaseFields):
    """森林管理署担当区域データの属性管理クラスです。"""

    def __init__(self):
        super().__init__(fields=config_yaml.dissolved_office_fields)


class DissolvedBranchOfficeFields(BaseFields):
    """森林管理署支署担当区域データの属性管理クラスです。"""

    def __init__(self):
        super().__init__(fields=config_yaml.dissolved_branch_office_fields)


class DissolvedLocalityFields(BaseFields):
    """森林管理署地域区分データの属性管理クラスです。"""

    def __init__(self):
        super().__init__(fields=config_yaml.dissolved_locality_fields)


class DissolvedMainAddressFields(BaseFields):
    """森林管理署地域区分データの属性管理クラスです。"""

    def __init__(self):
        super().__init__(fields=config_yaml.dissolved_main_address_fields)


class DissolvedProtectedForestFields(BaseFields):
    """森林管理署地域区分データの属性管理クラスです。"""

    def __init__(self):
        super().__init__(fields=config_yaml.dissolved_protected_forest_fields)
