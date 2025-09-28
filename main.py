import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import urllib.parse
import re
from dataclasses import dataclass
from typing import List

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Замените на ваш токен бота
BOT_TOKEN = ""

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dataclass
class Product:
    marketplace: str
    name: str
    price: int
    rating: float
    feedbacks: int
    image_url: str
    product_url: str
    product_id: str = ""

class WildberriesScraper:
    def __init__(self):
        self.driver = None
    
    def setup_driver(self):
        """Настройка Chrome WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
    
    def search_products(self, query: str, limit: int = 5) -> List[Product]:
        """Поиск товаров в Wildberries"""
        try:
            if not self.driver:
                self.setup_driver()
                
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.wildberries.ru/catalog/0/search.aspx?search={encoded_query}"
            
            logger.info(f"Wildberries: Opening URL: {url}")
            self.driver.get(url)
            
            # Ждем загрузки результатов
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product-card"))
            )
            
            time.sleep(3)
            return self.parse_search_results(limit)
            
        except Exception as e:
            logger.error(f"Wildberries search error: {e}")
            return []
    
    def parse_search_results(self, limit):
        """Парсинг результатов поиска Wildberries"""
        products = []
        
        try:
            product_cards = self.driver.find_elements(By.CLASS_NAME, "product-card")[:limit]
            
            for card in product_cards:
                try:
                    product = self.parse_product_card(card)
                    if product:
                        products.append(product)
                except Exception as e:
                    logger.error(f"Error parsing Wildberries product card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Wildberries parse results error: {e}")
        
        return products
    
    def parse_product_card(self, card):
        """Парсинг отдельной карточки товара Wildberries"""
        try:
            product_id = card.get_attribute("data-nm-id")
            if not product_id:
                return None
            
            # Название товара
            name_element = card.find_element(By.CLASS_NAME, "product-card__name")
            name = name_element.text.strip() if name_element else "Название не указано"
            
            # Бренд
            brand_element = card.find_element(By.CLASS_NAME, "product-card__brand")
            brand = brand_element.text.strip() if brand_element else "Бренд не указан"
            
            # Цена
            price = 0
            try:
                price_element = card.find_element(By.CLASS_NAME, "price__lower-price")
                price_text = price_element.text.strip() if price_element else "0"
                price = int(re.sub(r'[^\d]', '', price_text))
            except:
                pass
            
            # Рейтинг
            rating = 0
            try:
                rating_element = card.find_element(By.CLASS_NAME, "product-card__rating")
                rating_text = rating_element.get_attribute("textContent").strip()
                rating = float(rating_text) if rating_text else 0
            except:
                pass
            
            # Количество отзывов
            feedbacks = 0
            try:
                feedbacks_element = card.find_element(By.CLASS_NAME, "product-card__count")
                feedbacks_text = feedbacks_element.text.strip().replace("(", "").replace(")", "")
                feedbacks = int(feedbacks_text) if feedbacks_text.isdigit() else 0
            except:
                pass
            
            # Ссылка на товар
            product_url = f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx"
            
            # Изображение
            image_url = self.get_product_image(product_id)
            
            return Product(
                marketplace="Wildberries",
                name=f"{brand} - {name}",
                price=price,
                rating=rating,
                feedbacks=feedbacks,
                image_url=image_url,
                product_url=product_url,
                product_id=product_id
            )
            
        except Exception as e:
            logger.error(f"Wildberries parse card error: {e}")
            return None
    
    def get_product_image(self, product_id):
        """Получение URL изображения товара Wildberries"""
        if not product_id:
            return "https://via.placeholder.com/400x300/7100FF/FFFFFF?text=No+Image"
        
        try:
            vol = int(product_id) // 100000
            part = int(product_id) // 1000
            return f"https://basket-{vol:02d}.wbbasket.ru/vol{vol}/part{part}/{product_id}/images/c516x688/1.jpg"
        except:
            return "https://via.placeholder.com/400x300/7100FF/FFFFFF?text=No+Image"
    
    def close(self):
        """Закрытие драйвера"""
        if self.driver:
            self.driver.quit()

# Создаем экземпляр скрейпера только для Wildberries
wb_scraper = WildberriesScraper()

def create_search_keyboards(query: str):
    """Создание клавиатур для поиска в других маркетплейсах"""
    encoded_query = urllib.parse.quote(query)
    
    # Клавиатура для быстрого перехода к поиску
    search_keyboard = InlineKeyboardBuilder()
    search_keyboard.add(
        InlineKeyboardButton(
            text="🔍 Искать в OZON",
            url=f"https://www.ozon.ru/search/?text={encoded_query}"
        ),
        InlineKeyboardButton(
            text="🔍 Искать в Яндекс Маркете", 
            url=f"https://market.yandex.ru/search?text={encoded_query}"
        )
    )
    
    # Клавиатура для сравнения цен
    compare_keyboard = InlineKeyboardBuilder()
    compare_keyboard.add(
        InlineKeyboardButton(
            text="🔄 Сравнить цены в других магазинах",
            url=f"https://www.ozon.ru/search/?text={encoded_query}"
        )
    )
    
    return search_keyboard.as_markup(), compare_keyboard.as_markup()

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        "👋 Привет! Я помогу найти товары по лучшим ценам!\n\n"
        "🔍 Просто отправь мне название товара, например:\n"
        "• \"кеды\"\n"
        "• \"кроссовки nike\"\n"
        "• \"телефон\"\n\n"
        "Я покажу товары из Wildberries и помогу сравнить цены в других маркетплейсах!"
    )

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    help_text = (
        "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
        "1. Отправь название товара\n"
        "2. Я найду товары в Wildberries\n"
        "3. Покажу цены, фото и ссылки\n"
        "4. Предоставлю кнопки для поиска в других магазинах\n\n"
        "<b>Примеры запросов:</b>\n"
        "• <code>кеды</code>\n"
        "• <code>куртка зимняя</code>\n"
        "• <code>redmi 15c</code>\n\n"
        "💡 <b>Совет:</b> Используйте кнопки под сообщениями для быстрого перехода в другие маркетплейсы!"
    )
    await message.answer(help_text, parse_mode="HTML")

@dp.message(F.text)
async def search_handler(message: types.Message):
    query = message.text.strip()
    
    if len(query) < 2:
        await message.answer("❌ Слишком короткий запрос. Попробуйте ввести более конкретное название товара.")
        return
    
    # Создаем клавиатуры для поиска
    search_keyboard, compare_keyboard = create_search_keyboards(query)
    
    # Отправляем сообщение о начале поиска
    search_message = await message.answer("🔍 Ищу товары в Wildberries...")
    
    try:
        # Ищем товары в Wildberries
        products = wb_scraper.search_products(query, limit=5)
        
        if not products:
            await search_message.edit_text(
                f"❌ По запросу \"{query}\" ничего не найдено в Wildberries.\n\n"
                "Попробуйте:\n"
                "• Изменить формулировку\n"
                "• Проверить орфографию\n"
                "• Использовать более общий запрос"
            )
            # Предлагаем поискать в других магазинах
            await message.answer(
                "💡 Попробуйте поискать в других маркетплейсах:",
                reply_markup=search_keyboard
            )
            return
        
        # Редактируем сообщение о результате
        await search_message.edit_text(
            f"✅ Нашёл {len(products)} товаров по запросу \"{query}\" в Wildberries:",
            reply_markup=compare_keyboard
        )
        
        # Отправляем каждый товар отдельным сообщением
        for i, product in enumerate(products, 1):
            caption = (
                f"🏷️ <b>{product.name}</b>\n\n"
                f"💰 <b>Цена:</b> {product.price:,} ₽\n"
                f"⭐ <b>Рейтинг:</b> {product.rating}\n"
                f"💬 <b>Отзывы:</b> {product.feedbacks}\n"
                f"🆔 <b>Артикул:</b> {product.product_id}"
            )
            
            keyboard = InlineKeyboardBuilder()
            keyboard.add(InlineKeyboardButton(
                text="🛒 Перейти к товару",
                url=product.product_url
            ))
            
            try:
                await message.answer_photo(
                    photo=product.image_url,
                    caption=caption,
                    reply_markup=keyboard.as_markup(),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error sending photo: {e}")
                await message.answer(
                    f"{caption}\n\n🔗 Ссылка: {product.product_url}",
                    parse_mode="HTML",
                    reply_markup=keyboard.as_markup()
                )
            
            # Небольшая задержка между сообщениями
            await asyncio.sleep(0.5)
        
        # Показываем сравнение цен (только для Wildberries)
        await send_price_comparison(message, products, query)
        
        # Предлагаем поискать в других магазинах
        await message.answer(
            "💡 <b>Хотите сравнить цены в других магазинах?</b>\n\n"
            "Нажмите на кнопки ниже для быстрого перехода:",
            parse_mode="HTML",
            reply_markup=search_keyboard
        )
                
    except Exception as e:
        logger.error(f"Search handler error: {e}")
        await search_message.edit_text(
            "❌ Произошла ошибка при поиске товаров.\n"
            "Пожалуйста, попробуйте позже."
        )
        # Все равно предлагаем поискать в других магазинах
        await message.answer(
            "💡 Попробуйте поискать в других маркетплейсах:",
            reply_markup=search_keyboard
        )

async def send_price_comparison(message: types.Message, products: List[Product], query: str):
    """Отправка сравнения цен"""
    if not products:
        return
    
    # Сортируем товары по цене
    sorted_products = sorted(products, key=lambda x: x.price)
    
    # Формируем сообщение со сравнением
    comparison_text = f"🏆 <b>Сравнение цен в Wildberries по запросу \"{query}\"</b>\n\n"
    
    for i, product in enumerate(sorted_products[:5], 1):
        comparison_text += (
            f"{i}. 🏷️ <b>{product.name[:60]}...</b>\n"
            f"   💰 <b>{product.price:,} ₽</b>\n"
            f"   ⭐ {product.rating} | 💬 {product.feedbacks}\n\n"
        )
    
    # Находим самый дешевый товар
    cheapest = sorted_products[0]
    comparison_text += f"💡 <b>Самый дешевый вариант:</b>\n"
    comparison_text += f"💰 {cheapest.price:,} ₽\n"
    comparison_text += f"🔗 {cheapest.product_url}"
    
    await message.answer(comparison_text, parse_mode="HTML")

@dp.message(Command("search_ozon"))
async def search_ozon_handler(message: types.Message):
    """Команда для быстрого поиска в Ozon"""
    await message.answer(
        "🔍 Для поиска в Ozon отправьте мне название товара, "
        "и я предоставлю ссылку для быстрого перехода!"
    )

@dp.message(Command("search_yandex"))
async def search_yandex_handler(message: types.Message):
    """Команда для быстрого поиска в Яндекс Маркете"""
    await message.answer(
        "🔍 Для поиска в Яндекс Маркете отправьте мне название товара, "
        "и я предоставлю ссылку для быстрого перехода!"
    )

@dp.shutdown()
async def on_shutdown():
    """Очистка ресурсов при завершении работы"""
    wb_scraper.close()

async def main():
    logger.info("Бот запускается...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())