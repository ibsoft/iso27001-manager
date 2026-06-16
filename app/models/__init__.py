from app.models.user import User, Role, Permission, user_roles
from app.models.domain import Domain
from app.models.control import Control
from app.models.clause import Clause
from app.models.asset import Asset
from app.models.risk import Risk, RiskTreatment
from app.models.incident import Incident
from app.models.policy import Policy, PolicyVersion
from app.models.audit import InternalAudit, AuditFinding, NonConformity, CorrectiveAction
from app.models.supplier import Supplier
from app.models.soa import SoAEntry
from app.models.metric import KpiDefinition, KpiMeasurement
from app.models.audit_log import AuditLog
from app.models.processing import ProcessingActivity
from app.models.data_breach import DataBreach
from app.models.dpia import Dpia
from app.models.data_subject_request import DataSubjectRequest
from app.models.consent import ConsentRecord
from app.models.data_controller import DataControllerProcessor
from app.models.privacy_notice import PrivacyNotice
from app.models.nis2 import Nis2EntityRegistration, Nis2IncidentNotification, Nis2SupplyChainAssessment, Nis2ContinuityPlan, Nis2ComplianceCheck
from app.models.user import SystemSetting
from app.models.asset_assignment import AssetAssignment
from app.models.management_review import ManagementReview, ReviewActionItem
from app.models.capa import CapaRequest
from app.models.training import TrainingCourse, TrainingSession, TrainingRecord, CompetenceProfile
from app.models.business_continuity import BusinessImpactAnalysis, BusinessContinuityPlan, BusinessContinuityTest, BusinessContinuityAction
