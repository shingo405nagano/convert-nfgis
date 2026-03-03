import pydantic

from .enums import JsimaJpsUuidRefEnum


class JsimaGmPointModel(pydantic.BaseModel):
    """JSIMA/JPGIS の `GM_Point` と `Sokuten` 参照情報を保持するモデル。

    本モデルは座標値と参照系 (`uuidref`) を受け取り、JSIMA XML 生成時に必要となる
    識別子を一貫した規則で自動採番する。

    Attributes:
        x: 点の X 座標。
        y: 点の Y 座標。
        uuidref: 座標参照系を表す UUID 文字列。
        number: 点番号（1 始まりの連番を想定）。
        id: `GM_Point` 要素 ID（`pnt0000001` 形式）。
        sokuten_id: `Sokuten` 要素 ID（`simapnt0000001` 形式）。
        name: 測点名。`Sokuten/Name` に出力される。
    """

    x: float
    y: float
    uuidref: str
    number: int
    id: str = pydantic.Field(default="", description="GM_PointのID")
    sokuten_id: str = pydantic.Field(default="", description="Sokuten要素のID")
    name: str = pydantic.Field(default="", description="Sokuten要素の名称")

    @pydantic.field_validator("uuidref", mode="before")
    @classmethod
    def validate_uuidref(cls, value):
        """`uuidref` が許可された列挙値であることを検証・正規化する。

        Args:
            value: `JsimaJpsUuidRefEnum` または列挙値に対応する文字列。

        Returns:
            XML 出力に使える UUID 文字列。

        Raises:
            ValueError: `JsimaJpsUuidRefEnum` に存在しない値が指定された場合。
        """
        if value not in JsimaJpsUuidRefEnum:
            raise ValueError(
                f"uuidref must be one of {list(JsimaJpsUuidRefEnum.__members__.keys())}"
            )
        if isinstance(value, JsimaJpsUuidRefEnum):
            return value.value
        return value

    @pydantic.model_validator(mode="after")
    def _validate_id(self) -> "JsimaGmPointModel":
        """`number` から `GM_Point`/`Sokuten` の識別子を生成する。

        Returns:
            識別子が補完された自身のモデルインスタンス。
        """
        self.id = f"pnt{str(self.number).zfill(7)}"
        self.sokuten_id = f"simapnt{str(self.number).zfill(7)}"
        return self


class JsimaGmPointModels(object):
    """重複座標を除去しながら `JsimaGmPointModel` を集約するコンテナ。

    同一座標（小数点 9 桁に丸めたキー）が複数回現れた場合は 1 点として扱い、
    `GM_Point` の重複生成を防ぐ。
    """

    def __init__(
        self,
        x_list: list[float],
        y_list: list[float],
        uuidref: JsimaJpsUuidRefEnum = JsimaJpsUuidRefEnum.JGD_2024_PL10,
        start_index: int = 1,
        names: list[str] | None = None,
        **kwargs,
    ):
        """座標配列から `JsimaGmPointModel` 群を構築する。

        Args:
            x_list: X 座標列。
            y_list: Y 座標列。
            uuidref: 座標参照系 UUID。
            start_index: `number` 採番の開始値。
            names: 測点名リスト。`None` の場合は空文字で補完。
            **kwargs: 互換性維持のため受け取る未使用引数。

        Raises:
            ValueError: `names` の要素数が座標数と一致しない場合。

        Attributes:
            start_idx: 連番開始値。
            end_idx: 実際に作成された最後の連番。
            _points: 座標キー（`"{x:.9f} {y:.9f}"`）で保持した点辞書。
        """
        self.start_idx = start_index
        self.end_idx = start_index + 1
        # Sokuten要素に名前を付与するためのリストを保持する
        self.names = []
        if names is None:
            self.names = [""] * len(x_list)
        else:
            if len(names) != len(x_list):
                raise ValueError("namesの長さはGM_Pointの数と一致する必要があります")
            self.names = names
        # 座標文字列キーで保持したGM_Pointモデルの辞書を作成する
        self._points = {}
        for i, (x, y, name) in enumerate(
            zip(x_list, y_list, self.names), start=self.start_idx
        ):
            key = self._coordinate_key(x, y)
            if key not in self._points:
                self._points[key] = JsimaGmPointModel(
                    x=x,
                    y=y,
                    uuidref=uuidref,
                    number=i,
                    name=name,
                )
                self.end_idx = i

    def as_dict(self) -> dict[str, JsimaGmPointModel]:
        """内部保持している座標キー付き辞書のコピーを返す。

        Returns:
            キーが座標文字列、値が `JsimaGmPointModel` の辞書。
        """
        return dict(self._points)

    def values(self) -> list[JsimaGmPointModel]:
        """保持している `JsimaGmPointModel` 一覧を返す。

        Returns:
            追加順で並んだ点モデルのリスト。
        """
        return list(self._points.values())

    def search_id(self, x: float, y: float) -> str | None:
        """指定座標に対応する `GM_Point` ID を検索する。

        Args:
            x: 検索対象の X 座標。
            y: 検索対象の Y 座標。

        Returns:
            一致する `GM_Point` の ID。存在しない場合は `None`。
        """
        key = self._coordinate_key(x, y)
        point = self._points.get(key)
        if point is not None:
            return point.id
        return None

    @staticmethod
    def _coordinate_key(x: float, y: float) -> str:
        """座標の正規化キーを生成する。

        Args:
            x: X 座標。
            y: Y 座標。

        Returns:
            小数点 9 桁固定の `"x y"` 形式文字列。
        """
        return f"{x:.9f} {y:.9f}"
