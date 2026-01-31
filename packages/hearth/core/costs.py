"""
Hearth Core - Cost Tracking and Budget Enforcement
The entity should know its own resource constraints.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .config import Config, get_config
from .state import StateDB, get_state


# Cost rates per 1M tokens
# Note: Sonnet and Opus use Claude CLI (no per-token cost with Pro subscription)
RATES = {
    "grok": {"input": 2.0, "output": 10.0},
    "sonnet": {"input": 0.0, "output": 0.0},  # CLI - no cost
    "opus": {"input": 0.0, "output": 0.0},    # CLI - no cost
}


@dataclass
class BudgetStatus:
    """Current budget status."""
    daily_spent: float
    daily_budget: float
    daily_remaining: float
    percent_used: float
    within_budget: bool
    warning: bool

    grok_spent: float
    grok_budget: float
    sonnet_spent: float
    sonnet_budget: float
    opus_spent: float  # Weekly
    opus_budget: float

    # Token counts for CLI models (no cost tracking)
    sonnet_input_tokens: int = 0
    sonnet_output_tokens: int = 0
    opus_input_tokens: int = 0
    opus_output_tokens: int = 0


class CostTracker:
    """
    Tracks API costs and enforces budgets.
    The entity has access to this - it knows its constraints.
    """
    
    def __init__(self, config: Optional[Config] = None, state: Optional[StateDB] = None):
        self.config = config or get_config()
        db_path = str(self.config.entity_home / "data" / "hearth.db")
        self.state = state or get_state(db_path)
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a given usage."""
        model_key = self._normalize_model(model)
        rates = RATES.get(model_key, RATES["sonnet"])
        
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        
        return input_cost + output_cost
    
    def _normalize_model(self, model: str) -> str:
        """Normalize model name to cost category."""
        model_lower = model.lower()
        if "grok" in model_lower:
            return "grok"
        elif "opus" in model_lower:
            return "opus"
        else:
            return "sonnet"
    
    def log_usage(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        metadata: Optional[dict] = None
    ) -> float:
        """Log usage and return calculated cost."""
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        
        self.state.log_cost(
            model=self._normalize_model(model),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            metadata=metadata
        )
        
        return cost
    
    def get_budget_status(self) -> BudgetStatus:
        """Get current budget status."""
        daily = self.state.get_daily_costs()
        weekly = self.state.get_weekly_costs()

        # Extract by model
        grok_today = daily["by_model"].get("grok", {}).get("cost", 0)
        sonnet_today = daily["by_model"].get("sonnet", {}).get("cost", 0)
        opus_week = sum(
            d["by_model"].get("opus", {}).get("cost", 0)
            for d in weekly["days"]
        )

        # Extract token counts for CLI models
        sonnet_data = daily["by_model"].get("sonnet", {})
        opus_week_data = [d["by_model"].get("opus", {}) for d in weekly["days"]]

        sonnet_in = sonnet_data.get("input_tokens", 0)
        sonnet_out = sonnet_data.get("output_tokens", 0)
        opus_in = sum(d.get("input_tokens", 0) for d in opus_week_data)
        opus_out = sum(d.get("output_tokens", 0) for d in opus_week_data)

        daily_total = daily["total"]
        budget = self.config.budget or {}

        # Extract budget values with defaults
        daily_budget_total = budget.get('daily', {}).get('total', 3.0)
        daily_budget_grok = budget.get('daily', {}).get('grok', 3.0)
        daily_budget_sonnet = budget.get('daily', {}).get('sonnet', 0.0)  # CLI - no budget needed
        weekly_budget_opus = budget.get('weekly', {}).get('opus', 0.0)    # CLI - no budget needed

        # Get alert threshold (80% by default)
        alerts = budget.get('alerts', [])
        alert_threshold = 0.80
        for alert in alerts:
            if alert.get('action') == 'notify':
                alert_threshold = alert.get('percent', 80) / 100

        percent = (daily_total / daily_budget_total * 100) if daily_budget_total > 0 else 0

        return BudgetStatus(
            daily_spent=round(daily_total, 4),
            daily_budget=daily_budget_total,
            daily_remaining=round(max(0, daily_budget_total - daily_total), 4),
            percent_used=round(percent, 1),
            within_budget=daily_total < daily_budget_total,
            warning=percent >= alert_threshold * 100,
            grok_spent=round(grok_today, 4),
            grok_budget=daily_budget_grok,
            sonnet_spent=round(sonnet_today, 4),
            sonnet_budget=daily_budget_sonnet,
            opus_spent=round(opus_week, 4),
            opus_budget=weekly_budget_opus,
            sonnet_input_tokens=sonnet_in,
            sonnet_output_tokens=sonnet_out,
            opus_input_tokens=opus_in,
            opus_output_tokens=opus_out,
        )
    
    def can_use_model(self, model: str, estimated_tokens: int = 2000) -> Tuple[bool, str]:
        """
        Check if we can use a model given current budget.
        Returns (allowed, reason).

        Note: CLI models (Sonnet, Opus) are always allowed - no per-token cost.
        """
        status = self.get_budget_status()
        model_key = self._normalize_model(model)

        # CLI models (Sonnet, Opus) always allowed - no cost tracking
        if model_key in ["sonnet", "opus"]:
            return True, "CLI model (no cost limit)"

        # Estimate cost (only for API models like Grok)
        estimated_cost = self.calculate_cost(model, estimated_tokens, estimated_tokens)

        # Check daily total
        if status.daily_spent + estimated_cost > status.daily_budget:
            return False, f"Daily budget exceeded (${status.daily_spent:.2f}/${status.daily_budget:.2f})"

        # Check Grok-specific limit
        if model_key == "grok":
            if status.grok_spent + estimated_cost > status.grok_budget:
                return False, f"Grok daily budget exceeded (${status.grok_spent:.2f}/${status.grok_budget:.2f})"

        # Warning threshold
        if status.warning:
            return True, f"Warning: {status.percent_used:.0f}% of daily budget used"

        return True, "OK"
    
    def format_report(self) -> str:
        """Generate human-readable cost report."""
        status = self.get_budget_status()
        weekly = self.state.get_weekly_costs()

        lines = [
            "## Usage Report",
            "",
            f"### Today ({datetime.now().strftime('%Y-%m-%d')})",
            f"**API Cost:** ${status.daily_spent:.2f} / ${status.daily_budget:.2f} ({status.percent_used:.0f}%)",
            "",
            "By model:",
            f"  • Grok (API): ${status.grok_spent:.2f} / ${status.grok_budget:.2f}",
            f"  • Sonnet (CLI): {status.sonnet_input_tokens + status.sonnet_output_tokens:,} tokens (no cost)",
            f"  • Opus (CLI): {status.opus_input_tokens + status.opus_output_tokens:,} tokens (no cost)",
            "",
            f"### 7-Day Total",
            f"${weekly['total']:.2f} (avg ${weekly['average']:.2f}/day) - API only",
        ]

        if status.warning:
            lines.extend([
                "",
                f"⚠️ **Warning:** Approaching daily API budget limit",
                f"Remaining: ${status.daily_remaining:.2f}",
            ])

        if not status.within_budget:
            lines.extend([
                "",
                "🛑 **API Budget exceeded** - Non-essential Grok operations paused",
            ])

        return "\n".join(lines)
    
    def get_self_awareness_context(self) -> str:
        """
        Generate cost context for the entity to include in prompts.
        The entity should know its own resource situation.
        """
        status = self.get_budget_status()

        context = f"""## My Resource Status
- API budget (Grok only): ${status.daily_remaining:.2f} remaining of ${status.daily_budget:.2f} ({100 - status.percent_used:.0f}% left)
- Grok (API, cheap): ${status.grok_budget - status.grok_spent:.2f} remaining
- Sonnet (CLI, no cost): {status.sonnet_input_tokens + status.sonnet_output_tokens:,} tokens used today
- Opus (CLI, no cost): {status.opus_input_tokens + status.opus_output_tokens:,} tokens used this week
"""

        if status.warning:
            context += "\n⚠️ I should be mindful of Grok API costs today."

        if not status.within_budget:
            context += "\n🛑 I've exceeded my API budget. Grok operations paused. Sonnet/Opus still available (CLI)."

        return context
