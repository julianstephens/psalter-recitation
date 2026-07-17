from psalter.cli.commands.init import register as register_init
from psalter.cli.commands.learn import register as register_learn
from psalter.cli.commands.progress import register as register_progress
from psalter.cli.commands.review import register as register_review

__all__ = [
    "register_init",
    "register_learn",
    "register_progress",
    "register_review",
]
