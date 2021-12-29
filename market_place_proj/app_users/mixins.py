from django.utils.functional import cached_property

from view_breadcrumbs import BaseBreadcrumbMixin


class AuthBaseBreadcrumbMixin(BaseBreadcrumbMixin):
    """Миксин для генерации breadcrumbs."""
    breadcrumbs = []

    @cached_property
    def crumbs(self):
        return self.breadcrumbs
