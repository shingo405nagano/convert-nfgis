"""
───────────────────────────────────────────────────────────────────────────────
MultiPolygonを含む、複数のポリゴンを例に、`JsimaXmlBuilder` を用いて JSIMA XML を構築する例。

───────────────────────────────────────────────────────────────────────────────
"""

import shapely

from jsima.enums import (
    JsimaChimokuEnum,
    JsimaCoordinateSystemEnum,
    JsimaCrsEnum,
    JsimaJpsUuidRefEnum,
)
from jsima.gm_polygon import JsimaGmPolygonModel, dissambly_poly_to_dict, replacement_xy
from jsima.xml_builder import JsimaXmlBuilder

# Testデータの作成
wkt_polys = [
    "MULTIPOLYGON Z (((-8790.926128249788 92291.06573485197 0, -8748.583309058538 92233.69801112477 0, -8655.702175474546 92317.0177889374 0, -8790.926128249788 92291.06573485197 0)), ((-8812.806774543065 92456.1450380336 0, -8888.8950372265 92332.50168438835 0, -8662.868176294867 92384.53256665185 0, -8812.806774543065 92456.1450380336 0)))",
    "MULTIPOLYGON Z (((-9040.885664626006 92610.68609576307 0, -9155.621185524677 92357.99478225614 0, -9029.958500584422 92355.262946802 0, -9040.885664626006 92610.68609576307 0)))",
    "MULTIPOLYGON Z (((-8730.826574249832 92095.74216570107 0, -8739.021988895516 91982.372565882 0, -8617.456983773089 91987.83612162028 0, -8636.579577875356 92087.54675109127 0, -8730.826574249832 92095.74216570107 0)), ((-9087.326282085412 92117.59653736549 0, -9096.669036995434 91997.34282141124 0, -8848.293891915344 92013.78821597269 0, -8814.146427763406 92016.52007806189 0, -8799.121564735253 92154.47587535853 0, -9088.692119934261 92146.28044005265 0, -9087.326282085412 92117.59653736549 0), (-9053.998399328177 92116.49742853221 0, -8838.73264822672 92109.40115691305 0, -8844.176186284243 92054.96535220712 0, -9027.609169345616 92044.54829057913 0, -9053.998399328177 92116.49742853221 0)))",
]
polys = [shapely.from_wkt(wkt) for wkt in wkt_polys]
names = [
    "事務所周辺",
    "柳川庁舎周辺",
    "篠田",
]
comments = [
    "青森市の事務所周辺のテストポリゴン",
    "青森市の柳川庁舎周辺のテストポリゴン",
    "青森市の篠田周辺のテストポリゴン",
]
chimoku_list = [
    JsimaChimokuEnum.SANRIN,
    JsimaChimokuEnum.HOANRIN,
    JsimaChimokuEnum.TANBO,
]
# JSIMA XML ビルダーのインスタンスを作成
jsima_builder = JsimaXmlBuilder()
lst_point_models = []
lst_poly_model = []
next_start_idx = 1
for poly, name, comment, chimoku in zip(polys, names, comments, chimoku_list):
    disd_poly_dict = dissambly_poly_to_dict(poly, prefix=name)
    for key, disd_poly in disd_poly_dict.items():
        poly_model = JsimaGmPolygonModel(
            polygon=replacement_xy(disd_poly),
            start_idx=next_start_idx,
            name="",  # インスタンス化の際に'name'を設定すると、GM_Pointモデルの'name'属性に反映される為、ここでは空文字を指定
            chimoku=chimoku,  # JsimaChimokuEnum.HOANRIN など、適切な地目を指定
            comment=comment,
        )
        point_model = poly_model.to_point_model(
            start_idx=next_start_idx, uuidref=JsimaJpsUuidRefEnum.JGD_2024_PL10
        )
        # ポリゴンモデルに名前を設定する
        poly_model.name = key
        # 次のポリゴンの開始インデックスを更新する
        next_start_idx = point_model.end_idx + 1
        # モデルをリストに追加する
        lst_poly_model.append(poly_model)
        lst_point_models.append(point_model)

# 現場情報を追加
jsima_builder.add_genba_joho(
    name="現場情報名のSIMAテスト",
    coordinate_system=JsimaCoordinateSystemEnum.JPR_10,
    crs=JsimaCrsEnum.JGD_2024,
    start="2026-3-3",
    end="2026-3-4",
)
for point_models in lst_point_models:
    jsima_builder.add_gm_points(point_models)

next_poly_index = 1
for poly_model, point_models in zip(lst_poly_model, lst_point_models):
    jsima_builder.add_polygon_objects(
        polygon_model=poly_model,
        point_models=point_models,
        index=next_poly_index,
    )
    next_poly_index += 1

for point_models in lst_point_models:
    jsima_builder.add_sokutens(point_models)

jsima_builder.save("./jsima_builded_multi_poly.xml")
