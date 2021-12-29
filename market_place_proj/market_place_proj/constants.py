class CacheTime:
    """Класс констант кэширования"""

    TIME = {'one_min': 60, 'one_hour': 3600, 'one_day': 86400, 'one_month' 'one_year': 31536000}
    GOOD_CARDS = TIME['one_day']
    SLIDER = TIME['one_min'] * 10
    DETAIL_PROD_PAGE = TIME['one_day']
    SIDEBARS = TIME['one_day']
    CATEGORIES = TIME['one_day']
    LIMIT_EDITION = TIME['one_day']
    HOT_PRODUCT = TIME['one_day']
    COUNT_PROD = TIME['one_day']
    DETAIL_PRODUCT = TIME['one_day']
    CATEGORY_MIN_PRICE = TIME['one_day']
    COMPARE_GOODS = TIME['one_day']
    TAGS_FOR_CATALOG_PAGE = TIME['one_day']

    @classmethod
    def set_minute(cls, minute):
        return 60 * minute

    @classmethod
    def set_hour(cls, hour):
        return 60 * 60 * hour

    @classmethod
    def set_day(cls, day):
        return 60 * 60 * 24 * day

    @classmethod
    def set_year(cls, year):
        return 60 * 60 * 24 * 365 * year


class CounterSettings:
    """
    Класс констант различных счетчиков
    """
    # количество товаров на главной странице из ограниченной серии
    LIMIT_EDITION_COUNT = 17
    LIMIT_HOT_GOOD_COUNT = 9
    BEST_CATEGORY_COUNT = 3
    VIEW_COUNT = 20
    TAG_COUNT = 7


# курс доллара для конвертации
USD = 74
