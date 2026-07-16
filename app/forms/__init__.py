from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    StringField, PasswordField, BooleanField, SelectField, TextAreaField,
    IntegerField, DateField, FloatField, HiddenField, SelectMultipleField,
    SubmitField, DateTimeField
)
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, ValidationError
from flask_babel import lazy_gettext as _l
import re


class BaseForm(FlaskForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self:
            if any(isinstance(v, DataRequired) for v in field.validators):
                if field.render_kw is None:
                    field.render_kw = {}
                field.render_kw.setdefault("required", True)

TIMEZONE_CHOICES = [
    ("UTC", "UTC"),
    ("Europe/London", "Europe/London (GMT/BST)"),
    ("Europe/Paris", "Europe/Paris (CET/CEST)"),
    ("Europe/Berlin", "Europe/Berlin (CET/CEST)"),
    ("Europe/Athens", "Europe/Athens (EET/EEST)"),
    ("Europe/Moscow", "Europe/Moscow (MSK/MSK+1)"),
    ("Europe/Istanbul", "Europe/Istanbul (TRT)"),
    ("US/Eastern", "US/Eastern (EST/EDT)"),
    ("US/Central", "US/Central (CST/CDT)"),
    ("US/Mountain", "US/Mountain (MST/MDT)"),
    ("US/Pacific", "US/Pacific (PST/PDT)"),
    ("America/New_York", "America/New_York"),
    ("America/Chicago", "America/Chicago"),
    ("America/Denver", "America/Denver"),
    ("America/Los_Angeles", "America/Los_Angeles"),
    ("America/Sao_Paulo", "America/Sao_Paulo (BRT)"),
    ("America/Argentina/Buenos_Aires", "America/Buenos_Aires (ART)"),
    ("Asia/Dubai", "Asia/Dubai (GST)"),
    ("Asia/Kolkata", "Asia/Kolkata (IST)"),
    ("Asia/Singapore", "Asia/Singapore (SGT)"),
    ("Asia/Shanghai", "Asia/Shanghai (CST)"),
    ("Asia/Tokyo", "Asia/Tokyo (JST)"),
    ("Asia/Seoul", "Asia/Seoul (KST)"),
    ("Australia/Sydney", "Australia/Sydney (AEST/AEDT)"),
    ("Australia/Perth", "Australia/Perth (AWST)"),
    ("Pacific/Auckland", "Pacific/Auckland (NZST/NZDT)"),
    ("Africa/Cairo", "Africa/Cairo (EET)"),
    ("Africa/Johannesburg", "Africa/Johannesburg (SAST)"),
    ("Africa/Lagos", "Africa/Lagos (WAT)"),
]


class LoginForm(BaseForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Sign In")


class ProfileForm(BaseForm):
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=64)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=64)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    phone_number = StringField("Internal Phone", validators=[Optional(), Length(max=32)])
    mobile_phone = StringField("Mobile Phone", validators=[Optional(), Length(max=32)])
    avatar_url = StringField("Profile Image URL (overrides Gravatar)", validators=[Optional(), Length(max=512)])
    avatar_file = FileField("Upload Profile Image", validators=[Optional()])
    timezone = SelectField("Timezone", choices=TIMEZONE_CHOICES, validators=[Optional()])
    default_language = SelectField("Default Language", choices=[("", "Browser Default"), ("en", "English"), ("el", "Ελληνικά")], validators=[Optional()])
    force_language = BooleanField("Enforce language for all users")
    force_timezone = BooleanField("Enforce timezone for all users")
    submit = SubmitField("Save Profile")


class UserForm(BaseForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=64)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=64)])
    password = PasswordField("Password", validators=[Optional(), Length(min=12)])
    is_active = BooleanField("Active")
    roles = SelectMultipleField("Roles", coerce=int)
    groups = SelectMultipleField("Groups", coerce=int)
    department = SelectField("Department", coerce=int, validators=[Optional()])
    manager = SelectField("Manager", coerce=int, validators=[Optional()])
    submit = SubmitField("Save")

    def validate_password(form, field):
        if field.data:
            if not re.search(r'[A-Z]', field.data):
                raise ValidationError("Must contain uppercase letter")
            if not re.search(r'[a-z]', field.data):
                raise ValidationError("Must contain lowercase letter")
            if not re.search(r'[0-9]', field.data):
                raise ValidationError("Must contain digit")
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', field.data):
                raise ValidationError("Must contain special character")


