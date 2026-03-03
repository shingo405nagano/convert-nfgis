from __future__ import annotations
import os


from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

global TEMPLATE_JSIMA_XML
TEMPLATE_JSIMA_XML = os.path.join(os.path.dirname(__file__), ".confs", "jsima.xml")


class JsimaXmlBuilder(object):
    """JSIMA XMLテンプレートを読み込み、dataset要素を編集して保存するビルダー。

    Example:
        >>> from jsima.xml_builder import JsimaXmlBuilder
        >>> builder = JsimaXmlBuilder("./jsima.xml")
        >>> builder.add_dataset_xml(
        ...     '<jsima:GenbaJoho><jsima:Name>test</jsima:Name></jsima:GenbaJoho>'
        ... )
        >>> builder.save("./output_jsima.xml")
        PosixPath('output_jsima.xml')
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
        self._dataset = self.root.find("jsima:dataset", self.NS)
        if self._dataset is None:
            raise ValueError("テンプレート内に <jsima:dataset> が見つかりません。")
        self.root.set("timeStamp", datetime.now().isoformat(timespec="seconds"))

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
        self._dataset.append(element)# type: ignore # 
        return element

    def add_dataset_xml(self, xml_fragment: str) -> None:
        """`<jsima:dataset>`配下にXML断片をそのまま追加する。

        Args:
            xml_fragment: 追加したいXML文字列。
        """
        wrapper = (
            f"<root xmlns:jsima=\"{self.NS['jsima']}\" "
            f"xmlns:jps=\"{self.NS['jps']}\" "
            f"xmlns:xsi=\"{self.NS['xsi']}\" "
            f"xmlns:xlink=\"{self.NS['xlink']}\">{xml_fragment}</root>"
        )
        parsed = ET.fromstring(wrapper)
        for child in list(parsed):
            self._dataset.append(deepcopy(child)) # type: ignore # 

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
