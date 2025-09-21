from django.contrib.auth import get_user_model
from rest_framework import viewsets, permissions, serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from census_app.surveys.models import Survey
from census_app.surveys.models import SurveyQuestion, QuestionGroup, OrganizationMembership, SurveyMembership, Organization, AuditLog
from rest_framework.decorators import action
from census_app.surveys.permissions import can_view_survey, can_edit_survey


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


class OrgOwnerOrAdminPermission(permissions.BasePermission):
    """Object-level permission that mirrors SSR rules using surveys.permissions.

    - SAFE methods require can_view_survey
    - Unsafe methods require can_edit_survey
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return can_view_survey(request.user, obj)
        return can_edit_survey(request.user, obj)


class SurveyViewSet(viewsets.ModelViewSet):
    serializer_class = SurveySerializer
    permission_classes = [permissions.IsAuthenticated, OrgOwnerOrAdminPermission]

    def get_queryset(self):
        user = self.request.user
        # Owner's surveys
        owned = Survey.objects.filter(owner=user)
        # Org-admin surveys: any survey whose organization has the user as ADMIN
        org_admin = Survey.objects.filter(
            organization__memberships__user=user,
            organization__memberships__role=OrganizationMembership.Role.ADMIN,
        )
        return (owned | org_admin).distinct()

    def get_object(self):
        """Fetch object without scoping to queryset, then run object permissions.

        This ensures authenticated users receive 403 (Forbidden) rather than
        404 (Not Found) when they lack permission on an existing object.
        """
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs.get(lookup_url_kwarg)
        obj = Survey.objects.select_related("organization").get(**{self.lookup_field: lookup_value})
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        obj = serializer.save(owner=self.request.user)
        import os
        key = os.urandom(32)
        obj.set_key(key)
        # Attach to serializer context for response augmentation
        self._created_key = key

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated, OrgOwnerOrAdminPermission],
    )
    def seed(self, request, pk=None):
        survey = self.get_object()
        # get_object already runs object permission checks via check_object_permissions
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


class OrganizationMembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = OrganizationMembership
        fields = ["id", "organization", "user", "username", "role", "created_at"]
        read_only_fields = ["created_at"]


class SurveyMembershipSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())

    class Meta:
        model = SurveyMembership
        fields = ["id", "survey", "user", "username", "role", "created_at"]
        read_only_fields = ["created_at"]


class OrganizationMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # Only orgs where the user is admin
        admin_orgs = Organization.objects.filter(memberships__user=user, memberships__role=OrganizationMembership.Role.ADMIN)
        return OrganizationMembership.objects.filter(organization__in=admin_orgs).select_related("user", "organization")

    def perform_create(self, serializer):
        org = serializer.validated_data.get("organization")
        if not OrganizationMembership.objects.filter(organization=org, user=self.request.user, role=OrganizationMembership.Role.ADMIN).exists():
            raise PermissionDenied("Not an admin for this organization")
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            scope=AuditLog.Scope.ORGANIZATION,
            organization=org,
            action=AuditLog.Action.ADD,
            target_user=instance.user,
            metadata={"role": instance.role},
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        org = instance.organization
        if not OrganizationMembership.objects.filter(organization=org, user=self.request.user, role=OrganizationMembership.Role.ADMIN).exists():
            raise PermissionDenied("Not an admin for this organization")
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            scope=AuditLog.Scope.ORGANIZATION,
            organization=org,
            action=AuditLog.Action.UPDATE,
            target_user=instance.user,
            metadata={"role": instance.role},
        )

    def perform_destroy(self, instance):
        org = instance.organization
        if not OrganizationMembership.objects.filter(organization=org, user=self.request.user, role=OrganizationMembership.Role.ADMIN).exists():
            raise PermissionDenied("Not an admin for this organization")
        # Prevent org admin removing themselves
        if instance.user_id == self.request.user.id and instance.role == OrganizationMembership.Role.ADMIN:
            raise PermissionDenied("You cannot remove yourself as an organization admin")
        instance.delete()
        AuditLog.objects.create(
            actor=self.request.user,
            scope=AuditLog.Scope.ORGANIZATION,
            organization=org,
            action=AuditLog.Action.REMOVE,
            target_user=instance.user,
            metadata={"role": instance.role},
        )


class SurveyMembershipViewSet(viewsets.ModelViewSet):
    serializer_class = SurveyMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        # user can see memberships for surveys they can view
        allowed_survey_ids = []
        for s in Survey.objects.all():
            if s.owner_id == user.id:
                allowed_survey_ids.append(s.id)
            elif s.organization_id and OrganizationMembership.objects.filter(
                organization=s.organization, user=user, role=OrganizationMembership.Role.ADMIN
            ).exists():
                allowed_survey_ids.append(s.id)
            elif SurveyMembership.objects.filter(user=user, survey=s).exists():
                allowed_survey_ids.append(s.id)
        return SurveyMembership.objects.filter(survey_id__in=allowed_survey_ids).select_related("user", "survey")

    def _can_manage(self, survey: Survey) -> bool:
        # org admin, owner, or survey creator can manage
        if survey.owner_id == self.request.user.id:
            return True
        if survey.organization_id and OrganizationMembership.objects.filter(
            organization=survey.organization, user=self.request.user, role=OrganizationMembership.Role.ADMIN
        ).exists():
            return True
        return SurveyMembership.objects.filter(user=self.request.user, survey=survey, role=SurveyMembership.Role.CREATOR).exists()

    def perform_create(self, serializer):
        survey = serializer.validated_data.get("survey")
        if not self._can_manage(survey):
            raise PermissionDenied("Not allowed to manage users for this survey")
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            scope=AuditLog.Scope.SURVEY,
            survey=instance.survey,
            action=AuditLog.Action.ADD,
            target_user=instance.user,
            metadata={"role": instance.role},
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        if not self._can_manage(instance.survey):
            raise PermissionDenied("Not allowed to manage users for this survey")
        instance = serializer.save()
        AuditLog.objects.create(
            actor=self.request.user,
            scope=AuditLog.Scope.SURVEY,
            survey=instance.survey,
            action=AuditLog.Action.UPDATE,
            target_user=instance.user,
            metadata={"role": instance.role},
        )

    def perform_destroy(self, instance):
        if not self._can_manage(instance.survey):
            raise PermissionDenied("Not allowed to manage users for this survey")
        instance.delete()
        AuditLog.objects.create(
            actor=self.request.user,
            scope=AuditLog.Scope.SURVEY,
            survey=instance.survey,
            action=AuditLog.Action.REMOVE,
            target_user=instance.user,
            metadata={"role": instance.role},
        )


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = User.objects.all()


class ScopedUserCreateSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)


class ScopedUserViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["post"], url_path="org/(?P<org_id>[^/.]+)/create")
    def create_in_org(self, request, org_id=None):
        # Only org admins can create users within their org context
        org = Organization.objects.get(id=org_id)
        if not OrganizationMembership.objects.filter(organization=org, user=request.user, role=OrganizationMembership.Role.ADMIN).exists():
            raise PermissionDenied("Not an admin for this organization")
        ser = ScopedUserCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        email = (data.get("email") or "").strip().lower()
        if email:
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                if User.objects.filter(username=data["username"]).exists():
                    raise serializers.ValidationError({"username": "already exists"})
                user = User.objects.create_user(username=data["username"], email=email, password=data["password"])
        else:
            if User.objects.filter(username=data["username"]).exists():
                raise serializers.ValidationError({"username": "already exists"})
            user = User.objects.create_user(username=data["username"], email="", password=data["password"])
        # Optionally add as viewer by default
        OrganizationMembership.objects.get_or_create(organization=org, user=user, defaults={"role": OrganizationMembership.Role.VIEWER})
        AuditLog.objects.create(
            actor=request.user,
            scope=AuditLog.Scope.ORGANIZATION,
            organization=org,
            action=AuditLog.Action.ADD,
            target_user=user,
            metadata={"created_via": "org"},
        )
        return Response({"id": user.id, "username": user.username, "email": user.email})

    @action(detail=False, methods=["post"], url_path="survey/(?P<survey_id>[^/.]+)/create")
    def create_in_survey(self, request, survey_id=None):
        # Survey creators/admins/owner can create users within the survey context
        survey = Survey.objects.get(id=survey_id)
        # Reuse the SurveyMembershipViewSet _can_manage logic inline
        def can_manage(user):
            if survey.owner_id == user.id:
                return True
            if survey.organization_id and OrganizationMembership.objects.filter(organization=survey.organization, user=user, role=OrganizationMembership.Role.ADMIN).exists():
                return True
            return SurveyMembership.objects.filter(user=user, survey=survey, role=SurveyMembership.Role.CREATOR).exists()

        if not can_manage(request.user):
            raise PermissionDenied("Not allowed to manage users for this survey")
        ser = ScopedUserCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        email = (data.get("email") or "").strip().lower()
        if email:
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                if User.objects.filter(username=data["username"]).exists():
                    raise serializers.ValidationError({"username": "already exists"})
                user = User.objects.create_user(username=data["username"], email=email, password=data["password"])
        else:
            if User.objects.filter(username=data["username"]).exists():
                raise serializers.ValidationError({"username": "already exists"})
            user = User.objects.create_user(username=data["username"], email="", password=data["password"])
        SurveyMembership.objects.get_or_create(survey=survey, user=user, defaults={"role": SurveyMembership.Role.VIEWER})
        AuditLog.objects.create(
            actor=request.user,
            scope=AuditLog.Scope.SURVEY,
            survey=survey,
            action=AuditLog.Action.ADD,
            target_user=user,
            metadata={"created_via": "survey"},
        )
        return Response({"id": user.id, "username": user.username, "email": user.email})


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def healthcheck(request):
    return Response({"status": "ok"})