class ChangePasswordForm(BaseForm):
    current_password = PasswordField("Current Password", validators=[DataRequired()])
    new_password = PasswordField("New Password", validators=[DataRequired(), Length(min=12)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired()])
    submit = SubmitField("Change Password")

    def validate_new_password(form, field):
        if not re.search(r'[A-Z]', field.data):
            raise ValidationError("Must contain uppercase letter")
        if not re.search(r'[a-z]', field.data):
            raise ValidationError("Must contain lowercase letter")
        if not re.search(r'[0-9]', field.data):
            raise ValidationError("Must contain digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', field.data):
            raise ValidationError("Must contain special character")


class ControlForm(BaseForm):
    code = StringField("Control Code", validators=[DataRequired(), Length(max=8)])
    title = StringField("Title", validators=[DataRequired(), Length(max=256)])
    description = TextAreaField("Description", validators=[Optional()])
    description_el = TextAreaField("Description (EL)", validators=[Optional()])
    detailed_description = TextAreaField("Detailed Description", validators=[Optional()])
    detailed_description_el = TextAreaField("Detailed Description (EL)", validators=[Optional()])
    purpose = TextAreaField("Purpose", validators=[Optional()])
    guidance = TextAreaField("Guidance", validators=[Optional()])
    domain_id = SelectField("Domain", coerce=int, validators=[DataRequired()])
    implementation_status = SelectField(
        "Implementation Status",
        choices=[("not_started", "Not Started"), ("in_progress", "In Progress"),
                 ("implemented", "Implemented"), ("not_applicable", "Not Applicable")],
        default="not_started",
    )
    owner_id = SelectField("Owner", coerce=int, validators=[Optional()])
    target_date = DateField("Target Date", validators=[Optional()])
    review_date = DateField("Review Date", validators=[Optional()])
    evidence_notes = TextAreaField("Evidence Notes", validators=[Optional()])
    submit = SubmitField("Save")


class RiskForm(BaseForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=256)])
    description = TextAreaField("Description", validators=[Optional()])
    asset_id = SelectField("Affected Asset", coerce=int, validators=[Optional()])
    likelihood = SelectField(
        "Likelihood (1-5)",
        coerce=int,
        choices=[(1, "1 - Very Rare"), (2, "2 - Unlikely"), (3, "3 - Possible"),
                 (4, "4 - Likely"), (5, "5 - Almost Certain")],
        validators=[DataRequired()],
    )
    impact = SelectField(
        "Impact (1-5)",
        coerce=int,
        choices=[(1, "1 - Negligible"), (2, "2 - Minor"), (3, "3 - Moderate"),
                 (4, "4 - Major"), (5, "5 - Catastrophic")],
        validators=[DataRequired()],
    )
    treatment_option = SelectField(
        "Treatment Option",
        choices=[("", "Select..."), ("accept", "Accept"), ("mitigate", "Mitigate"),
                 ("transfer", "Transfer"), ("avoid", "Avoid")],
        validators=[Optional()],
    )
    treatment_plan = TextAreaField("Treatment Plan", validators=[Optional()])
    residual_likelihood = SelectField(
        "Residual Likelihood (1-5)", coerce=int,
        choices=[(0, "N/A"), (1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
        validators=[Optional()],
    )
    residual_impact = SelectField(
        "Residual Impact (1-5)", coerce=int,
        choices=[(0, "N/A"), (1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5")],
        validators=[Optional()],
    )
    status = SelectField(
        "Status",
        choices=[("identified", "Identified"), ("assessed", "Assessed"),
                 ("treatment_in_progress", "Treatment In Progress"),
                 ("residual_accepted", "Residual Accepted"), ("closed", "Closed")],
        default="identified",
    )
    owner_id = SelectField("Risk Owner", coerce=int, validators=[Optional()])
    target_date = DateField("Target Date", validators=[Optional()])
    submit = SubmitField("Save")


class AssetForm(BaseForm):
    name = StringField("Asset Name", validators=[DataRequired(), Length(max=256)])
    serial_number = StringField("Serial Number", validators=[Optional(), Length(max=128)])
    description = TextAreaField("Description", validators=[Optional()])
    asset_type = SelectField(
        "Asset Type",
        choices=[("", "Select..."), ("hardware", "Hardware"), ("software", "Software"),
                 ("data", "Data"), ("personnel", "Personnel"), ("facility", "Facility"),
                 ("other", "Other")],
        validators=[Optional()],
    )
    classification = SelectField(
        "Classification",
        choices=[("public", "Public"), ("internal", "Internal"),
                 ("confidential", "Confidential"), ("restricted", "Restricted")],
        default="internal",
    )
    owner_id = SelectField("Asset Owner", coerce=int, validators=[Optional()])
    location = StringField("Location", validators=[Optional(), Length(max=256)])
    status = SelectField(
        "Status",
        choices=[("active", "Active"), ("inactive", "Inactive"), ("disposed", "Disposed")],
        default="active",
    )
    criticality = SelectField(
        "Criticality",
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium",
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    picture = FileField("Asset Picture", validators=[Optional()])
    barcode = StringField("Barcode / QR Code", validators=[Optional(), Length(max=256)])
    submit = SubmitField("Save")


class IncidentForm(BaseForm):
    title = StringField("Incident Title", validators=[DataRequired(), Length(max=256)])
    description = TextAreaField("Description", validators=[DataRequired()])
    severity = SelectField(
        "Severity",
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium",
    )
    category = SelectField(
        "Category",
        choices=[("", "Select..."), ("malware", "Malware"), ("unauthorized_access", "Unauthorized Access"),
                 ("data_breach", "Data Breach"), ("phishing", "Phishing"),
                 ("physical", "Physical Security"), ("other", "Other")],
        validators=[Optional()],
    )
    assigned_to_id = SelectField("Assign To", coerce=int, validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("reported", "Reported"), ("investigating", "Investigating"),
                 ("contained", "Contained"), ("resolved", "Resolved"), ("closed", "Closed")],
        default="reported",
    )
    root_cause = TextAreaField("Root Cause", validators=[Optional()])
    impact_description = TextAreaField("Impact Description", validators=[Optional()])
    lessons_learned = TextAreaField("Lessons Learned", validators=[Optional()])
    nis2_reportable = BooleanField("NIS2 Reportable Incident")
    nis2_early_warning_submitted_at = DateTimeField("Early Warning Submitted At (24h)", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    nis2_notification_submitted_at = DateTimeField("Notification Submitted At (72h)", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    nis2_final_report_submitted_at = DateTimeField("Final Report Submitted At (1 month)", validators=[Optional()], format="%Y-%m-%dT%H:%M")
    nis2_csirt_reference = StringField("CSIRT Reference", validators=[Optional(), Length(max=128)])
    submit = SubmitField("Save")


class PolicyForm(BaseForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=256)])
    description = TextAreaField("Description", validators=[Optional()])
    is_document = BooleanField("This is an uploaded document (not WYSIWYG content)")
    category = SelectField(
        "Category",
        choices=[("", "Select..."), ("information_security", "Information Security"),
                 ("access_control", "Access Control"), ("incident_response", "Incident Response"),
                 ("risk_management", "Risk Management"), ("data_protection", "Data Protection"),
                 ("physical_security", "Physical Security"), ("hr_security", "HR Security"),
                 ("supplier_security", "Supplier Security"),
                 ("forms", "Forms"), ("other", "Other")],
        validators=[Optional()],
    )
    owner_id = SelectField("Policy Owner", coerce=int, validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("draft", "Draft"), ("reviewed", "Reviewed"), ("approved", "Approved"),
                 ("published", "Published"), ("retired", "Retired")],
        default="draft",
    )
    effective_date = DateField("Effective Date", validators=[Optional()])
    review_date = DateField("Review Date", validators=[Optional()])
    content = TextAreaField("Content", validators=[Optional()])
    file = FileField("Upload File", validators=[Optional()])
    submit = SubmitField("Save")


class AuditForm(BaseForm):
    title = StringField("Audit Title", validators=[DataRequired(), Length(max=256)])
    lead_auditor_id = SelectField("Lead Auditor", coerce=int, validators=[Optional()])
    audit_date = DateField("Audit Date", validators=[DataRequired()])
    scope = TextAreaField("Scope", validators=[Optional()])
    findings_summary = TextAreaField("Findings Summary", validators=[Optional()])
    conclusion = TextAreaField("Conclusion", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("planned", "Planned"), ("in_progress", "In Progress"),
                 ("completed", "Completed"), ("reported", "Reported")],
        default="planned",
    )
    submit = SubmitField("Save")


class AuditFindingForm(BaseForm):
    control_id = SelectField("Related Control", coerce=int, validators=[Optional()])
    finding_type = SelectField(
        "Finding Type",
        choices=[("nonconformity", "Non-Conformity"), ("observation", "Observation"),
                 ("opportunity_for_improvement", "Opportunity for Improvement")],
        validators=[DataRequired()],
    )
    description = TextAreaField("Description", validators=[DataRequired()])
    severity = SelectField(
        "Severity",
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium",
    )
    submit = SubmitField("Save")


class CorrectiveActionForm(BaseForm):
    description = TextAreaField("Action Description", validators=[DataRequired()])
    owner_id = SelectField("Assigned To", coerce=int, validators=[Optional()])
    target_date = DateField("Target Date", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("open", "Open"), ("in_progress", "In Progress"),
                 ("completed", "Completed"), ("verified_closed", "Verified Closed")],
        default="open",
    )
    closure_evidence = TextAreaField("Closure Evidence", validators=[Optional()])
    effectiveness_review = TextAreaField("Effectiveness Review", validators=[Optional()])
    submit = SubmitField("Save")


class SupplierForm(BaseForm):
    name = StringField(_l("Supplier Name"), validators=[DataRequired(), Length(max=256)])
    vendor_type = SelectField(
        _l("Supplier/Vendor Type"),
        choices=[("supplier", _l("Supplier")), ("vendor", _l("Vendor")),
                 ("processor", _l("Data Processor")), ("subprocessor", _l("Subprocessor")),
                 ("outsourcer", _l("Outsourcer")), ("partner", _l("Partner"))],
        default="supplier",
    )
    lifecycle_stage = SelectField(
        _l("Lifecycle Stage"),
        choices=[("identified", _l("Identified")), ("due_diligence", _l("Due Diligence")),
                 ("contracting", _l("Contracting")), ("onboarded", _l("Onboarded")),
                 ("active_monitoring", _l("Active Monitoring")), ("renewal", _l("Renewal")),
                 ("offboarding", _l("Offboarding")), ("terminated", _l("Terminated"))],
        default="onboarded",
    )
    contact_name = StringField(_l("Contact Name"), validators=[Optional(), Length(max=128)])
    contact_email = StringField(_l("Contact Email"), validators=[Optional(), Email(), Length(max=128)])
    contact_phone = StringField(_l("Contact Phone"), validators=[Optional(), Length(max=64)])
    service_description = TextAreaField(_l("Service Description"), validators=[Optional()])
    security_requirements = TextAreaField(_l("Security Requirements"), validators=[Optional()])
    assessment_status = SelectField(
        _l("Assessment Status"),
        choices=[("pending", _l("Pending")), ("assessed", _l("Assessed")),
                 ("approved", _l("Approved")), ("rejected", _l("Rejected")),
                 ("review_required", _l("Review Required"))],
        default="pending",
    )
    assessment_notes = TextAreaField(_l("Assessment Notes"), validators=[Optional()])
    assessment_date = DateField(_l("Assessment Date"), validators=[Optional()])
    contract_start_date = DateField(_l("Contract Start"), validators=[Optional()])
    contract_end_date = DateField(_l("Contract End"), validators=[Optional()])
    data_processing_agreement = BooleanField(_l("DPA in Place"))
    criticality = SelectField(
        _l("Criticality"),
        choices=[("low", _l("Low")), ("medium", _l("Medium")), ("high", _l("High")), ("critical", _l("Critical"))],
        default="medium",
    )
    data_access_level = SelectField(
        _l("Data Access Level"),
        choices=[("none", _l("No Data Access")), ("public", _l("Public")),
                 ("internal", _l("Internal")), ("confidential", _l("Confidential")),
                 ("restricted", _l("Restricted")), ("personal_data", _l("Personal Data")),
                 ("special_category", _l("Special Category Data"))],
        default="none",
    )
    inherent_risk = SelectField(
        _l("Inherent Risk"),
        choices=[("low", _l("Low")), ("medium", _l("Medium")), ("high", _l("High")), ("critical", _l("Critical"))],
        default="medium",
    )
    residual_risk = SelectField(
        _l("Residual Risk"),
        choices=[("low", _l("Low")), ("medium", _l("Medium")), ("high", _l("High")), ("critical", _l("Critical"))],
        default="medium",
    )
    risk_score = IntegerField(_l("Risk Score (0-100)"), validators=[Optional(), NumberRange(min=0, max=100)], default=50)
    risk_treatment = SelectField(
        _l("Risk Treatment"),
        choices=[("accept", _l("Accept")), ("mitigate", _l("Mitigate")),
                 ("transfer", _l("Transfer")), ("avoid", _l("Avoid"))],
        default="mitigate",
    )
    risk_owner = StringField(_l("Risk Owner"), validators=[Optional(), Length(max=128)])
    next_review_date = DateField(_l("Next Review Date"), validators=[Optional()])
    monitoring_frequency = SelectField(
        _l("Monitoring Frequency"),
        choices=[("monthly", _l("Monthly")), ("quarterly", _l("Quarterly")),
                 ("semi_annual", _l("Semi-Annual")), ("annual", _l("Annual")),
                 ("event_based", _l("Event Based"))],
        default="annual",
    )
    status = SelectField(
        _l("Status"),
        choices=[("active", _l("Active")), ("inactive", _l("Inactive")), ("terminated", _l("Terminated"))],
        default="active",
    )
    ict_service_type = SelectField(
        _l("ICT Service Type"),
        choices=[("", _l("Select...")), ("cloud", _l("Cloud Services")),
                 ("saas", _l("SaaS")), ("network", _l("Network Services")),
                 ("hardware", _l("Hardware")), ("software", _l("Software")),
                 ("managed_service", _l("Managed Service")),
                 ("consulting", _l("Consulting")), ("other", _l("Other"))],
        validators=[Optional()],
    )
    security_certification = StringField(_l("Security Certifications"), validators=[Optional(), Length(max=256)])
    dependency_tier = SelectField(
        _l("Dependency Tier"),
        choices=[("1", _l("Tier 1 - Direct critical")), ("2", _l("Tier 2 - Direct non-critical")),
                 ("3", _l("Tier 3 - Indirect"))],
        default="3",
    )
    nis2_in_scope = BooleanField(_l("In NIS2 Supply Chain Scope"))
    last_supply_chain_review = DateField(_l("Last Supply Chain Review"), validators=[Optional()])
    due_diligence_completed = BooleanField(_l("Due Diligence Completed"))
    contract_security_clauses = BooleanField(_l("Security Clauses in Contract"))
    audit_rights = BooleanField(_l("Audit Rights Included"))
    subcontractors_allowed = BooleanField(_l("Subcontractors Allowed"))
    incident_notification_sla = StringField(_l("Incident Notification SLA"), validators=[Optional(), Length(max=64)])
    sla_requirements = TextAreaField(_l("SLA Requirements"), validators=[Optional()])
    risk_treatment_plan = TextAreaField(_l("Risk Treatment Plan"), validators=[Optional()])
    exit_strategy = TextAreaField(_l("Exit Strategy / Offboarding Plan"), validators=[Optional()])
    offboarding_date = DateField(_l("Offboarding Date"), validators=[Optional()])
    submit = SubmitField("Save")


class SoAForm(BaseForm):
    applicable = SelectField(
        _l("Applicable"),
        choices=[(1, _l("Yes - Control is applicable")), (0, _l("No - Control is not applicable"))],
        coerce=int,
        validators=[DataRequired()],
    )
    justification = TextAreaField(_l("Justification"), validators=[Optional()])
    justification_el = TextAreaField(_l("Justification (Greek)"), validators=[Optional()])
    implementation_status = SelectField(
        _l("Implementation Status"),
        choices=[("not_started", _l("Not Started")), ("in_progress", _l("In Progress")),
                 ("implemented", _l("Implemented")), ("not_applicable", _l("Not Applicable"))],
        default="not_started",
    )
    selected_control_description = TextAreaField(_l("Control Description"), validators=[Optional()])
    selected_control_description_el = TextAreaField(_l("Control Description (Greek)"), validators=[Optional()])
    responsible_person_id = SelectField(_l("Responsible Person"), coerce=int, validators=[Optional()])
    submit = SubmitField(_l("Save"))


class ProcessingActivityForm(BaseForm):
    name = StringField("Processing Activity Name", validators=[DataRequired(), Length(max=256)])
    controller_name = StringField("Data Controller Name", validators=[DataRequired(), Length(max=256)])
    controller_contact = StringField("Controller Contact Details", validators=[Optional(), Length(max=256)])
    controller_email = StringField("Controller Email", validators=[Optional(), Email(), Length(max=120)])
    representative = StringField("EU Representative (Art 27)", validators=[Optional(), Length(max=256)])
    dpo_name = StringField("DPO Name", validators=[Optional(), Length(max=128)])
    dpo_contact = StringField("DPO Contact Details", validators=[Optional(), Length(max=256)])
    processing_purpose = TextAreaField("Processing Purpose", validators=[DataRequired()])
    legal_basis = SelectField(
        "Legal Basis for Processing",
        choices=[("", "Select..."), ("consent", "Consent (Art 6(1)(a))"),
                 ("contract", "Contract (Art 6(1)(b))"),
                 ("legal_obligation", "Legal Obligation (Art 6(1)(c))"),
                 ("vital_interests", "Vital Interests (Art 6(1)(d))"),
                 ("public_task", "Public Task (Art 6(1)(e))"),
                 ("legitimate_interest", "Legitimate Interest (Art 6(1)(f))")],
        validators=[DataRequired()],
    )
    legal_basis_details = TextAreaField("Legal Basis Details", validators=[Optional()])
    data_subject_categories = TextAreaField("Data Subject Categories", validators=[DataRequired()])
    personal_data_categories = TextAreaField("Personal Data Categories", validators=[DataRequired()])
    special_category_data = BooleanField("Special Category Data (Art 9)")
    special_category_details = TextAreaField("Special Category Details", validators=[Optional()])
    criminal_data = BooleanField("Criminal Conviction Data (Art 10)")
    recipients = TextAreaField("Categories of Recipients", validators=[Optional()])
    data_retention = TextAreaField("Data Retention Periods / Erasure Schedule", validators=[DataRequired()])
    tech_org_measures = TextAreaField("Technical & Organisational Measures", validators=[Optional()])
    cross_border_transfer = BooleanField("Cross-border Transfer (outside EU/EEA)")
    transfer_countries = TextAreaField("Third Countries", validators=[Optional()])
    transfer_safeguards = TextAreaField("Transfer Safeguards (SCCs, BCRs, etc.)", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")],
        default="active",
    )
    submit = SubmitField("Save")


class DpiaForm(BaseForm):
    project_name = StringField("Project / System Name", validators=[DataRequired(), Length(max=256)])
    project_description = TextAreaField("Project Description", validators=[DataRequired()])
    processing_description = TextAreaField("Processing Description", validators=[DataRequired()])
    necessity_assessment = TextAreaField("Necessity & Proportionality Assessment", validators=[Optional()])
    proportionality_assessment = TextAreaField("Proportionality Assessment", validators=[Optional()])
    data_subject_categories = TextAreaField("Data Subject Categories", validators=[Optional()])
    personal_data_categories = TextAreaField("Personal Data Categories", validators=[Optional()])
    special_category_data = BooleanField("Special Category Data")
    risks_to_rights = TextAreaField("Risks to Rights & Freedoms", validators=[Optional()])
    mitigation_measures = TextAreaField("Mitigation Measures", validators=[Optional()])
    residual_risk_level = SelectField(
        "Residual Risk Level",
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium",
    )
    dpo_review = TextAreaField("DPO Review / Comments", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("draft", "Draft"), ("in_progress", "In Progress"),
                 ("reviewed", "Reviewed"), ("approved", "Approved"), ("rejected", "Rejected")],
        default="draft",
    )
    submit = SubmitField("Save")


