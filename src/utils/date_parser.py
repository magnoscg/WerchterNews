from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class DateParser:
    """
    Utilidad para parsing y formateo de fechas con manejo robusto de errores.
    Implementa el patrón Strategy para diferentes formatos de fecha.
    """
    
    # Formatos de fecha conocidos en orden de prioridad
    DATE_FORMATS = [
        "%d %B %Y",        # 25 October 2024
        "%B %d %Y",        # October 25 2024
        "%Y-%m-%d",        # 2024-10-25
        "%d-%m-%Y",        # 25-10-2024
        "%d/%m/%Y",        # 25/10/2024
    ]
    
    MONTH_REPLACEMENTS = {
        'januari': 'january',
        'februari': 'february',
        'maart': 'march',
        'mei': 'may',
        'juni': 'june',
        'juli': 'july',
        'augustus': 'august',
        'oktober': 'october',
        'december': 'december'
    }
    
    @classmethod
    def parse_date(cls, date_str: str) -> Optional[datetime]:
        """
        Parsea una cadena de fecha en formato flexible.
        
        Args:
            date_str: String que contiene la fecha
            
        Returns:
            datetime opcional con la fecha parseada
        """
        if not date_str:
            return None
            
        # Limpieza y normalización del string de fecha
        clean_date = cls._normalize_date_string(date_str)
        
        # Intenta cada formato conocido
        for date_format in cls.DATE_FORMATS:
            try:
                return datetime.strptime(clean_date, date_format)
            except ValueError:
                continue
                
        logger.warning(f"No se pudo parsear la fecha: {date_str}")
        return None
    
    @classmethod
    def _normalize_date_string(cls, date_str: str) -> str:
        """
        Normaliza el string de fecha para el parsing.
        
        Args:
            date_str: String de fecha original
            
        Returns:
            String de fecha normalizado
        """
        # Limpieza básica
        normalized = date_str.lower().strip()
        
        # Reemplaza nombres de meses en holandés
        for dutch, english in cls.MONTH_REPLACEMENTS.items():
            normalized = normalized.replace(dutch, english)
        
        # Capitaliza para formato estándar
        normalized = normalized.title()
        
        return normalized
    
    @staticmethod
    def format_date(date: Optional[datetime], format_str: str = "%d %B %Y") -> str:
        """
        Formatea una fecha para visualización.
        
        Args:
            date: Fecha a formatear
            format_str: Formato deseado
            
        Returns:
            String formateado de la fecha
        """
        if not date:
            return "Fecha no disponible"
            
        try:
            return date.strftime(format_str)
        except Exception as e:
            logger.error(f"Error formateando fecha: {e}")
            return "Error en formato de fecha"