import asyncio
import logging
import logging.handlers
import signal
import sys
from typing import Optional, List
from datetime import datetime
from pathlib import Path
from src.services.news_services import NewsService
from src.services.telegram_services import TelegramService
from src.services.storage_services import StorageService
from src.config import Config
from src.models import NewsItem

# Configuración de logging estructurado con rotación de archivos
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            'logs/werchter_monitor.log',
            maxBytes=5_000_000,  # 5MB
            backupCount=5
        )
    ]
)
logger = logging.getLogger(__name__)

class WerchterMonitor:
    """
    Monitor principal para noticias de Rock Werchter.
    
    Implementa el patrón Observer para monitorear cambios en la web y notificar
    a través de Telegram cuando se detectan nuevas noticias.
    
    Attributes:
        config (Config): Configuración del monitor
        news_service (NewsService): Servicio de obtención de noticias
        telegram_service (TelegramService): Servicio de notificaciones
        storage_service (StorageService): Servicio de persistencia
    """
    
    def __init__(self, config: Config):
        """
        Inicializa el monitor con su configuración y servicios.
        
        Args:
            config (Config): Configuración del monitor
        """
        self.config = config
        self.news_service = NewsService()
        self.telegram_service = TelegramService(
            bot_token=config.telegram_bot_token,
            chat_id=config.telegram_chat_id
        )
        self.storage_service = StorageService()
        self._shutdown_event = asyncio.Event()
        self._last_check = datetime.now()
        
        # Validación de configuración inicial
        self._validate_config()

    def _validate_config(self) -> None:
        """
        Valida la configuración inicial del monitor.
        Implementa validaciones robustas para prevenir problemas en runtime.
        """
        if self.config.check_interval < 60:
            logger.warning(
                f"Intervalo de chequeo ({self.config.check_interval}s) es menor "
                "al mínimo recomendado de 60 segundos. Esto podría causar sobrecarga."
            )

    async def run(self) -> None:
        """
        Ejecuta el ciclo principal del monitor.
        
        Implementa un patrón de retry con backoff exponencial para manejar errores
        y evitar sobrecarga del sistema en caso de fallos.
        """
        logger.info("Iniciando monitorización de Rock Werchter")
        consecutive_errors = 0
        
        while not self._shutdown_event.is_set():
            try:
                await self._check_for_updates()
                consecutive_errors = 0
                self._last_check = datetime.now()
                
                logger.info(
                    f"Ciclo completado exitosamente. Próximo chequeo en "
                    f"{self.config.check_interval} segundos"
                )
                
                await asyncio.sleep(self.config.check_interval)
                
            except Exception as e:
                consecutive_errors += 1
                wait_time = min(2 ** consecutive_errors * 30, 3600)
                
                logger.error(
                    f"Error en ciclo de monitorización (intento {consecutive_errors}): "
                    f"{str(e)}. Esperando {wait_time} segundos antes de reintentar.",
                    exc_info=True
                )
                
                if consecutive_errors >= 5:
                    logger.critical(
                        "Múltiples errores consecutivos detectados. "
                        "Verificar conectividad y estado de los servicios."
                    )
                
                await asyncio.sleep(wait_time)

    async def shutdown(self) -> None:
        """
        Realiza un apagado controlado del monitor.
        
        Implementa un patrón de limpieza para asegurar que todos los recursos
        son liberados apropiadamente.
        """
        logger.info("Iniciando proceso de apagado controlado...")
        self._shutdown_event.set()
        
        try:
            await self.telegram_service.cleanup()
            logger.info("Recursos de Telegram liberados correctamente")
        except Exception as e:
            logger.error(f"Error durante limpieza de Telegram: {str(e)}")
            
        try:
            self.storage_service.cleanup_old_entries()
            logger.info("Limpieza de almacenamiento completada")
        except Exception as e:
            logger.error(f"Error durante limpieza de almacenamiento: {str(e)}")
            
        logger.info("Apagado completado exitosamente")

    async def _check_for_updates(self) -> None:
        """
        Verifica la existencia de nuevas noticias y las procesa.
        
        Implementa un patrón de Unit of Work para asegurar la consistencia
        en el procesamiento de las noticias.
        """
        try:
            news_items = await self.news_service.get_news()
            await self._process_news_batch(news_items)
            
        except Exception as e:
            logger.error(f"Error en verificación de actualizaciones: {str(e)}")
            raise

    async def _process_news_batch(self, news_items: List[NewsItem]) -> None:
        """
        Procesa un lote de noticias de manera atómica, enviando solo las nuevas.
        
        Args:
            news_items: Lista de noticias a procesar
        """
        if not news_items:
            logger.debug("No se encontraron noticias para procesar")
            return

        # Filtrar solo noticias no procesadas
        unprocessed_news = self.storage_service.get_unprocessed_news(news_items)
        
        if not unprocessed_news:
            logger.info("No se encontraron noticias nuevas para procesar")
            return
            
        logger.info(f"Procesando {len(unprocessed_news)} noticias nuevas")
        
        for news_item in unprocessed_news:
            try:
                logger.info(f"Procesando nueva noticia: {news_item.title}")
                success = await self.telegram_service.send_notification(news_item)
                
                if success:
                    self.storage_service.mark_as_processed(news_item)
                    logger.info(f"Noticia procesada exitosamente: {news_item.title}")
                else:
                    logger.error(f"No se pudo procesar la noticia: {news_item.title}")
                    
            except Exception as e:
                logger.error(
                    f"Error procesando noticia {news_item.title}: {str(e)}",
                    exc_info=True
                )
                continue
        
        # Limpieza periódica de entradas antiguas
        self.storage_service.cleanup_old_entries()

async def main() -> None:
    """
    Punto de entrada principal de la aplicación.
    
    Implementa el patrón de Control de Ciclo de Vida para gestionar
    el inicio, ejecución y terminación de la aplicación.
    """
    # Asegurar que existe el directorio de logs
    Path('logs').mkdir(exist_ok=True)
    
    monitor: Optional[WerchterMonitor] = None
    
    def signal_handler() -> None:
        """Manejador de señales del sistema."""
        logger.info("Señal de terminación recibida")
        if monitor:
            asyncio.create_task(monitor.shutdown())

    try:
        # Configuración de manejadores de señales
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        # Inicialización y ejecución del monitor
        config = Config.load_config()
        monitor = WerchterMonitor(config)
        await monitor.run()
        
    except Exception as e:
        logger.error(f"Error fatal en la aplicación: {str(e)}", exc_info=True)
        sys.exit(1)
    finally:
        if monitor:
            await monitor.shutdown()
        logger.info("Aplicación finalizada")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Aplicación interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error no controlado: {str(e)}", exc_info=True)
        sys.exit(1)