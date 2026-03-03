import pydantic

from .enums import JsimaJpsUuidRefEnum


class JsimaGmPointModel(pydantic.BaseModel):
    """JSIMAのGM_Pointを表すモデル

    使用するタグは'<jsima:GM_Point>'

    Attributes:

         - uuidref: GM_Pointの測地系を表すUUID参照
         - x: GM_PointのX座標
         - y: GM_PointのY座標
         - id: GM_PointのID.他のオブジェクトから参照するための識別子
         - number: GM_Pointのインデックス.連番で管理される
         - name: GM_Pointの名称.任意の文字列
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
        """uuidrefがJsimaJpsUuidRefEnumのいずれかであることを検証する"""
        if value not in JsimaJpsUuidRefEnum:
            raise ValueError(
                f"uuidref must be one of {list(JsimaJpsUuidRefEnum.__members__.keys())}"
            )
        if isinstance(value, JsimaJpsUuidRefEnum):
            return value.value
        return value

    @pydantic.model_validator(mode="after")
    def _validate_id(self) -> "JsimaGmPointModel":
        """idが空の場合、numberから自動生成する"""
        self.id = f"pnt{str(self.number).zfill(7)}"
        self.sokuten_id = f"simapnt{str(self.number).zfill(7)}"
        return self


class JsimaGmPointModels(object):
    """複数のJsimaGmPointModelを管理するクラス

    - x_list: GM_PointのX座標のリスト
    - y_list: GM_PointのY座標のリスト
    - uuidref: GM_Pointの測地系を表すUUID参照
    - id_template: GM_PointのIDテンプレート.デフォルトは'pnt{index}'で、indexは1から始まる連番
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
        """複数のJsimaGmPointModelを管理するクラス

        Args:
            x_list: GM_PointのX座標のリスト
            y_list: GM_PointのY座標のリスト
            uuidref: GM_Pointの測地系を表すUUID参照
            id_template: GM_PointのIDテンプレート.デフォルトは'pnt{index}'で、indexは1から始まる連番
            start_index: GM_Pointの連番の開始値.デフォルトは1

        Attributes:
            start_idx: GM_Pointの連番の開始値
            end_idx: GM_Pointの連番の終了値
            _points: 座標文字列キーで保持したGM_Pointモデルの辞書
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
        """座標文字列キーで保持したGM_Point辞書を返す。"""
        return dict(self._points)

    def values(self) -> list[JsimaGmPointModel]:
        """保持しているGM_Pointモデル一覧を返す。"""
        return list(self._points.values())

    def search_id(self, x: float, y: float) -> str | None:
        """指定された座標に対応するGM_PointのIDを検索する

        Args:
            x: GM_PointのX座標
            y: GM_PointのY座標

        Returns:
            指定された座標に対応するGM_PointのID.見つからない場合はNoneを返す
        """
        key = self._coordinate_key(x, y)
        point = self._points.get(key)
        if point is not None:
            return point.id
        return None

    @staticmethod
    def _coordinate_key(x: float, y: float) -> str:
        """座標辞書のキー文字列を返す。"""
        return f"{x:.9f} {y:.9f}"
