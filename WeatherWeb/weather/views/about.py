from django.views import View
from django.shortcuts import render
from weather.models import AboutContent


class AboutView(View):
    """
    About view – renders page content from the database (AboutContent model).
    Falls back to a static message if no content has been seeded yet.
    Use the management command 'seed_about_content' to populate initial data.
    """
    template_name = 'weather/about.html'

    def get(self, request):
        blocks = AboutContent.objects.filter(is_visible=True).order_by('order', 'key')
        return render(request, self.template_name, {'blocks': blocks})
