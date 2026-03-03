from typing import Optional, Union  # noqa: F401

import pydantic  # noqa: F401
import shapely  # noqa: F401
from shapely.geometry.polygon import orient

from .enums import (  # noqa: F401
    JsimaChimokuEnum,
    JsimaJpsUuidRefEnum,
    JsimaPolyRotationEnum,
)
from .gm_point import JsimaGmPointModel, JsimaGmPointModels  # noqa: F401


def dissambly_poly_to_dict(geom, prefix="ply") -> dict[str, shapely.Polygon]:
    """
    Polygon / MultiPolygon を完全分解し、
    外周と穴をすべて独立した Polygon として
    {ID: Polygon} の辞書で返す。
    """
    result = {}
    counter = 1

    def add_poly(poly, tag):
        nonlocal counter
        key = f"{prefix}_{tag}_{counter}"
        result[key] = poly
        counter += 1

    def process_polygon(p):
        # 外周
        shell_poly = shapely.Polygon(p.exterior)
        add_poly(shell_poly, "shell")

        # 穴
        for i, interior in enumerate(p.interiors):
            hole_poly = shapely.Polygon(interior)
            add_poly(hole_poly, f"hole{i}")

    # MultiPolygon の場合
    if isinstance(geom, shapely.MultiPolygon):
        for idx, p in enumerate(geom.geoms):
            process_polygon(p)
        return result

    # Polygon の場合
    if isinstance(geom, shapely.Polygon):
        process_polygon(geom)
        return result

    return result


class JsimaGmPolygonModel(pydantic.BaseModel):
    """JSIMAの'GM_Curve','GM_Surface','Kakuchi','Chiban'を表すモデル

    使用するタグは'<jsima:GM_Curve>','<jsima:GM_Surface>','<jsima:Kakuchi>','<jsima:Chiban>'

    """

    model_config = pydantic.ConfigDict(arbitrary_types_allowed=True)

    polygon: Union[shapely.Polygon, shapely.MultiPolygon]
    start_idx: int = pydantic.Field(
        default=1, description="GM_Pointのインデックスの開始番号"
    )
    name: str = pydantic.Field(default="", description="地物の名称")
    chimoku: Optional[JsimaChimokuEnum] = pydantic.Field(
        default=None, description="地物の地目"
    )
    comment: Optional[str] = pydantic.Field(default=None, description="地物のコメント")

    @pydantic.field_validator("polygon", mode="before")
    @classmethod
    def validate_polygon(cls, value):
        """polygonがshapely.Polygonまたはshapely.MultiPolygonであることを検証する"""
        if not isinstance(value, (shapely.Polygon, shapely.MultiPolygon)):
            raise ValueError(
                "polygon must be a shapely.Polygon or shapely.MultiPolygon"
            )
        value = shapely.make_valid(value)
        if value.is_empty:
            raise ValueError("polygon is empty")
        # 右回りに統一
        value = orient(value, sign=-1.0)
        return value

    @pydantic.model_validator(mode="after")
    def _validate(self) -> "JsimaGmPolygonModel":
        """nameが空の場合、start_idxから自動生成する"""
        if self.chimoku is None:
            return self
        else:
            if self.chimoku not in JsimaChimokuEnum:
                raise ValueError(
                    f"chimoku must be one of {list(JsimaChimokuEnum.__members__.keys())}"
                )
        return self

    def dissambly(self) -> list["JsimaGmPolygonModel"]:
        """Polygon / MultiPolygon を完全分解し、外周と穴をすべて独立した JsimaGmPolygonModel として返す"""
        result = []
        disassembled = dissambly_poly_to_dict(self.polygon, prefix=self.name)
        for key, poly in disassembled.items():
            result.append(
                JsimaGmPolygonModel(
                    polygon=poly,
                    name=key,
                    chimoku=self.chimoku,
                    comment=self.comment,
                )
            )
        return result

    def area(self, digits: int = 7) -> float:
        """ポリゴンの面積を返す"""
        return round(self.polygon.area, digits)

    def to_point_model(
        self, start_idx: int, uuidref: JsimaJpsUuidRefEnum
    ) -> JsimaGmPointModels:
        """ポリゴンの頂点をGM_Pointモデルのリストに変換する。

        Polygon由来のSokuten名は空で扱うため、`names`は渡さない。
        """
        x_list = []
        y_list = []
        for x, y in self.polygon.exterior.coords:
            x_list.append(x)
            y_list.append(y)
        return JsimaGmPointModels(
            x_list=x_list,
            y_list=y_list,
            uuidref=uuidref,
            start_index=start_idx,
        )

    def exterior_vertex_count(self) -> int:
        """外周の頂点数（閉合点を除く）を返す。"""
        coords = list(self.polygon.exterior.coords)
        if len(coords) <= 1:
            return 0
        return len(coords) - 1

    def curve_ids(self, start_index: int = 1) -> list[str]:
        """外周辺数ぶんのGM_Curve ID配列を返す。"""
        size = self.exterior_vertex_count()
        return [f"crv{str(start_index + i).zfill(6)}" for i in range(size)]

    @staticmethod
    def surface_id(index: int) -> str:
        """GM_SurfaceのIDを返す。"""
        return f"srf{str(index).zfill(6)}"

    @staticmethod
    def boundary_id(index: int) -> str:
        """GM_Surface境界のIDを返す。"""
        return f"sfb{str(index).zfill(6)}"

    @staticmethod
    def ring_id(index: int) -> str:
        """外周リングのIDを返す。"""
        return f"rng{str(index).zfill(6)}"

    @staticmethod
    def kakuchi_id(index: int) -> str:
        """KakuchiのIDを返す。"""
        return f"simasrf{str(index).zfill(6)}"

    @staticmethod
    def chiban_id(index: int) -> str:
        """ChibanのIDを返す。"""
        return f"simacbn{str(index).zfill(6)}"

    def rotation(self) -> JsimaPolyRotationEnum:
        """外周リングの回転方向を返す。"""
        if self.polygon.exterior.is_ccw:
            return JsimaPolyRotationEnum.COUNTERCLOCKWISE
        return JsimaPolyRotationEnum.CLOCKWISE
