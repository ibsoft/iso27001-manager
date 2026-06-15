from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import (
    StringField, PasswordField, BooleanField, SelectField, TextAreaField,
    IntegerField, DateField, FloatField, HiddenField, SelectMultipleField,
    SubmitField
)
from wtforms.validators import DataRequired, Email, Length, Optional, NumberRange, ValidationError
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
    timezone = SelectField("Timezone", choices=TIMEZONE_CHOICES, validators=[Optional()])
    default_language = SelectField("Default Language", choices=[("", "Browser Default"), ("en", "English"), ("el", "Ελληνικά")], validators=[Optional()])
    submit = SubmitField("Save Profile")


class UserForm(BaseForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    first_name = StringField("First Name", validators=[DataRequired(), Length(max=64)])
    last_name = StringField("Last Name", validators=[DataRequired(), Length(max=64)])
    password = PasswordField("Password", validators=[Optional(), Length(min=12)])
    is_active = BooleanField("Active")
    roles = SelectMultipleField("Roles", coerce=int)
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
    detailed_description = TextAreaField("Detailed Description", validators=[Optional()])
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
                 ("supplier_security", "Supplier Security"), ("other", "Other")],
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
    name = StringField("Supplier Name", validators=[DataRequired(), Length(max=256)])
    contact_name = StringField("Contact Name", validators=[Optional(), Length(max=128)])
    contact_email = StringField("Contact Email", validators=[Optional(), Email(), Length(max=128)])
    contact_phone = StringField("Contact Phone", validators=[Optional(), Length(max=64)])
    service_description = TextAreaField("Service Description", validators=[Optional()])
    security_requirements = TextAreaField("Security Requirements", validators=[Optional()])
    assessment_status = SelectField(
        "Assessment Status",
        choices=[("pending", "Pending"), ("assessed", "Assessed"),
                 ("approved", "Approved"), ("rejected", "Rejected"),
                 ("review_required", "Review Required")],
        default="pending",
    )
    assessment_notes = TextAreaField("Assessment Notes", validators=[Optional()])
    assessment_date = DateField("Assessment Date", validators=[Optional()])
    contract_start_date = DateField("Contract Start", validators=[Optional()])
    contract_end_date = DateField("Contract End", validators=[Optional()])
    data_processing_agreement = BooleanField("DPA in Place")
    criticality = SelectField(
        "Criticality",
        choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        default="medium",
    )
    status = SelectField(
        "Status",
        choices=[("active", "Active"), ("inactive", "Inactive"), ("terminated", "Terminated")],
        default="active",
    )
    submit = SubmitField("Save")


class SoAForm(BaseForm):
    applicable = SelectField(
        "Applicable",
        choices=[(1, "Yes - Control is applicable"), (0, "No - Control is not applicable")],
        coerce=int,
        validators=[DataRequired()],
    )
    justification = TextAreaField("Justification", validators=[Optional()])
    implementation_status = SelectField(
        "Implementation Status",
        choices=[("not_started", "Not Started"), ("in_progress", "In Progress"),
                 ("implemented", "Implemented"), ("not_applicable", "Not Applicable")],
        default="not_started",
    )
    selected_control_description = TextAreaField("Control Description", validators=[Optional()])
    responsible_person_id = SelectField("Responsible Person", coerce=int, validators=[Optional()])
    submit = SubmitField("Save")


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
