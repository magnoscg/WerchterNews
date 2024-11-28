from typing import Optional
import asyncio
import logging
from datetime import datetime
from telegram import Bot
from telegram.ext import Application
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class TelegramService:
    """
    Servicio mejorado para gestionar notificaciones de Telegram con manejo robusto
    de errores, gestión de recursos y patrón Singleton para la conexión del bot.
    """
    
    def __init__(self, bot_token: str, chat_id: str, max_retries: int = 3, timeout: int = 30):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.max_retries = max_retries
        self.timeout = timeout
        self._application: Optional[Application] = None
        self._bot: Optional[Bot] = None
        self._last_initialization: Optional[datetime] = None
        self._initialization_lock = asyncio.Lock()

    @asynccontextmanager
    async def get_bot(self):
        """
        Context manager para obtener una instancia del bot de manera segura.
        Implementa un patrón de reinicialización automática si la conexión es antigua.
        """
        try:
            async with self._initialization_lock:
                await self._ensure_initialized()
            yield self._bot
        except Exception as e:
            logger.error(f"Error en operación del bot: {str(e)}")
            await self._cleanup()
            raise

    async def _ensure_initialized(self) -> None:
        """
        Asegura que el bot está inicializado y la conexión es reciente.
        Implementa renovación automática de conexiones antiguas.
        """
        current_time = datetime.now()
        needs_initialization = (
            self._bot is None or 
            self._last_initialization is None or
            (current_time - self._last_initialization).total_seconds() > 3600
        )

        if needs_initialization:
            await self._initialize()

    async def _initialize(self) -> None:
        """
        Inicializa el bot de manera segura con manejo de errores mejorado.
        """
        try:
            if self._application:
                await self._cleanup()
            
            self._application = (
                Application.builder()
                .token(self.bot_token)
                .connect_timeout(self.timeout)
                .read_timeout(self.timeout)
                .write_timeout(self.timeout)
                .build()
            )
            
            self._bot = self._application.bot
            self._last_initialization = datetime.now()
            logger.info("Bot de Telegram inicializado correctamente")
            
        except Exception as e:
            logger.error(f"Error crítico inicializando bot: {str(e)}")
            await self._cleanup()
            raise

    async def send_notification(self, news_item) -> bool:
        """
        Envía una notificación con reintentos exponenciales y manejo robusto de errores.
        """
        for attempt in range(self.max_retries):
            try:
                async with self.get_bot() as bot:
                    if news_item.image_url:
                        await bot.send_photo(
                            chat_id=self.chat_id,
                            photo=news_item.image_url,
                            caption=news_item.telegram_message,
                            parse_mode='Markdown'
                        )
                    else:
                        await bot.send_message(
                            chat_id=self.chat_id,
                            text=news_item.telegram_message,
                            parse_mode='Markdown'
                        )
                
                logger.info(f"Notificación enviada exitosamente: {news_item.title}")
                return True
                
            except Exception as e:
                wait_time = min(2 ** attempt * 5, 60)
                logger.error(
                    f"Intento {attempt + 1}/{self.max_retries} fallido: {str(e)}. "
                    f"Esperando {wait_time}s antes de reintentar..."
                )
                
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Fallo al enviar notificación después de {self.max_retries} "
                        f"intentos: {news_item.title}"
                    )
                    return False
                    
                await asyncio.sleep(wait_time)

    async def _cleanup(self) -> None:
        """
        Limpia recursos y conexiones de manera segura.
        """
        if self._application:
            try:
                await self._application.shutdown()
                logger.info("Limpieza de recursos de Telegram completada")
            except Exception as e:
                logger.error(f"Error durante la limpieza: {str(e)}")
            finally:
                self._application = None
                self._bot = None
                self._last_initialization = None