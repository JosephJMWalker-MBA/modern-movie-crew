from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.characters.models import (
    Character,
    CharacterIdentityVersion,
    CharacterLook,
    CharacterRightsRecord,
)
from apps.projects.models import Membership, Project

User = get_user_model()


class CharactersModelBoundaryTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u1", password="p")
        self.project_a = Project.objects.create(
            name="Proj A", slug="proj-a", created_by=self.user
        )
        self.project_b = Project.objects.create(
            name="Proj B", slug="proj-b", created_by=self.user
        )

        self.member_a = Membership.objects.create(
            project=self.project_a, user=self.user, credited_name="User A"
        )
        self.member_b = Membership.objects.create(
            project=self.project_b, user=self.user, credited_name="User B"
        )

        self.char_a = Character.objects.create(
            project=self.project_a, name="Imani"
        )

    def test_identity_version_cross_project_approval_rejection(self):
        identity_v1 = CharacterIdentityVersion(
            character=self.char_a,
            version_number=1,
            approved_by=self.member_b,
        )
        with self.assertRaises(ValidationError):
            identity_v1.save()

    def test_character_look_cross_project_creation_rejection(self):
        look = CharacterLook(
            character=self.char_a,
            name="Airlock Suit",
            created_by=self.member_b,
        )
        with self.assertRaises(ValidationError):
            look.save()

    def test_character_rights_record_cross_project_rejection(self):
        rights = CharacterRightsRecord(
            character=self.char_a,
            licensor_name="Imani Actor",
            actor_membership=self.member_b,
        )
        with self.assertRaises(ValidationError):
            rights.save()
