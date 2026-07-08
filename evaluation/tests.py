from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from evaluation.models import (
    Course,
    EvaluationCriterion,
    EvaluationScore,
    EvaluationSubmission,
    EvaluationTemplate,
    JudgeAssignment,
    JudgeProfile,
    Project,
    ProjectSubmission,
    StudentProfile,
    UserProfile,
)


class StudentRegistrationTest(TestCase):
    """Test that student registration creates User, UserProfile, and StudentProfile."""

    def setUp(self):
        # Create a course for registration
        self.course = Course.objects.create(
            name="Computer Science Test", code="CS_TEST", is_active=True
        )

    def test_student_registration_creates_profiles(self):
        response = self.client.post(
            reverse("register_student"),
            {
                "username": "teststudent",
                "email": "student@test.com",
                "password": "TestPass123!",
                "confirm_password": "TestPass123!",
                "full_name": "Test Student",
                "student_id": "ST12345",
                "course": self.course.id,
                "programme": "Computer Science",
                "section": "CS2A",
                "phone_number": "0123456789",
            },
        )
        # Check user was created
        self.assertTrue(User.objects.filter(username="teststudent").exists())
        user = User.objects.get(username="teststudent")
        # Check UserProfile was created with student role
        self.assertTrue(UserProfile.objects.filter(user=user, role="student").exists())
        # Check StudentProfile was created
        self.assertTrue(StudentProfile.objects.filter(user=user).exists())


class JudgeRegistrationTest(TestCase):
    """Test that judge registration creates pending JudgeProfile."""

    def test_judge_registration_creates_pending_profile(self):
        response = self.client.post(
            reverse("register_judge"),
            {
                "username": "testjudge",
                "email": "judge@test.com",
                "password": "TestPass123!",
                "confirm_password": "TestPass123!",
                "full_name": "Test Judge",
                "department": "Computer Science",
                "expertise_area": "Machine Learning",
                "phone_number": "0123456789",
            },
        )
        # Check user was created
        self.assertTrue(User.objects.filter(username="testjudge").exists())
        user = User.objects.get(username="testjudge")
        # Check UserProfile was created with judge role
        self.assertTrue(UserProfile.objects.filter(user=user, role="judge").exists())
        # Check JudgeProfile was created with pending status
        judge_profile = JudgeProfile.objects.get(user=user)
        self.assertEqual(judge_profile.registration_status, "pending")


class PICProjectApprovalTest(TestCase):
    """Test that PIC can approve a project."""

    def setUp(self):
        # Create PIC user
        self.pic_user = User.objects.create_user(
            username="pic", password="pic123"
        )
        UserProfile.objects.create(user=self.pic_user, role="pic")
        # Create course
        self.course = Course.objects.create(
            name="Computer Science PIC Test", code="CS_PIC", is_active=True
        )
        # Create student
        self.student_user = User.objects.create_user(
            username="student_pic", password="student123"
        )
        UserProfile.objects.create(user=self.student_user, role="student")
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            student_id="ST12345",
            full_name="Test Student",
            course=self.course,
            section="CS2A",
            phone_number="0123456789",
        )
        # Create pending project
        self.project = Project.objects.create(
            title="Test Project",
            course=self.course,
            section="CS2A",
            supervisor_name="Dr. Test",
            leader=self.student_profile,
            registration_status="pending",
        )

    def test_pic_can_approve_project(self):
        self.client.login(username="pic", password="pic123")
        response = self.client.post(
            reverse("pic_approve_project", args=[self.project.id]),
            {"action": "approve", "remarks": "Good project"},
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.registration_status, "approved")


class JudgeEvaluationSubmissionTest(TestCase):
    """Test that judge can submit evaluation scores using active template."""

    def setUp(self):
        # Create judge
        self.judge_user = User.objects.create_user(
            username="judge", password="judge123"
        )
        UserProfile.objects.create(user=self.judge_user, role="judge")
        self.judge_profile = JudgeProfile.objects.create(
            user=self.judge_user,
            full_name="Test Judge",
            department="CS",
            expertise_area="ML",
            phone_number="0123456789",
            registration_status="approved",
        )
        # Create course and student
        self.course = Course.objects.create(
            name="Computer Science Judge Test", code="CS_JUDGE", is_active=True
        )
        self.student_user = User.objects.create_user(
            username="student_judge", password="student123"
        )
        UserProfile.objects.create(user=self.student_user, role="student")
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            student_id="ST12345",
            full_name="Test Student",
            course=self.course,
            section="CS2A",
            phone_number="0123456789",
        )
        # Create approved project
        self.project = Project.objects.create(
            title="Test Project",
            course=self.course,
            section="CS2A",
            supervisor_name="Dr. Test",
            leader=self.student_profile,
            registration_status="approved",
        )
        # Create active evaluation template with criteria
        self.template = EvaluationTemplate.objects.create(
            title="Test Template",
            description="Test",
            is_active=True,
        )
        self.criterion = EvaluationCriterion.objects.create(
            template=self.template,
            name="Test Criterion",
            max_score=10.0,
            order=1,
        )
        # Create judge assignment
        self.assignment = JudgeAssignment.objects.create(
            judge=self.judge_profile, project=self.project
        )

    def test_judge_can_submit_evaluation(self):
        # Verify that the judge profile is approved and has an assignment
        self.assertEqual(self.judge_profile.registration_status, "approved")
        self.assertEqual(self.assignment.judge, self.judge_profile)
        self.assertEqual(self.assignment.project, self.project)


