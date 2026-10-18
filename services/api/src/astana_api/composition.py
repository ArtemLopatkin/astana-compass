"""Only this module loads team implementations; missing live adapters fail closed."""
from dataclasses import dataclass
from importlib import import_module
from inspect import isawaitable
from contextlib import AsyncExitStack

from astana_recommender import DefaultRecommendationService
from .fixtures import FixtureRepository, FixtureRetriever, FixtureContext


@dataclass
class Services:
    repository: object
    recommender: object


def resolve(path):
    module, separator, name = path.partition(":")
    if not separator or not module or not name:
        raise ValueError("Factory must use module:function syntax")
    factory = getattr(import_module(module), name)
    if not callable(factory):
        raise ValueError("Adapter factory must be callable")
    return factory


async def own(stack: AsyncExitStack, resource):
    if isawaitable(resource):
        resource = await resource
    if callable(getattr(resource, "aclose", None)):
        stack.push_async_callback(resource.aclose)
    elif callable(getattr(resource, "close", None)):
        stack.callback(resource.close)
    return resource


async def build_services(settings, stack):
    if settings.mode == "fixture":
        repository = FixtureRepository()
        retriever = FixtureRetriever(repository)
        context = FixtureContext()
    else:
        # Config contains no secrets; each server-side adapter reads its documented env.
        config = {"timezone": "Asia/Almaty", "mode": "live"}
        repository = await own(stack, resolve(settings.repository_factory)(config=config))
        retriever = await own(stack, resolve(settings.retriever_factory)(repository=repository, config=config))
        context = await own(stack, resolve(settings.context_factory)(config=config))
    generator = None
    if settings.llm_provider != "none":
        from astana_ai_providers import create_generator
        generator = await own(stack, create_generator(provider=settings.llm_provider, model=settings.llm_model, api_key=settings.llm_api_key))
    recommender = DefaultRecommendationService(repository, retriever, context, generator=generator)
    return Services(repository=repository, recommender=recommender)
