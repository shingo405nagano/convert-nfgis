import shapely

from jsima.enums import (
    JsimaChimokuEnum,
    JsimaCoordinateSystemEnum,
    JsimaCrsEnum,
    JsimaJpsUuidRefEnum,
)
from jsima.gm_polygon import JsimaGmPolygonModel
from jsima.xml_builder import JsimaXmlBuilder

"""
───────────────────────────────────────────────────────────────────────────────
1つのポリゴンを例に、`JsimaXmlBuilder` を用いて JSIMA XML を構築する例。

この例では、青森市の田沢森ダム周辺を模したテストポリゴンを作成し、以下の手順で 
XML を構築している。実務ではあまりないケースだが、単一のポリゴンを扱う場合の基本
的な流れを示すための例である。
───────────────────────────────────────────────────────────────────────────────
"""
poly = shapely.Polygon(
    [
        (93885.684, -16757.853),
        (93860.786, -16614.827),
        (93807.990, -16632.215),
        (93850.082, -16771.502),
    ]
)
name = "田沢森ダム"
comment = "青森市の田沢森ダム周辺のテストポリゴン"

# JSIMA XML ビルダーのインスタンスを作成
jsima_builder = JsimaXmlBuilder()
# 現場情報を追加
jsima_builder.add_genba_joho(
    name="現場情報名のSIMAテスト",
    coordinate_system=JsimaCoordinateSystemEnum.JPR_10,
    crs=JsimaCrsEnum.JGD_2024,
    start="2026-3-3",
    end="2026-3-4",
)
# ポリゴンモデルを作成
poly_model = JsimaGmPolygonModel(
    polygon=poly,
    start_idx=1,
    name="",  # インスタンス化の際に'name'を設定すると、GM_Pointモデルの'name'属性に反映される為、ここでは空文字を指定
    chimoku=JsimaChimokuEnum.SANRIN,  # JsimaChimokuEnum.HOANRIN など、適切な地目を指定
    comment=comment,
)

# ポリゴンモデルから GM_Point モデル群を生成
pnt_models = poly_model.to_point_model(1, JsimaJpsUuidRefEnum.JGD_2024_PL10)

# GM_Point モデル群を作成したら、`poly_model`に`name`を設定する
poly_model.name = name

"""
XMLの構築は、順序を守らないと、意図した表示にならない可能性がある為、以下の順序で行うことが推奨される。
1. GM_Point モデル群を追加
2. ポリゴンオブジェクトを追加
3. Sokuten を追加
4. XML を保存
"""
jsima_builder.add_gm_points(pnt_models)
jsima_builder.add_polygon_objects(
    polygon_model=poly_model,
    point_models=pnt_models,
    index=1,
)
jsima_builder.add_sokutens(pnt_models)
jsima_builder.save("./jsima_builded.xml")
