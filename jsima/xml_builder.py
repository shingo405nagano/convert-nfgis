from __future__ import annotations

import datetime
import os
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from typing import Any

from .enums import (
    JsimaCoordinateSystemEnum,
    JsimaCrsEnum,
    JsimaJpsUuidRefEnum,
)
from .gm_point import JsimaGmPointModel, JsimaGmPointModels
from .gm_polygon import JsimaGmPolygonModel

global TEMPLATE_JSIMA_XML
TEMPLATE_JSIMA_XML = os.path.join(os.path.dirname(__file__), ".confs", "jsima.xml")


class JsimaXmlBuilder(object):
    """JSIMA XML テンプレートを読み込み、`dataset` 配下を構築するビルダー。

    テンプレート XML を基点に、現場情報・測点・ポリゴン関連オブジェクトを
    追記して最終的な JSIMA 形式 XML を生成する。

    Example:
        >>> from jsima.xml_builder import JsimaXmlBuilder
        >>> builder = JsimaXmlBuilder("./jsima.xml")
        >>> builder.add_genba_joho(
        ...     name="test-build-genba",
        ...     coordinate_system=JsimaCoordinateSystemEnum.JPR_10,
        ...     crs=JsimaCrsEnum.JGD_2024,
        ...     start="2026-3-3",
        ...     end="2026-3-4",
        ... )
        >>> builder.save("./output_jsima.xml")
    """

    NS = {
        "jsima": "http://www.jsima.or.jp/JSIMASchema/201206",
        "jps": "http://www.gsi.go.jp/GIS/jpgis/standardSchemas2.1_2009-05",
        "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        "xlink": "http://www.w3.org/1999/xlink",
    }

    def __init__(self, template_path: str = TEMPLATE_JSIMA_XML) -> None:
        """テンプレート XML を読み込み、ビルダーの初期状態を作成する。

        Args:
            template_path: 参照する JSIMA XML テンプレートのパス。

        Raises:
            ValueError: テンプレート内に `jsima:dataset` 要素が存在しない場合。
        """
        self.template_path = Path(template_path)
        self._register_namespaces()
        self.tree = ET.parse(self.template_path)
        self.root = self.tree.getroot()
        dataset = self.root.find("jsima:dataset", self.NS)
        if dataset is None:
            raise ValueError("テンプレート内に <jsima:dataset> が見つかりません。")
        self._dataset: ET.Element = dataset
        self.root.set(
            "timeStamp", datetime.datetime.now().isoformat(timespec="seconds")
        )

    def add_dataset_element(
        self,
        local_name: str,
        text: str | None = None,
        attrib: dict[str, str] | None = None,
        namespace: str = "jsima",
    ) -> ET.Element:
        """`<jsima:dataset>` 直下へ単一要素を追加する。

        Args:
            local_name: 追加する要素のローカル名。
            text: 要素テキスト。
            attrib: 要素属性。
            namespace: `NS`に定義された名前空間プレフィックス。

        Returns:
            追加したElementオブジェクト。

        Raises:
            ValueError: `namespace` が未定義プレフィックスの場合。
        """
        uri = self.NS.get(namespace)
        if uri is None:
            raise ValueError(f"未対応の名前空間: {namespace}")

        element = ET.Element(f"{{{uri}}}{local_name}", attrib=attrib or {})
        if text is not None:
            element.text = text
        self._dataset.append(element)  # type: ignore #
        return element

    def add_dataset_xml(self, xml_fragment: str) -> None:
        """`<jsima:dataset>` 配下に XML 断片を追加する。

        受け取った断片を名前空間付きの一時ルートでパースし、
        生成された子要素を `dataset` 直下へ順に追加する。

        Args:
            xml_fragment: 追加したいXML文字列。

        Raises:
            xml.etree.ElementTree.ParseError: `xml_fragment` が不正な XML の場合。
        """
        wrapper = (
            f'<root xmlns:jsima="{self.NS["jsima"]}" '
            f'xmlns:jps="{self.NS["jps"]}" '
            f'xmlns:xsi="{self.NS["xsi"]}" '
            f'xmlns:xlink="{self.NS["xlink"]}">{xml_fragment}</root>'
        )
        parsed = ET.fromstring(wrapper)
        for child in list(parsed):
            self._dataset.append(deepcopy(child))  # type: ignore #

    def add_genba_joho(
        self,
        name: str,
        coordinate_system: JsimaCoordinateSystemEnum | int,
        crs: JsimaCrsEnum | int,
        start: datetime.date | str | None = None,
        end: datetime.date | str | None = None,
    ) -> ET.Element:
        """`<jsima:dataset>`配下に現場情報 (`jsima:GenbaJoho`) を追加する。

        追加時に、現場情報の見出しコメントも合わせて追加する。

        Args:
            name: 現場名（必須）。
            coordinate_system: 座標系（必須）。`JsimaCoordinateSystemEnum` またはその値。
            crs: 測地系（必須）。`JsimaCrsEnum` またはその値。
            start: 開始日。`None` の場合は当日。
            end: 終了日。`None` の場合は当日。

        Returns:
            追加した `jsima:GenbaJoho` 要素。

        Raises:
            ValueError: `coordinate_system` または `crs` が列挙定義外の値の場合。

        ## JsimaCoordinateSystemEnum:
          - JPR_01 = 1
          - JPR_02 = 2
          ...
          - JPR_19 = 19
        ## JsimaCrsEnum:
          - JGD_2000 = 1
          - JGD_2011 = 2
          - JGD_2024 = 3

        """
        coordinate_system_value = self._coerce_enum_value(
            coordinate_system,
            JsimaCoordinateSystemEnum,
            "coordinate_system",
        )
        crs_value = self._coerce_enum_value(crs, JsimaCrsEnum, "crs")
        start_text = self._format_jsima_date(start)
        end_text = self._format_jsima_date(end)

        self._dataset.append(
            ET.Comment(
                " ===================================================================== "
            )
        )  # type: ignore[arg-type]
        self._dataset.append(ET.Comment("現場情報"))  # type: ignore[arg-type]

        genba = ET.SubElement(self._dataset, f"{{{self.NS['jsima']}}}GenbaJoho")
        ET.SubElement(genba, f"{{{self.NS['jsima']}}}Name").text = name
        ET.SubElement(genba, f"{{{self.NS['jsima']}}}CoordinateSystem").text = str(
            coordinate_system_value
        )
        ET.SubElement(genba, f"{{{self.NS['jsima']}}}Crs").text = str(crs_value)
        ET.SubElement(genba, f"{{{self.NS['jsima']}}}Start").text = start_text
        ET.SubElement(genba, f"{{{self.NS['jsima']}}}End").text = end_text
        return genba

    def add_gm_point(
        self,
        point_id: str,
        uuidref: JsimaJpsUuidRefEnum | str,
        x: float,
        y: float,
        number: int | None = None,
        name: str = "",
    ) -> ET.Element:
        """`<jsima:object>` 配下へ `GM_Point` を 1 件追加する。

        Args:
            point_id: 追加する `GM_Point` の ID（`pnt0000001` 形式）。
            uuidref: 座標参照系 UUID。
            x: X 座標。
            y: Y 座標。
            number: 点番号。`None` の場合は `point_id` から逆算。
            name: 対応する `Sokuten` 名称。

        Returns:
            追加された `jps:GM_Point` 要素。

        Raises:
            ValueError: `point_id` 形式が不正、または `point_id` と `number` が不整合な場合。
        """
        point_number = number
        if point_number is None:
            if not point_id.startswith("pnt"):
                raise ValueError("point_id は 'pnt0000001' 形式で指定してください。")
            try:
                point_number = int(point_id[3:])
            except ValueError as exc:
                raise ValueError(
                    "point_id は 'pnt0000001' 形式で指定してください。"
                ) from exc

        model = JsimaGmPointModel(
            x=x,
            y=y,
            uuidref=uuidref,
            number=point_number,
            name=name,
        )
        if model.id != point_id:
            raise ValueError("point_id と number の組み合わせが不正です。")
        object_element = self._get_or_create_object_element()
        return self._append_gm_point_element(object_element, model)

    def add_gm_points(self, points: JsimaGmPointModels) -> list[ET.Element]:
        """`JsimaGmPointModels` 内の全 `GM_Point` を追加する。

        Args:
            points: 追加対象の点モデル集合。

        Returns:
            追加した `jps:GM_Point` 要素の配列。
        """
        object_element = self._get_or_create_object_element()
        result: list[ET.Element] = []
        for point in points.values():
            result.append(self._append_gm_point_element(object_element, point))
        return result

    def add_sokuten(self, point: JsimaGmPointModel) -> ET.Element:
        """`<jsima:object>` 配下へ `Sokuten` を 1 件追加する。

        Args:
            point: 測点情報を保持した点モデル。

        Returns:
            追加された `jsima:Sokuten` 要素。
        """
        return self._append_sokuten_element(point)

    def add_sokutens(self, points: JsimaGmPointModels) -> list[ET.Element]:
        """`JsimaGmPointModels` 内の全 `Sokuten` を追加する。

        Args:
            points: 追加対象の点モデル集合。

        Returns:
            追加した `jsima:Sokuten` 要素の配列。
        """
        result: list[ET.Element] = []
        for point in points.values():
            result.append(self._append_sokuten_element(point))
        return result

    def add_polygon_objects(
        self,
        polygon_model: JsimaGmPolygonModel,
        point_models: JsimaGmPointModels,
        index: int,
    ) -> dict[str, ET.Element | list[ET.Element]]:
        """外周情報から面地物関連要素群をまとめて追加する。

        1 回の呼び出しで `GM_Curve` 群、`GM_Surface`、`Kakuchi`、`Chiban` を
        連動した ID で生成し、`<jsima:object>` 配下へ追加する。

        Args:
            polygon_model: 面地物の属性とジオメトリ情報。
            point_models: 外周頂点に対応する `GM_Point` 集合（閉合点を除く）。
            index: 各要素 ID 生成に使う基準インデックス。

        Returns:
            追加した要素を `curves/surface/kakuchi/chiban` キーでまとめた辞書。

        Raises:
            ValueError: 点数が外周頂点数と一致しない場合、または `chimoku` 未設定の場合。
        """
        object_element = self._get_or_create_object_element()
        points = point_models.values()
        required_points = polygon_model.exterior_vertex_count()
        if len(points) != required_points:
            raise ValueError(
                "point_modelsの点数はpolygon_modelの外周頂点数（閉合点除く）と一致する必要があります。"
            )
        if polygon_model.chimoku is None:
            raise ValueError("polygon_model.chimoku は必須です。")

        curve_elements = self._append_gm_curves(
            object_element=object_element,
            points=points,
            curve_ids=polygon_model.curve_ids(start_index=index),
        )
        surface_element = self._append_gm_surface(
            object_element=object_element,
            surface_id=polygon_model.surface_id(index),
            boundary_id=polygon_model.boundary_id(index),
            ring_id=polygon_model.ring_id(index),
            curve_ids=polygon_model.curve_ids(start_index=index),
        )
        kakuchi_element = self._append_kakuchi(
            object_element=object_element,
            kakuchi_id=polygon_model.kakuchi_id(index),
            number=index,
            name=polygon_model.name,
            surface_id=polygon_model.surface_id(index),
        )
        chiban_element = self._append_chiban(
            object_element=object_element,
            chiban_id=polygon_model.chiban_id(index),
            chimoku_value=int(polygon_model.chimoku.value),
            area_text=f"{polygon_model.area(7):.7f}",
            comment=polygon_model.comment,
            rotation_value=int(polygon_model.rotation().value),
            kakuchi_id=polygon_model.kakuchi_id(index),
        )

        return {
            "curves": curve_elements,
            "surface": surface_element,
            "kakuchi": kakuchi_element,
            "chiban": chiban_element,
        }

    def save(self, output_path: str = "./jsima.xml", encoding: str = "utf-8") -> Path:
        """現在のXML内容をファイルへ保存する。

        Args:
            output_path: 出力先パス。
            encoding: 出力時の文字コード。

        Returns:
            保存先のPathオブジェクト。

        Notes:
            出力前に `ET.indent` で 2 スペース整形を行う。
        """
        ET.indent(self.tree, space="  ")
        output = Path(output_path)
        self.tree.write(output, encoding=encoding, xml_declaration=True)
        return output

    def tostring(self, encoding: str = "utf-8") -> str:
        """現在のXML内容を整形済み文字列として取得する。

        Args:
            encoding: 文字列化時に使う文字コード。

        Returns:
            XML宣言を含むXML文字列。

        Notes:
            ルート要素をディープコピーした一時ツリーを整形し、
            元のツリー構造には影響を与えない。
        """
        clone = ET.ElementTree(deepcopy(self.root))
        ET.indent(clone, space="  ")
        data = ET.tostring(clone.getroot(), encoding=encoding, xml_declaration=True)
        return data.decode(encoding)

    @classmethod
    def _register_namespaces(cls) -> None:
        """`xml.etree.ElementTree` に利用する名前空間を登録する。

        `write()` 時に意図したプレフィックスで出力されるよう、
        クラス定義の `NS` マッピングを一括登録する。
        """
        for prefix, uri in cls.NS.items():
            ET.register_namespace(prefix, uri)

    @staticmethod
    def _format_jsima_date(value: datetime.date | str | None) -> str:
        """JSIMA 向けの日付文字列を `YYYY-M-D` 形式へ正規化する。

        Args:
            value: `date`、日付文字列、または `None`。

        Returns:
            `None` の場合は当日、`date` の場合は同形式へ変換、
            文字列の場合はそのまま返した値。
        """
        if value is None:
            current = datetime.date.today()
            return f"{current.year}-{current.month}-{current.day}"
        if isinstance(value, datetime.date):
            return f"{value.year}-{value.month}-{value.day}"
        return value

    def _get_or_create_object_element(self) -> ET.Element:
        """`<jsima:dataset>` 直下の `object` 要素を取得または新規作成する。

        Returns:
            既存または新規作成した `jsima:object` 要素。
        """
        object_element = self._dataset.find("jsima:object", self.NS)
        if object_element is None:
            object_element = ET.SubElement(
                self._dataset, f"{{{self.NS['jsima']}}}object"
            )
        return object_element

    def _append_gm_point_element(
        self, object_element: ET.Element, point: JsimaGmPointModel
    ) -> ET.Element:
        """`<jsima:object>` 配下へ `jps:GM_Point` 要素を追加する。

        初回追加時にはセクション見出しコメント（参照される座標）も付与する。

        Args:
            object_element: 追加先の `jsima:object` 要素。
            point: 追加する点情報。

        Returns:
            追加された `jps:GM_Point` 要素。
        """
        if object_element.find("jps:GM_Point", self.NS) is None:
            object_element.append(
                ET.Comment(
                    " ================================================================= "
                )
            )  # type: ignore[arg-type]
            object_element.append(ET.Comment("参照される座標"))  # type: ignore[arg-type]

        gm_point = ET.SubElement(
            object_element,
            f"{{{self.NS['jps']}}}GM_Point",
            attrib={"id": point.id},
        )
        ET.SubElement(
            gm_point, f"{{{self.NS['jps']}}}CRS", attrib={"uuidref": point.uuidref}
        )
        position = ET.SubElement(gm_point, f"{{{self.NS['jps']}}}position")
        ET.SubElement(
            position, f"{{{self.NS['jps']}}}coordinate"
        ).text = f"{point.x:.3f} {point.y:.3f}"
        return gm_point

    def _append_sokuten_element(self, point: JsimaGmPointModel) -> ET.Element:
        """`<jsima:object>` 配下へ `jsima:Sokuten` 要素を追加する。

        初回追加時にはセクション見出しコメント（測点）も付与する。

        Args:
            point: 追加する測点情報。

        Returns:
            追加された `jsima:Sokuten` 要素。
        """
        object_element = self._get_or_create_object_element()
        if object_element.find("jsima:Sokuten", self.NS) is None:
            object_element.append(
                ET.Comment(
                    " ================================================================= "
                )
            )  # type: ignore[arg-type]
            object_element.append(ET.Comment("測点"))  # type: ignore[arg-type]

        sokuten = ET.SubElement(
            object_element,
            f"{{{self.NS['jsima']}}}Sokuten",
            attrib={"id": point.sokuten_id},
        )
        ET.SubElement(sokuten, f"{{{self.NS['jsima']}}}Number").text = str(point.number)
        ET.SubElement(sokuten, f"{{{self.NS['jsima']}}}Name").text = point.name
        ET.SubElement(
            sokuten,
            f"{{{self.NS['jsima']}}}RefPoint",
            attrib={"idref": point.id},
        )
        return sokuten

    def _append_gm_curves(
        self,
        object_element: ET.Element,
        points: list[JsimaGmPointModel],
        curve_ids: list[str],
    ) -> list[ET.Element]:
        """外周辺に対応する `GM_Curve` 群を追加する。

        各曲線は `points[i] -> points[i+1]`（末尾は先頭へ閉合）として生成する。

        Args:
            object_element: 追加先の `jsima:object` 要素。
            points: 外周頂点に対応する点モデル配列。
            curve_ids: 生成する曲線 ID 配列。

        Returns:
            追加された `jps:GM_Curve` 要素配列。
        """
        self._append_section_comment_once(object_element, "jps:GM_Curve", "GM_Curve")
        result: list[ET.Element] = []
        size = len(points)
        for i, curve_id in enumerate(curve_ids):
            start_point = points[i].id
            end_point = points[(i + 1) % size].id
            curve = ET.SubElement(
                object_element,
                f"{{{self.NS['jps']}}}GM_Curve",
                attrib={"id": curve_id},
            )
            ET.SubElement(curve, f"{{{self.NS['jps']}}}CRS")
            ET.SubElement(
                curve, f"{{{self.NS['jps']}}}proxy", attrib={"idref": curve_id}
            )
            ET.SubElement(
                curve,
                f"{{{self.NS['jps']}}}proxy",
                attrib={"idref": f"_{curve_id}"},
            )
            ET.SubElement(curve, f"{{{self.NS['jps']}}}orientation").text = "+"
            ET.SubElement(
                curve, f"{{{self.NS['jps']}}}primitive", attrib={"idref": curve_id}
            )
            segment = ET.SubElement(curve, f"{{{self.NS['jps']}}}segment")
            line_string = ET.SubElement(segment, f"{{{self.NS['jps']}}}GM_LineString")
            ET.SubElement(
                line_string, f"{{{self.NS['jps']}}}interpolation"
            ).text = "linear"
            control_point = ET.SubElement(
                line_string, f"{{{self.NS['jps']}}}controlPoint"
            )

            start_column = ET.SubElement(control_point, f"{{{self.NS['jps']}}}column")
            start_indirect = ET.SubElement(
                start_column, f"{{{self.NS['jps']}}}indirect"
            )
            ET.SubElement(
                start_indirect,
                f"{{{self.NS['jps']}}}point",
                attrib={"idref": start_point},
            )

            end_column = ET.SubElement(control_point, f"{{{self.NS['jps']}}}column")
            end_indirect = ET.SubElement(end_column, f"{{{self.NS['jps']}}}indirect")
            ET.SubElement(
                end_indirect,
                f"{{{self.NS['jps']}}}point",
                attrib={"idref": end_point},
            )
            result.append(curve)
        return result

    def _append_gm_surface(
        self,
        object_element: ET.Element,
        surface_id: str,
        boundary_id: str,
        ring_id: str,
        curve_ids: list[str],
    ) -> ET.Element:
        """`GM_Curve` 群を参照する `GM_Surface` を追加する。

        Args:
            object_element: 追加先の `jsima:object` 要素。
            surface_id: `GM_Surface` の ID。
            boundary_id: 境界要素 ID。
            ring_id: 外周リング ID。
            curve_ids: 外周を構成する `GM_Curve` ID 配列。

        Returns:
            追加された `jps:GM_Surface` 要素。
        """
        self._append_section_comment_once(
            object_element, "jps:GM_Surface", "GM_Surface"
        )
        surface = ET.SubElement(
            object_element,
            f"{{{self.NS['jps']}}}GM_Surface",
            attrib={"id": surface_id},
        )
        ET.SubElement(surface, f"{{{self.NS['jps']}}}orientation").text = "+"
        ET.SubElement(
            surface, f"{{{self.NS['jps']}}}primitive", attrib={"idref": surface_id}
        )
        patch = ET.SubElement(surface, f"{{{self.NS['jps']}}}patch")
        polygon = ET.SubElement(patch, f"{{{self.NS['jps']}}}GM_Polygon")
        ET.SubElement(polygon, f"{{{self.NS['jps']}}}interpolation").text = "planar"
        boundary = ET.SubElement(
            polygon,
            f"{{{self.NS['jps']}}}boundary",
            attrib={"id": boundary_id},
        )
        ET.SubElement(
            boundary, f"{{{self.NS['jps']}}}element", attrib={"idref": ring_id}
        )
        exterior = ET.SubElement(
            boundary,
            f"{{{self.NS['jps']}}}exterior",
            attrib={"id": ring_id},
        )
        ET.SubElement(exterior, f"{{{self.NS['jps']}}}CRS")
        ET.SubElement(exterior, f"{{{self.NS['jps']}}}orientation").text = "+"
        ET.SubElement(
            exterior, f"{{{self.NS['jps']}}}primitive", attrib={"idref": ring_id}
        )
        for curve_id in curve_ids:
            ET.SubElement(
                exterior,
                f"{{{self.NS['jps']}}}generator",
                attrib={"idref": curve_id},
            )
        return surface

    def _append_kakuchi(
        self,
        object_element: ET.Element,
        kakuchi_id: str,
        number: int,
        name: str,
        surface_id: str,
    ) -> ET.Element:
        """`Kakuchi` 要素を追加する。

        Args:
            object_element: 追加先の `jsima:object` 要素。
            kakuchi_id: `Kakuchi` ID。
            number: 画地番号。
            name: 画地名称。
            surface_id: 参照する `GM_Surface` ID。

        Returns:
            追加された `jsima:Kakuchi` 要素。
        """
        self._append_section_comment_once(object_element, "jsima:Kakuchi", "画地")
        kakuchi = ET.SubElement(
            object_element,
            f"{{{self.NS['jsima']}}}Kakuchi",
            attrib={"id": kakuchi_id},
        )
        ET.SubElement(kakuchi, f"{{{self.NS['jsima']}}}Number").text = str(number)
        ET.SubElement(kakuchi, f"{{{self.NS['jsima']}}}Name").text = name
        ET.SubElement(
            kakuchi,
            f"{{{self.NS['jsima']}}}RefSurface",
            attrib={"idref": surface_id},
        )
        return kakuchi

    def _append_chiban(
        self,
        object_element: ET.Element,
        chiban_id: str,
        chimoku_value: int,
        area_text: str,
        comment: str | None,
        rotation_value: int,
        kakuchi_id: str,
    ) -> ET.Element:
        """`Chiban` 要素を追加する。

        Args:
            object_element: 追加先の `jsima:object` 要素。
            chiban_id: `Chiban` ID。
            chimoku_value: 地目コード値。
            area_text: 面積文字列（小数桁整形済み）。
            comment: 任意コメント。`None` の場合は出力しない。
            rotation_value: 回転方向コード値。
            kakuchi_id: 参照する `Kakuchi` ID。

        Returns:
            追加された `jsima:Chiban` 要素。
        """
        self._append_section_comment_once(object_element, "jsima:Chiban", "地番")
        chiban = ET.SubElement(
            object_element,
            f"{{{self.NS['jsima']}}}Chiban",
            attrib={"id": chiban_id},
        )
        ET.SubElement(chiban, f"{{{self.NS['jsima']}}}Chimoku").text = str(
            chimoku_value
        )
        ET.SubElement(chiban, f"{{{self.NS['jsima']}}}Area").text = area_text
        if comment is not None:
            ET.SubElement(chiban, f"{{{self.NS['jsima']}}}Comment").text = comment
        ET.SubElement(chiban, f"{{{self.NS['jsima']}}}Rotation").text = str(
            rotation_value
        )
        ET.SubElement(
            chiban,
            f"{{{self.NS['jsima']}}}RefKakuchi",
            attrib={"idref": kakuchi_id},
        )
        return chiban

    def _append_section_comment_once(
        self,
        object_element: ET.Element,
        element_xpath: str,
        title: str,
    ) -> None:
        """セクション要素が未作成のときだけ見出しコメントを挿入する。

        Args:
            object_element: コメント挿入先の `jsima:object` 要素。
            element_xpath: 対象要素の XPath（名前空間プレフィックス付き）。
            title: 見出しコメントの文言。
        """
        if object_element.find(element_xpath, self.NS) is not None:
            return
        object_element.append(
            ET.Comment(
                " ================================================================= "
            )
        )  # type: ignore[arg-type]
        object_element.append(ET.Comment(title))  # type: ignore[arg-type]

    @staticmethod
    def _coerce_enum_value(
        value: Any,
        enum_cls: type[JsimaCoordinateSystemEnum] | type[JsimaCrsEnum],
        arg_name: str,
    ) -> int:
        """列挙値または整数入力を列挙定義済み整数へ正規化する。

        Args:
            value: 列挙インスタンス、整数、または整数化可能な値。
            enum_cls: 検証対象の列挙型。
            arg_name: エラー文言に出力する引数名。

        Returns:
            列挙定義に存在する整数値。

        Raises:
            ValueError: `value` が `enum_cls` で許可されない値の場合。
        """
        if isinstance(value, enum_cls):
            return int(value.value)

        try:
            as_int = int(value)
            enum_cls(as_int)
            return as_int
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{arg_name} は {enum_cls.__name__} の有効な値を指定してください。"
            ) from exc