class DataSubjectRequestForm(BaseForm):
    request_type = SelectField(
        "Request Type",
        choices=[("", "Select..."), ("access", "Right of Access (Art 15)"),
                 ("rectification", "Right to Rectification (Art 16)"),
                 ("erasure", "Right to Erasure / Be Forgotten (Art 17)"),
                 ("portability", "Right to Data Portability (Art 20)"),
                 ("restriction", "Right to Restrict Processing (Art 18)"),
                 ("objection", "Right to Object (Art 21)"),
                 ("automated_decision", "Automated Decision-Making (Art 22)")],
        validators=[DataRequired()],
    )
    requester_name = StringField("Requester Full Name", validators=[DataRequired(), Length(max=128)])
    requester_email = StringField("Requester Email", validators=[DataRequired(), Email(), Length(max=120)])
    requester_phone = StringField("Requester Phone", validators=[Optional(), Length(max=32)])
    requester_identity_verified = BooleanField("Identity Verified")
    request_description = TextAreaField("Request Details", validators=[Optional()])
    outcome = SelectField(
        "Outcome",
        choices=[("", "Pending..."), ("granted", "Granted"),
                 ("partially_granted", "Partially Granted"),
                 ("denied", "Denied"), ("not_applicable", "Not Applicable")],
        validators=[Optional()],
    )
    response_summary = TextAreaField("Response Summary", validators=[Optional()])
    denial_reason = TextAreaField("Denial Reason", validators=[Optional()])
    extension_reason = TextAreaField("Extension Reason", validators=[Optional()])
    extension_granted = BooleanField("Extension Granted (additional 2 months)")
    extension_deadline = DateField("Extension Deadline", validators=[Optional()])
    notes = TextAreaField("Internal Notes", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("open", "Open"), ("in_progress", "In Progress"),
                 ("awaiting_info", "Awaiting Info"), ("completed", "Completed"),
                 ("closed", "Closed")],
        default="open",
    )
    assigned_to_id = SelectField("Assigned To", coerce=int, validators=[Optional()])
    submit = SubmitField("Save")


