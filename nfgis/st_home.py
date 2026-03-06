import html
from typing import Any

import folium
import leafmap.foliumap as leafmap
import streamlit as st

from .config import StSessionKeys, TileUrl, TileUrls


class StMappingUi(object):
    def __init__(self):
        self.map = None

    def run(self, tile_url: TileUrl):
        if StSessionKeys.GEODATAFRAME not in st.session_state:
            st.warning("データの抽出が完了していない為、マップが表示されません。")
            return
        gdf = st.session_state[StSessionKeys.GEODATAFRAME]
        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(epsg=4326)
        centroid_geoms = gdf.geometry.centroid
        self.m = leafmap.Map(
            # コントロールは最小限に
            draw_control=False,
            measure_control=False,
            center=(centroid_geoms.y.mean(), centroid_geoms.x.mean()),
            tiles=tile_url.url,
            attr=tile_url.attr,
            zoom=13,  # 地図の初期範囲を決めた場合
        )
        geoj = gdf.to_geo_dict()
        self.m.add_geojson(
            geoj,
            layer_name="抽出された林小班",
            info_mode="on_click",
            style_function=lambda feature: self._sub_address_style,
        )

        self._add_polygon_labels(m=self.m, gdf=gdf, column="sub_address_name")

        self.m.to_streamlit()

    def _add_polygon_labels(self, m, gdf, column: str):
        # 常時表示ラベルとして重心位置に DivIcon を重ねる。
        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            pt = geom.representative_point()
            label_text = html.escape(str(row.get(column, "")))
            if not label_text:
                continue
            folium.Marker(
                location=[pt.y, pt.x],
                icon=folium.DivIcon(
                    html=(
                        "<div style='font-size:10px; font-weight:700; "
                        "color:#1f2937; background:rgba(255,255,255,0.0); "
                        "padding:4px 6px; border-radius:6px; "
                        "border:1px solid rgba(31,41,55,0.0);'>"
                        f"{label_text}"
                        "</div>"
                    )
                ),
            ).add_to(m)

    @property
    def _sub_address_style(self) -> dict[str, Any]:
        return {
            "fillColor": "#4a505e",
            "color": "#4a505e",
            "weight": 1.5,
            "fillOpacity": 0.1,
        }


class StHomeUi(object):
    def __init__(self):
        st.markdown(
            """
            <style>
            .block-container {
                max-width: 100%;
                padding-left: 1rem;
                padding-right: 1rem;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        self.map_ui = StMappingUi()

    def run(self):
        show_map = st.toggle("マップに投影", value=False)
        if show_map:
            if st.session_state.get(StSessionKeys.CHANGE_SCOPE) is False:
                st.warning("抽出条件が変更されているため、マップが表示されません。")
                self.map_ui.map = None
                return 
            tile_urls = TileUrls()
            selected_tile_name = st.selectbox(
                "ベースマップを選択", tile_urls.tile_names
            )
            tile_url = tile_urls.get_tile_url(selected_tile_name)
            self._mapping(tile_url)

    def _mapping(self, tile_url: TileUrl):
        self.map_ui.run(tile_url)
