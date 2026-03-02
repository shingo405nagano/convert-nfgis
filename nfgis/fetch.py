"""URLからデータをダウンロードするためのモジュール

## Example:
```python
>>> from nfgis.fetch import GsShp
>>> gs_shp = GsShp(prefecture="青森県", caterory="address", endswith=".shp")
>>> print("office_names:", gs_shp.office_names)
office_names: ['三八上北', '下北', '東青', '津軽']
>>> office = "東青"
>>> _gdf = gs_shp.query_shp(office=office, columns=["署名称", "担当区"], file="小班区画", endswith=".shp")
>>> print("branch_office_names", _gdf["担当区"].unique())
branch_office_names ['広瀬後潟',   '宮田',   '大平',   '今別',  '大川平',   '三厩',   '龍飛',   '蟹田',  '八甲田', '平内',  '内真部', '北八甲田',    nan]
>>> gdf = gs_shp.read_file(office=office, file="小班区画", endswith=".shp")
>>> print("gdf.shape:", gdf.shape)
gdf.shape: (1234, 56)
# Zipファイル内のカテゴリーを全て読み込む
>>> category_data = gs_shp.read_category()
>>> print(category_data)
{
    "三八上北": {
        "署名称A": {
            "担当区X": ["国有林名1", "国有林名2", ...],
            "担当区Y": ["国有林名3", "国有林名4", ...],
            ...
        },
        "署名称B": {
            "担当区Z": ["国有林名5", "国有林名6", ...],
            ...
        },
        ...
    },
    "下北": {
        ...
    },
    "東青": {
        ...
    },
    "津軽": {
        ...
    },
}
"""

import io
import os
import re
import tempfile
import zipfile
from typing import Literal  # noqa: F401

import geopandas as gpd  # noqa: F401
import pyogrio
import requests

from .config import ConfigYaml, FieldInfo  # noqa: F401
from .enums import GsFile  # noqa: F401
from .fields import GsForestRoadFields, GsShpFields  # noqa: F401

global config_yaml
config_yaml = ConfigYaml()


