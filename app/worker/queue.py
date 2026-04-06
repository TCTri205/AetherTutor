from arq import create_pool
from arq.connections import RedisSettings
from ..config import settings
import logging

logger = logging.getLogger(__name__)

# Cấu hình Redis cho ARQ
redis_settings = RedisSettings.from_dsn(settings.ARQ_REDIS_URL)

async def get_redis_pool():
    """ Khởi tạo pool kết nối Redis cho worker. """
    try:
        pool = await create_pool(redis_settings)
        return pool
    except Exception as e:
        logger.error(f"Không thể kết nối Redis Pool cho ARQ: {e}")
        raise e