class ConsentRecordForm(BaseForm):
    data_subject_identifier = StringField("Data Subject Identifier", validators=[DataRequired(), Length(max=256)])
    data_subject_email = StringField("Data Subject Email", validators=[Optional(), Email(), Length(max=120)])
    processing_purpose = StringField("Processing Purpose", validators=[DataRequired(), Length(max=256)])
    consent_source = SelectField(
        "Consent Source",
        choices=[("", "Select..."), ("web_form", "Web Form"),
                 ("signed_form", "Signed Form"), ("verbal", "Verbal"),
                 ("email", "Email"), ("api", "API / System")],
        validators=[Optional()],
    )
    consent_proof = TextAreaField("Proof of Consent", validators=[Optional()])
    consent_version = StringField("Consent Version", validators=[Optional(), Length(max=16)])
    granted = BooleanField("Consent Granted", default=True)
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save")


class DataControllerForm(BaseForm):
    name = StringField("Entity Name", validators=[DataRequired(), Length(max=256)])
    role = SelectField(
        "Role",
        choices=[("", "Select..."), ("controller", "Data Controller"),
                 ("processor", "Data Processor"),
                 ("joint_controller", "Joint Controller")],
        validators=[DataRequired()],
    )
    contact_person = StringField("Contact Person", validators=[Optional(), Length(max=128)])
    email = StringField("Email", validators=[Optional(), Email(), Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), Length(max=32)])
    address = TextAreaField("Address", validators=[Optional()])
    representative_name = StringField("EU Representative Name (Art 27)", validators=[Optional(), Length(max=128)])
    representative_contact = TextAreaField("EU Representative Contact", validators=[Optional()])
    dpo_name = StringField("DPO Name", validators=[Optional(), Length(max=128)])
    dpo_email = StringField("DPO Email", validators=[Optional(), Email(), Length(max=120)])
    registration_number = StringField("Registration / ID Number", validators=[Optional(), Length(max=64)])
    country = StringField("Country", validators=[Optional(), Length(max=64)])
    status = SelectField(
        "Status",
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )
    notes = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save")


class PrivacyNoticeForm(BaseForm):
    title = StringField("Notice Title", validators=[DataRequired(), Length(max=256)])
    version = StringField("Version", validators=[DataRequired(), Length(max=16)], default="1.0")
    language = SelectField(
        "Language",
        choices=[("en", "English"), ("el", "Ελληνικά")],
        default="en",
    )
    content = TextAreaField("Notice Content", validators=[DataRequired()])
    effective_date = DateField("Effective Date", validators=[Optional()])
    review_date = DateField("Review Date", validators=[Optional()])
    status = SelectField(
        "Status",
        choices=[("draft", "Draft"), ("published", "Published"), ("retired", "Retired")],
        default="draft",
    )
    submit = SubmitField("Save")


