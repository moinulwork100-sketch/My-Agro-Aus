from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


def _split_csv(value):
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def _validate_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise ValueError("Enter a valid email address")
    return email


def _validate_strong_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not any(char.islower() for char in value):
        raise ValueError("Password must include a lowercase letter")
    if not any(char.isupper() for char in value):
        raise ValueError("Password must include an uppercase letter")
    if not any(char.isdigit() for char in value):
        raise ValueError("Password must include a number")
    if not any(not char.isalnum() for char in value):
        raise ValueError("Password must include a symbol")
    return value


class FeeRuleResponse(BaseModel):
    id: Optional[str] = None
    label: str
    rate: float
    minimum: Optional[float] = None
    maximum: Optional[float] = None


class PlatformConfigResponse(BaseModel):
    investor_fee_rate: float
    farmer_fee_rate: float
    investor_fee_tiers: list[FeeRuleResponse] = Field(default_factory=list)
    farmer_fee_tiers: list[FeeRuleResponse] = Field(default_factory=list)


class PlatformConfigUpdate(BaseModel):
    admin_id: str
    investor_fee_tiers: list[FeeRuleResponse]
    farmer_fee_tiers: list[FeeRuleResponse]

    @field_validator("investor_fee_tiers", "farmer_fee_tiers")
    @classmethod
    def validate_rates(cls, value: list[FeeRuleResponse]) -> list[FeeRuleResponse]:
        for rule in value:
            if rule.rate < 0 or rule.rate > 1:
                raise ValueError("Fee rule rates must be between 0 and 1")
        return value


class UserCreate(BaseModel):
    name: Optional[str] = None
    email: str
    password: Optional[str] = None
    remember_me: bool = False


class LoginCredentials(BaseModel):
    email: str
    password: str
    remember_me: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _validate_email(value)


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_strong_password(value)


class PasswordResetResponse(BaseModel):
    message: str
    reset_token: Optional[str] = None


class RegistrationAccount(BaseModel):
    name: str = Field(min_length=2)
    email: str
    password: str
    confirm_password: str
    country: str = Field(min_length=2)
    phone: str = Field(min_length=5)
    remember_me: bool = False

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return _validate_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_strong_password(value)

    @model_validator(mode="after")
    def validate_password_confirmation(self):
        if self.password != self.confirm_password:
            raise ValueError("Password confirmation does not match")
        return self


class InvestorRegister(RegistrationAccount):
    investor_type: Literal["Individual", "Company"]
    investment_interests: list[str] = Field(min_length=1)
    risk_tolerance: Literal["Low", "Medium", "High"]
    preferred_crops: list[str] = Field(min_length=1)
    preferred_investment_size: str = Field(min_length=2)
    kyc_status: str = "not_started"
    government_id_verification: str = "not_started"
    bank_verification: str = "not_started"

    @field_validator("investment_interests", "preferred_crops", mode="before")
    @classmethod
    def split_lists(cls, value):
        return _split_csv(value)


class FarmerRegister(BaseModel):
    name: str
    email: str
    password: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None


class FarmerOnboardingRegister(RegistrationAccount):
    farm_name: str = Field(min_length=2)
    farm_location: str = Field(min_length=2)
    farming_experience_years: int = Field(ge=0, le=100)
    farm_size: str = Field(min_length=1)
    crop_categories: list[str] = Field(min_length=1)
    farm_description: str = Field(min_length=20)
    profile_photo_url: Optional[str] = None
    land_ownership_verification: str = "not_started"
    government_id_verification: str = "not_started"
    farm_inspection_verification: str = "not_started"
    banking_verification: str = "not_started"

    @field_validator("crop_categories", mode="before")
    @classmethod
    def split_crop_categories(cls, value):
        return _split_csv(value)


class EmailVerificationRequest(BaseModel):
    token: str


class EmailVerificationResend(BaseModel):
    user_id: str


class EmailVerificationResponse(BaseModel):
    message: str
    verification_token: Optional[str] = None


