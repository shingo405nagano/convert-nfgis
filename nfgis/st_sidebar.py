import streamlit as st

from .config import URL_YAML, ConfigYaml, StSessionKeys  # noqa: F401
from .geospatial import GsShpData  # noqa: F401


class SidebarUi:
    """サイドバーのUIを管理するクラスです。"""

    def __init__(self):
        self.prefectures: dict[str, str] = URL_YAML["GS_SHAPE_URLS"]

    def run(self):
        st.title("🗾 都道府県の選択")
        col1, col2 = st.columns(2, vertical_alignment="bottom")
        selected_prefecture = col1.selectbox(
            "",
            options=list(self.prefectures.keys()),
            index=46,
        )
        downloaded = col2.button("ダウンロード")
        try:
            if downloaded:
                self.download_data(selected_prefecture)
        except Exception as e:
            st.error(
                f"データのダウンロード中にエラーが発生しました: {e}"
                "ダウンロードの失敗は、公開されているURLの変更が原因である"
                "可能性があります。"
            )

        if StSessionKeys.DOWNLOADED_DATA_DICT in st.session_state:
            data = st.session_state[StSessionKeys.DOWNLOADED_DATA_DICT]
            if selected_prefecture in data:
                self.query_ui(selected_prefecture)

    def download_data(self, prefecture: str):
        """選択された都道府県のデータをダウンロードする関数です。

        ダウンロードしたデータは、Streamlitのセッションステートに保存され、後で他
        のコンポーネントからアクセスできるようになります。
        """
        if (
            StSessionKeys.DOWNLOADED_DATA_DICT in st.session_state
            and st.session_state[StSessionKeys.DOWNLOADED_DATA_DICT].get(prefecture)
            is not None
        ):
            st.success(f"{prefecture}のデータは既にダウンロードされています。")
        else:
            cont = st.empty()
            cont.info(
                f"{prefecture}のデータをダウンロードしています..."
                "地域によっては1分程度かかる場合もあります。"
            )
            shp = GsShpData(prefecture=prefecture)
            if st.session_state.get(StSessionKeys.DOWNLOADED_DATA_DICT) is None:
                st.session_state[StSessionKeys.DOWNLOADED_DATA_DICT] = {}
            st.session_state[StSessionKeys.DOWNLOADED_DATA_DICT][prefecture] = shp
            # データが多くなりすぎないように、古いものを削除する
            self.__delete_downloaded_oldest_data()
            cont.empty()

    def query_ui(self, prefecture: str):
        """選択された都道府県のデータをクエリするUIを表示する関数です。

        このメソッドでは、ダウンロード済みのデータから、"計画区", "森林管理署",
        "担当区", "国有林名", "林班主番"の選択肢をサイドバーのUIで提供し、ユーザー
        が選択した条件に合うデータを抽出します。
        Args:
            prefecture (str): クエリ対象の都道府県名
        """
        if StSessionKeys.DOWNLOADED_DATA_DICT not in st.session_state:
            st.warning(f"{prefecture}のデータがダウンロードされていません。")

        shp_all = st.session_state[StSessionKeys.DOWNLOADED_DATA_DICT]
        if prefecture not in shp_all:
            st.warning(f"{prefecture}のデータがセッションに保存されていません")

        shp: GsShpData = shp_all[prefecture]
        # with st.expander(f"{prefecture}のデータから抽出"):
        category_data = shp.read_category()
        plan_area = st.selectbox("計画区", options=list(category_data.keys()))
        st.session_state[StSessionKeys.PLAN_AREA] = plan_area
        office = st.selectbox(
            "森林管理署", options=list(category_data[plan_area].keys())
        )
        st.session_state[StSessionKeys.OFFICE] = office
        branch_office = st.selectbox(
            "担当区", options=list(category_data[plan_area][office].keys())
        )
        st.session_state[StSessionKeys.BRANCH_OFFICE] = branch_office
        locality = st.selectbox(
            "国有林名", options=category_data[plan_area][office][branch_office]
        )
        st.session_state[StSessionKeys.LOCALITY] = locality
        main_address = st.selectbox(
            "林班主番",
            options=category_data[plan_area][office][branch_office][locality],
        )
        st.session_state[StSessionKeys.MAIN_ADDRESS] = main_address
        if main_address is None:
            st.warning(
                "林班主番が選択されていません。サイズが大きくなる可能性があります。"
            )

        current_query = (
            f"{prefecture}_{plan_area}_{office}_{branch_office}_{locality}_{main_address}"
        )
        last_extracted_query = st.session_state.get(StSessionKeys.LAST_EXTRACTED_QUERY)
        st.session_state[StSessionKeys.CHANGE_SCOPE] = (
            last_extracted_query == current_query
        )

        if st.button("抽出開始"):
            self._execute_query(prefecture, current_query)
        elif st.session_state[StSessionKeys.CHANGE_SCOPE] is False:
            st.markdown(
                "抽出条件を変更しました。抽出開始ボタンを押すと、条件に合うデータが抽出されます。"
            )

    def _execute_query(self, prefecture: str, query_key: str):
        """クエリを実行する関数です。

        Args:
            prefecture (str): クエリ対象の都道府県名
        """
        shp: GsShpData = st.session_state[StSessionKeys.DOWNLOADED_DATA_DICT][
            prefecture
        ]
        content = st.empty()
        content.info("実行しています...")
        gdf = shp.query(
            plan_area=st.session_state[StSessionKeys.PLAN_AREA],
            office=st.session_state[StSessionKeys.OFFICE],
            branch_office=st.session_state[StSessionKeys.BRANCH_OFFICE],
            locality=st.session_state[StSessionKeys.LOCALITY],
            main_address=st.session_state[StSessionKeys.MAIN_ADDRESS],
        )
        st.session_state[StSessionKeys.GEODATAFRAME] = gdf
        st.session_state[StSessionKeys.LAST_EXTRACTED_QUERY] = query_key
        st.session_state[StSessionKeys.CHANGE_SCOPE] = True
        content.empty()
        st.info(f"抽出された小班数は{gdf.shape[0]}件です。")

    def __delete_downloaded_oldest_data(self, maximum: int = 1):
        """ダウンロードされたデータの中で最も古いものを削除する関数です。

        ダウンロードされたデータが一定数を超えた場合に、最も古いデータを削除してメモリを解放するために使用されます。
        """
        if maximum < len(st.session_state.get(StSessionKeys.DOWNLOADED_DATA_DICT, {})):
            # 最も古いデータを削除する
            prefectures = st.session_state[StSessionKeys.DOWNLOADED_DATA_DICT].keys()
            oldest_prefecture = list(prefectures)[0]
            del st.session_state[StSessionKeys.DOWNLOADED_DATA_DICT][oldest_prefecture]


def run_sidebar():
    """サイドバーのUIを表示する関数です。"""
    st.markdown(
        """
        <style>
        /* サイドバーの基本幅とリサイズ時の最大幅を設定 */
        .css-1d391kg, .css-1lcbmhc, .css-17eq0hr, [data-testid="stSidebar"] {
            min-width: 200px;
            max-width: 600px !important;
            width: 250px;
        }
        
        /* リサイズハンドルとコンテナの最大幅設定 */
        .css-1d391kg .css-6qob1r, .css-1lcbmhc .css-6qob1r,
        .css-1d391kg > div, .css-1lcbmhc > div {
            max-width: 600px !important;
        }
        
        /* サイドバー全体のコンテナ */
        .css-1aumxhk {
            max-width: 600px !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.sidebar:
        # ファイルのアップロードと設定を行うUIを提供
        st.header("ダウンロードする地域の選択")
        st.markdown(
            "このアプリは、Web上で公開されている、国有林の地理空間データを取得し、"
            "必要な範囲だけを「SIMA(JPGIS版)」形式でダウンロードすることができます。"
        )
        SidebarUi().run()
