from django import forms


class RespostasForm(forms.Form):
    def __init__(self, questoes, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for indice, questao in enumerate(questoes):
            self.fields[f'questao_{indice}'] = forms.TypedChoiceField(
                label=questao['enunciado'], coerce=int, widget=forms.RadioSelect,
                choices=list(enumerate(questao['opcoes'])),
            )

    @property
    def respostas(self):
        return list(self.cleaned_data.values())
