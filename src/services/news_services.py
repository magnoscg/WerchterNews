import logging
from typing import List
import aiohttp
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from ..models import NewsItem

logger = logging.getLogger(__name__)

class NewsService:
    """Servicio para obtener y procesar noticias de Rock Werchter."""
    
    def __init__(self, base_url: str = "https://www.rockwerchter.be/en/"):
        self.base_url = base_url
    
    async def get_news(self) -> List[NewsItem]:
        """
        Obtiene las noticias ordenadas por fecha ascendente.
        
        Returns:
            List[NewsItem]: Lista ordenada de noticias
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url) as response:
                    if response.status != 200:
                        logger.error(f"Error fetching news: Status {response.status}")
                        return []
                    
                    html = await response.text()
                    news_items = self._parse_news_content(html)
                    
                    # Ordena las noticias por fecha
                    return sorted(news_items)
                    
        except Exception as e:
            logger.error(f"Error fetching news: {str(e)}", exc_info=True)
            return []
    
    def _parse_news_content(self, html: str) -> List[NewsItem]:
        """Parse del contenido HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        
        for card in soup.select('.card-grid__grid .card'):
            try:
                news_item = self._parse_news_card(card)
                if news_item:
                    news_items.append(news_item)
            except Exception as e:
                logger.error(f"Error parsing news card: {str(e)}", exc_info=True)
                continue
                
        return news_items
            
    def _parse_news_card(self, card) -> NewsItem:
        """Parse de una tarjeta de noticia individual."""
        link = urljoin(self.base_url, card.get('href', ''))
        title = card.select_one('.card__title').text.strip()
        
        date_element = card.select_one('.card__info')
        date = date_element.text.split('visit')[0].strip() if date_element else ''
        
        image = card.select_one('.card__image img')
        image_url = urljoin(self.base_url, image['src']) if image and 'src' in image.attrs else None
        
        return NewsItem(
            title=title,
            date=date,
            link=link,
            image_url=image_url
        )