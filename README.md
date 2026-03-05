# geo-to-jsima

`shapely` のジオメトリオブジェクト（`Polygon` / `MultiPolygon`）を、SIMA（JPGIS版）XML 形式に変換するためのライブラリです。  
本リポジトリでは、SIMA XML 生成用のビルダークラスと、複数ポリゴンを扱う実装例を提供しています。

## SIMA(JPGIS版)について

- [JPGIS](https://www.gsi.go.jp/GIS/jpgis-jpgidx.html)
- [SIMA](https://www.jsima.or.jp/sima/index.html)

SIMA（JPGIS版）は、測量・地理空間データ交換のための標準仕様です。  
本ライブラリは、この仕様に沿った XML を Python から組み立てるための補助を目的としています。

## `geo-to_jsima`の概要

- `shapely` のジオメトリオブジェクトを SIMA の XML 形式に変換するためのライブラリ
- SIMA の XML 生成を行うビルダークラス `JsimaXmlBuilder` を提供
- ポリゴンを `GM_Point` 群へ展開し、`Polygon Object`・`Sokuten` を順次追加して XML を構築

### 主な構成

- `jsima/xml_builder.py`  
	- `JsimaXmlBuilder` を提供
	- 現場情報 (`add_genba_joho`)・点 (`add_gm_points`)・ポリゴンオブジェクト (`add_polygon_objects`)・測点 (`add_sokutens`) を追加
- `jsima/gm_polygon.py`  
	- `JsimaGmPolygonModel` を提供
	- `dissambly_poly_to_dict` で `MultiPolygon` / 穴付きポリゴンを分解
	- `replacement_xy` で座標順序を変換
- `jsima/enums.py`  
	- 座標系・測地系・UUID・地目などの列挙を提供


## 実装例

実装例は `example_02.py` を参考にしてください。  


実行すると、複数地物を含む SIMA XML が `jsima_builded_multi_poly.xml` として出力されます。

### `example_02.py` の処理フロー


1. `dissambly_poly_to_dict` で外周・内周ごとに分解
2. `replacement_xy` で座標順序を調整
3. `JsimaGmPolygonModel` を生成し、`to_point_model` で `GM_Point` 群を作成
4. `JsimaXmlBuilder` に対して次の順序で追加
	 - `add_genba_joho`
	 - `add_gm_points`
	 - `add_polygon_objects`
	 - `add_sokutens`
5. `save` で XML を保存

### 実装時の注意点

- `start_idx` を連番で更新し、`GM_Point` の ID 重複を防ぐ
- `add_gm_points` → `add_polygon_objects` → `add_sokutens` の順で追加する
- 地目は `JsimaChimokuEnum` を使って明示する
- 座標系・測地系・UUID は `JsimaCoordinateSystemEnum` / `JsimaCrsEnum` / `JsimaJpsUuidRefEnum` で統一する

## 参考ファイル

- `example.py` : 単一ポリゴンの最小例
- `example_02.py` : 複数ポリゴン / MultiPolygon の実践例