class DataBreachForm(BaseForm):
    breach_type = SelectField(
        "Breach Type",
        choices=[("", "Select..."), ("confidentiality", "Confidentiality Breach"),
                 ("integrity", "Integrity Breach"), ("availability", "Availability Breach")],
        validators=[Optional()],
    )
    personal_data_breach = BooleanField("Personal Data Breach", default=True)
    notified_supervisory_authority = BooleanField("Notified Supervisory Authority")
    sa_notification_date = DateField("SA Notification Date", validators=[Optional()])
    sa_reference = StringField("SA Reference Number", validators=[Optional(), Length(max=64)])
    notified_data_subjects = BooleanField("Notified Data Subjects")
    ds_notification_date = DateField("Data Subject Notification Date", validators=[Optional()])
    ds_affected_count = IntegerField("Data Subjects Affected (count)", validators=[Optional()])
    records_affected_count = IntegerField("Personal Data Records Affected", validators=[Optional()])
    likelihood_of_risk = TextAreaField("Likelihood & Severity of Risk to Rights", validators=[Optional()])
    mitigation_measures = TextAreaField("Mitigation Measures Taken", validators=[Optional()])
    notification_delay_reason = TextAreaField("Reason for Notification Delay", validators=[Optional()])
    notification_delay_justified = BooleanField("Delay Justified (Art 33(3))")
    submit = SubmitField("Save Breach Details")