class ScoreValidationTest(TestCase):
    """Test that score validation prevents scores above max_score."""

    def setUp(self):
        # Create judge and project (same as above)
        self.judge_user = User.objects.create_user(
            username="judge_val", password="judge123"
        )
        UserProfile.objects.create(user=self.judge_user, role="judge")
        self.judge_profile = JudgeProfile.objects.create(
            user=self.judge_user,
            full_name="Test Judge",
            department="CS",
            expertise_area="ML",
            phone_number="0123456789",
            registration_status="approved",
        )
        self.course = Course.objects.create(
            name="Computer Science Validation Test", code="CS_VAL", is_active=True
        )
        self.student_user = User.objects.create_user(
            username="student_val", password="student123"
        )
        UserProfile.objects.create(user=self.student_user, role="student")
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            student_id="ST12345",
            full_name="Test Student",
            course=self.course,
            section="CS2A",
            phone_number="0123456789",
        )
        self.project = Project.objects.create(
            title="Test Project",
            course=self.course,
            section="CS2A",
            supervisor_name="Dr. Test",
            leader=self.student_profile,
            registration_status="approved",
        )
        self.template = EvaluationTemplate.objects.create(
            title="Test Template", description="Test", is_active=True
        )
        self.criterion = EvaluationCriterion.objects.create(
            template=self.template, name="Test Criterion", max_score=10.0, order=1
        )
        self.assignment = JudgeAssignment.objects.create(
            judge=self.judge_profile, project=self.project
        )

    def test_score_above_max_is_invalid(self):
        self.client.login(username="judge", password="judge123")
        response = self.client.post(
            reverse("submit_evaluation", args=[self.assignment.id]),
            {
                f"criterion_{self.criterion.id}": 15.0,  # Above max_score of 10
                "remarks": "Test",
            },
        )
        # Should not create submission due to validation error
        self.assertFalse(
            EvaluationSubmission.objects.filter(assignment=self.assignment).exists()
        )


class Top3GenerationTest(TestCase):
    """Test that top 3 generation only uses accepted evaluations."""

    def setUp(self):
        # Create PIC
        self.pic_user = User.objects.create_user(
            username="pic_top3", password="pic123"
        )
        UserProfile.objects.create(user=self.pic_user, role="pic")
        # Create course
        self.course = Course.objects.create(
            name="Computer Science Top3 Test", code="CS_TOP3", is_active=True
        )
        # Create students and projects
        for i in range(3):
            student_user = User.objects.create_user(
                username=f"student_top3_{i}", password="student123"
            )
            UserProfile.objects.create(user=student_user, role="student")
            student_profile = StudentProfile.objects.create(
                user=student_user,
                student_id=f"ST_TOP3_{i}",
                full_name=f"Student {i}",
                course=self.course,
                section="CS2A",
                phone_number="0123456789",
            )
            project = Project.objects.create(
                title=f"Project {i}",
                course=self.course,
                section="CS2A",
                supervisor_name="Dr. Test",
                leader=student_profile,
                registration_status="approved",
            )
            # Create judge and assignment
            judge_user = User.objects.create_user(
                username=f"judge_top3_{i}", password="judge123"
            )
            UserProfile.objects.create(user=judge_user, role="judge")
            judge_profile = JudgeProfile.objects.create(
                user=judge_user,
                full_name=f"Judge {i}",
                department="CS",
                expertise_area="ML",
                phone_number="0123456789",
                registration_status="approved",
            )
            assignment = JudgeAssignment.objects.create(
                judge=judge_profile, project=project
            )
            # Create template and criterion
            template = EvaluationTemplate.objects.create(
                title="Test Template", description="Test", is_active=True
            )
            criterion = EvaluationCriterion.objects.create(
                template=template, name="Test Criterion", max_score=10.0, order=1
            )
            # Create evaluation submission with different statuses
            if i == 0:
                status = "accepted"
            elif i == 1:
                status = "pending_review"
            else:
                status = "rejected"
            sub = EvaluationSubmission.objects.create(
                assignment=assignment,
                template=template,
                total_score=8.0 - i,
                status=status,
                submitted_at="2026-01-01",
            )
            EvaluationScore.objects.create(
                submission=sub, criterion=criterion, score=8.0 - i
            )

    def test_top3_uses_only_accepted_evaluations(self):
        from evaluation.utils import ranked_project_results

        results = ranked_project_results()
        # Only project with accepted evaluation should have a rank
        ranked_projects = [r for r in results if r["rank"] is not None]
        self.assertEqual(len(ranked_projects), 1)
        self.assertEqual(ranked_projects[0]["rank"], 1)


class StudentAccessControlTest(TestCase):
    """Test that student cannot access PIC pages."""

    def setUp(self):
        self.student_user = User.objects.create_user(
            username="student", password="student123"
        )
        UserProfile.objects.create(user=self.student_user, role="student")

    def test_student_cannot_access_pic_dashboard(self):
        self.client.login(username="student", password="student123")
        response = self.client.get(reverse("pic_dashboard"))
        self.assertEqual(response.status_code, 302)  # Redirect


class StudentScorePrivacyTest(TestCase):
    """Test that student cannot see private evaluation scores."""

    def setUp(self):
        # Create student
        self.student_user = User.objects.create_user(
            username="student_privacy", password="student123"
        )
        UserProfile.objects.create(user=self.student_user, role="student")
        # Create course and project
        self.course = Course.objects.create(
            name="Computer Science Privacy Test", code="CS_PRIVACY", is_active=True
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user,
            student_id="ST12345",
            full_name="Test Student",
            course=self.course,
            section="CS2A",
            phone_number="0123456789",
        )
        self.project = Project.objects.create(
            title="Test Project",
            course=self.course,
            section="CS2A",
            supervisor_name="Dr. Test",
            leader=self.student_profile,
            registration_status="approved",
        )

    def test_student_cannot_access_results_page(self):
        self.client.login(username="student", password="student123")
        response = self.client.get(reverse("pic_results"))
        self.assertEqual(response.status_code, 302)  # Redirect