class GsShp(object):
    """GS_shp_zipをダウンロード・展開してShapefileを取得するクラス"""

    def __init__(
        self,
        prefecture: str,
        caterory: Literal["address", "forest_road"] = "address",
        endswith: str = ".shp",
    ) -> None:
        # カテゴリに応じてフィールド情報の初期化とファイル名の取得
        if caterory.upper() == GsFile.ADDRESS.name:
            self.fields = GsShpFields()
            self.file_name = GsFile.ADDRESS.value
        elif caterory.upper() == GsFile.FOREST_ROAD.name:
            self.fields = GsForestRoadFields()
            self.file_name = GsFile.FOREST_ROAD.value
        else:
            raise ValueError(
                f"Invalid category: {caterory}. Must be '{GsFile.ADDRESS.name}' "
                f"or '{GsFile.FOREST_ROAD.name}'."
            )
        self.endswith = endswith
        self.url = config_yaml.get_shp_zip_url(prefecture)
        self.zip_file: zipfile.ZipFile | None = None
        self.file_names: list[str] = []
        self.temp_dir_obj: tempfile.TemporaryDirectory | None = None
        self.temp_dir_path: str | None = None
        self.extract_root_path: str | None = None
        self.fetch_and_extract()
        self.office_names = self.get_office_names()

    def fetch_and_extract(self) -> None:
        """指定された都道府県のZIPをダウンロードし、Tempディレクトリへ展開します。"""
        try:
            response = requests.get(self.url, timeout=120)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ValueError(
                f"URL '{self.url}' からデータをダウンロードできませんでした。エラー: {e}"
            )

        zip_buffer = io.BytesIO(response.content)
        self.zip_file = zipfile.ZipFile(zip_buffer)
        self.file_names = self.zip_file.namelist()
        self.temp_dir_obj = tempfile.TemporaryDirectory()
        self.temp_dir_path = self.temp_dir_obj.name
        self.zip_file.extractall(path=self.temp_dir_path)
        self.extract_root_path = self._extract_root_path()

    def _extract_root_path(self) -> str:
        """展開したデータセットのトップディレクトリパスを返します。"""
        if not self.temp_dir_path:
            raise ValueError("Tempディレクトリが初期化されていません。")

        top_dirs = []
        for name in self.file_names:
            parts = [part for part in name.split("/") if part]
            if parts:
                top_dirs.append(parts[0])

        if not top_dirs:
            return self.temp_dir_path

        top_dir = sorted(set(top_dirs))[0]
        return os.path.join(self.temp_dir_path, top_dir)

    @staticmethod
    def _normalize_office_name(name: str) -> str:
        result = re.sub(r"[0-9０-９]", "", name)
        result = result.replace("森林計画区", "")
        return result.strip()

    def get_office_names(self) -> list[str]:
        """展開したディレクトリから森林計画区名を抽出して返します。"""
        if not self.extract_root_path or not os.path.isdir(self.extract_root_path):
            return []

        office_names = []
        for entry in os.listdir(self.extract_root_path):
            full_path = os.path.join(self.extract_root_path, entry)
            if not os.path.isdir(full_path):
                continue

            normalized = self._normalize_office_name(entry)
            if normalized:
                office_names.append(normalized)

        return sorted(set(office_names))

    def select_file_path(self, office: str) -> str:
        """指定された森林計画区の対象Shapefileパスを返します。"""
        if not self.extract_root_path or not os.path.isdir(self.extract_root_path):
            raise ValueError("データ展開先ディレクトリが存在しません。")

        for entry in os.listdir(self.extract_root_path):
            office_dir = os.path.join(self.extract_root_path, entry)
            if not os.path.isdir(office_dir):
                continue

            normalized = self._normalize_office_name(entry)
            if office not in entry and office not in normalized:
                continue

            for root, _, files in os.walk(office_dir):
                for filename in files:
                    if self.file_name in filename and filename.endswith(self.endswith):
                        return os.path.join(root, filename)

        raise ValueError("指定された条件に対応するファイルが見つかりませんでした。")

    def read_shp(self, shp_path: str) -> gpd.GeoDataFrame:
        """指定されたShapefileパスをGeoDataFrameとして読み込みます。"""
        return pyogrio.read_dataframe(shp_path)

    def query_shp(
        self, office: str, columns: list[str] | None = None
    ) -> gpd.GeoDataFrame:
        """指定森林計画区のShapefileを読み込み、必要ならカラムを絞って返します。"""
        shp_path = self.select_file_path(office=office)
        return pyogrio.read_dataframe(shp_path, columns=columns)

    def select_file(self, office: str) -> str:
        """後方互換: select_file_path のエイリアス。"""
        return self.select_file_path(office=office)

    def read_file(self, office: str) -> gpd.GeoDataFrame:
        """後方互換: 指定森林計画区のShapefileをGeoDataFrameとして返します。"""
        shp_path = self.select_file_path(office=office)
        return self.read_shp(shp_path)

    def read_category(self) -> dict[str, dict[str, dict[str, list[str]]]]:
        """Zipファイル内の全てのShapefileを読み込み、署名称・担当区・国有林名で集約した辞書を返します。

        返り値の構造は以下の通りです:
        ```
        {
            "計画区1": {
                "署名称A": {
                    "担当区X": ["国有林名1", "国有林名2", ...],
                    "担当区Y": ["国有林名3", "国有林名4", ...],
                    ...
                },
                "署名称B": {
                    "担当区Z": ["国有林名5", "国有林名6", ...],
                    ...
                },
                ...
            },
            "計画区2": {
                ...
            },
            ...
        }
        ```
        """
        qcols = ["署名称", "担当区", "国有林名"]
        data = {}
        for office in self.office_names:
            _gdf = self.query_shp(office=office, columns=qcols)
            _gdf["計画区"] = office
            grouped = (
                _gdf.groupby(by=["計画区"] + qcols)
                .agg({"geometry": "count"})
                .reset_index()
                .sort_values(by=qcols)
            )
            for _, row in grouped.iterrows():
                keikaku = row["計画区"]
                off = row["署名称"]
                boff = row["担当区"]
                local = row["国有林名"]
                if keikaku not in data:
                    data[keikaku] = {}
                if off not in data[keikaku]:
                    data[keikaku][off] = {}
                if boff not in data[keikaku][off]:
                    data[keikaku][off][boff] = []
                data[keikaku][off][boff].append(local)
        return data

    def cleanup(self) -> None:
        """作成した一時ディレクトリを削除します。"""
        if self.temp_dir_obj is not None:
            self.temp_dir_obj.cleanup()
            self.temp_dir_obj = None
            self.temp_dir_path = None
            self.extract_root_path = None
