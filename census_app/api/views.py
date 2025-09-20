from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from census_app.surveys.models import Survey
from census_app.surveys.models import SurveyQuestion, QuestionGroup
from rest_framework.decorators import action


User = get_user_model()


class SurveySerializer(serializers.ModelSerializer):
    class Meta:
        model = Survey
        fields = ["id", "name", "slug", "description", "start_at", "end_at"]


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]


class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, "owner_id", None) == getattr(request.user, "id", None)


class SurveyViewSet(viewsets.ModelViewSet):
    serializer_class = SurveySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return Survey.objects.filter(owner=self.request.user)
        return Survey.objects.none()

    def perform_create(self, serializer):
        obj = serializer.save(owner=self.request.user)
        import os
        key = os.urandom(32)
        obj.set_key(key)
        # Attach to serializer context for response augmentation
        self._created_key = key

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def seed(self, request, pk=None):
        survey = self.get_object()
        payload = request.data
        created = 0
        # JSON schema: [{text, type, options=[], group_name, order}]
        items = payload if isinstance(payload, list) else payload.get("items", [])
        for item in items:
            group = None
            gname = item.get("group_name")
            if gname:
                group, _ = QuestionGroup.objects.get_or_create(name=gname, owner=request.user)
            SurveyQuestion.objects.create(
                survey=survey,
                group=group,
                text=item.get("text", "Untitled"),
                type=item.get("type", "text"),
                options=item.get("options", []),
                required=bool(item.get("required", False)),
                order=int(item.get("order", 0)),
            )
            created += 1
        return Response({"created": created})

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        # Return base64 key once to creator
        key = getattr(self, "_created_key", None)
        if key is not None:
            import base64
            resp.data["one_time_key_b64"] = base64.b64encode(key).decode("ascii")
        return resp


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def healthcheck(request):
    return Response({"status": "ok"})
