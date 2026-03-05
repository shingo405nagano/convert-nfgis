from typing import Optional, Union  # noqa: F401

import pydantic  # noqa: F401
import shapely  # noqa: F401

from .enums import (  # noqa: F401
    JsimaChimokuEnum,
    JsimaJpsUuidRefEnum,
    JsimaPolyRotationEnum,
)
from .gm_point import JsimaGmPointModel, JsimaGmPointModels  # noqa: F401


def dissambly_poly_to_dict(geom, prefix="ply") -> dict[str, shapely.Polygon]:
    """Polygon/MultiPolygon を外周・内周単位へ分解して辞書化する。

    `Polygon` の場合は 1 つの外周ポリゴンと、各 interior ring（穴）を
    独立した `Polygon` として返す。`MultiPolygon` の場合は全ジオメトリに対して
    同様の処理を行う。

    Args:
        geom: 分解対象の `shapely.Polygon` または `shapely.MultiPolygon`。
        prefix: 生成キーの接頭辞。

    Returns:
        `{"<prefix>_shell_n": Polygon, "<prefix>_hole0_n": Polygon, ...}` 形式の辞書。
        非対応型の場合は空辞書。
    """
    result = {}
    counter = 1

    def add_poly(poly, tag):
        nonlocal counter
        key = f"{prefix}_{tag}_{counter}"
        # 右回りに統一する
        result[key] = shapely.orient_polygons(poly)
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


def replacement_xy(polygon: shapely.Polygon) -> shapely.Polygon:
    """ポリゴンの座標を (x, y) → (y, x) に入れ替える。

    JSIMA XML 生成の際、座標系の違いにより、(x, y) の順序で座標が必要な場合があります。
    この関数は、Shapely のポリゴンの座標を入れ替えるためのユーティリティです。

    完全に単一の`Shell`のみを対象として、Polygonの座標を入れ替えます。

    Args:
        polygon: 入れ替え対象の `shapely.Polygon`。

    Returns:
        座標が入れ替えられた新しい `shapely.Polygon`。
    """
    # 外周の座標を入れ替える
    if shapely.has_z(polygon):
        # 3D座標の場合、z座標も保持する
        return shapely.Polygon([(y, x, z) for x, y, z in polygon.exterior.coords])
    return shapely.Polygon([(y, x) for x, y in polygon.exterior.coords])


class JsimaGmPolygonModel(pydantic.BaseModel):
    """JSIMA 面地物生成に必要なポリゴン情報を保持するモデル。

    本モデルは入力ポリゴンを妥当化し、向きを統一した上で
    `GM_Curve`/`GM_Surface`/`Kakuchi`/`Chiban` の ID 生成や属性計算に利用する。
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
        """ポリゴン型・妥当性・向きを検証して正規化する。

        Args:
            value: `shapely.Polygon` または `shapely.MultiPolygon`。

        Returns:
            `shapely.make_valid` 適用済みかつ右回り（時計回り）に統一したジオメトリ。

        Raises:
            ValueError: 非対応型、または妥当化後に空ジオメトリとなった場合。
        """
        if not isinstance(value, (shapely.Polygon, shapely.MultiPolygon)):
            raise ValueError(
                "polygon must be a shapely.Polygon or shapely.MultiPolygon"
            )
        value = shapely.make_valid(value)
        if value.is_empty:
            raise ValueError("polygon is empty")
        return value

    @pydantic.model_validator(mode="after")
    def _validate(self) -> "JsimaGmPolygonModel":
        """補助属性の整合性を検証する。

        Returns:
            検証済みの自身インスタンス。

        Raises:
            ValueError: `chimoku` が `JsimaChimokuEnum` に属さない場合。
        """
        if self.chimoku is None:
            return self
        else:
            if self.chimoku not in JsimaChimokuEnum:
                raise ValueError(
                    f"chimoku must be one of {list(JsimaChimokuEnum.__members__.keys())}"
                )
        return self

    def area(self, digits: int = 7) -> float:
        """ポリゴン面積を指定桁で丸めて返す。

        Args:
            digits: 四捨五入する小数桁数。

        Returns:
            面積値。
        """
        return round(self.polygon.area, digits)

    def to_point_model(
        self, start_idx: int, uuidref: JsimaJpsUuidRefEnum
    ) -> JsimaGmPointModels:
        """外周座標を `JsimaGmPointModels` へ変換する。

        Polygon 由来の `Sokuten` 名は空文字で扱うため、`names` は渡さない。

        Args:
            start_idx: `GM_Point` 採番開始インデックス。
            uuidref: 生成点に付与する座標参照系 UUID。

        Returns:
            外周座標列を保持する `JsimaGmPointModels`。
        """
        x_list = []
        y_list = []
        if self.polygon.has_z:
            for x, y, _ in self.polygon.exterior.coords:
                x_list.append(x)
                y_list.append(y)
        else:
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
        """外周頂点数（終端の閉合点を除く）を返す。

        Returns:
            有効頂点数。座標が不足している場合は `0`。
        """
        coords = list(self.polygon.exterior.coords)
        if len(coords) <= 1:
            return 0
        return len(coords) - 1

    def curve_ids(self, start_index: int = 1) -> list[str]:
        """外周辺数に対応した `GM_Curve` ID 一覧を返す。

        Args:
            start_index: 連番開始値。

        Returns:
            `crv000001` 形式の ID 配列。
        """
        start = self.start_idx
        end = self.start_idx + self.exterior_vertex_count() - 1
        return [f"crv{str(i).zfill(6)}" for i in range(start, end + 1)]

    @staticmethod
    def surface_id(index: int) -> str:
        """`GM_Surface` 用 ID を返す。

        Args:
            index: 連番インデックス。

        Returns:
            `srf000001` 形式の ID。
        """
        return f"srf{str(index).zfill(6)}"

    @staticmethod
    def boundary_id(index: int) -> str:
        """`GM_Surface` 境界要素 ID を返す。

        Args:
            index: 連番インデックス。

        Returns:
            `sfb000001` 形式の ID。
        """
        return f"sfb{str(index).zfill(6)}"

    @staticmethod
    def ring_id(index: int) -> str:
        """外周リング ID を返す。

        Args:
            index: 連番インデックス。

        Returns:
            `rng000001` 形式の ID。
        """
        return f"rng{str(index).zfill(6)}"

    @staticmethod
    def kakuchi_id(index: int) -> str:
        """`Kakuchi` 要素 ID を返す。

        Args:
            index: 連番インデックス。

        Returns:
            `simasrf000001` 形式の ID。
        """
        return f"simasrf{str(index).zfill(6)}"

    @staticmethod
    def chiban_id(index: int) -> str:
        """`Chiban` 要素 ID を返す。

        Args:
            index: 連番インデックス。

        Returns:
            `simacbn000001` 形式の ID。
        """
        return f"simacbn{str(index).zfill(6)}"

    def rotation(self) -> JsimaPolyRotationEnum:
        """外周リングの回転方向を返す。

        Returns:
            外周が反時計回りなら `COUNTERCLOCKWISE`、それ以外は `CLOCKWISE`。
        """
        return JsimaPolyRotationEnum.CLOCKWISE
