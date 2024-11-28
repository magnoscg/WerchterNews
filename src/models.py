from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .utils.date_parser import DateParser

@dataclass
class NewsItem:
    """
    Modelo de datos para noticias con soporte para ordenamiento por fecha.
    Implementa comparadores para permitir ordenamiento natural.
    """
    title: str
    date: str
    link: str
    image_url: Optional[str] = None
    _parsed_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Inicialización posterior a la creación para parsing de fecha."""
        self._parsed_date = DateParser.parse_date(self.date)
    
    @property
    def formatted_date(self) -> str:
        """
        Obtiene la fecha formateada para visualización.
        
        Returns:
            String con la fecha formateada
        """
        return DateParser.format_date(self._parsed_date)
    
    @property
    def telegram_message(self) -> str:
        """
        Genera el mensaje formateado para Telegram.
        
        Returns:
            String con el mensaje formateado
        """
        return (
            f"🎸 *Nueva noticia de Rock Werchter*\n\n"
            f"📌 *{self.title}*\n"
            f"📅 Fecha: {self.formatted_date}\n"
            f"🔗 [Leer más]({self.link})"
        )
    
    def __lt__(self, other: 'NewsItem') -> bool:
        """Permite ordenamiento ascendente por fecha."""
        if not isinstance(other, NewsItem):
            return NotImplemented
        
        # Si alguna fecha no se pudo parsear, la coloca al final
        if not self._parsed_date:
            return False
        if not other._parsed_date:
            return True
            
        return self._parsed_date < other._parsed_date
    
    def __eq__(self, other: object) -> bool:
        """Implementa comparación de igualdad."""
        if not isinstance(other, NewsItem):
            return NotImplemented
        return self.link == other.link