import pydantic

from .enums import JsimaJpsUuidRefEnum


class JsimaGmPointModel(pydantic.BaseModel):
    """JSIMAのGM_Pointを表すモデル

    使用するタグは'<jsima:GM_Point>'

    Attributes:
         - id: GM_PointのID.他のオブジェクトから参照するための識別子
         - uuidref: GM_Pointの測地系を表すUUID参照
         - x: GM_PointのX座標
         - y: GM_PointのY座標
    """

    id: str
    uuidref: str
    x: float
    y: float

    @pydantic.field_validator("uuidref", mode="before")
    def validate_uuidref(cls, value):
        """uuidrefがJsimaJpsUuidRefEnumのいずれかであることを検証する"""
        if value not in JsimaJpsUuidRefEnum:
            raise ValueError(
                f"uuidref must be one of {list(JsimaJpsUuidRefEnum.__members__.keys())}"
            )
        if isinstance(value, JsimaJpsUuidRefEnum):
            return value.value
        return value


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
        **kwargs,
    ):
        """複数のJsimaGmPointModelを管理するクラス

        Args:
            x_list: GM_PointのX座標のリスト
            y_list: GM_PointのY座標のリスト
            uuidref: GM_Pointの測地系を表すUUID参照
            id_template: GM_PointのIDテンプレート.デフォルトは'pnt{index}'で、indexは1から始まる連番
        """
        self.__id_template = kwargs.get("id_template", "pnt{index}")
        self._points = {}
        for i, (x, y) in enumerate(zip(x_list, y_list), start=1):
            point_id = self._generate_id(i)
            key = f"{x:.3f} {y:.3f}"
            if key not in self._points:
                self._points[key] = JsimaGmPointModel(
                    id=point_id, uuidref=uuidref, x=x, y=y
                )

    def as_dict(self) -> dict[str, JsimaGmPointModel]:
        """座標文字列キーで保持したGM_Point辞書を返す。"""
        return dict(self._points)

    def values(self) -> list[JsimaGmPointModel]:
        """保持しているGM_Pointモデル一覧を返す。"""
        return list(self._points.values())

    def _generate_id(self, index: int) -> str:
        """indexからGM_PointのIDを生成する

        Args:
            index: GM_Pointの連番.1から始まる整数

        Returns:
            GM_PointのID
        """
        if not isinstance(index, int):
            raise ValueError("index must be an integer")
        idx = str(index).zfill(7)
        return self.__id_template.format(index=idx)

    def search_id(self, x: float, y: float) -> str | None:
        """指定された座標に対応するGM_PointのIDを検索する

        Args:
            x: GM_PointのX座標
            y: GM_PointのY座標

        Returns:
            指定された座標に対応するGM_PointのID.見つからない場合はNoneを返す
        """
        key = f"{x:.3f} {y:.3f}"
        point = self._points.get(key)
        if point is not None:
            return point.id
        return None
