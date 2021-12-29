from django import template
from django.utils.html import format_html


register = template.Library()
yellow = """<span class="Rating-star Rating-star_view">
<svg xmlns="http://www.w3.org/2000/svg" width="19" height="18" viewBox="0 0 19 18">
    <g><g>
    <path fill="#ffc000"
          d="M9.5 14.925L3.629 18l1.121-6.512L0 6.875l6.564-.95L9.5 0l2.936 5.925 6.564.95-4.75 4.613L15.371 18z">
    </path>
    </g></g>
    </svg>
</span>"""

gray = """<span class="Rating-star">
<svg xmlns="http://www.w3.org/2000/svg" width="19" height="18" viewBox="0 0 19 18">
    <g><g><path fill="#ffc000"
                d="M9.5 14.925L3.629 18l1.121-6.512L0 6.875l6.564-.95L9.5 0l2.936 5.925 6.564.95-4.75 4.613L15.371 18z"
          >
    </path></g></g></svg>
</span>"""


@register.simple_tag
def yellow_star(count):
    """
    тэг возвращает рейтинг звёзд в шаблон
    """
    return format_html(yellow * count + gray * (5 - count))
