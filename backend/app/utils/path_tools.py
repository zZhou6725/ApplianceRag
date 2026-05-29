import os

def get_project_root() -> str:
    """
    获取工程根目录（无论脚本在哪个目录运行，都能返回正确的根目录）
    原理：基于当前文件的绝对路径，向上推导到工程根目录
    """
    # backend/app/utils/path_tools.py -> backend/app/utils -> backend/app -> backend
    current_file = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file)
    app_dir = os.path.dirname(current_dir)
    project_root = os.path.dirname(app_dir)
    return project_root

def get_abs_path(relative_path: str) -> str:
    """
    将工程内的相对路径转为绝对路径（统一路径基准）
    :param relative_path: 相对于工程根目录的路径，如 "config/rag.yml"
    :return: 绝对路径
    """
    project_root = get_project_root()
    return os.path.join(project_root, relative_path)
