from langchain.callbacks.manager import (
        CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
    )
from langchain.llms.base import create_base_retry_decorator

from langchain.llms.base import BaseLLM
from langchain.chat_models.base import BaseChatModel

import logging
from http import HTTPStatus

from typing import Optional, Union, Callable, Any

logger = logging.getLogger(__name__)


def completion_with_retry(
    llm_model: BaseLLM | BaseChatModel,
    run_manager: Optional[CallbackManagerForLLMRun] = None,
    **kwargs: Any
) -> Any:
    """Use tenacity to retry the completion call."""
    retry_decorator = _create_retry_decorator(llm_model, run_manager=run_manager)

    @retry_decorator
    def _completion_with_retry(**_kwargs: Any) -> Any:
        print("#"*60)
        print("kwargs: ", _kwargs)

        resp = llm_model.client.call(**_kwargs)
        print("<<- response: ", resp)
        if resp.status_code == HTTPStatus.OK:
            pass
        elif resp.status_code == HTTPStatus.BAD_REQUEST and "contain inappropriate content" in resp.message:
            resp.status_code = HTTPStatus.OK
            resp.output = {
                "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Input data may contain inappropriate content.🐶"}}]
            }
            resp.usage = {"output_tokens": 0, "input_tokens": 0}
        else:
            # TODO: error handling
            print("<<- http request failed: %s", resp.http_status)
        return resp

    return _completion_with_retry(**kwargs)


def _create_retry_decorator(
    llm_model: BaseLLM | BaseChatModel,
    run_manager: Optional[
        Union[AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun]
    ] = None,
) -> Callable[[Any], Any]:
    import dashscope

    errors = [
        # TODO: add more errors
        dashscope.common.error.RequestFailure,
        dashscope.common.error.InvalidInput,
        dashscope.common.error.ModelRequired,
    ]
    
    return create_base_retry_decorator(
        error_types=errors, max_retries=llm_model.max_retries, run_manager=run_manager
    )
