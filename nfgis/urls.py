import re

import bs4
import requests

from .config import base_url


class GsNationalForestZipUrls(object):
    """
    G空間センターから林野庁が公開している、国有林のGISデータのZipファイルの
    URLを取得するクラス。

    [G空間センター](https://front.geospatial.jp/)
    [国有林GISデータ（2024年度版）](https://www.geospatial.jp/ckan/dataset/nfgis-2024)

    Example:
        ```python
        >>> zip_urls = GsNationalForestZipUrls().run()
        >>> print(zip_urls)
        {
            "北海道": "https://www.geospatial.jp/ckan/dataset/nfgis-2024/resource/xxxx/download/hokkaido.zip",
            "青森県": "https://www.geospatial.jp/ckan/dataset/nfgis-2024/resource/yyyy/download/aomori.zip",
            ...
        }
        ```
    """

    def __init__(self, page_url: str = base_url["GS_shp_zip"]):
        self.page_url = page_url

    def normalize_prefecture_key(self, file_name: str) -> str:
        """ファイル名から都道府県キーを正規化して取得する。

        Args:
            file_name (str): ファイル名

        Returns:
            str: 正規化された都道府県キー
        """
        key = file_name.strip()
        key = re.sub(r"\.zip$", "", key, flags=re.IGNORECASE)
        key = re.sub(r"^\d+", "", key)
        key = re.sub(r"\s+", "", key)
        return key

    def extract_zip_download_urls(self, html_text: str) -> dict[str, str]:
        """HTMLテキストからZipファイルのダウンロードURLを抽出する。

        Args:
            html_text (str): HTMLテキスト
        Returns:
            dict[str, str]: 都道府県キーと対応するZipファイルのダウンロードURLの辞書
        """
        soup = bs4.BeautifulSoup(html_text, "html.parser")
        result: dict[str, str] = {}

        for item in soup.select("li.resource-item"):
            heading = item.select_one("a.heading")
            if heading is None:
                continue

            file_name = heading.get("title") or heading.get_text(strip=True)
            file_name = file_name.strip()
            if not file_name.lower().endswith(".zip"):
                continue

            download_link = None
            for link in item.select("a[href]"):
                href = link.get("href", "")
                if "/download/" in href and href.lower().endswith(".zip"):  # type: ignore
                    download_link = href.strip()  # type: ignore
                    break

            if not download_link:
                continue

            key = self.normalize_prefecture_key(file_name)
            if not key:
                continue

            result[key] = download_link

        return result

    def get_zip_urls_from_page(self, page_url: str) -> dict[str, str]:
        """指定したページURLからZipファイルのダウンロードURLを取得する。

        Args:
            page_url (str): ページのURL
        Returns:
            dict[str, str]: 都道府県キーと対応するZipファイルのダウンロードURLの辞書
        """
        response = requests.get(page_url, timeout=30)
        response.raise_for_status()
        response.encoding = response.apparent_encoding
        return self.extract_zip_download_urls(response.text)

    def run(self) -> dict[str, str]:
        """クラスのメイン処理を実行する。

        Returns:
            dict[str, str]: 都道府県キーと対応するZipファイルのダウンロードURLの辞書
        """
        return self.get_zip_urls_from_page(self.page_url)
