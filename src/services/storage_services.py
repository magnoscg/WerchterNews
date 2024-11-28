import json
import logging
from pathlib import Path
from typing import Dict, Set, Optional
from datetime import datetime
from ..models import NewsItem

logger = logging.getLogger(__name__)

class StorageService:
    """
    Servicio de almacenamiento persistente para control de estado de noticias.
    Implementa el patrón Repository con cache en memoria para optimizar rendimiento.
    """
    def __init__(self, storage_path: str = "data/processed_news.json"):
        self.storage_path = Path(storage_path)
        self._processed_news: Dict[str, dict] = {}
        self._processed_links: Set[str] = set()
        self._ensure_storage_exists()
        self._load_processed_news()

    def _ensure_storage_exists(self) -> None:
        """Asegura que el directorio y archivo de almacenamiento existan."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.storage_path.exists():
            self._save_processed_news({})

    def _load_processed_news(self) -> None:
        """
        Carga el estado desde almacenamiento persistente con manejo robusto de errores.
        """
        try:
            content = self.storage_path.read_text()
            self._processed_news = json.loads(content)
            # Actualiza el conjunto de enlaces procesados para búsqueda O(1)
            self._processed_links = set(self._processed_news.keys())
            logger.info(f"Cargadas {len(self._processed_links)} noticias procesadas")
        except Exception as e:
            logger.error(f"Error cargando noticias procesadas: {str(e)}")
            self._processed_news = {}
            self._processed_links = set()

    def _save_processed_news(self, data: Optional[Dict] = None) -> None:
        """
        Persiste el estado actual con formateo JSON legible.
        
        Args:
            data: Datos a persistir. Si es None, usa el estado actual.
        """
        try:
            content = json.dumps(
                data if data is not None else self._processed_news,
                indent=2,
                ensure_ascii=False
            )
            self.storage_path.write_text(content)
            logger.debug("Estado persistido exitosamente")
        except Exception as e:
            logger.error(f"Error persistiendo estado: {str(e)}")

    def is_processed(self, news_item: NewsItem) -> bool:
        """
        Verifica si una noticia ya ha sido procesada.
        Implementa búsqueda O(1) usando set en memoria.
        """
        return news_item.link in self._processed_links

    def mark_as_processed(self, news_item: NewsItem) -> None:
        """
        Marca una noticia como procesada y persiste el estado.
        
        Args:
            news_item: Noticia a marcar como procesada
        """
        if not self.is_processed(news_item):
            self._processed_news[news_item.link] = {
                'title': news_item.title,
                'date': news_item.formatted_date,
                'link': news_item.link,
                'image_url': news_item.image_url,
                'processed_at': datetime.now().isoformat()
            }
            self._processed_links.add(news_item.link)
            self._save_processed_news()
            logger.info(f"Nueva noticia marcada como procesada: {news_item.title}")

    def get_unprocessed_news(self, news_items: list[NewsItem]) -> list[NewsItem]:
        """
        Filtra y retorna solo las noticias no procesadas.
        
        Args:
            news_items: Lista de noticias a filtrar
            
        Returns:
            Lista de noticias no procesadas
        """
        return [
            news_item for news_item in news_items 
            if not self.is_processed(news_item)
        ]

    def cleanup_old_entries(self, max_age_days: int = 30) -> None:
        """
        Limpia entradas antiguas del almacenamiento para optimizar rendimiento.
        
        Args:
            max_age_days: Edad máxima de entradas en días
        """
        try:
            current_time = datetime.now()
            entries_to_remove = []
            
            for link, data in self._processed_news.items():
                processed_time = datetime.fromisoformat(data['processed_at'])
                age_days = (current_time - processed_time).days
                
                if age_days > max_age_days:
                    entries_to_remove.append(link)
            
            for link in entries_to_remove:
                self._processed_news.pop(link)
                self._processed_links.remove(link)
            
            if entries_to_remove:
                self._save_processed_news()
                logger.info(f"Limpiadas {len(entries_to_remove)} entradas antiguas")
                
        except Exception as e:
            logger.error(f"Error durante limpieza de entradas: {str(e)}")