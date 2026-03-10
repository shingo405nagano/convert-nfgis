import functools
import os
import warnings
from typing import Any, NamedTuple, Optional

import pydantic
import requests
import streamlit as st
import yaml

dirname = os.path.dirname(__file__)

global FIELD_YAML
with open(os.path.join(dirname, ".confs", "fields.yaml"), "r", encoding="utf-8") as f:
    FIELD_YAML = yaml.safe_load(f)

global URL_YAML
with open(os.path.join(dirname, ".confs", "urls.yaml"), "r", encoding="utf-8") as f:
    URL_YAML = yaml.safe_load(f)

global TILE_URLS
with open(os.path.join(dirname, ".confs", "tiles.yaml"), "r", encoding="utf-8") as f:
    TILE_URLS = yaml.safe_load(f)

global PROTECTED_FOREST_YAML
with open(os.path.join(dirname, ".confs", "protected.yaml"), "r", encoding="utf-8") as f:
    PROTECTED_FOREST_YAML = yaml.safe_load(f)


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
    agg: Optional[str] = pydantic.Field(default=None)

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
        self.protected = PROTECTED_FOREST_YAML

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


class StSessionKeys(NamedTuple):
    """Streamlitのセッションステートで使用するキーを定義するクラスです。"""

    PREFECTURE: str = "prefecture"
    SHP_URL: str = "shp_url"
    DOWNLOADED_DATA_DICT: str = "downloaded_data_dict"
    PLAN_AREA: str = "plan_area"
    OFFICE: str = "office"
    BRANCH_OFFICE: str = "branch_office"
    LOCALITY: str = "locality"
    MAIN_ADDRESS: str = "main_address"
    GEODATAFRAME: str = "geodataframe"
    CHANGE_SCOPE: str = "change_scope"
    LAST_EXTRACTED_QUERY: str = "last_extracted_query"

    def downloaded(self, prefecture: str) -> bool:
        """指定された都道府県のデータがダウンロードされているかを確認します。

        Args:
            prefecture (str): 都道府県名

        Returns:
            bool: データがダウンロードされている場合はTrue、そうでない場合はFalse
        """
        if self.DOWNLOADED_DATA_DICT not in st.session_state:
            return False
        downloaded_data_dict = st.session_state[self.DOWNLOADED_DATA_DICT]
        return (
            prefecture in downloaded_data_dict
            and downloaded_data_dict[prefecture] is not None
        )


class TileUrl(pydantic.BaseModel):
    """地図タイルのURLを表すクラスです。
    Attributes:
        name (str): タイルの名前
        url (str): タイルのURLテンプレート
        attr (str): タイルの著作権表示
    """

    name: str
    url: str
    attr: str


class TileUrls(object):
    def __init__(self):
        self.__tile_urls = {key: TileUrl(**data) for key, data in TILE_URLS.items()}

    @functools.cached_property
    def tile_names(self) -> list[str]:
        """利用可能なタイルの名前のリストを返します。"""
        return [tile.name for tile in self.__tile_urls.values()]

    def get_tile_url(self, name: str) -> TileUrl:
        """タイルの名前から対応するTileUrlオブジェクトを取得します。
        Args:
            name (str): タイルの名前
        Returns:
            TileUrl: 対応するTileUrlオブジェクト
        Raises:
            ValueError: 指定されたタイルの名前に対応するTileUrlが見つからない場合
        """
        for tile in self.__tile_urls.values():
            if tile.name == name:
                return tile
        raise ValueError(
            f"指定されたタイルの名前 '{name}' に対応するTileUrlが見つかりません。"
        )
