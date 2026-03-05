import os
import warnings
from typing import Any

import pydantic
import yaml

dirname = os.path.dirname(__file__)

global FIELD_YAML
with open(os.path.join(dirname, ".confs", "fields.yaml"), "r", encoding="utf-8") as f:
    FIELD_YAML = yaml.safe_load(f)

global URL_YAML
with open(os.path.join(dirname, ".confs", "urls.yaml"), "r", encoding="utf-8") as f:
    URL_YAML = yaml.safe_load(f)


class FieldInfo(pydantic.BaseModel):
    """属性情報を表すクラス

    Attributes:
        ja (str): 日本語の属性名
        en (str): 英語の属性名
        dtype (Any): データ型（string、geometry、integer、floatのいずれか）
        default (Any): デフォルト値
    """

    ja: str
    en: str
    dtype: Any
    default: Any

    @pydantic.field_validator("ja", "en", mode="before")
    def validate_string(cls, v):
        if not isinstance(v, str):
            raise ValueError("jaとenは文字列でなければなりません。")
        return v

    @pydantic.field_validator("dtype", mode="before")
    def validate_dtype(cls, v):
        if not isinstance(v, str):
            raise ValueError("dtypeは文字列でなければなりません。")
        v = v.lower()
        if v == "string":
            return str
        elif v == "geometry":
            return None
        elif v == "integer":
            return int
        elif v == "float":
            return float
        else:
            raise ValueError(
                "dtypeはstring、geometry、integer、floatのいずれかでなければなりません。"
            )

    def type_cast(self, value: Any) -> Any:
        """値をdtypeに基づいて型変換します。"""
        if value is None:
            return self.default
        if self.dtype is None:
            return value
        try:
            return self.dtype(value)
        except (ValueError, TypeError):
            warnings.warn(
                f"値 '{value}' を {self.dtype} に変換できません。デフォルト値を使用します。"
            )
            return self.default


class ConfigYaml(object):
    """YAMLファイルを読み込み、辞書形式でアクセスできるようにするクラスです。"""

    def __init__(self):
        self.field_yaml = FIELD_YAML
        self.url_yaml = URL_YAML

    @property
    def gs_shp_fields(self) -> dict[str, FieldInfo]:
        data = self.field_yaml["gs"]["address_shp"]
        return {key: FieldInfo(**value) for key, value in data.items()}

    @property
    def gs_forest_road_shp_fields(self) -> dict[str, FieldInfo]:
        data = self.field_yaml["gs"]["forest_road_shp"]
        return {key: FieldInfo(**value) for key, value in data.items()}

    @property
    def dissolved_office_fields(self) -> dict[str, FieldInfo]:
        data = self.field_yaml["dissolved"]["office"]
        return {key: FieldInfo(**value) for key, value in data.items()}

    @property
    def dissolved_branch_office_fields(self) -> dict[str, FieldInfo]:
        data = self.field_yaml["dissolved"]["branch_office"]
        return {key: FieldInfo(**value) for key, value in data.items()}

    @property
    def dissolved_locality_fields(self) -> dict[str, FieldInfo]:
        data = self.field_yaml["dissolved"]["locality"]
        return {key: FieldInfo(**value) for key, value in data.items()}

    @property
    def dissolved_main_address_fields(self) -> dict[str, FieldInfo]:
        data = self.field_yaml["dissolved"]["main_address"]
        return {key: FieldInfo(**value) for key, value in data.items()}

    @property
    def dissolved_protected_forest_fields(self) -> dict[str, FieldInfo]:
        data = self.field_yaml["dissolved"]["protected_forest"]
        return {key: FieldInfo(**value) for key, value in data.items()}

    def get_shp_zip_url(self, prefecture: str) -> str:
        """都道府県名から対応するShpファイルのZipダウンロードURLを取得します。

        Args:
            prefecture (str): 都道府県名

        Returns:
            str: 対応するShpファイルのZipダウンロードURL

        Raises:
            ValueError: 指定された都道府県に対応するURLが見つからない場合
        """
        url = self.url_yaml.get("GS_SHAPE_URLS", {}).get(prefecture)
        if url is None:
            raise ValueError(
                f"指定された都道府県 '{prefecture}' に対応するURLが見つかりません。"
            )
        return url
