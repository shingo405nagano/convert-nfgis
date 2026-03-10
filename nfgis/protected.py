import re
from .config import ConfigYaml


def search_protected(txt: str) -> str:
    """ 保安林の名称検索を行う関数
    
    この関数では、YAMLファイルに定義されている保安林の名称を検索し、存在しない場合は
    最も類似している名称を返します。
    Args:
        txt (str): 検索したい保安林の名称の一部または全部
    """
    conf = ConfigYaml()
    searched = conf.protected.get(txt, None)
    if searched is not None:
        return searched
    # 完全一致が見つからない場合は、部分一致を検索
    names = list(conf.protected.values())
    pattern = re.compile(re.escape(txt))
    for name in names:
        if pattern.search(name):
            return name
    # 部分一致も見つからない場合は、Errorを返す
    raise ValueError(f"保安林の名称 '{txt}' が見つかりませんでした。")
    