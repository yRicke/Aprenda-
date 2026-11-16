from django import forms


class CompraForm(forms.Form):
    cupom = forms.CharField(label='Cupom de desconto', max_length=40, required=False)
    token = forms.ChoiceField(label='Pagamento de demonstração', choices=[
        ('aprovar', 'Simular pagamento aprovado'),
        ('recusar', 'Simular pagamento recusado'),
        ('sem_resposta', 'Simular ausência de resposta'),
    ])
    oferta = forms.CharField(widget=forms.HiddenInput, required=False)
