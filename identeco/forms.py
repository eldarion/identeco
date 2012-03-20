from django import forms


class TrustForm(forms.Form):

    trust_root = forms.CharField()
    always_trust = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        self.openid_request = kwargs.pop("openid_request", None)
        super(TrustForm, self).__init__(*args, **kwargs)
