from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
from litestar.plugins.problem_details import ProblemDetailsPlugin
from litestar.plugins.structlog import StructlogPlugin
from litestar_granian import GranianPlugin

from app.config import app as config
from app.lib.oauth import OAuth2ProviderPlugin

structlog = StructlogPlugin(config=config.log)
alchemy = SQLAlchemyPlugin(config=config.alchemy)
granian = GranianPlugin()
problem_details = ProblemDetailsPlugin(config=config.problem_details)
oauth = OAuth2ProviderPlugin()
