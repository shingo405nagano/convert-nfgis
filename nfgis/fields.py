"""
データの属性名やデータ型、デフォルト値などの情報を定義するモジュールです。
"""

from typing import Any

from .config import ConfigYaml, FieldInfo
from .enums import Language


class GsShpFields(object):
    """G空間センターで公開されている国有林小班区画の属性管理クラス

    G空間センターで公開されている国有林GISデータの属性名と、変換後の属性名の
    対応データを管理するクラスです。


    """

    def __init__(self):
        config = ConfigYaml()
        self.fields = config.gs_shp_fields

    @property
    def original_field_names(self) -> list[str]:
        """元の属性名のリストを返します。"""
        return list(self.fields.keys())

    @property
    def japanese_field_names(self) -> list[str]:
        """日本語の属性名のリストを返します。"""
        return [field_info.ja for field_info in self.fields.values()]

    @property
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
