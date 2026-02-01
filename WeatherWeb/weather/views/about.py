from django.views import View
from django.shortcuts import render


class AboutView(View):
    """
    About view - Documentation and architecture explanation
    """
    template_name = "weather/about.html"

    def get(self, request):
        """
        Render about page - no data processing needed
        """
        return render(request, self.template_name)