class Nis2EntityForm(BaseForm):
    entity_name = StringField(_l("Entity Name"), validators=[DataRequired(), Length(max=256)])
    sector = SelectField(
        _l("Sector"),
        choices=[("", _l("Select...")), ("energy", _l("Energy")), ("transport", _l("Transport")),
                 ("banking", _l("Banking")), ("health", _l("Health")),
                 ("digital_infrastructure", _l("Digital Infrastructure")),
                 ("ict_service", _l("ICT Service")), ("water", _l("Water Supply")),
                 ("waste", _l("Waste Management")), ("manufacturing", _l("Manufacturing")),
                 ("food", _l("Food Production")), ("postal", _l("Postal Services")),
                 ("other", _l("Other"))],
        validators=[Optional()],
    )
    sub_sector = StringField(_l("Sub-Sector"), validators=[Optional(), Length(max=128)])
    entity_type = SelectField(
        _l("Entity Type"),
        choices=[("essential", _l("Essential")), ("important", _l("Important"))],
        default="essential",
    )
    registration_number = StringField(_l("Registration Number"), validators=[Optional(), Length(max=128)])
    competent_authority = StringField(_l("Competent Authority"), validators=[Optional(), Length(max=256)])
    csirt_name = StringField(_l("CSIRT Name"), validators=[Optional(), Length(max=256)])
    csirt_email = StringField(_l("CSIRT Email"), validators=[Optional(), Email(), Length(max=128)])
    csirt_phone = StringField(_l("CSIRT Phone"), validators=[Optional(), Length(max=64)])
    headquarters_address = TextAreaField(_l("Headquarters Address"), validators=[Optional()])
    operates_in_eu = BooleanField(_l("Operates in EU"), default=True)
    eu_member_states = StringField(_l("EU Member States"), validators=[Optional(), Length(max=256)])
    employee_count = IntegerField(_l("Employee Count"), validators=[Optional()])
    annual_turnover = StringField(_l("Annual Turnover"), validators=[Optional(), Length(max=64)])
    registration_date = DateField(_l("Registration Date"), validators=[Optional()])
    last_review_date = DateField(_l("Last Review Date"), validators=[Optional()])
    next_review_date = DateField(_l("Next Review Date"), validators=[Optional()])
    status = SelectField(
        _l("Status"),
        choices=[("active", _l("Active")), ("inactive", _l("Inactive")), ("suspended", _l("Suspended"))],
        default="active",
    )
    notes = TextAreaField(_l("Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class Nis2NotificationForm(BaseForm):
    incident_id = SelectField(_l("Related Incident"), coerce=int, validators=[Optional()])
    incident_title = StringField(_l("Incident Title"), validators=[DataRequired(), Length(max=256)])
    reportable_criteria = TextAreaField(_l("Reportable Criteria"), validators=[Optional()])
    service_disruption = BooleanField(_l("Service Disruption"))
    data_impact = BooleanField(_l("Data Impact"))
    financial_loss = BooleanField(_l("Financial Loss"))
    affected_users_count = IntegerField(_l("Affected Users Count"), validators=[Optional()])
    incident_detected_at = DateTimeField(_l("Incident Detected At"), validators=[Optional()], format="%Y-%m-%dT%H:%M")
    early_warning_deadline = DateTimeField(_l("Early Warning Deadline (24h)"), validators=[Optional()], format="%Y-%m-%dT%H:%M")
    early_warning_submitted_at = DateTimeField(_l("Early Warning Submitted At"), validators=[Optional()], format="%Y-%m-%dT%H:%M")
    early_warning_details = TextAreaField(_l("Early Warning Details"), validators=[Optional()])
    notification_deadline = DateTimeField(_l("Notification Deadline (72h)"), validators=[Optional()], format="%Y-%m-%dT%H:%M")
    notification_submitted_at = DateTimeField(_l("Notification Submitted At"), validators=[Optional()], format="%Y-%m-%dT%H:%M")
    notification_details = TextAreaField(_l("Notification Details"), validators=[Optional()])
    final_report_deadline = DateTimeField(_l("Final Report Deadline (1 month)"), validators=[Optional()], format="%Y-%m-%dT%H:%M")
    final_report_submitted_at = DateTimeField(_l("Final Report Submitted At"), validators=[Optional()], format="%Y-%m-%dT%H:%M")
    final_report_details = TextAreaField(_l("Final Report Details"), validators=[Optional()])
    csirt_reference = StringField(_l("CSIRT Reference"), validators=[Optional(), Length(max=128)])
    csirt_name = StringField(_l("CSIRT Name"), validators=[Optional(), Length(max=256)])
    notification_status = SelectField(
        _l("Notification Status"),
        choices=[("pending", _l("Pending")), ("early_warning_due", _l("Early Warning Due")),
                 ("early_warning_submitted", _l("Early Warning Submitted")),
                 ("notification_due", _l("Notification Due")),
                 ("notification_submitted", _l("Notification Submitted")),
                 ("final_report_due", _l("Final Report Due")),
                 ("final_report_submitted", _l("Final Report Submitted")),
                 ("completed", _l("Completed"))],
        default="pending",
    )
    notes = TextAreaField(_l("Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class Nis2SupplyChainForm(BaseForm):
    supplier_id = SelectField(_l("Related Supplier"), coerce=int, validators=[Optional()])
    supplier_name = StringField(_l("Supplier Name"), validators=[DataRequired(), Length(max=256)])
    ict_service_type = SelectField(
        _l("ICT Service Type"),
        choices=[("", _l("Select...")), ("cloud", _l("Cloud Services")),
                 ("saas", _l("SaaS")), ("network", _l("Network Services")),
                 ("hardware", _l("Hardware")), ("software", _l("Software")),
                 ("managed_service", _l("Managed Service")),
                 ("consulting", _l("Consulting")), ("other", _l("Other"))],
        validators=[Optional()],
    )
    service_criticality = SelectField(
        _l("Service Criticality"),
        choices=[("low", _l("Low")), ("medium", _l("Medium")), ("high", _l("High")), ("critical", _l("Critical"))],
        default="medium",
    )
    dependency_tier = SelectField(
        _l("Dependency Tier"),
        choices=[("1", _l("Tier 1 - Direct critical")), ("2", _l("Tier 2 - Direct non-critical")),
                 ("3", _l("Tier 3 - Indirect"))],
        default="3",
    )
    security_certifications = StringField(_l("Security Certifications"), validators=[Optional(), Length(max=256)])
    nis2_in_scope = BooleanField(_l("In NIS2 Scope"))
    supply_chain_risk_level = SelectField(
        _l("Supply Chain Risk Level"),
        choices=[("low", _l("Low")), ("medium", _l("Medium")), ("high", _l("High")), ("critical", _l("Critical"))],
        default="medium",
    )
    last_assessment_date = DateField(_l("Last Assessment Date"), validators=[Optional()])
    next_assessment_date = DateField(_l("Next Assessment Date"), validators=[Optional()])
    assessment_findings = TextAreaField(_l("Assessment Findings"), validators=[Optional()])
    mitigation_actions = TextAreaField(_l("Mitigation Actions"), validators=[Optional()])
    subcontractors_known = BooleanField(_l("Subcontractors Identified"))
    subcontractor_details = TextAreaField(_l("Subcontractor Details"), validators=[Optional()])
    sla_in_place = BooleanField(_l("SLA in Place"))
    incident_reporting_defined = BooleanField(_l("Incident Reporting Defined"))
    right_to_audit = BooleanField(_l("Right to Audit"))
    data_processing_agreement = BooleanField(_l("DPA in Place"))
    termination_notice_days = IntegerField(_l("Termination Notice (days)"), validators=[Optional()])
    status = SelectField(
        _l("Status"),
        choices=[("pending", _l("Pending")), ("assessed", _l("Assessed")),
                 ("approved", _l("Approved")), ("review_required", _l("Review Required")),
                 ("rejected", _l("Rejected"))],
        default="pending",
    )
    notes = TextAreaField(_l("Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class Nis2ContinuityForm(BaseForm):
    title = StringField(_l("Plan Title"), validators=[DataRequired(), Length(max=256)])
    plan_type = SelectField(
        _l("Plan Type"),
        choices=[("business_continuity", _l("Business Continuity")),
                 ("disaster_recovery", _l("Disaster Recovery")),
                 ("crisis_management", _l("Crisis Management")),
                 ("combined", _l("Combined"))],
        default="business_continuity",
    )
    scope = TextAreaField(_l("Scope"), validators=[Optional()])
    objectives = TextAreaField(_l("Objectives"), validators=[Optional()])
    critical_services = TextAreaField(_l("Critical Services"), validators=[Optional()])
    rto = StringField(_l("RTO (Recovery Time Objective)"), validators=[Optional(), Length(max=32)])
    rpo = StringField(_l("RPO (Recovery Point Objective)"), validators=[Optional(), Length(max=32)])
    recovery_procedures = TextAreaField(_l("Recovery Procedures"), validators=[Optional()])
    responsible_team = StringField(_l("Responsible Team"), validators=[Optional(), Length(max=256)])
    testing_frequency = SelectField(
        _l("Testing Frequency"),
        choices=[("monthly", _l("Monthly")), ("quarterly", _l("Quarterly")),
                 ("semi_annual", _l("Semi-Annual")), ("annual", _l("Annual")),
                 ("biannual", _l("Biannual"))],
        default="annual",
    )
    last_test_date = DateField(_l("Last Test Date"), validators=[Optional()])
    last_test_result = TextAreaField(_l("Last Test Result"), validators=[Optional()])
    next_test_date = DateField(_l("Next Test Date"), validators=[Optional()])
    maintenance_schedule = TextAreaField(_l("Maintenance Schedule"), validators=[Optional()])
    version = StringField(_l("Version"), validators=[Optional(), Length(max=16)], default="1.0")
    status = SelectField(
        _l("Status"),
        choices=[("draft", _l("Draft")), ("approved", _l("Approved")),
                 ("active", _l("Active")), ("review_required", _l("Review Required")),
                 ("archived", _l("Archived"))],
        default="draft",
    )
    notes = TextAreaField(_l("Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class AssetCheckoutForm(BaseForm):
    assignee_type = SelectField(
        _l("Assignee Type"),
        choices=[("internal", _l("Internal User")), ("external", _l("External Person"))],
        default="internal",
    )
    user_id = SelectField(_l("Internal User"), coerce=int, validators=[Optional()])
    assignee_name = StringField(_l("Full Name"), validators=[Optional(), Length(max=256)])
    department = StringField(_l("Department / Team"), validators=[Optional(), Length(max=128)])
    contact_email = StringField(_l("Contact Email"), validators=[Optional(), Email(), Length(max=120)])
    contact_phone = StringField(_l("Contact Phone"), validators=[Optional(), Length(max=64)])
    expected_return_date = DateField(_l("Expected Return Date"), validators=[Optional()])
    purpose = TextAreaField(_l("Purpose / Reason"), validators=[Optional()])
    notes = TextAreaField(_l("Notes"), validators=[Optional()])
    signature_data = HiddenField(_l("Signature"))
    submit = SubmitField(_l("Check Out Asset"))


class AssetCheckinForm(BaseForm):
    actual_return_date = DateField(_l("Actual Return Date"), validators=[Optional()])
    condition_notes = TextAreaField(_l("Condition on Return"), validators=[Optional()])
    checkin_signature_data = HiddenField(_l("Return Signature"))
    submit = SubmitField(_l("Check In Asset"))


class Nis2ComplianceForm(BaseForm):
    measure = SelectField(
        _l("NIS2 Measure"),
        choices=[("risk_analysis", _l("Risk Analysis & IS Policies")),
                 ("incident_handling", _l("Incident Handling")),
                 ("business_continuity", _l("Business Continuity")),
                 ("supply_chain_security", _l("Supply Chain Security")),
                 ("network_security", _l("Network & Information Security")),
                 ("access_control", _l("Access Control")),
                 ("cryptography", _l("Cryptography")),
                 ("hr_security", _l("HR Security")),
                 ("mfa", _l("Multi-Factor Authentication")),
                 ("security_training", _l("Security Training"))],
        validators=[DataRequired()],
    )
    measure_display = StringField(_l("Measure Display Name"), validators=[DataRequired(), Length(max=256)])
    article_ref = StringField(_l("Article Reference"), validators=[Optional(), Length(max=16)])
    status = SelectField(
        _l("Status"),
        choices=[("not_started", _l("Not Started")), ("in_progress", _l("In Progress")),
                 ("implemented", _l("Implemented")), ("not_applicable", _l("Not Applicable")),
                 ("review_required", _l("Review Required"))],
        default="not_started",
    )
    implementation_details = TextAreaField(_l("Implementation Details"), validators=[Optional()])
    evidence_notes = TextAreaField(_l("Evidence Notes"), validators=[Optional()])
    control_references = StringField(_l("Control References"), validators=[Optional(), Length(max=256)])
    guidance = TextAreaField(_l("Guidance"), validators=[Optional()], render_kw={"readonly": True, "rows": 6})
    target_date = DateField(_l("Target Date"), validators=[Optional()])
    completion_date = DateField(_l("Completion Date"), validators=[Optional()])
    review_date = DateField(_l("Review Date"), validators=[Optional()])
    responsible_person_id = SelectField(_l("Responsible Person"), coerce=int, validators=[Optional()])
    notes = TextAreaField(_l("Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class ManagementReviewForm(BaseForm):
    title = StringField(_l("Review Title"), validators=[DataRequired(), Length(max=256)])
    review_date = DateField(_l("Review Date"), validators=[DataRequired()])
    conducted_by_id = SelectField(_l("Conducted By"), coerce=int, validators=[Optional()])
    agenda = TextAreaField(_l("Agenda"), validators=[Optional()])
    minutes = TextAreaField(_l("Minutes / Notes"), validators=[Optional()])
    attendees = TextAreaField(_l("Attendees"), validators=[Optional()],
                              description=_l("Comma-separated list of names"))
    status = SelectField(
        _l("Status"),
        choices=[("planned", _l("Planned")), ("in_progress", _l("In Progress")),
                 ("completed", _l("Completed"))],
        default="planned",
    )
    recommendations = TextAreaField(_l("Recommendations"), validators=[Optional()])
    next_review_date = DateField(_l("Next Review Date"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class ReviewActionItemForm(BaseForm):
    description = TextAreaField(_l("Action Description"), validators=[DataRequired()])
    owner_id = SelectField(_l("Owner"), coerce=int, validators=[Optional()])
    deadline = DateField(_l("Deadline"), validators=[Optional()])
    status = SelectField(
        _l("Status"),
        choices=[("open", _l("Open")), ("in_progress", _l("In Progress")),
                 ("completed", _l("Completed")), ("closed", _l("Closed"))],
        default="open",
    )
    completed_at = DateField(_l("Completed Date"), validators=[Optional()])
    closure_notes = TextAreaField(_l("Closure Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class BusinessImpactAnalysisForm(BaseForm):
    process_name = StringField(_l("Process Name"), validators=[DataRequired(), Length(max=256)])
    process_owner_id = SelectField(_l("Process Owner"), coerce=int, validators=[Optional()])
    department = StringField(_l("Department"), validators=[Optional(), Length(max=128)])
    description = TextAreaField(_l("Description"), validators=[Optional()])
    dependencies = TextAreaField(_l("Dependencies"), validators=[Optional()])
    criticality = SelectField(
        _l("Criticality"),
        choices=[("low", _l("Low")), ("medium", _l("Medium")),
                 ("high", _l("High")), ("critical", _l("Critical"))],
        default="medium",
    )
    impact_financial = TextAreaField(_l("Financial Impact"), validators=[Optional()])
    impact_operational = TextAreaField(_l("Operational Impact"), validators=[Optional()])
    impact_legal = TextAreaField(_l("Legal / Regulatory Impact"), validators=[Optional()])
    impact_reputation = TextAreaField(_l("Reputation Impact"), validators=[Optional()])
    mtpd = StringField(_l("MTPD (Maximum Tolerable Period of Disruption)"), validators=[Optional(), Length(max=32)])
    rto = StringField(_l("RTO (Recovery Time Objective)"), validators=[Optional(), Length(max=32)])
    rpo = StringField(_l("RPO (Recovery Point Objective)"), validators=[Optional(), Length(max=32)])
    minimum_resources = TextAreaField(_l("Minimum Resources"), validators=[Optional()])
    workaround = TextAreaField(_l("Manual Workaround"), validators=[Optional()])
    assessment_date = DateField(_l("Assessment Date"), validators=[DataRequired()])
    next_review_date = DateField(_l("Next Review Date"), validators=[Optional()])
    status = SelectField(
        _l("Status"),
        choices=[("draft", _l("Draft")), ("reviewed", _l("Reviewed")),
                 ("approved", _l("Approved")), ("archived", _l("Archived"))],
        default="draft",
    )
    notes = TextAreaField(_l("Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class BusinessContinuityPlanForm(BaseForm):
    bia_id = SelectField(_l("Linked Business Impact Analysis (BIA)"), coerce=int, validators=[Optional()])
    title = StringField(_l("Plan Title"), validators=[DataRequired(), Length(max=256)])
    plan_type = SelectField(
        _l("Plan Type"),
        choices=[("business_continuity", _l("Business Continuity")),
                 ("disaster_recovery", _l("Disaster Recovery")),
                 ("crisis_management", _l("Crisis Management")),
                 ("combined", _l("Combined"))],
        default="business_continuity",
    )
    scope = TextAreaField(_l("Scope"), validators=[Optional()])
    objectives = TextAreaField(_l("Objectives"), validators=[Optional()])
    activation_criteria = TextAreaField(_l("Activation Criteria"), validators=[Optional()])
    critical_processes = TextAreaField(_l("Critical Processes"), validators=[Optional()])
    recovery_strategy = TextAreaField(_l("Recovery Strategy"), validators=[Optional()])
    communication_plan = TextAreaField(_l("Communication Plan"), validators=[Optional()])
    responsible_team = StringField(_l("Responsible Team"), validators=[Optional(), Length(max=256)])
    owner_id = SelectField(_l("Owner"), coerce=int, validators=[Optional()])
    rto = StringField(_l("RTO (Recovery Time Objective)"), validators=[Optional(), Length(max=32)])
    rpo = StringField(_l("RPO (Recovery Point Objective)"), validators=[Optional(), Length(max=32)])
    version = StringField(_l("Version"), validators=[Optional(), Length(max=16)], default="1.0")
    lifecycle_stage = SelectField(
        _l("Lifecycle Stage"),
        choices=[("draft", _l("Draft")), ("review", _l("Review")),
                 ("approved", _l("Approved")), ("active", _l("Active")),
                 ("test_due", _l("Test Due")), ("improvement", _l("Improvement")),
                 ("retired", _l("Retired"))],
        default="draft",
    )
    review_date = DateField(_l("Review Date"), validators=[Optional()])
    next_test_date = DateField(_l("Next Test Date"), validators=[Optional()])
    notes = TextAreaField(_l("Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class BusinessContinuityTestForm(BaseForm):
    plan_id = SelectField(_l("Plan"), coerce=int, validators=[DataRequired()])
    title = StringField(_l("Test Title"), validators=[DataRequired(), Length(max=256)])
    test_type = SelectField(
        _l("Test Type"),
        choices=[("tabletop", _l("Tabletop")), ("walkthrough", _l("Walkthrough")),
                 ("technical", _l("Technical Recovery")), ("full_interruption", _l("Full Interruption")),
                 ("drp", _l("Disaster Recovery Plan (DRP) Test"))],
        default="tabletop",
    )
    scheduled_date = DateField(_l("Scheduled Date"), validators=[Optional()])
    performed_date = DateField(_l("Performed Date"), validators=[Optional()])
    facilitator_id = SelectField(_l("Facilitator"), coerce=int, validators=[Optional()])
    participants = TextAreaField(_l("Participants"), validators=[Optional()])
    objectives = TextAreaField(_l("Objectives"), validators=[Optional()])
    scenario = TextAreaField(_l("Scenario"), validators=[Optional()])
    results = TextAreaField(_l("Results"), validators=[Optional()])
    issues_found = TextAreaField(_l("Issues Found"), validators=[Optional()])
    rto_met = BooleanField(_l("RTO (Recovery Time Objective) Met"))
    rpo_met = BooleanField(_l("RPO (Recovery Point Objective) Met"))
    outcome = SelectField(
        _l("Outcome"),
        choices=[("planned", _l("Planned")), ("passed", _l("Passed")),
                 ("partial", _l("Partially Passed")), ("failed", _l("Failed")),
                 ("cancelled", _l("Cancelled"))],
        default="planned",
    )
    next_test_date = DateField(_l("Next Test Date"), validators=[Optional()])
    evidence_reference = StringField(_l("Evidence Reference"), validators=[Optional(), Length(max=256)])
    submit = SubmitField(_l("Save"))


class BusinessContinuityActionForm(BaseForm):
    test_id = SelectField(_l("Related Test"), coerce=int, validators=[Optional()])
    description = TextAreaField(_l("Action Description"), validators=[DataRequired()])
    owner_id = SelectField(_l("Owner"), coerce=int, validators=[Optional()])
    due_date = DateField(_l("Due Date"), validators=[Optional()])
    status = SelectField(
        _l("Status"),
        choices=[("open", _l("Open")), ("in_progress", _l("In Progress")),
                 ("completed", _l("Completed")), ("closed", _l("Closed"))],
        default="open",
    )
    closure_notes = TextAreaField(_l("Closure Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class CapaRequestForm(BaseForm):
    title = StringField(_l("Title"), validators=[DataRequired(), Length(max=256)])
    description = TextAreaField(_l("Description"), validators=[DataRequired()])
    source_type = SelectField(
        _l("Source Type"),
        choices=[("internal", _l("Internal")), ("audit", _l("Audit")),
                 ("incident", _l("Incident")), ("complaint", _l("Complaint")),
                 ("supplier", _l("Supplier")), ("regulatory", _l("Regulatory")),
                 ("other", _l("Other"))],
        default="internal",
    )
    source_reference = StringField(_l("Source Reference"), validators=[Optional(), Length(max=128)])
    severity = SelectField(
        _l("Severity"),
        choices=[("minor", _l("Minor")), ("major", _l("Major")), ("critical", _l("Critical"))],
        default="medium",
    )
    status = SelectField(
        _l("Status"),
        choices=[("open", _l("Open")), ("under_review", _l("Under Review")),
                 ("action_planned", _l("Action Planned")),
                 ("in_progress", _l("In Progress")),
                 ("verified", _l("Verified")), ("closed", _l("Closed"))],
        default="open",
    )
    root_cause = TextAreaField(_l("Root Cause Analysis"), validators=[Optional()])
    root_cause_category = SelectField(
        _l("Root Cause Category"),
        choices=[("", _l("Select...")), ("people", _l("People")),
                 ("process", _l("Process")), ("technology", _l("Technology")),
                 ("external", _l("External")), ("other", _l("Other"))],
        validators=[Optional()],
    )
    proposed_action = TextAreaField(_l("Proposed Action / Corrective Plan"), validators=[Optional()])
    action_owner_id = SelectField(_l("Action Owner"), coerce=int, validators=[Optional()])
    target_date = DateField(_l("Target Completion Date"), validators=[Optional()])
    effectiveness_review = TextAreaField(_l("Effectiveness Review"), validators=[Optional()])
    effectiveness_rating = SelectField(
        _l("Effectiveness Rating"),
        choices=[("", _l("Select...")),
                 ("effective", _l("Effective")),
                 ("partially_effective", _l("Partially Effective")),
                 ("ineffective", _l("Ineffective"))],
        validators=[Optional()],
    )
    closure_notes = TextAreaField(_l("Closure Notes"), validators=[Optional()])
    created_by_id = SelectField(_l("Created By"), coerce=int, validators=[Optional()])
    assigned_to_id = SelectField(_l("Assigned To"), coerce=int, validators=[Optional()])
    submit = SubmitField(_l("Save"))


class TrainingCourseForm(BaseForm):
    title = StringField(_l("Course Title"), validators=[DataRequired(), Length(max=256)])
    description = TextAreaField(_l("Description"), validators=[Optional()])
    category = SelectField(
        _l("Category"),
        choices=[("awareness", _l("Awareness")), ("technical", _l("Technical")),
                 ("process", _l("Process")), ("compliance", _l("Compliance")),
                 ("management", _l("Management")), ("other", _l("Other"))],
        default="awareness",
    )
    provider = StringField(_l("Provider"), validators=[Optional(), Length(max=256)])
    duration_hours = FloatField(_l("Duration (hours)"), validators=[Optional()])
    validity_days = IntegerField(_l("Validity (days)"), validators=[Optional()])
    is_mandatory = BooleanField(_l("Mandatory"))
    status = SelectField(
        _l("Status"),
        choices=[("active", _l("Active")), ("inactive", _l("Inactive")),
                 ("archived", _l("Archived"))],
        default="active",
    )
    submit = SubmitField(_l("Save"))


class TrainingSessionForm(BaseForm):
    title = StringField(_l("Session Title"), validators=[Optional(), Length(max=256)])
    session_date = DateField(_l("Date"), validators=[DataRequired()])
    trainer = StringField(_l("Trainer"), validators=[Optional(), Length(max=256)])
    location = StringField(_l("Location / Platform"), validators=[Optional(), Length(max=256)])
    max_attendees = IntegerField(_l("Max Attendees"), validators=[Optional()])
    status = SelectField(
        _l("Status"),
        choices=[("scheduled", _l("Scheduled")), ("in_progress", _l("In Progress")),
                 ("completed", _l("Completed")), ("cancelled", _l("Cancelled"))],
        default="scheduled",
    )
    notes = TextAreaField(_l("Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))


class TrainingRecordForm(BaseForm):
    status = SelectField(
        _l("Status"),
        choices=[("enrolled", _l("Enrolled")), ("completed", _l("Completed")),
                 ("no_show", _l("No Show")), ("expired", _l("Expired"))],
        default="enrolled",
    )
    completed_date = DateField(_l("Completed Date"), validators=[Optional()])
    score = FloatField(_l("Score (%)"), validators=[Optional()])
    feedback = TextAreaField(_l("Feedback"), validators=[Optional()])
    certificate_ref = StringField(_l("Certificate Ref"), validators=[Optional(), Length(max=128)])
    submit = SubmitField(_l("Save"))


class CompetenceProfileForm(BaseForm):
    user_id = SelectField(_l("User"), coerce=int, choices=[])
    skill_name = StringField(_l("Skill / Competence"), validators=[DataRequired(), Length(max=128)])
    skill_level = SelectField(
        _l("Skill Level"),
        choices=[("beginner", _l("Beginner")), ("intermediate", _l("Intermediate")),
                 ("advanced", _l("Advanced")), ("expert", _l("Expert"))],
        default="beginner",
    )
    category = SelectField(
        _l("Category"),
        choices=[("technical", _l("Technical")), ("security", _l("Security")),
                 ("compliance", _l("Compliance")), ("management", _l("Management")),
                 ("soft_skill", _l("Soft Skill")), ("other", _l("Other"))],
        default="technical",
    )
    last_assessment_date = DateField(_l("Last Assessment Date"), validators=[Optional()])
    expiry_date = DateField(_l("Expiry Date"), validators=[Optional()])
    notes = TextAreaField(_l("Notes"), validators=[Optional()])
    submit = SubmitField(_l("Save"))
