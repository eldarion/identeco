import urlparse

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.views.generic.edit import FormView
from django.utils.decorators import method_decorator

from openid.consumer.discover import OPENID_IDP_2_0_TYPE
from openid.extensions import sreg
from openid.server.server import Server
from openid.server.server import EncodingError, ProtocolError
from openid.yadis.constants import YADIS_CONTENT_TYPE

from identeco.forms import TrustForm
from identeco.models import Trust
from identeco.utils import load_path_attr


LOGIN_REQUIRED = getattr(settings, "IDENTECO_LOGIN_REQUIRED", "django.contrib.auth.decorators.login_required")


class OpenIDView(object):

    def get_openid_store(self):
        store = getattr(settings, "IDENTECO_STORE", "identeco.store.DjangoORMStore")
        return load_path_attr(store)()

    def get_openid_endpoint(self):
        return self.request.build_absolute_uri(reverse("identeco_endpoint"))

    def get_openid_server(self):
        return Server(self.get_openid_store(), self.get_openid_endpoint())

    def render_openid_response(self, openid_response):
        if not hasattr(self, "server"):
            self.server = self.get_openid_server()
        try:
            webresponse = self.server.encodeResponse(openid_response)
        except EncodingError as e:
            self.template_name = self.template_names["error"]
            return self.render_to_response({"error": e.response.encodeToKVForm()})
        response = HttpResponse(webresponse.body)
        response.status_code = webresponse.code
        for header, value in webresponse.headers.iteritems():
            response[header] = value
        return response


class OpenIDUserData(object):

    def add_sreg(self, request, response, user):
        sreg_req = sreg.SRegRequest.fromOpenIDRequest(request)
        sreg_data = {
            "nickname": user.username,
        }
        sreg_resp = sreg.SRegResponse.extractResponse(sreg_req, sreg_data)
        response.addExtension(sreg_resp)


class DecideTrust(OpenIDView, OpenIDUserData, FormView):

    form_class = TrustForm
    template_name = "identeco/trust/decide.html"

    def get_initial(self):
        initial = super(DecideTrust, self).get_initial()
        initial.update({
            "trust_root": self.request.session.get("openid_request").trust_root,
        })
        return initial

    def get_form_kwargs(self):
        kwargs = super(DecideTrust, self).get_form_kwargs()
        kwargs.update({
            "openid_request": self.request.session.get("openid_request"),
        })
        return kwargs

    def form_valid(self, form):
        if form.cleaned_data["always_trust"]:
            Trust.objects.get_or_create(
                user=self.request.user,
                trust_root=form.cleaned_data["trust_root"],
                defaults={"always_trust": form.cleaned_data["always_trust"]}
            )
        identity = self.request.build_absolute_uri(reverse("identeco_identity", kwargs={"username": self.request.user.username}))
        openid_request = self.request.session.get("openid_request")
        if self.request.POST.get("allow"):
            openid_response = openid_request.answer(True, identity=identity)
            self.add_sreg(openid_request, openid_response, self.request.user)
        else:
            openid_response = openid_request.answer(False, identity=identity)
        return self.render_openid_response(openid_response)

    def get(self, request, *args, **kwargs):
        identity = self.request.build_absolute_uri(reverse("identeco_identity", kwargs={"username": self.request.user.username}))
        openid_request = self.request.session.get("openid_request")
        url = urlparse.urlparse(openid_request.trust_root)
        trusted_domains = getattr(settings, "IDENTECO_TRUSTED_DOMAINS", [])
        if url.hostname in trusted_domains:
            trusted = True
        else:
            try:
                t = Trust.objects.get(user=self.request.user, trust_root=openid_request.trust_root)
            except Trust.DoesNotExist:
                trusted = False
            else:
                trusted = t.always_trust
        if trusted:
            openid_response = openid_request.answer(True, identity=identity)
            self.add_sreg(openid_request, openid_response, self.request.user)
            return self.render_openid_response(openid_response)
        else:
            return super(DecideTrust, self).get(request, *args, **kwargs)

    @method_decorator(load_path_attr(LOGIN_REQUIRED))
    def dispatch(self, *args, **kwargs):
        return super(DecideTrust, self).dispatch(*args, **kwargs)


class Endpoint(OpenIDView, OpenIDUserData, TemplateView):

    template_names = {
        "error": "identeco/endpoint/error.html",
        "empty": "identeco/endpoint/empty.html",
    }

    def handle_checkid(self):
        # @@@ Do Something with self.openid_request.idSelect()
        print "~>", self.openid_request.idSelect()
        if self.openid_request.immediate:
            if self.request.user.is_authorized():
                try:
                    t = Trust.objects.get(user=self.request.user, trust_root=self.openid_request.trust_root)
                    if t.always_trust:
                        identity = self.request.build_absolute_uri(reverse("identeco_identity", kwargs={"username": self.request.user.username}))
                        openid_response = self.openid_request.answer(True, identity=identity)
                        self.add_sreg(self.openid_request, openid_response, self.request.user)
                        return self.render_openid_response(openid_response)
                except Trust.DoesNotExist:
                    pass
            return self.render_openid_response(self.openid_request.answer(False))
        else:
            self.request.session["openid_request"] = self.openid_request
            return HttpResponseRedirect(reverse("identeco_decide_trust"))

    def process_openid_request(self, data):
        self.server = self.get_openid_server()
        try:
            self.openid_request = self.server.decodeRequest(data)
        except ProtocolError as e:
            self.template_name = self.template_names["error"]
            return self.render_to_response({"error": str(e)})
        if self.openid_request is None:
            self.template_name = self.template_names["empty"]
            return self.render_to_response({})
        if self.openid_request.mode in ["checkid_immediate", "checkid_setup"]:
            return self.handle_checkid()
        else:
            return self.render_openid_response(self.server.handleRequest(self.openid_request))

    def get(self, request, *args, **kwargs):
        return self.process_openid_request(request.GET.dict())

    def post(self, request, *args, **kwargs):
        return self.process_openid_request(request.POST.dict())

    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(Endpoint, self).dispatch(*args, **kwargs)


class XRDS(TemplateView):

    template_name = "identeco/xrds.xml"
    identity = False

    def get_type_uris(self):
        if self.identity:
            return ["http://specs.openid.net/auth/2.0/signon"]
        return [OPENID_IDP_2_0_TYPE, "http://specs.openid.net/auth/2.0/signon"]

    def get_endpoint_uris(self):
        return [self.request.build_absolute_uri(reverse("identeco_endpoint"))] + getattr(settings, "IDENTECO_EXTRA_ENDPOINTS", [])

    def get_context_data(self, **kwargs):
        ctx = super(XRDS, self).get_context_data(**kwargs)
        ctx.update({
            "type_uris": self.get_type_uris(),
            "endpoint_uris": self.get_endpoint_uris(),
            "local_id": None if not self.identity else self.request.build_absolute_uri(reverse("identeco_identity", kwargs={"username": self.kwargs["username"]})),
        })
        return ctx

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        return self.render_to_response(context, content_type=YADIS_CONTENT_TYPE)


class Identity(TemplateView):
    template_name = "identeco/identity.html"

    def get_context_data(self, **kwargs):
        ctx = super(Identity, self).get_context_data(**kwargs)
        ctx.update({
            "username": self.kwargs.get("username"),
        })
        return ctx