class ProfileUpdate(BaseModel):
    phone: Optional[str] = None
    country: Optional[str] = None
    investor_type: Optional[Literal["Individual", "Company"]] = None
    investment_interests: Optional[list[str]] = None
    risk_tolerance: Optional[Literal["Low", "Medium", "High"]] = None
    preferred_crops: Optional[list[str]] = None
    preferred_investment_size: Optional[str] = None
    profile_photo_url: Optional[str] = None
    farm_name: Optional[str] = None
    farm_location: Optional[str] = None
    farming_experience_years: Optional[int] = Field(default=None, ge=0, le=100)
    farm_size: Optional[str] = None
    crop_categories: Optional[list[str]] = None
    farm_description: Optional[str] = None

    @field_validator("investment_interests", "preferred_crops", "crop_categories", mode="before")
    @classmethod
    def split_lists(cls, value):
        return _split_csv(value)


class FarmerLogin(BaseModel):
    email: Optional[str] = None
    identifier: Optional[str] = None
    password: str
    remember_me: bool = False


class AdminLogin(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    access_code: Optional[str] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    role: str = "investor"
    farmer_id: Optional[str] = None
    created_at: Optional[datetime] = None


class AuthSession(BaseModel):
    id: str
    name: str
    email: str
    role: str
    farmer_id: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    email_verified: bool = False
    profile_completion: int = 0
    profile_minimum_met: bool = False
    missing_profile_items: list[str] = Field(default_factory=list)
    investor_type: Optional[str] = None
    investment_interests: list[str] = Field(default_factory=list)
    risk_tolerance: Optional[str] = None
    preferred_crops: list[str] = Field(default_factory=list)
    preferred_investment_size: Optional[str] = None
    kyc_status: Optional[str] = None
    government_id_verification: Optional[str] = None
    bank_verification: Optional[str] = None
    farm_name: Optional[str] = None
    farm_location: Optional[str] = None
    farming_experience_years: Optional[int] = None
    farm_size: Optional[str] = None
    crop_categories: list[str] = Field(default_factory=list)
    farm_description: Optional[str] = None
    profile_photo_url: Optional[str] = None
    land_ownership_verification: Optional[str] = None
    farm_inspection_verification: Optional[str] = None
    banking_verification: Optional[str] = None
    email_verification_token: Optional[str] = None
    session_expires_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class FarmerSummary(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    verified: bool
    rating: float
    completed_projects: int
    on_time_rate: int
    risk_classification: Optional[str] = None
    portrait_url: Optional[str] = None
    reputation_score: Optional[float] = None
    project_success_rate: Optional[float] = None
    investor_satisfaction_score: Optional[float] = None
    years_experience: Optional[int] = None
    crop_categories: list[str] = Field(default_factory=list)


class HistoricalProjectPerformance(BaseModel):
    farm_id: Optional[str] = None
    name: Optional[str] = None
    crop_type: Optional[str] = None
    status: Optional[str] = None
    success_rate: Optional[float] = None
    funded_percent: Optional[int] = None
    total_raised: float = 0
    profit_generated: float = 0
    completed_on_time: bool = False


class FarmerReputationProfile(BaseModel):
    overall_rating: float
    reputation_score: float
    total_completed_projects: int
    total_active_projects: int
    total_funded_projects: int
    total_investment_received: float
    total_profit_generated: float
    project_success_rate: float
    on_time_completion_rate: float
    investor_satisfaction_score: float
    years_experience: int
    crop_categories: list[str] = Field(default_factory=list)
    verification_status: str
    failed_projects: int = 0
    historical_project_performance: list[HistoricalProjectPerformance] = Field(default_factory=list)


class ReviewResponse(BaseModel):
    id: str
    rating: int
    comment: Optional[str] = None
    reviewer_name: Optional[str] = None
    created_at: Optional[datetime] = None


class ReviewCreate(BaseModel):
    user_id: str
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    reviewer_name: Optional[str] = None


class FarmerResponse(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    verified: bool
    rating: float
    completed_projects: int
    on_time_rate: int
    risk_classification: Optional[str] = None
    bio: Optional[str] = None
    portrait_url: Optional[str] = None
    reviews: list[ReviewResponse] = Field(default_factory=list)
    reputation: Optional[FarmerReputationProfile] = None


class FarmListItem(BaseModel):
    id: str
    name: str
    crop_type: str
    location: str
    expected_roi: float
    risk_level: str
    success_rate: Optional[int] = None
    days_left: Optional[int] = None
    funded_percent: Optional[int] = None
    harvest_date: Optional[date] = None
    status: str
    image_type: Optional[str] = None
    farmer_id: Optional[str] = None
    farmer_name: Optional[str] = None
    farmer_rating: Optional[float] = None
    risk_score: Optional[int] = None
    risk_reasoning_summary: Optional[str] = None
    current_milestone: Optional[str] = None
    progress_percent: Optional[int] = None


class RiskAssessmentResponse(BaseModel):
    risk_level: str
    risk_score: int
    risk_reasoning_summary: str
    risk_reasons: list[str] = Field(default_factory=list)
    risk_factors: dict[str, float] = Field(default_factory=dict)


class FarmDetailResponse(BaseModel):
    id: str
    name: str
    crop_type: str
    location: str
    expected_roi: float
    risk_level: str
    success_rate: Optional[int] = None
    duration_months: Optional[int] = None
    harvest_date: Optional[date] = None
    funded_percent: Optional[int] = None
    total_funding_goal: Optional[float] = None
    days_left: Optional[int] = None
    status: str
    image_type: Optional[str] = None
    farmer: Optional[FarmerSummary] = None
    risk_score: Optional[int] = None
    risk_reasoning_summary: Optional[str] = None
    risk_reasons: list[str] = Field(default_factory=list)
    risk_factors: dict[str, float] = Field(default_factory=dict)
    ai_insight: Optional[str] = None
    current_milestone: Optional[str] = None
    progress_percent: Optional[int] = None
    expected_completion_date: Optional[date] = None
    reputation: Optional[FarmerReputationProfile] = None


class InvestorSummary(BaseModel):
    id: str
    name: str
    email: Optional[str] = None


class InvestmentCreate(BaseModel):
    user_id: str
    farm_id: str
    amount: float

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: float) -> float:
        if value < 100 or value > 10000:
            raise ValueError("Investment amount must be between $100 and $10,000")
        return value


class InvestmentResponse(BaseModel):
    id: str
    user_id: str
    farm_id: str
    amount: float
    expected_return: float
    gross_profit: float = 0
    investor_fee_rate: float = 0
    investor_platform_fee: float = 0
    net_profit: float = 0
    farmer_fee_rate: float = 0
    farmer_platform_fee: float = 0
    farmer_payout: float = 0
    loss_protection_applied: bool = False
    status: str
    created_at: Optional[datetime] = None
    farm: Optional[FarmListItem] = None
    user: Optional[InvestorSummary] = None


class PortfolioSummary(BaseModel):
    total_invested: float
    expected_returns: float
    total_gross_profit: float
    total_platform_fees: float
    total_net_profit: float
    projected_percent: float
    investments: list[InvestmentResponse]


class ProgressResponse(BaseModel):
    id: str
    farm_id: str
    milestone: Optional[str] = None
    progress_percent: Optional[int] = None
    stage: Optional[str] = None
    health: Optional[str] = None
    weather: Optional[str] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    document_url: Optional[str] = None
    yield_report: Optional[str] = None
    expense_report: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


class ProgressCreate(BaseModel):
    farmer_id: str
    milestone: str
    progress_percent: Optional[int] = Field(default=None, ge=0, le=100)
    stage: Optional[str] = None
    health: Optional[str] = None
    weather: Optional[str] = None
    photo_url: Optional[str] = None
    video_url: Optional[str] = None
    document_url: Optional[str] = None
    yield_report: Optional[str] = None
    expense_report: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("milestone")
    @classmethod
    def validate_milestone(cls, value: str) -> str:
        allowed = {
            "Planning",
            "Land Preparation",
            "Planting",
            "Growing",
            "Harvesting",
            "Distribution",
            "Completed",
        }
        if value not in allowed:
            raise ValueError("Invalid milestone")
        return value


class ProjectTimelineResponse(BaseModel):
    start_date: Optional[datetime] = None
    current_milestone: str
    expected_completion_date: Optional[date] = None
    progress_percent: int
    latest_update: Optional[ProgressResponse] = None
    milestones: list[dict[str, str]] = Field(default_factory=list)


class MessageCreate(BaseModel):
    sender: str
    body: str

    @field_validator("sender")
    @classmethod
    def validate_sender(cls, value: str) -> str:
        if value not in ("investor", "farmer"):
            raise ValueError("sender must be 'investor' or 'farmer'")
        return value


class MessageResponse(BaseModel):
    id: str
    investment_id: str
    sender: str
    body: str
    created_at: Optional[datetime] = None


class ChartDatum(BaseModel):
    id: Optional[str] = None
    label: str
    value: float
    sublabel: Optional[str] = None


class GrowthDatum(BaseModel):
    label: str
    revenue: float
    profit: float


class InvestorDashboardResponse(BaseModel):
    user: UserResponse
    portfolio: PortfolioSummary
    most_invested_farmer: Optional[ChartDatum] = None
    most_invested_crop: Optional[ChartDatum] = None
    platform_fee_rate: float


class FarmerProjectSummary(BaseModel):
    farm: FarmListItem
    investments: list[InvestmentResponse]
    total_raised: float
    farmer_platform_fee: float
    net_farmer_payout: float
    expected_farmer_profit: float
    funding_progress: float
    status: str
    progress_percent: Optional[int] = None
    current_milestone: Optional[str] = None
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None


class FarmerDashboardResponse(BaseModel):
    farmer: FarmerResponse
    projects: list[FarmerProjectSummary]
    total_raised: float
    total_farmer_fees: float
    net_farmer_payout: float
    most_active_investors: list[ChartDatum]
    platform_fee_rate: float


class AdminTotals(BaseModel):
    total_platform_commission: float
    total_investment_volume: float
    total_farmer_payouts: float
    total_investor_profit: float
    active_projects: int
    completed_projects: int
    user_count: int
    farmer_count: int
    low_risk_projects: int = 0
    medium_risk_projects: int = 0
    high_risk_projects: int = 0
    average_farmer_rating: float = 0
    platform_revenue: float = 0
    total_farmer_profit: float = 0
    profit_sharing_revenue: float = 0


class AdminAnalytics(BaseModel):
    revenue_by_month: list[ChartDatum]
    growth_over_time: list[GrowthDatum]
    revenue_breakdown: list[ChartDatum]
    most_invested_farmers: list[ChartDatum]
    most_invested_crops: list[ChartDatum]
    most_frequent_investors: list[ChartDatum]
    risk_distribution: list[ChartDatum] = Field(default_factory=list)
    top_performing_farmers: list[ChartDatum] = Field(default_factory=list)
    lowest_performing_farmers: list[ChartDatum] = Field(default_factory=list)
    project_success_rates: list[ChartDatum] = Field(default_factory=list)
    risk_trends_over_time: list[ChartDatum] = Field(default_factory=list)


class AdminDashboardResponse(BaseModel):
    totals: AdminTotals
    users: list[UserResponse]
    projects: list[FarmListItem]
    investments: list[InvestmentResponse]
    analytics: AdminAnalytics


class OutstandingFeeInvestment(BaseModel):
    investment_id: str
    farm_name: str
    fee_type: str
    amount: float
    completed_at: Optional[datetime] = None


class OutstandingFeeUser(BaseModel):
    user_id: str
    name: str
    email: str
    role: str
    farmer_id: Optional[str] = None
    farm_name: Optional[str] = None
    total_outstanding: float
    investment_count: int
    last_notified_at: Optional[datetime] = None
    investments: list[OutstandingFeeInvestment]


class OutstandingFeesResponse(BaseModel):
    investors: list[OutstandingFeeUser]
    farmers: list[OutstandingFeeUser]
    total_investor_outstanding: float
    total_farmer_outstanding: float
    grand_total: float


class FeeNotifyPayload(BaseModel):
    admin_id: str
    user_ids: list[str]
    message: Optional[str] = None


class FeeSettleItem(BaseModel):
    investment_id: str
    user_id: str
    fee_type: str
    amount: float
    notes: Optional[str] = None


class FeeSettlePayload(BaseModel):
    admin_id: str
    settlements: list[FeeSettleItem]


class FeeNotificationResponse(BaseModel):
    id: str
    message: str
    sent_at: datetime
