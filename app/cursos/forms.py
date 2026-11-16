from django import forms

from .models import Aula, AulaTexto, AulaVideo, Curso, Modulo, Questionario


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ('titulo', 'descricao', 'preco')


class ModuloForm(forms.ModelForm):
    class Meta:
        model = Modulo
        fields = ('titulo', 'ordem')

    def clean_ordem(self):
        ordem = self.cleaned_data['ordem']
        if Modulo.objects.filter(curso=self.instance.curso, ordem=ordem).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Já existe um módulo nesta ordem.')
        return ordem


class AulaForm(forms.ModelForm):
    def clean_ordem(self):
        ordem = self.cleaned_data['ordem']
        if Aula.objects.filter(modulo=self.instance.modulo, ordem=ordem).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Já existe uma aula nesta ordem.')
        return ordem


class AulaVideoForm(AulaForm):
    class Meta:
        model = AulaVideo
        fields = ('titulo', 'ordem', 'url_video', 'duracao_segundos')


class AulaTextoForm(AulaForm):
    class Meta:
        model = AulaTexto
        fields = ('titulo', 'ordem', 'texto')


class QuestionarioForm(AulaForm):
    class Meta:
        model = Questionario
        fields = ('titulo', 'ordem', 'questoes')
        help_texts = {'questoes': (
            'Use uma lista JSON. Exemplo de questão com duas opções e a primeira correta '
            '[{"enunciado": "Qual linguagem usamos?", "opcoes": ["Python", "Java"], "correta": 0}]'
        )}
