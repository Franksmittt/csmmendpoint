from functools import lru_cache
from pathlib import Path

import yaml
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

import engagement_learner

_CONFIG_DIR = Path(__file__).resolve().parent / "config"


@lru_cache(maxsize=1)
def _load_agents_yaml() -> dict:
    """Full ``agents.yaml`` — path anchored to this package (reliable on Streamlit Cloud / any cwd)."""
    with (_CONFIG_DIR / "agents.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def _load_tasks_yaml() -> dict:
    with (_CONFIG_DIR / "tasks.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def inject_engagement_insights(
    research_inputs: dict,
    client_id: int,
    *,
    enabled: bool = True,
) -> dict:
    """
    Mutates ``research_inputs`` with ``engagement_insights`` for ``research_task``.

    When disabled or data is thin (<3 Posted posts with metrics), injects a clear "None" line.
    """
    key = "engagement_insights"
    if not enabled:
        research_inputs[key] = (
            "None — past performance insights are turned off for this run "
            "(Generation Hub toggle)."
        )
        return research_inputs
    if not engagement_learner.client_has_sufficient_engagement_data(client_id):
        research_inputs[key] = (
            "None — fewer than three Posted posts with recorded likes or reach. "
            "Mark posts as Posted and enter metrics to unlock automatic learning."
        )
        return research_inputs
    summary = engagement_learner.build_performance_summary(client_id)
    research_inputs[key] = engagement_learner.format_insights_for_research_task(
        summary["winning_patterns"]
    )
    return research_inputs


@CrewBase
class SocialMediaCrew:
    """
    Client-tailored research + creative crew.

    Required kickoff inputs (all strings):
        company_name, industry, brand_context, tone,
        services_list, target_markets, photography_style, post_format, content_pillar,
        featured_brand ("None" or a key from config.brand_vault.TIRE_BRAND_GUIDELINES),
        brand_guidelines (formatted vault text from format_brand_guidelines_for_prompt),
        brand_models (SA top_models lines from format_brand_models_for_prompt — product enforcement),
        vertical_mode ("firewood" | "battery" | "automotive"),
        battery_featured_line ("Auto" or a battery line like Eco Plus/Power Plus/Willard/Exide/Enertec),
        vertical_creative_rules (from config.vertical_creative.get_vertical_creative_rules_for_tasks),
        research_vertical_hint (short routing line for research_task)

    Creative task JSON (strict): Caption, Image_Generation_Prompt_1_1, Image_Generation_Prompt_9_16,
    Suggested_Text_Overlay {Heading, Footer}, Video_Prompt (non-empty only for Short Video (9:16)).
    Optional input: creative_angle (hook style).
    Legacy single key Image_Generation_Prompt is not used—always output both aspect prompts.
    Caption must end with contact details from brand_context, website when present, and hashtags; omit
    street address when brand_context says online/delivery-only (e.g. Miwesu).
    """

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def market_researcher(self) -> Agent:
        return Agent(config=self.agents_config["market_researcher"])

    @agent
    def content_creator(self) -> Agent:
        return Agent(config=self.agents_config["content_creator"])

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config["research_task"])

    @task
    def content_creation_task(self) -> Task:
        return Task(config=self.tasks_config["content_creation_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=False,
        )


@CrewBase
class CaptionOnlyCrew:
    """Single-task caption regeneration (image prompts unchanged)."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def content_creator(self) -> Agent:
        return Agent(config=self.agents_config["content_creator"])

    @task
    def caption_only_task(self) -> Task:
        return Task(config=self.tasks_config["caption_only_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.content_creator],
            tasks=[self.caption_only_task],
            process=Process.sequential,
            verbose=False,
        )


@CrewBase
class VideoPromptOnlyCrew:
    """Regenerate only the 9:16 video motion prompt (short video format)."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def content_creator(self) -> Agent:
        return Agent(config=self.agents_config["content_creator"])

    @task
    def video_prompt_only_task(self) -> Task:
        return Task(config=self.tasks_config["video_prompt_only_task"])

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.content_creator],
            tasks=[self.video_prompt_only_task],
            process=Process.sequential,
            verbose=False,
        )


@CrewBase
class CriticRefinementCrew:
    """Post-pass QA on a full creative JSON bundle."""

    # Paths for CrewBase metadata only; agent/task configs are loaded explicitly so
    # ``creative_critic`` is always resolved (some CrewAI versions scope agents_config oddly).
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def creative_critic(self) -> Agent:
        cfg = _load_agents_yaml().get("creative_critic")
        if not cfg:
            raise KeyError(
                "creative_critic missing from agents.yaml — check src/config/agents.yaml"
            )
        return Agent(config=cfg)

    @task
    def critic_refine_task(self) -> Task:
        tcfg = _load_tasks_yaml().get("critic_refine_task")
        if not tcfg:
            raise KeyError(
                "critic_refine_task missing from tasks.yaml — check src/config/tasks.yaml"
            )
        return Task(config=tcfg)

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=[self.creative_critic],
            tasks=[self.critic_refine_task],
            process=Process.sequential,
            verbose=False,
        )
