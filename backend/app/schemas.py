from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class TechnologyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str
    name: str
    category: str
    description: str | None = None


class TechnologyDetail(TechnologyOut):
    aliases: list[str]
    latest_metrics: dict[str, float]
    devintel_score: float | None = None
    growth_30d: float | None = None
    is_emerging: bool = False


class RankingItem(BaseModel):
    slug: str
    name: str
    category: str
    devintel_score: float | None
    growth_30d: float | None
    is_emerging: bool
    computed_on: date


class MetricPoint(BaseModel):
    metric: str
    source: str
    value: float
    captured_on: date


class PipelineRunOut(BaseModel):
    id: int
    source: str
    started_at: datetime
    finished_at: datetime | None
    status: str
    records_fetched: int
    error_count: int


class ArticleOut(BaseModel):
    id: int
    source: str
    title: str
    url: str
    discussion_url: str | None = None
    author: str | None
    tags: list[str]
    published_at: datetime | None
    score: int
    comments: int
    reading_time: int | None
    technology: str | None = None


class RepoOut(BaseModel):
    rank: int
    full_name: str
    url: str
    description: str | None
    language: str | None
    stars: int
    forks: int
    created_at: datetime | None


class ScorePoint(BaseModel):
    date: date
    score: float


class CompareTech(BaseModel):
    slug: str
    name: str
    category: str
    devintel_score: float | None
    growth_30d: float | None
    is_emerging: bool
    metrics: dict[str, float]
    history: list[ScorePoint]


class CompareOut(BaseModel):
    technologies: list[CompareTech]


class SkillGapRequest(BaseModel):
    skills: list[str] = []
    github_username: str | None = None
    category: str | None = None


class KnownSkill(BaseModel):
    slug: str
    name: str
    category: str
    devintel_score: float | None
    growth_30d: float | None
    source: str            # manual / github / both
    repos: int | None = None


class StarterArticle(BaseModel):
    title: str
    url: str


class Recommendation(BaseModel):
    slug: str
    name: str
    category: str
    priority: float        # 0-100
    devintel_score: float | None
    growth_30d: float | None
    is_emerging: bool
    reasons: list[str]
    related_to: list[str]
    starters: list[StarterArticle]


class GithubSummary(BaseModel):
    username: str
    repos_scanned: int


class Coverage(BaseModel):
    known_in_top10: int
    top10: list[str]


class SkillGapOut(BaseModel):
    known: list[KnownSkill]
    unrecognized: list[str]
    github: GithubSummary | None = None
    coverage: Coverage
    recommendations: list[Recommendation]
    note: str | None = None


class UserOut(BaseModel):
    id: int
    email: str
    name: str | None
    avatar_url: str | None
    github_username: str | None
    role: str


class MeOut(BaseModel):
    authenticated: bool
    login_enabled: bool
    user: UserOut | None = None
    banned: bool = False
    profile: "ProfileOut | None" = None


class WatchItemOut(BaseModel):
    slug: str
    name: str
    category: str
    devintel_score: float | None
    growth_30d: float | None
    is_emerging: bool


class ProfileOut(BaseModel):
    user: UserOut
    skills: list[str]
    watchlist: list[WatchItemOut]


class ProfileUpdate(BaseModel):
    github_username: str | None = None


class SkillsUpdate(BaseModel):
    skills: list[str] = []


class SkillsOut(BaseModel):
    skills: list[str]
    unrecognized: list[str]


class CommentIn(BaseModel):
    kind: str
    ref: str
    body: str
    parent_id: int | None = None


class CommentEdit(BaseModel):
    body: str


class VoteIn(BaseModel):
    voted: bool


class ReportIn(BaseModel):
    reason: str


class CommentAuthor(BaseModel):
    name: str
    initial: str


class CommentOut(BaseModel):
    id: int
    author: CommentAuthor | None       # None when the comment is deleted or hidden
    body: str
    status: str                        # visible / deleted / hidden
    created_at: datetime
    edited_at: datetime | None
    score: int
    voted: bool
    mine: bool
    replies: list["CommentOut"] = []


class DiscussionOut(BaseModel):
    kind: str
    ref: str
    total: int
    comments: list[CommentOut]


class VoteOut(BaseModel):
    score: int
    voted: bool


class ReportInfo(BaseModel):
    reason: str
    reporter: str
    created_at: datetime


class CaseOut(BaseModel):
    comment_id: int
    thread_kind: str
    thread_ref: str
    body: str
    status: str
    created_at: datetime
    author_id: int
    author_name: str
    author_banned: bool
    reports: list[ReportInfo]


class ModActionIn(BaseModel):
    action: str            # restore / remove
    note: str | None = None


class BanIn(BaseModel):
    reason: str | None = None


class RoleIn(BaseModel):
    role: str              # moderator / user


class LogOut(BaseModel):
    id: int
    moderator: str
    action: str
    comment_id: int | None
    target_user_id: int | None
    note: str | None
    created_at: datetime


class AdminUserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    banned: bool
    created_at: datetime


class ComponentOut(BaseModel):
    value: float
    rank: float            # 0 to 1: share of technologies this one is ahead of on this signal


class BreakdownTech(BaseModel):
    slug: str
    name: str
    category: str
    devintel_score: float | None
    growth_30d: float | None
    is_emerging: bool
    components: dict[str, ComponentOut]


class BreakdownOut(BaseModel):
    computed_on: date | None
    weights: dict[str, float]          # the default weight of each signal
    technologies: list[BreakdownTech]


MeOut.model_rebuild()


class TopicIn(BaseModel):
    title: str
    body: str
    technology: str | None = None
    article_id: int | None = None


class TopicTech(BaseModel):
    slug: str
    name: str


class TopicArticle(BaseModel):
    id: int
    title: str
    url: str


class TopicOut(BaseModel):
    ref: str
    title: str
    author: CommentAuthor
    created_at: datetime
    last_activity: datetime
    replies: int
    preview: str
    first_comment_id: int
    technology: TopicTech | None
    article: TopicArticle | None


class RelatedTech(BaseModel):
    slug: str
    name: str
    category: str
    together: int          # recent articles that mention both


class LearnArticle(BaseModel):
    id: int
    title: str
    url: str
    author: str | None
    score: int
    reading_time: int | None
    beginner: bool


class RepoLite(BaseModel):
    full_name: str
    url: str
    stars: int
    language: str | None


class TechnologyPageOut(BaseModel):
    technology: TechnologyDetail
    related: list[RelatedTech]
    articles: list[LearnArticle]
    repos: list[RepoLite]


class BacktestEvent(BaseModel):
    slug: str
    technology: str
    flagged_on: date
    forward_growth: float
    median_growth: float
    beat_median: bool


class BacktestOut(BaseModel):
    status: str                      # ready / waiting / no_data
    message: str
    horizon_days: int
    latest_data_date: date | None
    baseline: float
    flags: int
    hits: int
    hit_rate: float | None
    ci_low: float | None
    ci_high: float | None
    avg_forward_growth_flagged: float | None
    avg_forward_growth_all: float | None
    events: list[BacktestEvent]


class SeriesPoint(BaseModel):
    date: date
    value: float


class HistoryOut(BaseModel):
    slug: str
    name: str
    score: list[SeriesPoint]
    metrics: dict[str, list[SeriesPoint]]
