# this file is only used by wmflabs for hosting
from montage.app import create_app
from montage.utils import get_env_name

env_name = get_env_name()
app = create_app(env_name=env_name)
