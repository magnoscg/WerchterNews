from dataclasses import dataclass
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

@dataclass
class Config:
    """
    Gestiona la configuración de la aplicación implementando el patrón Singleton.
    
    Attributes:
        telegram_bot_token (str): Token de autenticación del bot de Telegram
        telegram_chat_id (str): ID del chat donde se enviarán las notificaciones
        check_interval (int): Intervalo de verificación en segundos
    """
    telegram_bot_token: str
    telegram_chat_id: str
    check_interval: int = 600
    
    _instance: Optional['Config'] = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    @classmethod
    def load_config(cls) -> 'Config':
        """
        Carga y valida la configuración desde variables de entorno.
        
        Returns:
            Config: Instancia configurada
            
        Raises:
            ValueError: Si faltan variables de entorno requeridas
        """
        load_dotenv(override=True)
        
        # Obtener variables de entorno con validación
        config_values = {
            'telegram_bot_token': os.getenv('TELEGRAM_BOT_TOKEN'),
            'telegram_chat_id': os.getenv('TELEGRAM_CHAT_ID'),
            'check_interval': int(os.getenv('CHECK_INTERVAL', '600'))
        }
        
        # Validación de campos requeridos
        missing_vars = [
            var_name for var_name, value in {
                'TELEGRAM_BOT_TOKEN': config_values['telegram_bot_token'],
                'TELEGRAM_CHAT_ID': config_values['telegram_chat_id']
            }.items() if not value
        ]
        
        if missing_vars:
            error_message = (
                "Error de configuración. Variables de entorno faltantes:"
                f"\n- {', '.join(missing_vars)}\n\n"
                "Asegúrate de:\n"
                "1. Crear un archivo .env con las variables requeridas, o\n"
                "2. Configurar las variables de entorno directamente\n\n"
                "Ejemplo de archivo .env:\n"
                "TELEGRAM_BOT_TOKEN=tu_token_aquí\n"
                "TELEGRAM_CHAT_ID=tu_chat_id_aquí\n"
                "CHECK_INTERVAL=600  # Opcional, valor por defecto: 600 segundos"
            )
            logger.error(error_message)
            raise ValueError(error_message)
        
        # Validación de intervalo de chequeo
        if config_values['check_interval'] < 60:
            logger.warning(
                "Intervalo de chequeo configurado a {} segundos. "
                "Se recomienda un valor mínimo de 60 segundos.".format(
                    config_values['check_interval']
                )
            )
        
        # Log de configuración exitosa
        logger.info(
            "Configuración cargada exitosamente:\n"
            "CHECK_INTERVAL: {} segundos\n"
            "TELEGRAM_BOT_TOKEN: [CONFIGURADO]\n"
            "TELEGRAM_CHAT_ID: [CONFIGURADO]".format(
                config_values['check_interval']
            )
        )
        
        return cls(**config_values)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte la configuración a diccionario con ofuscación de datos sensibles.
        
        Returns:
            Dict[str, Any]: Configuración en formato diccionario
        """
        return {
            'telegram_bot_token': '[PROTECTED]',
            'telegram_chat_id': '[PROTECTED]',
            'check_interval': self.check_interval
        }