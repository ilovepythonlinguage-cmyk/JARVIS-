from urllib.parse import quote_plus
import shutil
from jarvis.actions.base import ActionContext, ActionResult, registry
from jarvis.actions.helpers import run_detached
from jarvis.core.models import Command, Intent

def _open(url: str, context: ActionContext, message: str) -> ActionResult:
    browser = context.settings.browser
    command = [browser, url] if shutil.which(browser) else ["xdg-open", url]
    return run_detached(command, message)

@registry.register(Intent.OPEN_WEBSITE)
def open_website(command: Command, context: ActionContext) -> ActionResult:
    target = command.slots["target"]
    return _open(str(context.websites[target]["url"]), context, f"Abrindo {target}.")

@registry.register(Intent.WEB_SEARCH, Intent.YOUTUBE_SEARCH)
def search(command: Command, context: ActionContext) -> ActionResult:
    query = quote_plus(str(command.slots["query"]))
    base = "https://www.youtube.com/results?search_query=" if command.intent is Intent.YOUTUBE_SEARCH else "https://www.google.com/search?q="
    return _open(base + query, context, "Pesquisando.")
