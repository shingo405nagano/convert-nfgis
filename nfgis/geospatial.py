from typing import Optional

import geopandas as gpd

from .fields import DissolvedMainAddressFields, DissolvedProtectedForestFields  # noqa: F401
from .fetch import GsShp


class GsShpData(GsShp):
    """GsShpDataは、GsShpを継承して、Shapefileデータのクエリと後処理を行うクラスです。

    クエリの条件は、森林計画区、署名称、担当区、国有林名の4つで、これらを組み合
    わせてデータをフィルタリングします。クエリ結果のGeoDataFrameは、カラム名を英
    語に変換し、必要な型変換を行った上で返されます。また、同名林小班のディゾルブ
    処理も行われます。

    Example:
    ```python
    >>> from nfgis.geospatial import GsShpData
    >>> shp = GsShpData(prefecture="岡山県")
    >>> category_data = shp.read_category()
    >>> print(category_data)
    {
        "吉井川": {
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
        ...
    }
    >>> gdf = shp.query("吉井川", "岡山", "加茂", "岩渕")
    >>> gdf.to_crs(epsg=4326).to_file("test.geojson")
    ```
    """

    def __init__(
        self, prefecture: str, caterory: str = "address", endswith: str = ".shp"
    ):
        super().__init__(prefecture=prefecture, caterory=caterory, endswith=endswith)

    def query(
        self,
        plan_area: str,
        office: str,
        branch_office: str,
        locality: str,
        main_address: Optional[int] = None,
    ) -> gpd.GeoDataFrame:
        """指定された条件でShapefileをクエリして返します。"""
        # データ内の計画区名とファイル名としての計画区名が異なる場合がある為、ファイル名としての計画区名を取得する
        file = {key: val for val, key in self.plan_area2keikaku.items()}.get(plan_area)
        gdf = self.read_file(plan_area=file)
        qs = (
            f"計画区 == '{plan_area}'"
            f" and 署名称 == '{office}'"
            f" and 担当区 == '{branch_office}'"
            f" and 国有林名 == '{locality}'"
        )
        if isinstance(main_address, int):
            qs += f" and 林班主番 == '{main_address}'"
        filtered_gdf = gdf.query(qs)
        filtered_gdf = self._cast_geodataframe(filtered_gdf)
        filtered_gdf = self._after_processing(filtered_gdf)
        return filtered_gdf

    def _cast_geodataframe(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """必要に応じて、ジオデータフレームのカラムを適切な型に変換します。"""
        # カラム名を英語に変換
        original_names = self.fields.original_field_names()
        en_names = self.fields.english_field_names()
        renames = {orig: en for orig, en in zip(original_names, en_names)}
        gdf = gdf.rename(columns=renames)
        # データ型変換
        for en in en_names:
            field_info = self.fields.get_field_info(en, lang="en")
            if en not in gdf.columns:
                gdf[en] = field_info.default
            elif field_info.en == "geometry":
                continue
            gdf[en] = gdf[en].apply(lambda x: field_info.type_cast(x))
            gdf[en] = gdf[en].fillna(field_info.default)
            if field_info.dtype == str:
                gdf[en] = gdf[en].replace(
                    {"nan": field_info.default, "NaN": field_info.default}
                )
        return gdf[en_names].copy()

    def _after_processing(self, gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
        """GeoDataFrameの後処理を行います。

        - 同名林小班のディゾルブ
        """
        cols = gdf.columns.tolist()
        gdf["address"] = gdf["address"].apply(lambda s: s.replace("_林班_", ""))
        dissolved = gdf.dissolve(by=["office", "address"], as_index=False)
        return dissolved[cols].copy()

    def query_main_address(
        self,
        plan_area: str,
        office: str,
        branch_office: str,
        locality: str,
        main_address: Optional[int] = None,
    ) -> gpd.GeoDataFrame:
        sub_addrs = self.query(
            plan_area=plan_area,
            office=office,
            branch_office=branch_office,
            locality=locality,
            main_address=main_address,
        )
        fields = DissolvedMainAddressFields()
        agg_dict = {}
        agg_dict.update(fields.get_agg_method("office", lang="en"))
        agg_dict.update(fields.get_agg_method("branch_office", lang="en"))
        agg_dict.update(fields.get_agg_method("locality", lang="en"))
        main_addrs_gdf = sub_addrs.dissolve(
            by=["main_address"], as_index=False, aggfunc=agg_dict
        )
        return main_addrs_gdf


class GeoJsonData(GsShpData):
    """GeoJsonDataは、GsShpDataを継承して、クエリ結果をGeoJSON形式で出力するクラスです。"""

    def __init__(
        self, prefecture: str, caterory: str = "address", endswith: str = ".shp"
    ):
        super().__init__(prefecture=prefecture, caterory=caterory, endswith=endswith)

    def query_geojson(
        self, plan_area: str, office: str, branch_office: str, locality: str
    ) -> str:
        """指定された条件でShapefileをクエリし、GeoJSON形式の文字列で返します。"""
        gdf = self.query(
            plan_area=plan_area,
            office=office,
            branch_office=branch_office,
            locality=locality,
        )
        return gdf.to_json()
