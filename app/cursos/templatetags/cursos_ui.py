from django import template
from django.templatetags.static import static

register = template.Library()


@register.filter
def capa_curso(curso):
    if curso.capa_url:
        return curso.capa_url
    titulo = curso.titulo.lower()
    if any(palavra in titulo for palavra in ('python', 'programa', 'django', 'desenvolvimento', 'código')):
        return static('images/programacao.jpg')
    return static('images/estudos.jpg')
