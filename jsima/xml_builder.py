from __future__ import annotations

import datetime
import os
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from typing import Any

from .enums import JsimaCoordinateSystemEnum, JsimaCrsEnum, JsimaJpsUuidRefEnum
from .gm_point import JsimaGmPointModel, JsimaGmPointModels

global TEMPLATE_JSIMA_XML
TEMPLATE_JSIMA_XML = os.path.join(os.path.dirname(__file__), ".confs", "jsima.xml")


class JsimaXmlBuilder(object):
    """JSIMA XMLテンプレートを読み込み、dataset要素を編集して保存するビルダー。

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
        """テンプレートXMLを読み込み、timeStampを現在時刻で初期化する。

        Args:
            template_path: 参照するJSIMA XMLテンプレートのパス。
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
        """`<jsima:dataset>`配下に単一要素を追加する。

        Args:
            local_name: 追加する要素のローカル名。
            text: 要素テキスト。
            attrib: 要素属性。
            namespace: `NS`に定義された名前空間プレフィックス。

        Returns:
            追加したElementオブジェクト。
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
        """`<jsima:dataset>`配下にXML断片をそのまま追加する。

        Args:
            xml_fragment: 追加したいXML文字列。
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
        """`<jsima:object>`配下に`<jps:GM_Point>`を1件追加する。"""
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
        """`JsimaGmPointModels`内の全`GM_Point`を`<jsima:object>`へ追加する。"""
        object_element = self._get_or_create_object_element()
        result: list[ET.Element] = []
        for point in points.values():
            result.append(self._append_gm_point_element(object_element, point))
        return result

    def add_sokuten(self, point: JsimaGmPointModel) -> ET.Element:
        """`<jsima:object>`配下に`<jsima:Sokuten>`を1件追加する。"""
        return self._append_sokuten_element(point)

    def add_sokutens(self, points: JsimaGmPointModels) -> list[ET.Element]:
        """`JsimaGmPointModels`内の全`Sokuten`を`<jsima:object>`へ追加する。"""
        result: list[ET.Element] = []
        for point in points.values():
            result.append(self._append_sokuten_element(point))
        return result

    def save(self, output_path: str = "./jsima.xml", encoding: str = "utf-8") -> Path:
        """現在のXML内容をファイルへ保存する。

        Args:
            output_path: 出力先パス。
            encoding: 出力時の文字コード。

        Returns:
            保存先のPathオブジェクト。
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
        """
        clone = ET.ElementTree(deepcopy(self.root))
        ET.indent(clone, space="  ")
        data = ET.tostring(clone.getroot(), encoding=encoding, xml_declaration=True)
        return data.decode(encoding)

    @classmethod
    def _register_namespaces(cls) -> None:
        """ElementTreeへ利用する名前空間を登録する。"""
        for prefix, uri in cls.NS.items():
            ET.register_namespace(prefix, uri)

    @staticmethod
    def _format_jsima_date(value: datetime.date | str | None) -> str:
        """JSIMA向けの日付文字列を `YYYY-M-D` 形式で返す。"""
        if value is None:
            current = datetime.date.today()
            return f"{current.year}-{current.month}-{current.day}"
        if isinstance(value, datetime.date):
            return f"{value.year}-{value.month}-{value.day}"
        return value

    def _get_or_create_object_element(self) -> ET.Element:
        """`<jsima:dataset>`直下の`<jsima:object>`を取得または作成する。"""
        object_element = self._dataset.find("jsima:object", self.NS)
        if object_element is None:
            object_element = ET.SubElement(
                self._dataset, f"{{{self.NS['jsima']}}}object"
            )
        return object_element

    def _append_gm_point_element(
        self, object_element: ET.Element, point: JsimaGmPointModel
    ) -> ET.Element:
        """`<jsima:object>`配下へ`<jps:GM_Point>`を追加する。"""
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
        """`<jsima:object>`配下へ`<jsima:Sokuten>`を追加する。"""
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

    @staticmethod
    def _coerce_enum_value(
        value: Any,
        enum_cls: type[JsimaCoordinateSystemEnum] | type[JsimaCrsEnum],
        arg_name: str,
    ) -> int:
        """Enumまたは整数を受け取り、Enum定義された整数値へ正規化する。"""
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
