from enum import StrEnum, Enum # noqa: F401

class JsimaCoordinateSystemEnum(Enum):
    """ JPGISの座標系を表す列挙型

    ここでは平面直角座標系の系番号のみを定義する。
    平面直角座標系は日本全国を19の系に分割している。
    使用するタグは'<jsima:CoordinateSystem>'

     - https://www.gsi.go.jp/sokuchikijun/jpc.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_1.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_2.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_3.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_4.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_5.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_6.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_7.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_8.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_9.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_10.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_11.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_12.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_13.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_14.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_15.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_16.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_17.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_18.html
     - https://www.gsi.go.jp/sokuchikijun/jpc_19.html
    """
    JPR_01 = 1
    JPR_02 = 2
    JPR_03 = 3
    JPR_04 = 4
    JPR_05 = 5
    JPR_06 = 6
    JPR_07 = 7
    JPR_08 = 8
    JPR_09 = 9
    JPR_10 = 10
    JPR_11 = 11
    JPR_12 = 12
    JPR_13 = 13
    JPR_14 = 14
    JPR_15 = 15
    JPR_16 = 16
    JPR_17 = 17
    JPR_18 = 18
    JPR_19 = 19


class JsimaCrsEnum(Enum):
    """ JPGISの測地系を表す列挙型

    使用するタグは'<jsima:Crs>'
    """
    JGD_2000 = 1
    JGD_2011 = 2
    JGD_2024 = 3

class JsimaJpsUuidRefEnum(StrEnum):
    """JPGISのCRS UUIDを表す列挙型

    使用するタグは'<jps:CRS uuidref="..."/>'
    """
    JGD_2000_PL10 = "jpsuuid:jgd2000.pl10"
    JGD_2011_PL10 = "jpsuuid:jgd2011.pl10"
    JGD_2024_PL10 = "jpsuuid:jgd2024.pl10"